"""Pure reducer for a terminal channel within a session."""

from __future__ import annotations

from ahp.types import (
    StateAction,
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


def terminal_reducer(state: TerminalState, action: StateAction) -> TerminalState:
    """Apply ``action`` to ``state``, returning a new :class:`TerminalState`."""
    if isinstance(action, TerminalDataAction):
        content = list(state.content)
        tail = content[-1] if content else None
        if tail and tail.get("type") == "command" and not tail.get("isComplete"):
            content[-1] = {**tail, "output": tail["output"] + action.data}
        elif tail and tail.get("type") == "unclassified":
            content[-1] = {**tail, "value": tail["value"] + action.data}
        else:
            content.append({"type": "unclassified", "value": action.data})
        return state.model_copy(update={"content": content})

    if isinstance(action, TerminalExitedAction):
        return state.model_copy(update={"exit_code": action.exit_code})

    if isinstance(action, TerminalTitleChangedAction):
        return state.model_copy(update={"title": action.title})

    if isinstance(action, TerminalCwdChangedAction):
        return state.model_copy(update={"cwd": action.cwd})

    if isinstance(action, TerminalResizedAction):
        return state.model_copy(update={"cols": action.cols, "rows": action.rows})

    if isinstance(action, TerminalClearedAction):
        return state.model_copy(update={"content": []})

    if isinstance(action, TerminalClaimedAction):
        return state.model_copy(update={"claim": action.claim})

    if isinstance(action, TerminalCommandDetectionAvailableAction):
        return state.model_copy(update={"supports_command_detection": True})

    if isinstance(action, TerminalCommandExecutedAction):
        part = {
            "type": "command",
            "commandId": action.command_id,
            "commandLine": action.command_line,
            "output": "",
            "timestamp": action.timestamp,
            "isComplete": False,
        }
        return state.model_copy(update={
            "content": [*state.content, part],
            "supports_command_detection": True,
        })

    if isinstance(action, TerminalCommandFinishedAction):
        content = [
            {**p, "isComplete": True, "exitCode": action.exit_code, "durationMs": action.duration_ms}
            if p.get("type") == "command" and p.get("commandId") == action.command_id
            else p
            for p in state.content
        ]
        return state.model_copy(update={"content": content})

    return state
