# CLAUDE.md — clients/python

Working memory for Claude sessions picking up work in this directory
(`clients/python/` — the Python client for the Agent Host Protocol, AHP).

## Read this first, in this order

**[`STARTER.md`](./STARTER.md)** -- READ THIS FIRST and then follow steps as below.

1. **[`HANDOFF.md`](./HANDOFF.md)** — **start here.** What's done, what's not,
   what was actually tested vs. only syntax-checked, known gotchas, and a
   recommended order of work. Written specifically for picking this project
   back up in a new session.
2. **[`GAPANALYSIS.md`](./GAPANALYSIS.md)** — **read before touching
   `types/` or `reducers/`.** A field-by-field diff of this client's
   types/reducers against the canonical protocol source (repo-root
   `types/*.ts`, `schema/*.schema.json`). The current source of truth for
   what to fix next and in what order.
3. > **[`GAPCONTEXT.md`](./GAPCONTEXT.md)** — **⚠ read this before deciding
   > whether a gap in `GAPANALYSIS.md` is worth fixing.** For each remaining
   > gap, this file records *why* it matters: cross-client evidence (does
   > TypeScript/Go/Rust have it?), what breaks or degrades without it, and
   > the canonical shape to model. `GAPANALYSIS.md` tells you *what* is
   > wrong; `GAPCONTEXT.md` tells you *why it's necessary*. When you see a
   > gap in `GAPANALYSIS.md`, check here first before writing a single line
   > of code — the context may change the priority or the approach.
4. **[`SPEC.md`](./SPEC.md)** — the design plan and the full decision/changelog
   history (§7 open questions, §7a verification caveats, §8 phase-by-phase
   changelog). Update this as you go, the same way prior sessions did.
5. **[`CHANGELOG.md`](./CHANGELOG.md)** — package-level changelog, Keep a
   Changelog format. This client releases independently on its own
   `python/vX.Y.Z` tags, matching the Rust/Go/TypeScript/Kotlin clients in
   this repo.
6. **[`WISDOM.md`](./WISDOM.md)** — constraints, traps, ditches, and best
   practices specific to this package, plus the Red/Green TDD conventions.
   Read before writing new code, not just before debugging.

## The one thing to do before anything else

**With `uv`**:

```bash
# Method-1: RECOMMENDED
cd clients/python
uv sync
uv sync --extra websocket --extra dev --extra agent
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

As of 2026-07-07 the full suite is **257/257 passing** (`uv run pytest -v`) —
`ahp.client`, `ahp.hosts`, `ahp.types`, `ahp.reducers`, and `ahp.transport`
are all executed. See `HANDOFF.md`'s "Test coverage" section for detail.
**Green here means the code matches its own tests, not that it matches the
protocol** — see `GAPANALYSIS.md` (what's wrong) and `GAPCONTEXT.md` (why
each remaining gap matters).

## Conventions in this package

- Red/Green TDD throughout: write the failing test against the API you wish
  existed, confirm it fails, then implement.
- Reducers are pure: `(state, action) -> new_state`, no I/O, no in-place
  mutation (`model_copy(update=...)`).
- `Transport` is a structural `typing.Protocol`, not an ABC.
- Wire types are pydantic v2 models with `populate_by_name=True` +
  `extra="allow"`.
