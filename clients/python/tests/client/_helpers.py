"""Shared helpers for scripting a fake AHP host over ``InMemoryTransport`` in
the ``tests/client/`` test suite. Not itself a test module (no ``test_``
prefix), so pytest won't try to collect it.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ahp.client import AhpClient
from ahp.transport.memory import InMemoryTransport

ROOT_SNAPSHOT: dict[str, Any] = {
    "channel": "agenthost:/root",
    "serverSeq": 1,
    "state": {"agents": [], "activeSessions": 0, "sessionUris": []},
}


def initialize_result(client_id: str = "client-123") -> dict[str, Any]:
    return {
        "protocolVersion": 1,
        "clientId": client_id,
        "capabilities": {
            "channels": ["session", "chat"],
            "changesets": False,
            "completions": False,
        },
        "rootSnapshot": ROOT_SNAPSHOT,
    }


def session_snapshot_result(uri: str, *, title: str | None = "Untitled") -> dict[str, Any]:
    return {
        "snapshot": {
            "channel": uri,
            "serverSeq": 1,
            "state": {
                "uri": uri,
                "title": title,
                "chatUris": [],
                "terminalUris": [],
                "disposed": False,
            },
        }
    }


async def respond_to_next_request(host_transport: InMemoryTransport, result: dict[str, Any]) -> dict[str, Any]:
    """Read one raw JSON-RPC request off the host side, reply with ``result``,
    and return the decoded request for the caller to assert against.
    """
    raw = await host_transport.receive()
    request = json.loads(raw)
    response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
    await host_transport.send(json.dumps(response))
    return request


async def respond_with_error(host_transport: InMemoryTransport, code: int, message: str) -> dict[str, Any]:
    raw = await host_transport.receive()
    request = json.loads(raw)
    response = {"jsonrpc": "2.0", "id": request["id"], "error": {"code": code, "message": message}}
    await host_transport.send(json.dumps(response))
    return request


async def initialized_client(client_transport: InMemoryTransport, host_transport: InMemoryTransport) -> AhpClient:
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
