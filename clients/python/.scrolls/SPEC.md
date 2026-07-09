# AHP Python Client — Specification & Implementation Plan

> Location (intended): `clients/python/SPEC.md`
> Status: Draft v1
> Source repo analyzed: `microsoft/agent-host-protocol` (fork: `sugatoray/agent-host-protocol`, branch `ahp_python_client`)

This document plans a Python client for the Agent Host Protocol (AHP), modeled on the
existing Rust, Go, and TypeScript clients in this repository. It is a living document —
update it as design decisions are made or the upstream protocol/spec changes.

---

## 1. Background

The Agent Host Protocol (AHP) defines how a portable, standalone sessions server
communicates with its clients. Multiple clients can connect to the server and see a
synchronized view of AI agent sessions through immutable state, pure reducers, and
write-ahead reconciliation. In the lineage of LSP/DAP: the host owns authoritative
session state, clients speak AHP, and any client can drive any agent while all clients
stay in sync.

Reference implementation: VS Code agent host (`src/vs/platform/agentHost/node/`).
Protocol docs: https://microsoft.github.io/agent-host-protocol/

## 2. What the existing clients look like

Every language client in this repo follows the same three-layer shape:

| Layer | Rust | Go | TypeScript | Purpose |
|---|---|---|---|---|
| Wire types | `ahp-types` | `ahptypes` | `@microsoft/agent-host-protocol` (types) | Generated/mirrored types — `Snapshot`, `ActionEnvelope`, `StateAction` union, per-channel state/action types, `CommandMap`/`ServerCommandMap` registries |
| Pure reducers | in `ahp` | in `ahp` | in same package | `rootReducer`, `sessionReducer`, etc. — `(state, action) -> newState`, no I/O |
| Client + transport | `ahp` crate + `ahp-ws` | `ahp` pkg + `ahpws` | `AhpClient` + `WebSocketTransport` | JSON-RPC dispatch, subscription bookkeeping, write-ahead reconciliation, pluggable `Transport` |
| Multi-host | `ahp::hosts::MultiHostClient` (`::single`) | `ahp/hosts.MultiHostClient` (`.Single(...)`) | not yet shipped | Fan a single logical client out across N host connections |

Release convention: each client tags independently (`rust/vX.Y.Z`, `clients/go/vX.Y.Z`,
`typescript/vX.Y.Z`), has its own `CHANGELOG.md`, and the protocol itself versions
separately (currently protocol version `1`, semver-negotiated at `initialize`). The
Python client should follow this same convention: independent `python/vX.Y.Z` tags and
its own `CHANGELOG.md`.

## 3. Protocol shape the client must model

From the specification pages:

- JSON-RPC 2.0 over any ordered, reliable, bidirectional transport (WebSocket is the
  de facto one used by all current clients).
- Every command's `params` and every notification carries a top-level `channel: URI` —
  this is the routing key, so dispatch can be done on `(method, channel)` without
  per-method parsing.
- Lifecycle: `initialize` (version negotiation + snapshots) → `subscribe` /
  `unsubscribe` → `dispatchAction` (fire-and-forget, optimistic, client → server) ↔
  `action` notification (server echo, carries `serverSeq` + `origin`) → `reconnect` on
  drop (replay-or-resnapshot).
- ~20 commands in `CommandMap`: `initialize`, `ping`, `reconnect`, `subscribe`,
  `createSession`, `disposeSession`, `createChat`, `disposeChat`, `createTerminal`,
  `disposeTerminal`, `listSessions`, the `resource*` filesystem family, `fetchTurns`,
  `authenticate`, `completions`, `invokeChangesetOperation`, etc.
- A large `StateAction` discriminated union (root / session / chat / terminal /
  changeset / annotations actions) that reducers consume.
- `resource*` commands are symmetrical — the server can call the client too. This
  matters for transport design (the transport must support bidirectional dispatch, not
  just request/response from one side).

## 4. Proposed `clients/python/` layout

