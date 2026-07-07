"""Common wire types shared across the AHP protocol.

These mirror the shapes described in the protocol specification's "Common Types"
reference page (https://microsoft.github.io/agent-host-protocol/reference/common.html)
and the equivalent hand-written types in ``ahp-types`` (Rust) / ``ahptypes`` (Go) /
``@microsoft/agent-host-protocol`` (TypeScript).

NOTE: This is a hand-written first pass, not a codegen output. Field sets should be
verified/extended against ``schema/*.schema.json`` in the upstream repo as that
review happens (see SPEC.md open questions).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Primitive aliases
# ---------------------------------------------------------------------------

# AHP resources, sessions, chats, terminals, etc. are all addressed by URI, e.g.
# "agenthost:/root", "ahp-session:/<uuid>", "ahp-log://warn".
URI = str

# Monotonically increasing sequence number the host stamps on every mutation it
# broadcasts. Used for ordering and for detecting missed messages on reconnect.
ServerSeq = int

# Monotonically increasing sequence number a single client assigns to its own
# outgoing actions, used together with ``client_id`` to identify the origin of
# an action for write-ahead reconciliation.
ClientSeq = int


class AhpModel(BaseModel):
    """Base class for all AHP wire types.

    - ``populate_by_name`` allows constructing models with either the Python
      (snake_case) field name or the wire (camelCase) alias.
    - Unknown fields from the wire are preserved rather than rejected, since the
      protocol may add optional fields in minor/patch versions and clients
      should not hard-fail on forward-compatible payloads.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


# ---------------------------------------------------------------------------
# Actor / origin
# ---------------------------------------------------------------------------


class ActionOrigin(AhpModel):
    """Identifies which client produced an action, for write-ahead reconciliation.

    The client stamps its own outgoing actions with ``(client_id, client_seq)``.
    When the server echoes the action back (see ``notifications.ActionNotification``),
    the client matches it against its own optimistically-applied local copy via this
    origin before treating it as a "foreign" (other-client) mutation.
    """

    client_id: str = Field(alias="clientId")
    client_seq: ClientSeq = Field(alias="clientSeq")


# ---------------------------------------------------------------------------
# Content references (attachments, files, images, etc. referenced from turns)
# ---------------------------------------------------------------------------


class ContentRef(AhpModel):
    """A reference to content (e.g. a file, image, or blob) associated with a
    session/turn, resolved lazily via the ``resource*`` command family rather than
    inlined into state snapshots.
    """

    uri: URI
    mime_type: str | None = Field(default=None, alias="mimeType")
    name: str | None = None
    size: int | None = None


# ---------------------------------------------------------------------------
# Error info (distinct from JSON-RPC error envelope, see errors.py)
# ---------------------------------------------------------------------------


class ErrorInfo(AhpModel):
    """Structured error detail embedded in state (e.g. a failed turn), as opposed
    to a JSON-RPC transport-level error (see ``errors.JsonRpcErrorObject``).
    """

    message: str
    code: str | None = None
    detail: Any | None = None


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------


class Snapshot(AhpModel):
    """A point-in-time, full-state snapshot of a channel, returned by
    ``initialize``/``subscribe``/``reconnect`` when the client has no (or a stale)
    local copy and the host decides to resend full state rather than a replay of
    missed actions.
    """

    channel: URI
    server_seq: ServerSeq = Field(alias="serverSeq")
    state: Any  # narrowed per-channel by state.py's discriminated per-channel types


# ---------------------------------------------------------------------------
# Action envelope
# ---------------------------------------------------------------------------


class ActionEnvelope(AhpModel):
    """Wraps a ``StateAction`` (see actions.py) with routing + provenance metadata.

    This is the shape carried by both the client's outgoing ``dispatchAction``
    command and the server's outgoing ``action`` notification.
    """

    channel: URI
    server_seq: ServerSeq | None = Field(default=None, alias="serverSeq")
    origin: ActionOrigin | None = None
    action: dict[str, Any]  # replaced by the concrete StateAction union at call sites


# ---------------------------------------------------------------------------
# Capabilities (negotiated at `initialize`)
# ---------------------------------------------------------------------------


class ClientCapabilities(AhpModel):
    """Capabilities the client advertises during ``initialize``."""

    resources: bool = False
    """Whether this client can serve `resource*` calls initiated by the server."""

    authentication: bool = False
    """Whether this client can respond to `auth/required` challenges."""


class HostCapabilities(AhpModel):
    """Capabilities the host advertises back during ``initialize``."""

    channels: list[str] = Field(default_factory=list)
    """Channel URI schemes this host supports (e.g. session, chat, terminal)."""

    changesets: bool = False
    completions: bool = False


ProtocolVersion = Literal[1]
"""Current stable AHP protocol version. Negotiated during `initialize`; a
major-version mismatch is rejected at handshake per the specification."""
