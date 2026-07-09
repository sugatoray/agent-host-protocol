---
description: Update SPEC/GAPANALYSIS/GAPCONTEXT/HANDOFF and write/update WISDOM.md for the Python client
---

Update `.scrolls/SPEC.md`, `.scrolls/GAPANALYSIS.md` (and `.scrolls/GAPCONTEXT.md`), `.scrolls/HANDOFF.md` and
add/update `.scrolls/WISDOM.md` in this directory (`clients/python/`).

`.scrolls/WISDOM.md` must contain project-specific:

- **Constraints**: things to respect and conform to.
- **Traps**: things to always avoid.
- **Ditches**: bad patterns or decisions to avoid.
- **Wisdom**: best practices to adopt within the Python client, alongside
  Red/Green TDD.

> **NOTE — gap-closure two-pass workflow**:
> `.scrolls/GAPANALYSIS.md` records *what* each gap is; `.scrolls/GAPCONTEXT.md` records *why*
> it matters (cross-client evidence, what breaks without it, canonical shape).
>
> When a gap is closed:
>
> **Pass 1** — implement (Red → Green TDD), then mark the entry in
> `.scrolls/GAPCONTEXT.md` as `Status: closed (date)`. Commit.
>
> **Pass 2** — move the entry from "Open Gaps" to "Closed Gaps" in
> `.scrolls/GAPCONTEXT.md`. Update `.scrolls/SPEC.md §8` with a changelog entry describing the
> fix. Strike through or annotate the item in `.scrolls/GAPANALYSIS.md`. Update
> `.scrolls/HANDOFF.md` test count and "What's NOT completed". Commit.
>
> Never skip pass 2 — stale open entries in `.scrolls/GAPCONTEXT.md` mislead the next
> session about what remains.
