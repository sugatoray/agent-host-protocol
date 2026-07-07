# Handoff — AHP Python Client

> Read this file first, before SPEC.md or the source. SPEC.md is the design
> plan and decision log (why things are shaped this way); this file is the
> "what actually happened, what to do next" operational summary for picking
> the work back up in a fresh session.

## TL;DR

- A full-surface Python client for the Agent Host Protocol (AHP) has been
  scaffolded: `ahp.types`, `ahp.reducers`, `ahp.transport`, `ahp.client`
  (`AhpClient`), and `ahp.hosts` (`MultiHostClient`). All built via Red/Green
  TDD (tests written first, then implementation).
- **Only `ahp.transport` has ever actually been executed.** Everything else
  has been `py_compile`-checked (syntax valid) and cross-referenced
  statically (method names match), but never run, because the sandbox this
  was built in had no network access to install `pydantic`.
- **The single most important next step**: `cd clients/python && pip install
  -e ".[dev]" && pytest -v`. Do this before writing any more code. Fix
  whatever it finds before extending anything.
- Nothing here has been checked against the actual Rust/Go/TypeScript client
  source or the JSON schema files upstream — GitHub blocked automated access
  to subdirectory pages from the sandbox this was built in. If you have
  browser/API access to `microsoft/agent-host-protocol`, reconciling against
  those is probably the second most valuable thing to do.

## Repo context

- Upstream: `microsoft/agent-host-protocol`
- Working fork: `sugatoray/agent-host-protocol`, branch `ahp_python_client`
- This package lives at `clients/python/` in that repo, alongside the
  existing `clients/rust/`, `clients/go/`, `clients/typescript/`,
  `clients/kotlin/`, `clients/swift/`.
- Protocol docs: https://microsoft.github.io/agent-host-protocol/

## What's completed

| Module | Status | Built via |
|---|---|---|
| `ahp/types/` | Implemented | TDD-adjacent (types have no behavior to red/green; scaffolded then smoke-tested) |
| `ahp/reducers/` | Implemented | Red/Green TDD |
| `ahp/transport/` | Implemented **and actually executed** | Red/Green TDD, real run |
| `ahp/client.py` (`AhpClient`) | Implemented | Red/Green TDD (not executed) |
| `ahp/hosts.py` (`MultiHostClient`) | Implemented | Red/Green TDD (not executed) |

Concretely, `AhpClient` supports: `initialize`, `subscribe`, `dispatch_action`
(with write-ahead reconciliation), `reconnect` (replay vs. resnapshot,
optional transport swap), `close`, async context manager,
`authenticate`/`resource_read`/`resource_write`/`resource_list`/`resource_stat`
(client→host), and the host→client direction of `resource*` via a registered
`ResourceProvider`. `MultiHostClient` wraps N `AhpClient`s behind a
host_id-keyed registry with concurrent `initialize_all`/`close_all` and
delegating `get_state`/`dispatch_action`.

## What's NOT completed

- **`unsubscribe()`** — never implemented on `AhpClient`. Should be a small
  addition: send the `unsubscribe` command, remove the channel from
  `_channel_states`/`_last_seen_server_seq`. Not covered by any test yet.
- **`ping`** command — exists in `types/commands.py`'s `COMMANDS` registry but
  `AhpClient` never calls it. Low priority (mostly a liveness check).
- **`createSession`/`disposeSession`/`listSessions`/`createChat`/`disposeChat`/
  `createTerminal`/`disposeTerminal`/`fetchTurns`/`completions`/
  `invokeChangesetOperation`** — all have `Params`/`Result` models already
  defined in `types/commands.py` and are in the `COMMANDS` registry, but
  `AhpClient` has **no methods wrapping them**. This is probably the biggest
  gap: a real host integration needs session/chat/terminal lifecycle
  management, and right now `AhpClient` can only `subscribe` to
  already-existing channels, not create new sessions/chats/terminals. Adding
  these should be mechanical — they follow the exact same
  `_send_request(method, Params(...))` → `Result.model_validate(...)` pattern
  as `subscribe`/`dispatch_action`. Do this next, before anything fancier.
- **`StateAction` only has a seed set of variants** (a handful per channel
  family), not the full ~80-variant union the real protocol has. The
  extension pattern is documented at the top of `types/actions.py`. Adding
  more variants is mechanical but there are a lot of them.
