# Wisdom — AHP Python Client

Standing reference for this package. Unlike `GAPANALYSIS.md` (a point-in-time diff,
gets rewritten as gaps close) and `HANDOFF.md` (a narrative "what happened last
session"), this file doesn't expire — update it when a constraint, trap, or lesson
turns out to still apply, not on a schedule.

## Constraints — respect and conform to them

- **Canonical source of truth is repo-root `types/*.ts`** (per-channel
  `channels-*/{state,actions,commands,notifications,reducer}.ts` + `common/*.ts`),
  with `schema/*.schema.json` as tie-breaker. Not spec prose, not third-party ports,
  not "what seems reasonable." Every field/variant/shape in `ahp/types/` and
  `ahp/reducers/` must trace back to it.
- **Wire models are pydantic v2** with `populate_by_name=True` + `extra="allow"`
  (`AhpModel` base). Don't change this config without checking every model that
  relies on accepting both camelCase wire keys and snake_case Python kwargs.
- **Reducers are pure**: `(state, action) -> new_state`. No I/O, no in-place
  mutation — always `model_copy(update=...)`.
- **`Transport` is a structural `typing.Protocol`**, not an ABC. New transports
  (e.g. `StdioTransport`) just need to duck-type it, not subclass anything.
- **This client releases independently** on its own `python/vX.Y.Z` tags with its
  own `CHANGELOG.md` (Keep a Changelog format), matching the Rust/Go/TypeScript/
  Kotlin clients — not tied to the overall repo version.
- **Tests assume `pytest` runs from `clients/python/`** (matches
  `pyproject.toml`'s `testpaths = ["tests"]`). None of `tests/*/` has
  `__init__.py`; `tests/client/_helpers.py` is imported bare (`from _helpers import
  ...`) relying on pytest's default "prepend" import mode. Reorganizing tests or
  changing `--import-mode` breaks this silently.

## Traps — avoid them always

- **A `Transport.close()` must unblock a `receive()` already pending on *this same
  end*, not just signal the peer.** `AhpClient`'s reader loop spends most of its
  life parked in `await self._transport.receive()`. The original
  `InMemoryTransport.close()` only pushed a sentinel into the peer's queue, so
  `AhpClient.close()` hung forever. Fixed by pushing into both queues — write an
  analogous regression test for any new transport (see
  `test_close_unblocks_a_receive_already_pending_on_the_same_end`).
- **`_own_pending_client_seqs` is one global `set[int]` with no eviction policy.**
  If a dispatched action's echo never arrives, its `client_seq` sits there forever.
  Not a correctness bug today, but don't be surprised by unbounded growth under
  real production load — add a cap/TTL before that matters.
- **`reconnect()` cancels the old reader task instead of awaiting it**, on
  purpose (the old transport is presumably dead). This can surface as "Task was
  destroyed but it is pending" warnings at GC — expected, not a new bug to chase.
- **The reader loop swallows malformed messages silently**
  (`except Exception: continue` around `json.loads` + `parse_protocol_message`).
  No logging. This will make real host-integration debugging much harder than it
  needs to be — add structured logging before depending on this in anger.
- **`_channel_binding()` infers channel "kind" from a naive URI scheme split**
  against a hardcoded dict (`agenthost`, `ahp-session`, `ahp-chat`, `ahp-terminal`,
  `ahp-changeset`, `ahp-annotations`). If a real host uses different scheme names,
  every `subscribe`/`dispatch_action`/reconciliation call fails with
  `AhpClientError: unrecognized channel scheme`. Verify against a real host or the
  schema before trusting this.
- **Don't trust a field name in `state.py`/`actions.py`/`commands.py` just because
  it's there.** A large fraction were invented from spec prose or a third-party
  port before canonical `types/*.ts` was reachable — check `GAPANALYSIS.md`'s
  current per-channel section before relying on any shape you haven't personally
  verified.

## Ditches — bad patterns or decisions to avoid

- **Don't hand-invent a field/command/notification shape when canonical
  `types/*.ts` is reachable.** This is exactly how the client accumulated dozens
  of discrepancies the first time around (see `GAPANALYSIS.md`'s original
  2026-07-06 pass — nearly every shape disagreed with canonical TS). Read the
  `.ts` file for the channel you're touching before writing the pydantic model.
- **Don't add a `StateAction` variant without its matching reducer branch** — the
  extension pattern is documented at the top of `types/actions.py`; several
  reducers currently no-op on real variants precisely because this was skipped.
  Track it in `GAPANALYSIS.md` rather than leaving it implicit.
- **Don't treat "tests pass" as "matches the protocol."** Green `pytest` only
  proves the code matches its *own* tests — if the tests were written against an
  invented shape, they'll happily stay green while disagreeing with the real wire
  format. Cross-check against `types/*.ts` explicitly; that's what
  `GAPANALYSIS.md` is for.
- **Don't layer a corrected model alongside an old wrong one "to be safe."** No
  external caller depends on this package's invented shapes yet — when
  `GAPANALYSIS.md` flags something wrong, delete and replace it, don't add a
  second parallel type.
- **Don't let `SPEC.md`/`HANDOFF.md`/`GAPANALYSIS.md` drift from the code.** They
  are living documents by convention here, not one-time writeups — update them in
  the same session as the code change that invalidates them (this file's own
  2026-07-07 rewrite happened *because* a prior session skipped this).

## Wisdom — best practices, Red/Green TDD

- **Every module in this package was built Red/Green, keep doing that.** Write
  the failing test against the API/shape you wish existed, confirm it fails for
  the right reason (not a typo or import error), then implement until it's green.
  Don't write implementation first and backfill tests.
- **Before touching a channel's `types/`/`reducers/` code, read that channel's
  section in `GAPANALYSIS.md` first.** It's the field-by-field authority, and
  it's kept current — check its date/verification note before trusting it blindly
  on a much later date.
- **Run `uv run pytest -v` for real, not `py_compile`.** This package has already
  been burned once by "syntax-checked only" being mistaken for "tested" (see
  `SPEC.md` §7a's history) — a real run has caught genuine bugs (the transport
  deadlock) that static review missed.
- **Fix one channel family at a time, cheapest/highest-value first**, per
  `GAPANALYSIS.md`'s suggested order — don't try to reconcile everything in one
  pass; that's how partial reducer coverage (session/chat/terminal/changeset all
  still have no-op branches) happens and gets lost track of.
- **When a fix touches a shared primitive** (`AhpErrorCode`, `Snapshot`,
  `ActionEnvelope`, etc.), grep for every model/reducer that references it before
  changing it — these are used across all six channel families.
