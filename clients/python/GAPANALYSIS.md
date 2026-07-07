# Gap Analysis — Python client vs. canonical protocol source

> **See also [`GAPCONTEXT.md`](./GAPCONTEXT.md)** for cross-client evidence and
> rationale on *why* the gaps below matter. `GAPANALYSIS.md` answers *what* is
> wrong; `GAPCONTEXT.md` answers *why it's worth fixing*.
>
> Originally produced 2026-07-06, diffing `clients/python/src/ahp/{types,reducers}`
> against the canonical TypeScript source at repo-root `types/` (per-channel
> `channels-*/{state,actions,commands,notifications,reducer}.ts` + `common/*.ts`), with
> `schema/*.schema.json` as a secondary reference where the TS was ambiguous.
>
> **Re-verified 2026-07-07** after two passes of Red/Green TDD work (commits
> `8fceda9` and the session that followed it) that closed all five priorities from the
> prior revision's sequencing list. Full suite: **213/213 passing** (`uv run pytest -v`,
> 2026-07-07). This revision replaces the prior "short mechanical list" framing —
> essentially everything mechanical is now done.

## `common/`

**State primitives** — FIXED. `Snapshot`, `ActionEnvelope`, `ClientCapabilities`,
`ProtocolVersion` match canonical `types/common/*.ts` field-for-field.

**Commands** — FIXED. All command param/result shapes now match canonical TS:

- `CreateSessionResult`, `CreateChatResult`, `CreateTerminalResult` — all empty
  (match TS `result: null`). Client generates the URI client-side via `uuid.uuid4()`
  and passes it as the `channel` param, exactly per protocol.
- `CreateChatParams` — `{channel, chat, initialMessage?, source?}`. Client-chosen
  `chat` URI passed in.
- `CreateTerminalParams` — `{channel, claim (required), name?, cwd?, cols?, rows?}`.
- `FetchTurnsResult` — empty. Turns arrive via `chat/turnsLoaded` action.
- `ListSessionsParams` — `{channel, limit?, cursor?}`.
  `ListSessionsResult` — `{items, nextCursor?}`.
- `ResolveSessionConfigParams` — `{channel, provider?, workingDirectory?, config?}`.
  `ResolveSessionConfigResult` — `{schema, values}`.
- `SessionConfigCompletionsParams/Result` — added; registered in `COMMANDS`.
- `CreateResourceWatchParams/Result` — added; registered in `COMMANDS`.
- `InvokeChangesetOperationParams` — `{channel, operationId, target?}`.
  `InvokeChangesetOperationResult` — `{message?, followUp?}`.

`AhpClient` updated accordingly: `create_session`/`create_chat`/`create_terminal`
all return client-generated URIs; `fetch_turns` returns `None`; `list_sessions`
returns `ListSessionsResult`; `invoke_changeset_operation` returns a typed result.

**Notifications** — FIXED. All field shapes match canonical TS:

- `auth/required` — `{channel, resource, reason?}`.
- `root/sessionRemoved` — `{channel, session}`.
- `root/sessionSummaryChanged` — `{channel, session, changes}`.
- `root/progress` — `{channel, progressToken, progress, total?, message?}`.
  Registry key: `"root/progress"` (was incorrectly `"$/progress"`).
- `otlp/exportLogs`, `otlp/exportTraces`, `otlp/exportMetrics` — `{channel, payload}`.
  No longer flattened into direct fields.

**Errors** — FIXED. `AhpErrorCode` matches `types/common/errors.ts:41-98` exactly.

## `root`

FIXED, fully. State, all 4 action variants, and `reducers/root.py` match canonical TS.

## `session`

**State** — FIXED. `SessionState` carries every canonical field.

**Actions** — FIXED. All 22+ canonical variants with matching field names.

