import io
import json
import pytest
import fitz
import docx
import openpyxl
from PIL import Image
from fastapi.testclient import TestClient

from app.audit.logger import AuditStore
from app.config import Settings
from app.extraction.ocr import get_ocr_diagnostics
from app.main import create_app
from app.services.gateway import Gateway


from dataclasses import replace

@pytest.fixture(scope="module")
def app_client(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("audit_e2e")
    db_path = tmp_path / "audit_integration.db"
    settings = replace(Settings.from_env(), database_url=f"sqlite:///{db_path}")
    audit = AuditStore(settings.database_url)
    audit.initialize()
    gw = Gateway(settings, audit)
    app = create_app(settings, gw)
    with TestClient(app) as client:
        yield client, gw


def test_1_health_and_ocr_status(app_client):
    client, gw = app_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    ocr_resp = client.get("/api/ocr/status")
    assert ocr_resp.status_code == 200
    ocr_data = ocr_resp.json()
    assert "available" in ocr_data
    assert "supported_targets" in ocr_data
    print("\n[AUDIT] OCR Status on host:", ocr_data["available"])
    print("[AUDIT] OCR Missing Requirements:", ocr_data.get("missing_requirements"))


def test_2_legacy_api_process_endpoint(app_client):
    client, gw = app_client
    # Original Privacy Gateway test
    payload = {
        "text": "Applicant Rajesh Verma with phone 9876543210 and PAN ABCPK1234F requested loan approval.",
        "task": "summarize",
        "provider": "configured_provider",
    }
    resp = client.post("/api/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "<PERSON_" in data["sanitized_text"]
    assert "Rajesh Verma" not in data["sanitized_text"]
    assert "final_response" in data
    assert data["leakage_detected"] is False
    print("\n[AUDIT] Legacy /api/process verified: status = success, leakage_detected = False")


def test_3_documents_analyze_with_pdf(app_client):
    client, gw = app_client
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Loan Application Dossier\nApplicant: Vikram Seth\nPhone: 9876543210\nPAN: ABCPK1234F")
    pdf_bytes = doc.tobytes()
    doc.close()

    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("application.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["file_type"] == "pdf"
    assert data["page_count"] == 1
    assert "Vikram Seth" in data["extracted_text"]
    assert "<PERSON_" in data["sanitized_text"]
    assert "Vikram Seth" not in data["sanitized_text"]


def test_4_documents_analyze_with_docx(app_client):
    client, gw = app_client
    d = docx.Document()
    d.add_heading("Employment Verification", level=1)
    d.add_paragraph("Employee: Sunita Narain")
    d.add_paragraph("PAN: BZRPK5678Q")
    d.add_paragraph("Contact: 9123456780")
    buf = io.BytesIO()
    d.save(buf)
    docx_bytes = buf.getvalue()

    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("employment.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["file_type"] == "docx"
    assert "Sunita Narain" in data["extracted_text"]
    assert "<PERSON_" in data["sanitized_text"]
    assert "Sunita Narain" not in data["sanitized_text"]


def test_5_documents_analyze_with_txt(app_client):
    client, gw = app_client
    txt_content = "Customer Record: Ananya Deshmukh, Phone: 9811223344, Email: ananya@example.com, PAN: CDEPK9988Z"
    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("customer.txt", txt_content.encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["file_type"] == "txt"
    assert "<EMAIL_ADDRESS_" in data["sanitized_text"] or "<EMAIL_" in data["sanitized_text"]
    assert "ananya@example.com" not in data["sanitized_text"]


def test_6_documents_analyze_with_csv(app_client):
    client, gw = app_client
    csv_content = "Name,Phone,PAN\nHarish Rao,9876543210,ABCPK1234F\nMeera Nair,9123456789,XYZPK4321D\n"
    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("data.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["file_type"] == "csv"
    assert "Harish Rao" in data["extracted_text"]
    assert "Harish Rao" not in data["sanitized_text"]


def test_7_documents_analyze_with_xlsx(app_client):
    client, gw = app_client
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "KYC"
    ws.append(["Name", "Contact", "PAN"])
    ws.append(["Deepak Chopra", "9876543210", "ABCPK1234F"])
    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("accounts.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["file_type"] == "xlsx"
    assert "Deepak Chopra" in data["extracted_text"]
    assert "Deepak Chopra" not in data["sanitized_text"]


def test_8_documents_analyze_with_image_png(app_client):
    client, gw = app_client
    from PIL import ImageDraw
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "KYC Document\nName: Rahul Sharma\nPAN: ABCPK1234F\nPhone: 9876543210", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("scanned_id.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "png"
    assert data["status"] == "success"
    assert data["ocr_used"] is True
    # Verify OCR text was extracted, and then PII masked before any LLM handling
    assert "<PERSON_" in data["sanitized_text"] or "<PAN_" in data["sanitized_text"] or "<PHONE_" in data["sanitized_text"]
    assert "ABCPK1234F" not in data["sanitized_text"]

def test_9_multilingual_english_hindi_kannada_mixed(app_client):
    client, gw = app_client

    # Hindi
    hindi_doc = "ऋण आवेदन पत्र: आवेदक राहुल शर्मा, पैन संख्या ABCPK1234F, संपर्क दूरभाष 9876543210, पता: 45 कनाट प्लेस, नई दिल्ली।"
    resp_hi = client.post("/api/documents/analyze", json={"text": hindi_doc, "filename": "hindi.txt"})
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    assert "Hindi" in data_hi["detected_languages"]
    assert "Hindi" in data_hi["primary_language"]

    # Kannada
    kannada_doc = "ಸಾಲದ ಅರ್ಜಿ: ಅರ್ಜಿದಾರ ಆನಂದ್ ಕುಮಾರ್, ಪ್ಯಾನ್ ABCPK1234F, ದೂರವಾಣಿ 9876543210, ವಿಳಾಸ: 12 ಎಂಜಿ ರಸ್ತೆ, ಬೆಂಗಳೂರು 560001."
    resp_kn = client.post("/api/documents/analyze", json={"text": kannada_doc, "filename": "kannada.txt"})
    assert resp_kn.status_code == 200
    data_kn = resp_kn.json()
    assert "Kannada" in data_kn["detected_languages"]
    assert "Kannada" in data_kn["primary_language"]

    # Mixed Code-switched (Hinglish / Kanglish)
    mixed_doc = "Customer grievance ticket. Namma customer Anand Kumar ge housing loan approve aagide. Kripya applicant PAN ABCPK1234F dastavej verify karein."
    resp_mix = client.post("/api/documents/analyze", json={"text": mixed_doc, "filename": "mixed.txt"})
    assert resp_mix.status_code == 200
    data_mix = resp_mix.json()
    assert data_mix["is_mixed_language"] is True


def test_10_invalid_phone_email_pan_dates_validation(app_client):
    client, gw = app_client
    invalid_text = (
        "Loan Application Form.\n"
        "Applicant: Ramesh Gupta\n"
        "Phone: 1234567890\n"  # Invalid Indian mobile prefix (starts with 1)
        "Email: ramesh@invalid\n"  # Missing domain/TLD
        "PAN: ABC12345\n"  # Invalid PAN length and structure
        "Date of Birth: 31/02/1990\n"  # Impossible date (Feb 31)
        "Loan Sanction Date: 15/08/2045\n"  # Inconsistent future loan date
        "Declared Income: INR 50000\n"
        "Proposed EMI: INR 85000\n"  # Contradictory: EMI > Income
    )
    resp = client.post("/api/documents/analyze", json={"text": invalid_text, "filename": "invalid_test.txt"})
    assert resp.status_code == 200
    data = resp.json()
    summary = data["validation_summary"]
    categories = {f["category"] for f in data["validation_findings"]}
    severities = {f["severity"] for f in data["validation_findings"]}

    assert summary["errors"] >= 2, f"Expected errors for invalid phone and PAN, got {summary}"
    assert "PHONE" in categories
    assert "PAN" in categories or "EMAIL" in categories or "DATES" in categories
    assert "ERROR" in severities
    assert data["overall_risk"] in ("medium", "high")


def test_11_audit_records_and_metrics_consistency(app_client):
    client, gw = app_client
    metrics_resp = client.get("/api/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_requests"] >= 1
    assert "leakage_blocked" in metrics
    assert "pii_by_category" in metrics
    assert "risk_distribution" in metrics
    print("\n[AUDIT] /api/metrics successfully verified with live DB aggregations.")


def test_12_scanned_pdf_ocr_and_pii_masking(app_client):
    client, gw = app_client
    from PIL import ImageDraw
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Loan Document\nBorrower: Priya Nair\nPAN: ABCPK1234F\nContact: 9876543210", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=600, height=150)
    page.insert_image(page.rect, stream=png_bytes)
    scanned_pdf_bytes = doc.tobytes()
    doc.close()

    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("scanned_loan_app.pdf", scanned_pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["ocr_used"] is True
    # Verify PII is masked before reaching any LLM
    assert "<PERSON_" in data["sanitized_text"] or "<PAN_" in data["sanitized_text"] or "<PHONE_" in data["sanitized_text"]
    assert "ABCPK1234F" not in data["sanitized_text"]
