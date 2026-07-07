"""Tests for ahp.reducers.terminal.terminal_reducer."""

from __future__ import annotations

from ahp.reducers.terminal import terminal_reducer
from ahp.types import (
    SessionTitleChangedAction,
    TerminalClearedAction,
    TerminalClaimedAction,
    TerminalCommandDetectionAvailableAction,
    TerminalCommandExecutedAction,
    TerminalCommandFinishedAction,
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


def test_data_creates_unclassified_part():
    # canonical: {type: "unclassified", value: data} not {type: "data", data: ...}
    state = make_state(content=[])
    action = TerminalDataAction(data="$ ls\n")

    new_state = terminal_reducer(state, action)

    assert len(new_state.content) == 1
    assert new_state.content[0] == {"type": "unclassified", "value": "$ ls\n"}
    assert state.content == []  # input not mutated


def test_data_appends_to_incomplete_command_output():
    cmd_part = {
        "type": "command", "commandId": "cmd-1", "commandLine": "npm test",
        "output": "", "timestamp": 1700000000000, "isComplete": False,
    }
    state = make_state(content=[cmd_part])

    new_state = terminal_reducer(state, TerminalDataAction(data="PASS\r\n"))

    assert len(new_state.content) == 1
    assert new_state.content[0]["output"] == "PASS\r\n"


def test_data_appends_to_unclassified_tail():
    state = make_state(content=[{"type": "unclassified", "value": "$ "}])

    new_state = terminal_reducer(state, TerminalDataAction(data="ls\n"))

    assert len(new_state.content) == 1
    assert new_state.content[0]["value"] == "$ ls\n"


def test_data_after_complete_command_creates_unclassified():
    cmd_part = {
        "type": "command", "commandId": "cmd-1", "commandLine": "echo hi",
        "output": "hi\r\n", "timestamp": 1700000000000, "isComplete": True, "exitCode": 0,
    }
    state = make_state(content=[cmd_part])

    new_state = terminal_reducer(state, TerminalDataAction(data="$ "))

    assert len(new_state.content) == 2
    assert new_state.content[1] == {"type": "unclassified", "value": "$ "}


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


def test_claimed_updates_claim():
    state = make_state()
    claim = {"kind": "client", "clientId": "vscode-1"}
    new_state = terminal_reducer(state, TerminalClaimedAction(claim=claim))
    assert new_state.claim == claim


def test_command_detection_available_sets_flag():
    state = make_state()
    new_state = terminal_reducer(state, TerminalCommandDetectionAvailableAction())
    assert new_state.supports_command_detection is True


def test_command_executed_appends_part_and_sets_flag():
    state = make_state(content=[])
    action = TerminalCommandExecutedAction(
        command_id="cmd-1", command_line="npm test", timestamp=1700000000000
    )
    new_state = terminal_reducer(state, action)

    assert new_state.supports_command_detection is True
    assert len(new_state.content) == 1
    part = new_state.content[0]
    assert part["type"] == "command"
    assert part["commandId"] == "cmd-1"
    assert part["commandLine"] == "npm test"
    assert part["output"] == ""
    assert part["isComplete"] is False


def test_command_finished_marks_command_complete():
    cmd_part = {
        "type": "command", "commandId": "cmd-1", "commandLine": "npm test",
        "output": "All tests passed\r\n", "timestamp": 1700000000000, "isComplete": False,
    }
    state = make_state(content=[cmd_part])

    action = TerminalCommandFinishedAction(command_id="cmd-1", exit_code=0, duration_ms=1234)
    new_state = terminal_reducer(state, action)

    assert len(new_state.content) == 1
    p = new_state.content[0]
    assert p["isComplete"] is True
    assert p["exitCode"] == 0
    assert p["durationMs"] == 1234
