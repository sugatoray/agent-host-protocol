"""``StateAction`` — the discriminated union of every mutation reducers understand.

The full upstream union has on the order of ~80 variants across six channel
families (root/session/chat/terminal/changeset/annotations). This module seeds
each family with the handful of variants needed to exercise the client end-to-end
(subscribe -> dispatch -> reconcile) and documents the extension pattern so the
remaining variants can be added mechanically without touching client/reducer code.

Extension pattern
------------------
1. Add a new ``AhpModel`` subclass with ``type: Literal["<family>/<eventName>"]``.
2. Add it to the relevant ``...Action`` union below.
3. Add a matching branch in the corresponding ``ahp.reducers.<family>`` function.

Each action's ``type`` string is the discriminator pydantic uses to pick the right
model out of the union when validating an incoming ``ActionEnvelope.action`` payload.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from .common import AhpModel, ContentRef, URI
from .state import AgentInfo, ChangesetOperationStatus, Turn, TurnRole

# ---------------------------------------------------------------------------
# Root actions
# ---------------------------------------------------------------------------


class RootAgentsChangedAction(AhpModel):
    type: Literal["root/agentsChanged"] = "root/agentsChanged"
    agents: list[AgentInfo]


class RootSessionAddedAction(AhpModel):
    type: Literal["root/sessionAdded"] = "root/sessionAdded"
    session_uri: URI = Field(alias="sessionUri")


class RootSessionRemovedAction(AhpModel):
    type: Literal["root/sessionRemoved"] = "root/sessionRemoved"
    session_uri: URI = Field(alias="sessionUri")


RootAction = Annotated[
    Union[RootAgentsChangedAction, RootSessionAddedAction, RootSessionRemovedAction],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Session actions
# ---------------------------------------------------------------------------


class SessionTitleChangedAction(AhpModel):
    type: Literal["session/titleChanged"] = "session/titleChanged"
    title: str


class SessionChatAddedAction(AhpModel):
    type: Literal["session/chatAdded"] = "session/chatAdded"
    chat_uri: URI = Field(alias="chatUri")


class SessionTerminalAddedAction(AhpModel):
    type: Literal["session/terminalAdded"] = "session/terminalAdded"
    terminal_uri: URI = Field(alias="terminalUri")


class SessionDisposedAction(AhpModel):
    type: Literal["session/disposed"] = "session/disposed"


SessionAction = Annotated[
    Union[
        SessionTitleChangedAction,
        SessionChatAddedAction,
        SessionTerminalAddedAction,
        SessionDisposedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Chat actions
# ---------------------------------------------------------------------------


class ChatTurnStartedAction(AhpModel):
    type: Literal["chat/turnStarted"] = "chat/turnStarted"
    turn_id: str = Field(alias="turnId")
    role: TurnRole


class ChatTurnDeltaAction(AhpModel):
    """Incremental text appended to an in-progress turn (streaming)."""

    type: Literal["chat/turnDelta"] = "chat/turnDelta"
    turn_id: str = Field(alias="turnId")
    text_delta: str = Field(alias="textDelta")


class ChatTurnCompletedAction(AhpModel):
    type: Literal["chat/turnCompleted"] = "chat/turnCompleted"
    turn: Turn


class ChatTurnContentRefAddedAction(AhpModel):
    type: Literal["chat/turnContentRefAdded"] = "chat/turnContentRefAdded"
    turn_id: str = Field(alias="turnId")
    content_ref: ContentRef = Field(alias="contentRef")


class ChatConfirmationRequestedAction(AhpModel):
    type: Literal["chat/confirmationRequested"] = "chat/confirmationRequested"
    turn_id: str = Field(alias="turnId")
    prompt: str


ChatAction = Annotated[
    Union[
        ChatTurnStartedAction,
        ChatTurnDeltaAction,
        ChatTurnCompletedAction,
        ChatTurnContentRefAddedAction,
        ChatConfirmationRequestedAction,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Terminal actions
# ---------------------------------------------------------------------------


class TerminalOutputAction(AhpModel):
    type: Literal["terminal/output"] = "terminal/output"
    data: str


class TerminalExitedAction(AhpModel):
    type: Literal["terminal/exited"] = "terminal/exited"
    exit_code: int = Field(alias="exitCode")


TerminalAction = Annotated[
    Union[TerminalOutputAction, TerminalExitedAction],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Changeset actions
# ---------------------------------------------------------------------------


class ChangesetOperationStatusChangedAction(AhpModel):
    type: Literal["changeset/operationStatusChanged"] = "changeset/operationStatusChanged"
    status: ChangesetOperationStatus


ChangesetAction = Annotated[
    Union[ChangesetOperationStatusChangedAction],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Annotations actions
# ---------------------------------------------------------------------------


class AnnotationAddedAction(AhpModel):
    type: Literal["annotations/added"] = "annotations/added"
    annotation: dict


class AnnotationRemovedAction(AhpModel):
    type: Literal["annotations/removed"] = "annotations/removed"
    annotation_id: str = Field(alias="annotationId")


AnnotationsAction = Annotated[
    Union[AnnotationAddedAction, AnnotationRemovedAction],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Aggregate union
# ---------------------------------------------------------------------------

StateAction = Annotated[
    Union[
        RootAgentsChangedAction,
        RootSessionAddedAction,
        RootSessionRemovedAction,
        SessionTitleChangedAction,
        SessionChatAddedAction,
        SessionTerminalAddedAction,
        SessionDisposedAction,
        ChatTurnStartedAction,
        ChatTurnDeltaAction,
        ChatTurnCompletedAction,
        ChatTurnContentRefAddedAction,
        ChatConfirmationRequestedAction,
        TerminalOutputAction,
        TerminalExitedAction,
        ChangesetOperationStatusChangedAction,
        AnnotationAddedAction,
        AnnotationRemovedAction,
    ],
    Field(discriminator="type"),
]
"""Every action variant currently modeled, discriminated on the ``type`` field.

Pass this as the type of ``ActionEnvelope.action`` at call sites (rather than the
loose ``dict[str, Any]`` used in ``common.ActionEnvelope`` for forward-compat
parsing) once a payload needs to be dispatched to a reducer.
"""
