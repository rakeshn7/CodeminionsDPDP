from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"
    database_url: str = "sqlite:///./data/audit.db"
    spacy_model: str = "en_core_web_sm"
    gliner_model: str = "urchade/gliner_small-v2.1"
    enable_gliner: bool = True
    max_input_chars: int = 100_000
    audit_api_key: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        from dotenv import load_dotenv

        load_dotenv()
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "groq").strip().lower(),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_base_url=os.getenv(
                "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
            ).rstrip("/"),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/audit.db"),
            spacy_model=os.getenv("SPACY_MODEL", "en_core_web_sm"),
            gliner_model=os.getenv("GLINER_MODEL", "urchade/gliner_small-v2.1"),
            enable_gliner=_as_bool(os.getenv("ENABLE_GLINER"), True),
            max_input_chars=int(os.getenv("MAX_INPUT_CHARS", "100000")),
            audit_api_key=os.getenv("AUDIT_API_KEY", ""),
        )