- **`state.py` field sets are inferred, not schema-verified.** `RootState`,
  `SessionState`, `ChatState`, `TerminalState`, `ChangesetState`,
  `AnnotationsState` field sets came from spec prose + one third-party
  AHP-adjacent VS Code plugin's ported TS interfaces — not from
  `schema/*.schema.json` directly (couldn't fetch it — see "Access
  limitations" below). Treat every field name as a hypothesis to verify.
- **`errors.AhpErrorCode` values are explicit placeholders** (`-32000` through
  `-32009`, sequentially assigned) — not sourced from any authoritative
  upstream error-code table.
- **No `unsubscribe` test, no `ping` test.**
- **Open design decisions** (see SPEC.md §7 for full detail):
  - WebSocket library: `websockets>=12.0` is pinned in `pyproject.toml`'s
    optional extra, but `ahp/transport/websocket.py` is library-agnostic by
    design (only imports `websockets` lazily inside `.connect()`) — the
    choice of *default* library is still open if you want to reconsider.
  - Minimum Python version: tentatively `>=3.10`, not treated as final.

## Test coverage — what was actually run vs. what wasn't

**This is the part to read most carefully.** "Tests exist" and "tests pass"
are different claims here, and the gap matters:

| Layer | Tests written? | Actually executed? | Notes |
|---|---|---|---|
| `ahp.types` | Yes (`tests/types/test_types.py`) | **No** — `py_compile` only | Needs real pydantic install |
| `ahp.reducers` | Yes (`tests/reducers/*.py`, 6 files) | **No** — `py_compile` only | Reducer state models are pydantic; same blocker |
| `ahp.transport` | Yes (`tests/transport/*.py`, 3 files, 24 tests) | **Yes — real run, 24/24 passing** | Zero pydantic dependency, so a throwaway hand-rolled async test runner + minimal `pytest.raises`-only shim could actually execute it in-sandbox |
| `ahp.client` | Yes (`tests/client/*.py`, 4 files) | **No** — `py_compile` only, plus a static AST cross-check that every `client.method()` call in the tests resolves to a real method on `AhpClient` (no typos) | Needs real pydantic |
| `ahp.hosts` | Yes (`tests/hosts/test_multi_host_client.py`) | **No** — same as above | Needs real pydantic |

**Why pydantic couldn't be installed**: the sandbox this was built in had no
network egress at all. Tried: `pip install pydantic` (fails, no index
reachable), `uv pip install --offline` against `uv`'s local cache (nothing
cached). If your environment has network access, installing should be
trivial and is the first thing to do.

**What "actually executed" means for transport, concretely**: a ~40-line
throwaway script (`asyncio.run()` + manual iteration over `test_*` functions
in each module, with a hand-written `pytest.raises`-equivalent context
manager) ran the real test bodies against the real implementation. This
caught a genuine deadlock bug (see Gotchas below) that a purely-static review
would very plausibly have missed. That script was **not preserved** — it was
sandbox scratch work, not a deliverable, so it isn't in this repo. If you want
that level of confidence for `ahp.client`/`ahp.hosts` without a full pydantic
install, you'd need to rebuild something like it, but it's much simpler to
just install pydantic for real and run pytest normally.

## Gotchas / things that will bite you if you're not careful

1. **`InMemoryTransport.close()` had a real deadlock bug, now fixed — don't
   reintroduce the pattern elsewhere.** The original implementation only
   pushed a "closed" sentinel into the *peer's* inbound queue. It never woke
   up a `receive()` call already blocked on *this same end's own* queue. That
   matters a lot in practice: `AhpClient`'s background reader loop spends
   most of its life parked in exactly that state (`await
   self._transport.receive()` with nothing queued), so `AhpClient.close()`
   would hang forever awaiting the reader task. Fixed by having `close()`
   push the sentinel into **both** queues (the peer's inbound *and* this
   end's own inbound). If you write a new `Transport` implementation (e.g.
   `StdioTransport`), make sure its `close()` has the equivalent property:
   **any receive() already in flight on this end must be unblocked by this
   end's own close(), not just by traffic from the peer.** The regression
   test is `tests/transport/test_memory_transport.py::
   test_close_unblocks_a_receive_already_pending_on_the_same_end` — write an
   analogous test for any new transport.
2. **Write-ahead reconciliation matching is global, not per-channel.**
   `AhpClient._own_pending_client_seqs` is a single `set[int]` shared across
   all channels, keyed only by `client_seq` (which is itself a single global
   monotonic counter, not per-channel). This works because `client_seq`
   values are unique across the whole client regardless of channel, so there's
   no collision risk — but it does mean the set has **no eviction policy**.
   If a dispatched action's echo notification never arrives (e.g. dispatched
   to a channel with no other subscribers so the host has some other reason
   not to broadcast, or some protocol edge case), that `client_seq` sits in
   the set forever. Not a correctness bug today, but worth adding a cap/TTL
   or at least a metric if this client sees serious production use.
3. **`reconnect()` cancels the old reader task rather than awaiting it.** This
   is deliberate — the old transport is presumably dead/unclosed, so awaiting
   its reader task risks hanging. But it does mean the old task is never
   confirmed to have actually finished; in a real asyncio app this can
   produce "Task was destroyed but it is pending" warnings at garbage
   collection if the old task doesn't get cancelled cleanly. Worth revisiting
   with a `try/except asyncio.CancelledError` + short timeout if this bites
   in practice.
4. **The reader loop silently swallows malformed messages** (`except
   Exception: continue` around the `json.loads` + `parse_protocol_message`
   step in `_reader_loop`). No logging currently. Fine for a first pass, but
   will make debugging a real host integration harder than it needs to be —
   consider adding structured logging before shipping.
