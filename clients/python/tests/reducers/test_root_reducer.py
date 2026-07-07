"""Tests for ahp.reducers.root.root_reducer.

TDD note: this file is written before ``ahp/reducers/root.py`` exists (or before
it handles these cases), per the Red/Green TDD workflow requested for this
package. Running `pytest tests/reducers/test_root_reducer.py` right now should
fail with an ImportError / AttributeError until `ahp.reducers.root` is
implemented to satisfy it.
"""

from __future__ import annotations

from ahp.reducers.root import root_reducer
from ahp.types import (
    AgentInfo,
    RootAgentsChangedAction,
    RootSessionAddedAction,
    RootSessionRemovedAction,
    RootState,
    TerminalOutputAction,
)


def make_state(**overrides) -> RootState:
    defaults = dict(agents=[], active_sessions=0, session_uris=[])
    defaults.update(overrides)
    return RootState(**defaults)


def test_agents_changed_replaces_agent_list():
    state = make_state(agents=[AgentInfo(provider="old")])
    action = RootAgentsChangedAction(agents=[AgentInfo(provider="copilot", id="a1")])

    new_state = root_reducer(state, action)

    assert [a.provider for a in new_state.agents] == ["copilot"]
    # reducer must not mutate the input state in place
    assert state.agents[0].provider == "old"


def test_session_added_appends_new_uri():
    state = make_state(session_uris=["ahp-session:/existing"])
    action = RootSessionAddedAction(session_uri="ahp-session:/new")

    new_state = root_reducer(state, action)

    assert new_state.session_uris == ["ahp-session:/existing", "ahp-session:/new"]


def test_session_added_is_idempotent_for_duplicate_uri():
    state = make_state(session_uris=["ahp-session:/dup"])
    action = RootSessionAddedAction(session_uri="ahp-session:/dup")

    new_state = root_reducer(state, action)

    assert new_state.session_uris == ["ahp-session:/dup"]


def test_session_removed_drops_matching_uri():
    state = make_state(session_uris=["ahp-session:/a", "ahp-session:/b"])
    action = RootSessionRemovedAction(session_uri="ahp-session:/a")

    new_state = root_reducer(state, action)

    assert new_state.session_uris == ["ahp-session:/b"]


def test_session_removed_is_a_noop_for_unknown_uri():
    state = make_state(session_uris=["ahp-session:/a"])
    action = RootSessionRemovedAction(session_uri="ahp-session:/does-not-exist")

    new_state = root_reducer(state, action)

    assert new_state.session_uris == ["ahp-session:/a"]


def test_reducer_ignores_actions_belonging_to_other_channels():
    """The root channel only ever receives root/* actions in practice (the client
    routes by channel), but the reducer itself must be defensive: an
    out-of-family action should be a strict no-op rather than raising.
    """
    state = make_state(session_uris=["ahp-session:/a"])
    foreign_action = TerminalOutputAction(data="ls -la\n")

    new_state = root_reducer(state, foreign_action)

    assert new_state == state
