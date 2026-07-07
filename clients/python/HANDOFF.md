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
- **2026-07-06: first real pydantic run — 94/94 passing.** Fixed one genuine
  bug: `ahp/types/__init__.py` only re-exported `COMMANDS`, not the individual
  `Params`/`Result` models, so `test_resource_provider.py` failed at import.
- **2026-07-06 (later): field-by-field diff against canonical `types/*.ts`.**
  Result: nearly every state field, action variant, command param/result shape,
  notification shape, and every error-code value disagreed with canonical TS.
  Written up in [`GAPANALYSIS.md`](./GAPANALYSIS.md).
- **2026-07-07 (commit `8fceda9`): bulk reconciliation.** Rewrote most of
  `ahp/types/` and all of `ahp/reducers/` against canonical `types/*.ts`. Suite:
  127/127 passing. GAPANALYSIS.md re-verified and rewritten with the narrower
  remaining gap list.
- **2026-07-07 (this session): all five GAPANALYSIS.md priorities closed.**
  Suite: 213/213. See SPEC.md v11 and GAPANALYSIS.md for detail.
- **2026-07-07: `TelemetryCapabilities` closed, `ping` + logging added.**
  Suite: 220/220. See SPEC.md v12. `GAPCONTEXT.md` introduced.
- **2026-07-07: `Turn.state` type fixed + chat reducer architectural correction.**
  Suite: **231/231**. See SPEC.md v13. `Turn.state` is now
  `Literal["complete","cancelled","error"]`; in-progress turns live in
  `ChatState.active_turn` (dict), not `turns`.
- **2026-07-07: `ChatToolCallConfirmedAction` subtype split closed.**
  Suite: **240/240**. See SPEC.md v14. Added `confirmed`, `reason`, `reason_message`,
  `user_suggestion`, `edited_tool_input`, `selected_option_id` fields.
  `ChatToolCallApprovedAction` and `ChatToolCallDeniedAction` added as typed helpers.

## Repo context

- Upstream: `microsoft/agent-host-protocol`
- Working fork: `sugatoray/agent-host-protocol`, branch `ahp_python_client_02`
- This package lives at `clients/python/` alongside `clients/rust/`, `clients/go/`,
  `clients/typescript/`, `clients/kotlin/`, `clients/swift/`.
- Protocol docs: https://microsoft.github.io/agent-host-protocol/

## What's completed

| Module | Status |
|---|---|
| `ahp/types/` | Complete and verified — all shapes match canonical `types/*.ts` |
| `ahp/reducers/` | Complete — all channel reducers handle all canonical action variants |
| `ahp/transport/` | Complete and verified — 24/24 tests, real deadlock bug found+fixed |
| `ahp/client.py` (`AhpClient`) | Complete — full lifecycle, reconnect, resource*, auth |
| `ahp/hosts.py` (`MultiHostClient`) | Complete — N-host fan-out, concurrent init/close |

`AhpClient` supports: `initialize`, `subscribe`, `unsubscribe`, `dispatch_action`
(write-ahead reconciliation), `reconnect` (replay vs. resnapshot, optional transport
swap), `close`, async context manager, `create_session`/`create_chat`/
`create_terminal` (returns client-generated URI), `dispose_session`/`dispose_chat`/
`dispose_terminal`, `list_sessions`, `fetch_turns`, `completions`,
`invoke_changeset_operation`, `authenticate`, `resource_read`/`resource_write`/
`resource_list`/`resource_stat`, host→client `resource*` via registered
`ResourceProvider`, and `ping` (liveness check).

## What's NOT completed

The mechanically-fixable gaps in `GAPANALYSIS.md` are all done. What remains
is intentional laxity or depth choices — open when the need arises:

- **`ChatState` missing fields** — `origin`, `interactivity`, `workingDirectory`
  (`types/channels-chat/state.ts:51-69`). Add when needed.
