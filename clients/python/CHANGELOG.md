# Changelog

All notable changes to the AHP Python client will be documented here. Follows
[Keep a Changelog](https://keepachangelog.com/) conventions; this client releases
independently on its own `python/vX.Y.Z` tags, per the convention used by the
Rust/Go/TypeScript/Kotlin clients in this repo.

## [Unreleased]

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
