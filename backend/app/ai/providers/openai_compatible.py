"""Language model over an OpenAI-compatible chat API: vLLM, Ollama, llama.cpp, or a hosted API.

Uses constrained JSON decoding via ``response_format: {type: json_schema}``, which vLLM supports
in its OpenAI-compatible server (the older ``guided_json`` field was removed in vLLM 0.12) and
which Ollama also accepts. Temperature 0 and a fixed seed for extraction.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.ai import prompts
from app.ai.interfaces import ProviderError
from app.domain.facts import FactSpec, FactType


def _value_schema(f: FactSpec) -> dict[str, Any]:
    if f.type is FactType.tristate:
        return {"enum": ["yes", "no", None]}
    if f.type is FactType.enum:
        return {"enum": [*f.values, None]}
    return {"anyOf": [{"type": "string", "maxLength": 60}, {"type": "null"}]}  # phrase as spoken


def extraction_schema(facts: list[FactSpec], pathways: list[str]) -> dict[str, Any]:
    """JSON schema the model must follow: one fixed slot per fact key, facts first.

    A list of {key, value} entries let the model loop, repeat or skip keys (seen in evals);
    fixed slots make every key appear exactly once. Everything is length-bounded.
    """

    def slot(f: FactSpec) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "value": _value_schema(f),
                "evidence": {"anyOf": [{"type": "string", "maxLength": 160}, {"type": "null"}]},
            },
            "required": ["value", "evidence"],
            "additionalProperties": False,
        }

    short_list = {"type": "array", "items": {"type": "string", "maxLength": 160}, "maxItems": 5}
    return {
        "type": "object",
        "properties": {
            "facts": {
                "type": "object",
                "properties": {f.key: slot(f) for f in facts},
                "required": [f.key for f in facts],
                "additionalProperties": False,
            },
            "suggested_pathways": {
                "type": "array",
                "items": {"enum": pathways or [""]},
                "maxItems": max(len(pathways), 1),
            },
            "unparsed_concerns": short_list,
            "chief_complaints": short_list,
        },
        "required": ["facts", "suggested_pathways", "unparsed_concerns", "chief_complaints"],
        "additionalProperties": False,
    }


def to_extraction_output(content: str) -> str:
    """Convert the slot-shaped answer to the ExtractionOutput list shape. Invalid JSON is
    returned unchanged so that validation fails and the orchestrator retries or degrades."""
    try:
        data = json.loads(content)
        slots = data["facts"]
        data["facts"] = [
            {"key": k, "value": v.get("value"), "evidence": v.get("evidence")}
            for k, v in slots.items()
        ]
        return json.dumps(data, ensure_ascii=False)
    except (ValueError, KeyError, TypeError, AttributeError):
        return content


_DEVANAGARI = re.compile(r"[\u0900-\u097f]")
_LATIN = re.compile(r"[A-Za-z]")


def mostly_devanagari(text: str) -> bool:
    """True for transcripts as the speech model writes them (Devanagari, at most a stray Latin
    letter); false for romanised or mixed typed text."""
    dev, lat = len(_DEVANAGARI.findall(text)), len(_LATIN.findall(text))
    return dev > 0 and dev >= 9 * lat


def describe_facts(facts: list[FactSpec], hindi_labels: bool = False) -> str:
    """One line per fact key. Hindi labels are added only for Devanagari transcripts (speech):
    they help the model link Hindi speech to the right key but, for romanised or mixed
    transcripts, pull its answers into Devanagari so they no longer match the transcript."""
    lines = []
    for f in facts:
        if f.type is FactType.tristate:
            kind = 'yes/no ("yes", "no" or null)'
        elif f.type is FactType.enum:
            kind = "one of " + ", ".join(f'"{v}"' for v in f.values) + " or null"
        else:
            kind = f"number phrase as spoken ({f.unit}) or null"
        label = f"{f.label.en} / {f.label.hi}" if hindi_labels else f.label.en
        lines.append(f"- {f.key}: {label} — {kind}")
    return "\n".join(lines)


MAX_EXTRACTION_TOKENS = 1500  # a complete answer is ~600 tokens; more means the model is looping


class OpenAICompatibleExtractor:
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_s: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url or not model:
            raise ValueError(
                "LLM_BASE_URL and LLM_MODEL must be set for the openai_compatible provider"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_rev = model
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._timeout = timeout_s
        self._transport = transport

    def request_body(
        self, transcript: str, facts: list[FactSpec], pathways: list[str]
    ) -> dict[str, Any]:
        system = prompts.load(prompts.EXTRACT_PROMPT_VERSION).format(
            fact_list=describe_facts(facts, hindi_labels=mostly_devanagari(transcript)),
            pathways=", ".join(pathways) or "(none)",
        )
        return {
            "model": self.model,
            "temperature": 0,
            "seed": 0,
            "max_tokens": MAX_EXTRACTION_TOKENS,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"<transcript>\n{transcript}\n</transcript>"},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction",
                    "strict": True,
                    "schema": extraction_schema(facts, pathways),
                },
            },
        }

    async def extract(
        self, transcript: str, language: str, facts: list[FactSpec], pathways: list[str]
    ) -> str:
        body = self.request_body(transcript, facts, pathways)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions", json=body, headers=self._headers
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            raise ProviderError(
                f"{type(e).__name__}"
            ) from e  # no response text: it may echo patient data
        if not isinstance(content, str):
            raise ProviderError("non-text content")
        return to_extraction_output(content)


REWRITE_PROMPT_VERSION = "rewrite_v1"
REWRITE_SYSTEM = (
    "You improve the wording of a health referral text for {reader}, in {language}. Keep every "
    "fact, number, place and time exactly. Keep every line that the user marks as fixed, word for "
    "word. Do not add any disease name, medicine, dose, money amount, advice or reassurance. Short "
    "sentences. Return only the rewritten text."
)


class OpenAICompatibleWriter:
    name = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str = "", timeout_s: float = 30.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:  # fmt: skip
        if not base_url or not model:
            raise ValueError("LLM_BASE_URL and LLM_MODEL must be set")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_rev = f"{model}/{REWRITE_PROMPT_VERSION}"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._timeout = timeout_s
        self._transport = transport

    async def rewrite(self, kind: str, language: str, text: str) -> str:
        reader = "a doctor or nurse" if kind == "clinician_handoff" else "a family, read aloud"
        body = {
            "model": self.model,
            "temperature": 0.2,
            "seed": 0,
            "messages": [
                {
                    "role": "system",
                    "content": REWRITE_SYSTEM.format(
                        reader=reader, language="Hindi" if language == "hi" else "English"
                    ),
                },
                {"role": "user", "content": text},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions", json=body, headers=self._headers
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            raise ProviderError(type(e).__name__) from e
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("empty")
        return content.strip()
