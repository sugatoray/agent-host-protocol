"""``MultiHostClient`` — fan a single logical client out across N
:class:`~ahp.client.AhpClient` connections, one per host.

Mirrors ``ahp::hosts::MultiHostClient`` (Rust) / ``ahp/hosts.MultiHostClient``
(Go): most consumers only ever talk to one host, via
:meth:`MultiHostClient.single`, which is the recommended entry point even for
single-host use so that code can grow into multi-host without an API change.

This is intentionally a thin registry + fan-out layer on top of
:class:`~ahp.client.AhpClient` — it does not duplicate any protocol logic
(handshake, reconciliation, etc.), only host_id-keyed bookkeeping and
convenience delegation.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .client import AhpClient
from .types import URI, AnyChannelState, RootState, StateAction


class MultiHostClientError(Exception):
    """Raised for local misuse — e.g. referencing an unregistered host_id, or
    registering a host_id that's already taken.
    """


class MultiHostClient:
    """A registry of :class:`AhpClient` instances keyed by an arbitrary
    ``host_id`` string, with convenience methods for operating across all of
    them (or delegating to one by id).
    """

    def __init__(self, clients: dict[str, AhpClient] | None = None) -> None:
        self._clients: dict[str, AhpClient] = dict(clients) if clients else {}

    @classmethod
    def single(cls, client: AhpClient, host_id: str = "default") -> "MultiHostClient":
        """Wrap exactly one :class:`AhpClient` — the common case. Prefer this
        over constructing a single-entry dict by hand so single-host code can
        grow into multi-host later without changing shape.
        """
        return cls({host_id: client})

    @property
    def host_ids(self) -> list[str]:
        return list(self._clients.keys())

    def client_for(self, host_id: str) -> AhpClient:
        """Return the :class:`AhpClient` registered under ``host_id``.

        Raises :class:`MultiHostClientError` if ``host_id`` isn't registered.
        """
        try:
            return self._clients[host_id]
        except KeyError as exc:
            raise MultiHostClientError(f"unknown host_id: {host_id!r}") from exc

    def add_host(self, host_id: str, client: AhpClient) -> None:
        """Register a new host. Raises :class:`MultiHostClientError` if
        ``host_id`` is already registered — use :meth:`remove_host` first if
        you intend to replace it.
        """
        if host_id in self._clients:
            raise MultiHostClientError(f"host_id already registered: {host_id!r}")
        self._clients[host_id] = client

    def remove_host(self, host_id: str) -> AhpClient:
        """Unregister and return the client for ``host_id``.

        This does *not* close the client's transport — callers that want that
        should call ``.close()`` on the returned client themselves (e.g. as
        part of a reconnect flow that replaces it with a fresh connection).
        """
        try:
            return self._clients.pop(host_id)
        except KeyError as exc:
            raise MultiHostClientError(f"unknown host_id: {host_id!r}") from exc

    async def initialize_all(self) -> dict[str, RootState]:
        """Call ``initialize()`` on every registered host concurrently.

        Returns a ``{host_id: RootState}`` mapping. If any host's
        ``initialize()`` raises, the exception propagates (via
        ``asyncio.gather``'s default fail-fast behavior) once all have had a
        chance to run; other hosts are not cancelled mid-flight.
        """
        host_ids = list(self._clients.keys())
        results = await asyncio.gather(*(self._clients[host_id].initialize() for host_id in host_ids))
        return dict(zip(host_ids, results))

    async def close_all(self) -> None:
        """Close every registered host's client concurrently.

        Uses ``return_exceptions=True`` so that one host failing to close
        cleanly doesn't prevent the others from being closed.
        """
        await asyncio.gather(
            *(client.close() for client in self._clients.values()),
            return_exceptions=True,
        )

    def get_state(self, host_id: str, channel: URI) -> AnyChannelState | None:
        """Convenience delegate: ``self.client_for(host_id).get_state(channel)``."""
        return self.client_for(host_id).get_state(channel)

    async def dispatch_action(self, host_id: str, channel: URI, action: StateAction) -> int:
        """Convenience delegate:
        ``await self.client_for(host_id).dispatch_action(channel, action)``.
        """
        return await self.client_for(host_id).dispatch_action(channel, action)

    async def __aenter__(self) -> "MultiHostClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close_all()
