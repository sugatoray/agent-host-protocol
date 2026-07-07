"""Tests for unsubscribe() and the session/chat/terminal lifecycle commands."""

from __future__ import annotations

import asyncio

from ahp.transport.memory import InMemoryTransport

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


async def test_create_session_sends_channel_and_returns_uri():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, session_uri = await asyncio.gather(
        respond_to_next_request(host_transport, {"session": "ahp-session:/new"}),
        client.create_session("ahp-root://", provider="copilot"),
    )

    assert request["method"] == "createSession"
    assert request["params"]["channel"] == "ahp-root://"
    assert request["params"]["provider"] == "copilot"
    assert session_uri == "ahp-session:/new"


async def test_dispose_session_sends_channel_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.dispose_session("ahp-session:/abc"),
    )

    assert request["method"] == "disposeSession"
    assert request["params"]["channel"] == "ahp-session:/abc"
    assert client.get_state("ahp-session:/abc") is None


async def test_list_sessions_returns_result():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, {"sessions": [{"uri": "ahp-session:/a"}]}),
        client.list_sessions(),
    )

    assert request["method"] == "listSessions"
    assert len(result.sessions) == 1


async def test_create_chat_sends_channel_and_returns_uri():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    request, chat_uri = await asyncio.gather(
        respond_to_next_request(host_transport, {"chat": "ahp-chat:/new"}),
        client.create_chat("ahp-session:/abc", title="My Chat"),
    )

    assert request["method"] == "createChat"
    assert request["params"]["channel"] == "ahp-session:/abc"
    assert request["params"]["title"] == "My Chat"
    assert chat_uri == "ahp-chat:/new"


async def test_dispose_chat_sends_channel_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    # Subscribe to a chat channel first.
    await asyncio.gather(
        respond_to_next_request(
            host_transport,
            {"snapshot": {"resource": "ahp-chat:/x", "fromSeq": 1, "state": {"turns": []}}},
        ),
        client.subscribe("ahp-chat:/x"),
    )

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.dispose_chat("ahp-chat:/x"),
    )

    assert request["method"] == "disposeChat"
    assert request["params"]["channel"] == "ahp-chat:/x"
    assert client.get_state("ahp-chat:/x") is None


async def test_fetch_turns_sends_params_and_returns_result():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "turns": [{"id": "t1", "message": {}, "responseParts": [], "state": {"type": "complete"}}],
        "nextCursor": "prev-page-token",
    }

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.fetch_turns("ahp-chat:/x", cursor="tok"),
    )

    assert request["method"] == "fetchTurns"
    assert request["params"]["channel"] == "ahp-chat:/x"
    assert request["params"]["cursor"] == "tok"
    assert result.next_cursor == "prev-page-token"
    assert result.turns[0]["id"] == "t1"


async def test_create_terminal_sends_channel_and_returns_uri():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    request, terminal_uri = await asyncio.gather(
        respond_to_next_request(host_transport, {"terminal": "ahp-terminal:/new"}),
        client.create_terminal("ahp-session:/abc", shell="/bin/zsh", cwd="/tmp"),
    )

    assert request["method"] == "createTerminal"
    assert request["params"]["channel"] == "ahp-session:/abc"
    assert request["params"]["shell"] == "/bin/zsh"
    assert terminal_uri == "ahp-terminal:/new"


async def test_dispose_terminal_sends_channel_and_forgets_local_state():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await subscribed_session_client(client_transport, host_transport, "ahp-session:/abc")

    await asyncio.gather(
        respond_to_next_request(
            host_transport,
            {"snapshot": {"resource": "ahp-terminal:/x", "fromSeq": 1, "state": {"title": "", "content": []}}},
        ),
        client.subscribe("ahp-terminal:/x"),
    )

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.dispose_terminal("ahp-terminal:/x"),
    )

    assert request["method"] == "disposeTerminal"
    assert request["params"]["channel"] == "ahp-terminal:/x"
    assert client.get_state("ahp-terminal:/x") is None


async def test_completions_sends_params_and_returns_result():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, {"items": ["foo", "foobar"]}),
        client.completions("ahp-session:/abc", kind="path", text="foo", offset=3),
    )

    assert request["method"] == "completions"
    assert request["params"]["channel"] == "ahp-session:/abc"
    assert request["params"]["kind"] == "path"
    assert request["params"]["text"] == "foo"
    assert request["params"]["offset"] == 3
    assert result.items == ["foo", "foobar"]


async def test_invoke_changeset_operation_sends_params_and_returns_status():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, status = await asyncio.gather(
        respond_to_next_request(host_transport, {"status": "applied"}),
        client.invoke_changeset_operation("ahp-changeset:/x", "accept", args={"id": "1"}),
    )

    assert request["method"] == "invokeChangesetOperation"
    assert request["params"]["channel"] == "ahp-changeset:/x"
    assert request["params"]["operation"] == "accept"
    assert request["params"]["args"] == {"id": "1"}
    assert status == "applied"
