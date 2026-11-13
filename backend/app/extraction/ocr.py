from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Standard Windows installation paths for Tesseract OCR
_TESSERACT_CANDIDATE_PATHS = [
    os.getenv("TESSERACT_CMD", ""),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\User\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]


def find_tesseract_binary() -> str | None:
    """Find tesseract binary on the host system."""
    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd

    for candidate in _TESSERACT_CANDIDATE_PATHS:
        if candidate and Path(candidate).is_file():
            return str(candidate)

    return None


def find_tessdata_dir(tesseract_binary: str | None = None) -> Path | None:
    """Find the directory containing Tesseract .traineddata language packs.

    Checks:
    1. Project backend/data/tessdata (bundled / user-downloaded language packs)
    2. TESSDATA_PREFIX environment variable
    3. tessdata directory adjacent to tesseract executable
    4. Standard C:\\Program Files\\Tesseract-OCR\\tessdata
    """
    candidates: list[Path] = []

    # 1. Project local tessdata
    project_tessdata = Path(__file__).resolve().parent.parent.parent / "data" / "tessdata"
    candidates.append(project_tessdata)

    # 2. Environment variable
    env_tessdata = os.getenv("TESSDATA_PREFIX")
    if env_tessdata:
        candidates.append(Path(env_tessdata))

    # 3. Adjacent to binary
    if tesseract_binary:
        bin_tessdata = Path(tesseract_binary).parent / "tessdata"
        candidates.append(bin_tessdata)

    # 4. Standard path
    candidates.append(Path(r"C:\Program Files\Tesseract-OCR\tessdata"))

    # Return the directory that has the most traineddata files (favoring one with hin and kan)
    best_dir = None
    max_langs = 0
    for p in candidates:
        if p.is_dir():
            trained = list(p.glob("*.traineddata"))
            if len(trained) > max_langs:
                max_langs = len(trained)
                best_dir = p

    return best_dir


def get_ocr_diagnostics() -> dict[str, Any]:
    """Inspect OCR installation and available language packs."""
    binary = find_tesseract_binary()
    available = binary is not None
    installed_languages: list[str] = []
    missing_requirements: list[str] = []
    tessdata_dir = find_tessdata_dir(binary)

    if not available:
        missing_requirements.append("Tesseract OCR binary not found on system PATH.")
    else:
        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = binary
            if tessdata_dir:
                os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)

            langs = pytesseract.get_languages()
            installed_languages = sorted(langs)
        except Exception as exc:
            missing_requirements.append(f"Failed to query Tesseract languages: {exc}")

    # Check for English, Hindi, Kannada
    desired_languages = {"eng": "English", "hin": "Hindi", "kan": "Kannada"}
    missing_langs = [
        f"{name} ({code}.traineddata)"
        for code, name in desired_languages.items()
        if code not in installed_languages
    ]
    if missing_langs and available:
        missing_requirements.append(
            f"Missing OCR language packs: {', '.join(missing_langs)}"
        )

    setup_instructions = (
        "To enable local optical character recognition (OCR) for scanned PDFs and images:\n"
        "1. Download and install Tesseract OCR for Windows (e.g. from UB-Mannheim:\n"
        "   https://github.com/UB-Mannheim/tesseract/wiki or via winget: 'winget install UB-Mannheim.TesseractOCR').\n"
        "2. Place 'hin.traineddata' and 'kan.traineddata' in the 'data/tessdata' folder.\n"
        "3. Set TESSERACT_CMD in your .env if installed outside standard program files."
    )

    return {
        "available": available,
        "tesseract_path": binary,
        "tessdata_path": str(tessdata_dir) if tessdata_dir else None,
        "installed_languages": installed_languages,
        "supported_targets": ["eng", "hin", "kan"],
        "missing_requirements": missing_requirements,
        "setup_instructions": setup_instructions if missing_requirements else "OCR is fully configured with English, Hindi, and Kannada support.",
    }


def extract_text_from_image(
    image_bytes: bytes,
    preferred_languages: list[str] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Extract text from raw image bytes using Tesseract OCR if available.

    Never fabricates text if OCR is unavailable or fails.
    """
    diagnostics = diagnostics or get_ocr_diagnostics()
    if not diagnostics["available"]:
        return "", {
            "success": False,
            "error": "OCR engine (Tesseract) is not installed on this system.",
            "diagnostics": diagnostics,
        }

    try:
        import io
        from PIL import Image
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = diagnostics["tesseract_path"]
        tessdata_dir = diagnostics.get("tessdata_path")
        if tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)

        image = Image.open(io.BytesIO(image_bytes))

        # Select supported languages
        available_langs = set(diagnostics["installed_languages"])
        targets = preferred_languages or ["eng", "hin", "kan"]
        active_langs = [lang for lang in targets if lang in available_langs]
        if not active_langs and "eng" in available_langs:
            active_langs = ["eng"]

        lang_param = "+".join(active_langs) if active_langs else "eng"
        extracted = pytesseract.image_to_string(image, lang=lang_param)
        cleaned = extracted.strip()

        return cleaned, {
            "success": True,
            "languages_used": active_langs,
            "character_count": len(cleaned),
            "diagnostics": diagnostics,
        }
    except Exception as exc:
        _LOGGER.warning("Image OCR failed: %s", exc)
        return "", {
            "success": False,
            "error": f"OCR processing failed: {str(exc)}",
            "diagnostics": diagnostics,
        }
