"""Tests for ahp.reducers.changeset.changeset_reducer."""

from __future__ import annotations

from ahp.reducers.changeset import changeset_reducer
from ahp.types import (
    ChangesetClearedAction,
    ChangesetFileRemovedAction,
    ChangesetFileSetAction,
    ChangesetOperationStatusChangedAction,
    ChangesetOperationsChangedAction,
    ChangesetState,
    ChangesetStatusChangedAction,
    SessionTitleChangedAction,
)


def make_state(**overrides) -> ChangesetState:
    defaults: dict = dict(status="computing", files=[], operations=None)
    defaults.update(overrides)
    return ChangesetState(**defaults)


def test_status_changed():
    state = make_state(status="computing")
    action = ChangesetStatusChangedAction(status="ready")

    new_state = changeset_reducer(state, action)

    assert new_state.status == "ready"
    assert state.status == "computing"  # input not mutated


def test_file_set_adds_new_file():
    state = make_state(files=[])
    action = ChangesetFileSetAction(file={"id": "f1", "path": "src/foo.py"})

    new_state = changeset_reducer(state, action)

    assert len(new_state.files) == 1
    assert new_state.files[0]["id"] == "f1"


def test_file_set_updates_existing_file():
    state = make_state(files=[{"id": "f1", "path": "old.py"}])
    action = ChangesetFileSetAction(file={"id": "f1", "path": "new.py"})

    new_state = changeset_reducer(state, action)

    assert len(new_state.files) == 1
    assert new_state.files[0]["path"] == "new.py"


def test_file_removed_drops_by_id():
    state = make_state(files=[{"id": "f1"}, {"id": "f2"}])
    action = ChangesetFileRemovedAction(id="f1")

    new_state = changeset_reducer(state, action)

    assert len(new_state.files) == 1
    assert new_state.files[0]["id"] == "f2"


def test_operations_changed():
    state = make_state()
    ops = [{"id": "op1", "type": "apply"}]
    action = ChangesetOperationsChangedAction(operations=ops)

    new_state = changeset_reducer(state, action)

    assert new_state.operations == ops


def test_operation_status_changed():
    state = make_state(operations=[{"id": "op1", "status": "pending"}])
    action = ChangesetOperationStatusChangedAction(operation_id="op1", status="applied")

    new_state = changeset_reducer(state, action)

    assert new_state.operations[0]["status"] == "applied"


def test_cleared_resets_files_and_operations():
    state = make_state(files=[{"id": "f1"}], operations=[{"id": "op1"}])
    action = ChangesetClearedAction()

    new_state = changeset_reducer(state, action)

    assert new_state.files == []
    assert new_state.operations is None


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionTitleChangedAction(title="other")

    new_state = changeset_reducer(state, foreign_action)

    assert new_state == state
