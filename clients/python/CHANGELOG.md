# Changelog

All notable changes to the AHP Python client will be documented here. Follows
[Keep a Changelog](https://keepachangelog.com/) conventions; this client releases
independently on its own `python/vX.Y.Z` tags, per the convention used by the
Rust/Go/TypeScript/Kotlin clients in this repo.

## [Unreleased]

### Added

- `ChatToolCallApprovedAction` and `ChatToolCallDeniedAction`: typed convenience
  models for constructing/dispatching tool-call confirmations. `approved: Literal[True]`
  with required `confirmed: str` (ToolCallConfirmationReason), and `approved: Literal[False]`
  with required `reason: str` (ToolCallCancellationReason), respectively. Both exported
  from `ahp.types`. See `types/channels-chat/actions.ts:226–271`.

- `TelemetryCapabilities`: new model in `ahp.types` with optional `logs`, `traces`,
  `metrics` URI fields, matching `types/channels-otlp/state.ts:35–68`. `InitializeResult.telemetry`
  typed as `TelemetryCapabilities | None` instead of `dict[str, Any] | None`. The `logs`
  URI may be an RFC 6570 template with a `{level}` variable.

- `AhpClient.ping()`: liveness-check wrapper that sends a `ping` request to the host.

- `ahp.reducers.resource_watch`: new `resource_watch_reducer` for the
  `ResourceWatch` channel family. State is a pass-through (change events are
  ephemeral); the reducer exists so the channel is handled uniformly.

- Structured logging in `ahp.client`: `logging.getLogger("ahp.client")` emits
  `WARNING` for malformed messages in the reader loop and for unhandled host
  requests, and `ERROR` for unexpected exceptions in `_handle_host_request`.

### Fixed

- **`ChatToolCallConfirmedAction` subtype fields** — added `confirmed`, `reason`,
  `reason_message`, `user_suggestion`, `edited_tool_input`, and `selected_option_id`
  fields. Previously `approved: bool` was the only discrimination point; denied
  tool-call `reason` strings and approved `confirmed` reasons were silently dropped.
  Canonical TS uses `ChatToolCallApprovedAction | ChatToolCallDeniedAction` (two
  concrete interfaces); Python keeps a flat model as the `StateAction` union member
  (pydantic cannot discriminate two entries with the same `type` literal) but now
  exposes all fields from both subtypes.

- **`Turn.state` type** — changed from `dict[str, Any]` (defaulting to
  `{"type": "running"}`) to `Literal["complete", "cancelled", "error"]`, matching
  canonical `types/channels-chat/state.ts:477–481`. Only completed turns appear in
  `ChatState.turns`; in-progress turns are tracked in `ChatState.active_turn` (a
  `dict | None`, mirroring the wire `ActiveTurn` shape). `ChatState.active_turn` type
  corrected from `str | None` to `dict[str, Any] | None`. Chat reducer rewritten
  accordingly: `ChatTurnStartedAction` populates `active_turn`; delta/reasoning
  actions update it; complete/cancelled/error actions finalize the turn into `turns`
  and clear `active_turn`.

- **Full field-by-field reconciliation against canonical `types/*.ts`** (2026-07-07,
  commit `8fceda9`) — substantially all types and reducers were incorrect. Specific
  fixes across every channel:
  - `Snapshot`, `ActionEnvelope`, `ClientCapabilities`, `ProtocolVersion` — field
    names and types corrected.
  - `CreateSession/Chat/TerminalResult` — now empty (`result: null` per protocol);
    client generates the URI client-side via `uuid.uuid4()` and passes it as
    the `channel` param.
  - `FetchTurnsResult` — now empty (turns arrive via `chat/turnsLoaded` action).
  - `ListSessionsParams/Result`, `ResolveSessionConfigParams/Result`,
    `SessionConfigCompletionsParams/Result`, `CreateResourceWatchParams/Result`,
    `InvokeChangesetOperationParams/Result` — added or corrected.
  - `auth/required`, `root/sessionRemoved`, `root/sessionSummaryChanged`,
    `root/progress` (was `$/progress`), `otlp/export*` notifications — field names
    corrected.
  - `AhpErrorCode` — all values now match `types/common/errors.ts:41–98` exactly.
  - `SessionState` — all canonical fields present.
  - Session reducer — `IsRead`/`IsArchived` status bitflags, `CustomizationUpdated`
    upsert, `CustomizationRemoved` cascade, `ChatRemoved` (now filters by
    `c.get("resource")` not `"uri"`).
  - `ChatState` — `resource`, `title`, `status`, `activity`, `modified_at`, `turns`,
    `turns_next_cursor`, `steering_message`, `queued_messages`, `input_requests`,
    `draft`, `meta`.
  - Chat action field shapes — `ChatToolCallConfirmedAction`/`ResultConfirmedAction`
    (`approved: bool`), `ChatPendingMessageSetAction` (`kind`, `id`),
    `ChatPendingMessageRemovedAction` (`kind`), `ChatQueuedMessagesReorderedAction`
    (`order` not `ids`), `ChatInputAnswerChangedAction` (`questionId`, optional
    `answer`), `ChatInputCompletedAction` (`response` required, `answers` optional).
  - `TerminalState` — matches `types/channels-terminal/state.ts:79–110`.
  - Terminal reducer — `TerminalDataAction` appends to correct part type
    (`command` output or `unclassified`); no more invented `{"type":"data"}` part.
    `TerminalCommandExecutedAction`/`TerminalCommandFinishedAction` implemented.
  - `ChangesetState` — `status`, `error`, `files`, `operations`.
  - `ChangesetFileRemovedAction` (`fileId` alias), `ChangesetContentChangedAction`
    (`files`/`operations`/`error`).
  - `ResourceWatchState{root, recursive, excludes?, includes?}` — added to
    `state.py` and included in the `AnyChannelState` union.
  - `ResourceWatchChangedAction.changes` — `list[Any]` not `dict[str, Any]`.

### Added

- `AhpClient.unsubscribe()`, plus the full session/chat/terminal lifecycle:
  `create_session`/`dispose_session`/`list_sessions`,
  `create_chat`/`dispose_chat`/`fetch_turns`, and
  `create_terminal`/`dispose_terminal`. Also `completions()` and
  `invoke_changeset_operation()`. Built via Red/Green TDD
  (`tests/client/test_lifecycle.py`, 11 tests, real run, all passing).

### Fixed

- `ahp/types/__init__.py` didn't re-export the command `Params`/`Result`
  models from `ahp.types.commands` (only the `COMMANDS` registry dict), so
  `ResourceListResult`/`ResourceReadResult`/`ResourceStatResult`/etc. weren't
  importable from `ahp.types` directly — broke `tests/client/test_resource_provider.py`
  at collection. Found by running the full test suite for the first time
  against a real pydantic install (previously only `py_compile`-checked).
  All 94 tests pass now.

### Added

- `ahp.hosts.MultiHostClient`: a host_id-keyed registry over `AhpClient` —
  `.single(client)` for the common single-host case, `add_host`/`remove_host`/
  `client_for`, concurrent `initialize_all`/`close_all` (the latter tolerates
  individual hosts failing to close), and `get_state`/`dispatch_action`
  convenience delegates. Pure fan-out, no new protocol logic.
- `AhpClient.reconnect()`: sends per-channel `last_seen_server_seq`, overwrites
  local state for any `resnapshotted` channels, and leaves `replayed` channels
  for the existing `action`-notification handler to catch up on normally
  (including correctly deduplicating this client's own pre-drop actions).
  Optionally swaps in a new `Transport`.
- `AhpClient.authenticate()` / `resource_read()` / `resource_write()` /
  `resource_list()` / `resource_stat()`: the client-initiated half of the
  symmetric commands.
- `AhpClient.register_resource_provider()` + a new `ResourceProvider`
  protocol: the host-initiated half — the reader loop now also handles
  incoming `JsonRpcRequest` messages (not just responses/notifications),
  routing `resource*` calls to the registered provider and always replying
  with success or a JSON-RPC error, so a missing provider or a provider bug
  can't crash the reader loop.
- `ahp.client.AhpClient`: `initialize`, `subscribe`, `dispatch_action` (with
  write-ahead reconciliation against the host's `action` notification echo),
  `get_state`, `close`, async context manager support.
- `ahp.transport`: the `Transport` structural protocol, `InMemoryTransport`
  (paired in-memory duplex for testing), and `WebSocketTransport` (wraps any
  duck-typed async connection; real `websockets` package only imported lazily
  inside `.connect()`). Built via Red/Green TDD and verified by actually
  running the test suite (24/24 passing) in-sandbox via a minimal throwaway
  runner, since neither `pytest` nor `websockets` were installable there.
- `ahp.reducers`: pure `(state, action) -> new_state` reducers for all six
  channel families (root/session/chat/terminal/changeset/annotations), built via
  Red/Green TDD — see `tests/reducers/`. Each reducer is a strict no-op for
  actions outside its own family.
- Reorganized `tests/` into `tests/types/`, `tests/reducers/`, `tests/transport/`,
  `tests/client/`, and `tests/hosts/` subfolders. Fake-host scripting helpers
  shared across `tests/client/*` were factored into `tests/client/_helpers.py`
  rather than duplicated per file.
- Initial scaffold of `ahp.types`: common types, JSON-RPC envelope, error types,
  per-channel state models, `StateAction` discriminated union (seed set of
  variants), `CommandMap`-equivalent command registry, and notification payloads.
- `pyproject.toml` targeting `pydantic>=2.0,<3.0`, Python `>=3.10`.
- Smoke tests for camelCase/snake_case round-tripping and discriminated-union
  parsing (`tests/types/test_types.py`).
- `ahp/__init__.py` now re-exports the public API (`AhpClient`,
  `MultiHostClient`, etc.).

### Fixed

- `InMemoryTransport.close()` previously only signaled the *peer* end; a
  `receive()` call already blocked on *this* end's own queue (e.g. a reader
  loop parked mid-poll, exactly what `AhpClient` does) would hang forever.
  Found while wiring up `AhpClient.close()`; fixed with a regression test
  (`test_close_unblocks_a_receive_already_pending_on_the_same_end`) confirmed
  against the old (deadlocking) code before the fix.

### Verification status

Everything in `ahp.types`, `ahp.reducers`, and `ahp.transport` is Red/Green
TDD'd; the transport layer was *actually executed* in-sandbox (24/24 passing).
Everything in `ahp.client` and `ahp.hosts` is syntax-checked only
(`py_compile`) — no network access to install `pydantic` in the sandbox this
was built in. **Run `pytest` for real before relying on `AhpClient` or
`MultiHostClient`.** See `SPEC.md` §7a for details.

Not yet implemented: `unsubscribe()`. See `SPEC.md` for the phased plan.
