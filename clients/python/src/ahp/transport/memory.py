"""An in-memory, paired duplex transport — no sockets, no I/O — used to unit
test ``ahp.client.AhpClient`` (and anything else built on ``Transport``)
without a real WebSocket server.

Two ``InMemoryTransport`` instances are created together via :meth:`pair`, each
end reading what the other end sent, so tests can simulate a full client<->host
conversation in a single process.
"""

from __future__ import annotations

import asyncio

from .base import TransportClosedError

# Sentinel placed on a queue to signal "the writer has closed"; re-queued after
# being observed so every subsequent receive() on that queue also sees it.
_CLOSED_SENTINEL: None = None


class InMemoryTransport:
    """One end of an in-memory duplex pair. See :meth:`pair`."""

    def __init__(self, send_queue: "asyncio.Queue[str | None]", recv_queue: "asyncio.Queue[str | None]") -> None:
        self._send_queue = send_queue
        self._recv_queue = recv_queue
        self._closed = False

    @classmethod
    def pair(cls) -> tuple["InMemoryTransport", "InMemoryTransport"]:
        """Create two linked ends: whatever one side sends, the other side
        receives, and vice versa.
        """
        a_to_b: "asyncio.Queue[str | None]" = asyncio.Queue()
        b_to_a: "asyncio.Queue[str | None]" = asyncio.Queue()
        a = cls(send_queue=a_to_b, recv_queue=b_to_a)
        b = cls(send_queue=b_to_a, recv_queue=a_to_b)
        return a, b

    async def send(self, message: str) -> None:
        if self._closed:
            raise TransportClosedError("cannot send on a closed transport")
        await self._send_queue.put(message)

    async def receive(self) -> str:
        if self._closed:
            raise TransportClosedError("transport already closed")

        item = await self._recv_queue.get()
        if item is _CLOSED_SENTINEL:
            # Leave the sentinel in place for any other/future receive() calls
            # on this same end, then surface the closure to this caller.
            await self._recv_queue.put(_CLOSED_SENTINEL)
            self._closed = True
            raise TransportClosedError("peer closed the transport")
        return item

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Tell the peer we've stopped sending (they'll see this on their next
        # receive()) — and also wake up any receive() of our own that's
        # currently blocked waiting on this end's queue. Without the second
        # put, a reader loop parked in `await self.receive()` at the moment
        # close() is called would hang forever, since nothing else would ever
        # populate this end's recv_queue.
        await self._send_queue.put(_CLOSED_SENTINEL)
        await self._recv_queue.put(_CLOSED_SENTINEL)

    @property
    def closed(self) -> bool:
        return self._closed
