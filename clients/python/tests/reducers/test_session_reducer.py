"""Tests for ahp.reducers.session.session_reducer."""

from __future__ import annotations

from ahp.reducers.session import session_reducer
from ahp.types import (
    RootAgentsChangedAction,
    SessionActivityChangedAction,
    SessionChatAddedAction,
    SessionChatRemovedAction,
    SessionConfigChangedAction,
    SessionCreationFailedAction,
    SessionCustomizationRemovedAction,
    SessionCustomizationUpdatedAction,
    SessionIsArchivedChangedAction,
    SessionIsReadChangedAction,
    SessionReadyAction,
    SessionState,
    SessionTitleChangedAction,
)


def make_state(**overrides) -> SessionState:
    defaults: dict = dict(provider="", title="", lifecycle="creating", active_clients=[], chats=[])
    defaults.update(overrides)
    return SessionState(**defaults)


def test_ready_transitions_lifecycle():
    state = make_state(lifecycle="creating")
    action = SessionReadyAction()

    new_state = session_reducer(state, action)

    assert new_state.lifecycle == "ready"
    assert state.lifecycle == "creating"  # input not mutated


def test_creation_failed_sets_lifecycle_and_error():
    state = make_state(lifecycle="creating")
    error = {"errorType": "ProviderUnavailable", "message": "offline"}
    action = SessionCreationFailedAction(error=error)

    new_state = session_reducer(state, action)

    assert new_state.lifecycle == "creationFailed"
    assert new_state.creation_error == error


def test_title_changed_updates_title():
    state = make_state(title="Untitled")
    action = SessionTitleChangedAction(title="Debugging flaky test")

    new_state = session_reducer(state, action)

    assert new_state.title == "Debugging flaky test"
    assert state.title == "Untitled"  # input not mutated


def test_activity_changed():
    state = make_state()
    action = SessionActivityChangedAction(activity="running")

    new_state = session_reducer(state, action)

    assert new_state.activity == "running"


def test_chat_added_appends_summary():
    state = make_state(chats=[{"uri": "ahp-chat:/1", "title": "First"}])
    action = SessionChatAddedAction(summary={"uri": "ahp-chat:/2", "title": "Second"})

    new_state = session_reducer(state, action)

    assert len(new_state.chats) == 2
    assert new_state.chats[-1]["uri"] == "ahp-chat:/2"


def test_chat_removed_drops_by_resource():
    # canonical identity field is "resource", not "uri"
    state = make_state(
        chats=[{"resource": "ahp-chat:/1"}, {"resource": "ahp-chat:/2"}]
    )
    action = SessionChatRemovedAction(chat="ahp-chat:/1")

    new_state = session_reducer(state, action)

    assert len(new_state.chats) == 1
    assert new_state.chats[0]["resource"] == "ahp-chat:/2"


def test_chat_removed_clears_default_chat_when_it_matches():
    state = make_state(
        chats=[{"resource": "ahp-chat:/1"}, {"resource": "ahp-chat:/2"}],
        default_chat="ahp-chat:/1",
    )
    action = SessionChatRemovedAction(chat="ahp-chat:/1")

    new_state = session_reducer(state, action)

    assert new_state.default_chat is None


def test_config_changed_merges():
    state = make_state()
    state = state.model_copy(update={"config": {"model": "gpt-4"}})
    action = SessionConfigChangedAction(config={"temperature": 0.7})

    new_state = session_reducer(state, action)

    assert new_state.config == {"model": "gpt-4", "temperature": 0.7}


def test_config_changed_replace():
    state = make_state()
    state = state.model_copy(update={"config": {"model": "gpt-4"}})
    action = SessionConfigChangedAction(config={"model": "claude-3"}, replace=True)

    new_state = session_reducer(state, action)

    assert new_state.config == {"model": "claude-3"}


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = RootAgentsChangedAction(agents=[])

    new_state = session_reducer(state, foreign_action)

    assert new_state == state


