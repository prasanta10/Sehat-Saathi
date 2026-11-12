"""Invariant tests run against both the synthetic fixture and the real repository content."""

import pytest

from app.config import REPO_ROOT
from app.rules.loader import RuleSet, load_ruleset
from tests.conftest import FIXTURE_ROOT

ROOTS = {"fixture": FIXTURE_ROOT, "repo": REPO_ROOT}


@pytest.fixture(scope="session", params=sorted(ROOTS))
def ruleset(request: pytest.FixtureRequest) -> RuleSet:
    return load_ruleset(ROOTS[request.param])
