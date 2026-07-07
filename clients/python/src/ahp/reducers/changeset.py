"""Pure reducer for a changeset channel within a session (``ahp-changeset:/<uuid>``)."""

from __future__ import annotations

from ahp.types import (
    ChangesetOperationStatusChangedAction,
    ChangesetState,
    StateAction,
)


def changeset_reducer(state: ChangesetState, action: StateAction) -> ChangesetState:
    """Apply ``action`` to ``state``, returning a new :class:`ChangesetState`.

    As with the other channel reducers, actions outside the ``changeset/*``
    family are a no-op.
    """
    if isinstance(action, ChangesetOperationStatusChangedAction):
        return state.model_copy(update={"operation_status": action.status})

    return state
