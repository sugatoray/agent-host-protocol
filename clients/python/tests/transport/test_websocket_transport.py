"""Tests for ahp.transport.websocket.WebSocketTransport.

These exercise the wrapper logic (closed-state tracking, exception
translation) against a minimal fake connection object, so they don't require
the optional ``websockets`` dependency to be installed. ``WebSocketTransport.connect()``
(the part that actually opens a real socket via the ``websockets`` library) is
integration-level and deliberately out of scope here — see
``test_connect_without_websockets_installed_raises_helpful_error`` for the one
thing about it we *can* test without the dependency.
"""

from __future__ import annotations

import pytest

from ahp.transport.base import TransportClosedError
from ahp.transport.websocket import WebSocketTransport


class FakeConnectionClosed(Exception):
    """Stands in for websockets.exceptions.ConnectionClosed in these tests."""


class FakeRawConnection:
    """Minimal fake satisfying the duck-typed shape WebSocketTransport expects
    from a real ``websockets`` connection: async send/recv/close.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed_by_test = False
        self._inbox: list[str] = []
        self.close_called = False

    def queue_incoming(self, message: str) -> None:
        self._inbox.append(message)

    async def send(self, message: str) -> None:
        if self.closed_by_test:
            raise FakeConnectionClosed("cannot send, connection closed")
        self.sent.append(message)

    async def recv(self) -> str:
        if self._inbox:
            return self._inbox.pop(0)
        raise FakeConnectionClosed("connection closed, no more messages")

    async def close(self) -> None:
        self.close_called = True
        self.closed_by_test = True


def make_transport(connection: FakeRawConnection) -> WebSocketTransport:
    return WebSocketTransport(
        connection, closed_exception_types=(FakeConnectionClosed,)
    )


async def test_send_forwards_message_to_underlying_connection():
    connection = FakeRawConnection()
    transport = make_transport(connection)

    await transport.send("hello")

    assert connection.sent == ["hello"]


async def test_receive_forwards_from_underlying_connection():
    connection = FakeRawConnection()
    connection.queue_incoming("hi there")
    transport = make_transport(connection)

    assert await transport.receive() == "hi there"


async def test_close_delegates_to_underlying_connection_and_marks_closed():
    connection = FakeRawConnection()
    transport = make_transport(connection)

    assert not transport.closed
    await transport.close()

    assert connection.close_called
    assert transport.closed


async def test_close_is_idempotent():
    connection = FakeRawConnection()
    transport = make_transport(connection)

    await transport.close()
    await transport.close()  # must not raise, must not double-call underlying close

    assert connection.close_called


async def test_send_after_close_raises_without_touching_underlying_connection():
    connection = FakeRawConnection()
    transport = make_transport(connection)
    await transport.close()

    with pytest.raises(TransportClosedError):
        await transport.send("too late")


async def test_underlying_closed_exception_on_recv_translates_to_transport_closed_error():
    connection = FakeRawConnection()  # empty inbox -> recv() raises FakeConnectionClosed
    transport = make_transport(connection)

    with pytest.raises(TransportClosedError):
        await transport.receive()

    assert transport.closed


async def test_underlying_closed_exception_on_send_translates_to_transport_closed_error():
    connection = FakeRawConnection()
    connection.closed_by_test = True  # simulate peer having closed already
    transport = make_transport(connection)

    with pytest.raises(TransportClosedError):
        await transport.send("hello")

    assert transport.closed


async def test_connect_without_websockets_installed_raises_helpful_error(monkeypatch):
    """Simulates the optional dependency being missing by making the
    ``websockets`` import fail, and checks the error message tells the caller
    what to do about it rather than surfacing a bare ImportError.
    """
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "websockets":
            raise ImportError("simulated: websockets not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="websockets"):
        await WebSocketTransport.connect("ws://localhost:1234")