```
clients/python/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── SPEC.md                      # this file
├── src/ahp/
│   ├── __init__.py
│   ├── types/                   # mirrors ahp-types / ahptypes
│   │   ├── common.py            # URI, Snapshot, ActionEnvelope, ActionOrigin, ContentRef, ErrorInfo, etc.
│   │   ├── commands.py          # CommandMap-equivalent: one model per params+result
│   │   ├── actions.py           # StateAction union (root/session/chat/terminal/changeset/annotations)
│   │   ├── state.py             # RootState, SessionState, ChatState, TerminalState, ChangesetState, AnnotationsState
│   │   ├── notifications.py     # action, root/sessionAdded, auth/required, otlp/*
│   │   ├── errors.py            # AhpError, error code enum (-32005, -32007, -32009, ...)
│   │   └── jsonrpc.py           # JsonRpcRequest/Response/Notification, ProtocolMessage union
│   ├── reducers/
│   │   ├── root.py
│   │   ├── session.py
│   │   ├── chat.py
│   │   ├── terminal.py
│   │   ├── changeset.py
│   │   └── annotations.py
│   ├── transport/
│   │   ├── base.py              # Transport protocol/ABC: send(str), receive() -> AsyncIterator[str], close()
│   │   └── websocket.py         # WebSocketTransport (websockets or httpx-ws)
│   ├── client.py                 # AhpClient: connect/initialize/subscribe/dispatch_action/reconnect
│   └── hosts.py                  # MultiHostClient + MultiHostClient.single(...)
└── tests/
    ├── test_reducers.py          # pure, no I/O — port straight from TS/Rust test fixtures
    ├── test_client.py            # against a fake/in-memory transport
    └── test_reconnect.py         # replay vs snapshot paths
```

## 5. Core design decisions

**5.1 Sync vs async.**
Go and TS clients are async by nature (goroutines / event loop); Rust is `async`
(tokio). Python should be `asyncio`-based (`AhpClient` as an async context manager:
`async with AhpClient(transport) as client:`), matching the concurrency model the
other three share rather than bolting on threads.

**5.2 Types: pydantic v2 vs stdlib dataclasses.**
This is wire-format modeling with a discriminated `StateAction` union and JSON
round-tripping. Pydantic v2 (`Literal`-discriminated tagged unions on `type`/`method`)
gets validation + serialization for free and mirrors what the TS generated types are
doing. Tradeoff: adds a dependency. **Open decision — not yet made.** Given a general
preference for dependency-light, Python-first solutions, this should be decided
explicitly before types are scaffolded, rather than defaulted.

**5.3 Reducers must stay pure.**
Same discipline as the TS/Rust reducers: `def session_reducer(state: SessionState,
action: StateAction) -> SessionState`, no I/O, fully unit-testable in isolation. This
can be ported almost mechanically from the TS reducer source since the logic is small
and the type shapes are fully spec'd.

**5.4 Transport abstraction first.**
Define `Transport` as a `Protocol` (structural typing) before writing
`WebSocketTransport`, so a `StdioTransport` or in-memory test transport drops in
without touching `AhpClient`. This mirrors the Rust/Go `Transport` trait/interface
pattern and is what makes `MultiHostClient` cheap to build later — it's just N
`AhpClient`s over N transports with a merged dispatch surface.

**5.5 Reconnection state machine.**
`AhpClient` needs to track `client_id`, `client_seq`, `last_seen_server_seq`, and
current `subscriptions: set[URI]` internally so `reconnect()` can be called
transparently on transport drop without the caller re-deriving that state.

**5.6 Write-ahead reconciliation.**
`dispatch_action()` should apply the reducer optimistically to local state keyed by
`ActionOrigin(client_id, client_seq)`, then reconcile against the server's `action`
notification echo. This is the trickiest correctness-sensitive piece and deserves its
own test file covering the concurrent-edit / reconciliation scenario from the docs.

## 6. Suggested phased build order

1. **Types** (`types/`) — mechanical, spec-driven, no logic. Do this first; everything
   else depends on it. Can be hand-written or generated from the JSON Schemas at
   `schema/*.schema.json` if a codegen step is preferred over hand-translation.
