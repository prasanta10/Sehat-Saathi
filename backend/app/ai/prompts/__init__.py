"""Versioned prompt templates. Every stored AI result records the prompt version."""

from pathlib import Path

PROMPT_DIR = Path(__file__).parent
EXTRACT_PROMPT_VERSION = "extract_v3"


def load(name: str) -> str:
    return (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8")
