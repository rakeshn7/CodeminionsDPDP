from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GatewayRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    text: str = Field(max_length=100_000)
    task: Literal["summarize", "extract"] = "summarize"
    provider: str | None = None


class TextRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    text: str = Field(max_length=100_000)


class ReinsertRequest(BaseModel):
    request_id: str
    text: str = Field(max_length=100_000)


class EntityResponse(BaseModel):
    type: str
    placeholder: str | None = None
    start: int
    end: int
    score: float
    source: str


class RestorationResponse(BaseModel):
    restored: list[str]
    missing: list[str]
    unknown: list[str]
    malformed: list[str] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    total_requests: int
    leakage_blocked: int
    failed_requests: int
    average_processing_latency_ms: float
    total_pii_detected: int = 0
    documents_with_errors: int = 0
    pii_by_category: list[dict[str, Any]] = Field(default_factory=list)
    request_trend: list[dict[str, Any]] = Field(default_factory=list)
    language_distribution: dict[str, int] = Field(default_factory=dict)
    risk_distribution: dict[str, int] = Field(default_factory=dict)


class PresidioStatus(BaseModel):
    state: str
    spacy_model: str
    error: str | None = None
    india_regex_fallback: bool


class GlinerStatus(BaseModel):
    enabled: bool
    state: str
    model: str
    error: str | None = None


class DetectionStatus(BaseModel):
    presidio: PresidioStatus
    gliner: GlinerStatus


class DetectResponse(BaseModel):
    entities: list[EntityResponse]
    detection_status: DetectionStatus


class MaskResponse(BaseModel):
    request_id: str
    sanitized_text: str
    entities: list[EntityResponse]
    detection_status: DetectionStatus


class ProcessResponse(BaseModel):
    request_id: str
    status: Literal["success"]
    original_text: str
    sanitized_text: str
    entities: list[EntityResponse]
    llm_response: str
    final_response: str
    leakage_detected: bool
    restoration: RestorationResponse
    metrics: dict[str, float]
    provider: str
    model: str
    detection_status: DetectionStatus


class ReinsertResultResponse(BaseModel):
    request_id: str
    final_response: str
    restoration: RestorationResponse


class SecurityEventResponse(BaseModel):
    event_type: str
    timestamp: str
    details: dict[str, Any]


class AuditResponse(BaseModel):
    request_id: str
    timestamp: str
    status: str
    entity_counts: dict[str, int]
    outbound_payload: str | None
    provider: str | None
    model: str | None
    leakage_verified: bool
    processing_latency_ms: float
    restoration_status: dict[str, Any]
    security_events: list[SecurityEventResponse]


class AuditListResponse(BaseModel):
    records: list[AuditResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    detection: DetectionStatus


class ValidationFindingResponse(BaseModel):
    category: str
    severity: str
    location: str
    field: str
    masked_value: str
    explanation: str
    suggestion: str
    confidence: float


class ValidationSummaryResponse(BaseModel):
    errors: int
    warnings: int
    info: int
    total: int


class LLMFindingResponse(BaseModel):
    category: str
    severity: str
    location: str
    explanation: str
    suggestion: str
    confidence: float


class LLMAnalysisResponse(BaseModel):
    status: str
    summary: str | None = None
    restored_summary: str | None = None
    restoration: RestorationResponse | None = None
    findings: list[LLMFindingResponse] = Field(default_factory=list)
    error: str | None = None
    model: str | None = None


class LanguageProfileResponse(BaseModel):
    primary_language: str
    detected_languages: list[str]
    is_mixed: bool
    scripts: dict[str, float]
    confidence: float
    notes: str | None = None


class DocumentAnalyzeResponse(BaseModel):
    request_id: str
    status: str
    filename: str
    file_type: str
    file_size_bytes: int
    extraction_status: str
    page_count: int
    pages: list[dict[str, Any]] = Field(default_factory=list)
    detected_languages: list[str]
    primary_language: str
    is_mixed_language: bool
    language_profile: LanguageProfileResponse
    extracted_text: str
    sanitized_text: str
    entities: list[EntityResponse]
    entity_counts: dict[str, int]
    placeholders_summary: dict[str, str] = Field(default_factory=dict)
    validation_findings: list[ValidationFindingResponse] = Field(default_factory=list)
    validation_summary: ValidationSummaryResponse
    llm_analysis: LLMAnalysisResponse
    overall_risk: str
    risk_score: float
    risk_factors: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    ocr_used: bool = False
    ocr_status: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
