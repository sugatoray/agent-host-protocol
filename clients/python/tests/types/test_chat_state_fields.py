"""Tests for ChatState missing fields: origin, interactivity, workingDirectory.
Canonical source: types/channels-chat/state.ts:51-69.
"""
from ahp.types.state import ChatState


def test_chat_state_origin_defaults_none():
    assert ChatState().origin is None


def test_chat_state_origin_parses_user_kind():
    s = ChatState.model_validate({"origin": {"kind": "user"}})
    assert s.origin == {"kind": "user"}


def test_chat_state_origin_parses_tool_kind():
    s = ChatState.model_validate({
        "origin": {"kind": "tool", "chat": "ahp-chat:/parent", "toolCallId": "tc1"}
    })
    assert s.origin["kind"] == "tool"
    assert s.origin["toolCallId"] == "tc1"


def test_chat_state_interactivity_defaults_none():
    assert ChatState().interactivity is None


def test_chat_state_interactivity_parses_read_only():
    s = ChatState.model_validate({"interactivity": "read-only"})
    assert s.interactivity == "read-only"


def test_chat_state_interactivity_parses_hidden():
    s = ChatState.model_validate({"interactivity": "hidden"})
    assert s.interactivity == "hidden"


def test_chat_state_working_directory_defaults_none():
    assert ChatState().working_directory is None


def test_chat_state_working_directory_parses_from_wire():
    s = ChatState.model_validate({"workingDirectory": "file:///home/user/project"})
    assert s.working_directory == "file:///home/user/project"


def test_chat_state_all_three_fields_together():
    s = ChatState.model_validate({
        "origin": {"kind": "fork", "chat": "ahp-chat:/parent", "turnId": "t1"},
        "interactivity": "full",
        "workingDirectory": "file:///srv/repo",
    })
    assert s.origin["kind"] == "fork"
    assert s.interactivity == "full"
    assert s.working_directory == "file:///srv/repo"
