"""Tests for ahp.hosts.MultiHostClient.

TDD note: written before ``ahp/hosts.py`` exists; should fail at collection
(ImportError) until implemented.

Self-contained fake-host helpers here (rather than importing
``tests/client/_helpers.py``) since this directory has no straightforward
import path back to ``tests/client/`` under pytest's default rootdir-based
discovery.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from ahp.client import AhpClient
from ahp.hosts import MultiHostClient, MultiHostClientError
from ahp.transport.memory import InMemoryTransport
from ahp.types import RootState, SessionTitleChangedAction


def root_snapshot(session_uris: list[str] | None = None) -> dict:
    return {
        "channel": "agenthost:/root",
        "serverSeq": 1,
        "state": {"agents": [], "activeSessions": 0, "sessionUris": session_uris or []},
    }


def initialize_result(client_id: str) -> dict:
    return {
        "protocolVersion": 1,
        "clientId": client_id,
        "capabilities": {"channels": ["session"], "changesets": False, "completions": False},
        "rootSnapshot": root_snapshot(),
    }


async def respond_to_next_request(host_transport: InMemoryTransport, result: dict) -> dict:
    raw = await host_transport.receive()
    request = json.loads(raw)
    await host_transport.send(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}))
    return request


async def initialized_client(client_transport, host_transport, client_id: str) -> AhpClient:
    client = AhpClient(client_transport)
    await asyncio.gather(
        respond_to_next_request(host_transport, initialize_result(client_id)),
        client.initialize(),
    )
    return client


async def subscribed_session_client(client_transport, host_transport, client_id: str, uri: str) -> AhpClient:
    client = await initialized_client(client_transport, host_transport, client_id)
    snapshot_result = {
        "snapshot": {
            "channel": uri,
            "serverSeq": 1,
            "state": {
                "uri": uri,
                "title": "Untitled",
                "chatUris": [],
                "terminalUris": [],
                "disposed": False,
            },
        }
    }
    await asyncio.gather(
        respond_to_next_request(host_transport, snapshot_result),
        client.subscribe(uri),
    )
    return client


# ---------------------------------------------------------------------------
# registry mechanics
# ---------------------------------------------------------------------------


def test_single_wraps_one_client_under_the_default_host_id():
    _client_transport, _host_transport = InMemoryTransport.pair()
    client = AhpClient(_client_transport)

    multi = MultiHostClient.single(client)

    assert multi.host_ids == ["default"]
    assert multi.client_for("default") is client


def test_single_accepts_a_custom_host_id():
    _client_transport, _host_transport = InMemoryTransport.pair()
    client = AhpClient(_client_transport)

    multi = MultiHostClient.single(client, host_id="primary")

    assert multi.host_ids == ["primary"]
    assert multi.client_for("primary") is client


def test_client_for_unknown_host_id_raises():
    multi = MultiHostClient()

    with pytest.raises(MultiHostClientError):
        multi.client_for("does-not-exist")


def test_add_host_and_remove_host():
    _client_transport, _host_transport = InMemoryTransport.pair()
    client = AhpClient(_client_transport)
    multi = MultiHostClient()

    multi.add_host("a", client)
    assert multi.client_for("a") is client

    removed = multi.remove_host("a")
    assert removed is client
    with pytest.raises(MultiHostClientError):
        multi.client_for("a")


def test_add_host_with_duplicate_id_raises():
    ct1, _ht1 = InMemoryTransport.pair()
    ct2, _ht2 = InMemoryTransport.pair()
    multi = MultiHostClient()
    multi.add_host("a", AhpClient(ct1))

    with pytest.raises(MultiHostClientError):
        multi.add_host("a", AhpClient(ct2))


def test_remove_unknown_host_raises():
    multi = MultiHostClient()
    with pytest.raises(MultiHostClientError):
        multi.remove_host("does-not-exist")


# ---------------------------------------------------------------------------
# fan-out behavior
# ---------------------------------------------------------------------------


async def test_initialize_all_initializes_every_host_concurrently():
    ct_a, ht_a = InMemoryTransport.pair()
    ct_b, ht_b = InMemoryTransport.pair()
    multi = MultiHostClient(
        {"host-a": AhpClient(ct_a), "host-b": AhpClient(ct_b)}
    )

    async def fake_host_a():
        await respond_to_next_request(ht_a, initialize_result("client-a"))

    async def fake_host_b():
        await respond_to_next_request(ht_b, initialize_result("client-b"))

    (_ha, _hb), results = await asyncio.gather(
        asyncio.gather(fake_host_a(), fake_host_b()),
        multi.initialize_all(),
    )

    assert set(results.keys()) == {"host-a", "host-b"}
    assert isinstance(results["host-a"], RootState)
    assert multi.client_for("host-a").client_id == "client-a"
    assert multi.client_for("host-b").client_id == "client-b"


async def test_get_state_and_dispatch_action_are_isolated_per_host():
    ct_a, ht_a = InMemoryTransport.pair()
    ct_b, ht_b = InMemoryTransport.pair()

    client_a = await subscribed_session_client(ct_a, ht_a, "client-a", "ahp-session:/abc")
    client_b = await subscribed_session_client(ct_b, ht_b, "client-b", "ahp-session:/abc")
    multi = MultiHostClient({"host-a": client_a, "host-b": client_b})

    dispatch_task = asyncio.create_task(
        multi.dispatch_action("host-a", "ahp-session:/abc", SessionTitleChangedAction(title="Renamed on A"))
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    request = json.loads(await ht_a.receive())
    await ht_a.send(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": {"serverSeq": 2}}))
    await dispatch_task

    assert multi.get_state("host-a", "ahp-session:/abc").title == "Renamed on A"
    # Host B's identically-URI'd session must be completely unaffected.
    assert multi.get_state("host-b", "ahp-session:/abc").title == "Untitled"


async def test_close_all_closes_every_host_client():
    ct_a, ht_a = InMemoryTransport.pair()
    ct_b, ht_b = InMemoryTransport.pair()
    client_a = await initialized_client(ct_a, ht_a, "client-a")
    client_b = await initialized_client(ct_b, ht_b, "client-b")
    multi = MultiHostClient({"host-a": client_a, "host-b": client_b})

    await asyncio.wait_for(multi.close_all(), timeout=1.0)

    assert ct_a.closed
    assert ct_b.closed


async def test_close_all_does_not_abort_early_if_one_host_errors():
    """If closing one host's transport somehow raises, the other host must
    still get closed rather than the whole close_all() call bailing out.
    """
    ct_a, ht_a = InMemoryTransport.pair()
    ct_b, ht_b = InMemoryTransport.pair()
    client_a = await initialized_client(ct_a, ht_a, "client-a")
    client_b = await initialized_client(ct_b, ht_b, "client-b")

    async def exploding_close():
        raise RuntimeError("boom")

    client_a.close = exploding_close  # type: ignore[method-assign]
    multi = MultiHostClient({"host-a": client_a, "host-b": client_b})

    await asyncio.wait_for(multi.close_all(), timeout=1.0)

    assert ct_b.closed  # host B still closed despite host A's close() raising


async def test_async_context_manager_closes_all_hosts_on_exit():
    ct_a, ht_a = InMemoryTransport.pair()
    client_a = await initialized_client(ct_a, ht_a, "client-a")

    async with MultiHostClient.single(client_a) as multi:
        assert multi.client_for("default") is client_a

    assert ct_a.closed
