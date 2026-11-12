"""Invariant 7: Every rule and scheme statement has a source in knowledge/references/."""

from app.config import REPO_ROOT
from app.content.validate import validate_content
from app.content.yamlio import load_yaml
from app.rules.loader import RuleSet


def test_repository_content_validates() -> None:
    errors = validate_content(REPO_ROOT)
    assert errors == [], "\n".join(map(str, errors))


def test_every_rule_and_sign_cites_an_excerpt(ruleset: RuleSet) -> None:
    # validate_content (run by load_ruleset) already checks this; assert it explicitly here so the
    # invariant cannot be lost by a refactor of the validator.

    cited = []
    for s in ruleset.danger_signs.signs:
        assert s.sources, s.id
        cited += list(s.sources)
    for p in ruleset.pathways.values():
        assert p.sources, p.id
        for item in [*p.danger_signs, *p.rules]:
            cited.append(item.source)
        if p.low_care:
            cited.append(p.low_care.source)
    assert cited


def test_references_are_official_https_documents() -> None:
    for path in (REPO_ROOT / "knowledge" / "references").glob("*.yaml"):
        ref = load_yaml(path)
        assert ref["url"].startswith("https://"), path.name
        assert ref["excerpts"], path.name
        host = ref["url"].split("/")[2]
        assert host.endswith((".gov.in", ".nic.in", "nhsrcindia.org")), (path.name, host)
