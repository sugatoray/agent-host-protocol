"""WebSocket-backed transport.

Wraps an already-connected, duck-typed WebSocket connection object rather than
depending on any particular WebSocket library at the type level: anything
exposing ``async send(str)``, ``async recv() -> str``, and ``async close()``
works — including a real ``websockets`` client connection, or (in tests) a
minimal fake with no real socket at all.

The optional ``websockets`` dependency (``pip install
"agent-host-protocol[websocket]"``) is only imported lazily, inside
:meth:`WebSocketTransport.connect`, so the rest of this module — and its unit
tests — don't require it to be installed.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .base import TransportClosedError


@runtime_checkable
class RawWebSocketLike(Protocol):
    """The minimal shape :class:`WebSocketTransport` expects from whatever
    connection object it wraps.
    """

    async def send(self, message: str) -> None: ...

    async def recv(self) -> str: ...

    async def close(self) -> None: ...


def _default_closed_exception_types() -> tuple[type[Exception], ...]:
    """Best-effort default for ``closed_exception_types``: if the real
    ``websockets`` package happens to be installed, translate its
    ``ConnectionClosed`` family automatically. If not, callers using a
    different WebSocket library (or a fake, in tests) should pass their own
    exception type(s) explicitly via the constructor.
    """
    try:
        import websockets.exceptions as _wse
    except ImportError:
        return ()
    return (_wse.ConnectionClosed,)


class WebSocketTransport:
    """Adapts a connected WebSocket-like object to the :class:`ahp.transport.base.Transport`
    protocol.
    """

    def __init__(
        self,
        connection: RawWebSocketLike,
        *,
        closed_exception_types: tuple[type[Exception], ...] | None = None,
    ) -> None:
        self._connection = connection
        self._closed = False
        self._closed_exception_types = (
            closed_exception_types
            if closed_exception_types is not None
            else _default_closed_exception_types()
        )

    async def send(self, message: str) -> None:
        if self._closed:
            raise TransportClosedError("cannot send on a closed transport")
        try:
            await self._connection.send(message)
        except self._closed_exception_types as exc:
            self._closed = True
            raise TransportClosedError("connection closed while sending") from exc

    async def receive(self) -> str:
        if self._closed:
            raise TransportClosedError("transport already closed")
        try:
            return await self._connection.recv()
        except self._closed_exception_types as exc:
            self._closed = True
            raise TransportClosedError("connection closed while receiving") from exc

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._connection.close()

    @property
    def closed(self) -> bool:
        return self._closed

    @classmethod
    async def connect(cls, uri: str, **kwargs: Any) -> "WebSocketTransport":
        """Open a new WebSocket connection to ``uri`` and wrap it.

        Requires the optional ``websockets`` dependency:
        ``pip install "agent-host-protocol[websocket]"``.
        """
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError(
                "WebSocketTransport.connect() requires the 'websockets' package. "
                'Install it with: pip install "agent-host-protocol[websocket]"'
            ) from exc

        connection = await websockets.connect(uri, **kwargs)
        return cls(
            connection,
            closed_exception_types=(websockets.exceptions.ConnectionClosed,),
        )
