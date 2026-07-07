"""Pure reducer for a terminal channel within a session (``ahp-terminal:/<uuid>``)."""

from __future__ import annotations

from ahp.types import (
    StateAction,
    TerminalExitedAction,
    TerminalOutputAction,
    TerminalState,
    TerminalStatus,
)


def terminal_reducer(state: TerminalState, action: StateAction) -> TerminalState:
    """Apply ``action`` to ``state``, returning a new :class:`TerminalState`.

    As with the other channel reducers, actions outside the ``terminal/*``
    family are a no-op.
    """
    if isinstance(action, TerminalOutputAction):
        return state.model_copy(update={"buffer": state.buffer + action.data})

    if isinstance(action, TerminalExitedAction):
        return state.model_copy(
            update={"status": TerminalStatus.EXITED, "exit_code": action.exit_code}
        )

    return state
