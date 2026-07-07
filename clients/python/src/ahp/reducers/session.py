"""Pure reducer for an individual session channel."""

from __future__ import annotations

from ahp.types import (
    SessionActivityChangedAction,
    SessionActiveClientRemovedAction,
    SessionActiveClientSetAction,
    SessionChangesetsChangedAction,
    SessionChatAddedAction,
    SessionChatRemovedAction,
    SessionConfigChangedAction,
    SessionCreationFailedAction,
    SessionCustomizationRemovedAction,
    SessionCustomizationsChangedAction,
    SessionCustomizationToggledAction,
    SessionCustomizationUpdatedAction,
    SessionDefaultChatChangedAction,
    SessionInputNeededRemovedAction,
    SessionInputNeededSetAction,
    SessionIsArchivedChangedAction,
    SessionIsReadChangedAction,
    SessionMcpServerStateChangedAction,
    SessionMetaChangedAction,
    SessionReadyAction,
    SessionServerToolsChangedAction,
    SessionState,
    SessionTitleChangedAction,
    StateAction,
)

# SessionStatus bit flags (from types/channels-session/state.ts)
_IS_READ = 1 << 5      # 32
_IS_ARCHIVED = 1 << 6  # 64


def _with_status_flag(status: int, flag: int, value: bool) -> int:
    return (status | flag) if value else (status & ~flag)


def session_reducer(state: SessionState, action: StateAction) -> SessionState:
    """Apply ``action`` to ``state``, returning a new :class:`SessionState`."""
    if isinstance(action, SessionReadyAction):
        return state.model_copy(update={"lifecycle": "ready"})

    if isinstance(action, SessionCreationFailedAction):
        return state.model_copy(
            update={"lifecycle": "creationFailed", "creation_error": action.error}
        )

    if isinstance(action, SessionTitleChangedAction):
        return state.model_copy(update={"title": action.title})

    if isinstance(action, SessionActivityChangedAction):
        return state.model_copy(update={"activity": action.activity})

    if isinstance(action, SessionChatAddedAction):
        return state.model_copy(update={"chats": [*state.chats, action.summary]})

    if isinstance(action, SessionIsReadChangedAction):
        return state.model_copy(
            update={"status": _with_status_flag(state.status, _IS_READ, action.is_read)}
        )

    if isinstance(action, SessionIsArchivedChangedAction):
        return state.model_copy(
            update={"status": _with_status_flag(state.status, _IS_ARCHIVED, action.is_archived)}
        )

    if isinstance(action, SessionChatRemovedAction):
        # identity field is "resource", not "uri" (canonical types/channels-chat/state.ts)
        remaining = [c for c in state.chats if c.get("resource") != action.chat]
        default_chat = state.default_chat if state.default_chat != action.chat else None
        return state.model_copy(update={"chats": remaining, "default_chat": default_chat})

    if isinstance(action, SessionDefaultChatChangedAction):
        return state.model_copy(update={"default_chat": action.default_chat})

    if isinstance(action, SessionServerToolsChangedAction):
        return state.model_copy(update={"server_tools": list(action.tools)})

    if isinstance(action, SessionActiveClientSetAction):
        clients = [
            c for c in state.active_clients
            if c.get("clientId") != action.active_client.get("clientId")
        ]
        return state.model_copy(update={"active_clients": [*clients, action.active_client]})

    if isinstance(action, SessionActiveClientRemovedAction):
        clients = [c for c in state.active_clients if c.get("clientId") != action.client_id]
        return state.model_copy(update={"active_clients": clients})

    if isinstance(action, SessionInputNeededSetAction):
        existing = [
            r for r in (state.input_needed or [])
            if r.get("id") != action.request.get("id")
        ]
        return state.model_copy(update={"input_needed": [*existing, action.request]})

    if isinstance(action, SessionInputNeededRemovedAction):
        remaining = [r for r in (state.input_needed or []) if r.get("id") != action.id]
        return state.model_copy(update={"input_needed": remaining or None})

    if isinstance(action, SessionCustomizationsChangedAction):
        return state.model_copy(update={"customizations": list(action.customizations)})

    if isinstance(action, SessionCustomizationToggledAction):
        updated = [
            {**c, "enabled": action.enabled} if c.get("id") == action.id else c
            for c in (state.customizations or [])
        ]
        return state.model_copy(update={"customizations": updated})

    if isinstance(action, SessionCustomizationUpdatedAction):
        existing = state.customizations or []
        target_id = action.customization.get("id")
        if any(c.get("id") == target_id for c in existing):
            upserted = [
                action.customization if c.get("id") == target_id else c
                for c in existing
            ]
        else:
            upserted = [*existing, action.customization]
        return state.model_copy(update={"customizations": upserted})

    if isinstance(action, SessionCustomizationRemovedAction):
        existing = state.customizations or []
        # Remove at top level; also remove from children arrays
        without_top = [c for c in existing if c.get("id") != action.id]
        pruned = [
            {**c, "children": [ch for ch in c.get("children", []) if ch.get("id") != action.id]}
            if "children" in c else c
            for c in without_top
        ]
        return state.model_copy(update={"customizations": pruned})

    if isinstance(action, SessionMcpServerStateChangedAction):
        return state  # ponytail: MCP server state is inside config; skip for now

    if isinstance(action, SessionChangesetsChangedAction):
        return state.model_copy(update={"changesets": action.changesets})

    if isinstance(action, SessionConfigChangedAction):
        if action.replace:
            return state.model_copy(update={"config": action.config})
        merged = {**(state.config or {}), **action.config}
        return state.model_copy(update={"config": merged})

    if isinstance(action, SessionMetaChangedAction):
        return state.model_copy(update={"meta": action.meta})

    return state