5. **Test imports rely on pytest's default rootdir-based `sys.path` behavior.**
   None of the `tests/*/` subdirectories have `__init__.py` files, and
   `tests/client/_helpers.py` is imported as a bare `from _helpers import
   ...` from sibling test files in the same directory. This works under
   pytest's default "prepend" import mode as long as you run `pytest` from
   `clients/python/` (matching `pyproject.toml`'s `testpaths = ["tests"]`).
   If you reorganize tests, add `__init__.py` files, or change
   `--import-mode`, revisit these imports.
6. **`_channel_binding()` derives the channel "kind" from a naive URI scheme
   split** (`channel.split(":", 1)[0]`) against a hardcoded dict
   (`agenthost`, `ahp-session`, `ahp-chat`, `ahp-terminal`, `ahp-changeset`,
   `ahp-annotations`). This is inferred from the README/spec's example URIs
   (`agenthost:/root`, `ahp-session:/<uuid>`, etc.), not confirmed against a
   real host. If the real scheme names differ even slightly, every
   `subscribe`/`dispatch_action`/notification-reconciliation call breaks
   silently-ish (raises `AhpClientError: unrecognized channel scheme`).
   Verify this first against a real host or the schema files.
7. **GitHub blocked automated browsing of subdirectory tree/blob pages**
   (`robots.txt`) from the sandbox this was built in — so the actual test
   suites and directory layouts of `clients/rust/`, `clients/go/`,
   `clients/typescript/` were never directly inspected. Everything here is
   based on the top-level README description plus idiomatic conventions for
   each language, not a port of the real thing. If you (or a session with
   browser access) can look at those directly, it's worth reconciling
   directory/test naming and, more importantly, double-checking the
   `state.py`/`actions.py` field sets against the real generated types.

## Do / Don't

**Do:**
- Run `pytest -v` before making any other changes. Fix red tests before
  adding features.
- Follow the existing Red/Green TDD pattern for anything new: write the
  failing test against the API you wish existed, confirm it fails for the
  right reason, then implement.
- Keep reducers pure — no I/O, no mutation of the input state
  (`model_copy(update=...)`, never in-place field assignment).
- Keep `Transport` implementations symmetric on `close()` per Gotcha #1
  above.
- Update `SPEC.md` §7/§7a/§8 and `CHANGELOG.md` as you go, the way this
  session did — they're meant to stay living documents, not a one-time
  writeup.

**Don't:**
- Don't assume anything marked "syntax-checked only" in SPEC.md §7a actually
  works until you've run it.
- Don't add new `StateAction` variants without also adding the matching
  reducer branch (see the extension pattern documented at the top of
  `types/actions.py`).
- Don't change `AhpModel`'s `extra="allow"` / `populate_by_name=True` config
  without checking every model that relies on accepting both camelCase wire
  keys and snake_case Python kwargs.
- Don't trust `state.py`/`actions.py` field names as ground truth — they're
  flagged provisional for a reason (see "What's NOT completed" above).

## Recommended order of work for the next session

1. `cd clients/python && pip install -e ".[dev]" && pytest -v`. Fix anything
   red. This is non-negotiable — everything below assumes a green baseline.
2. If you have GitHub browser/API access this session didn't have, spot-check
   `state.py` and `actions.py` field names against
   `microsoft/agent-host-protocol`'s `schema/*.schema.json` and the
   TypeScript client's generated types. Fix discrepancies.
3. Add `unsubscribe()` to `AhpClient` (small, same pattern as everything
   else) with a test.
4. Add the missing session/chat/terminal lifecycle methods
   (`create_session`, `dispose_session`, `list_sessions`, `create_chat`,
   `dispose_chat`, `create_terminal`, `dispose_terminal`, `fetch_turns`,
   `completions`, `invoke_changeset_operation`) — this is the biggest
   functional gap and is mechanical given the existing `Params`/`Result`
   models.
5. Only after 1–4: consider expanding `StateAction` toward full coverage,
   revisiting the WebSocket-library and min-Python-version open questions,
   and adding structured logging to the reader loop.

## File map

```
clients/python/
├── SPEC.md          # design plan + decision log + phase-by-phase changelog (§8)
├── CHANGELOG.md      # package-level changelog (Keep a Changelog format)
├── HANDOFF.md          # this file
├── CLAUDE.md            # working-memory pointer for Claude Code sessions
├── README.md              # user-facing package README
├── pyproject.toml
├── src/ahp/
│   ├── __init__.py        # re-exports AhpClient, MultiHostClient, etc.
│   ├── types/             # DONE, untested-at-runtime
│   ├── reducers/          # DONE, untested-at-runtime
│   ├── transport/         # DONE, ACTUALLY VERIFIED (24/24 tests, real bug found+fixed)
│   ├── client.py          # DONE except unsubscribe/session-lifecycle, untested-at-runtime
│   └── hosts.py           # DONE, untested-at-runtime
└── tests/
    ├── types/             # 1 file
    ├── reducers/          # 6 files, one per channel family
    ├── transport/         # 3 files, 24 tests — the only ones actually run
    ├── client/            # 4 files + shared _helpers.py
    └── hosts/             # 1 file
```
