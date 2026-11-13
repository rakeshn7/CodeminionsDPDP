import io
import zipfile
import fitz  # PyMuPDF
import docx
import openpyxl
from PIL import Image

from app.extraction.extractor import extract_document
from app.extraction.ocr import get_ocr_diagnostics


def test_txt_extraction():
    content = "Hello, this is a plain text test.\nSecond line with Hindi: नमस्ते दुनिया."
    result = extract_document(content.encode("utf-8"), "sample.txt")
    assert result.status == "success"
    assert "Hello, this is a plain text test." in result.full_text
    assert "नमस्ते दुनिया." in result.full_text
    assert result.page_count == 1
    assert result.file_type == "txt"


def test_txt_latin1_fallback():
    latin_bytes = "Café au lait with accent \xe9".encode("latin-1")
    result = extract_document(latin_bytes, "french.txt")
    assert result.status == "success"
    assert "Café" in result.full_text or "accent" in result.full_text


def test_csv_extraction():
    csv_data = "Name,Phone,City\nRajesh Kumar,9876543210,Bengaluru\nPriya Sharma,9123456789,Delhi\n"
    result = extract_document(csv_data.encode("utf-8"), "data.csv")
    assert result.status == "success"
    assert "Rajesh Kumar" in result.full_text
    assert "9876543210" in result.full_text
    assert "Bengaluru" in result.full_text
    assert result.file_type == "csv"


def test_xlsx_extraction():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Applicants"
    ws.append(["ID", "Name", "Score"])
    ws.append([101, "Vikram Malhotra", 95.5])
    ws.append([102, "Sunita Rao", 88.0])

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    result = extract_document(xlsx_bytes, "applicants.xlsx")
    assert result.status == "success"
    assert "Applicants" in result.full_text
    assert "Vikram Malhotra" in result.full_text
    assert "Sunita Rao" in result.full_text
    assert result.file_type == "xlsx"


def test_docx_extraction():
    doc = docx.Document()
    doc.add_heading("KYC Application Form", level=1)
    doc.add_paragraph("Applicant Name: Suresh Raina")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Field"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "PAN"
    table.cell(1, 1).text = "ABCDE1234F"

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    result = extract_document(docx_bytes, "application.docx")
    assert result.status == "success"
    assert "KYC Application Form" in result.full_text
    assert "Suresh Raina" in result.full_text
    assert "ABCDE1234F" in result.full_text
    assert result.file_type == "docx"


def test_docx_extracts_header_and_footer_text():
    doc = docx.Document()
    doc.add_paragraph("Main body content")
    doc.sections[0].header.paragraphs[0].text = "Synthetic header"
    doc.sections[0].footer.paragraphs[0].text = "Synthetic footer"

    buf = io.BytesIO()
    doc.save(buf)
    result = extract_document(buf.getvalue(), "header-footer.docx")

    assert result.status == "success"
    assert "Synthetic header" in result.full_text
    assert "Synthetic footer" in result.full_text


def test_pptx_extracts_slide_text_and_reports_embedded_image_text_limit():
    slide_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
           xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <p:cSld><p:spTree><a:p><a:r><a:t>Synthetic slide content</a:t></a:r></a:p></p:spTree></p:cSld>
    </p:sld>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_xml)
        archive.writestr("ppt/media/image1.png", b"not-an-image")

    result = extract_document(buf.getvalue(), "slides.pptx")

    assert result.status == "success"
    assert result.page_count == 1
    assert "Synthetic slide content" in result.full_text
    assert any("embedded images" in warning for warning in result.warnings)


def test_json_and_html_extraction_preserve_text_and_ignore_scripts():
    json_result = extract_document(
        b'{"applicant":"Synthetic User","language":"\xe0\xa4\xb9\xe0\xa4\xbf\xe0\xa4\xa8\xe0\xa5\x8d\xe0\xa4\xa6\xe0\xa5\x80"}',
        "application.json",
    )
    html_result = extract_document(
        b"<h1>Review</h1><p>Synthetic content</p><script>hidden secret</script>",
        "application.html",
    )

    assert json_result.status == "success"
    assert "Synthetic User" in json_result.full_text
    assert "हिन्दी" in json_result.full_text
    assert html_result.status == "success"
    assert "Synthetic content" in html_result.full_text
    assert "hidden secret" not in html_result.full_text