- **`ChatToolCallConfirmedAction` subtype split** — **DONE** (2026-07-07).
  `ChatToolCallConfirmedAction` now carries all subtype fields; `ChatToolCallApprovedAction`
  and `ChatToolCallDeniedAction` added as typed construction helpers.
- **`SessionMcpServerStateChangedAction` reducer** — deliberately no-ops. TS updates
  matching customization entries; implement when MCP tools are used.
- **Chat reducer coverage** — 17 of 24 variants no-op. Fine — canonical TS has no
  `channels-chat/reducer.ts` at all.
- **WebSocket library choice** — `websockets>=12.0` pinned in optional extra but the
  transport is library-agnostic. Revisit if needed.
- **Minimum Python version** — tentatively `>=3.10`, not final.

## Test coverage

| Layer | Tests | Count | Notes |
|---|---|---|---|
| `ahp.types` | `tests/types/` — 4 files | ~70 tests | Includes dedicated files for commands, notifications, chat actions |
| `ahp.reducers` | `tests/reducers/` — 7 files | ~80 tests | One per channel family + resource-watch |
| `ahp.transport` | `tests/transport/` — 3 files | 24 tests | |
| `ahp.client` | `tests/client/` — 5 files + `_helpers.py` | ~30 tests | |
| `ahp.hosts` | `tests/hosts/` — 1 file | 11 tests | |

**Full suite: `uv run pytest -v` → 240 passed (2026-07-07).**

## Gotchas — things that will bite you if you're not careful

1. **`Transport.close()` must unblock a `receive()` already pending on *this same
   end*, not just signal the peer.** `AhpClient`'s reader loop spends most of its
   life parked in `await self._transport.receive()`. The original
   `InMemoryTransport.close()` only pushed a sentinel into the peer's queue so
   `AhpClient.close()` hung forever. Fixed by pushing into both queues. Write an
   analogous regression test for any new transport (see
   `test_close_unblocks_a_receive_already_pending_on_the_same_end`).

2. **Write-ahead reconciliation (`_own_pending_client_seqs`) has no eviction
   policy.** It's a single global `set[int]` across all channels. If a dispatched
   action's echo never arrives, that `client_seq` sits there forever. Not a
   correctness bug today, but worth a cap/TTL under heavy production load.

3. **`reconnect()` cancels the old reader task instead of awaiting it.** The old
   transport is presumably dead, so awaiting risks hanging. Side effect: "Task was
   destroyed but it is pending" GC warnings — expected, not a new bug.

4. **The reader loop silently swallows malformed messages** (`except Exception:
   continue` around `json.loads` + `parse_protocol_message`). No logging. Will make
   real host-integration debugging painful — add structured logging before shipping.

5. **Test imports rely on pytest's default `sys.path` behavior.** None of
   `tests/*/` has `__init__.py`; `tests/client/_helpers.py` is imported bare
   (`from _helpers import ...`). Reorganizing tests or changing `--import-mode`
   breaks this silently.

6. **`_channel_binding()` infers channel kind from a naive URI scheme split** against
   a hardcoded dict. If a real host uses different scheme names, every
   `subscribe`/`dispatch_action`/reconciliation call fails silently-ish. Verify
   scheme names against a live host before deploying.

7. **`ChatSummary` identity field is `resource`, not `uri`.** The canonical
   `types/channels-chat/state.ts:118-121` uses `resource`. If you add any code that
   filters a list of chat summaries, filter by `.get("resource")`. The session
   reducer's `chatRemoved` handler was burned by this (was filtering on `"uri"` for
   a long time while tests passed because both test data and reducer used the same
   wrong key — only caught when compared against canonical TS).

8. **Terminal content parts are `{type: "command", ...}` or `{type: "unclassified",
   value}`, never `{type: "data", data}`.** The original terminal reducer used an
   invented `"data"` part type. If you add terminal content handling anywhere, use
   the canonical shapes from `types/channels-terminal/reducer.ts:17-28`.

