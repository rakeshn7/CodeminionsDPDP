from __future__ import annotations

import asyncio
import email.utils
import json
import logging
import math
import re
import time
from datetime import datetime, timezone

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


def _rate_limit_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after", "").strip()
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        if retry_after:
            try:
                retry_time = email.utils.parsedate_to_datetime(retry_after)
                if retry_time.tzinfo is None:
                    retry_time = retry_time.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_time - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass

    reset = response.headers.get("x-ratelimit-reset-requests", "").strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s|m)", reset)
    if match:
        amount = float(match.group(1))
        return amount / 1000 if match.group(2) == "ms" else amount * (60 if match.group(2) == "m" else 1)

    return min(2**attempt, 8)


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
        self.max_rate_limit_retries = settings.groq_max_rate_limit_retries
        self.max_rate_limit_wait_seconds = settings.groq_max_rate_limit_wait_seconds
        self._request_lock = asyncio.Lock()
        self._rate_limited_until = 0.0

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
            async with self._request_lock:
                remaining = self._rate_limited_until - time.monotonic()
                if remaining > 0:
                    raise LLMError(
                        f"Groq is temporarily rate-limiting requests. Try again in about {math.ceil(remaining)} seconds."
                    )
                self._rate_limited_until = 0.0
                rate_limit_retries = 0
                json_retry_used = False
                async with httpx.AsyncClient(timeout=45.0) as client:
                    while True:
                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            content=serialized_payload.encode("utf-8"),
                            headers=headers,
                        )
                        if response.status_code == 429:
                            delay = _rate_limit_delay(response, rate_limit_retries)
                            self._rate_limited_until = time.monotonic() + delay
                            if (
                                rate_limit_retries < self.max_rate_limit_retries
                                and delay <= self.max_rate_limit_wait_seconds
                            ):
                                rate_limit_retries += 1
                                _LOGGER.warning(
                                    "Groq rate limit reached; retrying the sanitized request after %.1f seconds (attempt %s/%s).",
                                    delay,
                                    rate_limit_retries,
                                    self.max_rate_limit_retries,
                                )
                                await asyncio.sleep(delay)
                                self._rate_limited_until = 0.0
                                continue
                            raise LLMError(
                                "Groq is temporarily rate-limiting requests. "
                                f"Try again in about {math.ceil(delay)} seconds."
                            )
                        if (
                            not json_retry_used
                            and response.status_code == 400
                            and "code=json_validate_failed"
                            in _safe_error_metadata(response)
                        ):
                            json_retry_used = True
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
