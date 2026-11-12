import pytest

from app.rules.conditions import evaluate, referenced_facts, unknown_facts


@pytest.mark.parametrize(
    ("cond", "facts", "expected"),
    [
        ({"a": "yes"}, {"a": "yes"}, True),
        ({"a": "yes"}, {"a": "no"}, False),
        ({"a": "yes"}, {}, None),
        ({"n": {"gte": 14}}, {"n": 14}, True),
        ({"n": {"gte": 14}}, {"n": 13}, False),
        ({"n": {"gt": 14}}, {"n": 14}, False),
        ({"n": {"lt": 3}}, {"n": 2.5}, True),
        ({"n": {"lte": 3}}, {"n": 3}, True),
        ({"n": {"gte": 2, "lt": 5}}, {"n": 5}, False),
        ({"k": {"in": ["x", "y"]}}, {"k": "y"}, True),
        ({"k": {"eq": "x"}}, {"k": "y"}, False),
        # implicit all
        ({"a": "yes", "b": "yes"}, {"a": "yes"}, None),
        ({"a": "yes", "b": "yes"}, {"a": "no"}, False),
        # all / any / not with unknowns
        ({"all": [{"a": "yes"}, {"b": "yes"}]}, {"a": "yes", "b": "yes"}, True),
        ({"all": [{"a": "yes"}, {"b": "yes"}]}, {"b": "no"}, False),
        ({"any": [{"a": "yes"}, {"b": "yes"}]}, {"b": "yes"}, True),
        ({"any": [{"a": "yes"}, {"b": "yes"}]}, {"b": "no"}, None),
        ({"any": [{"a": "yes"}, {"b": "yes"}]}, {"a": "no", "b": "no"}, False),
        ({"not": {"a": "yes"}}, {"a": "no"}, True),
        ({"not": {"a": "yes"}}, {}, None),
    ],
)
def test_three_valued_evaluation(cond, facts, expected) -> None:  # type: ignore[no-untyped-def]
    assert evaluate(cond, facts) is expected


def test_unknown_is_never_false() -> None:
    # A negated condition on an unknown fact must not become true: unknown is not "no".
    assert evaluate({"not": {"danger": "yes"}}, {}) is None


def test_referenced_and_unknown_facts() -> None:
    cond = {"all": [{"a": "yes"}, {"any": [{"b": {"gte": 1}}, {"not": {"c": "no"}}]}], "a": "yes"}
    assert referenced_facts(cond) == ["a", "b", "c"]
    assert unknown_facts(cond, {"b": 2}) == ["a", "c"]


def test_numeric_comparison_on_text_is_an_error() -> None:
    with pytest.raises(TypeError):
        evaluate({"a": {"gte": 1}}, {"a": "yes"})
