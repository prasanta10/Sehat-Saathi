"""Provider interfaces for every AI capability. Each has a deterministic mock.

Providers return *raw* model output; the orchestrator validates it against these schemas,
verifies evidence spans, and falls back to manual entry. Nothing from a provider reaches rules or
stored facts without that validation.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.facts import FactSpec


class ProviderError(RuntimeError):
    """The provider could not produce output (network, timeout, server error)."""


class ExtractedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    # yes/no for tristate, an allowed value for enum, the spoken phrase for numbers ("teen hafte").
    value: str | None
    evidence: str | None = Field(description="Exact words from the transcript, or null.")


class ExtractionOutput(BaseModel):
    """What the language model must return (constrained JSON)."""

    model_config = ConfigDict(extra="forbid")
    chief_complaints: list[str]
    facts: list[ExtractedFact]
    suggested_pathways: list[str]
    unparsed_concerns: list[str]


class Transcript(BaseModel):
    text: str
    language: str
    provider: str
    model_rev: str | None = None
    duration_s: float | None = None


class Extractor(Protocol):
    name: str
    model_rev: str

    async def extract(
        self, transcript: str, language: str, facts: list[FactSpec], pathways: list[str]
    ) -> str:
        """Return the raw JSON text produced by the model."""
        ...


class ASR(Protocol):
    name: str

    async def transcribe(self, audio: bytes, language: str) -> Transcript: ...


class Writer(Protocol):
    """Rewrites a complete template for fluency. Output is checked; the template is the fallback."""

    name: str
    model_rev: str

    async def rewrite(self, kind: str, language: str, text: str) -> str: ...
