from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile

from app.extraction.extractor import MAX_FILE_SIZE_BYTES
from app.extraction.ocr import get_ocr_diagnostics
from app.llm.base import LLMError
from app.schemas.request_response import (
    AuditListResponse,
    AuditResponse,
    DetectResponse,
    DocumentAnalyzeResponse,
    GatewayRequest,
    HealthResponse,
    MaskResponse,
    MetricsResponse,
    ProcessResponse,
    ReinsertRequest,
    ReinsertResultResponse,
    TextRequest,
)
from app.services.gateway import Gateway, PrivacyLeakError

router = APIRouter()


def get_gateway(request: Request) -> Gateway:
    return request.app.state.gateway


async def require_audit_access(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    expected = request.app.state.settings.audit_api_key
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Audit access is disabled until AUDIT_API_KEY is configured.",
        )
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid audit credentials.")


@router.post("/api/process", response_model=ProcessResponse)
async def process(
    body: GatewayRequest, gateway: Gateway = Depends(get_gateway)
) -> ProcessResponse:
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    if len(body.text) > gateway.settings.max_input_chars:
        raise HTTPException(status_code=413, detail="text exceeds configured input limit")
    try:
        return await gateway.process(body.text, body.task, body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrivacyLeakError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/detect", response_model=DetectResponse, response_model_exclude_none=True)
async def detect(
    body: TextRequest, gateway: Gateway = Depends(get_gateway)
) -> DetectResponse:
    if len(body.text) > gateway.settings.max_input_chars:
        raise HTTPException(status_code=413, detail="text exceeds configured input limit")
    _, entities = gateway.detect(body.text)
    return {
        "entities": entities,
        "detection_status": gateway.detection_status(),
    }


@router.post("/api/mask", response_model=MaskResponse)
async def mask(
    body: TextRequest, gateway: Gateway = Depends(get_gateway)
) -> MaskResponse:
    if len(body.text) > gateway.settings.max_input_chars:
        raise HTTPException(status_code=413, detail="text exceeds configured input limit")
    return gateway.mask(body.text)


@router.post("/api/reinsert", response_model=ReinsertResultResponse)
async def reinsert(
    body: ReinsertRequest, gateway: Gateway = Depends(get_gateway)
) -> ReinsertResultResponse:
    if len(body.text) > gateway.settings.max_input_chars:
        raise HTTPException(status_code=413, detail="text exceeds configured input limit")
    result = gateway.reinsert(body.request_id, body.text)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Request mapping not found or expired."
        )
    return result


@router.get(
    "/api/audit/{request_id}",
    response_model=AuditResponse,
    dependencies=[Depends(require_audit_access)],
)
async def get_audit(
    request_id: str, gateway: Gateway = Depends(get_gateway)
) -> AuditResponse:
    record = gateway.audit.get(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit record not found.")
    return record


@router.get(
    "/api/audit",
    response_model=AuditListResponse,
    dependencies=[Depends(require_audit_access)],
)
async def list_audit(
    gateway: Gateway = Depends(get_gateway),
    limit: int = Query(default=50, ge=1, le=200),
) -> AuditListResponse:
    return {"records": gateway.audit.list_recent(limit)}


@router.get("/api/metrics", response_model=MetricsResponse)
async def metrics(gateway: Gateway = Depends(get_gateway)) -> MetricsResponse:
    return gateway.audit.metrics()


@router.post("/api/documents/analyze", response_model=DocumentAnalyzeResponse)
async def analyze_document_endpoint(
    request: Request,
    gateway: Gateway = Depends(get_gateway),
) -> DocumentAnalyzeResponse:
    content_type = request.headers.get("content-type", "")

    # Handle multipart/form-data (file upload or form fields)
    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        text_field = form.get("text")
        provider_name = form.get("provider") or "configured_provider"
        run_llm_val = form.get("run_llm")
        run_llm = True if run_llm_val is None else str(run_llm_val).lower() in {"1", "true", "yes"}

        if uploaded_file and hasattr(uploaded_file, "read"):
            file_bytes = await uploaded_file.read()
            filename = getattr(uploaded_file, "filename", "uploaded_document") or "uploaded_document"
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Uploaded file exceeds server size limits.")
            return await gateway.analyze_file(
                file_bytes=file_bytes,
                filename=filename,
                provider_name=str(provider_name),
                run_llm=run_llm,
            )

        if text_field and isinstance(text_field, str):
            if len(text_field) > gateway.settings.max_input_chars:
                raise HTTPException(status_code=413, detail="text exceeds configured input limit.")
            return await gateway.analyze_document(
                text=text_field,
                filename=str(form.get("filename") or "document.txt"),
                file_type="txt",
                file_size_bytes=len(text_field.encode("utf-8")),
                provider_name=str(provider_name),
                run_llm=run_llm,
            )

        raise HTTPException(
            status_code=422,
            detail="Either a 'file' upload or 'text' content must be provided.",
        )

    # Handle application/json
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid request body.") from exc

    raw_text = str(body.get("text", "")).strip()
    if not raw_text:
        raise HTTPException(status_code=422, detail="Document text must not be empty.")
    if len(raw_text) > gateway.settings.max_input_chars:
        raise HTTPException(status_code=413, detail="text exceeds configured input limit.")

    filename = str(body.get("filename", "document.txt"))
    provider = body.get("provider") or "configured_provider"
    run_llm = bool(body.get("run_llm", True))

    return await gateway.analyze_document(
        text=raw_text,
        filename=filename,
        file_type="txt",
        file_size_bytes=len(raw_text.encode("utf-8")),
        provider_name=provider,
        run_llm=run_llm,
    )


@router.get("/api/ocr/status")
async def ocr_status_endpoint() -> dict:
    return get_ocr_diagnostics()


@router.get("/health", response_model=HealthResponse)
async def health(gateway: Gateway = Depends(get_gateway)) -> HealthResponse:
    return {"status": "ok", "detection": gateway.detection_status()}
