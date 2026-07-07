"""AHP command params/result models — reconciled against canonical TS CommandMap.

Each command is a (Params, Result) pair of pydantic models.
``COMMANDS`` registry maps wire method name → (Params, Result) for generic
serialization/validation in ahp.client.AhpClient.

``dispatchAction`` is NOT in this registry — it is a fire-and-forget notification
on the wire (no response), handled separately in the client.

Canonical sources:
  - types/common/commands.ts
  - types/channels-session/commands.ts
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field

from .common import (
    URI,
    ActionEnvelope,
    AhpModel,
    ClientCapabilities,
    ProtocolVersion,
    ServerSeq,
    Snapshot,
)

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class BaseParams(AhpModel):
    channel: URI = "ahp-root://"


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


class InitializeParams(BaseParams):
    """types/common/commands.ts InitializeParams.

    The client generates its own ``clientId`` UUID before calling initialize.
    """

    channel: URI = "ahp-root://"
    protocol_versions: list[ProtocolVersion] = Field(alias="protocolVersions")
    client_id: str = Field(alias="clientId")
    initial_subscriptions: list[URI] | None = Field(default=None, alias="initialSubscriptions")
    locale: str | None = None
    capabilities: ClientCapabilities | None = None


class InitializeResult(AhpModel):
    protocol_version: ProtocolVersion = Field(alias="protocolVersion")
    server_seq: ServerSeq = Field(alias="serverSeq")
    snapshots: list[Snapshot] = Field(default_factory=list)
    default_directory: str | None = Field(default=None, alias="defaultDirectory")
    completion_trigger_characters: list[str] | None = Field(
        default=None, alias="completionTriggerCharacters"
    )
    telemetry: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# ping
# ---------------------------------------------------------------------------


class PingParams(BaseParams):
    channel: URI = "ahp-root://"


class PingResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# reconnect
# ---------------------------------------------------------------------------


class ReconnectParams(AhpModel):
    channel: URI
    client_id: str = Field(alias="clientId")
    last_seen_server_seq: ServerSeq = Field(alias="lastSeenServerSeq")
    subscriptions: list[URI] = Field(default_factory=list)


class ReconnectReplayResult(AhpModel):
    type: Literal["replay"] = "replay"
    actions: list[ActionEnvelope] = Field(default_factory=list)
    missing: list[URI] = Field(default_factory=list)


class ReconnectSnapshotResult(AhpModel):
    type: Literal["snapshot"] = "snapshot"
    snapshots: list[Snapshot] = Field(default_factory=list)


ReconnectResult = Annotated[
    Union[ReconnectReplayResult, ReconnectSnapshotResult],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# subscribe / unsubscribe
# ---------------------------------------------------------------------------


class SubscribeParams(AhpModel):
    channel: URI
    delivery: str | None = None  # 'snapshot' | 'actions' | 'none'
    view: dict[str, Any] | None = None


class SubscribeResult(AhpModel):
    snapshot: Snapshot | None = None


class UnsubscribeParams(AhpModel):
    channel: URI


class UnsubscribeResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# dispatchAction  — fire-and-forget notification, NOT a command
# Params shape kept here for client-side serialization; no Result model.
# ---------------------------------------------------------------------------


class DispatchActionParams(AhpModel):
    channel: URI
    client_seq: int = Field(alias="clientSeq")
    action: dict[str, Any]


# ---------------------------------------------------------------------------
# Session lifecycle — types/channels-session/commands.ts
# ---------------------------------------------------------------------------


class CreateSessionParams(AhpModel):
    channel: URI
    provider: str | None = None
    working_directory: str | None = Field(default=None, alias="workingDirectory")
    fork: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    active_client: dict[str, Any] | None = Field(default=None, alias="activeClient")
    progress_token: str | int | None = Field(default=None, alias="progressToken")


class CreateSessionResult(AhpModel):
    pass  # TS: result: null


class DisposeSessionParams(BaseParams):
    channel: URI  # session channel URI


class DisposeSessionResult(AhpModel):
    pass


class ListSessionsParams(BaseParams):
    channel: URI = "ahp-root://"
    limit: int | None = None
    cursor: str | None = None


class ListSessionsResult(AhpModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = Field(default=None, alias="nextCursor")


# ---------------------------------------------------------------------------
# Chat lifecycle — types/channels-chat/commands.ts
# ---------------------------------------------------------------------------


class CreateChatParams(AhpModel):
    channel: URI  # session channel URI
    chat: URI  # client-chosen chat URI e.g. ahp-chat:/<uuid>
    initial_message: dict[str, Any] | None = Field(default=None, alias="initialMessage")
    source: dict[str, Any] | None = None  # ChatForkSource


class CreateChatResult(AhpModel):
    pass  # TS: result: null


class DisposeChatParams(AhpModel):
    channel: URI  # chat channel URI


class DisposeChatResult(AhpModel):
    pass


class FetchTurnsParams(AhpModel):
    """types/channels-session/commands.ts FetchTurnsParams."""

    channel: URI  # chat channel URI
    cursor: str | None = None


class FetchTurnsResult(AhpModel):
    pass  # TS: FetchTurnsResult = {}; turns arrive via chat/turnsLoaded action


# ---------------------------------------------------------------------------
# Terminal lifecycle — types/channels-terminal/commands.ts
# ---------------------------------------------------------------------------


class CreateTerminalParams(AhpModel):
    channel: URI  # session channel URI
    claim: dict[str, Any]  # TerminalClaim — required
    name: str | None = None
    cwd: str | None = None
    cols: int | None = None
    rows: int | None = None


class CreateTerminalResult(AhpModel):
    pass  # TS: result: null


class DisposeTerminalParams(AhpModel):
    channel: URI  # terminal channel URI


class DisposeTerminalResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# Authentication — types/common/commands.ts
# ---------------------------------------------------------------------------


class AuthenticateParams(BaseParams):
    channel: URI = "ahp-root://"
    resource: str  # protected resource URI
    token: str


class AuthenticateResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# Completions — types/channels-session/commands.ts
# ---------------------------------------------------------------------------


class CompletionsParams(AhpModel):
    kind: str  # 'provider' | 'model' | 'customization' | ...
    channel: URI
    text: str
    offset: int


class CompletionsResult(AhpModel):
    items: list[Any] = Field(default_factory=list)  # list[CompletionItem]


# ---------------------------------------------------------------------------
# Session config — types/channels-root/commands.ts
# ---------------------------------------------------------------------------


class ResolveSessionConfigParams(AhpModel):
    channel: URI = "ahp-root://"
    provider: str | None = None
    working_directory: URI | None = Field(default=None, alias="workingDirectory")
    config: dict[str, Any] | None = None


class ResolveSessionConfigResult(AhpModel):
    schema_: dict[str, Any] = Field(alias="schema")
    values: dict[str, Any]


class SessionConfigCompletionsParams(AhpModel):
    channel: URI = "ahp-root://"
    provider: str | None = None
    working_directory: URI | None = Field(default=None, alias="workingDirectory")
    config: dict[str, Any] | None = None
    property: str  # property id from the schema to query values for
    query: str | None = None


class SessionConfigCompletionsResult(AhpModel):
    items: list[dict[str, Any]] = Field(default_factory=list)  # list[SessionConfigValueItem]


# ---------------------------------------------------------------------------
# Changesets — types/channels-changeset/commands.ts
# ---------------------------------------------------------------------------


class InvokeChangesetOperationParams(AhpModel):
    channel: URI  # changeset channel URI
    operation_id: str = Field(alias="operationId")
    target: dict[str, Any] | None = None  # ChangesetOperationTarget


class InvokeChangesetOperationResult(AhpModel):
    message: str | dict[str, Any] | None = None  # StringOrMarkdown
    follow_up: dict[str, Any] | None = Field(default=None, alias="followUp")


# ---------------------------------------------------------------------------
# Resource-watch — types/channels-resource-watch/commands.ts
# ---------------------------------------------------------------------------


class CreateResourceWatchParams(AhpModel):
    channel: URI = "ahp-root://"
    uri: URI
    recursive: bool | None = None
    excludes: dict[str, Any] | None = None  # {items: list[str]}
    includes: dict[str, Any] | None = None  # {items: list[str]}


class CreateResourceWatchResult(AhpModel):
    channel: URI  # ahp-resource-watch:/<id>


# ---------------------------------------------------------------------------
# Resource family — types/common/commands.ts
# ---------------------------------------------------------------------------


class ResourceReadParams(AhpModel):
    channel: URI = "ahp-root://"
    uri: URI
    encoding: str | None = None  # 'base64' | 'utf-8'


class ResourceReadResult(AhpModel):
    data: str
    encoding: str
    content_type: str | None = Field(default=None, alias="contentType")


class ResourceWriteParams(AhpModel):
    channel: URI = "ahp-root://"
    uri: URI
    data: str
    encoding: str
    content_type: str | None = Field(default=None, alias="contentType")
    create_only: bool | None = Field(default=None, alias="createOnly")
    mode: str | None = None  # 'overwrite' | 'append' | ...
    position: int | None = None
    if_match: str | None = Field(default=None, alias="ifMatch")


class ResourceWriteResult(AhpModel):
    pass


class ResourceListParams(AhpModel):
    channel: URI
    uri: URI


class ResourceListResult(AhpModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


class ResourceCopyParams(AhpModel):
    source: URI
    destination: URI
    fail_if_exists: bool | None = Field(default=None, alias="failIfExists")


class ResourceCopyResult(AhpModel):
    pass


class ResourceDeleteParams(AhpModel):
    uri: URI
    recursive: bool | None = None


class ResourceDeleteResult(AhpModel):
    pass


class ResourceRequestParams(AhpModel):
    uri: URI
    read: bool | None = None
    write: bool | None = None


class ResourceRequestResult(AhpModel):
    pass


class ResourceMoveParams(AhpModel):
    source: URI
    destination: URI


class ResourceMoveResult(AhpModel):
    pass


class ResourceResolveParams(AhpModel):
    uri: URI
    follow_symlinks: bool | None = Field(default=None, alias="followSymlinks")


class ResourceResolveResult(AhpModel):
    uri: URI


class ResourceMkdirParams(AhpModel):
    uri: URI


class ResourceMkdirResult(AhpModel):
    pass


# ---------------------------------------------------------------------------
# Registry  (dispatchAction excluded — fire-and-forget)
# ---------------------------------------------------------------------------

COMMANDS: dict[str, tuple[type[AhpModel], type[AhpModel]]] = {
    "initialize": (InitializeParams, InitializeResult),
    "ping": (PingParams, PingResult),
    "reconnect": (ReconnectParams, AhpModel),  # result parsed as union at call site
    "subscribe": (SubscribeParams, SubscribeResult),
    "unsubscribe": (UnsubscribeParams, UnsubscribeResult),
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
    "resolveSessionConfig": (ResolveSessionConfigParams, ResolveSessionConfigResult),
    "sessionConfigCompletions": (SessionConfigCompletionsParams, SessionConfigCompletionsResult),
    "invokeChangesetOperation": (InvokeChangesetOperationParams, InvokeChangesetOperationResult),
    "createResourceWatch": (CreateResourceWatchParams, CreateResourceWatchResult),
    "resourceRead": (ResourceReadParams, ResourceReadResult),
    "resourceWrite": (ResourceWriteParams, ResourceWriteResult),
    "resourceList": (ResourceListParams, ResourceListResult),
    "resourceCopy": (ResourceCopyParams, ResourceCopyResult),
    "resourceDelete": (ResourceDeleteParams, ResourceDeleteResult),
    "resourceRequest": (ResourceRequestParams, ResourceRequestResult),
    "resourceMove": (ResourceMoveParams, ResourceMoveResult),
    "resourceResolve": (ResourceResolveParams, ResourceResolveResult),
    "resourceMkdir": (ResourceMkdirParams, ResourceMkdirResult),
}
