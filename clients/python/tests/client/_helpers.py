"""Shared helpers for scripting a fake AHP host over InMemoryTransport."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ahp.client import AhpClient
from ahp.transport.memory import InMemoryTransport

# Canonical snapshot: "resource" (not "channel"), "fromSeq" (not "serverSeq").
ROOT_SNAPSHOT: dict[str, Any] = {
    "resource": "ahp-root://",
    "fromSeq": 1,
    "state": {"agents": [], "activeSessions": 0},
}


def initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": "0.1.0",
        "serverSeq": 1,
        "snapshots": [ROOT_SNAPSHOT],
    }


def session_snapshot_result(uri: str, *, title: str | None = "Untitled") -> dict[str, Any]:
    """Return a SubscribeResult payload with canonical Snapshot fields."""
    return {
        "snapshot": {
            "resource": uri,
            "fromSeq": 1,
            "state": {
                "provider": "",
                "title": title,
                "lifecycle": "ready",
                "activeClients": [],
                "chats": [],
            },
        }
    }


async def respond_to_next_request(
    host_transport: InMemoryTransport, result: dict[str, Any]
) -> dict[str, Any]:
    """Read one JSON-RPC request off the host side, reply with ``result``,
    and return the decoded request."""
    raw = await host_transport.receive()
    request = json.loads(raw)
    response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
    await host_transport.send(json.dumps(response))
    return request


async def respond_with_error(
    host_transport: InMemoryTransport, code: int, message: str
) -> dict[str, Any]:
    raw = await host_transport.receive()
    request = json.loads(raw)
    response = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "error": {"code": code, "message": message},
    }
    await host_transport.send(json.dumps(response))
    return request


async def initialized_client(
    client_transport: InMemoryTransport, host_transport: InMemoryTransport
) -> AhpClient:
    client = AhpClient(client_transport)
    await asyncio.gather(
        respond_to_next_request(host_transport, initialize_result()),
        client.initialize(),
    )
    return client


async def subscribed_session_client(
    client_transport: InMemoryTransport,
    host_transport: InMemoryTransport,
    uri: str = "ahp-session:/abc",
) -> AhpClient:
    client = await initialized_client(client_transport, host_transport)
    await asyncio.gather(
        respond_to_next_request(host_transport, session_snapshot_result(uri)),
        client.subscribe(uri),
    )
    return client
