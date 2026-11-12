"""Validate content data files (rules, knowledge) against JSON Schema and cross-references.

Run: ``uv run python -m app.content.validate [--root PATH]``. Exit status 1 on any error.

Checks beyond JSON Schema:
- every reference ID used anywhere exists in knowledge/references/, and every cited locator has
  a verbatim excerpt in that reference record
- every excerpt occurs verbatim (after whitespace/ligature normalisation) in the reference's
  stored text copy, when one is stored
- a clinician_reviewed file's content hash matches its current content (any edit resets review)
- every fact key used in a condition, question or danger sign is declared in the fact registry
- condition values fit the fact's type; nothing may match on "unknown"
- every fact a pathway's danger signs or rules depend on can be asked (is a pathway question)
  or comes from the person record
- danger signs point at tristate facts
- IDs are unique within their kind
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from app.config import REPO_ROOT
from app.content.review import content_hash
from app.content.yamlio import load_yaml

SCHEMA_DIR = REPO_ROOT / "schemas"
_LOGIC_KEYS = {"all", "any", "not"}


@dataclass(frozen=True)
class ContentError:
    file: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}: {self.where}: {self.message}"


@lru_cache
def _registry() -> Registry:
    resources = []
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(schema)
        resources.append((schema["$id"], resource))
        resources.append((path.name, resource))
    return Registry().with_resources(resources)


@lru_cache
def validator_for(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{schema_name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def schema_errors(data: Any, schema_name: str, file: str) -> list[ContentError]:
    errors = []
    for err in validator_for(schema_name).iter_errors(data):
        where = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(ContentError(file, where, err.message))
    return errors


def normalise_text(text: str) -> str:
    """Normalise extracted PDF text for excerpt matching: ligatures, private-use 'fi', spaces."""
    text = unicodedata.normalize("NFKC", text).replace("\uf001", "fi").replace("\uf002", "fl")
    return re.sub(r"\s+", " ", text).strip()


def excerpt_found(excerpt: str, source_text: str) -> bool:
    """True if every '…'-separated fragment of the excerpt occurs in the source, in order."""
    pos = 0
    for fragment in (normalise_text(f) for f in excerpt.split("…")):
        if not fragment:
            continue
        idx = source_text.find(fragment, pos)
        if idx < 0:
            return False
        pos = idx + len(fragment)
    return True


def condition_fact_keys(cond: Any) -> Iterator[str]:
    """Yield every fact key referenced by a condition."""
    if not isinstance(cond, dict):
        return
    for key, value in cond.items():
        if key in ("all", "any"):
            for sub in value:
                yield from condition_fact_keys(sub)
        elif key == "not":
            yield from condition_fact_keys(value)
        else:
            yield key


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def validate_content(root: Path) -> list[ContentError]:
    errors: list[ContentError] = []

    # --- references -----------------------------------------------------------------------
    ref_ids: set[str] = set()
    ref_locators: dict[str, set[str]] = {}
    for path in sorted((root / "knowledge" / "references").glob("*.yaml")):
        f = _rel(path, root)
        data = load_yaml(path)
        errs = schema_errors(data, "reference", f)
        errors += errs
        if errs:
            continue
        if data["id"] in ref_ids:
            errors.append(ContentError(f, "id", f"duplicate reference id {data['id']!r}"))
        if path.stem != data["id"]:
            errors.append(ContentError(f, "id", "file name must equal the reference id"))
        ref_ids.add(data["id"])
        ref_locators[data["id"]] = {e["locator"] for e in data["excerpts"]}
        locators = [e["locator"] for e in data["excerpts"]]
        if len(set(locators)) != len(locators):
            errors.append(ContentError(f, "excerpts", "duplicate excerpt locator"))
        if data.get("local_copy"):
            copy = root / data["local_copy"]
            if not copy.exists():
                errors.append(ContentError(f, "local_copy", f"missing file {data['local_copy']}"))
            else:
                text = normalise_text(copy.read_text(encoding="utf-8"))
                for i, ex in enumerate(data["excerpts"]):
                    if not excerpt_found(ex["text"], text):
                        errors.append(
                            ContentError(
                                f, f"excerpts/{i}", "excerpt not found verbatim in local copy"
                            )
                        )

    def check_ref(ref: str, f: str, where: str, locator: str | None = None) -> None:
        if ref not in ref_ids:
            errors.append(ContentError(f, where, f"unknown reference {ref!r}: no source, no rule"))
        elif locator is not None and locator not in ref_locators[ref]:
            errors.append(
                ContentError(
                    f, where, f"locator {locator!r} has no verbatim excerpt in reference {ref!r}"
                )
            )

    def check_source(src: dict[str, str], f: str, where: str) -> None:
        check_ref(src["ref"], f, where, src["locator"])

    # --- fact registry --------------------------------------------------------------------
    facts: dict[str, Any] = {}
    reg_path = root / "rules" / "fact_registry.yaml"
    if reg_path.exists():
        f = _rel(reg_path, root)
        data = load_yaml(reg_path)
        errs = schema_errors(data, "fact_registry", f)
        errors += errs
        if not errs:
            facts = data["facts"]
            for key, spec in facts.items():
                if spec["type"] == "enum":
                    missing = set(spec["values"]) - set(spec["value_labels"])
                    if missing:
                        errors.append(
                            ContentError(
                                f, f"facts/{key}", f"value_labels missing {sorted(missing)}"
                            )
                        )

    def check_review(data: dict[str, Any], f: str) -> None:
        review = data["review"]
        if review["status"] == "clinician_reviewed" and review.get("content_hash") != content_hash(
            data
        ):
            errors.append(
                ContentError(f, "review", "content changed since review; set status back to draft")
            )

    def check_fact(key: str, f: str, where: str) -> None:
        if facts and key not in facts:
            errors.append(ContentError(f, where, f"undeclared fact key {key!r}"))

    def check_leaf(key: str, spec: Any, f: str, where: str) -> None:
        fs = facts.get(key)
        if fs is None:
            return
        ops = spec if isinstance(spec, dict) else {"eq": spec}
        for op, arg in ops.items():
            values = arg if op == "in" else [arg]
            if fs["type"] == "number":
                bad = [v for v in values if isinstance(v, bool) or not isinstance(v, int | float)]
                if bad:
                    errors.append(ContentError(f, where, f"{key}: number fact compared to {bad}"))
                continue
            if op not in ("eq", "in"):
                errors.append(ContentError(f, where, f"{key}: {op!r} needs a number fact"))
                continue
            allowed = ["yes", "no"] if fs["type"] == "tristate" else fs.get("values", [])
            bad = [v for v in values if v not in allowed]
            if bad:
                errors.append(
                    ContentError(
                        f, where, f"{key}: value(s) {bad} not in {allowed} (never match on unknown)"
                    )
                )

    def check_condition(cond: Any, f: str, where: str) -> None:
        if not isinstance(cond, dict):
            return
        for key, spec in cond.items():
            if key in ("all", "any"):
                for sub in spec:
                    check_condition(sub, f, where)
            elif key == "not":
                check_condition(spec, f, where)
            else:
                check_fact(key, f, where)
                check_leaf(key, spec, f, where)

    # --- danger signs ---------------------------------------------------------------------
    ds_path = root / "rules" / "danger_signs.yaml"
    if ds_path.exists():
        f = _rel(ds_path, root)
        data = load_yaml(ds_path)
        errs = schema_errors(data, "danger_signs", f)
        errors += errs
        if not errs:
            check_review(data, f)
            seen: set[str] = set()
            for i, sign in enumerate(data["signs"]):
                where = f"signs/{i}"
                if sign["id"] in seen:
                    errors.append(ContentError(f, where, f"duplicate sign id {sign['id']!r}"))
                seen.add(sign["id"])
                check_fact(sign["fact"], f, where)
                if facts.get(sign["fact"], {}).get("type") not in (None, "tristate"):
                    errors.append(ContentError(f, where, "danger-sign fact must be tristate"))
                for j, src in enumerate(sign["sources"]):
                    check_source(src, f, f"{where}/sources/{j}")

    # --- pathways -------------------------------------------------------------------------
    pathway_ids: set[str] = set()
    for path in sorted((root / "rules" / "pathways").glob("*.yaml")):
        f = _rel(path, root)
        data = load_yaml(path)
        errs = schema_errors(data, "pathway", f)
        errors += errs
        if errs:
            continue
        if data["id"] in pathway_ids:
            errors.append(ContentError(f, "id", f"duplicate pathway id {data['id']!r}"))
        pathway_ids.add(data["id"])
        check_review(data, f)
        for ref in data["sources"]:
            check_ref(ref, f, "sources")
        check_condition(data["applies_when"], f, "applies_when")
        for i, q in enumerate(data["questions"]):
            check_fact(q["fact"], f, f"questions/{i}")
            if "ask_when" in q:
                check_condition(q["ask_when"], f, f"questions/{i}/ask_when")
        rule_ids: set[str] = set()
        for section in ("danger_signs", "rules"):
            for i, item in enumerate(data[section]):
                where = f"{section}/{i}"
                if item["id"] in rule_ids:
                    errors.append(ContentError(f, where, f"duplicate id {item['id']!r}"))
                rule_ids.add(item["id"])
                check_condition(item["when"], f, f"{where}/when")
                check_source(item["source"], f, f"{where}/source")
        if data["low_care"] is not None:
            check_condition(data["low_care"]["when"], f, "low_care/when")
            check_source(data["low_care"]["source"], f, "low_care/source")
        askable = {q["fact"] for q in data["questions"]} | {
            k for k, spec in facts.items() if spec["group"] == "person"
        }
        decisive = [*data["danger_signs"], *data["rules"]]
        if data["low_care"] is not None:
            decisive.append(data["low_care"])
        for item in decisive:
            for key in condition_fact_keys(item["when"]):
                if facts and key not in askable:
                    errors.append(
                        ContentError(
                            f, item["id"], f"{key!r} is used but never asked in this pathway"
                        )
                    )

    # --- schemes --------------------------------------------------------------------------
    for path in sorted((root / "knowledge" / "schemes").glob("*.yaml")):
        f = _rel(path, root)
        data = load_yaml(path)
        errs = schema_errors(data, "scheme", f)
        errors += errs
        if errs:
            continue
        for i, src in enumerate(data["sources"]):
            check_source(src, f, f"sources/{i}")
        for i, amount in enumerate(data["amounts"]):
            check_source(amount["source"], f, f"amounts/{i}/source")
        for i, sig in enumerate(data["eligibility_signals"]):
            check_fact(sig["fact"], f, f"eligibility_signals/{i}")
        if "applies_to" in data:
            check_condition(data["applies_to"], f, "applies_to")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    errors = validate_content(args.root)
    for e in errors:
        print(e, file=sys.stderr)
    print(f"content validation: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
