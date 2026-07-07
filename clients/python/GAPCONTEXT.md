# Gap Context — AHP Python Client

> **Purpose**: this file records *why* each gap identified in
> [`GAPANALYSIS.md`](./GAPANALYSIS.md) is necessary to fix — cross-client
> evidence, protocol impact, and which real-world scenarios break if the gap
> stays open. `GAPANALYSIS.md` answers *what* is wrong and *where* in the
> code; this file answers *why it matters* before you decide whether to act.
>
> **When to update**:
> - **New gap**: add an entry under "Open Gaps" whenever a gap is identified
>   that isn't self-evidently "just match the TS shape."
> - **Gap closed (pass 1)**: mark `Status: closed (date)` in the entry.
> - **Gap closed (pass 2)**: move the entry from "Open Gaps" to "Closed Gaps"
>   at the bottom, and update `SPEC.md §8` with the closure.

---

## Template for new entries

```
## <GapName>

**GAPANALYSIS.md section**: <section heading>
**Priority**: high | medium | low
**Status**: open | in-progress | closed (date)

### What is missing
<One paragraph: what the Python client does vs. what canonical TS specifies.>

### Cross-client evidence
| Client     | Has it? | Location |
|------------|---------|----------|
| TypeScript | yes/no  | path:line |
| Go         | yes/no  | path:line |
| Rust       | yes/no  | path:line |
| Python     | **no**  | — |

### Why it matters
<What breaks or degrades if this stays unimplemented.>

### Canonical shape
<Minimal reproduction of the TS interface / Go struct / Rust struct that Python should mirror.>
```

---

## Open Gaps

*All identified gaps are now closed.*

---

## Closed Gaps

Entries below were open gaps that have been resolved. Kept for historical
context — the rationale and cross-client evidence remain valid reference
material for understanding the protocol shape.

---

## ChatState missing fields (origin, interactivity, workingDirectory)

**GAPANALYSIS.md section**: `chat` → State
**Priority**: low
**Status**: closed (2026-07-07)
**Closed in**: SPEC.md v15 · `tests/types/test_chat_state_fields.py` (10 tests) · suite 257/257

### What was missing

`ChatState` was missing `origin`, `interactivity`, and `workingDirectory`
from `types/channels-chat/state.ts:51–69`. All three are present in TypeScript,
Go, and Rust clients.

### Cross-client evidence

| Client     | Has these fields? | Location |
|------------|-------------------|----------|
| TypeScript | **yes** | `types/channels-chat/state.ts:51–69` |
| Go         | **yes** | `clients/go/ahptypes/state.generated.go` |
| Rust       | **yes** | `clients/rust/crates/ahp-types/src/state.rs` |
| Python     | **was no** → now yes | `src/ahp/types/state.py` |

### Fix applied

```python
class ChatState(AhpModel):
    origin: dict[str, Any] | None = None          # ChatOrigin tagged union
    interactivity: str | None = None              # 'full'|'read-only'|'hidden'
    working_directory: str | None = Field(default=None, alias="workingDirectory")
```

---

## SessionMcpServerStateChangedAction reducer

**GAPANALYSIS.md section**: `session` → Reducer
**Priority**: low
**Status**: closed (2026-07-07)
**Closed in**: SPEC.md v15 · `tests/reducers/test_session_mcp_reducer.py` (9 tests) · suite 257/257

### What was missing

`SessionMcpServerStateChangedAction` in `reducers/session.py` deliberately no-oped.
The canonical TS reducer (`types/channels-session/reducer.ts:278–329`) updates
`state` and `channel` on the matching `McpServerCustomization` entry (top-level
or nested child).

### Fix applied

```python
# Searches state.customizations by action.id at top-level, then in children.
# Updates {"state": action.state, "channel": action.channel} on the matched entry.
# Returns state unchanged if no match or if customizations is None/empty.
# Immutable: builds new list/dict, never mutates in place.
```

---

## ChatToolCallConfirmedAction subtype split

**GAPANALYSIS.md section**: `chat` → Actions
**Priority**: medium
**Status**: closed (2026-07-07)
**Closed in**: SPEC.md v14 · `tests/types/test_chat_actions.py` (24 tests) · suite 240/240

### What was missing

`ChatToolCallConfirmedAction` used `approved: bool` as the only discrimination point.
The canonical TS protocol defines two distinct action subtypes (`ChatToolCallApprovedAction`,
`ChatToolCallDeniedAction`) with non-overlapping fields: `confirmed` (approved path) and
`reason`/`reason_message`/`user_suggestion` (denied path).

### Cross-client evidence

