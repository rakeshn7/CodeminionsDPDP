from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.detection.india_recognizers import (
    build_presidio_recognizers,
    detect_india_patterns,
)
from app.detection.ner_engine import GlinerEngine
from app.validation.validator import non_person_candidate_type

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntitySpan:
    entity_type: str
    start: int
    end: int
    score: float
    source: str


class PresidioDetectionEngine:
    _PERSON_LABELS = {
        "AADHAAR",
        "AADHAR",
        "GSTIN",
        "PAN",
        "PASSPORT",
        "PIN",
        "PIN CODE",
        "VOTER",
        "VOTER ID",
        "EMAIL",
        "EMAIL ADDRESS",
        "PHONE",
        "PHONE NUMBER",
        "BANK ACCOUNT",
        "DOB",
        "DATE OF BIRTH",
    }

    def __init__(self, spacy_model: str, gliner: GlinerEngine) -> None:
        self.spacy_model = spacy_model
        self.gliner = gliner
        self._analyzer = None
        self._presidio_error: str | None = None
        self._initialize_presidio()

    def _initialize_presidio(self) -> None:
        try:
            from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": self.spacy_model}],
                }
            )
            nlp_engine = provider.create_engine()
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(languages=["en"])
            for recognizer in build_presidio_recognizers():
                registry.add_recognizer(recognizer)
            self._analyzer = AnalyzerEngine(
                registry=registry,
                nlp_engine=nlp_engine,
                supported_languages=["en"],
            )
        except Exception as exc:
            self._presidio_error = f"{type(exc).__name__}: {str(exc)[:240]}"

    def status(self) -> dict[str, object]:
        return {
            "presidio": {
                "state": "ready" if self._analyzer is not None else "unavailable",
                "spacy_model": self.spacy_model,
                "error": self._presidio_error,
                "india_regex_fallback": True,
            },
            "gliner": self.gliner.status(),
        }

    def classify_name_value(self, value: str) -> str | None:
        """Classify non-person entities in a name field using local spaCy."""
        if self._analyzer is None or not value.strip():
            return None
        try:
            nlp = self._analyzer.nlp_engine.nlp.get("en")
            if nlp is None:
                return None
            doc = nlp(value)
            labels = {entity.label_ for entity in doc.ents}
        except Exception as exc:
            _LOGGER.warning("Local name-field classification unavailable (%s)", type(exc).__name__)
            return None

        if labels.intersection({"GPE", "LOC", "LOCATION"}):
            return "LOCATION"
        if labels.intersection({"FAC"}):
            return "ADDRESS"
        if labels.intersection({"PRODUCT"}):
            return "PRODUCT"
        if labels.intersection({"ORG"}):
            return "ORG"
        return None

    def detect(self, text: str) -> list[EntitySpan]:
        candidates: list[EntitySpan] = []
        if self._analyzer is not None and text:
            try:
                results = self._analyzer.analyze(
                    text=text,
                    language="en",
                    entities=[
                        "PERSON",
                        "AADHAAR",
                        "PAN",
                        "GSTIN",
                        "VOTER_ID",
                        "PASSPORT",
                        "PHONE_NUMBER",
                        "PIN_CODE",
                        "ADDRESS",
                        "EMAIL_ADDRESS",
                    ],
                )
                candidates.extend(
                    EntitySpan(
                        result.entity_type,
                        result.start,
                        result.end,
                        float(result.score or 0.5),
                        "presidio",
                    )
                    for result in results
                )
            except Exception as exc:
                self._presidio_error = f"{type(exc).__name__}: {str(exc)[:240]}"

        candidates.extend(
            EntitySpan(item.entity_type, item.start, item.end, item.score, item.source)
            for item in detect_india_patterns(text)
        )
        try:
            from app.nlp.multilingual_pii import detect_multilingual_entities

            candidates.extend(detect_multilingual_entities(text))
        except Exception:
            pass
        ner_results, ner_error = self.gliner.detect(text)
        if ner_error:
            self.gliner._load_error = ner_error.removeprefix("GLiNER unavailable: ")
        candidates.extend(
            EntitySpan(item.entity_type, item.start, item.end, item.score, item.source)
            for item in ner_results
        )
        candidates = [
            item
            for item in candidates
            if not self._is_person_label(text, item)
            and not (
                item.entity_type == "PERSON"
                and non_person_candidate_type(text[item.start : item.end]) is not None
            )
        ]
        return self._resolve_overlaps(candidates, len(text), text)

    @classmethod
    def _is_person_label(cls, text: str, item: EntitySpan) -> bool:
        value = text[item.start : item.end].strip()
        return (
            item.entity_type == "PERSON"
            and value.isupper()
            and value in cls._PERSON_LABELS
        )

    @staticmethod
    def _resolve_overlaps(
        candidates: list[EntitySpan], text_length: int, text: str = ""
    ) -> list[EntitySpan]:
        priority = {
            "GSTIN": 8,
            "AADHAAR": 8,
            "PAN": 7,
            "VOTER_ID": 7,
            "PASSPORT": 7,
            "PHONE_NUMBER": 7,
            "EMAIL_ADDRESS": 8,
            "BANK_ACCOUNT": 7,
            "DATE_OF_BIRTH": 7,
            "PIN_CODE": 9,
            "PERSON": 6,
            "ADDRESS": 2,
        }
        valid = [
            item
            for item in candidates
            if 0 <= item.start < item.end <= text_length
        ]
        if text:
            pin_codes = [
                item for item in valid if item.entity_type == "PIN_CODE"
            ]
            adjusted: list[EntitySpan] = []
            for item in valid:
                if item.entity_type == "ADDRESS":
                    trailing_pin = next(
                        (
                            pin
                            for pin in pin_codes
                            if item.start < pin.start < item.end
                            and not text[pin.end : item.end].strip(" ,.-:")
                        ),
                        None,
                    )
                    if trailing_pin is not None:
                        address_end = trailing_pin.start
                        while (
                            address_end > item.start
                            and text[address_end - 1].isspace()
                        ):
                            address_end -= 1
                        item = EntitySpan(
                            item.entity_type,
                            item.start,
                            address_end,
                            item.score,
                            item.source,
                        )
                if item.start < item.end:
                    adjusted.append(item)
            valid = adjusted
        valid.sort(
            key=lambda item: (
                priority.get(item.entity_type, 0),
                int(
                    item.entity_type == "ADDRESS"
                    and item.source == "india_regex"
                ),
                item.score,
                item.end - item.start,
            ),
            reverse=True,
        )
        selected: list[EntitySpan] = []
        for item in valid:
            if not any(item.start < kept.end and kept.start < item.end for kept in selected):
                selected.append(item)
        ordered = sorted(selected, key=lambda item: item.start)
        if not text:
            return ordered

        merged: list[EntitySpan] = []
        for item in ordered:
            if (
                item.entity_type == "ADDRESS"
                and item.source == "gliner"
                and merged
                and merged[-1].entity_type == "ADDRESS"
                and merged[-1].source == "gliner"
            ):
                previous = merged[-1]
                separator = text[previous.end : item.start]
                if len(separator) <= 3 and re.fullmatch(r",\s*", separator):
                    merged[-1] = EntitySpan(
                        entity_type="ADDRESS",
                        start=previous.start,
                        end=item.end,
                        score=min(previous.score, item.score),
                        source="gliner",
                    )
                    continue
            merged.append(item)
        return merged
