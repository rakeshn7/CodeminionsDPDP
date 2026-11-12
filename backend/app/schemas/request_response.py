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
