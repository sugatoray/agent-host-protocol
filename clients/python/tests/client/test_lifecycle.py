"""Tests for unsubscribe() and the session/chat/terminal lifecycle commands:
create_session, dispose_session, list_sessions, create_chat, dispose_chat,
fetch_turns, create_terminal, dispose_terminal, completions, and
invoke_changeset_operation.
"""

from __future__ import annotations

import asyncio

from ahp.transport.memory import InMemoryTransport
from ahp.types import ChangesetOperationStatus

from _helpers import initialized_client, respond_to_next_request, subscribed_session_client


async def test_unsubscribe_sends_channel_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")
    assert client.get_state("ahp-session:/abc") is not None

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.unsubscribe("ahp-session:/abc"),
    )

    assert request["method"] == "unsubscribe"
    assert request["params"]["channel"] == "ahp-session:/abc"
    assert client.get_state("ahp-session:/abc") is None


async def test_create_session_sends_agent_and_title_and_returns_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "sessionUri": "ahp-session:/new",
        "snapshot": {
            "channel": "ahp-session:/new",
            "serverSeq": 1,
            "state": {"uri": "ahp-session:/new", "title": "Hi", "chatUris": [], "terminalUris": [], "disposed": False},
        },
    }

    request, state = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.create_session(title="Hi"),
    )

    assert request["method"] == "createSession"
    assert request["params"]["title"] == "Hi"
    assert state.uri == "ahp-session:/new"
    assert client.get_state("ahp-session:/new") == state


async def test_dispose_session_sends_uri_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.dispose_session("ahp-session:/abc"),
    )

    assert request["method"] == "disposeSession"
    assert request["params"]["sessionUri"] == "ahp-session:/abc"
    assert client.get_state("ahp-session:/abc") is None


async def test_list_sessions_returns_uris():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, uris = await asyncio.gather(
        respond_to_next_request(host_transport, {"sessionUris": ["ahp-session:/a", "ahp-session:/b"]}),
        client.list_sessions(),
    )

    assert request["method"] == "listSessions"
    assert uris == ["ahp-session:/a", "ahp-session:/b"]


async def test_create_chat_sends_session_uri_and_returns_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    result_payload = {
        "chatUri": "ahp-chat:/new",
        "snapshot": {
            "channel": "ahp-chat:/new",
            "serverSeq": 1,
            "state": {"uri": "ahp-chat:/new", "sessionUri": "ahp-session:/abc", "turns": [], "pendingConfirmation": False},
        },
    }

    request, state = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.create_chat("ahp-session:/abc"),
    )

    assert request["method"] == "createChat"
    assert request["params"]["sessionUri"] == "ahp-session:/abc"
    assert state.uri == "ahp-chat:/new"
    assert client.get_state("ahp-chat:/new") == state


async def test_dispose_chat_sends_uri_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")
    result_payload = {
        "chatUri": "ahp-chat:/x",
        "snapshot": {
            "channel": "ahp-chat:/x",
            "serverSeq": 1,
            "state": {"uri": "ahp-chat:/x", "sessionUri": "ahp-session:/abc", "turns": [], "pendingConfirmation": False},
        },
    }
    await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.create_chat("ahp-session:/abc"),
    )

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.dispose_chat("ahp-chat:/x"),
    )

    assert request["method"] == "disposeChat"
    assert request["params"]["chatUri"] == "ahp-chat:/x"
    assert client.get_state("ahp-chat:/x") is None


async def test_fetch_turns_sends_params_and_returns_result():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "turns": [{"id": "t1", "role": "user", "status": "complete", "text": "hi"}],
        "hasMore": True,
    }

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.fetch_turns("ahp-chat:/x", before_turn_id="t2", limit=10),
    )

    assert request["method"] == "fetchTurns"
    assert request["params"]["chatUri"] == "ahp-chat:/x"
    assert request["params"]["beforeTurnId"] == "t2"
    assert request["params"]["limit"] == 10
    assert result.has_more is True
    assert result.turns[0].id == "t1"


async def test_create_terminal_sends_session_uri_and_returns_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    result_payload = {
        "terminalUri": "ahp-terminal:/new",
        "snapshot": {
            "channel": "ahp-terminal:/new",
            "serverSeq": 1,
            "state": {"uri": "ahp-terminal:/new", "sessionUri": "ahp-session:/abc", "status": "running", "buffer": ""},
        },
    }

    request, state = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.create_terminal("ahp-session:/abc", shell="/bin/zsh", cwd="/tmp"),
    )

    assert request["method"] == "createTerminal"
    assert request["params"]["sessionUri"] == "ahp-session:/abc"
    assert request["params"]["shell"] == "/bin/zsh"
    assert state.uri == "ahp-terminal:/new"
    assert client.get_state("ahp-terminal:/new") == state


async def test_dispose_terminal_sends_uri_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")
    result_payload = {
        "terminalUri": "ahp-terminal:/x",
        "snapshot": {
            "channel": "ahp-terminal:/x",
            "serverSeq": 1,
            "state": {"uri": "ahp-terminal:/x", "sessionUri": "ahp-session:/abc", "status": "running", "buffer": ""},
        },
    }
    await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.create_terminal("ahp-session:/abc"),
    )

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.dispose_terminal("ahp-terminal:/x"),
    )

    assert request["method"] == "disposeTerminal"
    assert request["params"]["terminalUri"] == "ahp-terminal:/x"
    assert client.get_state("ahp-terminal:/x") is None


async def test_completions_sends_params_and_returns_items():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, items = await asyncio.gather(
        respond_to_next_request(host_transport, {"items": ["foo", "foobar"]}),
        client.completions("ahp-session:/abc", prefix="foo", kind="path"),
    )

    assert request["method"] == "completions"
    assert request["params"]["sessionUri"] == "ahp-session:/abc"
    assert request["params"]["prefix"] == "foo"
    assert request["params"]["kind"] == "path"
    assert items == ["foo", "foobar"]


async def test_invoke_changeset_operation_sends_params_and_returns_status():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, status = await asyncio.gather(
        respond_to_next_request(host_transport, {"status": "applied"}),
        client.invoke_changeset_operation("ahp-changeset:/x", "accept", args={"id": "1"}),
    )

    assert request["method"] == "invokeChangesetOperation"
    assert request["params"]["changesetUri"] == "ahp-changeset:/x"
    assert request["params"]["operation"] == "accept"
    assert request["params"]["args"] == {"id": "1"}
    assert status == ChangesetOperationStatus.APPLIED
