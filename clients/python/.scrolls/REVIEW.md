# Code Review Instruction

Run a thorough code review of the `clients/python` implementation by comparing it with `clients/{{ x }}`, where {{ x }} is `typescript` [**RECOMMENDED] or `rust` or `go`.

## NOTES-A

Provide a detailed analysis, in a tabular form inside the folder `clients/python/reviews` and add files named as `code_review_{{ yyyymmdd }}T{{ HHMMSS }}_L_{{ latest_gitsha }}_R_{{ reference_gitsha }}.md`.

Use only **first 8 characters** of the gitsha for `latest_gitsha` and `reference_gitsha`.

### Review comparison target

Use `clients/typescript` unless the user explicitly requests another client.
If TypeScript is unavailable or materially behind the current protocol surface,
fall back to `clients/rust`, then `clients/go`.

### Review content expectations

Include:

- The exact latest SHA, reference SHA, and comparison client.
- The test command run and result.
- A severity-ranked findings table with evidence, impact, and recommendation.
- A short positive-observations section so parity strengths are captured too.
- A follow-up order table for actionable next steps.

When citing evidence, include file paths and line numbers where practical.

## NOTES-B

At the very top add a `**REVIEWER**`: Codex/Claude/Gemini/Human/OtherAI.

Add a `**TIMESTAMP-GENERATED**`: `YYYY-MM-DD HH:MM:SS` at the top showing when the file `code_review_{{ ... }}.md` was first generated.

Based on who is doing the code review, and updating this file, this field should be manually validated before closing the review.

## NOTES-C

Add a summary section showing the coverage of the review and most important aspects that a seasoned/experienced code-reviewer would add.

```md
## REVIEW SUMMARY TABLE

...
```

## Example of how to prompt with this `REVIEW.md` file.

```text
with reference_gitsha="a1fc2bc0aa273dd52cac89ae51c3f84819c1604a", use the instruction from REVIEW.md
```
