from __future__ import annotations

from app.detection.presidio_engine import EntitySpan


class TokenManager:
    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self._tokens_by_value: dict[tuple[str, str], str] = {}
        self._counters: dict[str, int] = {}

    def token_for(self, entity_type: str, value: str) -> str:
        key = (entity_type, value)
        if key in self._tokens_by_value:
            return self._tokens_by_value[key]
        index = self._counters.get(entity_type, 0) + 1
        self._counters[entity_type] = index
        token = f"<{entity_type}_{index}>"
        self._tokens_by_value[key] = token
        self.mapping[token] = value
        return token

    def mask(self, text: str, entities: list[EntitySpan]) -> tuple[str, list[dict]]:
        replacements = []
        for entity in entities:
            value = text[entity.start : entity.end]
            token = self.token_for(entity.entity_type, value)
            replacements.append((entity, token))

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
