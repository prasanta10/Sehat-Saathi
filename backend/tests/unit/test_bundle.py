from app.config import REPO_ROOT
from app.content.bundle import BUNDLE_PATH, build_bundle, render
from app.rules.loader import load_ruleset


def test_frontend_bundle_is_up_to_date() -> None:
    expected = render(build_bundle(load_ruleset(REPO_ROOT), REPO_ROOT))
    assert BUNDLE_PATH.read_text(encoding="utf-8") == expected, "run `make bundle`"
