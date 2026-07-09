"""Pure reducer for a resource-watch channel.

The reducer is a trivial pass-through: resourceWatch/changed events are
ephemeral (the state tracks only the watch descriptor, set at subscribe time).
"""

from __future__ import annotations

from ahp.types import ResourceWatchState, StateAction


def resource_watch_reducer(state: ResourceWatchState, action: StateAction) -> ResourceWatchState:
    """Apply ``action`` to ``state``, returning a new :class:`ResourceWatchState`.

    Per canonical types/channels-resource-watch/reducer.ts, no action
    mutates the watch descriptor state — change events are delivered
    ephemerally and not retained.
    """
    return state