2. **Reducers** — pure functions; port test fixtures from TS/Rust to validate against
   known-good behavior. **Done (v3)** — scaffolded via Red/Green TDD: see
   `tests/reducers/` and `src/ahp/reducers/`. Test fixtures are original (written
   against the seed `StateAction` variants in `types/actions.py`), not ported from
   TS/Rust, since those test suites weren't directly browsable from this
   environment (see §7a and the v3 changelog entry above).
3. **Transport + basic `AhpClient`** — `initialize`, `subscribe`,
   `dispatchAction`/`action` round-trip against a fake transport. **Done (v4/v5)**:
   `ahp.transport` built and actually executed (24/24 passing after fixing a
   real deadlock found while building the client — see v5 changelog entry).
   `ahp.client.AhpClient` implemented with `initialize`/`subscribe`/
   `dispatch_action`/`get_state`/`close`, tested against a scripted fake host
   over `InMemoryTransport` (`tests/client/test_ahp_client.py`) — but **not
   executed**, since this layer needs real pydantic and no network was
   available to install it in the sandbox. Syntax-checked only
   (`py_compile`). Running this for real is the first thing to do before
   trusting it — see §7a.
4. **Reconnection** — replay vs snapshot paths. **Done (v6)**: `AhpClient.reconnect()`
   sends `last_seen_server_seq` per channel, overwrites local state immediately
   for any `resnapshotted` channels, and deliberately leaves `replayed`
   channels untouched — the ordinary `action` notification handler (already
   built for phase 3) applies whatever the host replays, including correctly
   deduplicating echoes of this client's own not-yet-acknowledged actions
   from before the drop. Optionally swaps in a new `Transport` (cancels the
   old reader task rather than awaiting it, since the old transport may not
   be cleanly closed). Syntax-checked only (see §7a).
5. **`resource*` family + `authenticate`** — symmetrical (server can call back), which
   affects transport design if these are to be supported properly. **Done (v6)**:
   client-initiated `authenticate`/`resource_read`/`resource_write`/`resource_list`/
   `resource_stat` implemented as ordinary `_send_request` wrappers. The
   host-initiated direction is handled via a `ResourceProvider` protocol
   (`read`/`write`/`list`/`stat`) registered with
   `AhpClient.register_resource_provider()`; the reader loop now also
   recognizes incoming `JsonRpcRequest` messages (not just responses/
   notifications) and routes them there, always replying with success or a
   JSON-RPC error — a provider exception or a missing provider never crashes
   the reader loop. Syntax-checked only (see §7a).
6. **`MultiHostClient`** — last, since Rust/Go already validate the abstraction and
   it's additive. **Done (v6)**: `ahp.hosts.MultiHostClient` is a thin
   host_id-keyed registry over `AhpClient` — `.single(client)` for the common
   case, `add_host`/`remove_host`/`client_for`, `initialize_all`/`close_all`
   (concurrent via `asyncio.gather`; `close_all` uses `return_exceptions=True`
   so one host's failure to close doesn't block the others), plus
   `get_state`/`dispatch_action` convenience delegates and an async context
   manager. No new protocol logic — everything routes through `AhpClient`.
   Syntax-checked only (see §7a).
7. **Packaging** — `pyproject.toml` targeting PyPI, `python/vX.Y.Z` tag convention to
   match the other clients, CI workflow mirroring the TS Azure DevOps pipeline pattern
   (or GitHub Actions with OIDC Trusted Publishing).

## 7. Open questions / decisions log

- [x] **pydantic v2 vs stdlib `dataclasses`** — decided: pydantic v2
      (`pydantic>=2.0,<3.0`). Gives alias-based camelCase/snake_case round-tripping,
      discriminated-union validation for `StateAction`, and `extra="allow"`
      forward-compatibility for free. See `src/ahp/types/`.
- [ ] Hand-write types vs codegen from `schema/*.schema.json` — currently
      hand-written as a first pass (see §7a below); revisit once the schema files
      have been reviewed directly.
- [ ] WebSocket library choice: `websockets` vs `httpx-ws` vs `aiohttp` — `pyproject.toml`
      currently pins the optional `websocket` extra to `websockets>=12.0`.
      `ahp/transport/websocket.py` only imports it lazily inside `.connect()`,
      so the wrapper class itself is library-agnostic; the choice of *which*
      library backs `.connect()` by default is still open.
