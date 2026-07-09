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
    """AHP-specific error codes (``types/common/errors.ts`` ``AhpErrorCodes``)."""

    SESSION_NOT_FOUND = -32001
    PROVIDER_NOT_FOUND = -32002
    SESSION_ALREADY_EXISTS = -32003
    TURN_IN_PROGRESS = -32004
    UNSUPPORTED_PROTOCOL_VERSION = -32005
    CONTENT_NOT_FOUND = -32006
    AUTH_REQUIRED = -32007
    NOT_FOUND = -32008
    PERMISSION_DENIED = -32009
    ALREADY_EXISTS = -32010
    CONFLICT = -32011


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
