"""Tests for ahp.reducers.annotations.annotations_reducer."""

from __future__ import annotations

from ahp.reducers.annotations import annotations_reducer
from ahp.types import (
    Annotation,
    AnnotationsEntryRemovedAction,
    AnnotationsEntrySetAction,
    AnnotationsRemovedAction,
    AnnotationsSetAction,
    AnnotationsState,
    AnnotationsUpdatedAction,
    SessionTitleChangedAction,
)


def make_state(**overrides) -> AnnotationsState:
    defaults: dict = dict(annotations=[])
    defaults.update(overrides)
    return AnnotationsState(**defaults)


def make_annotation(id: str, **overrides) -> Annotation:
    return Annotation(id=id, entries=[], **overrides)


def test_set_adds_new_annotation():
    state = make_state()
    action = AnnotationsSetAction(annotation={"id": "note-1", "entries": [], "resolved": False})

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations) == 1
    assert new_state.annotations[0].id == "note-1"


def test_set_replaces_existing_annotation_by_id():
    state = make_state(annotations=[make_annotation("note-1", resolved=False)])
    action = AnnotationsSetAction(annotation={"id": "note-1", "entries": [], "resolved": True})

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations) == 1
    assert new_state.annotations[0].resolved is True


def test_updated_patches_fields():
    state = make_state(annotations=[make_annotation("note-1", resolved=False)])
    action = AnnotationsUpdatedAction(id="note-1", changes={"resolved": True})

    new_state = annotations_reducer(state, action)

    assert new_state.annotations[0].resolved is True


def test_removed_drops_by_id():
    state = make_state(
        annotations=[make_annotation("note-1"), make_annotation("note-2")]
    )
    action = AnnotationsRemovedAction(annotation_id="note-1")

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations) == 1
    assert new_state.annotations[0].id == "note-2"


def test_removed_is_a_noop_for_unknown_id():
    state = make_state(annotations=[make_annotation("note-1")])
    action = AnnotationsRemovedAction(annotation_id="does-not-exist")

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations) == 1


def test_entry_set_appends_entry():
    state = make_state(annotations=[make_annotation("note-1")])
    action = AnnotationsEntrySetAction(
        annotation_id="note-1", entry={"id": "e1", "comment": "look here"}
    )

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations[0].entries) == 1
    assert new_state.annotations[0].entries[0]["id"] == "e1"


def test_entry_set_replaces_existing_entry_by_id():
    ann = make_annotation("note-1")
    ann = ann.model_copy(update={"entries": [{"id": "e1", "comment": "old"}]})
    state = make_state(annotations=[ann])
    action = AnnotationsEntrySetAction(
        annotation_id="note-1", entry={"id": "e1", "comment": "new"}
    )

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations[0].entries) == 1
    assert new_state.annotations[0].entries[0]["comment"] == "new"


def test_entry_removed_drops_by_entry_id():
    ann = make_annotation("note-1")
    ann = ann.model_copy(update={"entries": [{"id": "e1"}, {"id": "e2"}]})
    state = make_state(annotations=[ann])
    action = AnnotationsEntryRemovedAction(annotation_id="note-1", entry_id="e1")

    new_state = annotations_reducer(state, action)

    assert len(new_state.annotations[0].entries) == 1
    assert new_state.annotations[0].entries[0]["id"] == "e2"


def test_reducer_ignores_actions_belonging_to_other_channels():
    state = make_state()
    foreign_action = SessionTitleChangedAction(title="other")

    new_state = annotations_reducer(state, foreign_action)

    assert new_state == state
