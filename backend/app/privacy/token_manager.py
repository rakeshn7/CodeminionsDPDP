from __future__ import annotations

import unicodedata

from app.detection.presidio_engine import EntitySpan
from app.privacy.outbound_guard import find_value_spans


class BatchTokenRegistry:
    """Request-scoped token assignments shared across documents, never across batches."""

    def __init__(self) -> None:
        self.tokens: dict[tuple[str, str], str] = {}
        self.counters: dict[str, int] = {}
        self.managers: list[TokenManager] = []

    @staticmethod
    def normalize(entity_type: str, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value)
        normalized = " ".join(normalized.split())
        kind = entity_type.upper()
        if "PHONE" in kind or "MOBILE" in kind:
            digits = "".join(
                str(unicodedata.decimal(character))
                for character in normalized
                if character.isdecimal()
            )
            return ("+" if normalized.lstrip().startswith("+") else "") + digits
        if kind in {"EMAIL_ADDRESS", "EMAIL"}:
            return normalized.casefold()
        if kind in {"PAN", "AADHAAR", "GSTIN", "VOTER_ID", "PASSPORT"}:
            characters = []
            for character in normalized:
                if character.isdecimal():
                    characters.append(str(unicodedata.decimal(character)))
                elif character.isalnum():
                    characters.append(character.upper())
            return "".join(characters)
        if kind == "PERSON":
            return normalized.casefold()
        return normalized

    def clear(self) -> None:
        for manager in self.managers:
            manager.clear()
        self.managers.clear()
        self.tokens.clear()
        self.counters.clear()


class TokenManager:
    def __init__(self, registry: BatchTokenRegistry | None = None) -> None:
        self.mapping: dict[str, str] = {}
        self.raw_values: set[str] = set()
        self._tokens_by_value: dict[tuple[str, str], str] = {}
        self._counters: dict[str, int] = {}
        self.registry = registry
        if registry is not None:
            registry.managers.append(self)

    def token_for(self, entity_type: str, value: str) -> str:
        self.raw_values.add(value)
        key_value = (
            self.registry.normalize(entity_type, value)
            if self.registry is not None
            else value
        )
        key = (entity_type, key_value)
        if key in self._tokens_by_value:
            return self._tokens_by_value[key]
        if self.registry is not None and key in self.registry.tokens:
            token = self.registry.tokens[key]
        else:
            counters = self.registry.counters if self.registry is not None else self._counters
            index = counters.get(entity_type, 0) + 1
            counters[entity_type] = index
            token = f"<{entity_type}_{index}>"
            if self.registry is not None:
                self.registry.tokens[key] = token
        self._tokens_by_value[key] = token
        self.mapping.setdefault(token, value)
        return token

    def clear(self) -> None:
        self.mapping.clear()
        self.raw_values.clear()
        self._tokens_by_value.clear()
        self._counters.clear()

    def mask(self, text: str, entities: list[EntitySpan]) -> tuple[str, list[dict]]:
        ordered = sorted(entities, key=lambda item: (item.start, item.end))
        previous_end = 0
        for entity in ordered:
            if (
                entity.start < previous_end
                or not 0 <= entity.start < entity.end <= len(text)
            ):
                raise ValueError("Entity spans must be valid and non-overlapping.")
            previous_end = entity.end

        replacements = []
        pii_sources: dict[tuple[str, str], tuple[EntitySpan, str]] = {}
        for entity in ordered:
            value = text[entity.start : entity.end]
            token = self.token_for(entity.entity_type, value)
            replacements.append((entity, token))
            pii_sources.setdefault((entity.entity_type, value), (entity, value))

        occupied = [(entity.start, entity.end) for entity, _ in replacements]
        for source_entity, value in pii_sources.values():
            for start, end in find_value_spans(text, value):
                if any(start < current_end and current_start < end for current_start, current_end in occupied):
                    continue
                matched_value = text[start:end]
                repeated_entity = EntitySpan(
                    source_entity.entity_type,
                    start,
                    end,
                    source_entity.score,
                    "repeat_pii_mask",
                )
                replacements.append(
                    (
                        repeated_entity,
                        self.token_for(source_entity.entity_type, matched_value),
                    )
                )
                occupied.append((start, end))

        replacements.sort(key=lambda item: (item[0].start, item[0].end))
        anonymized = self._presidio_anonymize(text, replacements)
        if anonymized is None:
            anonymized = text
            for entity, token in sorted(
                replacements, key=lambda item: item[0].start, reverse=True
            ):
                anonymized = (
                    anonymized[: entity.start] + token + anonymized[entity.end :]
                )

        public_entities = [
            {
                "type": entity.entity_type,
                "placeholder": token,
                "start": entity.start,
                "end": entity.end,
                "score": round(entity.score, 4),
                "source": entity.source,
            }
            for entity, token in replacements
        ]
        return anonymized, public_entities

    @staticmethod
    def _presidio_anonymize(text: str, replacements) -> str | None:
        try:
            from presidio_anonymizer import AnonymizerEngine
            from presidio_anonymizer.entities import OperatorConfig
            from presidio_analyzer import RecognizerResult
        except ImportError:
            return None

        results = []
        operators = {}
        for index, (entity, token) in enumerate(replacements):
            # Unique synthetic entity types allow Presidio's anonymizer to apply
            # the request-specific token without exposing the mapping.
            entity_type = f"DPDP_TOKEN_{index}"
            results.append(
                RecognizerResult(
                    entity_type=entity_type,
                    start=entity.start,
                    end=entity.end,
                    score=entity.score,
                )
            )
            operators[entity_type] = OperatorConfig(
                "replace", {"new_value": token}
            )
        anonymized = AnonymizerEngine().anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text
