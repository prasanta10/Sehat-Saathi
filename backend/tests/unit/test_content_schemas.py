"""The JSON Schemas themselves are valid and the repository content passes them."""

import json

import pytest
from jsonschema import Draft202012Validator

from app.config import REPO_ROOT
from app.content.validate import SCHEMA_DIR, schema_errors, validate_content


@pytest.mark.parametrize("path", sorted(SCHEMA_DIR.glob("*.schema.json")), ids=lambda p: p.name)
def test_schema_is_valid(path) -> None:  # type: ignore[no-untyped-def]
    Draft202012Validator.check_schema(json.loads(path.read_text()))


def test_repository_content_is_valid() -> None:
    errors = validate_content(REPO_ROOT)
    assert errors == [], "\n".join(map(str, errors))


def test_i18n_text_requires_both_languages() -> None:
    reg = {
        "version": "0.1.0",
        "facts": {"x": {"type": "tristate", "group": "symptom", "label": {"en": "X"}}},
    }
    errors = schema_errors(reg, "fact_registry", "t")
    assert any("'hi' is a required property" in e.message for e in errors)
