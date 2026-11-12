"""Application configuration, read from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    asr_provider: Literal["mock", "indic_conformer_http"] = "mock"
    asr_base_url: str = ""
    llm_provider: Literal["mock", "openai_compatible", "hosted"] = "mock"
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    tts_provider: Literal["browser", "mock", "server"] = "browser"
    hosted_llm_allowed: bool = False
    llm_rewrite_outputs: bool = False  # LLM fluency rewrite of outputs (checked; template fallback)

    database_url: str = "sqlite:///./sehat.db"
    audio_retention: str = "delete_on_confirm"
    audio_dir: Path = REPO_ROOT / "backend" / "data" / "audio"
    asr_timeout_s: float = 60.0
    asr_language: str = "hi"  # speech language; IndicConformer has no English
    max_audio_bytes: int = 15 * 1024 * 1024

    cors_origins: str = "http://localhost:5173"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    audio_encryption_key: str = ""  # Fernet key; without it, audio is never written to disk
    encounter_retention_days: int = 365
    content_root: Path = REPO_ROOT

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
