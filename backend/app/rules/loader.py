"""Load and validate rules content (fact registry, danger signs, pathways) into typed objects."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.content.validate import ContentError, validate_content
from app.content.yamlio import load_yaml
from app.domain.facts import FactSpec
from app.rules.schema import DangerSigns, FactRegistry, Pathway


class ContentInvalid(RuntimeError):
    def __init__(self, errors: list[ContentError]) -> None:
        super().__init__("content validation failed:\n" + "\n".join(map(str, errors)))
        self.errors = errors


class RuleSet(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: str  # content hash: identical content -> identical version
    registry: FactRegistry
    danger_signs: DangerSigns
    pathways: dict[str, Pathway]

    def pathway(self, pathway_id: str) -> Pathway:
        return self.pathways[pathway_id]


def _content_hash(raw: dict[str, Any]) -> str:
    canonical = json.dumps(raw, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def load_ruleset(root: Path) -> RuleSet:
    errors = validate_content(root)
    if errors:
        raise ContentInvalid(errors)
    reg_raw = load_yaml(root / "rules" / "fact_registry.yaml")
    ds_raw = load_yaml(root / "rules" / "danger_signs.yaml")
    pw_raw = {p.stem: load_yaml(p) for p in sorted((root / "rules" / "pathways").glob("*.yaml"))}
    registry = FactRegistry(
        version=reg_raw["version"],
        facts={k: FactSpec(key=k, **v) for k, v in reg_raw["facts"].items()},
    )
    pathways = {raw["id"]: Pathway(**raw) for raw in pw_raw.values()}
    version = _content_hash({"registry": reg_raw, "danger_signs": ds_raw, "pathways": pw_raw})
    return RuleSet(
        version=version,
        registry=registry,
        danger_signs=DangerSigns(**ds_raw),
        pathways=pathways,
    )


@lru_cache
def get_ruleset() -> RuleSet:
    return load_ruleset(get_settings().content_root)
