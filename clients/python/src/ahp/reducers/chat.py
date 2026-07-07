"""Pure reducer for a chat channel within a session (``ahp-chat:/<uuid>``)."""

from __future__ import annotations

from ahp.types import (
    ChatConfirmationRequestedAction,
    ChatState,
    ChatTurnCompletedAction,
    ChatTurnContentRefAddedAction,
    ChatTurnDeltaAction,
    ChatTurnStartedAction,
    StateAction,
    Turn,
    TurnStatus,
)


def chat_reducer(state: ChatState, action: StateAction) -> ChatState:
    """Apply ``action`` to ``state``, returning a new :class:`ChatState`.

    As with the other channel reducers, actions outside the ``chat/*`` family
    are a no-op.
    """
    if isinstance(action, ChatTurnStartedAction):
        new_turn = Turn(id=action.turn_id, role=action.role, status=TurnStatus.RUNNING)
        return state.model_copy(update={"turns": [*state.turns, new_turn]})

    if isinstance(action, ChatTurnDeltaAction):
        found = False
        new_turns: list[Turn] = []
        for turn in state.turns:
            if turn.id == action.turn_id:
                found = True
                new_turns.append(
                    turn.model_copy(
                        update={"text": (turn.text or "") + action.text_delta}
                    )
                )
            else:
                new_turns.append(turn)
        if not found:
            return state
        return state.model_copy(update={"turns": new_turns})

    if isinstance(action, ChatTurnCompletedAction):
        found = False
        new_turns = []
        for turn in state.turns:
            if turn.id == action.turn.id:
                found = True
                new_turns.append(action.turn)
            else:
                new_turns.append(turn)
        if not found:
            new_turns.append(action.turn)
        return state.model_copy(update={"turns": new_turns})

    if isinstance(action, ChatTurnContentRefAddedAction):
        found = False
        new_turns = []
        for turn in state.turns:
            if turn.id == action.turn_id:
                found = True
                new_turns.append(
                    turn.model_copy(
                        update={
                            "content_refs": [*turn.content_refs, action.content_ref]
                        }
                    )
                )
            else:
                new_turns.append(turn)
        if not found:
            return state
        return state.model_copy(update={"turns": new_turns})

    if isinstance(action, ChatConfirmationRequestedAction):
        return state.model_copy(update={"pending_confirmation": True})

    return state
