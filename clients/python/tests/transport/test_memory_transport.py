"""Tests for ahp.transport.memory.InMemoryTransport.

This is the fake transport the client layer's tests will run against (per
SPEC.md: "tests/test_client.py — against a fake/in-memory transport"), so it's
worth testing thoroughly in isolation first.
"""

from __future__ import annotations

import asyncio

import pytest

from ahp.transport.base import TransportClosedError
from ahp.transport.memory import InMemoryTransport


def test_pair_returns_two_linked_ends():
    a, b = InMemoryTransport.pair()
    assert isinstance(a, InMemoryTransport)
    assert isinstance(b, InMemoryTransport)
    assert not a.closed
    assert not b.closed


async def test_send_from_a_is_received_by_b():
    a, b = InMemoryTransport.pair()
    await a.send("hello")
    assert await b.receive() == "hello"


async def test_communication_is_bidirectional():
    a, b = InMemoryTransport.pair()
    await a.send("ping")
    await b.send("pong")

    assert await b.receive() == "ping"
    assert await a.receive() == "pong"


async def test_messages_are_delivered_in_fifo_order():
    a, b = InMemoryTransport.pair()
    await a.send("one")
    await a.send("two")
    await a.send("three")

    assert await b.receive() == "one"
    assert await b.receive() == "two"
    assert await b.receive() == "three"


async def test_receive_awaits_until_a_message_arrives():
    a, b = InMemoryTransport.pair()

    async def delayed_send() -> None:
        await asyncio.sleep(0.01)
        await a.send("delayed")

    task = asyncio.create_task(delayed_send())
    message = await b.receive()
    await task

    assert message == "delayed"


async def test_close_marks_transport_closed():
    a, _b = InMemoryTransport.pair()
    assert not a.closed
    await a.close()
    assert a.closed


async def test_close_is_idempotent():
    a, _b = InMemoryTransport.pair()
    await a.close()
    await a.close()  # must not raise
    assert a.closed


async def test_send_after_close_raises_transport_closed_error():
    a, _b = InMemoryTransport.pair()
    await a.close()
    with pytest.raises(TransportClosedError):
        await a.send("too late")


async def test_peer_receive_raises_transport_closed_error_after_close():
    a, b = InMemoryTransport.pair()
    await a.close()
    with pytest.raises(TransportClosedError):
        await b.receive()


async def test_peer_is_marked_closed_after_observing_close():
    a, b = InMemoryTransport.pair()
    await a.close()
    with pytest.raises(TransportClosedError):
        await b.receive()
    assert b.closed


async def test_pending_messages_are_delivered_before_close_is_observed():
    """Closing shouldn't discard messages already in flight — the peer should
    drain everything sent before the close, and only then see the closed
    signal on its next receive().
    """
    a, b = InMemoryTransport.pair()
    await a.send("last message")
    await a.close()

    assert await b.receive() == "last message"
    with pytest.raises(TransportClosedError):
        await b.receive()


async def test_close_unblocks_a_receive_already_pending_on_the_same_end():
    """Regression test: if this end's reader loop is currently blocked inside
    receive() (nothing queued yet), calling close() on this same end must wake
    it up with TransportClosedError rather than leaving it hanging forever.
    This matters in practice: AhpClient.close() awaits its background reader
    task, and that task is very likely to be parked in receive() at the moment
    close() is called.
    """
    a, _b = InMemoryTransport.pair()

    receive_task = asyncio.create_task(a.receive())
    await asyncio.sleep(0.01)  # let receive_task actually start blocking
    await a.close()

    with pytest.raises(TransportClosedError):
        await asyncio.wait_for(receive_task, timeout=0.5)
