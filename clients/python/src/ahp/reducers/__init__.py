"""Pure reducers — one per AHP channel family.

Every function here has the shape ``(state, action) -> new_state``: no I/O, no
mutation of the input state, no side effects. This is what makes write-ahead
reconciliation in ``ahp.client.AhpClient`` (not yet implemented) safe to reason
about: the client can apply a reducer speculatively and later re-apply it
against a corrected state without any hidden coupling.
"""

from .annotations import annotations_reducer
from .changeset import changeset_reducer
from .chat import chat_reducer
from .resource_watch import resource_watch_reducer
from .root import root_reducer
from .session import session_reducer
from .terminal import terminal_reducer

__all__ = [
    "annotations_reducer",
    "changeset_reducer",
    "chat_reducer",
    "resource_watch_reducer",
    "root_reducer",
    "session_reducer",
    "terminal_reducer",
]
