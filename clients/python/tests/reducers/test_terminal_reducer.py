"""Tests for ahp.reducers.terminal.terminal_reducer."""

from __future__ import annotations

from ahp.reducers.terminal import terminal_reducer
from ahp.types import (
    SessionTitleChangedAction,
    TerminalClearedAction,
    TerminalCwdChangedAction,
    TerminalDataAction,
    TerminalExitedAction,
    TerminalResizedAction,
    TerminalState,
    TerminalTitleChangedAction,
)


def make_state(**overrides) -> TerminalState:
    defaults: dict = dict(title="", content=[], exit_code=None)
    defaults.update(overrides)
    return TerminalState(**defaults)


def test_data_appends_to_content():
    state = make_state(content=[])
    action = TerminalDataAction(data="$ ls\n")

    new_state = terminal_reducer(state, action)

    assert len(new_state.content) == 1
    assert new_state.content[0]["data"] == "$ ls\n"
    assert state.content == []  # input not mutated


def test_exited_sets_exit_code():
    state = make_state(exit_code=None)
    action = TerminalExitedAction(exit_code=0)

    new_state = terminal_reducer(state, action)

    assert new_state.exit_code == 0


def test_exited_exit_code_can_be_none():
    """exitCode is optional in canonical TS — reducer handles None."""
    state = make_state(exit_code=None)
    action = TerminalExitedAction(exit_code=None)

    new_state = terminal_reducer(state, action)

    assert new_state.exit_code is None


def test_title_changed():
    state = make_state(title="")
    action = TerminalTitleChangedAction(title="bash")

    new_state = terminal_reducer(state, action)

    assert new_state.title == "bash"


def test_cwd_changed():
    state = make_state()
    action = TerminalCwdChangedAction(cwd="/home/user/projects")

    new_state = terminal_reducer(state, action)

    assert new_state.cwd == "/home/user/projects"


def test_resized_updates_cols_rows():
    state = make_state()
    action = TerminalResizedAction(cols=120, rows=40)

    new_state = terminal_reducer(state, action)

    assert new_state.cols == 120
    assert new_state.rows == 40


def test_cleared_empties_content():
    state = make_state(
        content=[{"type": "data", "data": "foo"}, {"type": "data", "data": "bar"}]
    )
    action = TerminalClearedAction()

    new_state = terminal_reducer(state, action)

    assert new_state.content == []


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionTitleChangedAction(title="other")

    new_state = terminal_reducer(state, foreign_action)

    assert new_state == state
