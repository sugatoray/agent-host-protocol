"""Pure reducer for a terminal channel within a session."""

from __future__ import annotations

from ahp.types import (
    StateAction,
    TerminalClearedAction,
    TerminalCwdChangedAction,
    TerminalDataAction,
    TerminalExitedAction,
    TerminalResizedAction,
    TerminalState,
    TerminalTitleChangedAction,
)


def terminal_reducer(state: TerminalState, action: StateAction) -> TerminalState:
    """Apply ``action`` to ``state``, returning a new :class:`TerminalState`."""
    if isinstance(action, TerminalDataAction):
        return state.model_copy(
            update={"content": [*state.content, {"type": "data", "data": action.data}]}
        )

    if isinstance(action, TerminalExitedAction):
        return state.model_copy(update={"exit_code": action.exit_code})

    if isinstance(action, TerminalTitleChangedAction):
        return state.model_copy(update={"title": action.title})

    if isinstance(action, TerminalCwdChangedAction):
        return state.model_copy(update={"cwd": action.cwd})

    if isinstance(action, TerminalResizedAction):
        return state.model_copy(update={"cols": action.cols, "rows": action.rows})

    if isinstance(action, TerminalClearedAction):
        return state.model_copy(update={"content": []})

    return state
