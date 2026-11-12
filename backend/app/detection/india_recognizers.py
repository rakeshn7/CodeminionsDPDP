from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Match:
    entity_type: str
    start: int
    end: int
    score: float
    source: str = "india_regex"


_RULES: tuple[tuple[str, re.Pattern[str], float], ...] = (
    (
        "AADHAAR",
        re.compile(r"(?<!\d)[2-9]\d{3}(?:[ -]?\d{4}){2}(?!\d)", re.IGNORECASE),
        0.96,
    ),
    (
        "GSTIN",
        re.compile(
            r"(?<![A-Z0-9])(?:0[1-9]|[1-2]\d|3[0-8]|97)"
            r"[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Z0-9])",
            re.IGNORECASE,
        ),
        0.94,
    ),
    (
        "PAN",
        re.compile(
            r"(?<![A-Z0-9])[A-Z]{3}[PCHFABTLJG]"
            r"[A-Z][0-9]{4}[A-Z](?![A-Z0-9])",
            re.IGNORECASE,
        ),
        0.93,
    ),
    (
        "VOTER_ID",
        re.compile(r"(?<![A-Z0-9])[A-Z]{3}[0-9]{7}(?![A-Z0-9])", re.IGNORECASE),
        0.92,
    ),
    (
        "PASSPORT",
        re.compile(r"(?<![A-Z0-9])[A-Z][0-9]{7}(?![A-Z0-9])", re.IGNORECASE),
        0.88,
    ),
)

_ADDRESS = re.compile(
    r"\b(?:address|residing\s+at|resident\s+of|lives?\s+at|"
    r"flat|house|plot|door)\s*(?:no\.?|is|:|-)?\s*"
    r"(?P<value>[A-Z0-9][^.;\n]{5,100})",
    re.IGNORECASE,
)


def _is_valid(entity_type: str, value: str) -> bool:
    compact = re.sub(r"[ -]", "", value).upper()
    if entity_type == "AADHAAR":
        # UIDAI does not publish an API for validating number ownership; use
        # format checks and reject degenerate repeated-digit values.
        return (
            len(compact) == 12
            and compact[0] in "23456789"
            and compact.isdigit()
            and len(set(compact)) > 1
        )
    if entity_type == "PAN":
        return bool(
            re.fullmatch(r"[A-Z]{3}[PCHFABTLJG][A-Z][0-9]{4}[A-Z]", compact)
        )
    if entity_type == "GSTIN":
        pan = compact[2:12]
        return bool(
            len(compact) == 15
            and _valid_pan(pan)
            and compact[13] == "Z"
            and compact[-1].isalnum()
        )
    return True


def _valid_pan(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}[PCHFABTLJG][A-Z][0-9]{4}[A-Z]", value))


def detect_india_patterns(text: str) -> list[Match]:
    matches: list[Match] = []
    for entity_type, pattern, score in _RULES:
        for match in pattern.finditer(text):
            value = text[match.start() : match.end()]
            if _is_valid(entity_type, value):
                matches.append(
                    Match(entity_type, match.start(), match.end(), score)
                )
    for match in _ADDRESS.finditer(text):
        start, end = match.span("value")
        value = text[start:end].strip()
        end -= len(text[start:end]) - len(text[start:end].rstrip())
        if len(value) >= 6:
            matches.append(Match("ADDRESS", start, end, 0.78))
    return matches


def build_presidio_recognizers() -> list[object]:
    """Create Presidio recognizers while keeping regex fallback usable without it."""
    try:
        from presidio_analyzer import EntityRecognizer, RecognizerResult
    except ImportError:
        return []

    class IndiaPatternRecognizer(EntityRecognizer):
        def __init__(self) -> None:
            super().__init__(
                supported_entities=[rule[0] for rule in _RULES] + ["ADDRESS"],
                name="IndianIdentityAndAddressRecognizer",
                supported_language="en",
            )

        def load(self) -> None:
            return

        def analyze(self, text, entities, nlp_artifacts=None):
            requested = set(entities or self.supported_entities)
            return [
                RecognizerResult(
                    entity_type=match.entity_type,
                    start=match.start,
                    end=match.end,
                    score=match.score,
                )
                for match in detect_india_patterns(text)
                if match.entity_type in requested
            ]

    return [IndiaPatternRecognizer()]
