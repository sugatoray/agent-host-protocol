"""Smoke tests for ahp.types: camelCase<->snake_case round-tripping and the
StateAction discriminated union.
"""

from __future__ import annotations

from pydantic import TypeAdapter

from ahp.types import (
    ActionEnvelope,
    ChatDeltaAction,
    RootAgentsChangedAction,
    SessionTitleChangedAction,
    StateAction,
)


def test_camel_case_alias_round_trip():
    action = SessionTitleChangedAction(title="My Session")
    wire = action.model_dump(by_alias=True)
    assert wire == {"type": "session/titleChanged", "title": "My Session"}

    from_wire = SessionTitleChangedAction.model_validate(wire)
    assert from_wire.title == "My Session"


def test_state_action_discriminated_union_parses_chat_delta():
    adapter = TypeAdapter(StateAction)
    parsed = adapter.validate_python(
        {"type": "chat/delta", "turnId": "t1", "partId": "p1", "content": "hello"}
    )
    assert isinstance(parsed, ChatDeltaAction)
    assert parsed.content == "hello"
    assert parsed.turn_id == "t1"
    assert parsed.part_id == "p1"


def test_state_action_discriminated_union_parses_root_agents_changed():
    adapter = TypeAdapter(StateAction)
    parsed = adapter.validate_python({"type": "root/agentsChanged", "agents": []})
    assert isinstance(parsed, RootAgentsChangedAction)
    assert parsed.agents == []


def test_action_envelope_allows_forward_compatible_unknown_fields():
    # extra="allow" on AhpModel means future wire fields don't hard-fail.
    envelope = ActionEnvelope.model_validate(
        {
            "channel": "ahp-chat:/abc",
            "serverSeq": 42,
            "action": {"type": "chat/delta", "turnId": "t1", "partId": "p1", "content": "hi"},
            "futureField": "should not raise",
        }
    )
    assert envelope.server_seq == 42


def test_action_envelope_rejection_reason():
    envelope = ActionEnvelope.model_validate(
        {
            "channel": "ahp-session:/abc",
            "serverSeq": 7,
            "action": {"type": "session/titleChanged", "title": "bad"},
            "rejectionReason": "permission denied",
        }
    )
    assert envelope.rejection_reason == "permission denied"
