from __future__ import annotations

from fastapi.testclient import TestClient

from app.audit.logger import AuditStore
from app.config import Settings
from app.detection.india_recognizers import detect_india_patterns
from app.detection.ner_engine import NERMatch
from app.llm.base import LLMError, LLMProvider, LLMResult
from app.main import create_app
from app.services.gateway import Gateway


class StubProvider(LLMProvider):
    name = "openai"
    model = "test-model"

    def __init__(self, response: str = "Summary for <PERSON_1>.", fail: bool = False):
        self.response = response
        self.fail = fail
        self.payloads = []

    def build_payload(self, sanitized_text: str, task: str) -> dict:
        return {"messages": [{"role": "user", "content": sanitized_text}]}

    async def complete(self, serialized_payload: str) -> LLMResult:
        self.payloads.append(serialized_payload)
        if self.fail:
            raise LLMError("provider connection failed")
        return LLMResult(self.response, self.model)


def _client(tmp_path, provider=None, audit_api_key=""):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
        max_input_chars=100_000,
        audit_api_key=audit_api_key,
    )
    audit = AuditStore(settings.database_url)
    gateway = Gateway(settings, audit, {"openai": provider or StubProvider()})
    class TestDetector:
        def detect(self, text):
            names = ("Rahul Sharma", "Asha", "Ravi")
            entities = [
                NERMatch(item.entity_type, item.start, item.end, item.score, item.source)
                for item in detect_india_patterns(text)
            ]
            for name in names:
                start = 0
                while (index := text.find(name, start)) != -1:
                    entities.append(
                        NERMatch(
                            "PERSON", index, index + len(name), 0.99, "test"
                        )
                    )
                    start = index + len(name)
            return entities

        def status(self):
            return {
                "presidio": {
                    "state": "test",
                    "spacy_model": "test",
                    "error": None,
                    "india_regex_fallback": True,
                },
                "gliner": {
                    "state": "disabled",
                    "enabled": False,
                    "model": "test",
                    "error": None,
                },
            }

    gateway.detector = TestDetector()
    client = TestClient(create_app(settings, gateway))
    return client, gateway, provider