# ── SessionStatus bit flags ──────────────────────────────────────────────────
# IsRead = 1 << 5 = 32,  IsArchived = 1 << 6 = 64

def test_is_read_changed_sets_bit():
    state = make_state()  # status=1 (Idle)
    new_state = session_reducer(state, SessionIsReadChangedAction(is_read=True))
    assert new_state.status == 1 | 32  # 33


def test_is_read_changed_clears_bit():
    state = make_state(status=1 | 32)  # already read
    new_state = session_reducer(state, SessionIsReadChangedAction(is_read=False))
    assert new_state.status == 1


def test_is_archived_changed_sets_bit():
    state = make_state()
    new_state = session_reducer(state, SessionIsArchivedChangedAction(is_archived=True))
    assert new_state.status == 1 | 64  # 65


def test_is_archived_changed_clears_bit():
    state = make_state(status=1 | 64)
    new_state = session_reducer(state, SessionIsArchivedChangedAction(is_archived=False))
    assert new_state.status == 1


# ── customizationUpdated ─────────────────────────────────────────────────────

def test_customization_updated_upserts_by_id():
    c1 = {"id": "plugin-a", "name": "Plugin A", "enabled": True, "load": {"kind": "loading"}}
    c2 = {"id": "plugin-b", "name": "Plugin B", "enabled": True}
    state = make_state(customizations=[c1, c2])

    updated = {"id": "plugin-a", "name": "Plugin A", "enabled": True, "load": {"kind": "error"}}
    new_state = session_reducer(state, SessionCustomizationUpdatedAction(customization=updated))

    assert len(new_state.customizations) == 2
    assert new_state.customizations[0]["load"] == {"kind": "error"}
    assert new_state.customizations[1]["id"] == "plugin-b"


def test_customization_updated_appends_when_unknown_id():
    c1 = {"id": "plugin-a", "name": "Plugin A", "enabled": True}
    state = make_state(customizations=[c1])

    new_c = {"id": "plugin-b", "name": "Plugin B", "enabled": False}
    new_state = session_reducer(state, SessionCustomizationUpdatedAction(customization=new_c))

    assert len(new_state.customizations) == 2
    assert new_state.customizations[-1]["id"] == "plugin-b"


def test_customization_updated_creates_list_when_none():
    state = make_state(customizations=None)
    new_c = {"id": "plugin-x", "name": "X"}
    new_state = session_reducer(state, SessionCustomizationUpdatedAction(customization=new_c))
    assert len(new_state.customizations) == 1


# ── customizationRemoved ─────────────────────────────────────────────────────

def test_customization_removed_removes_container_and_children():
    skill = {"id": "skill-1", "name": "lint"}
    plugin_a = {"id": "plugin-a", "name": "Plugin A", "children": [skill]}
    plugin_b = {"id": "plugin-b", "name": "Plugin B"}
    state = make_state(customizations=[plugin_a, plugin_b])

    new_state = session_reducer(state, SessionCustomizationRemovedAction(id="plugin-a"))

    assert len(new_state.customizations) == 1
    assert new_state.customizations[0]["id"] == "plugin-b"


def test_customization_removed_removes_child():
    skill_1 = {"id": "skill-1", "name": "lint"}
    skill_2 = {"id": "skill-2", "name": "refactor"}
    plugin_a = {"id": "plugin-a", "name": "Plugin A", "children": [skill_1, skill_2]}
    state = make_state(customizations=[plugin_a])

    new_state = session_reducer(state, SessionCustomizationRemovedAction(id="skill-1"))

    assert len(new_state.customizations) == 1
    children = new_state.customizations[0]["children"]
    assert len(children) == 1
    assert children[0]["id"] == "skill-2"


def test_customization_removed_noop_for_unknown_id():
    c1 = {"id": "plugin-a", "name": "Plugin A"}
    state = make_state(customizations=[c1])

    new_state = session_reducer(state, SessionCustomizationRemovedAction(id="unknown"))

    assert len(new_state.customizations) == 1
