"""JSON-RPC 2.0 message envelope.

AHP commands/notifications ride on top of plain JSON-RPC 2.0. This module models
the transport-level envelope only; the AHP-specific ``method`` names and
``params``/``result`` payload shapes live in ``commands.py`` and
``notifications.py``.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import Field

from .common import AhpModel
from .errors import JsonRpcErrorObject

RequestId = Union[str, int]


class JsonRpcRequest(AhpModel):
    """A JSON-RPC request: expects exactly one matching response, correlated by
    ``id``. Used for AHP commands (``initialize``, ``subscribe``,
    ``dispatchAction``, the ``resource*`` family, etc.).
    """

    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId
    method: str
    params: dict[str, Any] | None = None


class JsonRpcResponseSuccess(AhpModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId
    result: Any


class JsonRpcResponseError(AhpModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId | None
    error: JsonRpcErrorObject


JsonRpcResponse = Union[JsonRpcResponseSuccess, JsonRpcResponseError]


class JsonRpcNotification(AhpModel):
    """A JSON-RPC notification: no ``id``, no response expected. Used for AHP
    server->client pushes such as the ``action`` notification, ``root/sessionAdded``,
    ``auth/required``, and ``otlp/*`` telemetry.
    """

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] | None = None


ProtocolMessage = Union[JsonRpcRequest, JsonRpcResponseSuccess, JsonRpcResponseError, JsonRpcNotification]
"""Any message that can appear on the wire in either direction."""


def parse_protocol_message(raw: dict[str, Any]) -> ProtocolMessage:
    """Discriminate a decoded JSON object into the correct envelope type.

    JSON-RPC doesn't carry an explicit discriminator field for this, so we infer
    the shape the same way every JSON-RPC implementation does:
      - has ``method`` and no ``id``       -> notification
      - has ``method`` and ``id``          -> request
      - has ``result``                     -> success response
      - has ``error``                      -> error response
    """
    if "method" in raw:
        if "id" in raw:
            return JsonRpcRequest.model_validate(raw)
        return JsonRpcNotification.model_validate(raw)
    if "error" in raw:
        return JsonRpcResponseError.model_validate(raw)
    if "result" in raw:
        return JsonRpcResponseSuccess.model_validate(raw)
    raise ValueError(f"Unrecognized JSON-RPC message shape: {raw!r}")
