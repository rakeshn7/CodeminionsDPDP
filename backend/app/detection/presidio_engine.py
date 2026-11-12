from __future__ import annotations

from dataclasses import dataclass

from app.detection.india_recognizers import (
    build_presidio_recognizers,
    detect_india_patterns,
)
from app.detection.ner_engine import GlinerEngine


@dataclass(frozen=True)
class EntitySpan:
    entity_type: str
    start: int
    end: int
    score: float
    source: str


class PresidioDetectionEngine:
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
                        "ADDRESS",
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
        ner_results, ner_error = self.gliner.detect(text)
        if ner_error:
            self.gliner._load_error = ner_error.removeprefix("GLiNER unavailable: ")
        candidates.extend(
            EntitySpan(item.entity_type, item.start, item.end, item.score, item.source)
            for item in ner_results
        )
        return self._resolve_overlaps(candidates, len(text))

    @staticmethod
    def _resolve_overlaps(
        candidates: list[EntitySpan], text_length: int
    ) -> list[EntitySpan]:
        priority = {
            "GSTIN": 8,
            "AADHAAR": 8,
            "PAN": 7,
            "VOTER_ID": 7,
            "PASSPORT": 7,
            "PERSON": 6,
            "ADDRESS": 2,
        }
        valid = [
            item
            for item in candidates
            if 0 <= item.start < item.end <= text_length
        ]
        valid.sort(
            key=lambda item: (
                priority.get(item.entity_type, 0),
                item.score,
                item.end - item.start,
            ),
            reverse=True,
        )
        selected: list[EntitySpan] = []
        for item in valid:
            if not any(item.start < kept.end and kept.start < item.end for kept in selected):
                selected.append(item)
        return sorted(selected, key=lambda item: item.start)
