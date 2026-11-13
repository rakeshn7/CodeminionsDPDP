from __future__ import annotations

import json
import time
import uuid
from collections import Counter

from app.audit.logger import AuditStore
from app.config import Settings
from app.detection.ner_engine import GlinerEngine
from app.detection.presidio_engine import PresidioDetectionEngine
from app.extraction.extractor import extract_document
from app.extraction.ocr import get_ocr_diagnostics
from app.llm.analyzer import analyze_document_with_llm
from app.llm.base import LLMError, LLMProvider
from app.llm.provider import GroqProvider, serialize_payload
from app.nlp.language import detect_document_language
from app.privacy.outbound_guard import verify_outbound
from app.privacy.reinsertion import reinsert
from app.privacy.token_manager import TokenManager
from app.validation.validator import validate_document_data


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

    async def analyze_document(
        self,
        text: str,
        filename: str = "document.txt",
        file_type: str = "txt",
        file_size_bytes: int = 0,
        page_count: int = 1,
        pages: list[dict] | None = None,
        ocr_used: bool = False,
        ocr_status: dict | None = None,
        warnings: list[str] | None = None,
        provider_name: str | None = None,
        run_llm: bool = True,
    ) -> dict:
        t_start = time.perf_counter()
        request_id = str(uuid.uuid4())
        warnings_list = list(warnings or [])

        # 1. Multilingual language profiling
        lang_profile = detect_document_language(text)
        if ocr_used:
            installed_ocr_languages = set(
                (ocr_status or {}).get("installed_languages", [])
            )
            for language, code in (("Hindi", "hin"), ("Kannada", "kan")):
                if (
                    language in lang_profile.detected_languages
                    and code not in installed_ocr_languages
                ):
                    warnings_list.append(
                        f"{language} text was detected, but the matching OCR language pack "
                        "was not available; scanned text in that language may be incomplete."
                    )

        # 2. PII Detection
        t_det_start = time.perf_counter()
        entities = self.detector.detect(text)
        entities = PresidioDetectionEngine._resolve_overlaps(entities, len(text), text)
        public_entities = self._public_entities(entities)
        det_latency = (time.perf_counter() - t_det_start) * 1000

        # 3. PII Masking
        manager = TokenManager()
        sanitized_text, masked_entities = manager.mask(text, entities)
        entity_counts = dict(Counter(item["type"] for item in masked_entities))
        self._save_mapping(request_id, manager.mapping)

        # Summary of placeholders without revealing raw values
        placeholders_summary = {
            token: f"[{entity_type} Placeholder]"
            for token in manager.mapping.keys()
            for entity_type in [token.strip("<>").split("_")[0]]
        }

        # 4. Smart Data Validation
        t_val_start = time.perf_counter()
        name_classifier = getattr(self.detector, "classify_name_value", None)
        raw_findings = validate_document_data(
            text,
            pages,
            name_classifier=name_classifier if callable(name_classifier) else None,
        )
        val_latency = (time.perf_counter() - t_val_start) * 1000
        findings_dicts = [f.to_dict() for f in raw_findings]

        err_cnt = sum(1 for f in raw_findings if f.severity == "ERROR")
        warn_cnt = sum(1 for f in raw_findings if f.severity == "WARNING")
        info_cnt = sum(1 for f in raw_findings if f.severity == "INFO")
        validation_summary = {
            "errors": err_cnt,
            "warnings": warn_cnt,
            "info": info_cnt,
            "total": len(raw_findings),
        }

        # 5. Risk Assessment
        risk_score = 0.1
        risk_factors = []
        if err_cnt > 0:
            risk_score += min(0.4, err_cnt * 0.15)
            risk_factors.append(f"{err_cnt} data validation error(s) found")
        if "AADHAAR" in entity_counts:
            risk_score += 0.25
            risk_factors.append("Contains UIDAI Aadhaar identity data")
        if "BANK_ACCOUNT" in entity_counts or "PAN" in entity_counts:
            risk_score += 0.2
            risk_factors.append("Contains sensitive financial identifiers (PAN/Bank Account)")
        if len(entities) >= 5:
            risk_score += 0.15
            risk_factors.append(f"High PII density ({len(entities)} personal entities detected)")

        risk_score = round(min(1.0, max(0.0, risk_score)), 2)
        overall_risk = "high" if risk_score >= 0.65 else "medium" if risk_score >= 0.35 else "low"

        # 6. Contextual LLM Analysis (Sanitized Text Only)
        provider_key = provider_name or self.settings.llm_provider
        if provider_key == "configured_provider":
            provider_key = self.settings.llm_provider
        provider = self.providers.get(provider_key)
        supported_detection_languages = {"English", "Hindi", "Kannada"}
        unsupported_languages = sorted(
            set(lang_profile.detected_languages) - supported_detection_languages
        )
        coverage_warning = None
        if unsupported_languages:
            coverage_warning = (
                "External review was skipped because local PII detection is not validated "
                f"for the detected language(s): {', '.join(unsupported_languages)}. "
                "Review extracted text locally before using any external service."
            )
            warnings_list.append(coverage_warning)

        llm_analysis: dict = {
            "status": "skipped",
            "summary": None if coverage_warning else "AI contextual analysis skipped or not requested.",
            "findings": [],
            "error": coverage_warning,
            "model": getattr(provider, "model", "none") if provider else "none",
        }
        llm_latency = 0.0

        if (
            run_llm
            and provider is not None
            and sanitized_text.strip()
            and not unsupported_languages
        ):
            # Check outbound guard to ensure zero raw PII leaks to LLM
            guard = verify_outbound(sanitized_text, list(manager.mapping.values()))
            if not guard.allowed:
                self.audit.save_security_event(
                    request_id,
                    "outbound_pii_blocked",
                    {"reason": "sanitized text contained unmasked raw PII"},
                )
                llm_analysis = {
                    "status": "failed",
                    "summary": None,
                    "findings": [],
                    "error": "Outbound request blocked: raw PII would have been transmitted.",
                    "model": provider.model,
                }
            else:
                t_llm_start = time.perf_counter()
                llm_analysis = await analyze_document_with_llm(
                    sanitized_text,
                    provider,
                    language=lang_profile.primary_language,
                )
                llm_latency = (time.perf_counter() - t_llm_start) * 1000
                if llm_analysis.get("status") == "success":
                    summary = llm_analysis.get("summary")
                    if isinstance(summary, str):
                        missing_tokens = [
                            token
                            for token in manager.mapping
                            if token not in summary
                        ]
                        if missing_tokens:
                            summary = (
                                f"{summary.rstrip()}\n\n"
                                f"Protected details: {', '.join(missing_tokens)}"
                            )
                        restoration = reinsert(summary, manager.mapping)
                        llm_analysis.update(
                            {
                                "summary": summary,
                                "restored_summary": restoration.text,
                                "restoration": {
                                    "restored": restoration.restored,
                                    "missing": restoration.missing,
                                    "unknown": restoration.unknown,
                                    "malformed": restoration.malformed,
                                },
                            }
                        )

        total_latency = (time.perf_counter() - t_start) * 1000

        # 7. Audit Logging
        self.audit.save_record(
            request_id=request_id,
            status="success" if err_cnt == 0 else "flagged",
            entity_counts=json.dumps(entity_counts),
            outbound_payload=sanitized_text if run_llm else None,
            provider=provider_key,
            model=getattr(provider, "model", None),
            leakage_verified=True,
            processing_latency_ms=total_latency,
            restoration_status=json.dumps({"placeholders_count": len(manager.mapping)}),
            security_events="[]",
        )

        return {
            "request_id": request_id,
            "status": "success",
            "filename": filename,
            "file_type": file_type,
            "file_size_bytes": file_size_bytes,
            "extraction_status": "success",
            "page_count": page_count,
            "pages": pages or [{"page_number": 1, "text": text, "char_count": len(text)}],
            "detected_languages": lang_profile.detected_languages,
            "primary_language": lang_profile.primary_language,
            "is_mixed_language": lang_profile.is_mixed,
            "language_profile": lang_profile.to_dict(),
            "extracted_text": text,
            "sanitized_text": sanitized_text,
            "entities": masked_entities,
            "entity_counts": entity_counts,
            "placeholders_summary": placeholders_summary,
            "validation_findings": findings_dicts,
            "validation_summary": validation_summary,
            "llm_analysis": llm_analysis,
            "overall_risk": overall_risk,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "metrics": {
                "detection_latency_ms": round(det_latency, 2),
                "validation_latency_ms": round(val_latency, 2),
                "llm_latency_ms": round(llm_latency, 2),
                "total_latency_ms": round(total_latency, 2),
            },
            "ocr_used": ocr_used,
            "ocr_status": ocr_status or get_ocr_diagnostics(),
            "warnings": warnings_list,
            "error": None,
        }

    async def analyze_file(
        self,
        file_bytes: bytes,
        filename: str,
        provider_name: str | None = None,
        run_llm: bool = True,
    ) -> dict:
        t_ext_start = time.perf_counter()
        ext_res = extract_document(file_bytes, filename)
        ext_latency = (time.perf_counter() - t_ext_start) * 1000

        if ext_res.status == "failed" or not ext_res.full_text:
            ocr_diag = ext_res.ocr_status or get_ocr_diagnostics()
            return {
                "request_id": str(uuid.uuid4()),
                "status": "empty" if ext_res.status == "empty" else "failed",
                "filename": ext_res.filename,
                "file_type": ext_res.file_type,
                "file_size_bytes": ext_res.file_size_bytes,
                "extraction_status": ext_res.status,
                "page_count": ext_res.page_count,
                "pages": ext_res.pages,
                "detected_languages": ["English"],
                "primary_language": "Unknown",
                "is_mixed_language": False,
                "language_profile": {
                    "primary_language": "Unknown",
                    "detected_languages": [],
                    "is_mixed": False,
                    "scripts": {},
                    "confidence": 0.0,
                    "notes": ext_res.error or "Extraction produced no text.",
                },
                "extracted_text": "",
                "sanitized_text": "",
                "entities": [],
                "entity_counts": {},
                "placeholders_summary": {},
                "validation_findings": [],
                "validation_summary": {"errors": 0, "warnings": 0, "info": 0, "total": 0},
                "llm_analysis": {
                    "status": "skipped",
                    "summary": None,
                    "findings": [],
                    "error": "No text extracted from document.",
                },
                "overall_risk": "low",
                "risk_score": 0.0,
                "risk_factors": ["No extractable document content"],
                "metrics": {"extraction_latency_ms": round(ext_latency, 2), "total_latency_ms": round(ext_latency, 2)},
                "ocr_used": ext_res.ocr_used,
                "ocr_status": ocr_diag,
                "warnings": ext_res.warnings,
                "error": ext_res.error,
            }

        result = await self.analyze_document(
            text=ext_res.full_text,
            filename=ext_res.filename,
            file_type=ext_res.file_type,
            file_size_bytes=ext_res.file_size_bytes,
            page_count=ext_res.page_count,
            pages=ext_res.pages,
            ocr_used=ext_res.ocr_used,
            ocr_status=ext_res.ocr_status,
            warnings=ext_res.warnings,
            provider_name=provider_name,
            run_llm=run_llm,
        )
        result["metrics"]["extraction_latency_ms"] = round(ext_latency, 2)
        result["metrics"]["total_latency_ms"] = round(result["metrics"]["total_latency_ms"] + ext_latency, 2)
        return result

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
