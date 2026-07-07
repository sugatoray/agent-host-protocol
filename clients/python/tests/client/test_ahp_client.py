"""Tests for ahp.client.AhpClient.

Drives AhpClient against InMemoryTransport with a scripted fake host.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from ahp.client import AhpClient, AhpClientError
from ahp.transport.memory import InMemoryTransport
from ahp.types import (
    AhpError,
    ChatDeltaAction,
    ChatState,
    ChatTurnStartedAction,
    SessionState,
    SessionTitleChangedAction,
)

from _helpers import (
    ROOT_SNAPSHOT,
    initialize_result,
    initialized_client,
    respond_to_next_request,
    respond_with_error,
    session_snapshot_result,
    subscribed_session_client,
)


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


async def test_initialize_sends_canonical_params():
    client_transport, host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)

    request, root_state = await asyncio.gather(
        respond_to_next_request(host_transport, initialize_result()),
        client.initialize(),
    )

    assert request["method"] == "initialize"
    # canonical: protocolVersions (plural list of strings)
    assert request["params"]["protocolVersions"] == ["0.1.0"]
    # canonical: clientId is sent by the client (UUID string)
    assert isinstance(request["params"]["clientId"], str)
    assert len(request["params"]["clientId"]) == 36  # UUID hyphenated format
    assert root_state.agents == []


async def test_initialize_client_id_is_stable_across_calls():
    """clientId is generated once at construction; it's what we send."""
    client_transport, host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)
    initial_id = client.client_id

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, initialize_result()),
        client.initialize(),
    )

    # The client sends its own generated clientId (not one from the server).
    assert request["params"]["clientId"] == initial_id
    assert client.client_id == initial_id


async def test_initialize_raises_ahp_error_on_error_response():
    client_transport, host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)

    async def do_initialize():
        with pytest.raises(AhpError) as exc_info:
            await client.initialize()
        assert exc_info.value.code == -32001

    await asyncio.gather(
        respond_with_error(host_transport, -32001, "not ready"),
        do_initialize(),
    )


# ---------------------------------------------------------------------------
# subscribe
# ---------------------------------------------------------------------------


async def test_subscribe_sends_channel_and_returns_typed_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, state = await asyncio.gather(
        respond_to_next_request(host_transport, session_snapshot_result("ahp-session:/abc")),
        client.subscribe("ahp-session:/abc"),
    )

    assert request["method"] == "subscribe"
    assert request["params"]["channel"] == "ahp-session:/abc"
    assert isinstance(state, SessionState)
    assert state.title == "Untitled"
    assert client.get_state("ahp-session:/abc") == state


# ---------------------------------------------------------------------------
# dispatch_action + write-ahead reconciliation
# ---------------------------------------------------------------------------


async def test_dispatch_action_raises_for_unsubscribed_channel():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    with pytest.raises(AhpClientError):
        await client.dispatch_action(
            "ahp-session:/never-subscribed", SessionTitleChangedAction(title="x")
        )


async def test_dispatch_action_is_fire_and_forget_notification():
    """dispatchAction sends a notification (no id) and returns None."""
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    result = await client.dispatch_action(
        "ahp-session:/abc", SessionTitleChangedAction(title="New Title")
    )
    assert result is None

    # The client should have sent a notification (no "id" field).
    raw = await host_transport.receive()
    notification = json.loads(raw)
    assert "id" not in notification
    assert notification["method"] == "dispatchAction"
    assert notification["params"]["channel"] == "ahp-session:/abc"


async def test_dispatch_action_applies_locally_before_wire():
    """Write-ahead: local state updates before notification is sent."""
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    dispatch_task = asyncio.create_task(
        client.dispatch_action("ahp-session:/abc", SessionTitleChangedAction(title="New Title"))
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    # Optimistic apply should already be visible locally.
    assert client.get_state("ahp-session:/abc").title == "New Title"

    await dispatch_task  # notification is sent; no response expected


async def test_own_action_echoed_back_via_notification_is_not_double_applied():
    """The host echoes our dispatched action back as an `action` notification.
    The client must not re-apply it on top of the already-optimistic state.
    """
    client_transport, host_transport = InMemoryTransport.pair()

    chat_uri = "ahp-chat:/1"
    client = await initialized_client(client_transport, host_transport)
    chat_snapshot_result = {
        "snapshot": {
            "resource": chat_uri,
            "fromSeq": 1,
            "state": {
                "resource": chat_uri,
                "turns": [
                    {
                        "id": "t1",
                        "message": {},
                        "responseParts": [],
                        "state": {"type": "running"},
                    }
                ],
            },
        }
    }
    await asyncio.gather(
        respond_to_next_request(host_transport, chat_snapshot_result),
        client.subscribe(chat_uri),
    )

    # Dispatch a delta action (fire-and-forget).
    await client.dispatch_action(
        chat_uri,
        ChatDeltaAction(turn_id="t1", part_id="p1", content="lo"),
    )

    # Read the notification the client sent to the host.
    raw = await host_transport.receive()
    notification = json.loads(raw)
    client_seq_used = notification["params"]["clientSeq"]

    # Host echoes the same mutation back as an `action` notification.
    echo_notification = {
        "jsonrpc": "2.0",
        "method": "action",
        "params": {
            "channel": chat_uri,
            "serverSeq": 2,
            "action": {
                "type": "chat/delta",
                "turnId": "t1",
                "partId": "p1",
                "content": "lo",
            },
            "origin": {"clientId": client.client_id, "clientSeq": client_seq_used},
        },
    }
    await host_transport.send(json.dumps(echo_notification))
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    state = client.get_state(chat_uri)
    # Should have exactly one delta part appended (not two).
    assert isinstance(state, ChatState)
    assert len(state.turns[0].response_parts) == 1


async def test_foreign_action_notification_is_applied_via_reducer():
    """An `action` notification from a different client must be applied."""
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    foreign_notification = {
        "jsonrpc": "2.0",
        "method": "action",
        "params": {
            "channel": "ahp-session:/abc",
            "serverSeq": 5,
            "action": {"type": "session/titleChanged", "title": "Renamed elsewhere"},
            "origin": {"clientId": "some-other-client", "clientSeq": 1},
        },
    }
    await host_transport.send(json.dumps(foreign_notification))
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert client.get_state("ahp-session:/abc").title == "Renamed elsewhere"


# ---------------------------------------------------------------------------
# get_state / close
# ---------------------------------------------------------------------------


async def test_get_state_returns_none_for_unknown_channel():
    client_transport, _host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)

    assert client.get_state("ahp-session:/never-subscribed") is None


async def test_close_closes_transport_and_stops_the_reader_loop():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    await asyncio.wait_for(client.close(), timeout=1.0)

    assert client_transport.closed


async def test_async_context_manager_closes_on_exit():
    client_transport, host_transport = InMemoryTransport.pair()

    async with AhpClient(client_transport) as client:
        await asyncio.gather(
            respond_to_next_request(host_transport, initialize_result()),
            client.initialize(),
        )

    assert client_transport.closed
