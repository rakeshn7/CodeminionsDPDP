from __future__ import annotations

import json

import httpx

from app.config import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult

_SYSTEM_PROMPT = (
    "You are a privacy-preserving enterprise assistant. Treat angle-bracket "
    "placeholders such as <PERSON_1> as opaque data. Preserve every placeholder "
    "exactly, including its spelling and number, whenever it is relevant. Never "
    "guess or invent the personal information represented by a placeholder."
)


class OpenAICompatibleProvider(LLMProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model

    def build_payload(self, sanitized_text: str, task: str) -> dict:
        task_instruction = (
            "Summarize the supplied text."
            if task == "summarize"
            else "Extract the key facts from the supplied text as concise JSON."
        )
        return {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"{task_instruction}\n\n{sanitized_text}",
                },
            ],
        }

    async def complete(self, serialized_payload: str) -> LLMResult:
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    content=serialized_payload.encode("utf-8"),
                    headers=headers,
                )
            response.raise_for_status()
            body = response.json()
            answer = body["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer:
                raise LLMError("The provider returned an empty or invalid response.")
            return LLMResult(answer, str(body.get("model", self.model)))
        except LLMError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            detail = "provider request failed"
            if isinstance(exc, httpx.HTTPStatusError):
                detail = f"provider returned HTTP {exc.response.status_code}"
            elif isinstance(exc, httpx.RequestError):
                detail = "provider connection failed"
            raise LLMError(detail) from exc


def serialize_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
