"""Tests for AhpClient.reconnect().

TDD note: written against the reconnect() API before it exists on AhpClient;
should fail with AttributeError until implemented.
"""

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
    subscribed_session_client,
)


async def test_reconnect_before_initialize_raises():
    client_transport, _host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)

    with pytest.raises(AhpClientError):
        await client.reconnect()


async def test_reconnect_sends_client_id_and_last_seen_server_seq():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    reconnect_task = asyncio.create_task(client.reconnect())
    request = json.loads(await host_transport.receive())
    await host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"replayed": [], "resnapshotted": []},
            }
        )
    )
    await reconnect_task

    assert request["method"] == "reconnect"
    assert request["params"]["clientId"] == client.client_id
    assert request["params"]["lastSeenServerSeq"] == {
        "agenthost:/root": 1,
        "ahp-session:/abc": 1,
    }


async def test_reconnect_leaves_replayed_channel_state_untouched():
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
                "result": {"replayed": ["ahp-session:/abc"], "resnapshotted": []},
            }
        )
    )
    result = await reconnect_task

    assert result.replayed == ["ahp-session:/abc"]
    assert client.get_state("ahp-session:/abc") == state_before


async def test_reconnect_overwrites_state_for_resnapshotted_channel():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    reconnect_task = asyncio.create_task(client.reconnect())
    request = json.loads(await host_transport.receive())
    fresh_snapshot = {
        "channel": "ahp-session:/abc",
        "serverSeq": 99,
        "state": {
            "uri": "ahp-session:/abc",
            "title": "Reloaded After Reconnect",
            "chatUris": [],
            "terminalUris": [],
            "disposed": False,
        },
    }
    await host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"replayed": [], "resnapshotted": [fresh_snapshot]},
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
    await old_client_transport.close()  # simulate the connection having dropped

    new_client_transport, new_host_transport = InMemoryTransport.pair()

    reconnect_task = asyncio.create_task(client.reconnect(new_client_transport))
    # The request must go out over the NEW transport, not the dead old one.
    request = json.loads(await new_host_transport.receive())
    await new_host_transport.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"replayed": [], "resnapshotted": []},
            }
        )
    )
    await reconnect_task

    assert request["method"] == "reconnect"

    # And the client keeps working normally afterwards, over the new transport.
    await asyncio.gather(
        respond_to_next_request(
            new_host_transport,
            {
                "snapshot": {
                    "channel": "ahp-session:/xyz",
                    "serverSeq": 1,
                    "state": {
                        "uri": "ahp-session:/xyz",
                        "title": None,
                        "chatUris": [],
                        "terminalUris": [],
                        "disposed": False,
                    },
                }
            },
        ),
        client.subscribe("ahp-session:/xyz"),
    )
    assert client.get_state("ahp-session:/xyz") is not None
