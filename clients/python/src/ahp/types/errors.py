"""JSON-RPC error envelope and AHP-specific error codes.

AHP uses JSON-RPC 2.0 error objects on the wire; this module models that envelope
plus the AHP-specific error code range, and provides ``AhpError``, the exception
raised client-side when a command response carries an error.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from .common import AhpModel


class JsonRpcErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 reserved error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class AhpErrorCode(IntEnum):
    """AHP-specific error codes, in the JSON-RPC "server error" reserved range
    (-32000 to -32099).

    NOTE: exact code values below are placeholders pending confirmation against
    the upstream ``docs/specification`` error-code table; update this enum once
    that page has been reviewed (tracked in SPEC.md open questions).
    """

    PROTOCOL_VERSION_MISMATCH = -32000
    NOT_INITIALIZED = -32001
    UNKNOWN_CHANNEL = -32002
    SUBSCRIPTION_REQUIRED = -32003
    STALE_CLIENT_SEQ = -32004
    RESOURCE_NOT_FOUND = -32005
    AUTHENTICATION_REQUIRED = -32006
    AUTHENTICATION_FAILED = -32007
    SESSION_DISPOSED = -32008
    OPERATION_NOT_SUPPORTED = -32009


class JsonRpcErrorObject(AhpModel):
    """The ``error`` member of a JSON-RPC 2.0 error response."""

    code: int
    message: str
    data: Any | None = None


class AhpError(Exception):
    """Raised by :class:`ahp.client.AhpClient` when a command response contains a
    JSON-RPC error, or when a protocol-level invariant is violated locally
    (e.g. a message arrives before initialization completes).
    """

    def __init__(self, error: JsonRpcErrorObject) -> None:
        self.error = error
        super().__init__(f"[{error.code}] {error.message}")

    @property
    def code(self) -> int:
        return self.error.code

    @property
    def message(self) -> str:
        return self.error.message

    @property
    def data(self) -> Any | None:
        return self.error.data

    @classmethod
    def from_response(cls, error_dict: dict[str, Any]) -> "AhpError":
        return cls(JsonRpcErrorObject.model_validate(error_dict))