**Reducer** — FIXED. All previously-no-op branches now implemented:
- `SessionIsReadChangedAction` — uses `status` bitflag `1 << 5` (32).
- `SessionIsArchivedChangedAction` — uses `status` bitflag `1 << 6` (64).
- `SessionCustomizationUpdatedAction` — upserts by `id` into `customizations`.
- `SessionCustomizationRemovedAction` — removes by `id` from top-level and from
  `children` arrays of parent customizations.
- `SessionChatRemovedAction` — filters `state.chats` by `c.get("resource")` (was
  incorrectly using `"uri"`); also clears `default_chat` if it matches.

`SessionMcpServerStateChangedAction` deliberately no-ops — the TS reducer updates
matching customization entries, but without a fully-modeled `ServerToolsCustomization`
shape this is acceptable laxity, not a naming gap.

## `chat`

**State** — MOSTLY FIXED. `ChatState` has `resource`, `title`, `status`, `activity`,
`modified_at`, `turns`, `turns_next_cursor`, `steering_message`, `queued_messages`,
`input_requests`, `draft`, `meta`. Remaining minor laxities (not naming gaps):

- Missing `origin`, `interactivity`, `workingDirectory`
  (`types/channels-chat/state.ts:51-69`) — depth choice, not a naming gap.
- `Turn.state` defaults to `{"type": "running"}` but TS `Turn.state` is a string enum
  (`'complete'|'cancelled'|'error'`); in-progress turns are the separate `ActiveTurn`
  type. Low-impact since `Turn` objects only appear in completed state in practice.

**Actions** — FIXED. All 24 canonical type strings present with correct field shapes:

- `ChatToolCallConfirmedAction` — `approved: bool` (simplified from TS's
  `ChatToolCallApprovedAction | ChatToolCallDeniedAction` discriminated union;
  captures the essential field without the full subtype split).
- `ChatToolCallResultConfirmedAction` — `approved: bool`.
- `ChatPendingMessageSetAction` — `{kind, id, message}`.
- `ChatPendingMessageRemovedAction` — `{kind, id}`.
- `ChatQueuedMessagesReorderedAction` — `{order}` (was `{ids}`).
- `ChatInputAnswerChangedAction` — `{requestId, questionId, answer?}`.
- `ChatInputCompletedAction` — `{requestId, response, answers?}`.

**Reducer** — structural asymmetry only. `reducers/chat.py` handles 7 variants
(turns loaded, delta, tool-call state, errors, activity, truncation, draft).
17 of 24 variants still no-op — but canonical `types/channels-chat/` has **no
`reducer.ts`** at all. The Python `chat_reducer` is an additive local convention,
not a protocol gap.

## `terminal`

**State** — FIXED. `TerminalState` matches `types/channels-terminal/state.ts:79-110`
exactly.

**Actions** — FIXED. All 11 canonical variants with matching fields.

**Reducer** — FIXED. All previously-missing branches now implemented:

- `TerminalDataAction` — appends to in-progress `command` part's `output`, or to an
  `unclassified` tail, or starts a new `unclassified` part. No more `{"type": "data"}`
  invented part type.
- `TerminalCommandExecutedAction` — appends a new `command` content part
  `{type, commandId, commandLine, output:"", timestamp, isComplete:false}`.
- `TerminalCommandFinishedAction` — marks the matching command part `isComplete:true`,
  sets `exitCode` and `durationMs`.

## `changeset`

**State** — FIXED. `ChangesetState{status, error, files, operations}` matches
`types/channels-changeset/state.ts:96-108`.

**Actions** — FIXED.
- `ChangesetFileRemovedAction` — `file_id = Field(alias="fileId")` (was `id`).
- `ChangesetContentChangedAction` — `{files, operations?, error?}` (was `{id, edit}`).

**Reducer** — FIXED. All 7 variants handled:
- `ChangesetFileRemovedAction` — filters by `file_id` correctly.
- `ChangesetContentChangedAction` — replaces `files`, optionally replaces `operations`,
  sets or clears `error`.

## `annotations`

FIXED, fully. State, all 5 action variants, and `reducers/annotations.py` match
canonical TS.

