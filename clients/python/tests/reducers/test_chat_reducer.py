"""Tests for ahp.reducers.chat.chat_reducer."""

from __future__ import annotations

from ahp.reducers.chat import chat_reducer
from ahp.types import (
    ChatConfirmationRequestedAction,
    ChatState,
    ChatTurnCompletedAction,
    ChatTurnContentRefAddedAction,
    ChatTurnDeltaAction,
    ChatTurnStartedAction,
    ContentRef,
    SessionDisposedAction,
    Turn,
    TurnRole,
    TurnStatus,
)


def make_state(**overrides) -> ChatState:
    defaults = dict(
        uri="ahp-chat:/1",
        session_uri="ahp-session:/abc",
        turns=[],
        pending_confirmation=False,
    )
    defaults.update(overrides)
    return ChatState(**defaults)


def test_turn_started_appends_a_new_running_turn():
    state = make_state(turns=[])
    action = ChatTurnStartedAction(turn_id="t1", role=TurnRole.ASSISTANT)

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    turn = new_state.turns[0]
    assert turn.id == "t1"
    assert turn.role == TurnRole.ASSISTANT
    assert turn.status == TurnStatus.RUNNING


def test_turn_delta_appends_text_to_matching_turn():
    state = make_state(
        turns=[Turn(id="t1", role=TurnRole.ASSISTANT, status=TurnStatus.RUNNING, text="Hel")]
    )
    action = ChatTurnDeltaAction(turn_id="t1", text_delta="lo")

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].text == "Hello"


def test_turn_delta_is_a_noop_for_unknown_turn_id():
    state = make_state(turns=[Turn(id="t1", role=TurnRole.ASSISTANT, text="Hi")])
    action = ChatTurnDeltaAction(turn_id="does-not-exist", text_delta="!")

    new_state = chat_reducer(state, action)

    assert new_state.turns[0].text == "Hi"


def test_turn_completed_replaces_matching_turn():
    state = make_state(
        turns=[Turn(id="t1", role=TurnRole.ASSISTANT, status=TurnStatus.RUNNING, text="Hello")]
    )
    completed_turn = Turn(
        id="t1", role=TurnRole.ASSISTANT, status=TurnStatus.COMPLETE, text="Hello there!"
    )
    action = ChatTurnCompletedAction(turn=completed_turn)

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    assert new_state.turns[0].status == TurnStatus.COMPLETE
    assert new_state.turns[0].text == "Hello there!"


def test_turn_completed_appends_if_turn_not_previously_known():
    state = make_state(turns=[])
    completed_turn = Turn(id="t1", role=TurnRole.ASSISTANT, status=TurnStatus.COMPLETE, text="Hi")
    action = ChatTurnCompletedAction(turn=completed_turn)

    new_state = chat_reducer(state, action)

    assert len(new_state.turns) == 1
    assert new_state.turns[0].id == "t1"


def test_turn_content_ref_added_appends_to_matching_turn():
    state = make_state(turns=[Turn(id="t1", role=TurnRole.ASSISTANT, content_refs=[])])
    ref = ContentRef(uri="ahp-resource:/file.png", mime_type="image/png")
    action = ChatTurnContentRefAddedAction(turn_id="t1", content_ref=ref)

    new_state = chat_reducer(state, action)

    assert len(new_state.turns[0].content_refs) == 1
    assert new_state.turns[0].content_refs[0].uri == "ahp-resource:/file.png"


def test_confirmation_requested_sets_pending_flag():
    state = make_state(pending_confirmation=False)
    action = ChatConfirmationRequestedAction(turn_id="t1", prompt="Allow running rm -rf?")

    new_state = chat_reducer(state, action)

    assert new_state.pending_confirmation is True


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionDisposedAction()

    new_state = chat_reducer(state, foreign_action)

    assert new_state == state
