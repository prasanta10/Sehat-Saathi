"""Encounter state machine."""

from __future__ import annotations

from enum import StrEnum


class EncounterState(StrEnum):
    draft = "draft"
    captured = "captured"
    extracted = "extracted"
    clarifying = "clarifying"
    confirmed = "confirmed"
    triaged = "triaged"
    plan_ready = "plan_ready"
    handed_off = "handed_off"
    closed = "closed"
    emergency = "emergency"
    follow_up_due = "follow_up_due"


S = EncounterState

_ALLOWED: dict[EncounterState, frozenset[EncounterState]] = {
    S.draft: frozenset({S.captured, S.clarifying}),  # clarifying directly = manual path
    S.captured: frozenset({S.captured, S.extracted, S.clarifying}),  # clarifying = AI degraded
    S.extracted: frozenset({S.clarifying}),
    S.clarifying: frozenset({S.clarifying, S.confirmed}),
    S.confirmed: frozenset({S.triaged, S.clarifying}),
    S.triaged: frozenset({S.plan_ready, S.clarifying, S.closed}),
    S.plan_ready: frozenset({S.handed_off, S.clarifying, S.closed}),
    S.handed_off: frozenset({S.closed}),
    S.closed: frozenset({S.follow_up_due}),
    # After an emergency the visit can still produce a handoff note and be closed.
    S.emergency: frozenset({S.handed_off, S.closed}),
    S.follow_up_due: frozenset({S.closed}),
}

# The emergency state is reachable from every state where the visit is still open.
_EMERGENCY_FROM = frozenset(set(EncounterState) - {S.closed, S.follow_up_due})

# Editing a confirmed fact sends the encounter back to clarifying (triage is invalidated).
REOPEN_ON_EDIT_FROM = frozenset({S.confirmed, S.triaged, S.plan_ready})


class InvalidTransition(ValueError):
    def __init__(self, current: EncounterState, target: EncounterState) -> None:
        super().__init__(f"cannot go from {current} to {target}")
        self.current = current
        self.target = target


def can_transition(current: EncounterState, target: EncounterState) -> bool:
    if target is S.emergency:
        return current in _EMERGENCY_FROM
    return target in _ALLOWED[current]


def transition(current: EncounterState, target: EncounterState) -> EncounterState:
    if not can_transition(current, target):
        raise InvalidTransition(current, target)
    return target
