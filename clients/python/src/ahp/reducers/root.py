"""Pure reducer for the root channel (``ahp-root://``)."""

from __future__ import annotations

from ahp.types import (
    RootActiveSessionsChangedAction,
    RootAgentsChangedAction,
    RootConfigChangedAction,
    RootState,
    RootTerminalsChangedAction,
    StateAction,
)


def root_reducer(state: RootState, action: StateAction) -> RootState:
    """Apply ``action`` to ``state``, returning a new :class:`RootState`."""
    if isinstance(action, RootAgentsChangedAction):
        return state.model_copy(update={"agents": list(action.agents)})

    if isinstance(action, RootActiveSessionsChangedAction):
        return state.model_copy(update={"active_sessions": action.active_sessions})

    if isinstance(action, RootTerminalsChangedAction):
        return state.model_copy(update={"terminals": list(action.terminals)})

    if isinstance(action, RootConfigChangedAction):
        if action.replace:
            return state.model_copy(update={"config": action.config})
        merged = {**(state.config or {}), **action.config}
        return state.model_copy(update={"config": merged})

    return state
