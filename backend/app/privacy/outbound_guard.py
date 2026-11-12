from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    leaked_values: tuple[str, ...]


def _value_pattern(value: str) -> re.Pattern[str]:
    escaped = re.escape(value)
    left = r"(?<![A-Za-z0-9_])" if value[0].isalnum() else ""
    right = r"(?![A-Za-z0-9_])" if value[-1].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


def verify_outbound(serialized_payload: str, known_values: list[str]) -> GuardResult:
    """Reject exact known values while avoiding substring matches in larger words."""
    leaked = []
    seen = set()
    for value in known_values:
        candidate = value.strip()
        if not candidate or candidate.casefold() in seen:
            continue
        seen.add(candidate.casefold())
        # Two-character names are common words and do not provide a reliable
        # content-based signal in a serialized prompt; longer identity values
        # and names are checked with token boundaries.
        if len(candidate) < 3:
            continue
        if _value_pattern(candidate).search(serialized_payload):
            leaked.append(candidate)
    return GuardResult(not leaked, tuple(leaked))
