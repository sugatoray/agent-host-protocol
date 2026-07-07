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


def make_active(id: str, **overrides) -> dict:
    """Construct an in-progress turn dict (ActiveTurn shape)."""
    base = {"id": id, "message": {}, "responseParts": []}
    base.update(overrides)
    return base


def make_completed_turn(id: str, state: str = "complete", **overrides) -> Turn:
    """Construct a completed Turn (terminal state only)."""
    return Turn(id=id, state=state, **overrides)


# ── ChatTurnStartedAction ─────────────────────────────────────────────────────

def test_turn_started_sets_active_turn():
    state = make_state()
    action = ChatTurnStartedAction(
        turn_id="t1", message={"role": "user", "content": "Hello"}
    )
    new_state = chat_reducer(state, action)

    assert new_state.active_turn is not None
    assert new_state.active_turn["id"] == "t1"
    assert new_state.active_turn["message"] == {"role": "user", "content": "Hello"}
    assert new_state.active_turn["responseParts"] == []


def test_turn_started_does_not_add_to_turns():
    # In-progress turns live in active_turn, not turns (ActiveTurn vs Turn).
    state = make_state()
    action = ChatTurnStartedAction(turn_id="t1", message={})
    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 0


# ── ChatDeltaAction ───────────────────────────────────────────────────────────

def test_delta_appends_to_active_turn_response_parts():
    state = make_state(active_turn=make_active("t1"))
    action = ChatDeltaAction(turn_id="t1", part_id="p1", content="Hello")

    new_state = chat_reducer(state, action)

    parts = new_state.active_turn["responseParts"]
    assert len(parts) == 1
    assert parts[0]["content"] == "Hello"


def test_delta_is_noop_for_unknown_turn_id():
    state = make_state(active_turn=make_active("t1"))
    action = ChatDeltaAction(turn_id="does-not-exist", part_id="p1", content="!")

    new_state = chat_reducer(state, action)

    assert new_state.active_turn["responseParts"] == []


def test_delta_is_noop_when_no_active_turn():
    state = make_state(active_turn=None)
    action = ChatDeltaAction(turn_id="t1", part_id="p1", content="!")

    new_state = chat_reducer(state, action)

    assert new_state is state


# ── ChatTurnCompleteAction ────────────────────────────────────────────────────

def test_turn_complete_moves_active_to_turns_with_complete_state():
    state = make_state(active_turn=make_active("t1"))
    action = ChatTurnCompleteAction(turn_id="t1")

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    assert new_state.turns[0].id == "t1"
    assert new_state.turns[0].state == "complete"
    assert new_state.active_turn is None


def test_turn_complete_preserves_response_parts():
    active = make_active("t1", responseParts=[{"type": "delta", "content": "hi"}])
    state = make_state(active_turn=active)
    action = ChatTurnCompleteAction(turn_id="t1")

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].response_parts == [{"type": "delta", "content": "hi"}]


def test_turn_complete_is_noop_for_unknown_turn():
    state = make_state(active_turn=make_active("t1"))
    action = ChatTurnCompleteAction(turn_id="different-id")

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 0
    assert new_state.active_turn is not None


# ── ChatTurnCancelledAction ───────────────────────────────────────────────────

def test_turn_cancelled_moves_active_to_turns_with_cancelled_state():
    state = make_state(active_turn=make_active("t1"))
    action = ChatTurnCancelledAction(turn_id="t1")

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    assert new_state.turns[0].state == "cancelled"
    assert new_state.active_turn is None


# ── ChatErrorAction ───────────────────────────────────────────────────────────

def test_error_moves_active_to_turns_with_error_state():
    state = make_state(active_turn=make_active("t1"))
    error = {"errorType": "NetworkError", "message": "timeout"}
    action = ChatErrorAction(turn_id="t1", error=error)

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    assert new_state.turns[0].state == "error"
    assert new_state.turns[0].error == error
    assert new_state.active_turn is None


# ── ChatTurnsLoadedAction ─────────────────────────────────────────────────────

def test_turns_loaded_prepends_to_existing_turns():
    existing = make_completed_turn("t3")
    state = make_state(turns=[existing])
    loaded_turns = [
        {"id": "t1", "message": {}, "responseParts": [], "state": "complete"},
        {"id": "t2", "message": {}, "responseParts": [], "state": "complete"},
    ]
    action = ChatTurnsLoadedAction(turns=loaded_turns, next_cursor="prev-cursor")

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 3
    assert new_state.turns_next_cursor == "prev-cursor"
    assert new_state.turns[-1].id == "t3"


# ── ChatActivityChangedAction ─────────────────────────────────────────────────

def test_activity_changed():
    state = make_state()
    action = ChatActivityChangedAction(activity="thinking")

    new_state = chat_reducer(state, action)

    assert new_state.activity == "thinking"


# ── Cross-channel no-op ───────────────────────────────────────────────────────

def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionTitleChangedAction(title="other")

    new_state = chat_reducer(state, foreign_action)

    assert new_state == state
