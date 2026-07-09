"""Pure reducer for an annotations channel within a session."""

from __future__ import annotations

from ahp.types import (
    Annotation,
    AnnotationsEntryRemovedAction,
    AnnotationsEntrySetAction,
    AnnotationsRemovedAction,
    AnnotationsSetAction,
    AnnotationsState,
    AnnotationsUpdatedAction,
    StateAction,
)


def annotations_reducer(state: AnnotationsState, action: StateAction) -> AnnotationsState:
    """Apply ``action`` to ``state``, returning a new :class:`AnnotationsState`."""
    if isinstance(action, AnnotationsSetAction):
        ann = Annotation.model_validate(action.annotation)
        existing = [a for a in state.annotations if a.id != ann.id]
        return state.model_copy(update={"annotations": [*existing, ann]})

    if isinstance(action, AnnotationsUpdatedAction):
        updated = [
            a.model_copy(update=action.changes) if a.id == action.id else a
            for a in state.annotations
        ]
        return state.model_copy(update={"annotations": updated})

    if isinstance(action, AnnotationsRemovedAction):
        remaining = [a for a in state.annotations if a.id != action.annotation_id]
        if len(remaining) == len(state.annotations):
            return state
        return state.model_copy(update={"annotations": remaining})

    if isinstance(action, AnnotationsEntrySetAction):
        new_anns = []
        for ann in state.annotations:
            if ann.id == action.annotation_id:
                entry_id = action.entry.get("id")
                existing_entries = [e for e in ann.entries if e.get("id") != entry_id]
                new_anns.append(ann.model_copy(
                    update={"entries": [*existing_entries, action.entry]}
                ))
            else:
                new_anns.append(ann)
        return state.model_copy(update={"annotations": new_anns})

    if isinstance(action, AnnotationsEntryRemovedAction):
        new_anns = []
        for ann in state.annotations:
            if ann.id == action.annotation_id:
                remaining_entries = [
                    e for e in ann.entries if e.get("id") != action.entry_id
                ]
                new_anns.append(ann.model_copy(update={"entries": remaining_entries}))
            else:
                new_anns.append(ann)
        return state.model_copy(update={"annotations": new_anns})

    return state
