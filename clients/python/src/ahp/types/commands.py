"""AHP command params/result models — the Python equivalent of the upstream
``CommandMap`` / ``ServerCommandMap`` registries.

Each command below is modeled as a ``(Params, Result)`` pair of pydantic models,
plus a ``COMMANDS`` registry dict keyed by wire method name so
``ahp.client.AhpClient`` can validate/serialize generically instead of hand-rolling
each call site.

Commands present: ``initialize``, ``ping``, ``reconnect``, ``subscribe``,
``unsubscribe``, ``dispatchAction``, ``createSession``, ``disposeSession``,
``listSessions``, ``createChat``, ``disposeChat``, ``createTerminal``,
``disposeTerminal``, ``fetchTurns``, ``authenticate``, ``completions``,
``invokeChangesetOperation``, and the ``resource*`` family (``resourceRead``,
``resourceWrite``, ``resourceList``, ``resourceStat``).

The ``resource*`` family is symmetric: the *host* can also invoke these against
the *client* (a client may be asked to read a local file, for instance). They are
modeled once here and reused for both directions; which direction is live in a
given exchange is a transport/client concern, not a typing concern.

PROVISIONAL: params/result field sets are a representative first pass; verify
against ``docs/specification`` command reference tables as that review happens.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .common import (
    URI,
    AhpModel,
    ClientCapabilities,
    ContentRef,
    HostCapabilities,
    ProtocolVersion,
    ServerSeq,
    Snapshot,
)
from .state import AgentInfo, ChangesetOperationStatus, Turn

# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


class InitializeParams(AhpModel):
    protocol_version: ProtocolVersion = Field(alias="protocolVersion")
    client_name: str = Field(alias="clientName")
    client_version: str = Field(alias="clientVersion")
    capabilities: ClientCapabilities = Field(default_factory=ClientCapabilities)


class InitializeResult(AhpModel):
    protocol_version: ProtocolVersion = Field(alias="protocolVersion")
    client_id: str = Field(alias="clientId")
    capabilities: HostCapabilities = Field(default_factory=HostCapabilities)
    root_snapshot: Snapshot = Field(alias="rootSnapshot")


# ---------------------------------------------------------------------------
# ping / reconnect
# ---------------------------------------------------------------------------


class PingParams(AhpModel):
    pass


class PingResult(AhpModel):
    pass


class ReconnectParams(AhpModel):
    client_id: str = Field(alias="clientId")
    last_seen_server_seq: dict[URI, ServerSeq] = Field(
        default_factory=dict, alias="lastSeenServerSeq"
    )
    """Per-channel last-seen sequence, so the host can decide replay vs.
    resnapshot independently for each subscribed channel."""


class ReconnectResult(AhpModel):
    replayed: list[URI] = Field(default_factory=list)
    """Channels the host replayed missed actions for (no snapshot needed)."""

    resnapshotted: list[Snapshot] = Field(default_factory=list)
    """Channels the host decided to resend a full snapshot for instead."""


# ---------------------------------------------------------------------------
# subscribe / unsubscribe
# ---------------------------------------------------------------------------


class SubscribeParams(AhpModel):
    channel: URI


class SubscribeResult(AhpModel):
    snapshot: Snapshot


class UnsubscribeParams(AhpModel):
    channel: URI


class UnsubscribeResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# dispatchAction
# ---------------------------------------------------------------------------


class DispatchActionParams(AhpModel):
    channel: URI
    client_seq: int = Field(alias="clientSeq")
    action: dict[str, Any]
    """Loosely typed here; callers should validate against
    ``ahp.types.actions.StateAction`` before/after this boundary."""


class DispatchActionResult(AhpModel):
    server_seq: ServerSeq = Field(alias="serverSeq")


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


class CreateSessionParams(AhpModel):
    agent: AgentInfo | None = None
    title: str | None = None


class CreateSessionResult(AhpModel):
    session_uri: URI = Field(alias="sessionUri")
    snapshot: Snapshot


class DisposeSessionParams(AhpModel):
    session_uri: URI = Field(alias="sessionUri")


class DisposeSessionResult(AhpModel):
    pass


class ListSessionsParams(AhpModel):
    pass


class ListSessionsResult(AhpModel):
    session_uris: list[URI] = Field(default_factory=list, alias="sessionUris")


# ---------------------------------------------------------------------------
# Chat lifecycle
# ---------------------------------------------------------------------------


class CreateChatParams(AhpModel):
    session_uri: URI = Field(alias="sessionUri")


class CreateChatResult(AhpModel):
    chat_uri: URI = Field(alias="chatUri")
    snapshot: Snapshot


class DisposeChatParams(AhpModel):
    chat_uri: URI = Field(alias="chatUri")


class DisposeChatResult(AhpModel):
    pass


class FetchTurnsParams(AhpModel):
    chat_uri: URI = Field(alias="chatUri")
    before_turn_id: str | None = Field(default=None, alias="beforeTurnId")
    limit: int = 50


class FetchTurnsResult(AhpModel):
    turns: list[Turn] = Field(default_factory=list)
    has_more: bool = Field(default=False, alias="hasMore")


# ---------------------------------------------------------------------------
# Terminal lifecycle
# ---------------------------------------------------------------------------


class CreateTerminalParams(AhpModel):
    session_uri: URI = Field(alias="sessionUri")
    shell: str | None = None
    cwd: str | None = None


class CreateTerminalResult(AhpModel):
    terminal_uri: URI = Field(alias="terminalUri")
    snapshot: Snapshot


class DisposeTerminalParams(AhpModel):
    terminal_uri: URI = Field(alias="terminalUri")


class DisposeTerminalResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class AuthenticateParams(AhpModel):
    scheme: str
    credentials: dict[str, Any] = Field(default_factory=dict)


class AuthenticateResult(AhpModel):
    authenticated: bool


# ---------------------------------------------------------------------------
# Completions
# ---------------------------------------------------------------------------


class CompletionsParams(AhpModel):
    session_uri: URI = Field(alias="sessionUri")
    prefix: str
    kind: str | None = None


class CompletionsResult(AhpModel):
    items: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Changesets
# ---------------------------------------------------------------------------


class InvokeChangesetOperationParams(AhpModel):
    changeset_uri: URI = Field(alias="changesetUri")
    operation: str
    args: dict[str, Any] = Field(default_factory=dict)


class InvokeChangesetOperationResult(AhpModel):
    status: ChangesetOperationStatus


# ---------------------------------------------------------------------------
# Resource family (symmetric: host->client or client->host)
# ---------------------------------------------------------------------------


class ResourceReadParams(AhpModel):
    uri: URI


class ResourceReadResult(AhpModel):
    content_ref: ContentRef = Field(alias="contentRef")
    data: str
    """Base64-encoded bytes, or raw text for text mime types — mirrors the
    binary/text split used by ``resource*`` calls elsewhere in the protocol."""


class ResourceWriteParams(AhpModel):
    uri: URI
    data: str


class ResourceWriteResult(AhpModel):
    pass


class ResourceListParams(AhpModel):
    uri: URI


class ResourceListResult(AhpModel):
    entries: list[ContentRef] = Field(default_factory=list)


class ResourceStatParams(AhpModel):
    uri: URI


class ResourceStatResult(AhpModel):
    content_ref: ContentRef = Field(alias="contentRef")
    exists: bool


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

COMMANDS: dict[str, tuple[type[AhpModel], type[AhpModel]]] = {
    "initialize": (InitializeParams, InitializeResult),
    "ping": (PingParams, PingResult),
    "reconnect": (ReconnectParams, ReconnectResult),
    "subscribe": (SubscribeParams, SubscribeResult),
    "unsubscribe": (UnsubscribeParams, UnsubscribeResult),
    "dispatchAction": (DispatchActionParams, DispatchActionResult),
    "createSession": (CreateSessionParams, CreateSessionResult),
    "disposeSession": (DisposeSessionParams, DisposeSessionResult),
    "listSessions": (ListSessionsParams, ListSessionsResult),
    "createChat": (CreateChatParams, CreateChatResult),
    "disposeChat": (DisposeChatParams, DisposeChatResult),
    "fetchTurns": (FetchTurnsParams, FetchTurnsResult),
    "createTerminal": (CreateTerminalParams, CreateTerminalResult),
    "disposeTerminal": (DisposeTerminalParams, DisposeTerminalResult),
    "authenticate": (AuthenticateParams, AuthenticateResult),
    "completions": (CompletionsParams, CompletionsResult),
    "invokeChangesetOperation": (
        InvokeChangesetOperationParams,
        InvokeChangesetOperationResult,
    ),
    "resourceRead": (ResourceReadParams, ResourceReadResult),
    "resourceWrite": (ResourceWriteParams, ResourceWriteResult),
    "resourceList": (ResourceListParams, ResourceListResult),
    "resourceStat": (ResourceStatParams, ResourceStatResult),
}
"""Wire method name -> (Params model, Result model). Used by AhpClient to
validate outgoing params and parse incoming results generically."""