| Client     | Has the subtype split? | Location |
|------------|------------------------|----------|
| TypeScript | **yes** — discriminated union | `types/channels-chat/actions.ts:226–271` |
| Go         | **yes** | `clients/go/ahptypes/state.generated.go` |
| Rust       | **yes** — enum variants | `clients/rust/crates/ahp-types/src/state.rs` |
| Python     | **was no** → now yes (flat + typed subtypes) | `src/ahp/types/actions.py` |

### Fix applied

```python
# ChatToolCallConfirmedAction — union member, now holds all fields:
class ChatToolCallConfirmedAction(AhpModel):
    approved: bool
    confirmed: str | None = None          # ToolCallConfirmationReason (approved=True)
    edited_tool_input: str | None = None
    reason: str | None = None             # ToolCallCancellationReason (approved=False)
    user_suggestion: Any | None = None
    reason_message: Any | None = None
    selected_option_id: str | None = None

# Typed convenience subtypes for construction/dispatch:
class ChatToolCallApprovedAction(AhpModel):
    approved: Literal[True] = True
    confirmed: str  # required

class ChatToolCallDeniedAction(AhpModel):
    approved: Literal[False] = False
    reason: str   # required
```

---

## Turn.state type

**GAPANALYSIS.md section**: `chat` → State
**Priority**: low
**Status**: closed (2026-07-07)
**Closed in**: SPEC.md v13 · `tests/types/test_turn_state.py` (7 tests) · suite 231/231

### What was missing

`Turn.state` in `src/ahp/types/state.py` defaulted to `{"type": "running"}` (a dict).
Canonical TS defines `TurnState` as `'complete' | 'cancelled' | 'error'` — a string
enum. In-progress turns are the separate `ActiveTurn` type and do not appear in
`ChatState.turns` at all; `"running"` is not a valid `TurnState` value.

### Cross-client evidence

| Client     | `Turn.state` type | Location |
|------------|-------------------|----------|
| TypeScript | `'complete' \| 'cancelled' \| 'error'` (string) | `types/channels-chat/state.ts:477–481` |
| Go         | `string` | `clients/go/ahptypes/state.generated.go` |
| Rust       | `TurnState` enum | `clients/rust/crates/ahp-types/src/state.rs` |
| Python     | **was** `dict` defaulting to `{"type":"running"}` → now `Literal` | `src/ahp/types/state.py` |

### Fix applied

```python
# state.py
state: Literal["complete", "cancelled", "error"]  # was dict[str, Any]

# reducers/chat.py — architectural correction:
# ChatTurnStartedAction → stores in active_turn dict (ActiveTurn shape), not turns
# ChatDeltaAction       → appends to active_turn["responseParts"]
# ChatTurnCompleteAction/CancelledAction/ChatErrorAction
#   → builds Turn(state="complete"|"cancelled"|"error") from active_turn, appends to turns

# ChatState.active_turn type corrected from str | None → dict[str, Any] | None
```

---

## TelemetryCapabilities in InitializeResult

**GAPANALYSIS.md section**: `otlp`
**Priority**: medium
**Status**: closed (2026-07-07)
**Closed in**: SPEC.md v12 · `tests/types/test_telemetry.py` (6 tests) · suite 220/220

### What was missing

`InitializeResult.telemetry` in `src/ahp/types/commands.py` was typed as
`dict[str, Any]`. The canonical protocol defines `TelemetryCapabilities` as a
first-class struct with three optional URI fields (`logs`, `traces`, `metrics`),
each pointing to an OTLP channel the host streams notifications on. Python was
the only client that left this untyped.

### Cross-client evidence

| Client     | Has `TelemetryCapabilities`? | Location |
|------------|------------------------------|----------|
| TypeScript | **yes** | `types/channels-otlp/state.ts:35–68` |
| Go         | **yes** | `clients/go/ahptypes/state.generated.go:2922` |
| Rust       | **yes** | `clients/rust/crates/ahp-types/src/state.rs:3551` |
| Python     | **was no** → now yes | `src/ahp/types/commands.py` |

### Why it mattered

1. Callers had to manually extract `result["telemetry"]["logs"]` from a raw dict —
   no IDE completion, no validation, no guard against malformed host responses.
2. The `logs` URI may be an RFC 6570 template (`ahp-otlp://logs/{level}`); a raw
   `dict` hid this distinction entirely.
3. `initialize_result.telemetry.logs` would `AttributeError` at runtime.

### Fix applied

```python
class TelemetryCapabilities(AhpModel):
    logs: URI | None = None
    traces: URI | None = None
    metrics: URI | None = None

class InitializeResult(AhpModel):
    # ...
    telemetry: TelemetryCapabilities | None = None  # was dict[str, Any] | None
```
