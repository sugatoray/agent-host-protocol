"""Tests for chat action field shapes against canonical types/channels-chat/actions.ts."""
import pytest
from ahp.types.actions import (
    ChatInputAnswerChangedAction,
    ChatInputCompletedAction,
    ChatPendingMessageRemovedAction,
    ChatPendingMessageSetAction,
    ChatQueuedMessagesReorderedAction,
    ChatToolCallApprovedAction,
    ChatToolCallConfirmedAction,
    ChatToolCallDeniedAction,
    ChatToolCallResultConfirmedAction,
)


# ── ChatToolCallConfirmedAction ───────────────────────────────────────────────

def test_tool_call_confirmed_has_approved_field():
    a = ChatToolCallConfirmedAction(turn_id="t1", tool_call_id="tc1", approved=True)
    assert a.approved is True


def test_tool_call_confirmed_denied():
    a = ChatToolCallConfirmedAction(turn_id="t1", tool_call_id="tc1", approved=False)
    assert a.approved is False


def test_tool_call_confirmed_parses_camel_case():
    raw = {"type": "chat/toolCallConfirmed", "turnId": "t1", "toolCallId": "tc1", "approved": True}
    a = ChatToolCallConfirmedAction.model_validate(raw)
    assert a.approved is True


def test_tool_call_confirmed_approved_has_confirmed_field():
    a = ChatToolCallConfirmedAction(
        turn_id="t1", tool_call_id="tc1", approved=True, confirmed="user-action"
    )
    assert a.confirmed == "user-action"


def test_tool_call_confirmed_denied_has_reason_field():
    a = ChatToolCallConfirmedAction(
        turn_id="t1", tool_call_id="tc1", approved=False, reason="denied"
    )
    assert a.reason == "denied"


def test_tool_call_confirmed_denied_has_reason_message():
    a = ChatToolCallConfirmedAction(
        turn_id="t1", tool_call_id="tc1", approved=False, reason="denied",
        reason_message="Not allowed in this environment",
    )
    assert a.reason_message == "Not allowed in this environment"


def test_tool_call_confirmed_approved_wire_round_trip():
    raw = {
        "type": "chat/toolCallConfirmed",
        "turnId": "t1",
        "toolCallId": "tc1",
        "approved": True,
        "confirmed": "user-action",
        "editedToolInput": "ls -la",
        "selectedOptionId": "opt-1",
    }
    a = ChatToolCallConfirmedAction.model_validate(raw)
    assert a.confirmed == "user-action"
    assert a.edited_tool_input == "ls -la"
    assert a.selected_option_id == "opt-1"


def test_tool_call_confirmed_denied_wire_round_trip():
    raw = {
        "type": "chat/toolCallConfirmed",
        "turnId": "t1",
        "toolCallId": "tc1",
        "approved": False,
        "reason": "skipped",
        "reasonMessage": "User skipped the step",
    }
    a = ChatToolCallConfirmedAction.model_validate(raw)
    assert a.reason == "skipped"
    assert a.reason_message == "User skipped the step"


# ── ChatToolCallApprovedAction / ChatToolCallDeniedAction (convenience types) ──

def test_approved_action_requires_confirmed():
    a = ChatToolCallApprovedAction(turn_id="t1", tool_call_id="tc1", confirmed="setting")
    assert a.approved is True
    assert a.confirmed == "setting"


def test_denied_action_requires_reason():
    a = ChatToolCallDeniedAction(turn_id="t1", tool_call_id="tc1", reason="denied")
    assert a.approved is False
    assert a.reason == "denied"


def test_approved_action_wire_round_trip():
    raw = {
        "type": "chat/toolCallConfirmed",
        "turnId": "t1",
        "toolCallId": "tc1",
        "approved": True,
        "confirmed": "not-needed",
    }
    a = ChatToolCallApprovedAction.model_validate(raw)
    assert a.confirmed == "not-needed"
    assert a.approved is True


def test_denied_action_wire_round_trip():
    raw = {
        "type": "chat/toolCallConfirmed",
        "turnId": "t1",
        "toolCallId": "tc1",
        "approved": False,
        "reason": "denied",
        "reasonMessage": "Access denied",
    }
    a = ChatToolCallDeniedAction.model_validate(raw)
    assert a.reason == "denied"
    assert a.reason_message == "Access denied"


# ── ChatToolCallResultConfirmedAction ─────────────────────────────────────────

def test_tool_call_result_confirmed_has_approved():
    a = ChatToolCallResultConfirmedAction(turn_id="t1", tool_call_id="tc1", approved=True)
    assert a.approved is True


def test_tool_call_result_confirmed_parses_camel_case():
    raw = {"type": "chat/toolCallResultConfirmed", "turnId": "t1", "toolCallId": "tc1", "approved": False}
    a = ChatToolCallResultConfirmedAction.model_validate(raw)
    assert a.approved is False


# ── ChatPendingMessageSetAction ───────────────────────────────────────────────

def test_pending_message_set_has_kind_and_id():
    a = ChatPendingMessageSetAction(
        kind="queued", id="msg-1", message={"role": "user", "content": "hello"}
    )
    assert a.kind == "queued"
    assert a.id == "msg-1"
    assert a.message == {"role": "user", "content": "hello"}


# ── ChatPendingMessageRemovedAction ───────────────────────────────────────────

def test_pending_message_removed_has_kind():
    a = ChatPendingMessageRemovedAction(kind="queued", id="msg-1")
    assert a.kind == "queued"
    assert a.id == "msg-1"


# ── ChatQueuedMessagesReorderedAction ─────────────────────────────────────────

def test_queued_messages_reordered_uses_order_field():
    a = ChatQueuedMessagesReorderedAction(order=["msg-2", "msg-1"])
    assert a.order == ["msg-2", "msg-1"]


def test_queued_messages_reordered_no_ids_field():
    a = ChatQueuedMessagesReorderedAction(order=["msg-1"])
    assert not hasattr(ChatQueuedMessagesReorderedAction, "ids") or "ids" not in ChatQueuedMessagesReorderedAction.model_fields


# ── ChatInputAnswerChangedAction ──────────────────────────────────────────────

def test_input_answer_changed_has_question_id():
    a = ChatInputAnswerChangedAction(
        request_id="req-1", question_id="q-1", answer={"value": "yes"}
    )
    assert a.question_id == "q-1"


def test_input_answer_changed_answer_optional():
    a = ChatInputAnswerChangedAction(request_id="req-1", question_id="q-1")
    assert a.answer is None


def test_input_answer_changed_parses_camel_case():
    raw = {"type": "chat/inputAnswerChanged", "requestId": "req-1", "questionId": "q-1"}
    a = ChatInputAnswerChangedAction.model_validate(raw)
    assert a.question_id == "q-1"


# ── ChatInputCompletedAction ──────────────────────────────────────────────────

def test_input_completed_has_response():
    a = ChatInputCompletedAction(request_id="req-1", response="accepted")
    assert a.response == "accepted"


def test_input_completed_answers_optional():
    a = ChatInputCompletedAction(request_id="req-1", response="declined")
    assert a.answers is None


def test_input_completed_with_answers():
    a = ChatInputCompletedAction(
        request_id="req-1", response="accepted", answers={"q-1": {"value": "yes"}}
    )
    assert a.answers == {"q-1": {"value": "yes"}}