def test_process_masks_restores_and_audits_without_mapping(tmp_path):
    provider = StubProvider("Applicant <PERSON_1> was reviewed.")
    client, gateway, _ = _client(tmp_path, provider)
    response = client.post(
        "/api/process",
        json={"text": "Rahul Sharma applied for a loan.", "provider": "openai"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sanitized_text"] == "<PERSON_1> applied for a loan."
    assert body["final_response"] == "Applicant Rahul Sharma was reviewed."
    assert "mapping" not in body
    assert "Rahul Sharma" not in provider.payloads[0]
    audit = gateway.audit.get(body["request_id"])
    assert audit["leakage_verified"] is True
    assert "Rahul Sharma" not in audit["outbound_payload"]


def test_mask_reinsert_round_trip_keeps_mapping_server_side(tmp_path):
    client, _, _ = _client(tmp_path)
    masked = client.post("/api/mask", json={"text": "Asha is an applicant."})
    assert masked.status_code == 200
    body = masked.json()
    assert "mapping" not in body
    restored = client.post(
        "/api/reinsert",
        json={"request_id": body["request_id"], "text": "Applicant <PERSON_1>."},
    )
    assert restored.json()["final_response"] == "Applicant Asha."


def test_empty_input_is_rejected_and_detect_endpoint_accepts_empty(tmp_path):
    client, _, _ = _client(tmp_path)
    assert client.post("/api/process", json={"text": ""}).status_code == 422
    detected = client.post("/api/detect", json={"text": ""})
    assert detected.status_code == 200
    assert detected.json()["entities"] == []


def test_provider_failure_returns_clear_error_and_is_audited(tmp_path):
    provider = StubProvider(fail=True)
    client, gateway, _ = _client(tmp_path, provider)
    response = client.post("/api/process", json={"text": "Asha applied."})
    assert response.status_code == 502
    assert response.json()["detail"] == "provider connection failed"
    records = gateway.audit.list_recent()
    assert records[0]["status"] == "failed"


def test_real_provider_without_credentials_fails_without_fabricating_response(tmp_path):
    settings = Settings(
        openai_api_key="",
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
    )
    audit = AuditStore(settings.database_url)
    client = TestClient(create_app(settings, Gateway(settings, audit)))
    response = client.post("/api/process", json={"text": "No PII in this sentence."})
    assert response.status_code == 502
    assert response.json()["detail"] == "OPENAI_API_KEY is not configured."
    assert audit.list_recent()[0]["status"] == "failed"


def test_large_input_limit_is_enforced(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
        max_input_chars=8,
    )
    audit = AuditStore(settings.database_url)
    client = TestClient(create_app(settings, Gateway(settings, audit, {"openai": StubProvider()})))
    response = client.post("/api/detect", json={"text": "0123456789"})
    assert response.status_code == 413


def test_audit_endpoints_require_credentials(tmp_path):
    client, _, _ = _client(tmp_path)
    assert client.get("/api/audit").status_code == 503


def test_audit_endpoints_reject_bad_key_and_accept_configured_key(tmp_path):
    client, _, _ = _client(tmp_path, audit_api_key="test-audit-secret")
    assert client.get("/api/audit").status_code == 401
    assert (
        client.get(
            "/api/audit", headers={"Authorization": "Bearer incorrect"}
        ).status_code
        == 401
    )
    authorized = client.get(
        "/api/audit",
        headers={"Authorization": "Bearer test-audit-secret"},
    )
    assert authorized.status_code == 200


def test_detect_endpoint_reports_pan_offsets_without_raw_values(tmp_path):
    client, _, _ = _client(tmp_path)
    text = "PAN ABCPK1234F; invalid PAN ABCDP1234F."
    response = client.post("/api/detect", json={"text": text})
    assert response.status_code == 200
    entities = response.json()["entities"]
    pans = [entity for entity in entities if entity["type"] == "PAN"]
    assert len(pans) == 1
    assert text[pans[0]["start"] : pans[0]["end"]] == "ABCPK1234F"
    assert "ABCPK1234F" not in response.text


def test_api_process_masks_all_detected_raw_pii_before_provider_call(tmp_path):
    provider = StubProvider(
        "Applicant <PERSON_1> has <PAN_1> and <AADHAAR_1>."
    )
    client, gateway, _ = _client(tmp_path, provider)
    text = (
        "Rahul Sharma has PAN ABCPK1234F and Aadhaar 2345 6789 0123."
    )
    response = client.post(
        "/api/process", json={"text": text, "provider": "openai"}
    )
    assert response.status_code == 200
    outbound = provider.payloads[0]
    assert "Rahul Sharma" not in outbound
    assert "ABCPK1234F" not in outbound
    assert "2345 6789 0123" not in outbound
    body = response.json()
    assert body["sanitized_text"] == (
        "<PERSON_1> has PAN <PAN_1> and Aadhaar <AADHAAR_1>."
    )
    audit = gateway.audit.get(body["request_id"])
    assert "Rahul Sharma" not in audit["outbound_payload"]
    assert "ABCPK1234F" not in audit["outbound_payload"]
    assert "2345 6789 0123" not in audit["outbound_payload"]


def test_audit_detail_requires_auth_and_contains_no_original_pii(tmp_path):
    client, _, _ = _client(tmp_path, audit_api_key="audit-test-key")
    response = client.post(
        "/api/process",
        json={"text": "Rahul Sharma applied for a loan.", "provider": "openai"},
    )
    assert response.status_code == 200
    request_id = response.json()["request_id"]
    endpoint = f"/api/audit/{request_id}"
    assert client.get(endpoint).status_code == 401
    audit = client.get(
        endpoint,
        headers={"Authorization": "Bearer audit-test-key"},
    )
    assert audit.status_code == 200
    assert "Rahul Sharma" not in audit.text
    assert "mapping" not in audit.text


def test_unknown_provider_returns_client_error(tmp_path):
    client, _, _ = _client(tmp_path)
    response = client.post(
        "/api/process", json={"text": "No personal information.", "provider": "unknown"}
    )
    assert response.status_code == 400
    assert "Unsupported provider" in response.json()["detail"]


def test_guard_records_blocked_payload_without_persisting_raw_value(tmp_path):
    class LeakingProvider(StubProvider):
        def build_payload(self, sanitized_text: str, task: str) -> dict:
            return {"content": "leak: Rahul Sharma"}

    provider = LeakingProvider()
    client, gateway, _ = _client(tmp_path, provider)
    response = client.post("/api/process", json={"text": "Rahul Sharma applied."})
    assert response.status_code == 502
    record = gateway.audit.list_recent()[0]
    assert record["status"] == "blocked"
    assert record["outbound_payload"] is None
    assert provider.payloads == []


def test_health_exposes_detection_degradation(tmp_path):
    client, _, _ = _client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "gliner" in response.json()["detection"]


def test_openapi_documents_response_shapes_and_docs_page(tmp_path):
    client, _, _ = _client(tmp_path)
    docs = client.get("/docs")
    openapi = client.get("/openapi.json").json()
    assert docs.status_code == 200
    process_schema = openapi["paths"]["/api/process"]["post"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    assert process_schema["$ref"].endswith("/ProcessResponse")
    assert "restoration" in openapi["components"]["schemas"]["ProcessResponse"][
        "properties"
    ]


def test_reinsert_respects_configured_input_limit(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
        max_input_chars=8,
    )
    audit = AuditStore(settings.database_url)
    client = TestClient(
        create_app(settings, Gateway(settings, audit, {"openai": StubProvider()}))
    )
    response = client.post(
        "/api/reinsert",
        json={"request_id": "unknown", "text": "longer than configured"},
    )
    assert response.status_code == 413
