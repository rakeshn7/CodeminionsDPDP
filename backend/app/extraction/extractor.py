from __future__ import annotations

import csv
import html.parser
import io
import json
import logging
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.extraction.ocr import extract_text_from_image, get_ocr_diagnostics

_LOGGER = logging.getLogger(__name__)

# Max file size limit: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".md": "text",
    ".markdown": "text",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tif": "image",
    ".tiff": "image",
}


@dataclass
class PageContent:
    page_number: int
    text: str
    char_count: int


@dataclass
class ExtractionResult:
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int
    full_text: str
    pages: list[dict[str, Any]]
    ocr_used: bool
    ocr_status: dict[str, Any]
    status: str  # "success", "empty", "failed"
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal and unsafe characters."""
    base = Path(name).name
    # Remove control characters, quotes, and dangerous shell symbols
    cleaned = re.sub(r'[\x00-\x1f\\/*?:"<>|]', "", base).strip()
    return cleaned or "unnamed_document"


def _extract_pdf(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    import fitz  # PyMuPDF

    pages: list[PageContent] = []
    warnings: list[str] = []
    ocr_used = False

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise ValueError(f"Could not open PDF file: {exc}") from exc

    try:
        if doc.is_encrypted:
            raise ValueError(
                "The PDF document is password-protected or encrypted. Decrypt before uploading."
            )

        total_pages = len(doc)
        if total_pages == 0:
            return [], False, ["PDF contains 0 pages."]

        diagnostics = get_ocr_diagnostics()
        for idx in range(total_pages):
            page = doc[idx]
            page_text = page.get_text("text", sort=True).strip()
            page_has_images = bool(page.get_images(full=True))
            needs_ocr = not page_text or (len(page_text) < 30 and page_has_images)

            if needs_ocr and diagnostics["available"]:
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                ocr_text, ocr_info = extract_text_from_image(
                    img_bytes,
                    diagnostics=diagnostics,
                )
                ocr_used = True
                if ocr_text:
                    normalized_text = re.sub(r"\W", "", page_text.casefold())
                    normalized_ocr = re.sub(r"\W", "", ocr_text.casefold())
                    if not page_text or normalized_text in normalized_ocr:
                        page_text = ocr_text
                    elif normalized_ocr not in normalized_text:
                        page_text = f"{page_text}\n{ocr_text}"
                else:
                    ocr_issue = ocr_info.get("error", "OCR did not recognize text")
                    warnings.append(
                        f"OCR could not read PDF page {idx + 1}: "
                        f"{ocr_issue}."
                    )
            elif needs_ocr:
                warnings.append(
                    f"PDF page {idx + 1} has image content but OCR is unavailable; "
                    "some text on that page may not be analyzed."
                )

            pages.append(
                PageContent(
                    page_number=idx + 1,
                    text=page_text,
                    char_count=len(page_text),
                )
            )

        if ocr_used:
            warnings.insert(
                0,
                "OCR was used for scanned or image-heavy PDF pages; verify the extracted text before relying on findings.",
            )
        return pages, ocr_used, warnings
    finally:
        doc.close()


def _extract_docx(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    import docx

    try:
        doc = docx.Document(file_path)
    except Exception as exc:
        raise ValueError(f"Corrupt or invalid DOCX document: {exc}") from exc

    parts: list[str] = []
    # Extract paragraphs
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            parts.append(txt)

    # Extract tables
    for table_idx, table in enumerate(doc.tables, 1):
        table_rows = []
        for row in table.rows:
            row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(row_cells):
                table_rows.append(" | ".join(row_cells))
        if table_rows:
            parts.append(f"\n--- [Table {table_idx}] ---\n" + "\n".join(table_rows))

    header_footer_parts: list[str] = []
    for section in doc.sections:
        for label, content in (
            ("Header", section.header),
            ("Footer", section.footer),
        ):
            content_text = "\n".join(
                paragraph.text.strip()
                for paragraph in content.paragraphs
                if paragraph.text.strip()
            )
            entry = f"{label}: {content_text}"
            if content_text and entry not in header_footer_parts:
                header_footer_parts.append(entry)
    parts.extend(header_footer_parts)

    full_text = "\n\n".join(parts).strip()
    warnings = []
    if doc.inline_shapes:
        warnings.append(
            "DOCX contains embedded images; image text is not extracted from those images."
        )
    return [PageContent(page_number=1, text=full_text, char_count=len(full_text))], False, warnings


class _HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        elif tag == "img" and not self._ignored_depth:
            alt = dict(attrs).get("alt")
            if alt:
                self.parts.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data.strip())


def _extract_pptx(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    slide_names = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
    pages: list[PageContent] = []
    warnings: list[str] = []

    try:
        with zipfile.ZipFile(file_path) as archive:
            slides = sorted(
                (
                    (int(match.group(1)), name)
                    for name in archive.namelist()
                    if (match := slide_names.fullmatch(name))
                ),
                key=lambda item: item[0],
            )
            for slide_number, name in slides:
                root = ET.fromstring(archive.read(name))
                paragraphs = []
                for paragraph in root.iter(
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}p"
                ):
                    content = "".join(
                        node.text or ""
                        for node in paragraph.iter(
                            "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
                        )
                    ).strip()
                    if content:
                        paragraphs.append(content)
                text = "\n".join(paragraphs)
                pages.append(PageContent(slide_number, text, len(text)))

            if any(name.startswith("ppt/media/") for name in archive.namelist()):
                warnings.append(
                    "PPTX contains embedded images; image text is not extracted from those images."
                )
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ValueError(f"Corrupt or invalid PowerPoint (PPTX) file: {exc}") from exc

    if not pages:
        warnings.append("PowerPoint file contains no readable slides.")
    return pages, False, warnings


def _extract_text_format(file_path: Path, file_type: str) -> tuple[list[PageContent], bool, list[str]]:
    raw_bytes = file_path.read_bytes()
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    warnings = []

    if file_type == "json":
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            warnings.append("File extension is JSON, but content is invalid JSON; treated as plain text.")
    elif file_type == "html":
        parser = _HTMLTextExtractor()
        parser.feed(text)
        parser.close()
        text = "\n".join(parser.parts)

    text = text.strip()
    return [PageContent(1, text, len(text))], False, warnings


def _extract_txt(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    raw_bytes = file_path.read_bytes()
    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252", "utf-16"]
    text = ""
    used_encoding = "utf-8"

    for enc in encodings:
        try:
            text = raw_bytes.decode(enc)
            used_encoding = enc
            break
        except UnicodeDecodeError:
            continue

    if not text and raw_bytes:
        text = raw_bytes.decode("utf-8", errors="replace")
        used_encoding = "utf-8 (lossy)"

    warnings = [f"Decoded with fallback {used_encoding}."] if used_encoding not in {"utf-8", "utf-8-sig"} else []
    cleaned = text.strip()
    return [PageContent(page_number=1, text=cleaned, char_count=len(cleaned))], False, warnings


def _extract_csv(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    raw_bytes = file_path.read_bytes()
    try:
        text_content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text_content = raw_bytes.decode("latin1", errors="replace")

    stream = io.StringIO(text_content)
    try:
        sample = text_content[:2048]
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
    except Exception:
        dialect = csv.excel

    stream.seek(0)
    reader = csv.reader(stream, dialect=dialect)
    rows = list(reader)

    if not rows:
        return [PageContent(page_number=1, text="", char_count=0)], False, []

    formatted_rows: list[str] = []
    headers = [h.strip() for h in rows[0]] if rows else []

    if headers:
        formatted_rows.append(f"Columns: {', '.join(headers)}")
        formatted_rows.append("-" * 40)

    for r_idx, row in enumerate(rows[1:], start=2):
        non_empty = [c.strip() for c in row if c.strip()]
        if not non_empty:
            continue
        if len(row) == len(headers):
            row_repr = ", ".join(f"{h}: {val.strip()}" for h, val in zip(headers, row) if val.strip())
        else:
            row_repr = ", ".join(row)
        formatted_rows.append(f"Row {r_idx}: {row_repr}")

    full_text = "\n".join(formatted_rows).strip()
    return [PageContent(page_number=1, text=full_text, char_count=len(full_text))], False, []


def _extract_xlsx(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError(f"Corrupt or invalid Excel (XLSX) workbook: {exc}") from exc

    sheets_text: list[str] = []
    warnings: list[str] = []

    try:
        for sheetname in wb.sheetnames:
            sheet = wb[sheetname]
            rows_data: list[str] = []
            for row in sheet.iter_rows(values_only=True):
                vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                if vals:
                    rows_data.append(" | ".join(vals))
            if rows_data:
                sheets_text.append(f"=== Sheet: {sheetname} ===\n" + "\n".join(rows_data))

        if not sheets_text:
            warnings.append("Workbook contains no populated sheets.")

        full_text = "\n\n".join(sheets_text).strip()
        return [PageContent(page_number=1, text=full_text, char_count=len(full_text))], False, warnings
    finally:
        wb.close()


def _extract_image(file_path: Path) -> tuple[list[PageContent], bool, list[str]]:
    from PIL import Image

    try:
        with Image.open(file_path) as img:
            img.verify()
    except Exception as exc:
        raise ValueError(f"Invalid or corrupted image file: {exc}") from exc

    raw_bytes = file_path.read_bytes()
    text, ocr_info = extract_text_from_image(raw_bytes)
    warnings: list[str] = []

    if not ocr_info.get("success"):
        warnings.append(
            ocr_info.get("error", "OCR failed or is not available on this server.")
        )

    return [PageContent(page_number=1, text=text, char_count=len(text))], True, warnings


def extract_document(
    file_bytes: bytes,
    filename: str,
) -> ExtractionResult:
    """Extract text from supported document types with safe temporary storage and validation."""
    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    ocr_diagnostics = get_ocr_diagnostics()

    if ext not in SUPPORTED_EXTENSIONS:
        return ExtractionResult(
            filename=clean_name,
            file_type=ext.lstrip(".") or "unknown",
            file_size_bytes=len(file_bytes),
            page_count=0,
            full_text="",
            pages=[],
            ocr_used=False,
            ocr_status=ocr_diagnostics,
            status="failed",
            error=(
                f"Unsupported file format '{ext}'. Supported formats include PDF, DOCX, "
                "PPTX, TXT, Markdown, JSON, HTML, CSV, XLSX, and raster images."
            ),
        )

    if len(file_bytes) == 0:
        return ExtractionResult(
            filename=clean_name,
            file_type=ext.lstrip("."),
            file_size_bytes=0,
            page_count=0,
            full_text="",
            pages=[],
            ocr_used=False,
            ocr_status=ocr_diagnostics,
            status="empty",
            error="Uploaded file is empty (0 bytes).",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return ExtractionResult(
            filename=clean_name,
            file_type=ext.lstrip("."),
            file_size_bytes=len(file_bytes),
            page_count=0,
            full_text="",
            pages=[],
            ocr_used=False,
            ocr_status=ocr_diagnostics,
            status="failed",
            error=f"File size ({round(len(file_bytes) / 1024 / 1024, 2)} MB) exceeds maximum limit of 25 MB.",
        )

    # Create temporary file securely and clean up in finally block
    temp_dir = tempfile.gettempdir()
    temp_file = Path(temp_dir) / f"dpdp_upload_{os.urandom(8).hex()}{ext}"

    try:
        temp_file.write_bytes(file_bytes)

        if ext == ".pdf":
            pages, ocr_used, warnings = _extract_pdf(temp_file)
        elif ext == ".docx":
            pages, ocr_used, warnings = _extract_docx(temp_file)
        elif ext == ".txt":
            pages, ocr_used, warnings = _extract_txt(temp_file)
        elif ext == ".csv":
            pages, ocr_used, warnings = _extract_csv(temp_file)
        elif ext == ".xlsx":
            pages, ocr_used, warnings = _extract_xlsx(temp_file)
        elif ext == ".pptx":
            pages, ocr_used, warnings = _extract_pptx(temp_file)
        elif ext in {".md", ".markdown", ".json", ".html", ".htm"}:
            file_type = SUPPORTED_EXTENSIONS[ext]
            pages, ocr_used, warnings = _extract_text_format(temp_file, file_type)
        elif SUPPORTED_EXTENSIONS[ext] == "image":
            pages, ocr_used, warnings = _extract_image(temp_file)
        else:
            raise ValueError(f"Unsupported extension {ext}")

        full_text = "\n\n".join(p.text for p in pages if p.text).strip()
        page_dicts = [
            {"page_number": p.page_number, "text": p.text, "char_count": p.char_count}
            for p in pages
        ]

        status = "success" if full_text else "empty"
        if not full_text and not warnings:
            warnings.append("Document extracted with zero printable text.")

        return ExtractionResult(
            filename=clean_name,
            file_type=ext.lstrip("."),
            file_size_bytes=len(file_bytes),
            page_count=len(pages),
            full_text=full_text,
            pages=page_dicts,
            ocr_used=ocr_used,
            ocr_status=ocr_diagnostics,
            status=status,
            warnings=warnings,
            error=None,
        )

    except Exception as exc:
        _LOGGER.exception("Extraction error for %s", clean_name)
        return ExtractionResult(
            filename=clean_name,
            file_type=ext.lstrip("."),
            file_size_bytes=len(file_bytes),
            page_count=0,
            full_text="",
            pages=[],
            ocr_used=False,
            ocr_status=ocr_diagnostics,
            status="failed",
            error=str(exc),
        )
    finally:
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception as cleanup_err:
            _LOGGER.warning("Failed to remove temp file %s: %s", temp_file, cleanup_err)
