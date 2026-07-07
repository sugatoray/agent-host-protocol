"""Tests for ahp.reducers.changeset.changeset_reducer."""

from __future__ import annotations

from ahp.reducers.changeset import changeset_reducer
from ahp.types import (
    ChangesetOperationStatus,
    ChangesetOperationStatusChangedAction,
    ChangesetState,
    SessionDisposedAction,
)


def make_state(**overrides) -> ChangesetState:
    defaults = dict(
        uri="ahp-changeset:/1",
        session_uri="ahp-session:/abc",
        operation_status=ChangesetOperationStatus.PENDING,
    )
    defaults.update(overrides)
    return ChangesetState(**defaults)


def test_operation_status_changed_updates_status():
    state = make_state(operation_status=ChangesetOperationStatus.PENDING)
    action = ChangesetOperationStatusChangedAction(status=ChangesetOperationStatus.APPLIED)

    new_state = changeset_reducer(state, action)

    assert new_state.operation_status == ChangesetOperationStatus.APPLIED


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionDisposedAction()

    new_state = changeset_reducer(state, foreign_action)

    assert new_state == state
