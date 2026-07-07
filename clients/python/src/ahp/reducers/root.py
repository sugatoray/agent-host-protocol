"""Pure reducer for the root channel (``agenthost:/root``).

Mirrors the ``rootReducer`` in the TypeScript/Rust clients: a plain function of
``(state, action) -> new_state`` with no I/O, no mutation of its inputs, and no
side effects — safe to call from anywhere (including tests) without a running
client or transport.
"""

from __future__ import annotations

from ahp.types import (
    RootAgentsChangedAction,
    RootSessionAddedAction,
    RootSessionRemovedAction,
    RootState,
    StateAction,
)


def root_reducer(state: RootState, action: StateAction) -> RootState:
    """Apply ``action`` to ``state``, returning a new :class:`RootState`.

    Actions that don't belong to the root family (i.e. anything other than the
    three ``root/*`` variants) are a no-op — the reducer returns ``state``
    unchanged rather than raising, since a single client may route the same
    dispatch loop's fallback handling through every channel's reducer.
    """
    if isinstance(action, RootAgentsChangedAction):
        return state.model_copy(update={"agents": list(action.agents)})

    if isinstance(action, RootSessionAddedAction):
        if action.session_uri in state.session_uris:
            return state
        return state.model_copy(
            update={"session_uris": [*state.session_uris, action.session_uri]}
        )

    if isinstance(action, RootSessionRemovedAction):
        if action.session_uri not in state.session_uris:
            return state
        return state.model_copy(
            update={
                "session_uris": [
                    uri for uri in state.session_uris if uri != action.session_uri
                ]
            }
        )

    return state
