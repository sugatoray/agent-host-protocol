"""Tests for ahp.reducers.terminal.terminal_reducer."""

from __future__ import annotations

from ahp.reducers.terminal import terminal_reducer
from ahp.types import (
    SessionDisposedAction,
    TerminalExitedAction,
    TerminalOutputAction,
    TerminalState,
    TerminalStatus,
)


def make_state(**overrides) -> TerminalState:
    defaults = dict(
        uri="ahp-terminal:/1",
        session_uri="ahp-session:/abc",
        status=TerminalStatus.RUNNING,
        exit_code=None,
        buffer="",
    )
    defaults.update(overrides)
    return TerminalState(**defaults)


def test_output_appends_to_buffer():
    state = make_state(buffer="$ ls\n")
    action = TerminalOutputAction(data="file1.txt\nfile2.txt\n")

    new_state = terminal_reducer(state, action)

    assert new_state.buffer == "$ ls\nfile1.txt\nfile2.txt\n"
    assert state.buffer == "$ ls\n"  # input not mutated


def test_exited_sets_status_and_exit_code():
    state = make_state(status=TerminalStatus.RUNNING, exit_code=None)
    action = TerminalExitedAction(exit_code=0)

    new_state = terminal_reducer(state, action)

    assert new_state.status == TerminalStatus.EXITED
    assert new_state.exit_code == 0


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionDisposedAction()

    new_state = terminal_reducer(state, foreign_action)

    assert new_state == state
