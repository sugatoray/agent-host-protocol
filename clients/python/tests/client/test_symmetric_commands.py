"""Tests for client-initiated authenticate/resource* commands.

The canonical authenticate takes ``resource`` (protected resource URI) and
``token``; it returns nothing (empty result). resourceStat is not in the
canonical protocol.
"""

from __future__ import annotations

import asyncio

import pytest

from ahp.transport.memory import InMemoryTransport
from ahp.types import AhpError

from _helpers import initialized_client, respond_to_next_request, respond_with_error


async def test_authenticate_sends_resource_and_token():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.authenticate("https://api.example.com", "my-bearer-token"),
    )

    assert request["method"] == "authenticate"
    assert request["params"]["resource"] == "https://api.example.com"
    assert request["params"]["token"] == "my-bearer-token"


async def test_authenticate_raises_ahp_error_on_failure_response():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    async def do_authenticate():
        with pytest.raises(AhpError):
            await client.authenticate("https://api.example.com", "bad-token")

    await asyncio.gather(
        respond_with_error(host_transport, -32007, "authentication failed"),
        do_authenticate(),
    )


async def test_resource_read_sends_uri_and_returns_data():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {"data": "hello world", "encoding": "utf-8"}

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.resource_read("ahp-resource:/file.txt"),
    )

    assert request["method"] == "resourceRead"
    assert request["params"]["uri"] == "ahp-resource:/file.txt"
    assert result.data == "hello world"
    assert result.encoding == "utf-8"


async def test_resource_write_sends_uri_and_data():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, _ = await asyncio.gather(
        respond_to_next_request(host_transport, {}),
        client.resource_write("ahp-resource:/file.txt", "new contents"),
    )

    assert request["method"] == "resourceWrite"
    assert request["params"]["uri"] == "ahp-resource:/file.txt"
    assert request["params"]["data"] == "new contents"
    assert request["params"]["encoding"] == "utf-8"


async def test_resource_list_returns_entries():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "entries": [
            {"uri": "ahp-resource:/a.txt"},
            {"uri": "ahp-resource:/b.txt"},
        ]
    }

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.resource_list("ahp-resource:/"),
    )

    assert request["method"] == "resourceList"
    assert [e["uri"] for e in result.entries] == ["ahp-resource:/a.txt", "ahp-resource:/b.txt"]
