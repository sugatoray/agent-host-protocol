# CLAUDE.md — clients/python

Working memory for Claude sessions picking up work in this directory
(`clients/python/` — the Python client for the Agent Host Protocol, AHP).

## Read this first, in this order

1. **[`HANDOFF.md`](./HANDOFF.md)** — **start here.** What's done, what's not,
   what was actually tested vs. only syntax-checked, known gotchas, and a
   recommended order of work. Written specifically for picking this project
   back up in a new session.
2. **[`SPEC.md`](./SPEC.md)** — the design plan and the full decision/changelog
   history (§7 open questions, §7a verification caveats, §8 phase-by-phase
   changelog). Update this as you go, the same way prior sessions did.
3. **[`CHANGELOG.md`](./CHANGELOG.md)** — package-level changelog, Keep a
   Changelog format. This client releases independently on its own
   `python/vX.Y.Z` tags, matching the Rust/Go/TypeScript/Kotlin clients in
   this repo.

## The one thing to do before anything else

**With `uv`**:

```bash
# Method-1: RECOMMENDED
cd clients/python
uv sync
uv sync --extra websocket --extra dev 
# uv sync --extra dev
# uv sync --extra websocket
uv run pytest -v
```

**With `pip`**:

```bash
# Method-2
cd clients/python
pip install -e ".[dev]"
pytest -v
```

Most of this codebase (`ahp.client`, `ahp.hosts`, `ahp.types`, `ahp.reducers`)
has never actually been executed — only `py_compile`-checked — because prior
sessions had no network access to install `pydantic`. Only `ahp.transport` has
a confirmed real green test run. See `HANDOFF.md`'s "Test coverage" section
for the exact breakdown before trusting anything.

## Conventions in this package

- Red/Green TDD throughout: write the failing test against the API you wish
  existed, confirm it fails, then implement.
- Reducers are pure: `(state, action) -> new_state`, no I/O, no in-place
  mutation (`model_copy(update=...)`).
- `Transport` is a structural `typing.Protocol`, not an ABC.
- Wire types are pydantic v2 models with `populate_by_name=True` +
  `extra="allow"`.
