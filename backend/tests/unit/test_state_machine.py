import itertools

import pytest

from app.domain.state_machine import (
    REOPEN_ON_EDIT_FROM,
    InvalidTransition,
    can_transition,
    transition,
)
from app.domain.state_machine import (
    EncounterState as S,
)


def test_happy_path() -> None:
    path = [
        S.draft,
        S.captured,
        S.extracted,
        S.clarifying,
        S.confirmed,
        S.triaged,
        S.plan_ready,
        S.handed_off,
        S.closed,
    ]
    for a, b in itertools.pairwise(path):
        assert transition(a, b) is b


def test_manual_path_skips_capture() -> None:
    assert can_transition(S.draft, S.clarifying)


@pytest.mark.parametrize("state", [s for s in S if s not in (S.closed, S.follow_up_due)])
def test_emergency_reachable_from_every_open_state(state: S) -> None:
    assert can_transition(state, S.emergency)


@pytest.mark.parametrize("state", [S.draft, S.captured, S.extracted, S.clarifying])
def test_cannot_triage_without_confirming(state: S) -> None:
    assert not can_transition(state, S.triaged)
    with pytest.raises(InvalidTransition):
        transition(state, S.triaged)


def test_editing_confirmed_facts_reopens_clarification() -> None:
    for state in REOPEN_ON_EDIT_FROM:
        assert can_transition(state, S.clarifying)