9. **`create*` commands return `null` in the protocol — the URI is client-generated.**
   `createSession`/`createChat`/`createTerminal` all have `result: null` in canonical
   TS. The client generates the URI via `uuid.uuid4()` before sending, passes it as
   the `channel` param, and returns it to the caller. Don't look for the URI in the
   JSON-RPC response — it won't be there.

## Do / Don't

**Do:**
- Run `uv run pytest -v` before making any other changes.
- Follow Red/Green TDD: write the failing test first, confirm it fails for the right
  reason, then implement.
- Keep reducers pure — `model_copy(update=...)`, never in-place field assignment.
- Keep `Transport.close()` symmetric per Gotcha #1.
- Update `SPEC.md §8`, `GAPANALYSIS.md`, `HANDOFF.md`, `WISDOM.md`, and
  `CHANGELOG.md` in the same session as the code changes that affect them.
- Read the relevant `types/channels-*/` TS source before modeling any new type.

**Don't:**
- Don't add `StateAction` variants without the matching reducer branch.
- Don't change `AhpModel`'s `extra="allow"` / `populate_by_name=True` without
  checking every downstream model.
- Don't invent field names — check `types/*.ts` first.
- Don't add a parallel "corrected" model alongside a wrong one — delete and replace.

## Recommended next steps

All canonical protocol gaps are closed. Remaining work is optional or on-demand:

1. **Integration test against a live AHP host** — verify URI scheme names,
   `create*` round-trips, and reconnect behavior against a real server.
2. **`ChatToolCallConfirmedAction` subtype split** — add `reason`/`confirmed` fields
   when tool-call denial reasons need to be surfaced (see `GAPCONTEXT.md`).
3. **Packaging** — `python/vX.Y.Z` tag, PyPI, CI/CD (GitHub Actions with OIDC
   Trusted Publishing matching the TS Azure DevOps pattern).
4. **Finalize open questions** in `SPEC.md §7`: WebSocket library, min Python version.

## File map

```
clients/python/
├── SPEC.md          # design plan + decision log + phase-by-phase changelog (§8)
├── GAPANALYSIS.md   # field-by-field diff vs. canonical types/*.ts — FULLY CLOSED
├── WISDOM.md        # constraints/traps/ditches/best-practices — standing reference
├── CHANGELOG.md     # package-level changelog (Keep a Changelog format)
├── HANDOFF.md       # this file
├── CLAUDE.md        # working-memory pointer for Claude Code sessions
├── README.md        # user-facing package README
├── pyproject.toml
├── src/ahp/
│   ├── __init__.py        # re-exports AhpClient, MultiHostClient, etc.
│   ├── types/             # COMPLETE — all shapes match canonical types/*.ts
│   │   ├── common.py
│   │   ├── commands.py
│   │   ├── actions.py
│   │   ├── state.py
│   │   ├── notifications.py
│   │   ├── errors.py
│   │   └── jsonrpc.py
│   ├── reducers/          # COMPLETE — all channel families, all canonical variants
│   │   ├── root.py
│   │   ├── session.py
│   │   ├── chat.py
│   │   ├── terminal.py
│   │   ├── changeset.py
│   │   ├── annotations.py
│   │   └── resource_watch.py
│   ├── transport/         # COMPLETE + VERIFIED (real deadlock found+fixed)
│   │   ├── base.py
│   │   └── websocket.py
│   ├── client.py          # COMPLETE — full AhpClient lifecycle
│   └── hosts.py           # COMPLETE — MultiHostClient
└── tests/
    ├── types/             # 4 files (~70 tests)
    ├── reducers/          # 7 files (~80 tests)
    ├── transport/         # 3 files (24 tests)
    ├── client/            # 5 files + _helpers.py (~30 tests)
    └── hosts/             # 1 file (11 tests)
```
