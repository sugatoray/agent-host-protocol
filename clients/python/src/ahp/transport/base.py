"""Transport abstraction: the pluggable boundary between AhpClient and the wire.

Modeled as a structural type (``typing.Protocol``) rather than an ABC, so any
object satisfying the shape — a real WebSocket wrapper, the in-memory pair used
in tests, a future stdio transport — can be used without inheriting from
anything. This mirrors the ``Transport`` trait (Rust) / interface (Go) pattern
used by the other AHP clients.

Every transport carries pre-framed, complete JSON-RPC text messages: framing
(WebSocket message boundaries, line-delimited JSON over stdio, etc.) is the
transport's job, not the client's.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class TransportError(Exception):
    """Base class for all transport-level errors."""


class TransportClosedError(TransportError):
    """Raised by ``receive()`` when the connection has closed (cleanly or not,
    locally or by the peer) and by ``send()`` when called on an already-closed
    transport.
    """


@runtime_checkable
class Transport(Protocol):
    """Structural interface every AHP transport must satisfy.

    Implementations: :class:`ahp.transport.memory.InMemoryTransport` (testing),
    :class:`ahp.transport.websocket.WebSocketTransport` (production).
    """

    async def send(self, message: str) -> None:
        """Send one complete, pre-serialized JSON-RPC message.

        Raises :class:`TransportClosedError` if the transport is already closed.
        """
        ...

    async def receive(self) -> str:
        """Wait for and return the next complete, pre-serialized JSON-RPC
        message from the peer.

        Raises :class:`TransportClosedError` when the connection has closed and
        no further messages will arrive.
        """
        ...

    async def close(self) -> None:
        """Close the transport. Idempotent — closing an already-closed
        transport must not raise.
        """
        ...

    @property
    def closed(self) -> bool:
        """Whether the transport has been closed."""
        ...
