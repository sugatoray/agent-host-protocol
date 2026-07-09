"""Tests for ahp.reducers.resource_watch.resource_watch_reducer."""

from __future__ import annotations

from ahp.reducers.resource_watch import resource_watch_reducer
from ahp.types import ResourceWatchState
from ahp.types.actions import ResourceWatchChangedAction


def make_state(**overrides) -> ResourceWatchState:
    defaults: dict = dict(root="file:///workspace", recursive=False)
    defaults.update(overrides)
    return ResourceWatchState(**defaults)


def test_resource_watch_state_has_root_and_recursive():
    state = ResourceWatchState(root="file:///workspace", recursive=True)
    assert state.root == "file:///workspace"
    assert state.recursive is True


def test_resource_watch_state_optional_fields():
    state = ResourceWatchState(root="file:///workspace", recursive=False)
    assert state.excludes is None
    assert state.includes is None


def test_resource_watch_state_with_excludes():
    state = ResourceWatchState(
        root="file:///workspace",
        recursive=True,
        excludes={"items": ["**/.git/**", "**/node_modules/**"]},
    )
    assert state.excludes == {"items": ["**/.git/**", "**/node_modules/**"]}


def test_changed_action_is_pass_through():
    # resourceWatch/changed never mutates state — events are ephemeral
    state = make_state()
    changes = [{"uri": "file:///workspace/src/a.ts", "type": "updated"}]
    action = ResourceWatchChangedAction(changes=changes)

    new_state = resource_watch_reducer(state, action)

    assert new_state == state


def test_unknown_action_is_pass_through():
    from ahp.types import SessionTitleChangedAction
    state = make_state()
    new_state = resource_watch_reducer(state, SessionTitleChangedAction(title="other"))
    assert new_state == state
