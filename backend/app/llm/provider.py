from __future__ import annotations

import json
import logging

import httpx

from app.config import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult

_LOGGER = logging.getLogger(__name__)

_SAFE_PROVIDER_ERROR_CODES = {
    "context_length_exceeded",
    "invalid_api_key",
    "invalid_request_error",
    "json_validate_failed",
    "model_not_found",
    "rate_limit_exceeded",
    "unsupported_value",
}
_SAFE_PROVIDER_PARAMS = {
    "max_tokens",
    "messages",
    "model",
    "reasoning_effort",
    "response_format",
    "temperature",
}


def _safe_error_metadata(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""

    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return ""

    fields = []
    code = error.get("code")
    if isinstance(code, str) and code in _SAFE_PROVIDER_ERROR_CODES:
        fields.append(f"code={code}")
    param = error.get("param")
    if isinstance(param, str) and param in _SAFE_PROVIDER_PARAMS:
        fields.append(f"param={param}")
    error_type = error.get("type")
    if error_type == "invalid_request_error":
        fields.append(f"type={error_type}")
    return ", ".join(fields)


_SYSTEM_PROMPT = (
    "You are a privacy-preserving enterprise assistant. Treat angle-bracket "
    "placeholders such as <PERSON_1> as opaque data. Preserve every placeholder "
    "exactly, including its spelling and number, whenever it is relevant. Never "
    "guess or invent the personal information represented by a placeholder."
)


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.groq_api_key
        self.base_url = settings.groq_base_url
        self.model = settings.groq_model

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
        if not self.api_key.strip():
            _LOGGER.error(
                "Groq provider failed (LLMError): GROQ_API_KEY is missing or empty."
            )
            raise LLMError("GROQ_API_KEY is not configured.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                for attempt in range(2):
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        content=serialized_payload.encode("utf-8"),
                        headers=headers,
                    )
                    if (
                        attempt == 0
                        and response.status_code == 400
                        and "code=json_validate_failed"
                        in _safe_error_metadata(response)
                    ):
                        _LOGGER.warning(
                            "Groq returned a JSON validation error; retrying the sanitized request once."
                        )
                        continue
                    response.raise_for_status()
                    break
            body = response.json()
            answer = body["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer:
                _LOGGER.error(
                    "Groq provider failed (LLMError): provider returned an empty or invalid response."
                )
                raise LLMError("The provider returned an empty or invalid response.")
            return LLMResult(answer, str(body.get("model", self.model)))
        except LLMError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            detail = "provider request failed"
            if isinstance(exc, httpx.HTTPStatusError):
                detail = f"provider returned HTTP {exc.response.status_code}"
            elif isinstance(exc, httpx.TimeoutException):
                detail = "provider request timed out"
            elif isinstance(exc, httpx.RequestError):
                detail = "provider connection failed"
            elif isinstance(exc, ValueError):
                detail = "provider response was not valid JSON"
            elif isinstance(exc, (KeyError, IndexError, TypeError)):
                detail = "provider response did not contain a valid chat completion"
            metadata = (
                _safe_error_metadata(exc.response)
                if isinstance(exc, httpx.HTTPStatusError)
                else ""
            )
            _LOGGER.error(
                "Groq provider failed (%s): %s%s",
                type(exc).__name__,
                detail,
                f" ({metadata})" if metadata else "",
            )
            raise LLMError(detail) from exc


def serialize_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