def test_pdf_extraction():
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Page 1: Customer Profile for DPDP Gateway")
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Page 2: Aadhaar Number 9876 5432 1098")

    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_document(pdf_bytes, "customer.pdf")
    assert result.status == "success"
    assert result.page_count == 2
    assert "Page 1: Customer Profile" in result.full_text
    assert "Page 2: Aadhaar Number" in result.full_text
    assert len(result.pages) == 2
    assert result.pages[0]["page_number"] == 1
    assert result.pages[1]["page_number"] == 2


def test_encrypted_pdf_handling():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Secret Confidential Data")

    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
        | fitz.PDF_PERM_ANNOTATE
    )
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="ownerpass",
        user_pw="userpass",
        permissions=perm,
    )
    doc.close()

    result = extract_document(pdf_bytes, "encrypted.pdf")
    assert result.status == "failed"
    assert "encrypted" in result.error.lower() or "password" in result.error.lower()


def test_empty_file_detection():
    result = extract_document(b"", "empty.txt")
    assert result.status == "empty"
    assert "empty" in result.error.lower()


def test_unsupported_file_extension():
    result = extract_document(b"binary content", "program.exe")
    assert result.status == "failed"
    assert "unsupported" in result.error.lower()


def test_corrupt_docx():
    result = extract_document(b"not a valid zip/docx file", "bad.docx")
    assert result.status == "failed"
    assert "failed" in result.error.lower() or "corrupt" in result.error.lower() or "bad" in result.error.lower()


def test_corrupt_pdf():
    result = extract_document(b"not a valid pdf file", "bad.pdf")
    assert result.status == "failed"


def test_image_handling_when_ocr_unavailable_or_available():
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    result = extract_document(png_bytes, "sample.png")
    diag = get_ocr_diagnostics()
    if not diag["available"]:
        assert result.status in ("empty", "failed")
        assert any("tesseract" in w.lower() or "ocr" in w.lower() for w in result.warnings) or "ocr" in (result.error or "").lower()
    else:
        assert result.file_type in ("png", "image")


def test_real_image_ocr_with_text():
    from PIL import ImageDraw
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Applicant: Rajesh Kumar\nPAN: ABCPK1234F\nPhone: 9876543210", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    result = extract_document(png_bytes, "id_card.png")
    diag = get_ocr_diagnostics()
    if diag["available"]:
        assert result.status == "success"
        assert result.ocr_used is True
        assert "Rajesh" in result.full_text or "ABCPK1234F" in result.full_text or "987" in result.full_text


def test_real_scanned_pdf_ocr():
    from PIL import ImageDraw
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Scanned Contract\nBorrower: Priya Sharma\nPhone: 9876543210", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=600, height=150)
    page.insert_image(page.rect, stream=png_bytes)
    scanned_bytes = doc.tobytes()
    doc.close()

    result = extract_document(scanned_bytes, "scanned_loan.pdf")
    diag = get_ocr_diagnostics()
    if diag["available"]:
        assert result.status == "success"
        assert result.ocr_used is True
        assert "Priya" in result.full_text or "Sharma" in result.full_text or "987" in result.full_text


def test_mixed_pdf_ocr_reads_scanned_page_even_when_another_page_has_text(monkeypatch):
    image = Image.new("RGB", (200, 80), color=(255, 255, 255))
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")

    doc = fitz.open()
    text_page = doc.new_page()
    text_page.insert_text((40, 50), "Selectable page content")
    scanned_page = doc.new_page()
    scanned_page.insert_image(scanned_page.rect, stream=image_buffer.getvalue())
    pdf_bytes = doc.tobytes()
    doc.close()

    monkeypatch.setattr(
        "app.extraction.extractor.get_ocr_diagnostics",
        lambda: {"available": True, "installed_languages": ["eng", "hin", "kan"]},
    )
    monkeypatch.setattr(
        "app.extraction.extractor.extract_text_from_image",
        lambda _bytes, diagnostics=None: (
            "OCR page content",
            {"success": True, "languages_used": ["eng"]},
        ),
    )

    result = extract_document(pdf_bytes, "mixed-pages.pdf")

    assert result.status == "success"
    assert result.ocr_used is True
    assert "Selectable page content" in result.pages[0]["text"]
    assert "OCR page content" in result.pages[1]["text"]
    assert len(result.pages) == 2

    monkeypatch.setattr(
        "app.extraction.extractor.get_ocr_diagnostics",
        lambda: {"available": False, "installed_languages": []},
    )
    unavailable_result = extract_document(pdf_bytes, "mixed-pages.pdf")
    assert unavailable_result.status == "success"
    assert any("some text on that page may not be analyzed" in warning for warning in unavailable_result.warnings)
