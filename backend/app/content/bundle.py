"""The content bundle: everything the client needs to run the visit flow and the danger-sign
check without the server (fact registry, danger signs, pathways, reference summaries).

``python -m app.content.bundle`` writes it to frontend/src/content/bundle.json so the emergency
checklist is part of the app itself and works with no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.content.yamlio import load_yaml
from app.rules.loader import RuleSet, load_ruleset

BUNDLE_PATH = REPO_ROOT / "frontend" / "src" / "content" / "bundle.json"


def references(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in sorted((root / "knowledge" / "references").glob("*.yaml")):
        ref = load_yaml(path)
        out[ref["id"]] = {
            k: ref.get(k)
            for k in (
                "id",
                "title",
                "publisher",
                "url",
                "version_or_date",
                "retrieved_on",
                "excerpts",
            )
        }
    return out


def build_bundle(rules: RuleSet, root: Path) -> dict[str, Any]:
    return {
        "ruleset_version": rules.version,
        "facts": {k: v.model_dump(mode="json") for k, v in rules.registry.facts.items()},
        "danger_signs": rules.danger_signs.model_dump(mode="json"),
        "pathways": {k: p.model_dump(mode="json") for k, p in rules.pathways.items()},
        "references": references(root),
    }


def render(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main() -> int:
    root = REPO_ROOT
    text = render(build_bundle(load_ruleset(root), root))
    if "--check" in sys.argv:
        if not BUNDLE_PATH.exists() or BUNDLE_PATH.read_text(encoding="utf-8") != text:
            print("bundle.json is out of date: run `make bundle`", file=sys.stderr)
            return 1
        print("bundle.json is up to date")
        return 0
    BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {BUNDLE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
