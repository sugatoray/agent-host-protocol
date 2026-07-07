"""Pure reducer for an individual session channel (``ahp-session:/<uuid>``)."""

from __future__ import annotations

from ahp.types import (
    SessionChatAddedAction,
    SessionDisposedAction,
    SessionState,
    SessionTerminalAddedAction,
    SessionTitleChangedAction,
    StateAction,
)


def session_reducer(state: SessionState, action: StateAction) -> SessionState:
    """Apply ``action`` to ``state``, returning a new :class:`SessionState`.

    As with :func:`ahp.reducers.root.root_reducer`, actions outside the
    ``session/*`` family are a no-op.
    """
    if isinstance(action, SessionTitleChangedAction):
        return state.model_copy(update={"title": action.title})

    if isinstance(action, SessionChatAddedAction):
        return state.model_copy(
            update={"chat_uris": [*state.chat_uris, action.chat_uri]}
        )

    if isinstance(action, SessionTerminalAddedAction):
        return state.model_copy(
            update={"terminal_uris": [*state.terminal_uris, action.terminal_uri]}
        )

    if isinstance(action, SessionDisposedAction):
        return state.model_copy(update={"disposed": True})

    return state
