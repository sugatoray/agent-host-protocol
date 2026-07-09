---
name: review-python-vs-typescript
description: Use when asked to review the Python AHP client implementation, compare it against a reference client (TypeScript/Rust/Go), or generate a code_review_*.md artifact in clients/python/reviews/. Triggers on phrases like "run a code review", "compare python to typescript", or a user supplying a reference_gitsha with .scrolls/REVIEW.md.
---

# Python Client Code Review

## Overview

Structured parity review of `clients/python` against a reference AHP client, producing a severity-ranked findings artifact in `clients/python/reviews/`.

## Reference Client Priority

TypeScript → Rust → Go (first available; TypeScript is the canonical reference per `.scrolls/REVIEW.md`)

## Step-by-Step

1. **Determine SHAs** (first 8 chars each):
   ```bash
   git rev-parse HEAD | cut -c1-8          # latest_gitsha
   git rev-parse <ref> | cut -c1-8         # reference_gitsha (user-supplied or same as latest)
   ```

2. **Run tests** and record the exact result:
   ```bash
   cd clients/python && uv run pytest -v   # preferred
   # fallback: pip install -e ".[dev]" && pytest -v
   ```

3. **Name the output file**:
   ```
   clients/python/reviews/code_review_{yyyymmdd}T{HHMMSS}_L_{latest_gitsha}_R_{reference_gitsha}.md
   ```
   Timestamp = when the file is first generated (`YYYY-MM-DD HH:MM:SS` → compact form for filename).

## Output Structure (sections in this order)

```md
**REVIEWER**: Codex/Claude/Gemini/Human/OtherAI
**TIMESTAMP-GENERATED**: YYYY-MM-DD HH:MM:SS

# Python Client Code Review

Reviewed `clients/python` at `{latest_gitsha}` against the {reference} client,
using `{reference_gitsha}` as the requested reference SHA.

## REVIEW SUMMARY TABLE
| Area | Python coverage | TypeScript reference | Assessment | Priority |

## Scope And Baseline
| Item | Result |
# Rows: latest SHA, reference SHA, comparison client, test command, test result, files emphasized

## Detailed Findings
| Severity | Finding | Evidence | Impact | Recommendation |

## Positive Observations
| Area | Observation |

## Suggested Follow-Up Order
| Order | Work item | Rationale |

## Manual Validation
| Field | Value |
# Rows: Reviewer field manually validated, Timestamp field manually validated, Test baseline recorded
```

## Evidence Format

Always cite both Python and reference paths with line numbers:
```
Python: `src/ahp/client.py:502-516`
TypeScript: `../typescript/src/client/client.ts:183-190`
```

## REVIEW SUMMARY TABLE — Row Topics

Cover these feature areas (one row each):
- Core JSON-RPC request/response loop
- Subscriptions and inbound notifications
- Reconnect
- Multi-host API
- Transports
- Generated/public types and reducers
- Tests

Columns: Python coverage | TypeScript reference | Assessment | Priority (High/Medium/Low)

## Common Mistakes

| Mistake | Fix |
|---|---|
| Full gitsha in filename | Truncate to first 8 chars |
| Skipping test run | Always record the actual result (`N passed`) |
| Omitting positive observations | Required section — parity strengths matter |
| No line numbers in evidence | Include `file:line-range` for both sides |
| Wrong timestamp format | `YYYY-MM-DD HH:MM:SS` in header; compact in filename |
| Missing Manual Validation section | Always close with it; set fields to Yes/No |
