"""Tests for ahp.reducers.session.session_reducer."""

from __future__ import annotations

from ahp.reducers.session import session_reducer
from ahp.types import (
    RootSessionAddedAction,
    SessionChatAddedAction,
    SessionDisposedAction,
    SessionState,
    SessionTerminalAddedAction,
    SessionTitleChangedAction,
)


def make_state(**overrides) -> SessionState:
    defaults = dict(uri="ahp-session:/abc", title=None, chat_uris=[], terminal_uris=[], disposed=False)
    defaults.update(overrides)
    return SessionState(**defaults)


def test_title_changed_updates_title():
    state = make_state(title="Untitled")
    action = SessionTitleChangedAction(title="Debugging flaky test")

    new_state = session_reducer(state, action)

    assert new_state.title == "Debugging flaky test"
    assert state.title == "Untitled"  # input not mutated


def test_chat_added_appends_chat_uri():
    state = make_state(chat_uris=["ahp-chat:/1"])
    action = SessionChatAddedAction(chat_uri="ahp-chat:/2")

    new_state = session_reducer(state, action)

    assert new_state.chat_uris == ["ahp-chat:/1", "ahp-chat:/2"]


def test_terminal_added_appends_terminal_uri():
    state = make_state(terminal_uris=[])
    action = SessionTerminalAddedAction(terminal_uri="ahp-terminal:/1")

    new_state = session_reducer(state, action)

    assert new_state.terminal_uris == ["ahp-terminal:/1"]


def test_disposed_sets_flag_true():
    state = make_state(disposed=False)
    action = SessionDisposedAction()

    new_state = session_reducer(state, action)

    assert new_state.disposed is True


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = RootSessionAddedAction(session_uri="ahp-session:/other")

    new_state = session_reducer(state, foreign_action)

    assert new_state == state
