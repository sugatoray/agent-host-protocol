# AHP Python Client (work in progress)

Python client for the [Agent Host Protocol](https://microsoft.github.io/agent-host-protocol/) (AHP).

> **Status:** feature-complete scaffold — `types`, `reducers`, `transport`,
> `client`, and `hosts` are all implemented via Red/Green TDD. **`ahp.client`
> and `ahp.hosts` have never actually been run** (no network to install
> pydantic in the sandbox this was built in) — run `pytest` before relying on
> them. See [`SPEC.md`](./SPEC.md) §7a and `CHANGELOG.md` for exactly what's
> verified vs. not.

## What's here

```
src/ahp/
├── __init__.py        # re-exports AhpClient, MultiHostClient, etc.
├── types/              # wire types (pydantic v2)
│   ├── common.py        # URI, Snapshot, ActionEnvelope, ActionOrigin, ContentRef, capabilities
│   ├── errors.py         # AhpError, JSON-RPC + AHP error codes
│   ├── jsonrpc.py         # JsonRpcRequest/Response/Notification envelope
│   ├── state.py            # RootState, SessionState, ChatState, TerminalState, ChangesetState, AnnotationsState
│   ├── actions.py           # StateAction discriminated union (seed set, extension pattern documented)
│   ├── commands.py           # CommandMap-equivalent: params/result models per JSON-RPC method
│   └── notifications.py       # Server->client notification payloads (action, auth/required, etc.)
├── reducers/            # pure (state, action) -> new_state, one per channel family
├── transport/            # Transport protocol, InMemoryTransport (testing), WebSocketTransport
├── client.py               # AhpClient: initialize/subscribe/dispatch_action/reconnect/
│                             authenticate/resource_*, + ResourceProvider for the host-initiated
│                             resource* direction
└── hosts.py                # MultiHostClient: fan-out registry over N AhpClient instances
```

Not yet implemented: `unsubscribe()`. See `SPEC.md` §6 for the full build order
and what's verified at each layer.

## Install (once published)

```bash
pip install ahp
# or, for the WebSocket transport:
pip install "ahp[websocket]"
# or, with uv
uv add ahp
# or, with uv for the WebSocket transport:
uv add ahp --extra websocket
```

## Local development

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

**If you run nothing else, run this first.** `ahp.types`, `ahp.reducers`, and
`ahp.transport` were verified for real during development; `ahp.client` and
`ahp.hosts` were only syntax-checked (`py_compile`) — see `SPEC.md` §7a.

## Quick start

```python
from ahp import AhpClient
from ahp.transport import WebSocketTransport

async with AhpClient(await WebSocketTransport.connect("ws://localhost:1234")) as client:
    root_state = await client.initialize()
    session_state = await client.subscribe(some_session_uri)
    await client.dispatch_action(some_session_uri, SessionTitleChangedAction(title="Hi"))
```

For multiple hosts:

```python
from ahp import MultiHostClient

async with MultiHostClient.single(client) as multi:
    ...
```

## Design notes

- Wire types use **pydantic v2**, with `populate_by_name=True` so models accept
  either the wire `camelCase` key or the Pythonic `snake_case` field name, and
  `extra="allow"` so forward-compatible optional fields added by the protocol in
  minor/patch versions don't hard-fail validation.
- `StateAction` is a `Literal["type"]`-discriminated union, mirroring the
  discriminated unions used in the TypeScript/Rust clients' `StateAction` type.
- `Transport` is a structural `typing.Protocol`, not an ABC — any duck-typed
  object with async `send`/`receive`/`close` and a `closed` property works,
  matching the Rust trait / Go interface pattern the other clients use.
- `dispatch_action()` applies the reducer **before** awaiting the host's
  response (write-ahead); the later `action` notification echo is matched via
  `(client_id, client_seq)` and deliberately not re-applied.
- Every field set here is a **provisional first pass** based on the public
  specification pages and README, not a line-by-line port of the generated
  Rust/Go/TypeScript types. Expect corrections once cross-checked against
  `schema/*.schema.json` upstream — see `SPEC.md` §7 (open questions).

## License

MIT, matching the upstream repository.
