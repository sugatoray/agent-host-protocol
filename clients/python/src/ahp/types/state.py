"""Per-channel state shapes.

Each AHP channel (root, session, chat, terminal, changeset, annotations) has its own
state shape, mutated exclusively by the corresponding reducer in ``ahp.reducers``.

PROVISIONAL: field sets here are a representative first pass based on the public
spec/README description of each channel's responsibilities, not a line-by-line port
of the generated TS/Rust types yet. Expect this file to grow once compared against
``schema/*.schema.json`` upstream (tracked in SPEC.md open questions). The intent is
that ``StateAction`` (actions.py) and the reducers (``ahp.reducers``) are additive on
top of these without changing this module's public names.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from .common import AhpModel, ContentRef, ErrorInfo, ServerSeq, URI


class AgentInfo(AhpModel):
    """Describes an agent backend available on the host (e.g. a specific
    provider/model combination), as advertised in root state.
    """

    provider: str
    id: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")


class RootState(AhpModel):
    """State for the well-known root channel (``agenthost:/root``).

    Subscribing here is how a client discovers what agents/sessions exist on a
    host before subscribing to any individual session channel.
    """

    agents: list[AgentInfo] = Field(default_factory=list)
    active_sessions: int | None = Field(default=None, alias="activeSessions")
    session_uris: list[URI] = Field(default_factory=list, alias="sessionUris")


class TurnRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class TurnStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class Turn(AhpModel):
    """A single turn in a chat/session transcript."""

    id: str
    role: TurnRole
    status: TurnStatus = TurnStatus.COMPLETE
    text: str | None = None
    content_refs: list[ContentRef] = Field(default_factory=list, alias="contentRefs")
    error: ErrorInfo | None = None


class SessionState(AhpModel):
    """State for an individual session channel (``ahp-session:/<uuid>``)."""

    uri: URI
    title: str | None = None
    agent: AgentInfo | None = None
    chat_uris: list[URI] = Field(default_factory=list, alias="chatUris")
    terminal_uris: list[URI] = Field(default_factory=list, alias="terminalUris")
    disposed: bool = False


class ChatState(AhpModel):
    """State for a chat channel within a session (``ahp-chat:/<uuid>``)."""

    uri: URI
    session_uri: URI = Field(alias="sessionUri")
    turns: list[Turn] = Field(default_factory=list)
    pending_confirmation: bool = Field(default=False, alias="pendingConfirmation")


class TerminalStatus(str, Enum):
    RUNNING = "running"
    EXITED = "exited"


class TerminalState(AhpModel):
    """State for a terminal channel within a session (``ahp-terminal:/<uuid>``)."""

    uri: URI
    session_uri: URI = Field(alias="sessionUri")
    status: TerminalStatus = TerminalStatus.RUNNING
    exit_code: int | None = Field(default=None, alias="exitCode")
    buffer: str = ""


class ChangesetOperationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


class ChangesetState(AhpModel):
    """State for a changeset channel, tracking proposed edits and their
    acceptance/rejection.
    """

    uri: URI
    session_uri: URI = Field(alias="sessionUri")
    operation_status: ChangesetOperationStatus = Field(
        default=ChangesetOperationStatus.PENDING, alias="operationStatus"
    )


class AnnotationsState(AhpModel):
    """State for an annotations channel (inline comments/markers over session
    content).
    """

    uri: URI
    session_uri: URI = Field(alias="sessionUri")
    annotations: list[dict] = Field(default_factory=list)


AnyChannelState = (
    RootState | SessionState | ChatState | TerminalState | ChangesetState | AnnotationsState
)


class VersionedState(AhpModel):
    """Pairs a channel's state with the server sequence it reflects, so callers
    can tell how "fresh" a given piece of local state is relative to the host.
    """

    server_seq: ServerSeq = Field(alias="serverSeq")
    state: AnyChannelState
