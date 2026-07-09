# What Is Agent Host Protocol?

Agent Host Protocol, or **AHP**, is a shared language for apps that want to
talk to an AI agent session.

Very simply:

> **AHP lets many clients watch and control the same AI agent session without
> getting out of sync.**

Think of it like Google Docs, but for AI agent sessions.

## Big Picture

```text
+-------------+        AHP messages        +----------------+
| VS Code     | <------------------------> |                |
| Web app     |                            | AHP Server     |
| CLI tool    | <------------------------> |                |
| Mobile app  |                            | Agent Sessions |
+-------------+                            +----------------+
```

The **server** owns the real session state.

The **clients** connect to it and say things like:

```text
"Show me this session"
"Send this user message"
"Change the session title"
"Tell me when something changes"
```

The server replies with state and updates.

## The Main Idea

AHP is about keeping everyone looking at the same state.

```text
Client A                     AHP Server                    Client B
--------                     ----------                    --------
opens session  ------------> stores session state
                             sends snapshot -------------> sees session

renames session ------------> applies action
                             broadcasts update ----------> sees new title
```

So if one client changes something, the others find out.

## Key Words

### Host or Server

The thing running the agent sessions.

Example: VS Code's agent host.

```text
AHP Server = the source of truth
```

### Client

An app or library that connects to the host.

Examples:

```text
VS Code UI
a terminal app
a web dashboard
a Python script
```

This repo has clients for languages like Rust, TypeScript, Kotlin, Go, Swift,
and Python.

### Session

One AI-agent conversation or workspace interaction.

```text
Session
|-- chat messages
|-- terminal state
|-- annotations
|-- changesets
`-- metadata like title/status
```

### State

The current shape of the session.

Example:

```json
{
  "session": {
    "title": "Fix login bug",
    "status": "running"
  },
  "chat": {
    "messages": [
      { "role": "user", "text": "Please inspect the auth flow" },
      { "role": "assistant", "text": "I'll look through the login code." }
    ]
  }
}
```

### Action

A small event that changes state.

For example:

```json
{
  "type": "session/titleChanged",
  "title": "Fix login bug"
}
```

Instead of sending the whole state every time, clients and servers mostly
exchange actions.

```text
Old State + Action = New State
```

Diagram:

```text
+-------------------+
| Current State     |
| title: "Untitled" |
+-------------------+
          |
          | action: titleChanged("Fix login bug")
          v
+------------------------+
| New State              |
| title: "Fix login bug" |
+------------------------+
```

### Reducer

A reducer is just a pure function that applies an action to state.

In plain language:

```text
reducer = the rulebook for how actions change state
```

Example:

```python
def reduce_session(state, action):
    if action.type == "session/titleChanged":
        state.title = action.title
    return state
```

AHP likes reducers because every client can calculate the same result from the
same action.

### Snapshot

A snapshot is a full copy of state at a moment in time.

When a client first joins, it may get a snapshot:

```text
"Here is the whole session as it exists right now."
```

After that, it can receive smaller updates:

```text
"Message added."
"Title changed."
"Terminal output appended."
```

## Write-Ahead Reconciliation

This phrase sounds scarier than it is.

It means:

> The client may apply its own action immediately, before the server confirms
> it, so the UI feels fast.

Diagram:

```text
Client                         Server
------                         ------
User renames session
Apply change locally
UI updates instantly  -------> Server receives action
                               Server accepts action
                    <--------- Server echoes action back
Client says:
"I already applied that one."
```

So the client does not wait around feeling slow.

## Multi-Client Sync

Imagine two clients are looking at the same session:

```text
+-------------+                 +-------------+
| Client A    |                 | Client B    |
| VS Code     |                 | Web UI      |
+-------------+                 +-------------+
       \                              /
        \                            /
         v                          v
              +----------------+
              | AHP Server     |
              | Session State  |
              +----------------+
```

If Client A sends a message:

```text
Client A: "Run tests"
```

The server updates the session, then tells Client B:

```text
Client B: now sees "Run tests"
```

That is the heart of AHP.

## Simple Python Example

Using the Python client idea from `clients/python/README.md`:

```python
from ahp import AhpClient
from ahp.transport import WebSocketTransport

async with AhpClient(
    await WebSocketTransport.connect("ws://localhost:1234")
) as client:
    root_state = await client.initialize()

    session_state = await client.subscribe("session://example")

    await client.dispatch_action(
        "session://example",
        {
            "type": "session/titleChanged",
            "title": "Fix login bug",
        },
    )
```

In plain English, this does:

```text
1. Connect to an AHP server.
2. Initialize the protocol.
3. Subscribe to one session.
4. Send an action that changes the session title.
```

## Why AHP Exists

Without a protocol, every agent UI would invent its own way to represent:

```text
sessions
messages
tool calls
terminal output
file changes
errors
permissions
auth prompts
```

That gets messy quickly.

AHP gives everyone one shared contract:

```text
Server and clients agree on:
- message shapes
- state shapes
- action names
- error formats
- update flow
- versioning rules
```

## Tiny Analogy

AHP is like a restaurant ticket system.

```text
Customer app       Kitchen system       Waiter display
-----------        --------------       --------------
orders food  --->  stores order   --->  sees update
changes item --->  updates order  --->  sees change
```

Everyone sees the same order because they share one protocol.

For AHP:

```text
Client app         AHP server           Other clients
----------         ----------           -------------
sends action --->  updates state  --->  receive update
```

## One-Sentence Version

Agent Host Protocol is a standard way for AI-agent clients and servers to share
session state, send actions, and keep multiple views of the same agent session
synchronized.
