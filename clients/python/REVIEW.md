# Code Review Instruction

Run a thorough code review of the `clients/python` implementation by comparing it with `clients/{{ x }}`, where {{ x }} is `typescript` [**RECOMMENDED] or `rust` or `go`.

Provide a detailed analysis, in a tabular form inside the folder `clients/python/reviews` and add files named as `code_review_{{ yyyymmdd }}_{{ latest_gitsha }}_{{ reference_gitsha }}.md`.

Use only **first 8 characters** of the gitsha for `latest_gitsha` nd `reference_gitsha`.

At the very top add a `**REVIEWER**`: Codex/Claude/Gemini/Human/OtherAI.

Based on who is doing the code review, and updating this file, this field should be manually validated before closing the review.
