from __future__ import annotations

import json
import time
import uuid
from collections import Counter

from app.audit.logger import AuditStore
from app.config import Settings
from app.detection.ner_engine import GlinerEngine
from app.detection.presidio_engine import PresidioDetectionEngine
from app.llm.base import LLMError, LLMProvider
from app.llm.provider import GroqProvider, serialize_payload
from app.privacy.outbound_guard import verify_outbound
from app.privacy.reinsertion import reinsert
from app.privacy.token_manager import TokenManager


class PrivacyLeakError(RuntimeError):
    pass


class Gateway:
    def __init__(
        self,
        settings: Settings,
        audit_store: AuditStore,
        providers: dict[str, LLMProvider] | None = None,
    ) -> None:
        self.settings = settings
        self.audit = audit_store
        self.ner = GlinerEngine(settings.gliner_model, settings.enable_gliner)
        self.detector = PresidioDetectionEngine(settings.spacy_model, self.ner)
        self.providers = providers or {"groq": GroqProvider(settings)}
        self._vault: dict[str, tuple[float, dict[str, str]]] = {}

    def detection_status(self) -> dict:
        return self.detector.status()

    def detect(self, text: str) -> tuple[list, dict]:
        entities = self.detector.detect(text)
        return entities, self._public_entities(entities)

    @staticmethod
    def _public_entities(entities: list) -> list[dict]:
        return [
            {
                "type": item.entity_type,
                "start": item.start,
                "end": item.end,
                "score": round(item.score, 4),
                "source": item.source,
            }
            for item in entities
        ]

    def mask(self, text: str) -> dict:
        request_id = str(uuid.uuid4())
        entities = self.detector.detect(text)
        manager = TokenManager()
        sanitized, public_entities = manager.mask(text, entities)
        self._save_mapping(request_id, manager.mapping)
        return {
            "request_id": request_id,
            "sanitized_text": sanitized,
            "entities": public_entities,
            "detection_status": self.detection_status(),
        }

    def reinsert(self, request_id: str, text: str) -> dict:
        mapping = self._get_mapping(request_id)
        if mapping is None:
            return None
        outcome = reinsert(text, mapping)
        return {
            "request_id": request_id,
            "final_response": outcome.text,
            "restoration": {
                "restored": outcome.restored,
                "missing": outcome.missing,
                "unknown": outcome.unknown,
                "malformed": outcome.malformed,
            },
        }

    async def process(self, text: str, task: str, provider_name: str | None) -> dict:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        entities = self.detector.detect(text)
        manager = TokenManager()
        sanitized, public_entities = manager.mask(text, entities)
        entity_counts = dict(Counter(item.entity_type for item in entities))
        provider_key = provider_name or self.settings.llm_provider
        if provider_key == "configured_provider":
            provider_key = self.settings.llm_provider
        provider = self.providers.get(provider_key)
        if provider is None:
            raise ValueError(f"Unsupported provider: {provider_key}")

        payload = provider.build_payload(sanitized, task)
        serialized = serialize_payload(payload)
        guard = verify_outbound(serialized, list(manager.mapping.values()))
        if not guard.allowed:
            self.audit.save_security_event(
                request_id,
                "outbound_pii_blocked",
                {"reason": "known detected value found in outbound payload"},
            )
            latency = (time.perf_counter() - started) * 1000
            self.audit.save_record(
                request_id=request_id,
                status="blocked",
                entity_counts=json.dumps(entity_counts),
                outbound_payload=None,
                provider=provider_key,
                model=provider.model,
                leakage_verified=False,
                processing_latency_ms=latency,
                restoration_status="{}",
                security_events=json.dumps(["outbound_pii_blocked"]),
            )
            raise PrivacyLeakError("Outbound request blocked by the privacy gateway.")

        try:
            llm_result = await provider.complete(serialized)
        except LLMError as exc:
            latency = (time.perf_counter() - started) * 1000
            self.audit.save_record(
                request_id=request_id,
                status="failed",
                entity_counts=json.dumps(entity_counts),
                outbound_payload=serialized,
                provider=provider_key,
                model=provider.model,
                leakage_verified=True,
                processing_latency_ms=latency,
                restoration_status="{}",
                security_events="[]",
            )
            raise

        restoration = reinsert(llm_result.text, manager.mapping)
        latency = (time.perf_counter() - started) * 1000
        self.audit.save_record(
            request_id=request_id,
            status="success",
            entity_counts=json.dumps(entity_counts),
            outbound_payload=serialized,
            provider=provider_key,
            model=llm_result.model,
            leakage_verified=True,
            processing_latency_ms=latency,
            restoration_status=json.dumps(
                {
                    "restored": restoration.restored,
                    "missing": restoration.missing,
                    "unknown": restoration.unknown,
                    "malformed": restoration.malformed,
                }
            ),
            security_events="[]",
        )
        self._save_mapping(request_id, manager.mapping)
        return {
            "request_id": request_id,
            "status": "success",
            "original_text": text,
            "sanitized_text": sanitized,
            "entities": public_entities,
            "llm_response": llm_result.text,
            "final_response": restoration.text,
            "leakage_detected": False,
            "restoration": {
                "restored": restoration.restored,
                "missing": restoration.missing,
                "unknown": restoration.unknown,
                "malformed": restoration.malformed,
            },
            "metrics": {"processing_latency_ms": round(latency, 2)},
            "provider": provider_key,
            "model": llm_result.model,
            "detection_status": self.detection_status(),
        }

    def _save_mapping(self, request_id: str, mapping: dict[str, str]) -> None:
        self._purge_vault()
        self._vault[request_id] = (time.monotonic(), dict(mapping))

    def _get_mapping(self, request_id: str) -> dict[str, str] | None:
        self._purge_vault()
        entry = self._vault.get(request_id)
        return dict(entry[1]) if entry else None

    def _purge_vault(self) -> None:
        cutoff = time.monotonic() - 3600
        self._vault = {
            key: value for key, value in self._vault.items() if value[0] >= cutoff
        }
