"""Tests for AhpClient.reconnect()."""

from __future__ import annotations

import asyncio
import json

import pytest

from ahp.client import AhpClient, AhpClientError
from ahp.transport.memory import InMemoryTransport
from ahp.types import SessionState

from _helpers import (
    initialized_client,
    respond_to_next_request,
    session_snapshot_result,
    subscribed_session_client,
)


async def test_reconnect_before_initialize_raises():
    client_transport, _host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)

    with pytest.raises(AhpClientError):
        await client.reconnect()


async def test_reconnect_sends_canonical_params():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    reconnect_task = asyncio.create_task(client.reconnect())
    request = json.loads(await host_transport.receive())
    # Canonical ReconnectResult must have a "type" discriminator.
    await host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"type": "replay", "actions": [], "missing": []},
            }
        )
    )
    await reconnect_task

    assert request["method"] == "reconnect"
    assert request["params"]["clientId"] == client.client_id
    # lastSeenServerSeq is a single int (for the target channel), not a dict.
    assert isinstance(request["params"]["lastSeenServerSeq"], int)
    # subscriptions carries the list of all subscribed channel URIs.
    assert "ahp-session:/abc" in request["params"]["subscriptions"]


async def test_reconnect_replay_result_leaves_local_state_untouched():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)
    state_before = client.get_state("ahp-session:/abc")

    reconnect_task = asyncio.create_task(client.reconnect())
    request = json.loads(await host_transport.receive())
    await host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"type": "replay", "actions": [], "missing": []},
            }
        )
    )
    result = await reconnect_task

    assert result.type == "replay"
    assert client.get_state("ahp-session:/abc") == state_before


async def test_reconnect_snapshot_result_overwrites_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    reconnect_task = asyncio.create_task(client.reconnect())
    request = json.loads(await host_transport.receive())
    fresh_snapshot = {
        "resource": "ahp-session:/abc",
        "fromSeq": 99,
        "state": {
            "provider": "",
            "title": "Reloaded After Reconnect",
            "lifecycle": "ready",
            "activeClients": [],
            "chats": [],
        },
    }
    await host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"type": "snapshot", "snapshots": [fresh_snapshot]},
            }
        )
    )
    await reconnect_task

    state = client.get_state("ahp-session:/abc")
    assert isinstance(state, SessionState)
    assert state.title == "Reloaded After Reconnect"


async def test_reconnect_can_swap_in_a_new_transport():
    old_client_transport, old_host_transport = InMemoryTransport.pair()
    client = await initialized_client(old_client_transport, old_host_transport)
    await old_client_transport.close()  # simulate dropped connection

    new_client_transport, new_host_transport = InMemoryTransport.pair()

    reconnect_task = asyncio.create_task(client.reconnect(new_client_transport))
    # Request must go out over the NEW transport.
    request = json.loads(await new_host_transport.receive())
    await new_host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"type": "replay", "actions": [], "missing": []},
            }
        )
    )
    await reconnect_task

    assert request["method"] == "reconnect"

    # Client keeps working normally afterwards over the new transport.
    await asyncio.gather(
        respond_to_next_request(new_host_transport, session_snapshot_result("ahp-session:/xyz")),
        client.subscribe("ahp-session:/xyz"),
    )
    assert client.get_state("ahp-session:/xyz") is not None
