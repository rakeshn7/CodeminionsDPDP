from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NERMatch:
    entity_type: str
    start: int
    end: int
    score: float
    source: str = "gliner"


class GlinerEngine:
    def __init__(self, model_name: str, enabled: bool = True) -> None:
        self.model_name = model_name
        self.enabled = enabled
        self._model: Any | None = None
        self._load_error: str | None = None

    def status(self) -> dict[str, str | bool | None]:
        if not self.enabled:
            state = "disabled"
        elif self._model is not None:
            state = "ready"
        elif self._load_error:
            state = "unavailable"
        else:
            state = "not_loaded"
        return {
            "enabled": self.enabled,
            "state": state,
            "model": self.model_name,
            "error": self._load_error,
        }

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        if self._load_error:
            raise RuntimeError(self._load_error)
        try:
            from gliner import GLiNER

            self._model = GLiNER.from_pretrained(self.model_name)
            return self._model
        except Exception as exc:
            self._load_error = f"{type(exc).__name__}: {str(exc)[:240]}"
            raise RuntimeError(self._load_error) from exc

    @staticmethod
    def _chunks(text: str, size: int = 2500, overlap: int = 200):
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind("\n", start + size // 2, end),
                               text.rfind(" ", start + size // 2, end))
                if boundary > start:
                    end = boundary
            yield start, end, text[start:end]
            if end == len(text):
                break
            start = max(start + 1, end - overlap)

    def detect(self, text: str) -> tuple[list[NERMatch], str | None]:
        if not self.enabled or not text:
            return [], None
        try:
            model = self._load()
            results: list[NERMatch] = []
            for offset, _, chunk in self._chunks(text):
                entities = model.predict_entities(
                    chunk,
                    ["person", "address"],
                    threshold=0.42,
                )
                for entity in entities:
                    label = str(entity.get("label", "")).lower()
                    entity_type = (
                        "PERSON"
                        if label in {"person", "name", "personal name"}
                        else "ADDRESS"
                        if label in {"address", "location"}
                        else ""
                    )
                    start, end = int(entity["start"]), int(entity["end"])
                    if entity_type and 0 <= start < end <= len(chunk):
                        results.append(
                            NERMatch(
                                entity_type,
                                offset + start,
                                offset + end,
                                float(entity.get("score", 0.65)),
                            )
                        )
            return results, None
        except Exception as exc:
            message = str(exc)[:240] or type(exc).__name__
            return [], f"GLiNER unavailable: {message}"
