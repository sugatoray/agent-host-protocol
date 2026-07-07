"""Tests for ahp.reducers.root.root_reducer."""

from __future__ import annotations

from ahp.reducers.root import root_reducer
from ahp.types import (
    AgentInfo,
    RootActiveSessionsChangedAction,
    RootAgentsChangedAction,
    RootConfigChangedAction,
    RootState,
    RootTerminalsChangedAction,
    SessionTitleChangedAction,
)


def make_state(**overrides) -> RootState:
    defaults: dict = dict(agents=[], active_sessions=None)
    defaults.update(overrides)
    return RootState(**defaults)


def test_agents_changed_replaces_agent_list():
    state = make_state(agents=[AgentInfo(provider="old", display_name="Old")])
    action = RootAgentsChangedAction(
        agents=[{"provider": "copilot", "displayName": "Copilot", "description": ""}]
    )

    new_state = root_reducer(state, action)

    assert len(new_state.agents) == 1
    # reducer must not mutate the input state in place
    assert state.agents[0].provider == "old"


def test_active_sessions_changed():
    state = make_state(active_sessions=None)
    action = RootActiveSessionsChangedAction(active_sessions=3)

    new_state = root_reducer(state, action)

    assert new_state.active_sessions == 3
    assert state.active_sessions is None


def test_terminals_changed_replaces_terminals():
    state = make_state()
    action = RootTerminalsChangedAction(terminals=[{"id": "t1"}, {"id": "t2"}])

    new_state = root_reducer(state, action)

    assert len(new_state.terminals) == 2


def test_config_changed_merges_by_default():
    state = make_state()
    state = state.model_copy(update={"config": {"a": 1}})
    action = RootConfigChangedAction(config={"b": 2})

    new_state = root_reducer(state, action)

    assert new_state.config == {"a": 1, "b": 2}


def test_config_changed_replace_overwrites():
    state = make_state()
    state = state.model_copy(update={"config": {"a": 1, "c": 3}})
    action = RootConfigChangedAction(config={"b": 2}, replace=True)

    new_state = root_reducer(state, action)

    assert new_state.config == {"b": 2}


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionTitleChangedAction(title="other channel")

    new_state = root_reducer(state, foreign_action)

    assert new_state == state
