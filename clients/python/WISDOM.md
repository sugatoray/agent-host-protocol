# Wisdom — AHP Python Client

Standing reference for this package. Unlike `GAPANALYSIS.md` (a point-in-time diff,
gets rewritten as gaps close) and `HANDOFF.md` (a narrative "what happened last
session"), this file doesn't expire — update it when a constraint, trap, or lesson
turns out to still apply, not on a schedule.

---

## Constraints — respect and conform to them

- **Canonical source of truth is repo-root `types/*.ts`** (per-channel
  `channels-*/{state,actions,commands,notifications,reducer}.ts` + `common/*.ts`),
  with `schema/*.schema.json` as tie-breaker. Not spec prose, not third-party ports,
  not "what seems reasonable." Every field/variant/shape in `ahp/types/` and
  `ahp/reducers/` must trace back to it.

- **Wire models are pydantic v2** with `populate_by_name=True` + `extra="allow"`
  (`AhpModel` base). Don't change this config without auditing every model that
  relies on accepting both camelCase wire keys and snake_case Python kwargs.
  `extra="allow"` is intentional forward-compatibility — unknown fields from a newer
  server version are silently preserved rather than rejected.

- **Reducers are pure**: `(state, action) -> new_state`. No I/O, no in-place
  mutation. Always use `model_copy(update=...)`, never `state.field = value`.
  This is what makes write-ahead reconciliation safe to reason about.

- **`Transport` is a structural `typing.Protocol`**, not an ABC. New transports
  (e.g. `StdioTransport`) just need to duck-type it; no subclassing required.

- **This client releases independently** on its own `python/vX.Y.Z` tags with its
  own `CHANGELOG.md` (Keep a Changelog format), matching the Rust/Go/TypeScript/
  Kotlin clients — not tied to the overall repo version.

- **Tests run from `clients/python/`** (`pyproject.toml` `testpaths = ["tests"]`).
  None of `tests/*/` has `__init__.py`; `tests/client/_helpers.py` is imported bare
  (`from _helpers import ...`) relying on pytest's default "prepend" import mode.
  Reorganizing tests or changing `--import-mode` silently breaks this.

- **`uv` is the package manager for this project.** Use `uv run pytest -v` to run
  the test suite; `uv sync --extra dev` to install dev dependencies.

---

## Traps — avoid them always

### Transport

- **`Transport.close()` must unblock a `receive()` already pending on *this same
  end*, not just signal the peer.** `AhpClient`'s reader loop spends most of its
  life parked in `await self._transport.receive()`. The original
  `InMemoryTransport.close()` only pushed a sentinel into the peer's queue — so
  `AhpClient.close()` hung forever awaiting the reader task. Fixed by pushing into
  both queues. Write an analogous regression test for any new `Transport`
  implementation (see
  `tests/transport/test_memory_transport.py::test_close_unblocks_a_receive_already_pending_on_the_same_end`).

- **`_own_pending_client_seqs` is a global `set[int]` with no eviction.** If a
  dispatched action's echo never arrives (edge case where the host doesn't broadcast
  it), that `client_seq` sits in the set forever. Not a correctness bug today, but
  add a cap/TTL before this sees heavy production use.

- **`reconnect()` cancels the old reader task instead of awaiting it** — deliberate,
  because the old transport is presumably dead. Side effect: "Task was destroyed but
  it is pending" GC warnings are expected, not new bugs.

- **The reader loop silently swallows malformed messages** (`except Exception:
  continue` around `json.loads` + `parse_protocol_message`). No logging currently.
  This makes real host-integration debugging painful. Add structured logging before
  depending on this in production.

### Types and field names

- **`ChatSummary` identity field is `resource`, not `uri`.** Canonical
  `types/channels-chat/state.ts:118-121` uses `resource`. Any code filtering a list
  of chat summaries must use `.get("resource")`. The session reducer's `chatRemoved`
  handler was wrong for a long time — both test data and the reducer used `"uri"`, so
  tests stayed green while the real behavior was broken. Only caught when compared
  against canonical TS.

- **Terminal content parts use `{type: "command", ...}` or `{type: "unclassified",
  value}` — never `{type: "data", data}`.** The original terminal reducer invented a
  `"data"` part type. Canonical shapes come from
  `types/channels-terminal/reducer.ts:17-28`. If you add any terminal content
  handling, use only `"command"` and `"unclassified"`.

- **`create*` commands return `null` in the protocol.** `createSession`,
  `createChat`, `createTerminal` all have `result: null` in canonical TS
  (`types/common/messages.ts:154-159`). The URI is **client-generated** (via
  `uuid.uuid4()`) before the request is sent and passed as the `channel` param. Don't
  look for the URI in the JSON-RPC response — it won't be there.

- **`_channel_binding()` infers channel kind from a naive URI scheme split** against
  a hardcoded dict. If a real host uses different scheme names, every
  `subscribe`/`dispatch_action`/reconciliation call fails with
  `AhpClientError: unrecognized channel scheme`. Verify scheme names against a live
  host before trusting this.

- **`ChatPendingMessageSetAction` needs both `kind` and `id`**, not just `message`.
  `kind` is the `PendingMessageKind` (`"steering"` | `"queued"`) that determines
  which list the message belongs to. Without it, pending-message routing is
  ambiguous.

- **`ChatQueuedMessagesReorderedAction` field is `order`, not `ids`.** The canonical
  TS name (`types/channels-chat/actions.ts:579`) is `order`. Easy to miss since
  `ids` is more intuitive.

- **`ChatInputAnswerChangedAction` requires `questionId`** (in addition to
  `requestId`). An input request can contain multiple questions; `questionId`
  identifies which question is being answered.

