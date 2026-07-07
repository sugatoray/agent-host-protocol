"""Pure reducer for a chat channel within a session."""

from __future__ import annotations

from typing import Any

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


def _update_turn(turns: list[Turn], turn_id: str, update: dict[str, Any]) -> list[Turn]:
    return [t.model_copy(update=update) if t.id == turn_id else t for t in turns]


def chat_reducer(state: ChatState, action: StateAction) -> ChatState:
    """Apply ``action`` to ``state``, returning a new :class:`ChatState`."""
    if isinstance(action, ChatTurnStartedAction):
        new_turn = Turn(
            id=action.turn_id,
            message=action.message,
            state={"type": "running"},
        )
        return state.model_copy(
            update={"turns": [*state.turns, new_turn], "active_turn": action.turn_id}
        )

    if isinstance(action, ChatDeltaAction):
        if not any(t.id == action.turn_id for t in state.turns):
            return state
        new_turns = _update_turn(
            state.turns,
            action.turn_id,
            {"response_parts": [
                *next(t.response_parts for t in state.turns if t.id == action.turn_id),
                {"type": "delta", "partId": action.part_id, "content": action.content},
            ]},
        )
        return state.model_copy(update={"turns": new_turns})

    if isinstance(action, ChatTurnCompleteAction):
        new_turns = _update_turn(
            state.turns, action.turn_id, {"state": {"type": "complete"}}
        )
        return state.model_copy(update={"turns": new_turns, "active_turn": None})

    if isinstance(action, ChatTurnCancelledAction):
        new_turns = _update_turn(
            state.turns, action.turn_id, {"state": {"type": "cancelled"}}
        )
        return state.model_copy(update={"turns": new_turns, "active_turn": None})

    if isinstance(action, ChatErrorAction):
        new_turns = _update_turn(
            state.turns,
            action.turn_id,
            {"state": {"type": "error"}, "error": action.error},
        )
        return state.model_copy(update={"turns": new_turns, "active_turn": None})

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
