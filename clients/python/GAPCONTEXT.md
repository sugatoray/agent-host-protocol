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

---

## ChatState missing fields (origin, interactivity, workingDirectory)

**GAPANALYSIS.md section**: `chat` → State
**Priority**: low
**Status**: open (2026-07-07)

### What is missing

`ChatState` in `src/ahp/types/state.py` is missing three fields present in the
canonical `types/channels-chat/state.ts:51–69`:

- `origin: ChatOrigin | None` — how the chat was created (user-initiated, tool-
  initiated, etc.)
- `interactivity: ChatInteractivity | None` — whether the chat accepts user input
- `workingDirectory: URI | None` — working directory context for the chat

### Cross-client evidence

| Client     | Has these fields? | Location |
|------------|-------------------|----------|
| TypeScript | **yes** | `types/channels-chat/state.ts:51–69` |
| Go         | **yes** | `clients/go/ahptypes/state.generated.go` |
| Rust       | **yes** | `clients/rust/crates/ahp-types/src/state.rs` |
| Python     | **no** | `src/ahp/types/state.py` (`ChatState`) |

### Why it matters

These fields are metadata about the chat's context, not its runtime state.
Missing them means:

1. A client rendering a chat list (e.g. to show which chats accept input) cannot
   check `chat.interactivity` — it must fall back to the raw extra fields dict via
   pydantic's `extra="allow"` leak-through, which is untyped and fragile.
2. `origin` is needed to distinguish agent-initiated chats from user-initiated
   ones — relevant for filtering or grouping in a UI.
3. `workingDirectory` is displayed in some host UIs alongside the chat title.

These are depth choices today (existing code works without them) but become
protocol gaps if the Python client is ever used to drive a real host UI.

### Canonical shape

```typescript
// types/channels-chat/state.ts:51–69 (abbreviated)
interface ChatState {
  // ... existing fields ...
  origin?: ChatOrigin;               // 'user' | 'agent' | ...
  interactivity?: ChatInteractivity; // 'interactive' | 'background'
  workingDirectory?: URI;
}
```

---


## ChatToolCallConfirmedAction subtype split

**GAPANALYSIS.md section**: `chat` → Actions
**Priority**: medium
**Status**: open (2026-07-07)

### What is missing

`ChatToolCallConfirmedAction` in `src/ahp/types/actions.py` uses `approved: bool`
as a flat field. The canonical TS protocol defines this as two distinct action
subtypes with different field sets, discriminated on `approved`:

- `ChatToolCallApprovedAction` (`approved: true`) — carries a `confirmed` field
- `ChatToolCallDeniedAction` (`approved: false`) — carries a `reason?: string` field

### Cross-client evidence

| Client     | Has the subtype split? | Location |
|------------|------------------------|----------|
| TypeScript | **yes** — discriminated union | `types/channels-chat/actions.ts:226–271` |
| Go         | **yes** | `clients/go/ahptypes/state.generated.go` |
| Rust       | **yes** — enum variants | `clients/rust/crates/ahp-types/src/state.rs` |
| Python     | **no** — flat `approved: bool` | `src/ahp/types/actions.py` |

### Why it matters

1. A denied tool-call carries a `reason` string (the host's explanation). Python
   code that wants to surface this reason to the user cannot access it — it's
   not a field on the current model.
2. An approved tool-call carries a `confirmed` field used for audit/logging. Same
   problem.
3. The flat `approved: bool` approach works for routing (approved vs. denied) but
   loses the payload that makes the action useful to a real application.

### Canonical shape

```typescript
// types/channels-chat/actions.ts:226–271 (abbreviated)
type ChatToolCallConfirmedAction =
  | { type: 'chat/toolCallConfirmed'; turnId: string; toolCallId: string;
      approved: true; confirmed: ToolCallConfirmation }
  | { type: 'chat/toolCallConfirmed'; turnId: string; toolCallId: string;
      approved: false; reason?: string };
```

---

## SessionMcpServerStateChangedAction reducer

**GAPANALYSIS.md section**: `session` → Reducer
**Priority**: low
**Status**: open (deliberate no-op, 2026-07-07)

### What is missing

`SessionMcpServerStateChangedAction` in `reducers/session.py` deliberately no-ops.
The canonical TS reducer (`types/channels-session/reducer.ts:278–329`) updates the
matching entry in `state.customizations` — specifically the
`ServerToolsCustomization` sub-shape that tracks per-MCP-server tool enable/disable
state.

### Cross-client evidence

The canonical TS reducer is the reference; Go and Rust reducers are not shipped
(reducers are a Python/TS concept only — Go and Rust delegate state management to
the application layer).

### Why it matters

Without this reducer branch, subscribing to a session and receiving
`session/mcpServerStateChanged` actions leaves the local `SessionState.customizations`
stale. Any UI that shows MCP server connection status or enabled tools will show
outdated data. This only matters if:

1. The application displays MCP server state, AND
2. The application uses the Python client's local `SessionState` copy rather than
   re-fetching on demand.

If neither is true, the no-op is harmless.

### Canonical shape

```typescript
// types/channels-session/reducer.ts:278–329 (logic summary)
// Find the ServerToolsCustomization in state.customizations by serverId,
// then update its connectionState / tools fields.
```

Full implementation requires modeling `ServerToolsCustomization` shape first
(currently `dict[str, Any]` in `SessionState.customizations`).

---

## Closed Gaps

Entries below were open gaps that have been resolved. Kept for historical
context — the rationale and cross-client evidence remain valid reference
material for understanding the protocol shape.

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
