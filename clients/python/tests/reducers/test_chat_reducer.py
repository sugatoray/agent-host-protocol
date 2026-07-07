"""Tests for ahp.reducers.chat.chat_reducer."""

from __future__ import annotations

from ahp.reducers.chat import chat_reducer
from ahp.types import (
    ChatActivityChangedAction,
    ChatDeltaAction,
    ChatErrorAction,
    ChatState,
    ChatTurnCancelledAction,
    ChatTurnCompleteAction,
    ChatTurnStartedAction,
    ChatTurnsLoadedAction,
    SessionTitleChangedAction,
    Turn,
)


def make_state(**overrides) -> ChatState:
    defaults: dict = dict(turns=[], active_turn=None)
    defaults.update(overrides)
    return ChatState(**defaults)


def make_turn(id: str, **overrides) -> Turn:
    defaults = dict(
        id=id,
        message={},
        response_parts=[],
        state={"type": "running"},
    )
    defaults.update(overrides)
    return Turn(**defaults)


def test_turn_started_appends_a_new_running_turn():
    state = make_state(turns=[])
    action = ChatTurnStartedAction(
        turn_id="t1", message={"role": "user", "content": "Hello"}
    )

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    turn = new_state.turns[0]
    assert turn.id == "t1"
    assert turn.state == {"type": "running"}
    assert new_state.active_turn == "t1"


def test_delta_appends_to_response_parts():
    state = make_state(turns=[make_turn("t1")])
    action = ChatDeltaAction(turn_id="t1", part_id="p1", content="Hello")

    new_state = chat_reducer(state, action)

    parts = new_state.turns[0].response_parts
    assert len(parts) == 1
    assert parts[0]["content"] == "Hello"


def test_delta_is_a_noop_for_unknown_turn_id():
    state = make_state(turns=[make_turn("t1")])
    action = ChatDeltaAction(turn_id="does-not-exist", part_id="p1", content="!")

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].response_parts == []


def test_turn_complete_sets_state_and_clears_active_turn():
    state = make_state(turns=[make_turn("t1")], active_turn="t1")
    action = ChatTurnCompleteAction(turn_id="t1")

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].state == {"type": "complete"}
    assert new_state.active_turn is None


def test_turn_cancelled_sets_state():
    state = make_state(turns=[make_turn("t1")], active_turn="t1")
    action = ChatTurnCancelledAction(turn_id="t1")

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].state == {"type": "cancelled"}
    assert new_state.active_turn is None


def test_error_sets_state_and_error_field():
    state = make_state(turns=[make_turn("t1")], active_turn="t1")
    error = {"errorType": "NetworkError", "message": "timeout"}
    action = ChatErrorAction(turn_id="t1", error=error)

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].state == {"type": "error"}
    assert new_state.turns[0].error == error
    assert new_state.active_turn is None


def test_activity_changed():
    state = make_state()
    action = ChatActivityChangedAction(activity="thinking")

    new_state = chat_reducer(state, action)

    assert new_state.activity == "thinking"


def test_turns_loaded_prepends_to_existing_turns():
    existing = make_turn("t3")
    state = make_state(turns=[existing])
    loaded_turns = [
        {"id": "t1", "message": {}, "responseParts": [], "state": {"type": "complete"}},
        {"id": "t2", "message": {}, "responseParts": [], "state": {"type": "complete"}},
    ]
    action = ChatTurnsLoadedAction(turns=loaded_turns, next_cursor="prev-cursor")

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 3
    assert new_state.turns_next_cursor == "prev-cursor"
    assert new_state.turns[-1].id == "t3"  # existing turn is at the end


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionTitleChangedAction(title="other")

    new_state = chat_reducer(state, foreign_action)

    assert new_state == state