---

## Ditches — bad patterns or decisions to avoid

- **Don't hand-invent a field/command/notification shape when canonical `types/*.ts`
  is reachable.** This is exactly how the client accumulated dozens of discrepancies
  the first time (see `GAPANALYSIS.md`'s original 2026-07-06 pass). Read the `.ts`
  file for the channel you're touching *before* writing the pydantic model.

- **Don't add a `StateAction` variant without its matching reducer branch.** The
  extension pattern is at the top of `types/actions.py`. Track partial reducer
  coverage explicitly in `GAPANALYSIS.md` rather than leaving it implicit — that is
  how "no-op" branches got lost track of across multiple sessions.

- **Don't treat "tests pass" as "matches the protocol."** Green `pytest` proves the
  code matches its *own* tests. If the tests were written against an invented shape,
  they'll stay green while disagreeing with the real wire format. Explicitly
  cross-check against `types/*.ts`.

- **Don't layer a corrected model alongside an old wrong one "to be safe."** No
  external caller depends on this package's shapes yet. When `GAPANALYSIS.md` flags
  something wrong, delete and replace it, don't add a second parallel type.

- **Don't let `SPEC.md`/`HANDOFF.md`/`GAPANALYSIS.md`/`WISDOM.md` drift from the
  code.** They are living documents — update them in the same session as the code
  change that invalidates them.

- **Don't use `model_fields` on a pydantic model *instance* for introspection.**
  `instance.model_fields` works but triggers a deprecation warning in pydantic v2 (it
  resolves to the class attribute, which already requires a class object). Always use
  `ClassName.model_fields` at the class level.

- **Don't invent a flattened notification shape when TS wraps in a `payload` field.**
  The original `otlp/export*` notifications placed `resource_logs`/`resource_spans`/
  `resource_metrics` directly on the notification params. Canonical TS wraps them:
  `{channel, payload: {resourceLogs: ...}}`. Check the TS notification shape before
  modeling.

- **Don't default `SessionStatusAction` handling to a raw bit value without the
  named constants.** `IsRead = 1 << 5 = 32`, `IsArchived = 1 << 6 = 64`. Use named
  constants (`_IS_READ`, `_IS_ARCHIVED`) and the `_with_status_flag(status, flag,
  value)` helper in `reducers/session.py` — not magic numbers.

---

## Wisdom — best practices and Red/Green TDD

### TDD discipline

- **Write the failing test first, confirm it fails for the right reason, then
  implement.** A test that fails with `ImportError` or `AttributeError` is not
  "confirmed red" — it may be a typo. Confirm the failure message reflects a genuine
  missing behavior before implementing.

- **Run `uv run pytest -v` for real, not just `py_compile`.** This package was burned
  once by "syntax-checked only" being treated as "tested" (see `SPEC.md §7a`). Real
  runs have caught genuine bugs that static review missed (the transport deadlock,
  the `chatRemoved` key mismatch).

- **Fix one channel family at a time, cheapest/highest-value first** per
  `GAPANALYSIS.md`'s priority order. Don't reconcile everything at once — that's how
  partial reducer coverage gets lost across sessions.

- **Run the full suite after every channel-family fix** to catch regressions. A
  change to `actions.py` (e.g. renaming a field) can break reducers and clients
  that weren't the direct target of the fix.

### Reading canonical TS source

- **Before touching a channel's `types/`/`reducers/` code, read that channel's
  `.ts` files first.** The ordering matters: `state.ts` → `actions.ts` →
  `reducer.ts` → `commands.ts` → `notifications.ts`. State defines the shape,
  actions define the mutations, the reducer defines the semantics.

- **When a canonical TS reducer is a trivial pass-through** (e.g.
  `channels-resource-watch/reducer.ts`), that's intentional — the channel's state
  is set at subscription time and change events are ephemeral. Don't add mutation
  logic that doesn't exist in TS.

- **When a canonical TS file doesn't exist** (e.g. `channels-chat/reducer.ts`,
  `channels-otlp/actions.ts`), that's also intentional. Having a Python
  `chat_reducer` or `otlp_reducer` is a structural asymmetry, not a gap to fill.

### Common patterns

- **Client-side URI generation**: `f"ahp-{scheme}:/{uuid.uuid4()}"` — generate the
  URI before the request, pass it as `channel` (and sometimes as a named field like
  `chat`), and return it to the caller. Never read the URI from the response.

- **Bitflag status fields**: use `_with_status_flag(status, flag, value)` —
  `(status | flag) if value else (status & ~flag)`. Avoids accidentally clearing
  unrelated bits. Named constants (`_IS_READ = 1 << 5`, `_IS_ARCHIVED = 1 << 6`)
  live in `reducers/session.py`.

- **Customization upsert**: find by `id`, replace in-place if found, append if not.
  The same pattern appears for any channel-local list-with-identity (MCP server
  tools, input-needed entries, etc.).

- **Pagination cursors**: `nextCursor` is optional in results and `cursor` is
  optional in params — always use `Field(default=None, alias="nextCursor")` and
  handle `None` at the call site rather than a sentinel string.

- **Notification registry keys** follow the method string exactly
  (`"root/progress"`, `"otlp/exportLogs"`, not `"$/progress"` or `"otlp/log"`).
  The key in `NOTIFICATIONS` must match what the server sends as `method`.

- **When a shared primitive changes** (`AhpErrorCode`, `Snapshot`, `ActionEnvelope`,
  `AhpModel`), grep for every model and reducer that references it before changing
  it — these are used across all six channel families.
