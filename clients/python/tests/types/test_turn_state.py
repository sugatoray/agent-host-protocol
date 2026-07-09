"""Tests for Turn.state canonical string enum shape.

Canonical source: types/channels-chat/state.ts:477-481,504-522
TurnState = 'complete' | 'cancelled' | 'error'  (no 'running')
In-progress turns are ActiveTurn, not Turn — so Turn.state is always a
terminal value and has no default.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ahp.types.state import Turn


def _turn(state: str, **kwargs) -> Turn:
    return Turn(id="t1", state=state, **kwargs)


def test_turn_state_complete():
    t = _turn("complete")
    assert t.state == "complete"


def test_turn_state_cancelled():
    t = _turn("cancelled")
    assert t.state == "cancelled"


def test_turn_state_error():
    t = _turn("error")
    assert t.state == "error"


def test_turn_state_is_string_not_dict():
    t = _turn("complete")
    assert isinstance(t.state, str)


def test_turn_state_parses_from_wire():
    raw = {"id": "t1", "state": "complete"}
    t = Turn.model_validate(raw)
    assert t.state == "complete"


def test_turn_state_required():
    with pytest.raises(ValidationError):
        Turn(id="t1")  # state omitted — must raise


def test_turn_state_no_running_default():
    # 'running' is not a valid TurnState; in-progress turns are ActiveTurn
    assert not hasattr(Turn.model_fields["state"], "default") or \
        Turn.model_fields["state"].default is None or \
        Turn.model_fields["state"].is_required()
