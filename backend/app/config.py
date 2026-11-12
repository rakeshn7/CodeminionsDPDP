from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
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
            llm_provider=os.getenv("LLM_PROVIDER", "openai").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv(
                "OPENAI_BASE_URL", "https://api.openai.com/v1"
            ).rstrip("/"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/audit.db"),
            spacy_model=os.getenv("SPACY_MODEL", "en_core_web_sm"),
            gliner_model=os.getenv("GLINER_MODEL", "urchade/gliner_small-v2.1"),
            enable_gliner=_as_bool(os.getenv("ENABLE_GLINER"), True),
            max_input_chars=int(os.getenv("MAX_INPUT_CHARS", "100000")),
            audit_api_key=os.getenv("AUDIT_API_KEY", ""),
        )
