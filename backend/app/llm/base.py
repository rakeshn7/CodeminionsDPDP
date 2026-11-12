from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def build_payload(self, sanitized_text: str, task: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def complete(self, serialized_payload: str) -> LLMResult:
        raise NotImplementedError
