"""Tests for ahp.client.AhpClient.

These drive a real ``AhpClient`` against one end of an ``InMemoryTransport``
pair, with a small scripted "fake host" coroutine on the other end that reads
raw JSON-RPC requests and replies by hand. This lets us test the client's
wire behavior (params sent, sequencing, reconciliation) without a real AHP
host or the ``websockets`` dependency.

TDD note: written before ``ahp/client.py`` exists. Every test here should fail
at collection (ImportError) until the client module is implemented.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from ahp.client import AhpClient, AhpClientError
from ahp.transport.memory import InMemoryTransport
from ahp.types import (
    AhpError,
    ChatState,
    ChatTurnDeltaAction,
    ChatTurnStartedAction,
    RootSessionAddedAction,
    SessionState,
    SessionTitleChangedAction,
    Turn,
    TurnRole,
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


async def test_initialize_sends_protocol_version_and_client_metadata():
    client_transport, host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport, client_name="test-client", client_version="0.0.1")

    request, root_state = await asyncio.gather(
        respond_to_next_request(host_transport, initialize_result()),
        client.initialize(),
    )

    assert request["method"] == "initialize"
    assert request["params"]["protocolVersion"] == 1
    assert request["params"]["clientName"] == "test-client"
    assert request["params"]["clientVersion"] == "0.0.1"
    assert root_state.session_uris == []


async def test_initialize_stores_client_id():
    client_transport, host_transport = InMemoryTransport.pair()
    client = AhpClient(client_transport)

    await asyncio.gather(
        respond_to_next_request(host_transport, initialize_result(client_id="abc-999")),
        client.initialize(),
    )

    assert client.client_id == "abc-999"


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
        await client.dispatch_action("ahp-session:/never-subscribed", SessionTitleChangedAction(title="x"))


async def test_dispatch_action_applies_locally_before_host_acknowledges():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport)

    dispatch_task = asyncio.create_task(
        client.dispatch_action("ahp-session:/abc", SessionTitleChangedAction(title="New Title"))
    )
    await asyncio.sleep(0)  # let the client send its request; host hasn't answered yet
    await asyncio.sleep(0)

    # Optimistic (write-ahead) apply must already be visible locally, even
    # though nothing has come back over the wire yet.
    assert client.get_state("ahp-session:/abc").title == "New Title"

    request = json.loads(await host_transport.receive())
    assert request["method"] == "dispatchAction"
    assert request["params"]["channel"] == "ahp-session:/abc"
    await host_transport.send(
        json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": {"serverSeq": 42}})
    )

    server_seq = await dispatch_task
    assert server_seq == 42


async def test_own_action_echoed_back_via_notification_is_not_double_applied():
    """The host also broadcasts every dispatched action back as an `action`
    notification (including to the originating client). If the client
    re-applied its own echoed action on top of the already-optimistically
    -applied state, a streaming append would show up twice. It must not.
    """
    client_transport, host_transport = InMemoryTransport.pair()

    chat_uri = "ahp-chat:/1"
    client = await initialized_client(client_transport, host_transport)
    chat_snapshot_result = {
        "snapshot": {
            "channel": chat_uri,
            "serverSeq": 1,
            "state": {
                "uri": chat_uri,
                "sessionUri": "ahp-session:/abc",
                "turns": [
                    {"id": "t1", "role": "assistant", "status": "running", "text": "Hel"}
                ],
                "pendingConfirmation": False,
            },
        }
    }
    await asyncio.gather(
        respond_to_next_request(host_transport, chat_snapshot_result),
        client.subscribe(chat_uri),
    )

    dispatch_task = asyncio.create_task(
        client.dispatch_action(chat_uri, ChatTurnDeltaAction(turn_id="t1", text_delta="lo"))
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    request = json.loads(await host_transport.receive())
    client_seq_used = request["params"]["clientSeq"]

    # Host acknowledges the direct RPC call...
    await host_transport.send(
        json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": {"serverSeq": 2}})
    )
    await dispatch_task

    # ...and separately broadcasts the same mutation as an `action`
    # notification, echoing this client's own origin.
    echo_notification = {
        "jsonrpc": "2.0",
        "method": "action",
        "params": {
            "channel": chat_uri,
            "serverSeq": 2,
            "action": {"type": "chat/turnDelta", "turnId": "t1", "textDelta": "lo"},
            "origin": {"clientId": client.client_id, "clientSeq": client_seq_used},
        },
    }
    await host_transport.send(json.dumps(echo_notification))
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    state = client.get_state(chat_uri)
    assert state.turns[0].text == "Hello"  # NOT "Hellolo"


async def test_foreign_action_notification_is_applied_via_reducer():
    """An `action` notification whose origin is a *different* client (e.g.
    another connected surface, or the host itself) must be applied through the
    channel's reducer, since this client never applied it optimistically.
    """
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
