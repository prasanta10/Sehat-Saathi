"""Invariant 8: Clinical content is never invented.

Every pathway and the danger-sign list are draft until a named clinician signs off on the exact
content (hash). Draft status propagates to every triage result so the UI shows the banner.
"""

from app.config import REPO_ROOT
from app.content.review import content_hash
from app.content.yamlio import load_yaml
from app.rules.loader import RuleSet
from app.rules.schema import ReviewStatus
from tests.invariants.helpers import triage


def test_reviewed_content_names_reviewer_and_matches_hash() -> None:
    files = [
        REPO_ROOT / "rules" / "danger_signs.yaml",
        *(REPO_ROOT / "rules" / "pathways").glob("*.yaml"),
    ]
    for path in files:
        data = load_yaml(path)
        review = data["review"]
        if review["status"] == "draft":
            continue
        assert review["reviewer"], path.name
        assert review["reviewed_on"], path.name
        assert review["content_hash"] == content_hash(data), path.name


def test_draft_status_reaches_every_result(ruleset: RuleSet) -> None:
    for pid, p in ruleset.pathways.items():
        r = triage(ruleset, {}, pid)
        if (
            p.review.status is ReviewStatus.draft
            or ruleset.danger_signs.review.status is ReviewStatus.draft
        ):
            assert r.review_status is ReviewStatus.draft
