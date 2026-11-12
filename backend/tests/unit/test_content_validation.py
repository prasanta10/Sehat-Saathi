"""Content CI must reject unsafe or incomplete content. Each test breaks a copy of the fixture."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.content.validate import validate_content
from app.content.yamlio import load_yaml
from tests.conftest import FIXTURE_ROOT

PATHWAY = "rules/pathways/fx_with_low.yaml"
REGISTRY = "rules/fact_registry.yaml"
DANGER = "rules/danger_signs.yaml"


def broken(tmp_path: Path, rel: str, mutate: Callable[[Any], None]) -> list[str]:
    root = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, root)
    data = load_yaml(root / rel)
    mutate(data)
    (root / rel).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    return [str(e) for e in validate_content(root)]


def test_fixture_itself_is_valid() -> None:
    assert validate_content(FIXTURE_ROOT) == []


def test_rejects_rule_without_source(tmp_path: Path) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["rules"][0].pop("source"))
    assert any("'source' is a required property" in e for e in errors)


def test_rejects_rule_citing_unknown_reference(tmp_path: Path) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["rules"][0]["source"].update(ref="made_up_doc"))
    assert any("unknown reference 'made_up_doc'" in e for e in errors)


def test_rejects_danger_sign_without_source(tmp_path: Path) -> None:
    errors = broken(tmp_path, DANGER, lambda d: d["signs"][0].update(sources=[]))
    assert any("signs/0/sources" in e for e in errors)


@pytest.mark.parametrize("lang", ["hi", "en"])
def test_rejects_missing_translation(tmp_path: Path, lang: str) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["rules"][0]["rationale"].pop(lang))
    assert any(f"'{lang}' is a required property" in e for e in errors)


def test_rejects_empty_translation(tmp_path: Path) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["questions"][0]["ask"].update(hi=""))
    assert any("questions/0/ask/hi" in e for e in errors)


def test_rejects_undeclared_fact(tmp_path: Path) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["rules"][0].update(when={"made_up_fact": "yes"}))
    assert any("undeclared fact key 'made_up_fact'" in e for e in errors)


def test_rejects_matching_on_unknown(tmp_path: Path) -> None:
    errors = broken(
        tmp_path, PATHWAY, lambda d: d["low_care"].update(when={"fx_optional": "unknown"})
    )
    assert any("never match on unknown" in e for e in errors)


def test_rejects_numeric_operator_on_tristate(tmp_path: Path) -> None:
    errors = broken(
        tmp_path, PATHWAY, lambda d: d["rules"][0].update(when={"fx_marker_high": {"gte": 1}})
    )
    assert any("needs a number fact" in e for e in errors)


def test_rejects_rule_on_fact_that_is_never_asked(tmp_path: Path) -> None:
    def mutate(d: Any) -> None:
        d["questions"] = [q for q in d["questions"] if q["fact"] != "fx_marker_high"]

    errors = broken(tmp_path, PATHWAY, mutate)
    assert any("'fx_marker_high' is used but never asked" in e for e in errors)


def test_rejects_low_rule_level_in_rules_list(tmp_path: Path) -> None:
    # LOW only comes from an explicit low_care block, never from an ordinary rule.
    errors = broken(tmp_path, PATHWAY, lambda d: d["rules"][0].update(level="LOW"))
    assert any("rules/0/level" in e for e in errors)


def test_rejects_reviewed_status_without_reviewer(tmp_path: Path) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["review"].update(status="clinician_reviewed"))
    assert any("review" in e for e in errors)


def test_rejects_unsourced_scheme_amount(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, root)
    scheme = {
        "id": "fx_scheme",
        "name": {"en": "Fixture", "hi": "परीक्षण"},
        "jurisdiction": "national",
        "states_excluded": [],
        "care_types": [],
        "not_for": [],
        "eligibility_signals": [],
        "may_cover": {"en": [], "hi": []},
        "does_not_cover": {"en": [], "hi": []},
        "documents": [],
        "where_to_confirm": {"en": "x", "hi": "x"},
        "amounts": [{"text": {"en": "Rs 1", "hi": "₹1"}}],
        "sources": [{"ref": "fixture_ref", "locator": "x"}],
        "review": {"status": "draft", "verified_on": None},
    }
    (root / "knowledge/schemes").mkdir(parents=True, exist_ok=True)  # empty dirs are not in git
    (root / "knowledge/schemes/fx_scheme.yaml").write_text(
        yaml.safe_dump(scheme, allow_unicode=True)
    )
    errors = [str(e) for e in validate_content(root)]
    assert any("amounts/0" in e and "'source' is a required property" in e for e in errors)


def test_yes_and_no_stay_strings() -> None:
    from app.content.yamlio import loads_yaml

    assert loads_yaml("a: yes\nb: no\nc: true\nd: on") == {
        "a": "yes",
        "b": "no",
        "c": True,
        "d": "on",
    }


def test_rejects_locator_without_verbatim_excerpt(tmp_path: Path) -> None:
    errors = broken(tmp_path, PATHWAY, lambda d: d["rules"][0]["source"].update(locator="p. 999"))
    assert any("has no verbatim excerpt" in e for e in errors)


def test_edit_after_review_is_rejected(tmp_path: Path) -> None:
    from app.content.review import content_hash

    def review_then_edit(d: Any) -> None:
        d["review"] = {
            "status": "clinician_reviewed",
            "reviewer": "Dr Fixture",
            "reviewed_on": "2026-01-01",
            "content_hash": content_hash(d),
        }
        d["rules"][0]["when"] = {"fx_marker_high": "no"}

    errors = broken(tmp_path, PATHWAY, review_then_edit)
    assert any("content changed since review" in e for e in errors)


def test_review_with_matching_hash_is_accepted(tmp_path: Path) -> None:
    from app.content.review import content_hash

    def review(d: Any) -> None:
        d["review"] = {
            "status": "clinician_reviewed",
            "reviewer": "Dr Fixture",
            "reviewed_on": "2026-01-01",
            "content_hash": content_hash(d),
        }

    assert broken(tmp_path, PATHWAY, review) == []


def test_excerpt_must_appear_in_stored_source_text(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, root)
    (root / "knowledge/references/files").mkdir()
    (root / "knowledge/references/files/fixture_ref.txt").write_text(
        "Header\n  Cough for   2 weeks or more    | other column\n  should be referred\n"
    )
    ref = load_yaml(root / "knowledge/references/fixture_ref.yaml")
    ref["local_copy"] = "knowledge/references/files/fixture_ref.txt"
    ref["excerpts"][0]["text"] = "Cough for 2 weeks or more … should be referred"
    (root / "knowledge/references/fixture_ref.yaml").write_text(
        yaml.safe_dump(ref, allow_unicode=True)
    )
    assert validate_content(root) == []
    for tampered in ["Cough for 3 weeks or more", "should be referred … Cough for 2 weeks"]:
        ref["excerpts"][0]["text"] = tampered
        (root / "knowledge/references/fixture_ref.yaml").write_text(
            yaml.safe_dump(ref, allow_unicode=True)
        )
        assert any("excerpt not found verbatim" in str(e) for e in validate_content(root)), tampered


def test_normalisation_handles_pdf_ligatures() -> None:
    from app.content.validate import excerpt_found, normalise_text

    assert excerpt_found("significant weight", normalise_text("signicant  weight"))
    assert excerpt_found("Convulsions or fits", normalise_text("Convulsions or ﬁts"))
