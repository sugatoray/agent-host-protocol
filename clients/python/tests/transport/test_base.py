"""Tests for ahp.transport.base: the structural Transport protocol and the
transport-level error hierarchy.
"""

from __future__ import annotations

from ahp.transport.base import Transport, TransportClosedError, TransportError


class ConformingTransport:
    """Implements every method Transport requires, with no inheritance from
    anything — this is the point of using a structural Protocol rather than an
    ABC: any duck-typed object qualifies.
    """

    def __init__(self) -> None:
        self._closed = False

    async def send(self, message: str) -> None:
        pass

    async def receive(self) -> str:
        return ""

    async def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


class MissingReceiveMethod:
    """Deliberately incomplete — should NOT satisfy the Transport protocol."""

    async def send(self, message: str) -> None:
        pass

    async def close(self) -> None:
        pass

    @property
    def closed(self) -> bool:
        return False


def test_conforming_object_satisfies_transport_protocol():
    assert isinstance(ConformingTransport(), Transport)


def test_incomplete_object_does_not_satisfy_transport_protocol():
    assert not isinstance(MissingReceiveMethod(), Transport)


def test_transport_closed_error_is_a_transport_error():
    assert issubclass(TransportClosedError, TransportError)


def test_transport_error_is_a_plain_exception():
    assert issubclass(TransportError, Exception)
