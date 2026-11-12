from typing import Any

from fastapi import APIRouter

from app.api.deps import RulesDep
from app.config import get_settings
from app.content.bundle import build_bundle
from app.services.errors import NotFound

router = APIRouter(tags=["content"])


@router.get("/content/bundle")
def content_bundle(rules: RulesDep) -> dict[str, Any]:
    return build_bundle(rules, get_settings().content_root)


@router.get("/references/{ref_id}")
def reference(ref_id: str, rules: RulesDep) -> dict[str, Any]:
    refs = build_bundle(rules, get_settings().content_root)["references"]
    if ref_id not in refs:
        raise NotFound("reference_not_found")
    ref: dict[str, Any] = refs[ref_id]
    return ref
