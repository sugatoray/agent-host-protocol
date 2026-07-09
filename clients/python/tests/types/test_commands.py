"""Tests for command param/result shapes against canonical types/*.ts."""
import pytest
from ahp.types.commands import (
    COMMANDS,
    CreateChatParams,
    CreateChatResult,
    CreateSessionResult,
    CreateTerminalParams,
    CreateTerminalResult,
    FetchTurnsResult,
    InvokeChangesetOperationParams,
    InvokeChangesetOperationResult,
    ListSessionsParams,
    ListSessionsResult,
    ResolveSessionConfigParams,
    ResolveSessionConfigResult,
    SessionConfigCompletionsParams,
    SessionConfigCompletionsResult,
    CreateResourceWatchParams,
    CreateResourceWatchResult,
)


# ── createSession result = null ──────────────────────────────────────────────

def test_create_session_result_is_empty():
    CreateSessionResult()  # instantiates without error
    assert not CreateSessionResult.model_fields  # no declared fields


# ── createChat ───────────────────────────────────────────────────────────────

def test_create_chat_params_requires_chat_uri():
    p = CreateChatParams(channel="ahp-session:/s1", chat="ahp-chat:/c1")
    assert p.chat == "ahp-chat:/c1"


def test_create_chat_params_optional_fields():
    p = CreateChatParams(
        channel="ahp-session:/s1",
        chat="ahp-chat:/c1",
        initial_message={"role": "user", "content": "hello"},
        source={"chat": "ahp-chat:/old", "turnId": "t1"},
    )
    assert p.initial_message == {"role": "user", "content": "hello"}
    assert p.source == {"chat": "ahp-chat:/old", "turnId": "t1"}


def test_create_chat_params_camel_case():
    raw = {
        "channel": "ahp-session:/s1",
        "chat": "ahp-chat:/c1",
        "initialMessage": {"role": "user", "content": "hi"},
    }
    p = CreateChatParams.model_validate(raw)
    assert p.initial_message == {"role": "user", "content": "hi"}


def test_create_chat_result_is_empty():
    CreateChatResult()
    assert not CreateChatResult.model_fields


def test_create_chat_params_no_title_or_config_fields():
    p = CreateChatParams(channel="ahp-session:/s1", chat="ahp-chat:/c1")
    assert not hasattr(p, "title")
    # extra="allow" means we can't easily check config absence, but the declared fields matter


# ── createTerminal ────────────────────────────────────────────────────────────

def test_create_terminal_params_requires_claim():
    claim = {"kind": "owner"}
    p = CreateTerminalParams(channel="ahp-session:/s1", claim=claim)
    assert p.claim == claim


def test_create_terminal_params_optional_fields():
    p = CreateTerminalParams(
        channel="ahp-session:/s1",
        claim={"kind": "owner"},
        name="My Terminal",
        cwd="file:///home/user",
        cols=80,
        rows=24,
    )
    assert p.name == "My Terminal"
    assert p.cols == 80


def test_create_terminal_result_is_empty():
    CreateTerminalResult()
    assert not CreateTerminalResult.model_fields


# ── fetchTurns result = {} ────────────────────────────────────────────────────

def test_fetch_turns_result_is_empty():
    FetchTurnsResult()
    assert not FetchTurnsResult.model_fields


# ── listSessions ──────────────────────────────────────────────────────────────

def test_list_sessions_params_has_pagination():
    p = ListSessionsParams(channel="ahp-root://", limit=50, cursor="tok")
    assert p.limit == 50
    assert p.cursor == "tok"


def test_list_sessions_params_pagination_optional():
    p = ListSessionsParams(channel="ahp-root://")
    assert p.limit is None
    assert p.cursor is None


def test_list_sessions_result_uses_items_key():
    r = ListSessionsResult(items=[{"resource": "ahp-session:/s1"}])
    assert r.items == [{"resource": "ahp-session:/s1"}]


def test_list_sessions_result_has_next_cursor():
    r = ListSessionsResult(items=[], next_cursor="abc")
    assert r.next_cursor == "abc"


def test_list_sessions_result_next_cursor_camel_case():
    r = ListSessionsResult.model_validate({"items": [], "nextCursor": "abc"})
    assert r.next_cursor == "abc"


# ── resolveSessionConfig ──────────────────────────────────────────────────────

def test_resolve_session_config_params_optional_fields():
    p = ResolveSessionConfigParams(channel="ahp-root://")
    assert p.provider is None
    assert p.working_directory is None
    assert p.config is None


def test_resolve_session_config_params_full():
    p = ResolveSessionConfigParams(
        channel="ahp-root://",
        provider="copilot",
        working_directory="file:///home/user",
        config={"target": "worktree"},
    )
    assert p.provider == "copilot"


def test_resolve_session_config_params_camel_case():
    raw = {"channel": "ahp-root://", "workingDirectory": "file:///home/user"}
    p = ResolveSessionConfigParams.model_validate(raw)
    assert p.working_directory == "file:///home/user"


def test_resolve_session_config_result_has_schema_and_values():
    r = ResolveSessionConfigResult(schema={"type": "object"}, values={"key": "val"})
    assert r.schema_ == {"type": "object"}
    assert r.values == {"key": "val"}


# ── sessionConfigCompletions ──────────────────────────────────────────────────

def test_session_config_completions_params():
    p = SessionConfigCompletionsParams(
        channel="ahp-root://",
        property="baseBranch",
        query="ma",
    )
    assert p.property == "baseBranch"
    assert p.query == "ma"


def test_session_config_completions_params_optional():
    p = SessionConfigCompletionsParams(channel="ahp-root://", property="baseBranch")
    assert p.provider is None
    assert p.working_directory is None
    assert p.config is None
    assert p.query is None


def test_session_config_completions_result():
    r = SessionConfigCompletionsResult(items=[{"value": "main", "label": "main"}])
    assert len(r.items) == 1


def test_session_config_completions_in_registry():
    assert "sessionConfigCompletions" in COMMANDS


# ── createResourceWatch ───────────────────────────────────────────────────────

def test_create_resource_watch_params():
    p = CreateResourceWatchParams(channel="ahp-root://", uri="file:///workspace", recursive=True)
    assert p.uri == "file:///workspace"
    assert p.recursive is True


def test_create_resource_watch_params_optional():
    p = CreateResourceWatchParams(channel="ahp-root://", uri="file:///workspace")
    assert p.recursive is None
    assert p.excludes is None
    assert p.includes is None


def test_create_resource_watch_result():
    r = CreateResourceWatchResult(channel="ahp-resource-watch:/abc")
    assert r.channel == "ahp-resource-watch:/abc"


def test_create_resource_watch_in_registry():
    assert "createResourceWatch" in COMMANDS


# ── invokeChangesetOperation ──────────────────────────────────────────────────

def test_invoke_changeset_operation_params():
    p = InvokeChangesetOperationParams(
        channel="ahp-changeset:/c1",
        operation_id="apply",
    )
    assert p.operation_id == "apply"
    assert p.target is None


def test_invoke_changeset_operation_params_camel_case():
    raw = {"channel": "ahp-changeset:/c1", "operationId": "apply"}
    p = InvokeChangesetOperationParams.model_validate(raw)
    assert p.operation_id == "apply"


def test_invoke_changeset_operation_result_optional_fields():
    r = InvokeChangesetOperationResult()
    assert r.message is None
    assert r.follow_up is None


def test_invoke_changeset_operation_result_with_fields():
    r = InvokeChangesetOperationResult(message="Applied", follow_up={"content": {"uri": "https://pr"}})
    assert r.message == "Applied"
