import pytest

from app.ai.parsing import parse_duration_days, parse_number, parse_yes_no


@pytest.mark.parametrize(
    ("text", "days", "approx"),
    [
        ("teen hafte", 21, False),
        ("teen hafte se", 21, False),
        ("2 weeks", 14, False),
        ("two weeks", 14, False),
        ("10 din", 10, False),
        ("das din se", 10, False),
        ("तीन हफ़्ते", 21, False),
        ("तीन हफ्ते से खांसी", 21, False),
        ("१४ दिन", 14, False),
        ("ek mahina", 30, True),
        ("a week", 7, False),
        ("do saal", 730, True),
        ("dedh hafta", 10.5, True),
        ("13 days", 13, False),
    ],
)
def test_durations(text: str, days: float, approx: bool) -> None:
    r = parse_duration_days(text)
    assert r is not None and r.value == days and r.approximate is approx


@pytest.mark.parametrize(
    "text",
    [
        "kuch din",
        "bahut din se",
        "do ya teen din",
        "2-3 din",
        "kal se",
        "",
        "hafte se",
        "teen din aur do hafte",
    ],
)
def test_ambiguous_durations_are_unknown(text: str) -> None:
    assert parse_duration_days(text) is None


@pytest.mark.parametrize(("text", "n"), [("62", 62), ("saat", 7), ("उम्र 45", 45)])
def test_numbers(text: str, n: float) -> None:
    assert parse_number(text) == n


@pytest.mark.parametrize(
    ("text", "v"),
    [
        ("haan", "yes"),
        ("ji haan", "yes"),
        ("nahi", "no"),
        ("नहीं", "no"),
        ("pata nahi", "unknown"),
        ("मालूम नहीं", "unknown"),
        ("hmm", None),
        ("bukhar nahi hai", "no"),
    ],
)
def test_yes_no(text: str, v: str | None) -> None:
    assert parse_yes_no(text) == v


@pytest.mark.parametrize(
    ("text", "days"),
    [("पाच दिन", 5), ("पाँच दिन", 5), ("पांच दिन", 5), ("दो हफ्ते", 14), ("दो हफ़्ते", 14)],
)
def test_durations_tolerate_spelling_marks(text: str, days: int) -> None:
    r = parse_duration_days(text)
    assert r is not None and r.value == days


def test_negation_survives_loose_spelling() -> None:
    assert parse_yes_no("नही") == "no" and parse_yes_no("नहीं") == "no"
