from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile

from app.extraction.extractor import MAX_FILE_SIZE_BYTES
from app.extraction.ocr import get_ocr_diagnostics
from app.llm.base import LLMError
from app.privacy.token_manager import BatchTokenRegistry
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
MAX_BATCH_FILES = 10
MAX_BATCH_REQUEST_BYTES = 100 * 1024 * 1024


async def _read_limited_upload(upload: UploadFile, limit: int) -> bytes:
    parts = []
    total = 0
    while chunk := await upload.read(min(1024 * 1024, limit + 1 - total)):
        total += len(chunk)
        if total > limit:
            raise ValueError("File exceeds the 25 MB per-file limit.")
        parts.append(chunk)
    return b"".join(parts)


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


@router.post("/api/documents/analyze-batch")
async def analyze_document_batch_endpoint(
    request: Request,
    gateway: Gateway = Depends(get_gateway),
) -> dict:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_BATCH_REQUEST_BYTES + 1024 * 1024:
        raise HTTPException(status_code=413, detail="Batch request exceeds the 100 MB total limit.")

    try:
        form = await request.form(
            max_files=MAX_BATCH_FILES + 1,
            max_fields=4,
            max_part_size=MAX_FILE_SIZE_BYTES,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid multipart upload.") from exc

    try:
        uploads = [
            item
            for item in form.getlist("files")
            if hasattr(item, "read") and hasattr(item, "filename")
        ]
        if not uploads:
            raise HTTPException(status_code=422, detail="Provide at least one file in the 'files' field.")
        if len(uploads) > MAX_BATCH_FILES:
            raise HTTPException(status_code=413, detail=f"A batch may contain at most {MAX_BATCH_FILES} files.")

        provider_name = str(form.get("provider") or "configured_provider")
        run_llm_value = form.get("run_llm")
        run_llm = True if run_llm_value is None else str(run_llm_value).lower() in {"1", "true", "yes"}
        registry = BatchTokenRegistry()
        results = []
        total_bytes = 0
        try:
            for upload in uploads:
                filename = upload.filename or "uploaded_document"
                document_id = str(uuid.uuid4())
                try:
                    file_bytes = await _read_limited_upload(
                        upload, MAX_FILE_SIZE_BYTES
                    )
                    total_bytes += len(file_bytes)
                    if total_bytes > MAX_BATCH_REQUEST_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail="Batch files exceed the 100 MB total limit.",
                        )
                    analysis = await gateway.analyze_file(
                        file_bytes=file_bytes,
                        filename=filename,
                        provider_name=provider_name,
                        run_llm=run_llm,
                        token_registry=registry,
                    )
                    if analysis.get("status") != "success":
                        error = analysis.get("error") or ""
                        safe_error = (
                            error
                            if error.startswith("Unsupported file format")
                            or error.startswith("Uploaded file is empty")
                            or error.startswith("File size (")
                            else "Document extraction failed. Verify that the file is valid and readable."
                        )
                        results.append({
                            "document_id": document_id,
                            "filename": analysis.get("filename", filename),
                            "status": "error",
                            "error": safe_error,
                        })
                        continue
                    results.append({
                        **analysis,
                        "document_id": document_id,
                        "filename": analysis.get("filename", filename),
                        "status": "success" if analysis.get("status") == "success" else "error",
                    })
                except HTTPException:
                    raise
                except ValueError as exc:
                    results.append({
                        "document_id": document_id,
                        "filename": filename,
                        "status": "error",
                        "error": str(exc),
                    })
                except Exception:
                    results.append({
                        "document_id": document_id,
                        "filename": filename,
                        "status": "error",
                        "error": "Document analysis failed. Other files in the batch were processed independently.",
                    })
        finally:
            registry.clear()

        successful = sum(result["status"] == "success" for result in results)
        return {
            "success": successful > 0,
            "total_files": len(results),
            "successful_files": successful,
            "failed_files": len(results) - successful,
            "results": results,
        }
    finally:
        await form.close()


@router.get("/api/ocr/status")
async def ocr_status_endpoint() -> dict:
    return get_ocr_diagnostics()


@router.get("/health", response_model=HealthResponse)
async def health(gateway: Gateway = Depends(get_gateway)) -> HealthResponse:
    return {"status": "ok", "detection": gateway.detection_status()}
