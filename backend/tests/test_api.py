from __future__ import annotations

import asyncio
import json

from fastapi import HTTPException
import pytest
from fastapi.testclient import TestClient

from app.api.routes import analyze_document_endpoint
from app.audit.logger import AuditStore
from app.config import Settings
from app.extraction.extractor import MAX_FILE_SIZE_BYTES
from app.detection.india_recognizers import detect_india_patterns
from app.detection.ner_engine import NERMatch
from app.llm.base import LLMError, LLMProvider, LLMResult
from app.llm.provider import GroqProvider
from app.main import create_app
from app.services.gateway import Gateway


class StubProvider(LLMProvider):
    name = "groq"
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
        llm_provider="groq",
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
        max_input_chars=100_000,
        audit_api_key=audit_api_key,
    )
    audit = AuditStore(settings.database_url)
    gateway = Gateway(settings, audit, {"groq": provider or StubProvider()})
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
        json={"text": "Rahul Sharma applied for a loan.", "provider": "groq"},
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


def test_document_upload_uses_extractor_file_size_limit(tmp_path, monkeypatch):
    _, gateway, _ = _client(tmp_path)
    observed = {}

    async def record_upload_size(**kwargs):
        observed["size"] = len(kwargs["file_bytes"])
        raise HTTPException(status_code=418, detail="upload reached extraction")

    class FakeUpload:
        filename = "sample.pdf"

        async def read(self):
            return b"x" * 1_000_001

    class FakeRequest:
        headers = {"content-type": "multipart/form-data"}

        async def form(self):
            return {"file": FakeUpload(), "run_llm": "false"}

    monkeypatch.setattr(gateway, "analyze_file", record_upload_size)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            analyze_document_endpoint(FakeRequest(), gateway)
        )

    assert exc_info.value.status_code == 418
    assert observed["size"] == 1_000_001
    assert observed["size"] < MAX_FILE_SIZE_BYTES