- [~] Minimum supported Python version — tentatively set to `>=3.10` in
      `pyproject.toml` (needed `X | Y` union syntax without `from __future__ import
      annotations` gymnastics, and `str, Enum` mixins work fine back to 3.9 if that
      floor needs to drop later). Not treated as final.
- [x] **How `resource*` server→client calls are handled architecturally** —
      decided: a `ResourceProvider` structural protocol
      (`read`/`write`/`list`/`stat`) registered via
      `AhpClient.register_resource_provider()`. The reader loop routes
      incoming `JsonRpcRequest` messages (as opposed to responses/
      notifications) to it and always replies (success or JSON-RPC error) —
      a missing provider or a provider exception never crashes the reader
      loop. See `src/ahp/client.py`'s `_handle_host_request`.

### 7a. Status of the types layer (this pass)

`src/ahp/types/` is scaffolded and syntax-checked, but **not yet runtime-verified**
against a real pydantic install (sandbox had no network access to install
`pydantic`). Before relying on it:

1. `pip install -e ".[dev]"` and run `pytest` in `clients/python/` to confirm the
   models actually import and validate as written.
2. `actions.py` seeds each of the six action families (root/session/chat/terminal/
   changeset/annotations) with a handful of representative variants rather than
   the full ~80-variant union — enough to exercise dispatch/reconciliation
   end-to-end, but incomplete. The extension pattern is documented at the top of
   that file.
3. `state.py` field sets (e.g. `RootState.agents`, `Turn`, `SessionState`) are
   inferred from the README/spec prose and one third-party AHP plugin's ported
   TS interfaces, not copied from an authoritative schema — flag anything that
   looks wrong once cross-checked against `schema/*.schema.json`.
4. Error codes in `errors.AhpErrorCode` are explicitly marked provisional
   placeholders pending the upstream error-code table.
5. **Update 2026-07-06 (v7): actually run.** A real pydantic install became
   available and `uv run pytest -v` was executed for the first time across
   the whole suite: 94/94 passing, including `ahp.types`, `ahp.reducers`,
   `ahp.client`, and `ahp.hosts` (previously `py_compile`-only). This found
   one real bug — `ahp/types/__init__.py` didn't re-export the command
   `Params`/`Result` models from `commands.py` (only `COMMANDS`), so
   `tests/client/test_resource_provider.py` failed at collection
   (`ImportError: cannot import name 'ResourceListResult'`). Fixed by adding
   the full set of command model names to `__init__.py`'s imports/`__all__`.
   Everything else — error codes (point 4), incomplete `StateAction` variants
   (point 2), unverified `state.py` field sets (point 3) — is still exactly
   as provisional as described above; passing tests confirm the code runs as
   written, not that the field sets match the real upstream schema.
6. **Update 2026-07-06 (v9): points 2-4 above are now confirmed, not just
   flagged.** With the repo-root `types/*.ts` canonical source reachable, a
   full field-by-field diff was run against it (and `schema/*.schema.json`
   as tie-breaker) — see [`GAPANALYSIS.md`](./GAPANALYSIS.md). Result: this
   isn't a handful of wrong field names. Nearly every state field, action
   variant, command param/result shape, notification shape, and every
   `AhpErrorCode` value disagrees with canonical `types/*.ts`, and two
   channel families (`otlp`, `resource-watch`) don't exist in this client at
   all. `GAPANALYSIS.md` has the itemized, file:line-cited diff and a
   suggested fix order. Treat points 2-4 above as historical context for
   *why* the gap exists, not as the current todo list — `GAPANALYSIS.md` is
   the current todo list.
7. **Update 2026-07-07 (v10): most of `GAPANALYSIS.md`'s todo list is now
   done.** See the v10 changelog entry below and `GAPANALYSIS.md` itself for
   what's left — it's a short, mechanical list now, not a rewrite.

## 8. Changelog of this document

- v1 — initial draft, based on repo README + specification pages (overview, transport,
  lifecycle, common types reference) as of this analysis.
