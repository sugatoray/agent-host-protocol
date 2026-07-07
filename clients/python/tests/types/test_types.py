"""Smoke tests for ahp.types: camelCase<->snake_case round-tripping and the
StateAction discriminated union.

These only exercise ``ahp.types`` (no client/transport/reducers yet, per the
phased build order in SPEC.md). Run with: `pip install -e ".[dev]"` then `pytest`.
"""

from __future__ import annotations

from pydantic import TypeAdapter

from ahp.types import (
    ActionEnvelope,
    ChatTurnDeltaAction,
    RootSessionAddedAction,
    StateAction,
)


def test_camel_case_alias_round_trip():
    action = RootSessionAddedAction(session_uri="ahp-session:/abc-123")
    # Serialize using wire (camelCase) aliases, as it would appear on the wire.
    wire = action.model_dump(by_alias=True)
    assert wire == {"type": "root/sessionAdded", "sessionUri": "ahp-session:/abc-123"}

    # And it should parse back whether given camelCase or snake_case.
    from_wire = RootSessionAddedAction.model_validate(wire)
    assert from_wire.session_uri == "ahp-session:/abc-123"

    from_snake = RootSessionAddedAction.model_validate(
        {"type": "root/sessionAdded", "session_uri": "ahp-session:/abc-123"}
    )
    assert from_snake.session_uri == "ahp-session:/abc-123"


def test_state_action_discriminated_union_parses_correct_variant():
    adapter = TypeAdapter(StateAction)
    parsed = adapter.validate_python(
        {"type": "chat/turnDelta", "turnId": "t1", "textDelta": "hello"}
    )
    assert isinstance(parsed, ChatTurnDeltaAction)
    assert parsed.text_delta == "hello"


def test_action_envelope_allows_forward_compatible_unknown_fields():
    # extra="allow" on AhpModel means a hypothetical future field on the wire
    # (e.g. a new optional metadata key) shouldn't hard-fail validation.
    envelope = ActionEnvelope.model_validate(
        {
            "channel": "ahp-chat:/abc",
            "serverSeq": 42,
            "action": {"type": "chat/turnDelta", "turnId": "t1", "textDelta": "hi"},
            "futureField": "should not raise",
        }
    )
    assert envelope.server_seq == 42