def test_document_review_can_be_skipped_then_requested_without_raw_pii(tmp_path):
    class JsonProvider(StubProvider):
        async def complete(self, serialized_payload: str) -> LLMResult:
            self.payloads.append(serialized_payload)
            return LLMResult(
                json.dumps({
                    "summary": "The applicant submitted a loan application.",
                    "findings": [],
                }),
                self.model,
            )

    provider = JsonProvider()
    client, _, _ = _client(tmp_path, provider)
    text = "Asha submitted a loan application."

    extracted = client.post(
        "/api/documents/analyze",
        json={"text": text, "filename": "application.txt", "run_llm": False},
    )
    assert extracted.status_code == 200
    assert extracted.json()["llm_analysis"]["status"] == "skipped"
    assert provider.payloads == []

    reviewed = client.post(
        "/api/documents/analyze",
        json={"text": text, "filename": "application.txt", "run_llm": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["llm_analysis"]["status"] == "success"
    assert "Asha" not in provider.payloads[0]


def test_provider_failure_returns_clear_error_and_is_audited(tmp_path):
    provider = StubProvider(fail=True)
    client, gateway, _ = _client(tmp_path, provider)
    response = client.post("/api/process", json={"text": "Asha applied."})
    assert response.status_code == 502
    assert response.json()["detail"] == "provider connection failed"
    records = gateway.audit.list_recent()
    assert records[0]["status"] == "failed"


def test_groq_provider_without_credentials_fails_without_fabricating_response(tmp_path):
    settings = Settings(
        llm_provider="groq",
        groq_api_key="",
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
    )
    audit = AuditStore(settings.database_url)
    client = TestClient(create_app(settings, Gateway(settings, audit)))
    response = client.post("/api/process", json={"text": "No PII in this sentence."})
    assert response.status_code == 502
    assert response.json()["detail"] == "GROQ_API_KEY is not configured."
    assert audit.list_recent()[0]["status"] == "failed"


def test_groq_provider_builds_model_request_without_network(monkeypatch):
    settings = Settings(
        groq_api_key="test-key-never-sent",
        groq_model="openai/gpt-oss-20b",
    )
    provider = GroqProvider(settings)
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "openai/gpt-oss-20b",
                "choices": [{"message": {"content": "Processed <PERSON_1>."}}],
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            captured.update(url=url, content=content, headers=headers)
            return FakeResponse()

    monkeypatch.setattr("app.llm.provider.httpx.AsyncClient", FakeAsyncClient)

    import asyncio

    payload = provider.build_payload("<PERSON_1> applied.", "summarize")
    result = asyncio.run(provider.complete(json.dumps(payload)))
    assert provider.name == "groq"
    assert payload["model"] == "openai/gpt-oss-20b"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key-never-sent"
    assert b"<PERSON_1>" in captured["content"]
    assert result.text == "Processed <PERSON_1>."


def test_groq_is_default_provider_and_reports_missing_key(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
        groq_api_key="",
    )
    audit = AuditStore(settings.database_url)
    gateway = Gateway(settings, audit)
    client = TestClient(create_app(settings, gateway))
    response = client.post(
        "/api/process", json={"text": "No personal information."}
    )
    assert gateway.settings.llm_provider == "groq"
    assert gateway.providers["groq"].model == "openai/gpt-oss-20b"
    assert response.status_code == 502
    assert response.json()["detail"] == "GROQ_API_KEY is not configured."


def test_groq_provider_reports_missing_key_by_environment_variable_name():
    provider = GroqProvider(Settings(groq_api_key=""))
    import asyncio

    try:
        asyncio.run(provider.complete("{}"))
    except LLMError as exc:
        assert str(exc) == "GROQ_API_KEY is not configured."
    else:
        raise AssertionError("Expected missing Groq API key to fail")


def test_groq_provider_logs_safe_http_failure_diagnostics(monkeypatch, caplog):
    import asyncio

    import httpx

    secret = "gsk_sensitive_test_value"
    personal_data = "Fictional Person"
    provider = GroqProvider(Settings(groq_api_key=secret))

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            request = httpx.Request("POST", url)
            response = httpx.Response(
                401,
                request=request,
                text=f"Rejected {secret} while processing {personal_data}",
            )
            response.raise_for_status()

    monkeypatch.setattr("app.llm.provider.httpx.AsyncClient", FakeAsyncClient)

    try:
        asyncio.run(provider.complete("{}"))
    except LLMError as exc:
        assert str(exc) == "provider returned HTTP 401"
    else:
        raise AssertionError("Expected an HTTP provider failure")

    assert "HTTPStatusError" in caplog.text
    assert "provider returned HTTP 401" in caplog.text
    assert secret not in caplog.text
    assert personal_data not in caplog.text


def test_groq_provider_logs_only_allowlisted_http_400_details(monkeypatch, caplog):
    import asyncio

    import httpx

    secret = "gsk_sensitive_test_value"
    personal_data = "Fictional Person"
    provider = GroqProvider(Settings(groq_api_key=secret))

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            request = httpx.Request("POST", url)
            response = httpx.Response(
                400,
                request=request,
                json={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "unsupported_value",
                        "param": "temperature",
                        "message": f"Rejected {secret} while processing {personal_data}",
                    }
                },
            )
            response.raise_for_status()

    monkeypatch.setattr("app.llm.provider.httpx.AsyncClient", FakeAsyncClient)

    try:
        asyncio.run(provider.complete("{}"))
    except LLMError as exc:
        assert str(exc) == "provider returned HTTP 400"
    else:
        raise AssertionError("Expected an HTTP provider failure")

    assert "code=unsupported_value" in caplog.text
    assert "param=temperature" in caplog.text
    assert "type=invalid_request_error" in caplog.text
    assert secret not in caplog.text
    assert personal_data not in caplog.text


def test_groq_provider_retries_json_validation_error_once(monkeypatch, caplog):
    import asyncio

    import httpx

    provider = GroqProvider(Settings(groq_api_key="test-key-never-sent"))
    calls = 0

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            nonlocal calls
            calls += 1
            request = httpx.Request("POST", url)
            if calls == 1:
                return httpx.Response(
                    400,
                    request=request,
                    json={"error": {"code": "json_validate_failed"}},
                )
            return httpx.Response(
                200,
                request=request,
                json={
                    "model": provider.model,
                    "choices": [{"message": {"content": "Review completed."}}],
                },
            )

    monkeypatch.setattr("app.llm.provider.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(provider.complete('{"messages":[]}'))

    assert calls == 2
    assert result.text == "Review completed."
    assert "retrying the sanitized request once" in caplog.text


def test_groq_provider_retries_rate_limit_after_retry_after(monkeypatch, caplog):
    import asyncio

    import httpx

    provider = GroqProvider(
        Settings(
            groq_api_key="test-key-never-sent",
            groq_max_rate_limit_retries=1,
        )
    )
    calls = 0
    waits = []

    async def fake_sleep(delay):
        waits.append(delay)

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            nonlocal calls
            calls += 1
            request = httpx.Request("POST", url)
            if calls == 1:
                return httpx.Response(
                    429,
                    request=request,
                    headers={"retry-after": "0.25"},
                )
            return httpx.Response(
                200,
                request=request,
                json={
                    "model": provider.model,
                    "choices": [{"message": {"content": "Review completed."}}],
                },
            )

    monkeypatch.setattr("app.llm.provider.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("app.llm.provider.asyncio.sleep", fake_sleep)

    result = asyncio.run(provider.complete('{"messages":[]}'))

    assert calls == 2
    assert waits == [0.25]
    assert result.text == "Review completed."
    assert "Groq rate limit reached" in caplog.text


def test_groq_provider_cools_down_after_rate_limit(monkeypatch):
    import asyncio

    import httpx
    import pytest

    provider = GroqProvider(
        Settings(
            groq_api_key="test-key-never-sent",
            groq_max_rate_limit_retries=0,
        )
    )
    calls = 0

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            nonlocal calls
            calls += 1
            return httpx.Response(
                429,
                request=httpx.Request("POST", url),
                headers={"retry-after": "5"},
            )

    monkeypatch.setattr("app.llm.provider.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(LLMError, match="rate-limiting"):
        asyncio.run(provider.complete('{"messages":[]}'))
    with pytest.raises(LLMError, match="about 5 seconds"):
        asyncio.run(provider.complete('{"messages":[]}'))
    assert calls == 1


def test_large_input_limit_is_enforced(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'audit.db'}",
        enable_gliner=False,
        max_input_chars=8,
    )
    audit = AuditStore(settings.database_url)
    client = TestClient(create_app(settings, Gateway(settings, audit, {"groq": StubProvider()})))
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
        "/api/process", json={"text": text, "provider": "groq"}
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
        json={"text": "Rahul Sharma applied for a loan.", "provider": "groq"},
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
        create_app(settings, Gateway(settings, audit, {"groq": StubProvider()}))
    )
    response = client.post(
        "/api/reinsert",
        json={"request_id": "unknown", "text": "longer than configured"},
    )
    assert response.status_code == 413
