"""Tests for ahp.reducers.session.session_reducer."""

from __future__ import annotations

from ahp.reducers.session import session_reducer
from ahp.types import (
    RootAgentsChangedAction,
    SessionActivityChangedAction,
    SessionChatAddedAction,
    SessionChatRemovedAction,
    SessionConfigChangedAction,
    SessionCreationFailedAction,
    SessionReadyAction,
    SessionState,
    SessionTitleChangedAction,
)


def make_state(**overrides) -> SessionState:
    defaults: dict = dict(provider="", title="", lifecycle="creating", active_clients=[], chats=[])
    defaults.update(overrides)
    return SessionState(**defaults)


def test_ready_transitions_lifecycle():
    state = make_state(lifecycle="creating")
    action = SessionReadyAction()

    new_state = session_reducer(state, action)

    assert new_state.lifecycle == "ready"
    assert state.lifecycle == "creating"  # input not mutated


def test_creation_failed_sets_lifecycle_and_error():
    state = make_state(lifecycle="creating")
    error = {"errorType": "ProviderUnavailable", "message": "offline"}
    action = SessionCreationFailedAction(error=error)

    new_state = session_reducer(state, action)

    assert new_state.lifecycle == "creationFailed"
    assert new_state.creation_error == error


def test_title_changed_updates_title():
    state = make_state(title="Untitled")
    action = SessionTitleChangedAction(title="Debugging flaky test")

    new_state = session_reducer(state, action)

    assert new_state.title == "Debugging flaky test"
    assert state.title == "Untitled"  # input not mutated


def test_activity_changed():
    state = make_state()
    action = SessionActivityChangedAction(activity="running")

    new_state = session_reducer(state, action)

    assert new_state.activity == "running"


def test_chat_added_appends_summary():
    state = make_state(chats=[{"uri": "ahp-chat:/1", "title": "First"}])
    action = SessionChatAddedAction(summary={"uri": "ahp-chat:/2", "title": "Second"})

    new_state = session_reducer(state, action)

    assert len(new_state.chats) == 2
    assert new_state.chats[-1]["uri"] == "ahp-chat:/2"


def test_chat_removed_drops_by_uri():
    state = make_state(
        chats=[{"uri": "ahp-chat:/1"}, {"uri": "ahp-chat:/2"}]
    )
    action = SessionChatRemovedAction(chat="ahp-chat:/1")

    new_state = session_reducer(state, action)

    assert len(new_state.chats) == 1
    assert new_state.chats[0]["uri"] == "ahp-chat:/2"


def test_config_changed_merges():
    state = make_state()
    state = state.model_copy(update={"config": {"model": "gpt-4"}})
    action = SessionConfigChangedAction(config={"temperature": 0.7})

    new_state = session_reducer(state, action)

    assert new_state.config == {"model": "gpt-4", "temperature": 0.7}


def test_config_changed_replace():
    state = make_state()
    state = state.model_copy(update={"config": {"model": "gpt-4"}})
    action = SessionConfigChangedAction(config={"model": "claude-3"}, replace=True)

    new_state = session_reducer(state, action)

    assert new_state.config == {"model": "claude-3"}


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = RootAgentsChangedAction(agents=[])

    new_state = session_reducer(state, foreign_action)

    assert new_state == state