- v2 — `ahp.types` scaffolded (pydantic v2, Python `>=3.10` tentative). Updated §7
  decisions log to reflect what's resolved vs. still open, added §7a documenting
  the current state/limits of the types layer. See `CHANGELOG.md` for the
  package-level changelog going forward.
- v3 — `ahp.reducers` scaffolded via Red/Green TDD: `tests/reducers/test_*.py`
  written first (red — `ahp.reducers` didn't exist), then
  `root/session/chat/terminal/changeset/annotations.py` implemented to satisfy
  them (green). Could not confirm the exact test-suite layout of the Rust/Go/
  TypeScript clients directly (GitHub blocks automated access to subdirectory
  tree pages from this environment) — the Python test structure below is based
  on idiomatic pytest conventions, not a port of theirs. If you browse those
  folders yourself, worth reconciling naming/structure against this.
- v4 — `ahp.transport` scaffolded via Red/Green TDD: `Transport` protocol,
  `InMemoryTransport` (paired in-memory duplex, for testing higher layers),
  and `WebSocketTransport` (wraps any duck-typed async send/recv/close
  connection; lazily imports the real `websockets` package only inside
  `.connect()`). Unlike the types/reducers passes, this one was *actually run*
  in the sandbox — no real `pytest` or `websockets` install available (no
  network), so a throwaway ~40-line async test runner plus a `pytest.raises`
  -only shim executed the real test bodies. Verified true red (deleting
  `ahp/transport/` breaks every test at import) → green (23/23 pass restored).
  `AhpClient` itself (the piece that actually uses `Transport`) is not started.
- v5 — `ahp.client.AhpClient` implemented (`initialize`, `subscribe`,
  `dispatch_action` with write-ahead reconciliation, `get_state`, `close`,
  async context manager). Building it surfaced a genuine bug in the v4
  transport: `InMemoryTransport.close()` only signaled the *peer* — a
  `receive()` already blocked on *this same end* (exactly what
  `AhpClient`'s background reader loop does while idle) would hang forever.
  Added a regression test
  (`test_close_unblocks_a_receive_already_pending_on_the_same_end`), confirmed
  it genuinely deadlocked against the old code (bounded by an outer timeout so
  the sandbox itself didn't hang), fixed `close()` to also wake up this end's
  own pending `receive()`, then reran the full transport suite for real
  (24/24). `AhpClient` tests
  (`tests/client/test_ahp_client.py`, scripted fake host over
  `InMemoryTransport`, covering initialize/subscribe/dispatch, the
  own-action-echo-is-not-double-applied case, foreign-action application, and
  close) are **syntax-checked only, not executed** — this layer needs real
  pydantic, and no network was available in the sandbox to install it (tried
  pip, and `uv` with its local cache — nothing available offline). Running
  `pytest` for real on this is the top priority before building further on top
  of it.
- v6 — three phases in one pass, same caveats as v5 (syntax-checked, not
  executed — same missing-pydantic constraint):
  - **`reconnect()`**: sends `last_seen_server_seq` per channel; overwrites
    local state for `resnapshotted` channels; deliberately leaves `replayed`
    channels alone so the existing `action`-notification handler (built in
    v5) applies whatever gets replayed, including correctly deduplicating
    this client's own pre-drop actions. Accepts an optional new `Transport` to
    swap in, cancelling (not awaiting) the old reader task since the old
    transport may not be cleanly closed.
  - **Symmetric commands**: `authenticate`/`resource_read`/`resource_write`/
    `resource_list`/`resource_stat` added as ordinary client-initiated
    `_send_request` wrappers. The harder half — the *host* calling
    `resource*` back against this client — is handled via a new
    `ResourceProvider` protocol registered through
    `register_resource_provider()`; the reader loop now recognizes incoming
    `JsonRpcRequest` messages (previously only responses/notifications were
    handled) and routes them to the provider, always replying with success or
    a JSON-RPC error so a missing provider or a provider bug can't crash the
    reader loop.
  - **`ahp.hosts.MultiHostClient`**: a thin host_id-keyed registry over
    `AhpClient` (`.single()`, `add_host`/`remove_host`/`client_for`,
    concurrent `initialize_all`/`close_all`, `get_state`/`dispatch_action`
    delegates, async context manager). Pure fan-out, no new protocol logic.
  - Refactored the repeated fake-host test scaffolding in `tests/client/`
    into a shared `_helpers.py` rather than continuing to duplicate it across
    test files.
  - `ahp/__init__.py` now re-exports the completed public API
    (`AhpClient`, `MultiHostClient`, etc.) instead of just stating what's
    planned.
- v7 (2026-07-06) — first real test run of the whole suite (`uv run pytest
  -v`, real pydantic install, no more `py_compile`-only caveat): 94/94
  passing. Fixed the one bug this surfaced — `ahp/types/__init__.py` re-exported
  only `COMMANDS` from `commands.py`, not the individual `Params`/`Result`
  classes, so `ResourceListResult`/`ResourceReadResult`/`ResourceStatResult`
  (imported directly by `tests/client/test_resource_provider.py`) weren't
  importable from `ahp.types`. Added the full set of command model names to
  `__init__.py`'s imports and `__all__`. No other code changes; see §7a point 5.
- v8 (2026-07-06) — closed the biggest remaining functional gap via Red/Green
  TDD: `AhpClient.unsubscribe()` plus the full session/chat/terminal
  lifecycle (`create_session`/`dispose_session`/`list_sessions`,
  `create_chat`/`dispose_chat`/`fetch_turns`,
  `create_terminal`/`dispose_terminal`, `completions`,
  `invoke_changeset_operation`). Tests written first
  (`tests/client/test_lifecycle.py`, 11 cases), verified red (`AttributeError:
  'AhpClient' object has no attribute ...`), then implemented — each
  `create_*` mirrors `subscribe()`'s snapshot registration
  (`_channel_states`/`_last_seen_server_seq`), each `dispose_*`/`unsubscribe`
  mirrors the same forgetting logic. Full suite: 105/105 passing. Only
  `ping` remains unwrapped from the `COMMANDS` registry (low priority).
- v9 (2026-07-06) — ran the field-by-field verification against canonical
  `types/*.ts` that §7a points 2-4 had been flagging as an open hypothesis
  since v2. Wrote up the full diff in the new `GAPANALYSIS.md` (one section
  per channel family plus `common/`, each discrepancy file:line-cited on
  both sides). No production code changed in this pass — this was
  documentation/verification only, per explicit direction to capture the
  analysis before starting the fix work. Conclusion: the gap is systemic,
  not a handful of typos — see `GAPANALYSIS.md`'s "What this means for
  next-session sequencing" section for the suggested channel-by-channel
  fix order (errors → common → root/session → chat/terminal →
  changeset/annotations → new otlp/resource-watch channels), each step
  still via Red/Green TDD.
- v10 (2026-07-07) — the reconciliation v9/`GAPANALYSIS.md` called for
  largely happened: commit `8fceda9` rewrote most of `ahp/types/`
  (`actions.py`, `commands.py`, `common.py`, `errors.py`, `notifications.py`,
  `state.py`) and all of `ahp/reducers/`, plus every test file, against
  canonical `types/*.ts`. `AhpErrorCode`, common state primitives, and the
  large majority of state/action field names now match canonical TS;
  invented fields/variants from the original scaffold (`HostCapabilities`,
  `RootSessionAdded/RemovedAction`, `terminal/output`, `annotations/added`,
  etc.) are gone. Full suite: 127/127 passing (up from 105). `GAPANALYSIS.md`
  has been re-verified against the current code and rewritten — it no
  longer describes a systemic gap, just a shorter list of remaining
  command-shape, notification-field, and reducer-completion items (see its
  "What this means for next-session sequencing" section). Added
  `WISDOM.md`, a standing reference for this package's constraints, traps,
  ditches, and TDD conventions, distinct from `GAPANALYSIS.md`'s
  point-in-time diff and `HANDOFF.md`'s narrative handoff.
- v11 (2026-07-07) — closed all five priorities from `GAPANALYSIS.md`'s
  prior sequencing list via Red/Green TDD. Full suite: 213/213 passing
  (up from 127). Changes by priority:
  - **Notification field shapes** (P1): `auth/required` — `{channel, resource,
    reason?}`; `root/sessionRemoved` — `{channel, session}`; `root/sessionSummaryChanged`
    — `{channel, session, changes}`; `root/progress` — `{channel, progressToken,
    progress, total?, message?}`, registry key fixed to `"root/progress"`; all three
    `otlp/export*` — `{channel, payload}` wrapper (no longer flattened). New test file:
    `tests/types/test_notifications.py` (14 tests).
  - **`create*` command shapes** (P2): `CreateSession/Chat/TerminalResult` now empty
    (match TS `result: null`); `CreateChatParams` gains required `chat` URI;
    `CreateTerminalParams` gains required `claim`; `FetchTurnsResult` now empty (turns
    arrive via `chat/turnsLoaded`); `ListSessionsParams` gains `limit?`/`cursor?`,
    `ListSessionsResult` uses `{items, nextCursor?}`; `ResolveSessionConfigParams` gains
    `provider?`/`workingDirectory?`, result is `{schema, values}`; added
    `SessionConfigCompletionsParams/Result` and `CreateResourceWatchParams/Result`;
    `InvokeChangesetOperationParams/Result` rewritten to `{channel, operationId, target?}`
    / `{message?, followUp?}`. `AhpClient` updated accordingly — `create_session`,
    `create_chat`, `create_terminal` now generate URIs client-side via `uuid.uuid4()`.
    New test file: `tests/types/test_commands.py` (31 tests); `tests/client/test_lifecycle.py`
    updated (6 tests).
  - **Reducer completion** (P3): session reducer — added `isRead`/`isArchived` bitflag
    ops (`1<<5`/`1<<6`), `customizationUpdated` (upsert by id), `customizationRemoved`
    (removes from top-level and nested children); fixed `chatRemoved` to filter by
    `resource` (not `uri`) and clear `default_chat`. Terminal reducer — rewrote
    `TerminalData` handler to use `command`/`unclassified` content part types; added
    `TerminalCommandExecuted` (appends new `command` part) and `TerminalCommandFinished`
    (marks `isComplete`, sets `exitCode`/`durationMs`). Changeset reducer — fixed
    `fileRemoved` to use `file_id`; added `contentChanged` branch (full replacement of
    `files`/`operations`/`error`).
  - **Action field-shape fixes** (P4): `ChangesetFileRemovedAction.file_id = Field(alias="fileId")`
    (was `id`); `ChangesetContentChangedAction` rewritten to `{files, operations?, error?}`;
    `ResourceWatchChangedAction.changes` → `list[Any]` (was `dict`); chat actions —
    `ChatToolCallConfirmedAction`/`ChatToolCallResultConfirmedAction`: `outcome:str` →
    `approved:bool`; `ChatPendingMessageSetAction`: added `kind:str`, `id:str`;
    `ChatPendingMessageRemovedAction`: added `kind:str`; `ChatQueuedMessagesReorderedAction`:
    `ids` → `order`; `ChatInputAnswerChangedAction`: added `question_id`, made `answer`
    optional; `ChatInputCompletedAction`: added `response` (required), `answers?`.
    New test file: `tests/types/test_chat_actions.py` (15 tests).
  - **`resource-watch`** (P5): `ResourceWatchState{root, recursive, excludes?, includes?}`
    added to `state.py` and `AnyChannelState` union; `reducers/resource_watch.py` added
    (trivial pass-through, matching canonical TS which has no state mutations post-subscribe);
    `CreateResourceWatchParams/Result` added (see P2 above). New test file:
    `tests/reducers/test_resource_watch_reducer.py` (5 tests).
  - `GAPANALYSIS.md` rewritten to reflect fully-closed status; remaining items
    are shallow laxities or depth choices, not protocol gaps.
  - Added `GAPCONTEXT.md` — standing companion to `GAPANALYSIS.md` that records
    *why* each remaining gap matters: cross-client evidence (TS/Go/Rust file:line),
    what breaks without it, canonical shape. `CLAUDE.md` updated to reference it
    as a required read before acting on any gap. Initial entries: `TelemetryCapabilities`,
    `ChatState` missing fields, `Turn.state` type, `ChatToolCallConfirmedAction`
    subtype split, `SessionMcpServerStateChangedAction` reducer.
  - `AhpClient.ping()` wrapper added; structured logging (`logging.getLogger(__name__)`)
    added to reader loop (malformed messages, unhandled host requests). Suite: 214/214.
- v15 (2026-07-07) — closed the last two open gaps from GAPCONTEXT.md via Red/Green TDD.
  (1) `ChatState` missing fields: `origin` (`dict[str, Any] | None`), `interactivity`
  (`str | None`, values `'full'|'read-only'|'hidden'`), and `working_directory`
  (`str | None`, alias `workingDirectory`) added to `ChatState` in `state.py`.
  10 tests in `tests/types/test_chat_state_fields.py`.
  (2) `SessionMcpServerStateChangedAction` reducer: was a deliberate no-op; now
  searches `state.customizations` for a matching `mcpServer` entry by `action.id`
  (top-level first, then inside container `.children`), updates its `state` and
  `channel` fields immutably. Returns state unchanged if no match, if
  customizations is `None`/empty, or if the matched entry has a non-`mcpServer`
  type. Logic mirrors `types/channels-session/reducer.ts:278–329`. 9 tests in
  `tests/reducers/test_session_mcp_reducer.py`. All gaps from GAPCONTEXT.md now
  closed. Suite: 257/257.
- v14 (2026-07-07) — closed `ChatToolCallConfirmedAction` subtype split via Red/Green TDD.
  `ChatToolCallConfirmedAction` (the `StateAction` union member) now carries all fields
  from both canonical subtypes: `confirmed` + `edited_tool_input` (approved path) and
  `reason` + `reason_message` + `user_suggestion` (denied path), plus shared
  `selected_option_id`. Pydantic's `Field(discriminator="type")` on `StateAction` prevents
  two separate classes with the same `type` literal, so a flat model is used as the union
  member. Additionally, `ChatToolCallApprovedAction` (`approved: Literal[True]`, required
  `confirmed: str`) and `ChatToolCallDeniedAction` (`approved: Literal[False]`, required
  `reason: str`) added as typed convenience models for callers that construct or dispatch
  confirmations. Both exported from `ahp.types`. 9 new tests in
  `tests/types/test_chat_actions.py` (24 total). Suite: 240/240.
- v13 (2026-07-07) — closed `Turn.state` type gap via Red/Green TDD.
  `Turn.state` changed from `dict[str, Any]` (defaulting to `{"type":"running"}`)
  to `Literal["complete", "cancelled", "error"]`, matching canonical
  `types/channels-chat/state.ts:477-481` and Go/Rust. Architectural correction
  to `chat_reducer`: in-progress turns now live in `ChatState.active_turn`
  (a `dict | None`, matching the wire `ActiveTurn` shape) instead of being placed
  in `turns` with an invented "running" state. `ChatTurnStartedAction` populates
  `active_turn`; delta/reasoning actions update it; complete/cancelled/error
  finalize the turn into `turns` with a terminal state string and clear
  `active_turn`. `ChatState.active_turn` type corrected from `str | None` to
  `dict[str, Any] | None`. 7 new tests in `tests/types/test_turn_state.py`;
  `tests/reducers/test_chat_reducer.py` rewritten (13 tests, up from 9);
  `tests/client/test_ahp_client.py` snapshot fixture updated. Suite: 231/231.
- v12 (2026-07-07) — closed `TelemetryCapabilities` gap via Red/Green TDD.
  `TelemetryCapabilities(AhpModel)` added to `src/ahp/types/commands.py` with
  `logs`, `traces`, `metrics` (all `URI | None`), matching canonical
  `types/channels-otlp/state.ts:35-68` and the Go/Rust generated types.
  `InitializeResult.telemetry` changed from `dict[str, Any] | None` to
  `TelemetryCapabilities | None`. Exported from `ahp.types`. 6 new tests in
  `tests/types/test_telemetry.py`. `GAPCONTEXT.md` entry marked closed and
  moved to closed-gaps archive. Suite: 220/220.
