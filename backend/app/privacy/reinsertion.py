from __future__ import annotations

import re
from dataclasses import dataclass


_PLACEHOLDER_CANDIDATE = re.compile(r"<[A-Za-z][A-Za-z0-9_-]{0,40}>")
_MALFORMED_CANDIDATE = re.compile(r"<[A-Za-z][A-Za-z0-9_-]{0,40}(?=\s|$|[.,;:!?])")


@dataclass(frozen=True)
class ReinsertionResult:
    text: str
    restored: list[str]
    missing: list[str]
    unknown: list[str]
    malformed: list[str]


def reinsert(text: str, mapping: dict[str, str]) -> ReinsertionResult:
    restored: list[str] = []
    present: set[str] = set()

    def restore(match: re.Match[str]) -> str:
        token = match.group(0)
        if token not in mapping:
            return token
        present.add(token)
        if token not in restored:
            restored.append(token)
        return mapping[token]

    result = _PLACEHOLDER_CANDIDATE.sub(restore, text)
    missing = [token for token in mapping if token not in present]
    unknown = list(
        dict.fromkeys(
            match.group(0)
            for match in _PLACEHOLDER_CANDIDATE.finditer(text)
            if match.group(0) not in mapping
        )
    )
    malformed = list(
        dict.fromkeys(
            match.group(0) for match in _MALFORMED_CANDIDATE.finditer(text)
        )
    )
    return ReinsertionResult(result, restored, missing, unknown, malformed)
