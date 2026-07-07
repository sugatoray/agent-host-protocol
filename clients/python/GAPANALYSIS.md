# Gap Analysis — Python client vs. canonical protocol source

> Originally produced 2026-07-06, diffing `clients/python/src/ahp/{types,reducers}`
> against the canonical TypeScript source at repo-root `types/` (per-channel
> `channels-*/{state,actions,commands,notifications,reducer}.ts` + `common/*.ts`), with
> `schema/*.schema.json` as a secondary reference where the TS was ambiguous.
>
> **Re-verified 2026-07-07** after commit `8fceda9` ("Refactor tests and reducers for
> improved clarity and functionality") rewrote most of `ahp/types/` and all of
> `ahp/reducers/`. That commit closed the large majority of the gaps this document
> originally reported — error codes, common state primitives, and most state/action
> field names now match canonical TS. **This revision replaces the original
> "nearly everything disagrees" framing.** What's below is the current, narrower gap
> list. Full suite: 127/127 passing (`uv run pytest -v`, 2026-07-07).

## `common/`

**State primitives** — all FIXED: `Snapshot`, `ActionEnvelope`, `ClientCapabilities`,
`ProtocolVersion` (now `str`/SemVer) match canonical `types/common/*.ts` field-for-field.
Invented `HostCapabilities` removed.

**Commands** — most FIXED (`initialize`, `ping`, `reconnect`, `subscribe`,
`dispatchAction` fire-and-forget semantics, the `resource*` family, `authenticate`,
`fetchTurns` params, `completions`). Still open:

- `[createSession/createChat/createTerminal result shape]` TS: `result: null`
  (`types/common/messages.ts:154-159`). Python still invents
  `CreateSessionResult{session}`/`CreateChatResult{chat}`/`CreateTerminalResult{terminal}`
  (`clients/python/src/ahp/types/commands.py:162-163,193-194,230-231`).
- `[createChat params]` TS `CreateChatParams{channel, chat, initialMessage?, source?}`
  (`types/channels-chat/commands.ts:32-41`) — `chat` (client-chosen chat URI) is
  **required**. Python has `channel, title, config`
  (`clients/python/src/ahp/types/commands.py:187-190`) — missing `chat` entirely,
  invents `title`/`config`.
- `[createTerminal params]` TS `CreateTerminalParams{channel, claim: TerminalClaim,
  name?, cwd?, cols?, rows?}` (`types/channels-terminal/commands.ts:26-39`) — `claim`
  is **required**. Python has `channel, shell, cwd, cols, rows`
  (`clients/python/src/ahp/types/commands.py:222-227`) — still invents `shell`, still
  missing `claim`/`name`. `cols`/`rows` are now correct.
- `[fetchTurns result]` TS `FetchTurnsResult` is `{}` — turns arrive via the
  `chat/turnsLoaded` action, never in the command result
  (`types/channels-session/commands.ts:165`). Python still returns
  `{turns: list[Any], next_cursor}` (`clients/python/src/ahp/types/commands.py:212-214`).
- `[listSessions]` TS extends `PaginatedParams` (`limit?`, `cursor?`) and returns
  `{items: SessionSummary[], nextCursor?}` (`types/channels-root/commands.ts:56-67`).
  Python's `ListSessionsParams` has no pagination fields, and
  `ListSessionsResult{sessions: list[dict]}` uses key `sessions`, not `items`, no
  `nextCursor` (`clients/python/src/ahp/types/commands.py:174-179`).
- `[resolveSessionConfig]` now registered, but `ResolveSessionConfigParams` is
  missing `provider?`/`workingDirectory?` and makes `config` required where TS has it
  optional; `ResolveSessionConfigResult{config: dict}` is the wrong shape — TS returns
  `{schema: SessionConfigSchema, values: Record<string, unknown>}`
  (`types/channels-root/commands.ts:127-145` vs
  `clients/python/src/ahp/types/commands.py:278-284`).
- `[sessionConfigCompletions]` still entirely missing from `commands.py`/`COMMANDS`
  (`types/channels-root/commands.ts:192-212`).
- `[createResourceWatch]` still entirely missing (`types/channels-resource-watch/commands.ts:53-86`).
- `[invokeChangesetOperation]` unchanged from original report — `commands.py:292-299`
  has `{channel, operation, args}` / `{status}` vs TS `{channel, operationId, target?}`
  / `{message?, followUp?}` (`types/channels-changeset/commands.ts:74-84,98-103`).

**Notifications** — method names now mostly right, several field-shape gaps remain:

- `[auth/required]` now has `resource` (was invented `scheme`), but still missing
  required `channel` and dropped `reason?`
  (`clients/python/src/ahp/types/notifications.py:52-58` vs
  `types/common/notifications.ts:55-62`).
- `[root/sessionRemoved]` field renamed to `session` correctly, but still missing
  required `channel` (`notifications.py:39-42` vs
  `types/channels-root/notifications.ts:71-76`).
- `[root/sessionSummaryChanged]` newly added but missing required `session: URI`
  (`notifications.py:45-49` vs `types/channels-root/notifications.ts:132-144`).
- `[root/progress]` newly added under the wrong method (`"$/progress"` instead of
  `root/progress`) with the wrong fields (`{token, value}` instead of
  `{channel, progressToken, progress, total?, message?}`)
  (`notifications.py:61-65,92` vs `types/channels-root/notifications.ts:180`).
- `[otlp/exportLogs, otlp/exportTraces, otlp/exportMetrics]` method names now correct
  (invented `otlp/log` removed), but the params are flattened
  (`{resource_logs}`/`{resource_spans}`/`{resource_metrics}` directly on params)
  instead of TS's `{channel, payload: {...}}` wrapper
  (`notifications.py:68-83` vs `types/channels-otlp/notifications.ts:45-130`).

**Errors** — FIXED. `AhpErrorCode` now matches `types/common/errors.ts:41-98` exactly,
including the two previously-missing `-32010`/`-32011` codes
(`clients/python/src/ahp/types/errors.py:26-39`). `JsonRpcErrorCode` still matches (no
discrepancy, unchanged from original report).

## `root`

State, actions, and reducer are all FIXED: `RootState` carries `agents`,
`active_sessions`, `terminals`, `config`, `meta`; all 4 canonical `RootAction`
variants present with correct fields; `reducers/root.py` handles all 4 including the
config merge/replace branch. Invented `RootSessionAdded/RemovedAction` removed.
Remaining gaps are the shared `listSessions`/`resolveSessionConfig`/
`sessionConfigCompletions` command issues and `sessionRemoved`/`sessionSummaryChanged`/
`progress` notification issues listed under `common/` above.

## `session`

**State** — FIXED. `SessionState` now carries every canonical field (`provider`,
`status`, `lifecycle`, `active_clients`, `chats`, `config`, `customizations`,
`changesets`, `input_needed`, etc., `clients/python/src/ahp/types/state.py:51-80`).
Nested shapes are still typed `Any`/`dict` rather than fully modeled — a depth choice,
not a naming gap.

**Actions** — FIXED. All 22+ canonical variants present with matching field names
(`clients/python/src/ahp/types/actions.py:64-210`); invented
`SessionTerminalAddedAction`/`SessionDisposedAction` removed.

**Reducer** — PARTIALLY FIXED. `reducers/session.py:29-105` now handles 18 of 22
variants (up from 3). Still no-op on `SessionIsReadChangedAction`,
`SessionIsArchivedChangedAction`, `SessionCustomizationUpdatedAction`,
`SessionCustomizationRemovedAction`. `SessionMcpServerStateChangedAction` is handled
but deliberately no-ops (`session.py:90-91`) where TS updates the matching
customization entry (`types/channels-session/reducer.ts:278-329`).

**New defect found this pass** (not in the original report):
`reducers/session.py:49` filters `state.chats` by `c.get("uri")`, but `ChatSummary`'s
identity field is `resource` (`types/channels-chat/state.ts:118-121`) — so
`session/chatRemoved` silently never removes the matching entry. Fix alongside the
reducer completion work above.

**Commands** — `createSession` params FIXED; `fetchTurns` params FIXED (result still
wrong, see `common/`); `completions` FIXED.

## `chat`

**State** — PARTIALLY FIXED. `ChatState` (`clients/python/src/ahp/types/state.py:105-121`)
now has `resource`, `title`, `status`, `activity`, `modified_at`, `turns`,
`turns_next_cursor`, `steering_message`, `queued_messages`, `input_requests`, `draft`,
`meta` — a full overhaul from the old invented shape. Still missing `origin`,
`interactivity`, `workingDirectory` (`types/channels-chat/state.ts:51-69`). `active_turn`
is typed as a bare `str | None` where TS's `activeTurn` is a full `ActiveTurn` object
(`state.py:116` vs `types/channels-chat/state.ts:84,529-542`).

`Turn.state` (`state.py:88-102`) defaults to `{"type": "running"}`, but TS `Turn.state`
is a plain string enum (`'complete'|'cancelled'|'error'`) with no `"running"` value —
in-progress turns are a separate `ActiveTurn` type, not a `Turn` state
(`types/channels-chat/state.ts:477-481,519`).

**Actions** — mostly FIXED. All 24 canonical type strings now present
(`clients/python/src/ahp/types/actions.py:217-408`), replacing the 5 invented
variants. Remaining field-level gaps:

- `ChatToolCallConfirmedAction{outcome}` (`actions.py:269-274`) should be the
  discriminated union `ChatToolCallApprovedAction{approved:true, confirmed, ...} |
  ChatToolCallDeniedAction{approved:false, reason, ...}`
  (`types/channels-chat/actions.ts:226-271`).
- `ChatToolCallResultConfirmedAction{outcome}` (`actions.py:284-288`) should be
  `approved: bool` (`types/channels-chat/actions.ts:307-311`).
- `ChatPendingMessageSetAction` (`actions.py:343-345`) missing required `kind`/`id`
  (`types/channels-chat/actions.ts:537-545`).
- `ChatPendingMessageRemovedAction` (`actions.py:348-350`) missing required `kind`
  (`types/channels-chat/actions.ts:558-564`).
- `ChatQueuedMessagesReorderedAction{ids}` (`actions.py:353-355`) — TS field is
  `order`, not `ids` (`types/channels-chat/actions.ts:579-583`).
- `ChatInputAnswerChangedAction` (`actions.py:368-371`) missing required `questionId`
  (`types/channels-chat/actions.ts:637-645`).
- `ChatInputCompletedAction` (`actions.py:374-376`) missing required `response` and
  optional `answers` (`types/channels-chat/actions.ts:657-665`).

**Reducer** — PARTIALLY FIXED. `reducers/chat.py:25-81` now handles 7 real matching
action types (up from 5 invented). 17 of 24 variants still no-op (tool-call
lifecycle, usage, reasoning, pending messages, draft, input requests). No canonical
`types/channels-chat/reducer.ts` exists — chat has no reducer in TS either, so
`chat_reducer`'s existence remains a structural asymmetry to flag, not a bug.

**Commands** — `createChat` still wrong (see `common/`); `disposeChat` FIXED.

## `terminal`

**State** — FIXED. `TerminalState` (`clients/python/src/ahp/types/state.py:129-143`)
now matches `types/channels-terminal/state.ts:79-110` exactly: `title`, `cwd`, `cols`,
`rows`, `content`, `exit_code`, `claim`, `supports_command_detection`.

**Actions** — FIXED. All 11 canonical variants present with matching fields
(`actions.py:415-492`); invented `terminal/output` removed.

**Reducer** — PARTIALLY FIXED. `reducers/terminal.py:17-39` now handles 6 of 11
variants (up from 2): `TerminalData`, `TerminalExited`, `TerminalTitleChanged`,
`TerminalCwdChanged`, `TerminalResized`, `TerminalCleared`. Still missing
`TerminalClaimedAction`, `TerminalCommandDetectionAvailableAction`,
`TerminalCommandExecutedAction`, `TerminalCommandFinishedAction`. Also,
`terminal_data` handling (`terminal.py:19-22`) appends a plain `{"type": "data",
"data": ...}` dict rather than conforming to the typed `TerminalContentPart` union
(`types/channels-terminal/reducer.ts:17-28`).

**Commands** — still wrong (`CreateTerminalParams`, see `common/`).

## `changeset`

**State** — FIXED. `ChangesetState{status, error, files, operations}`
(`clients/python/src/ahp/types/state.py:151-157`) matches
`types/channels-changeset/state.ts:96-108` exactly.

**Actions** — mostly FIXED. All 7 canonical type strings present
(`actions.py:499-546`); `ChangesetOperationStatusChangedAction` now correctly targets
one operation by `operation_id`. Still wrong:

- `ChangesetFileRemovedAction{id}` (`actions.py:509-511`) — TS field is `fileId`
  (`types/channels-changeset/actions.ts:54-58`).
- `ChangesetContentChangedAction{id, edit}` (`actions.py:514-517`) — unrelated shape;
  TS's variant is a full-replacement `{files, operations?, error?}`
  (`types/channels-changeset/actions.ts:72-80`), not a per-file `id`/`edit` event.

**Reducer** — PARTIALLY FIXED. `reducers/changeset.py:17-47` now handles 6 of 7
variants (up from 1); missing the `ChangesetContentChangedAction` branch entirely,
consistent with its still-wrong action shape.

**Commands** — still wrong (`invokeChangesetOperation`, see `common/`).

## `annotations`

FIXED, fully. `AnnotationsState`/`Annotation` field sets match
`types/channels-annotations/state.ts:45-133`
(`clients/python/src/ahp/types/state.py:165-181`); all 5 canonical action variants
present with matching field names (`actions.py:553-590`); `reducers/annotations.py:17-62`
handles all 5 with correct upsert/removal semantics. Invented `annotations/added`
removed. (`turn_id`/`resource` are optional in Python vs. required in TS — laxity, not
a naming gap.)

## `otlp`

Notification method names are now correct (`otlp/exportLogs`/`otlp/exportTraces`/
`otlp/exportMetrics`, invented `otlp/log` removed) but the wire shape is still wrong —
see the `common/` notifications section (missing `channel`, flattened instead of
wrapped in `payload`). `TelemetryCapabilities` (`types/channels-otlp/state.ts:35-68`)
still has no Python model; `InitializeResult.telemetry` remains an untyped
`dict[str, Any]` (`clients/python/src/ahp/types/commands.py:67`).

No `reducers/otlp.py` exists, and that's **correct, not a gap** — canonical
`types/channels-otlp/` has no `actions.ts`/`reducer.ts`; otlp is pure server→client
notification streaming with no dispatchable actions. (The original 2026-07-06 report
mischaracterized this as a gap.)

## `resource-watch`

Still almost entirely missing, one partial addition:

- `ResourceWatchChangedAction{type:'resourceWatch/changed', changes}` now exists and
  is included in the `StateAction` union (`clients/python/src/ahp/types/actions.py:597-605,695`),
  matching `types/channels-resource-watch/actions.ts:25-29`.
- `ResourceWatchState{root, recursive, excludes?, includes?}`
  (`types/channels-resource-watch/state.ts:23-47`) — still no Python model.
- `createResourceWatch` command — still missing from `commands.py`/`COMMANDS`
  (`types/channels-resource-watch/commands.ts:53-86`).
- `reducers/resource_watch.py` — still missing. Canonical
  `types/channels-resource-watch/reducer.ts` is a trivial pass-through (state never
  mutates after subscription), so this is a cheap, mechanical addition once
  `ResourceWatchState` exists.

## What this means for next-session sequencing

The systemic, "nearly everything disagrees" gap from 2026-07-06 is closed. What
remains is narrower and mostly mechanical — suggested order, cheapest/highest-value
first:

1. **Notification field shapes** — `auth/required`, `root/sessionRemoved`,
   `root/sessionSummaryChanged`, `root/progress` (wrong method name), `otlp/export*`
   (unwrap into `payload`). All in `notifications.py`, no reducer changes needed.
2. **`create*` command shapes** — `createSession`/`createChat`/`createTerminal`
   results should be `null`-equivalent (empty models, matching the existing
   `dispose*` pattern); `createChat`/`createTerminal` params need their missing
   required fields (`chat`, `claim`); `fetchTurns`/`listSessions`/
   `resolveSessionConfig` result shapes need correcting; `sessionConfigCompletions`/
   `createResourceWatch` need adding; `invokeChangesetOperation` needs a full
   params/result rewrite.
3. **Reducer completion** — finish the remaining no-op branches in `session.py`,
   `chat.py`, `terminal.py`, `changeset.py` reducers (all partially done, listed
   above per channel) — and fix the `session.py:49` `chatRemoved` key-mismatch bug
   found this pass.
4. **Action field-shape fixes** — the `chat/*` and `changeset/*` action field
   mismatches listed above (mostly renames/missing-required-fields, not structural).
5. **`resource-watch`** — add `ResourceWatchState`, `createResourceWatch`, and the
   trivial `reducers/resource_watch.py` pass-through.

Each step via Red/Green TDD as usual: write the failing test against the corrected
shape first, confirm red, then fix.
