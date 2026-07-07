"""Pure reducer for an annotations channel within a session
(``ahp-annotations:/<uuid>``).
"""

from __future__ import annotations

from ahp.types import (
    AnnotationAddedAction,
    AnnotationRemovedAction,
    AnnotationsState,
    StateAction,
)


def annotations_reducer(state: AnnotationsState, action: StateAction) -> AnnotationsState:
    """Apply ``action`` to ``state``, returning a new :class:`AnnotationsState`.

    As with the other channel reducers, actions outside the ``annotations/*``
    family are a no-op.

    NOTE: individual annotations are modeled as loose ``dict`` payloads (see
    ``ahp.types.state.AnnotationsState``) pending a firmer schema for what an
    annotation actually contains; the removal match is keyed on an ``"id"`` key
    by convention rather than a typed field.
    """
    if isinstance(action, AnnotationAddedAction):
        return state.model_copy(
            update={"annotations": [*state.annotations, action.annotation]}
        )

    if isinstance(action, AnnotationRemovedAction):
        remaining = [
            a for a in state.annotations if a.get("id") != action.annotation_id
        ]
        if len(remaining) == len(state.annotations):
            return state
        return state.model_copy(update={"annotations": remaining})

    return state
