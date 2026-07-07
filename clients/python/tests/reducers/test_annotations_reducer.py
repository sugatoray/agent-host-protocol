"""Tests for ahp.reducers.annotations.annotations_reducer."""

from __future__ import annotations

from ahp.reducers.annotations import annotations_reducer
from ahp.types import (
    AnnotationAddedAction,
    AnnotationRemovedAction,
    AnnotationsState,
    SessionDisposedAction,
)


def make_state(**overrides) -> AnnotationsState:
    defaults = dict(
        uri="ahp-annotations:/1",
        session_uri="ahp-session:/abc",
        annotations=[],
    )
    defaults.update(overrides)
    return AnnotationsState(**defaults)


def test_annotation_added_appends_annotation():
    state = make_state(annotations=[])
    action = AnnotationAddedAction(annotation={"id": "note-1", "text": "check this"})

    new_state = annotations_reducer(state, action)

    assert new_state.annotations == [{"id": "note-1", "text": "check this"}]


def test_annotation_removed_drops_matching_id():
    state = make_state(
        annotations=[{"id": "note-1", "text": "a"}, {"id": "note-2", "text": "b"}]
    )
    action = AnnotationRemovedAction(annotation_id="note-1")

    new_state = annotations_reducer(state, action)

    assert new_state.annotations == [{"id": "note-2", "text": "b"}]


def test_annotation_removed_is_a_noop_for_unknown_id():
    state = make_state(annotations=[{"id": "note-1", "text": "a"}])
    action = AnnotationRemovedAction(annotation_id="does-not-exist")

    new_state = annotations_reducer(state, action)

    assert new_state.annotations == [{"id": "note-1", "text": "a"}]


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionDisposedAction()

    new_state = annotations_reducer(state, foreign_action)

    assert new_state == state
