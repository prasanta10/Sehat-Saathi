import pytest

from app.domain.facts import (
    Fact,
    FactOrigin,
    FactSpec,
    FactStatus,
    FactType,
    I18nText,
    InvalidFactValue,
    confirmed_values,
    normalise_value,
)

L = I18nText(en="x", hi="x")
TRI = FactSpec(key="t", type=FactType.tristate, label=L, group="symptom")
NUM = FactSpec(
    key="n",
    type=FactType.number,
    label=L,
    group="symptom",
    unit="days",
    min=0,
    max=100,
    integer=True,
)
ENUM = FactSpec(key="e", type=FactType.enum, label=L, group="history", values=("a", "b"))


@pytest.mark.parametrize(
    ("spec", "value", "out"),
    [
        (TRI, "yes", "yes"),
        (TRI, "no", "no"),
        (TRI, "unknown", None),
        (TRI, None, None),
        (NUM, 14, 14),
        (NUM, 14.0, 14),
        (NUM, 0, 0),
        (ENUM, "b", "b"),
    ],
)
def test_valid_values(spec, value, out) -> None:  # type: ignore[no-untyped-def]
    assert normalise_value(spec, value) == out


@pytest.mark.parametrize(
    ("spec", "value"),
    [
        (TRI, True),
        (TRI, "maybe"),
        (NUM, "14"),
        (NUM, True),
        (NUM, -1),
        (NUM, 101),
        (NUM, 2.5),
        (ENUM, "c"),
    ],
)
def test_invalid_values(spec, value) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(InvalidFactValue):
        normalise_value(spec, value)


def test_only_confirmed_known_values_reach_the_engine() -> None:
    facts = [
        Fact(key="a", value="yes", status=FactStatus.confirmed),
        Fact(key="b", value="yes", status=FactStatus.suggested, origin=FactOrigin.extracted),
        Fact(key="c", value="yes", status=FactStatus.rejected),
        Fact(key="d", value=None, status=FactStatus.unknown),
        Fact(key="e", value="unknown", status=FactStatus.confirmed),
        Fact(key="f", value=0, status=FactStatus.confirmed),
    ]
    assert confirmed_values(facts) == {"a": "yes", "f": 0}
