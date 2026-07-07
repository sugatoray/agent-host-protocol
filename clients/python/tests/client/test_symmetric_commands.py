"""Tests for the client-initiated half of the symmetric authenticate/resource*
commands: AhpClient asking the *host* to authenticate a credential or to
read/write/list/stat a resource the host owns.

The other half — the host asking *this client* to serve a resource* call —
is covered in test_resource_provider.py.
"""

from __future__ import annotations

import asyncio

import pytest

from ahp.transport.memory import InMemoryTransport
from ahp.types import AhpError, ContentRef

from _helpers import initialized_client, respond_to_next_request, respond_with_error


async def test_authenticate_sends_scheme_and_credentials_and_returns_bool():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    request, authenticated = await asyncio.gather(
        respond_to_next_request(host_transport, {"authenticated": True}),
        client.authenticate(scheme="bearer", credentials={"token": "secret"}),
    )

    assert request["method"] == "authenticate"
    assert request["params"]["scheme"] == "bearer"
    assert request["params"]["credentials"] == {"token": "secret"}
    assert authenticated is True


async def test_authenticate_raises_ahp_error_on_failure_response():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    async def do_authenticate():
        with pytest.raises(AhpError):
            await client.authenticate(scheme="bearer", credentials={"token": "bad"})

    await asyncio.gather(
        respond_with_error(host_transport, -32007, "authentication failed"),
        do_authenticate(),
    )


async def test_resource_read_sends_uri_and_returns_content():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "contentRef": {"uri": "ahp-resource:/file.txt", "mimeType": "text/plain", "name": "file.txt"},
        "data": "hello world",
    }

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.resource_read("ahp-resource:/file.txt"),
    )

    assert request["method"] == "resourceRead"
    assert request["params"]["uri"] == "ahp-resource:/file.txt"
    assert result.data == "hello world"
    assert isinstance(result.content_ref, ContentRef)


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


async def test_resource_list_returns_entries():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "entries": [
            {"uri": "ahp-resource:/a.txt", "name": "a.txt"},
            {"uri": "ahp-resource:/b.txt", "name": "b.txt"},
        ]
    }

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.resource_list("ahp-resource:/"),
    )

    assert request["method"] == "resourceList"
    assert [entry.uri for entry in result.entries] == ["ahp-resource:/a.txt", "ahp-resource:/b.txt"]


async def test_resource_stat_returns_exists_flag():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    result_payload = {
        "contentRef": {"uri": "ahp-resource:/a.txt", "name": "a.txt"},
        "exists": True,
    }

    request, result = await asyncio.gather(
        respond_to_next_request(host_transport, result_payload),
        client.resource_stat("ahp-resource:/a.txt"),
    )

    assert request["method"] == "resourceStat"
    assert result.exists is True
