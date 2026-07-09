"""Tests for SessionMcpServerStateChangedAction in the session reducer.
Canonical logic: types/channels-session/reducer.ts:278-329.
Searches top-level customizations first, then children of container entries.
"""
from ahp.reducers.session import session_reducer
from ahp.types.actions import SessionMcpServerStateChangedAction
from ahp.types.state import SessionState


def _state_with_customizations(customizations):
    return SessionState(customizations=customizations)


MCP_READY = {"status": "ready"}
MCP_STARTING = {"status": "starting"}


# ── top-level match ──────────────────────────────────────────────────────────


def test_updates_top_level_mcp_server_state():
    state = _state_with_customizations([
        {"id": "srv-1", "type": "mcpServer", "enabled": True, "state": MCP_STARTING},
    ])
    action = SessionMcpServerStateChangedAction(id="srv-1", state=MCP_READY)
    new = session_reducer(state, action)
    assert new.customizations[0]["state"] == MCP_READY


def test_updates_top_level_mcp_server_channel():
    state = _state_with_customizations([
        {"id": "srv-1", "type": "mcpServer", "enabled": True, "state": MCP_STARTING, "channel": None},
    ])
    action = SessionMcpServerStateChangedAction(id="srv-1", state=MCP_READY, channel="mcp://srv-1")
    new = session_reducer(state, action)
    assert new.customizations[0]["channel"] == "mcp://srv-1"


def test_skips_top_level_entry_with_wrong_type():
    """A top-level entry with matching id but type != 'mcpServer' is left untouched."""
    state = _state_with_customizations([
        {"id": "srv-1", "type": "plugin", "enabled": True, "state": MCP_STARTING},
    ])
    action = SessionMcpServerStateChangedAction(id="srv-1", state=MCP_READY)
    new = session_reducer(state, action)
    assert new.customizations[0]["state"] == MCP_STARTING  # unchanged


# ── child match ───────────────────────────────────────────────────────────────


def test_updates_child_mcp_server_state():
    state = _state_with_customizations([
        {
            "id": "container-1",
            "type": "directory",
            "children": [
                {"id": "srv-child", "type": "mcpServer", "enabled": True, "state": MCP_STARTING},
            ],
        }
    ])
    action = SessionMcpServerStateChangedAction(id="srv-child", state=MCP_READY)
    new = session_reducer(state, action)
    assert new.customizations[0]["children"][0]["state"] == MCP_READY


def test_updates_child_mcp_server_channel():
    state = _state_with_customizations([
        {
            "id": "container-1",
            "type": "directory",
            "children": [
                {"id": "srv-child", "type": "mcpServer", "enabled": True, "state": MCP_STARTING},
            ],
        }
    ])
    action = SessionMcpServerStateChangedAction(id="srv-child", state=MCP_READY, channel="mcp://child")
    new = session_reducer(state, action)
    assert new.customizations[0]["children"][0]["channel"] == "mcp://child"


# ── no-match / edge cases ─────────────────────────────────────────────────────


def test_no_match_returns_same_state():
    state = _state_with_customizations([
        {"id": "other", "type": "mcpServer", "enabled": True, "state": MCP_STARTING},
    ])
    action = SessionMcpServerStateChangedAction(id="srv-unknown", state=MCP_READY)
    new = session_reducer(state, action)
    assert new is state


def test_none_customizations_returns_same_state():
    state = SessionState()  # customizations=None
    action = SessionMcpServerStateChangedAction(id="srv-1", state=MCP_READY)
    new = session_reducer(state, action)
    assert new is state


def test_does_not_mutate_original_customizations():
    original = {"id": "srv-1", "type": "mcpServer", "enabled": True, "state": MCP_STARTING}
    state = _state_with_customizations([original])
    action = SessionMcpServerStateChangedAction(id="srv-1", state=MCP_READY)
    session_reducer(state, action)
    assert original["state"] == MCP_STARTING  # original dict untouched
