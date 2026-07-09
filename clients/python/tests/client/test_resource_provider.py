"""Tests for the host-initiated symmetric resource* commands.

The host calls resourceRead/Write/List against this client; AhpClient routes
to a registered ResourceProvider. Without one, it must reply with a JSON-RPC
error rather than crashing.

Note: resourceStat is not part of the canonical protocol.
"""

from __future__ import annotations

import json

from ahp.transport.memory import InMemoryTransport
from ahp.types import ResourceListResult, ResourceReadResult

from _helpers import initialized_client


class FakeResourceProvider:
    """Minimal in-memory resource provider for routing tests."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.write_calls: list[tuple[str, str]] = []

    async def read(self, uri: str) -> ResourceReadResult:
        return ResourceReadResult(
            data=self.files.get(uri, ""),
            encoding="utf-8",
        )

    async def write(self, uri: str, data: str, encoding: str = "utf-8") -> None:
        self.write_calls.append((uri, data))
        self.files[uri] = data

    async def list(self, uri: str) -> ResourceListResult:
        return ResourceListResult(
            entries=[{"uri": u} for u in self.files if u.startswith(uri)]
        )


async def send_host_request(host_transport, request_id: int, method: str, params: dict) -> dict:
    """Send a host→client JSON-RPC request and return the decoded response."""
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
        {"uri": "ahp-resource:/notes.txt", "data": "written by host", "encoding": "utf-8"},
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

    response = await send_host_request(
        host_transport, 1001, "resourceList", {"uri": "ahp-resource:/", "channel": "ahp-root://"}
    )

    assert sorted(e["uri"] for e in response["result"]["entries"]) == [
        "ahp-resource:/a.txt",
        "ahp-resource:/b.txt",
    ]


async def test_host_resource_call_without_registered_provider_replies_with_error():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)
    # deliberately no provider registered

    response = await send_host_request(
        host_transport, 1003, "resourceRead", {"uri": "ahp-resource:/x.txt"}
    )

    assert "error" in response
    assert response["error"]["code"] is not None


async def test_host_resource_call_when_provider_raises_replies_with_error_not_crash():
    client_transport, host_transport = InMemoryTransport.pair()
    client = await initialized_client(client_transport, host_transport)

    class ExplodingProvider(FakeResourceProvider):
        async def read(self, uri: str) -> ResourceReadResult:
            raise RuntimeError("disk on fire")

    client.register_resource_provider(ExplodingProvider())

    response = await send_host_request(
        host_transport, 1004, "resourceRead", {"uri": "ahp-resource:/x.txt"}
    )
    assert "error" in response

    # Reader loop must survive the exception; next request still works.
    response2 = await send_host_request(
        host_transport, 1005, "resourceList", {"uri": "ahp-resource:/", "channel": "ahp-root://"}
    )
    assert "error" not in response2
