"""Pure reducer for a changeset channel within a session."""

from __future__ import annotations

from ahp.types import (
    ChangesetClearedAction,
    ChangesetContentChangedAction,
    ChangesetFileRemovedAction,
    ChangesetFileSetAction,
    ChangesetOperationsChangedAction,
    ChangesetOperationStatusChangedAction,
    ChangesetState,
    ChangesetStatusChangedAction,
    StateAction,
)


def changeset_reducer(state: ChangesetState, action: StateAction) -> ChangesetState:
    """Apply ``action`` to ``state``, returning a new :class:`ChangesetState`."""
    if isinstance(action, ChangesetStatusChangedAction):
        return state.model_copy(update={"status": action.status})

    if isinstance(action, ChangesetFileSetAction):
        file_id = action.file.get("id")
        existing = [f for f in state.files if f.get("id") != file_id]
        return state.model_copy(update={"files": [*existing, action.file]})

    if isinstance(action, ChangesetFileRemovedAction):
        remaining = [f for f in state.files if f.get("id") != action.file_id]
        return state.model_copy(update={"files": remaining})

    if isinstance(action, ChangesetContentChangedAction):
        update: dict = {"files": action.files}
        if action.operations is not None:
            update["operations"] = action.operations
        if action.error is not None:
            update["error"] = action.error
        else:
            update["error"] = None  # clear stale error
        return state.model_copy(update=update)

    if isinstance(action, ChangesetOperationsChangedAction):
        return state.model_copy(update={"operations": action.operations})

    if isinstance(action, ChangesetOperationStatusChangedAction):
        if not state.operations:
            return state
        ops = [
            {**op, "status": action.status}
            if op.get("id") == action.operation_id else op
            for op in state.operations
        ]
        return state.model_copy(update={"operations": ops})

    if isinstance(action, ChangesetClearedAction):
        return state.model_copy(update={"files": [], "operations": None})

    return state
