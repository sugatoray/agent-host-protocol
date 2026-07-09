"""Pure reducer for a chat channel within a session."""

from __future__ import annotations

from ahp.types import (
    ChatActivityChangedAction,
    ChatDeltaAction,
    ChatErrorAction,
    ChatState,
    ChatTurnCancelledAction,
    ChatTurnCompleteAction,
    ChatTurnStartedAction,
    ChatTurnsLoadedAction,
    StateAction,
    Turn,
)


def chat_reducer(state: ChatState, action: StateAction) -> ChatState:
    """Apply ``action`` to ``state``, returning a new :class:`ChatState`.

    In-progress turns are tracked in ``active_turn`` (an ActiveTurn dict).
    Only completed turns appear in ``turns``, each with a terminal state string.
    This matches canonical types/channels-chat/state.ts — Turn.state is always
    'complete' | 'cancelled' | 'error'; 'running' does not exist on Turn.
    """
    if isinstance(action, ChatTurnStartedAction):
        active = {"id": action.turn_id, "message": action.message, "responseParts": []}
        return state.model_copy(update={"active_turn": active})

    if isinstance(action, ChatDeltaAction):
        if state.active_turn is None or state.active_turn.get("id") != action.turn_id:
            return state
        part = {"type": "delta", "partId": action.part_id, "content": action.content}
        updated = {
            **state.active_turn,
            "responseParts": [*state.active_turn.get("responseParts", []), part],
        }
        return state.model_copy(update={"active_turn": updated})

    if isinstance(action, ChatTurnCompleteAction):
        if state.active_turn is None or state.active_turn.get("id") != action.turn_id:
            return state
        turn = Turn(
            id=state.active_turn["id"],
            message=state.active_turn.get("message", {}),
            response_parts=state.active_turn.get("responseParts", []),
            state="complete",
        )
        return state.model_copy(update={"turns": [*state.turns, turn], "active_turn": None})

    if isinstance(action, ChatTurnCancelledAction):
        if state.active_turn is None or state.active_turn.get("id") != action.turn_id:
            return state
        turn = Turn(
            id=state.active_turn["id"],
            message=state.active_turn.get("message", {}),
            response_parts=state.active_turn.get("responseParts", []),
            state="cancelled",
        )
        return state.model_copy(update={"turns": [*state.turns, turn], "active_turn": None})

    if isinstance(action, ChatErrorAction):
        if state.active_turn is None or state.active_turn.get("id") != action.turn_id:
            return state
        turn = Turn(
            id=state.active_turn["id"],
            message=state.active_turn.get("message", {}),
            response_parts=state.active_turn.get("responseParts", []),
            state="error",
            error=action.error,
        )
        return state.model_copy(update={"turns": [*state.turns, turn], "active_turn": None})

    if isinstance(action, ChatActivityChangedAction):
        return state.model_copy(update={"activity": action.activity})

    if isinstance(action, ChatTurnsLoadedAction):
        return state.model_copy(
            update={
                "turns": [*action.turns, *state.turns],
                "turns_next_cursor": action.next_cursor,
            }
        )

    return state
