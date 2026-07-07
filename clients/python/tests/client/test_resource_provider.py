"""Tests for the host-initiated half of the symmetric resource* commands: the
*host* calling resourceRead/Write/List/Stat against this client (e.g. to read
a local file the client has access to but the host doesn't).

AhpClient routes these to a registered "resource provider" object. Without one
registered, it must reply with a JSON-RPC error rather than silently ignoring
the request or crashing the reader loop.
"""

from __future__ import annotations

import json

from ahp.transport.memory import InMemoryTransport
from ahp.types import ContentRef, ResourceListResult, ResourceReadResult, ResourceStatResult

from _helpers import initialized_client


class FakeResourceProvider:
    """A minimal in-memory resource provider used to test routing."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.write_calls: list[tuple[str, str]] = []

    async def read(self, uri: str) -> ResourceReadResult:
        return ResourceReadResult(
            content_ref=ContentRef(uri=uri, mime_type="text/plain"),
            data=self.files.get(uri, ""),
        )

    async def write(self, uri: str, data: str) -> None:
        self.write_calls.append((uri, data))
        self.files[uri] = data

    async def list(self, uri: str) -> ResourceListResult:
        return ResourceListResult(
            entries=[ContentRef(uri=u) for u in self.files if u.startswith(uri)]
        )

    async def stat(self, uri: str) -> ResourceStatResult:
        return ResourceStatResult(
            content_ref=ContentRef(uri=uri), exists=uri in self.files
        )


async def send_host_request(host_transport, request_id: int, method: str, params: dict) -> dict:
    """Send a host->client JSON-RPC request and return the decoded response."""
    await host_transport.send(
        json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
    )
    raw = await host_transport.receive()
    return json.loads(raw)


async def test_host_resource_read_is_routed_to_registered_provider():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    provider = FakeResourceProvider()
    provider.files["ahp-resource:/notes.txt"] = "hello from the client"
    client.register_resource_provider(provider)

    response = await send_host_request(
        host_transport, 999, "resourceRead", {"uri": "ahp-resource:/notes.txt"}
    )

    assert response["id"] == 999
    assert response["result"]["data"] == "hello from the client"


async def test_host_resource_write_is_routed_to_registered_provider():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    provider = FakeResourceProvider()
    client.register_resource_provider(provider)

    response = await send_host_request(
        host_transport,
        1000,
        "resourceWrite",
        {"uri": "ahp-resource:/notes.txt", "data": "written by host"},
    )

    assert "error" not in response
    assert provider.write_calls == [("ahp-resource:/notes.txt", "written by host")]


async def test_host_resource_list_is_routed_to_registered_provider():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    provider = FakeResourceProvider()
    provider.files["ahp-resource:/a.txt"] = "a"
    provider.files["ahp-resource:/b.txt"] = "b"
    client.register_resource_provider(provider)

    response = await send_host_request(host_transport, 1001, "resourceList", {"uri": "ahp-resource:/"})

    assert sorted(e["uri"] for e in response["result"]["entries"]) == [
        "ahp-resource:/a.txt",
        "ahp-resource:/b.txt",
    ]


async def test_host_resource_stat_is_routed_to_registered_provider():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    provider = FakeResourceProvider()
    provider.files["ahp-resource:/a.txt"] = "a"
    client.register_resource_provider(provider)

    response = await send_host_request(host_transport, 1002, "resourceStat", {"uri": "ahp-resource:/a.txt"})

    assert response["result"]["exists"] is True


async def test_host_resource_call_without_registered_provider_replies_with_error():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)
    # deliberately no provider registered

    response = await send_host_request(host_transport, 1003, "resourceRead", {"uri": "ahp-resource:/x.txt"})

    assert "error" in response
    assert response["error"]["code"] is not None


async def test_host_resource_call_when_provider_raises_replies_with_error_not_crash():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    class ExplodingProvider(FakeResourceProvider):
        async def read(self, uri: str) -> ResourceReadResult:
            raise RuntimeError("disk on fire")

    client.register_resource_provider(ExplodingProvider())

    response = await send_host_request(host_transport, 1004, "resourceRead", {"uri": "ahp-resource:/x.txt"})

    assert "error" in response

    # The reader loop must have survived the exception: a normal request
    # afterwards should still work (stat() isn't overridden by
    # ExplodingProvider, so this succeeds normally).
    response2 = await send_host_request(host_transport, 1005, "resourceStat", {"uri": "ahp-resource:/x.txt"})
    assert "error" not in response2
    assert response2["result"]["exists"] is False
