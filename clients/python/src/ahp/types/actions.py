"""StateAction — the discriminated union of every mutation the reducers understand.

Reconciled against ``types/common/actions.ts`` and per-channel ``actions.ts`` files.
Only variants that reducers actively handle are fully typed; the aggregate
``StateAction`` union catches all remaining variants as generic dicts via the
``AhpModel`` base + ``extra="allow"``.

Extension pattern
-----------------
1. Add an ``AhpModel`` subclass with ``type: Literal["<family>/<eventName>"]``.
2. Add it to the relevant ``...Action`` union.
3. Add a matching branch in ``ahp.reducers.<family>``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field

from .common import AhpModel, URI

# ---------------------------------------------------------------------------
# Root actions — types/channels-root/actions.ts
# ---------------------------------------------------------------------------


class RootAgentsChangedAction(AhpModel):
    type: Literal["root/agentsChanged"] = "root/agentsChanged"
    agents: list[Any]  # list[AgentInfo]


class RootActiveSessionsChangedAction(AhpModel):
    type: Literal["root/activeSessionsChanged"] = "root/activeSessionsChanged"
    active_sessions: int = Field(alias="activeSessions")


class RootTerminalsChangedAction(AhpModel):
    type: Literal["root/terminalsChanged"] = "root/terminalsChanged"
    terminals: list[Any]  # list[TerminalInfo]


class RootConfigChangedAction(AhpModel):
    type: Literal["root/configChanged"] = "root/configChanged"
    config: dict[str, Any]
    replace: bool | None = None


RootAction = Annotated[
    Union[
        RootAgentsChangedAction,
        RootActiveSessionsChangedAction,
        RootTerminalsChangedAction,
        RootConfigChangedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Session actions — types/channels-session/actions.ts (key variants)
# ---------------------------------------------------------------------------


class SessionReadyAction(AhpModel):
    type: Literal["session/ready"] = "session/ready"


class SessionCreationFailedAction(AhpModel):
    type: Literal["session/creationFailed"] = "session/creationFailed"
    error: dict[str, Any]  # ErrorInfo


class SessionTitleChangedAction(AhpModel):
    type: Literal["session/titleChanged"] = "session/titleChanged"
    title: str


class SessionIsReadChangedAction(AhpModel):
    type: Literal["session/isReadChanged"] = "session/isReadChanged"
    is_read: bool = Field(alias="isRead")


class SessionIsArchivedChangedAction(AhpModel):
    type: Literal["session/isArchivedChanged"] = "session/isArchivedChanged"
    is_archived: bool = Field(alias="isArchived")


class SessionActivityChangedAction(AhpModel):
    type: Literal["session/activityChanged"] = "session/activityChanged"
    activity: str | None


class SessionChatAddedAction(AhpModel):
    type: Literal["session/chatAdded"] = "session/chatAdded"
    summary: dict[str, Any]  # ChatSummary


class SessionChatRemovedAction(AhpModel):
    type: Literal["session/chatRemoved"] = "session/chatRemoved"
    chat: URI


class SessionChatUpdatedAction(AhpModel):
    type: Literal["session/chatUpdated"] = "session/chatUpdated"
    chat: URI
    changes: dict[str, Any]


class SessionDefaultChatChangedAction(AhpModel):
    type: Literal["session/defaultChatChanged"] = "session/defaultChatChanged"
    default_chat: URI | None = Field(default=None, alias="defaultChat")


class SessionServerToolsChangedAction(AhpModel):
    type: Literal["session/serverToolsChanged"] = "session/serverToolsChanged"
    tools: list[Any]


class SessionActiveClientSetAction(AhpModel):
    type: Literal["session/activeClientSet"] = "session/activeClientSet"
    active_client: dict[str, Any] = Field(alias="activeClient")


class SessionActiveClientRemovedAction(AhpModel):
    type: Literal["session/activeClientRemoved"] = "session/activeClientRemoved"
    client_id: str = Field(alias="clientId")


class SessionInputNeededSetAction(AhpModel):
    type: Literal["session/inputNeededSet"] = "session/inputNeededSet"
    request: dict[str, Any]


class SessionInputNeededRemovedAction(AhpModel):
    type: Literal["session/inputNeededRemoved"] = "session/inputNeededRemoved"
    id: str


class SessionCustomizationsChangedAction(AhpModel):
    type: Literal["session/customizationsChanged"] = "session/customizationsChanged"
    customizations: list[Any]


class SessionCustomizationToggledAction(AhpModel):
    type: Literal["session/customizationToggled"] = "session/customizationToggled"
    id: str
    enabled: bool


class SessionCustomizationUpdatedAction(AhpModel):
    type: Literal["session/customizationUpdated"] = "session/customizationUpdated"
    customization: dict[str, Any]


class SessionCustomizationRemovedAction(AhpModel):
    type: Literal["session/customizationRemoved"] = "session/customizationRemoved"
    id: str


class SessionMcpServerStateChangedAction(AhpModel):
    type: Literal["session/mcpServerStateChanged"] = "session/mcpServerStateChanged"
    id: str
    state: dict[str, Any]
    channel: URI | None = None


class SessionChangesetsChangedAction(AhpModel):
    type: Literal["session/changesetsChanged"] = "session/changesetsChanged"
    changesets: list[Any] | None


class SessionConfigChangedAction(AhpModel):
    type: Literal["session/configChanged"] = "session/configChanged"
    config: dict[str, Any]
    replace: bool | None = None


class SessionMetaChangedAction(AhpModel):
    type: Literal["session/metaChanged"] = "session/metaChanged"
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


SessionAction = Annotated[
    Union[
        SessionReadyAction,
        SessionCreationFailedAction,
        SessionTitleChangedAction,
        SessionIsReadChangedAction,
        SessionIsArchivedChangedAction,
        SessionActivityChangedAction,
        SessionChatAddedAction,
        SessionChatRemovedAction,
        SessionChatUpdatedAction,
        SessionDefaultChatChangedAction,
        SessionServerToolsChangedAction,
        SessionActiveClientSetAction,
        SessionActiveClientRemovedAction,
        SessionInputNeededSetAction,
        SessionInputNeededRemovedAction,
        SessionCustomizationsChangedAction,
        SessionCustomizationToggledAction,
        SessionCustomizationUpdatedAction,
        SessionCustomizationRemovedAction,
        SessionMcpServerStateChangedAction,
        SessionChangesetsChangedAction,
        SessionConfigChangedAction,
        SessionMetaChangedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Chat actions — types/channels-chat/actions.ts (key variants)
# ---------------------------------------------------------------------------


class ChatTurnStartedAction(AhpModel):
    type: Literal["chat/turnStarted"] = "chat/turnStarted"
    turn_id: str = Field(alias="turnId")
    message: dict[str, Any]  # Message
    queued_message_id: str | None = Field(default=None, alias="queuedMessageId")
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class ChatDeltaAction(AhpModel):
    """Streaming text chunk appended to a specific response part."""

    type: Literal["chat/delta"] = "chat/delta"
    turn_id: str = Field(alias="turnId")
    part_id: str = Field(alias="partId")
    content: str
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class ChatResponsePartAction(AhpModel):
    type: Literal["chat/responsePart"] = "chat/responsePart"
    turn_id: str = Field(alias="turnId")
    part: dict[str, Any]  # ResponsePart


class ChatToolCallStartAction(AhpModel):
    type: Literal["chat/toolCallStart"] = "chat/toolCallStart"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    display_name: str = Field(alias="displayName")
    intention: str | None = None
    contributor: dict[str, Any] | None = None
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class ChatToolCallDeltaAction(AhpModel):
    type: Literal["chat/toolCallDelta"] = "chat/toolCallDelta"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    content: str
    invocation_message: Any | None = Field(default=None, alias="invocationMessage")
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class ChatToolCallReadyAction(AhpModel):
    type: Literal["chat/toolCallReady"] = "chat/toolCallReady"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    invocation_message: Any = Field(alias="invocationMessage")
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class ChatToolCallConfirmedAction(AhpModel):
    type: Literal["chat/toolCallConfirmed"] = "chat/toolCallConfirmed"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    approved: bool  # True=approved, False=denied
    meta: dict[str, Any] | None = Field(default=None, alias="_meta")


class ChatToolCallCompleteAction(AhpModel):
    type: Literal["chat/toolCallComplete"] = "chat/toolCallComplete"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    result: dict[str, Any]  # ToolCallResult


class ChatToolCallResultConfirmedAction(AhpModel):
    type: Literal["chat/toolCallResultConfirmed"] = "chat/toolCallResultConfirmed"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    approved: bool


class ChatToolCallContentChangedAction(AhpModel):
    type: Literal["chat/toolCallContentChanged"] = "chat/toolCallContentChanged"
    turn_id: str = Field(alias="turnId")
    tool_call_id: str = Field(alias="toolCallId")
    content: list[Any]


class ChatTurnCompleteAction(AhpModel):
    type: Literal["chat/turnComplete"] = "chat/turnComplete"
    turn_id: str = Field(alias="turnId")


class ChatTurnCancelledAction(AhpModel):
    type: Literal["chat/turnCancelled"] = "chat/turnCancelled"
    turn_id: str = Field(alias="turnId")


class ChatErrorAction(AhpModel):
    type: Literal["chat/error"] = "chat/error"
    turn_id: str = Field(alias="turnId")
    error: dict[str, Any]  # ErrorInfo


class ChatActivityChangedAction(AhpModel):
    type: Literal["chat/activityChanged"] = "chat/activityChanged"
    activity: str | None


class ChatUsageAction(AhpModel):
    type: Literal["chat/usage"] = "chat/usage"
    turn_id: str = Field(alias="turnId")
    usage: dict[str, Any]  # UsageInfo


class ChatReasoningAction(AhpModel):
    type: Literal["chat/reasoning"] = "chat/reasoning"
    turn_id: str = Field(alias="turnId")
    part_id: str = Field(alias="partId")
    content: str


class ChatTruncatedAction(AhpModel):
    type: Literal["chat/truncated"] = "chat/truncated"
    turn_id: str = Field(alias="turnId")


class ChatTurnsLoadedAction(AhpModel):
    type: Literal["chat/turnsLoaded"] = "chat/turnsLoaded"
    turns: list[Any]  # list[Turn]
    next_cursor: str | None = Field(default=None, alias="nextCursor")


class ChatPendingMessageSetAction(AhpModel):
    type: Literal["chat/pendingMessageSet"] = "chat/pendingMessageSet"
    kind: str  # PendingMessageKind: 'steering' | 'queued'
    id: str
    message: dict[str, Any]


class ChatPendingMessageRemovedAction(AhpModel):
    type: Literal["chat/pendingMessageRemoved"] = "chat/pendingMessageRemoved"
    kind: str  # PendingMessageKind
    id: str


class ChatQueuedMessagesReorderedAction(AhpModel):
    type: Literal["chat/queuedMessagesReordered"] = "chat/queuedMessagesReordered"
    order: list[str]  # canonical field name (was "ids")


class ChatDraftChangedAction(AhpModel):
    type: Literal["chat/draftChanged"] = "chat/draftChanged"
    draft: dict[str, Any] | None


class ChatInputRequestedAction(AhpModel):
    type: Literal["chat/inputRequested"] = "chat/inputRequested"
    request: dict[str, Any]


class ChatInputAnswerChangedAction(AhpModel):
    type: Literal["chat/inputAnswerChanged"] = "chat/inputAnswerChanged"
    request_id: str = Field(alias="requestId")
    question_id: str = Field(alias="questionId")
    answer: dict[str, Any] | None = None


class ChatInputCompletedAction(AhpModel):
    type: Literal["chat/inputCompleted"] = "chat/inputCompleted"
    request_id: str = Field(alias="requestId")
    response: str  # ChatInputResponseKind: 'accepted' | 'declined' | 'cancelled'
    answers: dict[str, Any] | None = None


ChatAction = Annotated[
    Union[
        ChatTurnStartedAction,
        ChatDeltaAction,
        ChatResponsePartAction,
        ChatToolCallStartAction,
        ChatToolCallDeltaAction,
        ChatToolCallReadyAction,
        ChatToolCallConfirmedAction,
        ChatToolCallCompleteAction,
        ChatToolCallResultConfirmedAction,
        ChatToolCallContentChangedAction,
        ChatTurnCompleteAction,
        ChatTurnCancelledAction,
        ChatErrorAction,
        ChatActivityChangedAction,
        ChatUsageAction,
        ChatReasoningAction,
        ChatTruncatedAction,
        ChatTurnsLoadedAction,
        ChatPendingMessageSetAction,
        ChatPendingMessageRemovedAction,
        ChatQueuedMessagesReorderedAction,
        ChatDraftChangedAction,
        ChatInputRequestedAction,
        ChatInputAnswerChangedAction,
        ChatInputCompletedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Terminal actions — types/channels-terminal/actions.ts
# ---------------------------------------------------------------------------


class TerminalDataAction(AhpModel):
    """Output data from the pty (server → client)."""

    type: Literal["terminal/data"] = "terminal/data"
    data: str


class TerminalInputAction(AhpModel):
    """Keyboard input sent to the terminal (client → pty, reducer no-op)."""

    type: Literal["terminal/input"] = "terminal/input"
    data: str


class TerminalResizedAction(AhpModel):
    type: Literal["terminal/resized"] = "terminal/resized"
    cols: int
    rows: int


class TerminalClaimedAction(AhpModel):
    type: Literal["terminal/claimed"] = "terminal/claimed"
    claim: dict[str, Any]  # TerminalClaim


class TerminalTitleChangedAction(AhpModel):
    type: Literal["terminal/titleChanged"] = "terminal/titleChanged"
    title: str


class TerminalCwdChangedAction(AhpModel):
    type: Literal["terminal/cwdChanged"] = "terminal/cwdChanged"
    cwd: str


class TerminalExitedAction(AhpModel):
    type: Literal["terminal/exited"] = "terminal/exited"
    exit_code: int | None = Field(default=None, alias="exitCode")


class TerminalClearedAction(AhpModel):
    type: Literal["terminal/cleared"] = "terminal/cleared"


class TerminalCommandDetectionAvailableAction(AhpModel):
    type: Literal["terminal/commandDetectionAvailable"] = "terminal/commandDetectionAvailable"


class TerminalCommandExecutedAction(AhpModel):
    type: Literal["terminal/commandExecuted"] = "terminal/commandExecuted"
    command_id: str = Field(alias="commandId")
    command_line: str = Field(alias="commandLine")
    timestamp: int


class TerminalCommandFinishedAction(AhpModel):
    type: Literal["terminal/commandFinished"] = "terminal/commandFinished"
    command_id: str = Field(alias="commandId")
    exit_code: int | None = Field(default=None, alias="exitCode")
    duration_ms: int | None = Field(default=None, alias="durationMs")


TerminalAction = Annotated[
    Union[
        TerminalDataAction,
        TerminalInputAction,
        TerminalResizedAction,
        TerminalClaimedAction,
        TerminalTitleChangedAction,
        TerminalCwdChangedAction,
        TerminalExitedAction,
        TerminalClearedAction,
        TerminalCommandDetectionAvailableAction,
        TerminalCommandExecutedAction,
        TerminalCommandFinishedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Changeset actions — types/channels-changeset/actions.ts
# ---------------------------------------------------------------------------


class ChangesetStatusChangedAction(AhpModel):
    type: Literal["changeset/statusChanged"] = "changeset/statusChanged"
    status: str  # ChangesetStatus string


class ChangesetFileSetAction(AhpModel):
    type: Literal["changeset/fileSet"] = "changeset/fileSet"
    file: dict[str, Any]  # ChangesetFile


class ChangesetFileRemovedAction(AhpModel):
    type: Literal["changeset/fileRemoved"] = "changeset/fileRemoved"
    file_id: str = Field(alias="fileId")  # canonical field name


class ChangesetContentChangedAction(AhpModel):
    type: Literal["changeset/contentChanged"] = "changeset/contentChanged"
    files: list[Any]  # full replacement file list
    operations: list[Any] | None = None  # full replacement when present
    error: dict[str, Any] | None = None  # ErrorInfo


class ChangesetOperationsChangedAction(AhpModel):
    type: Literal["changeset/operationsChanged"] = "changeset/operationsChanged"
    operations: list[Any] | None


class ChangesetOperationStatusChangedAction(AhpModel):
    type: Literal["changeset/operationStatusChanged"] = "changeset/operationStatusChanged"
    operation_id: str = Field(alias="operationId")
    status: str  # ChangesetOperationStatus string


class ChangesetClearedAction(AhpModel):
    type: Literal["changeset/cleared"] = "changeset/cleared"


ChangesetAction = Annotated[
    Union[
        ChangesetStatusChangedAction,
        ChangesetFileSetAction,
        ChangesetFileRemovedAction,
        ChangesetContentChangedAction,
        ChangesetOperationsChangedAction,
        ChangesetOperationStatusChangedAction,
        ChangesetClearedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Annotations actions — types/channels-annotations/actions.ts
# ---------------------------------------------------------------------------


class AnnotationsSetAction(AhpModel):
    type: Literal["annotations/set"] = "annotations/set"
    annotation: dict[str, Any]  # Annotation


class AnnotationsUpdatedAction(AhpModel):
    type: Literal["annotations/updated"] = "annotations/updated"
    id: str
    changes: dict[str, Any]


class AnnotationsRemovedAction(AhpModel):
    type: Literal["annotations/removed"] = "annotations/removed"
    annotation_id: str = Field(alias="annotationId")


class AnnotationsEntrySetAction(AhpModel):
    type: Literal["annotations/entrySet"] = "annotations/entrySet"
    annotation_id: str = Field(alias="annotationId")
    entry: dict[str, Any]  # AnnotationEntry


class AnnotationsEntryRemovedAction(AhpModel):
    type: Literal["annotations/entryRemoved"] = "annotations/entryRemoved"
    annotation_id: str = Field(alias="annotationId")
    entry_id: str = Field(alias="entryId")


AnnotationsAction = Annotated[
    Union[
        AnnotationsSetAction,
        AnnotationsUpdatedAction,
        AnnotationsRemovedAction,
        AnnotationsEntrySetAction,
        AnnotationsEntryRemovedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Resource-watch actions — types/channels-resource-watch/actions.ts
# ---------------------------------------------------------------------------


class ResourceWatchChangedAction(AhpModel):
    type: Literal["resourceWatch/changed"] = "resourceWatch/changed"
    changes: list[Any]  # list[ResourceChange]


ResourceWatchAction = Annotated[
    Union[ResourceWatchChangedAction],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Aggregate union
# ---------------------------------------------------------------------------

StateAction = Annotated[
    Union[
        # root
        RootAgentsChangedAction,
        RootActiveSessionsChangedAction,
        RootTerminalsChangedAction,
        RootConfigChangedAction,
        # session
        SessionReadyAction,
        SessionCreationFailedAction,
        SessionTitleChangedAction,
        SessionIsReadChangedAction,
        SessionIsArchivedChangedAction,
        SessionActivityChangedAction,
        SessionChatAddedAction,
        SessionChatRemovedAction,
        SessionChatUpdatedAction,
        SessionDefaultChatChangedAction,
        SessionServerToolsChangedAction,
        SessionActiveClientSetAction,
        SessionActiveClientRemovedAction,
        SessionInputNeededSetAction,
        SessionInputNeededRemovedAction,
        SessionCustomizationsChangedAction,
        SessionCustomizationToggledAction,
        SessionCustomizationUpdatedAction,
        SessionCustomizationRemovedAction,
        SessionMcpServerStateChangedAction,
        SessionChangesetsChangedAction,
        SessionConfigChangedAction,
        SessionMetaChangedAction,
        # chat
        ChatTurnStartedAction,
        ChatDeltaAction,
        ChatResponsePartAction,
        ChatToolCallStartAction,
        ChatToolCallDeltaAction,
        ChatToolCallReadyAction,
        ChatToolCallConfirmedAction,
        ChatToolCallCompleteAction,
        ChatToolCallResultConfirmedAction,
        ChatToolCallContentChangedAction,
        ChatTurnCompleteAction,
        ChatTurnCancelledAction,
        ChatErrorAction,
        ChatActivityChangedAction,
        ChatUsageAction,
        ChatReasoningAction,
        ChatTruncatedAction,
        ChatTurnsLoadedAction,
        ChatPendingMessageSetAction,
        ChatPendingMessageRemovedAction,
        ChatQueuedMessagesReorderedAction,
        ChatDraftChangedAction,
        ChatInputRequestedAction,
        ChatInputAnswerChangedAction,
        ChatInputCompletedAction,
        # terminal
        TerminalDataAction,
        TerminalInputAction,
        TerminalResizedAction,
        TerminalClaimedAction,
        TerminalTitleChangedAction,
        TerminalCwdChangedAction,
        TerminalExitedAction,
        TerminalClearedAction,
        TerminalCommandDetectionAvailableAction,
        TerminalCommandExecutedAction,
        TerminalCommandFinishedAction,
        # changeset
        ChangesetStatusChangedAction,
        ChangesetFileSetAction,
        ChangesetFileRemovedAction,
        ChangesetContentChangedAction,
        ChangesetOperationsChangedAction,
        ChangesetOperationStatusChangedAction,
        ChangesetClearedAction,
        # annotations
        AnnotationsSetAction,
        AnnotationsUpdatedAction,
        AnnotationsRemovedAction,
        AnnotationsEntrySetAction,
        AnnotationsEntryRemovedAction,
        # resource-watch
        ResourceWatchChangedAction,
    ],
    Field(discriminator="type"),
]
