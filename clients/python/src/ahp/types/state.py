"""Per-channel state shapes, reconciled against canonical types/*.ts.

Each model matches the wire field names from the TypeScript canonical source
(``types/channels-*/state.ts``). Complex nested types (Turn payload, content
parts, customizations) use ``Any`` where the reducer does not need to inspect
individual sub-fields — expand to typed models as needed.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .common import AhpModel, ServerSeq, URI

# ---------------------------------------------------------------------------
# Root channel — types/channels-root/state.ts
# ---------------------------------------------------------------------------


class AgentInfo(AhpModel):
    """An agent backend advertised on the root channel."""

    provider: str
    display_name: str = Field(alias="displayName")
    description: str = ""
    models: list[Any] = Field(default_factory=list)
    protected_resources: list[Any] | None = Field(default=None, alias="protectedResources")
    customizations: list[Any] | None = None
    capabilities: dict[str, Any] | None = None


class RootState(AhpModel):
    """State for the ``ahp-root://`` channel."""

    agents: list[AgentInfo] = Field(default_factory=list)
    active_sessions: int | None = Field(default=None, alias="activeSessions")
    # ponytail: TerminalInfo[] — typed when terminal channel is expanded
    terminals: list[Any] | None = None
    # ponytail: RootConfigState — typed when config actions are expanded
    config: dict[str, Any] | None = None
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


# ---------------------------------------------------------------------------
# Session channel — types/channels-session/state.ts
# ---------------------------------------------------------------------------


class SessionState(AhpModel):
    """State for an ``ahp-session:`` channel.

    Canonical fields from ``SessionState extends SessionMetadata``.
    Complex nested types (customizations, serverTools, inputNeeded) use Any.
    """

    # from SessionMetadata
    provider: str = ""
    title: str = ""
    # ponytail: SessionStatus bitset (int) — left as int for forward compat
    status: int = 1  # SessionStatus.Idle
    activity: str | None = None
    project: dict[str, Any] | None = None
    working_directory: str | None = Field(default=None, alias="workingDirectory")
    annotations: dict[str, Any] | None = None

    # from SessionState proper
    lifecycle: str = "creating"  # SessionLifecycle enum string
    creation_error: dict[str, Any] | None = Field(default=None, alias="creationError")
    server_tools: list[Any] | None = Field(default=None, alias="serverTools")
    active_clients: list[Any] = Field(default_factory=list, alias="activeClients")
    # ponytail: list[ChatSummary] — typed when chat actions are expanded
    chats: list[Any] = Field(default_factory=list)
    default_chat: URI | None = Field(default=None, alias="defaultChat")
    config: dict[str, Any] | None = None
    customizations: list[Any] | None = None
    changesets: list[Any] | None = None
    input_needed: list[Any] | None = Field(default=None, alias="inputNeeded")
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


# ---------------------------------------------------------------------------
# Chat channel — types/channels-chat/state.ts
# ---------------------------------------------------------------------------


class Turn(AhpModel):
    """A conversation turn in a chat channel (types/channels-chat/state.ts:504-522).

    Only completed turns appear in ChatState.turns; in-progress turns are the
    separate ActiveTurn type. state is therefore always a terminal value.
    """

    id: str
    # ponytail: Message typed shape — Any for now; expand when chat UI needs it
    message: dict[str, Any] = Field(default_factory=dict)
    response_parts: list[Any] = Field(default_factory=list, alias="responseParts")
    usage: dict[str, Any] | None = None
    # TurnState: 'complete' | 'cancelled' | 'error' (types/channels-chat/state.ts:477-481)
    state: Literal["complete", "cancelled", "error"]
    error: dict[str, Any] | None = None


class ChatState(AhpModel):
    """State for an ``ahp-chat:`` channel."""

    resource: URI = ""
    title: str = ""
    # ponytail: ChatStatus — int bitset or str enum per wire
    status: Any = None
    activity: str | None = None
    modified_at: str | None = Field(default=None, alias="modifiedAt")
    # ChatOrigin tagged union: {kind:'user'} | {kind:'fork',chat,turnId} | {kind:'tool',chat,toolCallId}
    origin: dict[str, Any] | None = None
    # ChatInteractivity: 'full' | 'read-only' | 'hidden' (types/channels-chat/state.ts:194-205)
    interactivity: str | None = None
    working_directory: str | None = Field(default=None, alias="workingDirectory")
    turns: list[Turn] = Field(default_factory=list)
    turns_next_cursor: str | None = Field(default=None, alias="turnsNextCursor")
    # activeTurn is an ActiveTurn object on the wire (types/channels-chat/state.ts:529-542)
    active_turn: dict[str, Any] | None = Field(default=None, alias="activeTurn")
    steering_message: Any | None = Field(default=None, alias="steeringMessage")
    queued_messages: list[Any] | None = Field(default=None, alias="queuedMessages")
    input_requests: list[Any] | None = Field(default=None, alias="inputRequests")
    draft: Any | None = None
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


# ---------------------------------------------------------------------------
# Terminal channel — types/channels-terminal/state.ts
# ---------------------------------------------------------------------------


class TerminalState(AhpModel):
    """State for an ``ahp-terminal:`` channel."""

    title: str = ""
    cwd: URI | None = None
    cols: int | None = None
    rows: int | None = None
    # ponytail: list[TerminalContentPart] — Any for now
    content: list[Any] = Field(default_factory=list)
    exit_code: int | None = Field(default=None, alias="exitCode")
    # ponytail: TerminalClaim discriminated union — Any for now
    claim: Any | None = None
    supports_command_detection: bool | None = Field(
        default=None, alias="supportsCommandDetection"
    )


# ---------------------------------------------------------------------------
# Changeset channel — types/channels-changeset/state.ts
# ---------------------------------------------------------------------------


class ChangesetState(AhpModel):
    """State for an ``ahp-changeset:`` channel."""

    status: str = "computing"  # ChangesetStatus enum string
    error: dict[str, Any] | None = None
    files: list[Any] = Field(default_factory=list)
    operations: list[Any] | None = None


# ---------------------------------------------------------------------------
# Annotations channel — types/channels-annotations/state.ts
# ---------------------------------------------------------------------------


class Annotation(AhpModel):
    """A single annotation entry (types/channels-annotations/state.ts)."""

    id: str
    turn_id: str | None = Field(default=None, alias="turnId")
    resource: URI | None = None
    range: dict[str, Any] | None = None
    resolved: bool = False
    # ponytail: list[AnnotationEntry] — Any for now
    entries: list[Any] = Field(default_factory=list)
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class AnnotationsState(AhpModel):
    """State for an ``ahp-annotations:`` channel."""

    annotations: list[Annotation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Resource-watch channel — types/channels-resource-watch/state.ts
# ---------------------------------------------------------------------------


class ResourceWatchState(AhpModel):
    """State for an ``ahp-resource-watch:`` channel.

    Watches are stateless: the reducer never mutates this.
    The state carries only the descriptor of what is being watched.
    """

    root: URI
    recursive: bool
    excludes: dict[str, Any] | None = None  # {items: list[str]}
    includes: dict[str, Any] | None = None  # {items: list[str]}


# ---------------------------------------------------------------------------
# Aggregate union + versioned wrapper
# ---------------------------------------------------------------------------

AnyChannelState = (
    RootState
    | SessionState
    | ChatState
    | TerminalState
    | ChangesetState
    | AnnotationsState
    | ResourceWatchState
)


class VersionedState(AhpModel):
    """Pairs channel state with the server sequence it reflects."""

    server_seq: ServerSeq = Field(alias="serverSeq")
    state: AnyChannelState
