"""Choose providers from configuration (.env)."""

from __future__ import annotations

from app.ai.interfaces import ASR, Extractor, Writer
from app.ai.providers.indic_conformer_http import IndicConformerHTTP
from app.ai.providers.mock import MockASR, MockExtractor, MockWriter
from app.ai.providers.openai_compatible import OpenAICompatibleExtractor, OpenAICompatibleWriter
from app.config import Settings


class HostedNotAllowed(RuntimeError):
    pass


def extractor_for(settings: Settings, *, synthetic: bool) -> Extractor:
    """The configured extractor. A hosted API may only ever see synthetic encounters, and only
    when HOSTED_LLM_ALLOWED=true (safety rule: no real patient data to hosted APIs)."""
    if settings.llm_provider == "mock":
        return MockExtractor()
    if settings.llm_provider == "hosted" and not (settings.hosted_llm_allowed and synthetic):
        raise HostedNotAllowed("hosted LLM blocked for this encounter")
    return OpenAICompatibleExtractor(
        settings.llm_base_url, settings.llm_model, settings.llm_api_key
    )


def asr_for(settings: Settings) -> ASR:
    if settings.asr_provider == "mock":
        return MockASR()
    return IndicConformerHTTP(settings.asr_base_url, settings.asr_timeout_s)


def writer_for(settings: Settings, *, synthetic: bool) -> Writer:
    if settings.llm_provider == "mock" or not settings.llm_rewrite_outputs:
        return MockWriter()
    if settings.llm_provider == "hosted" and not (settings.hosted_llm_allowed and synthetic):
        return MockWriter()
    return OpenAICompatibleWriter(settings.llm_base_url, settings.llm_model, settings.llm_api_key)