## `otlp`

Notification method names and wire shapes are FIXED (see `common/` above).

No `reducers/otlp.py` exists, and that's **correct** — canonical
`types/channels-otlp/` has no `actions.ts`/`reducer.ts`; otlp is pure server→client
notification streaming.

`TelemetryCapabilities` (`types/channels-otlp/state.ts:35-68`) still has no Python
model; `InitializeResult.telemetry` remains `dict[str, Any]`. Low priority — not
surfaced in any test or real-world usage yet.

## `resource-watch`

FIXED, fully.

- `ResourceWatchState{root, recursive, excludes?, includes?}` — added to `state.py`
  and included in the `AnyChannelState` union.
- `createResourceWatch` command — `CreateResourceWatchParams/Result` in `commands.py`;
  registered in `COMMANDS`.
- `reducers/resource_watch.py` — trivial pass-through, matching canonical
  `types/channels-resource-watch/reducer.ts` (state never mutates after subscription;
  change events are ephemeral).
- `ResourceWatchChangedAction.changes` — `list[Any]` (was `dict[str, Any]`), matching
  TS's `ResourceChange[]`.

## What remains

The five-priority sequencing list from the prior revision is fully complete. What
remains is genuinely shallow laxity or depth choices rather than protocol gaps:

For cross-client evidence and rationale on each item below, see
[`GAPCONTEXT.md`](./GAPCONTEXT.md).

1. ~~**`TelemetryCapabilities`**~~ — **DONE** (2026-07-07). `TelemetryCapabilities`
   model added; `InitializeResult.telemetry` is now `TelemetryCapabilities | None`.
   6 tests in `tests/types/test_telemetry.py`. 220/220 passing.
   → [GAPCONTEXT.md § TelemetryCapabilities](./GAPCONTEXT.md#telemetrycapabilities-in-initializeresult)

2. **`ChatState` missing fields** — `origin`, `interactivity`, `workingDirectory`
   (`types/channels-chat/state.ts:51-69`). Depth choice today; needed for any UI
   that renders chat metadata.
   → [GAPCONTEXT.md § ChatState missing fields](./GAPCONTEXT.md#chatstate-missing-fields-origin-interactivity-workingdirectory)

3. ~~**`Turn.state` default**~~ — **DONE** (2026-07-07). `Turn.state` is now
   `Literal["complete", "cancelled", "error"]`; `ChatState.active_turn` corrected
   from `str | None` to `dict[str, Any] | None`; chat reducer rewritten to keep
   in-progress turns in `active_turn` and only move to `turns` on completion.
   7 tests in `tests/types/test_turn_state.py`. Suite: 231/231.
   → [GAPCONTEXT.md § Turn.state type](./GAPCONTEXT.md#turnstate-type)

4. ~~**`ChatToolCallConfirmedAction` subtype split**~~ — **DONE** (2026-07-07).
   `ChatToolCallConfirmedAction` now carries all fields from both canonical subtypes
   (`confirmed`, `reason`, `reason_message`, `user_suggestion`, `edited_tool_input`,
   `selected_option_id`). `ChatToolCallApprovedAction` and `ChatToolCallDeniedAction`
   added as typed convenience models for construction. 9 new tests. Suite: 240/240.
   → [GAPCONTEXT.md § ChatToolCallConfirmedAction](./GAPCONTEXT.md#chattoollcallconfirmedaction-subtype-split)

5. **`SessionMcpServerStateChangedAction` reducer** — deliberately no-ops; TS
   updates matching customization entries. Implement when MCP server tools are used.
   → [GAPCONTEXT.md § SessionMcpServerStateChangedAction](./GAPCONTEXT.md#sessionmcpserverstatechangedaction-reducer)

6. **Chat reducer coverage** — 17 of 24 variants still no-op. Fine, since canonical
   TS has no chat reducer at all.

7. ~~**`ping` method**~~ — **DONE** (2026-07-07). `AhpClient.ping()` implemented.
