# Gap Analysis — Python client vs. canonical protocol source

> Produced 2026-07-06. Diffs `clients/python/src/ahp/{types,reducers}` against the
> canonical TypeScript source at repo-root `types/` (per-channel `channels-*/{state,
> actions,commands,notifications,reducer}.ts` + `common/*.ts`), with `schema/*.schema.json`
> as a secondary reference where the TS was ambiguous.

## Why this exists

The Python client was hand-written from spec prose and a third-party AHP-adjacent VS
Code plugin's ported TS interfaces (see `HANDOFF.md`'s "Access limitations" and
`SPEC.md` §7a) — never diffed field-by-field against `types/*.ts`. `HANDOFF.md`
already flagged this as a hypothesis ("treat every field name as a hypothesis to
verify"). This document is that verification pass. Conclusion up front: **the gap is
not a handful of field-name typos — nearly every state field, action variant, command
shape, notification, and error code in the Python client currently disagrees with the
canonical source, and two whole channel families (`otlp`, `resource-watch`) are absent.**
Treat this as a full reconciliation task, not spot fixes. No code has been changed as
part of producing this document — see `HANDOFF.md` / `SPEC.md` for how to sequence the
actual fix work.

## `common/`

**State primitives**
- `[Snapshot fields]` TS `Snapshot` has `resource: URI`, `state`, `fromSeq: number`
  (`types/common/state.ts:338-345`). Python `Snapshot` has `channel`,
  `server_seq`/`serverSeq`, `state` (`clients/python/src/ahp/types/common.py:108-118`) —
  both field names (`resource`→`channel`, `fromSeq`→`server_seq`) are genuine renames,
  not case variants.
- `[ActionEnvelope]` TS has `channel`, `action: StateAction`, `serverSeq: number`
  (required), `origin: ActionOrigin | undefined`, `rejectionReason?: string`
  (`types/common/actions.ts:213-220`). Python's `ActionEnvelope` is missing
  `rejectionReason` entirely and makes `server_seq` optional where TS requires it
  (`clients/python/src/ahp/types/common.py:125-136`).
- `[ClientCapabilities]` TS only has `mcpApps?: Record<string, never>`
  (`types/common/commands.ts:155-170`). Python invents `resources: bool` and
  `authentication: bool`; `mcpApps` is absent
  (`clients/python/src/ahp/types/common.py:143-150`).
- `[HostCapabilities]` Python defines a `HostCapabilities` model (`channels: list[str]`,
  `changesets: bool`, `completions: bool`, `clients/python/src/ahp/types/common.py:153-161`)
  that has **no TS counterpart anywhere in the repo** (confirmed via repo-wide grep) —
  `initialize`'s real result carries no such field.
- `[ProtocolVersion type]` TS negotiates SemVer strings, e.g.
  `InitializeParams.protocolVersions: string[]` (`types/common/commands.ts:125`).
  Python's `ProtocolVersion = Literal[1]` is an integer literal, not a SemVer string
  (`clients/python/src/ahp/types/common.py:163-165`).

**Commands (`common/commands.ts` vs `commands.py`)**
- `[initialize]` TS `InitializeParams` has `channel:'ahp-root://'`,
  `protocolVersions: string[]`, `clientId`, `initialSubscriptions?`, `locale?`,
  `capabilities?` (`types/common/commands.ts:114-144`). Python `InitializeParams` has
  `protocol_version` (singular), invented `client_name`/`client_version` fields (not in
  TS at all), and no `initialSubscriptions`/`locale`
  (`clients/python/src/ahp/types/commands.py:48-52`).
- `[InitializeResult]` TS returns `protocolVersion`, `serverSeq`,
  `snapshots: Snapshot[]`, `defaultDirectory?`, `completionTriggerCharacters?`,
  `telemetry?` (`types/common/commands.ts:181-211`). Python returns `protocol_version`,
  invented `client_id` (not returned by real `initialize`), invented `capabilities`,
  and a singular `root_snapshot` instead of the `snapshots` array
  (`clients/python/src/ahp/types/commands.py:55-59`).
- `[ping]` TS `PingParams extends BaseParams { channel: 'ahp-root://' }`
  (`types/common/commands.ts:229-231`). Python `PingParams` has no fields at all
  (`clients/python/src/ahp/types/commands.py:67-68`).
- `[reconnect params]` TS `ReconnectParams` has `clientId`,
  `lastSeenServerSeq: number` (single number), `subscriptions: URI[]`
  (`types/common/commands.ts:256-264`). Python `ReconnectParams` has
  `last_seen_server_seq: dict[URI, ServerSeq]` (per-channel map, not a single number)
  and is missing `subscriptions` entirely
  (`clients/python/src/ahp/types/commands.py:75-82`).
- `[reconnect result]` TS is a discriminated union
  `ReconnectReplayResult{type:'replay', actions: ActionEnvelope[], missing: URI[]} |
  ReconnectSnapshotResult{type:'snapshot', snapshots: Snapshot[]}`
  (`types/common/commands.ts:271-296`). Python's `ReconnectResult` has unrelated fields
  `replayed: list[URI]` and `resnapshotted: list[Snapshot]`, no `type` discriminant, no
  `actions`, no `missing` (`clients/python/src/ahp/types/commands.py:84-89`).
- `[subscribe]` TS `SubscribeParams` (via `BaseParams`) has `channel`,
  `delivery?: SubscriptionDeliveryOptions`, `view?: SubscribeView`
  (`types/common/commands.ts:315-331`). Python `SubscribeParams` has only `channel`
  (`clients/python/src/ahp/types/commands.py:97-98`) — missing `delivery`/`view`.
- `[dispatchAction result]` TS models `dispatchAction` as a fire-and-forget
  notification with **no result type** (`types/common/commands.ts:395-420`). Python
  invents `DispatchActionResult{server_seq}`
  (`clients/python/src/ahp/types/commands.py:126-128`).
- `[resource* family]` TS defines
  `resourceRead/Write/List/Copy/Delete/Request/Move/Resolve/Mkdir` (10 commands,
  `types/common/commands.ts:422-952`, e.g.
  `ResourceReadResult{data, encoding, contentType?}`). Python only implements
  `resourceRead/Write/List` plus an invented `resourceStat` (not in TS; TS's equivalent
  is `resourceResolve`), and the modeled shapes don't match, e.g. Python
  `ResourceReadResult{content_ref: ContentRef, data}` vs TS
  `ResourceReadResult{data, encoding: ContentEncoding, contentType?}`
  (`clients/python/src/ahp/types/commands.py:267-301` vs
  `types/common/commands.ts:470-492`). Missing entirely: `resourceCopy`,
  `resourceDelete`, `resourceRequest`, `resourceMove`, `resourceResolve`,
  `resourceMkdir`.
- `[authenticate]` TS `AuthenticateParams{channel, resource: string, token: string}`
  (`types/common/commands.ts:984-993`). Python
  `AuthenticateParams{scheme: str, credentials: dict}`
  (`clients/python/src/ahp/types/commands.py:223-225`) — unrelated field set.
- `[createSession/createChat/createTerminal — result shape]` TS's real result for
  these is `null`/untyped (see `types/common/messages.ts:156-157` for
  `createChat`/`disposeChat`: `result: null`; `channels-session/commands.ts`
  `CreateSessionParams` docblock example also shows `"result": null`). Python invents
  `CreateSessionResult{session_uri, snapshot}`, `CreateChatResult{chat_uri, snapshot}`,
  `CreateTerminalResult{terminal_uri, snapshot}`
  (`clients/python/src/ahp/types/commands.py:140-143,170-173,205-208`) with no TS
  counterpart.
- `[createSession params]` TS `CreateSessionParams` (channels-session) has `channel`
  (client-chosen session URI), `provider?`, `workingDirectory?`, `fork?`, `config?`,
  `activeClient?`, `progressToken?` (`types/channels-session/commands.ts:64-103`).
  Python `CreateSessionParams{agent: AgentInfo|None, title: str|None}` shares none of
  these field names (`clients/python/src/ahp/types/commands.py:135-138`).
- `[listSessions]` TS `ListSessionsParams` (channels-root) extends
  `BaseParams, PaginatedParams` (`channel`, `limit?`, `cursor?`); `ListSessionsResult`
  is `{items: SessionSummary[], nextCursor?}` (`types/channels-root/commands.ts:56-67`).
  Python `ListSessionsParams` has no fields at all, and
  `ListSessionsResult{session_uris: list[URI]}` uses a different shape entirely
  (`clients/python/src/ahp/types/commands.py:153-158`).
- `[Missing commands entirely]` TS also defines `resolveSessionConfig`/
  `sessionConfigCompletions` (`types/channels-root/commands.ts:127-213`) and
  `createResourceWatch` (`types/channels-resource-watch/commands.ts:53-86`) — none
  exist in Python's `COMMANDS` registry
  (`clients/python/src/ahp/types/commands.py:308-333`).

**Notifications (`common/notifications.ts` vs `notifications.py`)**
- `[auth/required]` TS `AuthRequiredParams{channel, resource: string, reason?:
  AuthRequiredReason}` (`types/common/notifications.ts:55-62`). Python
  `AuthRequiredNotification{scheme: str, reason: str|None}`
  (`clients/python/src/ahp/types/notifications.py:46-54`) — invents `scheme`, drops
  required `resource` and `channel`.
- `[root/sessionAdded]` TS `SessionAddedParams{channel, summary: SessionSummary}`
  (`types/channels-root/notifications.ts:41-46`). Python
  `SessionAddedNotification{session_uri}`
  (`clients/python/src/ahp/types/notifications.py:32-38`) — carries a bare URI instead
  of the full `SessionSummary`.
- `[root/sessionRemoved]` TS field is `session: URI`
  (`types/channels-root/notifications.ts:71-76`). Python field is
  `session_uri`/`sessionUri` (`clients/python/src/ahp/types/notifications.py:40-44`) —
  name mismatch, not just casing.
- `[Missing notifications]` TS also defines `root/sessionSummaryChanged` and
  `root/progress` (`types/channels-root/notifications.ts:78-224`) — absent from
  Python's `NOTIFICATIONS` registry
  (`clients/python/src/ahp/types/notifications.py:66-72`).
- `[otlp/log invented]` Python registers `"otlp/log": OtlpLogNotification`
  (`clients/python/src/ahp/types/notifications.py:56-71`); the real methods are
  `otlp/exportLogs`, `otlp/exportTraces`, `otlp/exportMetrics` carrying an OTLP/JSON
  `payload` (`types/channels-otlp/notifications.ts:45-130`) — `otlp/log` does not
  exist in TS.

**Errors (`common/errors.ts` vs `errors.py`)**
- `[Every AhpErrorCode value is wrong]` TS `AhpErrorCodes`
  (`types/common/errors.ts:41-98`): `SessionNotFound=-32001, ProviderNotFound=-32002,
  SessionAlreadyExists=-32003, TurnInProgress=-32004,
  UnsupportedProtocolVersion=-32005, ContentNotFound=-32006, AuthRequired=-32007,
  NotFound=-32008, PermissionDenied=-32009, AlreadyExists=-32010, Conflict=-32011`.
  Python `AhpErrorCode` (`clients/python/src/ahp/types/errors.py:26-44`):
  `PROTOCOL_VERSION_MISMATCH=-32000, NOT_INITIALIZED=-32001, UNKNOWN_CHANNEL=-32002,
  SUBSCRIPTION_REQUIRED=-32003, STALE_CLIENT_SEQ=-32004, RESOURCE_NOT_FOUND=-32005,
  AUTHENTICATION_REQUIRED=-32006, AUTHENTICATION_FAILED=-32007,
  SESSION_DISPOSED=-32008, OPERATION_NOT_SUPPORTED=-32009`. Every code from -32001
  through -32009 maps to a **different meaning** between the two (e.g. `-32001` =
  `SessionNotFound` in TS vs `NOT_INITIALIZED` in Python); TS's `-32010 AlreadyExists`
  and `-32011 Conflict` are missing from Python entirely; Python's `-32000
  PROTOCOL_VERSION_MISMATCH` doesn't exist in TS's range at all (TS starts its range
  at -32001).
- `[JsonRpcErrorCode]` matches exactly (`types/common/errors.ts:20-31` vs
  `clients/python/src/ahp/types/errors.py:16-23`) — no discrepancy.

## `root`

**State (`channels-root/state.ts` vs `state.py`)**
- `[RootState fields]` TS: `agents`, `activeSessions?`, `terminals?`,
  `config?: RootConfigState`, `_meta?` (`types/channels-root/state.ts:33-48`). Python
  `RootState`: `agents`, `active_sessions`, `session_uris`
  (`clients/python/src/ahp/types/state.py:33-42`) — `session_uris` doesn't exist on TS
  `RootState` (session lists are fetched via `listSessions`, not carried in state);
  `terminals`, `config`, `_meta` are missing.
- `[AgentInfo fields]` TS: `provider`, `displayName`, `description`,
  `models: SessionModelInfo[]`, `protectedResources?`, `customizations?`,
  `capabilities?` (`types/channels-root/state.ts:53-94`). Python `AgentInfo`:
  `provider`, `id`, `display_name` (`clients/python/src/ahp/types/state.py:23-30`) —
  `id` is invented (not in TS), `description`/`models`/`protectedResources`/
  `customizations`/`capabilities` are missing.

**Actions (`channels-root/actions.ts` vs `actions.py`)**
- `[Missing variants]` TS `RootAction` union has 4 variants:
  `root/agentsChanged`, `root/activeSessionsChanged`, `root/terminalsChanged`,
  `root/configChanged` (`types/channels-root/actions.ts:19-68`, aggregated in
  `types/common/actions.ts:228-231`). Python only implements `root/agentsChanged`
  correctly; `root/activeSessionsChanged`, `root/terminalsChanged`, `root/configChanged`
  are entirely missing (`clients/python/src/ahp/types/actions.py:33-51`).
- `[Invented variants]` Python's `RootSessionAddedAction`/`RootSessionRemovedAction`
  (`type: "root/sessionAdded"/"root/sessionRemoved"`,
  `clients/python/src/ahp/types/actions.py:38-46`) don't exist as *actions* in TS at
  all — `root/sessionAdded`/`root/sessionRemoved` are **notifications** in TS
  (`types/channels-root/notifications.ts:41,71`), not members of `StateAction`.

**Commands** — TS `listSessions`/`resolveSessionConfig`/`sessionConfigCompletions`
(`types/channels-root/commands.ts`) vs Python: see common section above (`listSessions`
shape wrong; other two missing).

**Notifications** — see common section (`SessionAddedNotification`/
`SessionRemovedNotification` field mismatches; `sessionSummaryChanged`/`progress`
missing).

**Reducer** — TS `rootReducer` handles all 4 `RootAction` variants including
config merge/replace logic (`types/channels-root/reducer.ts:15-42`). Python's
`root_reducer` handles 3 invented/mismatched variants (`RootAgentsChangedAction`,
`RootSessionAddedAction`, `RootSessionRemovedAction`) and silently no-ops on real TS
actions `root/activeSessionsChanged`, `root/terminalsChanged`, `root/configChanged`
(`clients/python/src/ahp/reducers/root.py:20-49`).

## `session`

**State** — TS `SessionState` (via `SessionMetadata`) has `provider`, `title`,
`status: SessionStatus`, `activity?`, `project?`, `workingDirectory?`, `annotations?`,
`lifecycle`, `creationError?`, `serverTools?`, `activeClients`, `chats:
ChatSummary[]`, `defaultChat?`, `config?`, `customizations?`, `changesets?`,
`inputNeeded?`, `_meta?` (`types/channels-session/state.ts:74-197`). Python
`SessionState` has `uri`, `title`, `agent`, `chat_uris`, `terminal_uris`, `disposed`
(`clients/python/src/ahp/types/state.py:71-79`) — `uri`, `agent`, `chat_uris`,
`terminal_uris`, `disposed` all have no TS `SessionState` counterpart (chats are
`ChatSummary[]`, not URI strings; terminals aren't tracked on session state at all;
there is no `disposed` flag — lifecycle uses `SessionLifecycle`); every real field
(`provider`, `status`, `lifecycle`, `activeClients`, `chats`, `config`,
`customizations`, etc.) is missing.

**Actions** — TS `SessionAction` union has 22 variants (`SessionReady`,
`SessionCreationFailed`, `SessionChatAdded/Removed/Updated`,
`SessionDefaultChatChanged`, `SessionTitleChanged`, `SessionIsReadChanged`,
`SessionIsArchivedChanged`, `SessionActivityChanged`, `SessionChangesetsChanged`,
`SessionConfigChanged`, `SessionMetaChanged`, `SessionServerToolsChanged`,
`SessionActiveClientSet/Removed`, `SessionInputNeededSet/Removed`,
`SessionCustomizationsChanged/Toggled/Updated/Removed`,
`SessionMcpServerStateChanged`; `types/channels-session/actions.ts:28-447`). Python
only has `SessionTitleChangedAction` (matches), plus invented
`SessionChatAddedAction{chat_uri}` (TS's real `session/chatAdded` carries `summary:
ChatSummary`, not a URI, `types/channels-session/actions.ts:54-58`), invented
`SessionTerminalAddedAction` (no TS equivalent — terminals aren't session-scoped
actions), and invented `SessionDisposedAction` (no TS equivalent)
(`clients/python/src/ahp/types/actions.py:58-85`). All 21 other real TS variants are
missing.

**Commands** — TS `channels-session/commands.ts` defines `createSession` (real field
set, see common section), `disposeSession`, `fetchTurns`, `completions` (with
`CompletionItemKind`, `CompletionItem`). Python's `commands.py` has mismatched
`CreateSessionParams`/`Result` (see common section), a `FetchTurnsParams{chat_uri,
before_turn_id, limit}` vs TS `FetchTurnsParams{channel, cursor?}`
(`types/channels-session/commands.ts:149-160` vs
`clients/python/src/ahp/types/commands.py:183-186`) — Python's
`before_turn_id`/`limit` don't exist in TS, and TS's cursor-based paging via
`channel`+`cursor` is absent — and `CompletionsParams` in Python (`session_uri,
prefix, kind`) doesn't match TS's `{kind, channel, text, offset}`
(`types/channels-session/commands.ts:223-238` vs
`clients/python/src/ahp/types/commands.py:237-240`).

**Reducer** — TS `sessionReducer` handles all 22 `SessionAction` variants including
bitset status logic (`types/channels-session/reducer.ts:52-335`). Python's
`session_reducer` handles only its 3 invented/mismatched actions and no-ops on every
real TS session action (`clients/python/src/ahp/reducers/session.py:15-37`).

## `chat`

**State** — TS `ChatState` has `resource`, `title`, `status`, `activity?`,
`modifiedAt`, `origin?`, `interactivity?`, `workingDirectory?`, `turns: Turn[]`,
`turnsNextCursor?`, `activeTurn?`, `steeringMessage?`, `queuedMessages?`,
`inputRequests?`, `draft?`, `_meta?` (`types/channels-chat/state.ts:38-109`). Python
`ChatState` has `uri`, `session_uri`, `turns`, `pending_confirmation`
(`clients/python/src/ahp/types/state.py:82-88`) — `session_uri` and
`pending_confirmation` have no TS `ChatState` counterpart at all; every real field is
missing. Python's `Turn` model (`id, role, status, text, content_refs, error`,
`clients/python/src/ahp/types/state.py:60-68`) also bears no resemblance to TS
`Turn{id, message: Message, responseParts: ResponsePart[], usage, state: TurnState,
error?}` (`types/channels-chat/state.ts:504-522`).

**Actions** — TS `ChatAction` union has 24 variants (`chat/turnStarted, chat/delta,
chat/responsePart, chat/toolCallStart, chat/toolCallDelta, chat/toolCallReady,
chat/toolCallConfirmed, chat/toolCallComplete, chat/toolCallResultConfirmed,
chat/toolCallContentChanged, chat/turnComplete, chat/turnCancelled, chat/error,
chat/activityChanged, chat/usage, chat/reasoning, chat/truncated, chat/turnsLoaded,
chat/pendingMessageSet, chat/pendingMessageRemoved, chat/queuedMessagesReordered,
chat/draftChanged, chat/inputRequested, chat/inputAnswerChanged,
chat/inputCompleted`, `types/channels-chat/actions.ts:668-694`). Python has 5
invented variants with no TS match: `chat/turnStarted` with fields `turn_id, role`
(real TS `chat/turnStarted` carries `turnId, message: Message, queuedMessageId?,
_meta?`, `types/channels-chat/actions.ts:64-82`); `chat/turnDelta` (doesn't exist —
TS's streaming action is `chat/delta` keyed by `partId`, not `turnId`+`textDelta`);
`chat/turnCompleted` with a `turn: Turn` payload (doesn't exist — TS's real
`chat/turnComplete` carries only `turnId`); `chat/turnContentRefAdded` (no TS
equivalent); `chat/confirmationRequested` (no TS equivalent)
(`clients/python/src/ahp/types/actions.py:92-131`). All 24 real variants are missing.

**Commands** — TS `createChat`/`disposeChat` (`types/channels-chat/commands.ts:32-54`)
are absent from Python's registry (Python's `createChat`/`fetchTurns` are
session-family entries with mismatched shapes noted above); no Python model exists for
`ChatForkSource`/`CompletionItem`.

**Reducer** — No `reducer.ts` file exists for chat under `types/channels-chat/`
(confirmed — chat has no canonical reducer, unlike root/session/terminal/
annotations/changeset which do). Python nonetheless ships `chat_reducer`
(`clients/python/src/ahp/reducers/chat.py:18-80`) handling only its 5 invented
actions — this can't be compared against a canonical TS chat reducer since none
exists; a structural asymmetry to flag rather than a field-level diff.

## `terminal`

**State** — TS `TerminalState` has `title`, `cwd?`, `cols?`, `rows?`, `content:
TerminalContentPart[]`, `exitCode?`, `claim: TerminalClaim`,
`supportsCommandDetection?` (`types/channels-terminal/state.ts:79-110`). Python
`TerminalState` has `uri`, `session_uri`, `status: TerminalStatus`, `exit_code`,
`buffer: str` (`clients/python/src/ahp/types/state.py:96-103`) — `uri`, `session_uri`,
`status`, `buffer` have no TS counterpart (TS has no top-level `status` enum field,
and output is a typed `content` array, not a flat `buffer` string); `title`, `cwd`,
`cols`, `rows`, `content`, `claim`, `supportsCommandDetection` are all missing.

**Actions** — TS `TerminalAction` has 11 variants: `terminal/data, terminal/input,
terminal/resized, terminal/claimed, terminal/titleChanged, terminal/cwdChanged,
terminal/exited, terminal/cleared, terminal/commandDetectionAvailable,
terminal/commandExecuted, terminal/commandFinished`
(`types/channels-terminal/actions.ts`). Python has
`TerminalOutputAction{type:"terminal/output", data}` — this type string does not exist
in TS at all (the real streaming action is `terminal/data`,
`types/channels-terminal/actions.ts:28-32`) — and `TerminalExitedAction{exit_code:
int}` where TS's `exitCode` is optional (`types/channels-terminal/actions.ts:121-125`
vs `clients/python/src/ahp/types/actions.py:139-152`). Missing entirely:
`terminal/input`, `terminal/resized`, `terminal/claimed`, `terminal/titleChanged`,
`terminal/cwdChanged`, `terminal/cleared`, `terminal/commandDetectionAvailable`,
`terminal/commandExecuted`, `terminal/commandFinished`.

**Commands** — TS `CreateTerminalParams{channel, claim: TerminalClaim, name?, cwd?,
cols?, rows?}` (`types/channels-terminal/commands.ts:26-39`). Python
`CreateTerminalParams{session_uri, shell, cwd}`
(`clients/python/src/ahp/types/commands.py:199-202`) — `session_uri`/`shell` are
invented, `claim`/`name`/`cols`/`rows` are missing.

**Reducer** — Python `terminal_reducer` handles only its 2 invented/mismatched
actions and no-ops on all 11 real TS terminal actions
(`clients/python/src/ahp/reducers/terminal.py:14-28`).

## `changeset`

**State** — TS `ChangesetState{status: ChangesetStatus, error?, files:
ChangesetFile[], operations?: ChangesetOperation[]}`
(`types/channels-changeset/state.ts:96-108`). Python `ChangesetState{uri, session_uri,
operation_status}` (`clients/python/src/ahp/types/state.py:112-121`) — `uri`/
`session_uri` don't exist on TS `ChangesetState`; `operation_status` is a top-level
singleton where TS's `ChangesetOperationStatus` only exists per-entry inside
`operations[].status` — there is no changeset-wide `operationStatus` field in TS at
all; `files` and `operations` (the actual state) are entirely missing.

**Actions** — TS `ChangesetAction` has 7 variants: `changeset/statusChanged,
changeset/fileSet, changeset/fileRemoved, changeset/contentChanged,
changeset/operationsChanged, changeset/operationStatusChanged, changeset/cleared`
(`types/channels-changeset/actions.ts`). Python implements only
`changeset/operationStatusChanged`, and even that mismatches shape: TS's variant
targets one operation by `operationId` (`types/channels-changeset/actions.ts:111-119`),
while Python's `ChangesetOperationStatusChangedAction{status}` has no `operationId`
and instead overwrites the (nonexistent-in-TS) whole-changeset `operation_status`
(`clients/python/src/ahp/types/actions.py:159-167`). Missing entirely:
`changeset/statusChanged`, `changeset/fileSet`, `changeset/fileRemoved`,
`changeset/contentChanged`, `changeset/operationsChanged`, `changeset/cleared`.

**Commands** — TS `InvokeChangesetOperationParams{channel, operationId, target?:
ChangesetOperationTarget}` (`types/channels-changeset/commands.ts:74-84`). Python
`InvokeChangesetOperationParams{changeset_uri, operation, args: dict}`
(`clients/python/src/ahp/types/commands.py:252-255`) — none of these field names
match; `target`/`ChangesetOperationTarget` unmodeled.

**Reducer** — Python `changeset_reducer` only handles its one mismatched action and
no-ops on the other 6 real TS variants (`clients/python/src/ahp/reducers/changeset.py:12-21`).

## `annotations`

**State** — TS `AnnotationsState{annotations: Annotation[]}` where `Annotation` is a
typed shape (`id, turnId, resource, range?, resolved, entries: AnnotationEntry[],
_meta?`, `types/channels-annotations/state.ts:45-133`). Python
`AnnotationsState{uri, session_uri, annotations: list[dict]}`
(`clients/python/src/ahp/types/state.py:124-131`) — `uri`/`session_uri` don't exist
on TS `AnnotationsState`; `annotations` is untyped `list[dict]` rather than the real
`Annotation[]` shape (no `turnId`, `resolved`, `entries` modeled at all).

**Actions** — TS `AnnotationsAction` has 5 variants: `annotations/set,
annotations/updated, annotations/removed, annotations/entrySet,
annotations/entryRemoved` (`types/channels-annotations/actions.ts`). Python has 2
invented type strings with no TS match: `annotations/added` (real TS equivalent is
`annotations/set` and carries a full `Annotation` with `turnId`/`resolved`/`entries`,
`types/channels-annotations/actions.ts:41-45`) and `annotations/removed` (Python's
field is `annotation_id`; TS's real `annotations/removed` field is also
`annotationId` but the type string `annotations/added` itself doesn't exist in TS)
(`clients/python/src/ahp/types/actions.py:174-187`). Missing entirely:
`annotations/updated`, `annotations/entrySet`, `annotations/entryRemoved`.

**Reducer** — Python `annotations_reducer` operates on untyped dicts keyed by `"id"`
by convention (its own docstring admits this,
`clients/python/src/ahp/reducers/annotations.py:21-24`) and handles only its 2
invented actions, no-oping on the 3 missing real variants.

## `otlp`

Missing entirely from the Python client. `types/channels-otlp/state.ts` defines
`TelemetryCapabilities{logs?, traces?, metrics?}` and
`types/channels-otlp/notifications.ts` defines `otlp/exportLogs`,
`otlp/exportTraces`, `otlp/exportMetrics` notifications carrying OTLP/JSON payloads.
Python has no `types/state.py` model for `TelemetryCapabilities`, no
`reducers/otlp.py`, and no notification models for the three real `otlp/export*`
methods — the only trace of "otlp" in the Python client is an invented
`"otlp/log"` notification (`clients/python/src/ahp/types/notifications.py:56-71`)
that does not correspond to any real TS method.

## `resource-watch`

Missing entirely from the Python client. `types/channels-resource-watch/state.ts`
(`ResourceWatchState{root, recursive, excludes?, includes?}`), `actions.ts`
(`ResourceWatchChangedAction{type:'resourceWatch/changed', changes:{items:
ResourceChange[]}}`), and `commands.ts` (`createResourceWatch`) have no equivalents
anywhere in `clients/python/src/ahp/types/` or `clients/python/src/ahp/reducers/`
(confirmed via repo-wide grep — zero matches for "resource.watch"/"ResourceWatch" in
the Python source tree). There is also no `reducers/resource_watch.py`.

## What this means for next-session sequencing

This supersedes the "spot-check" framing in `HANDOFF.md`'s previous "Recommended
order of work" §3. The fix is not a diff-and-patch pass; it's closer to a rewrite of
`ahp/types/` and `ahp/reducers/` driven channel-by-channel from `types/*.ts` (with
`schema/*.schema.json` as tie-breaker), each field/variant/reducer-branch introduced
via a failing test first (Red/Green TDD), same discipline the existing codebase
already uses. Suggested order, cheapest/highest-blast-radius first:

1. `common/errors.ts` → `errors.py` (one enum, ~10 values, used everywhere).
2. `common/` commands/notifications/state primitives (`Snapshot`, `ActionEnvelope`,
   `initialize`/`ping`/`reconnect`/`subscribe`/`dispatchAction`/`resource*`/
   `authenticate`).
3. `root` and `session` channels (highest traffic, most-used state).
4. `chat` and `terminal` channels.
5. `changeset` and `annotations` channels.
6. Add `otlp` and `resource-watch` channels from scratch (currently absent).

Each step should delete/replace the corresponding wrong models rather than layering
new ones alongside — the existing "invented" fields/types have no callers outside
this package's own tests, so there's no external compat surface to preserve.
