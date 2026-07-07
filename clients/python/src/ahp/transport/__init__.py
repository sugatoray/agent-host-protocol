"""Pluggable transports for AHP clients.

- :mod:`ahp.transport.base` — the structural ``Transport`` protocol + errors.
- :mod:`ahp.transport.memory` — an in-memory paired transport for tests.
- :mod:`ahp.transport.websocket` — the production WebSocket transport.
"""

from .base import Transport, TransportClosedError, TransportError
from .memory import InMemoryTransport
from .websocket import RawWebSocketLike, WebSocketTransport

__all__ = [
    "Transport",
    "TransportClosedError",
    "TransportError",
    "InMemoryTransport",
    "RawWebSocketLike",
    "WebSocketTransport",
]
