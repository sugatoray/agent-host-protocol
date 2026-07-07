"""Common wire types shared across the AHP protocol.

Mirrors ``types/common/state.ts`` + ``types/common/actions.ts`` primitives.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Primitive aliases
# ---------------------------------------------------------------------------

URI = str
ServerSeq = int
ClientSeq = int


class AhpModel(BaseModel):
    """Base class for all AHP wire types."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


# ---------------------------------------------------------------------------
# Protected resource metadata (RFC 9728) — types/common/state.ts
# ---------------------------------------------------------------------------


class ProtectedResourceMetadata(AhpModel):
    """OAuth 2.0 Protected Resource Metadata (RFC 9728), snake_case per the RFC."""

    resource: str
    resource_name: str | None = None
    authorization_servers: list[str] | None = None
    jwks_uri: str | None = None
    scopes_supported: list[str] | None = None
    bearer_methods_supported: list[str] | None = None
    resource_signing_alg_values_supported: list[str] | None = None
    resource_encryption_alg_values_supported: list[str] | None = None
    resource_encryption_enc_values_supported: list[str] | None = None
    resource_documentation: str | None = None
    resource_policy_uri: str | None = None
    resource_tos_uri: str | None = None
    required: bool | None = None


# ---------------------------------------------------------------------------
# Content reference
# ---------------------------------------------------------------------------


class ContentRef(AhpModel):
    """Reference to content stored outside the state tree (types/common/state.ts)."""

    uri: URI
    size_hint: int | None = Field(default=None, alias="sizeHint")
    content_type: str | None = Field(default=None, alias="contentType")
    nonce: str | None = None


# ---------------------------------------------------------------------------
# Error info (embedded in state, distinct from JSON-RPC error envelope)
# ---------------------------------------------------------------------------


class ErrorInfo(AhpModel):
    """Structured error embedded in state (types/common/state.ts)."""

    error_type: str = Field(alias="errorType")
    message: str
    stack: str | None = None
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------


class Snapshot(AhpModel):
    """Point-in-time state snapshot for a channel (types/common/state.ts).

    Field names match the wire: ``resource`` (channel URI) and ``fromSeq``
    (the serverSeq at which this snapshot was taken).
    """

    resource: URI
    from_seq: ServerSeq = Field(alias="fromSeq")
    state: Any  # narrowed per-channel at call sites


# ---------------------------------------------------------------------------
# Action origin / envelope
# ---------------------------------------------------------------------------


class ActionOrigin(AhpModel):
    """Identifies the client that dispatched an action (types/common/actions.ts)."""

    client_id: str = Field(alias="clientId")
    client_seq: ClientSeq = Field(alias="clientSeq")


class ActionEnvelope(AhpModel):
    """Wraps a StateAction with routing + provenance metadata (types/common/actions.ts).

    ``server_seq`` is required (host always stamps actions before broadcast).
    ``rejection_reason`` is set when the server rejected the action but still
    echoes it back so the originating client can roll back optimistic state.
    """

    channel: URI
    server_seq: ServerSeq = Field(alias="serverSeq")
    action: dict[str, Any]
    origin: ActionOrigin | None = None
    rejection_reason: str | None = Field(default=None, alias="rejectionReason")


# ---------------------------------------------------------------------------
# Capabilities (negotiated at `initialize`)
# ---------------------------------------------------------------------------


class ClientCapabilities(AhpModel):
    """Capabilities the client advertises during ``initialize`` (types/common/commands.ts).

    Each field is a presence flag — an empty dict {} means "supported".
    ``mcpApps`` signals the client can render MCP App Views.
    """

    mcp_apps: dict[str, Any] | None = Field(default=None, alias="mcpApps")


# ProtocolVersion is a SemVer string (e.g. "0.1.0"), negotiated during initialize.
ProtocolVersion = str
