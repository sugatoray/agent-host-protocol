"""``AhpClient`` — single-host AHP client: JSON-RPC dispatch, channel
subscription bookkeeping, and write-ahead reconciliation against the pure
reducers in ``ahp.reducers``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Protocol, runtime_checkable

_log = logging.getLogger(__name__)

from pydantic import TypeAdapter

from .reducers import (
    annotations_reducer,
    changeset_reducer,
    chat_reducer,
    root_reducer,
    session_reducer,
    terminal_reducer,
)
from .transport.base import Transport, TransportClosedError
from .types import (
    URI,
    AhpError,
    AhpModel,
    AnnotationsState,
    AnyChannelState,
    ChangesetState,
    ChatState,
    JsonRpcErrorCode,
    JsonRpcErrorObject,
    RootState,
    SessionState,
    StateAction,
    TerminalState,
)
from .types.commands import (
    AuthenticateParams,
    CompletionsParams,
    CompletionsResult,
    CreateChatParams,
    CreateChatResult,
    CreateSessionParams,
    CreateSessionResult,
    CreateTerminalParams,
    CreateTerminalResult,
    DispatchActionParams,
    DisposeChatParams,
    DisposeChatResult,
    DisposeSessionParams,
    DisposeSessionResult,
    DisposeTerminalParams,
    DisposeTerminalResult,
    FetchTurnsParams,
    FetchTurnsResult,
    InitializeParams,
    InitializeResult,
    InvokeChangesetOperationParams,
    InvokeChangesetOperationResult,
    ListSessionsParams,
    ListSessionsResult,
    PingParams,
    ReconnectParams,
    ReconnectReplayResult,
    ReconnectSnapshotResult,
    ResourceListParams,
    ResourceListResult,
    ResourceReadParams,
    ResourceReadResult,
    ResourceWriteParams,
    ResourceWriteResult,
    SubscribeParams,
    SubscribeResult,
    UnsubscribeParams,
    UnsubscribeResult,
)
from .types.jsonrpc import (
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponseError,
    JsonRpcResponseSuccess,
    parse_protocol_message,
)
from .types.notifications import ActionNotification

# Channel URI scheme -> (state model, pure reducer).
# Scheme is everything before the first ':' (e.g. "ahp-root" in "ahp-root://").
_CHANNEL_BINDINGS: dict[str, tuple[type[AhpModel], Callable[[Any, StateAction], Any]]] = {
    "ahp-root": (RootState, root_reducer),
    "ahp-session": (SessionState, session_reducer),
    "ahp-chat": (ChatState, chat_reducer),
    "ahp-terminal": (TerminalState, terminal_reducer),
    "ahp-changeset": (ChangesetState, changeset_reducer),
    "ahp-annotations": (AnnotationsState, annotations_reducer),
}

_state_action_adapter: TypeAdapter[StateAction] = TypeAdapter(StateAction)

_ROOT_CHANNEL: URI = "ahp-root://"
_PROTOCOL_VERSION = "0.1.0"


class AhpClientError(Exception):
    """Local protocol misuse — not a JSON-RPC error from the host."""


@runtime_checkable
class ResourceProvider(Protocol):
    """Implement to serve host-initiated ``resource*`` calls (symmetric direction)."""

    async def read(self, uri: URI) -> ResourceReadResult: ...

    async def write(self, uri: URI, data: str, encoding: str = "utf-8") -> None: ...

    async def list(self, uri: URI) -> ResourceListResult: ...


def _channel_scheme(channel: URI) -> str:
    return channel.split(":", 1)[0]


def _channel_binding(channel: URI) -> tuple[type[AhpModel], Callable[[Any, StateAction], Any]]:
    scheme = _channel_scheme(channel)
    try:
        return _CHANNEL_BINDINGS[scheme]
    except KeyError as exc:
        raise AhpClientError(
            f"unrecognized channel scheme: {scheme!r} (channel={channel!r})"
        ) from exc


class AhpClient:
    """A single-host AHP client bound to one :class:`Transport`.

    Usage::

        async with AhpClient(transport) as client:
            root_state = await client.initialize()
            session_uri = await client.create_session(channel="ahp-session:/...")
            session_state = await client.subscribe(session_uri)
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

        # Client generates its own clientId UUID before sending initialize.
        self._client_id: str = str(uuid.uuid4())
        self._initialized: bool = False

        self._channel_states: dict[URI, AnyChannelState] = {}
        self._last_seen_server_seq: dict[URI, int] = {}

        self._next_request_id_counter = 0
        self._next_client_seq_counter = 0
        self._pending_requests: dict[int, "asyncio.Future[Any]"] = {}
        self._own_pending_client_seqs: set[int] = set()

        self._reader_task: "asyncio.Task[None] | None" = None
        self._resource_provider: ResourceProvider | None = None

    # -- properties --------------------------------------------------------

    @property
    def client_id(self) -> str:
        """UUID this client uses when communicating with the host."""
        return self._client_id

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> "AhpClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close transport and stop background reader. Idempotent."""
        await self._transport.close()
        if self._reader_task is not None:
            await self._reader_task

    # -- commands ----------------------------------------------------------

    async def initialize(
        self,
        *,
        initial_subscriptions: list[URI] | None = None,
        locale: str | None = None,
    ) -> RootState:
        """Perform the AHP handshake and return the root channel's initial state.

        The client generates its own ``clientId`` UUID; no client-id is
        returned by the server.  The server returns ``snapshots`` (a list)
        rather than a single root snapshot.
        """
        params = InitializeParams(
            protocol_versions=[_PROTOCOL_VERSION],
            client_id=self._client_id,
            initial_subscriptions=initial_subscriptions,
            locale=locale,
        )
        raw_result = await self._send_request("initialize", params)
        result = InitializeResult.model_validate(raw_result)

        # Ingest all snapshots the server sent along with the initialize result.
        for snap in result.snapshots:
            state_model, _reducer = _channel_binding(snap.resource)
            state = state_model.model_validate(snap.state)
            self._channel_states[snap.resource] = state
            self._last_seen_server_seq[snap.resource] = snap.from_seq

        self._initialized = True
        return self._channel_states.get(_ROOT_CHANNEL, RootState())  # type: ignore[return-value]

    async def subscribe(self, channel: URI) -> AnyChannelState:
        """Subscribe to ``channel`` and return its current (snapshot) state."""
        state_model, _reducer = _channel_binding(channel)

        params = SubscribeParams(channel=channel)
        raw_result = await self._send_request("subscribe", params)
        result = SubscribeResult.model_validate(raw_result)

        if result.snapshot is None:
            # Server sent no snapshot — use default empty state.
            state: AnyChannelState = state_model()  # type: ignore[call-arg]
        else:
            state = state_model.model_validate(result.snapshot.state)
            self._last_seen_server_seq[channel] = result.snapshot.from_seq

        self._channel_states[channel] = state
        return state

    async def unsubscribe(self, channel: URI) -> None:
        """Unsubscribe from ``channel`` and forget its local state."""
        await self._send_request("unsubscribe", UnsubscribeParams(channel=channel))
        self._channel_states.pop(channel, None)
        self._last_seen_server_seq.pop(channel, None)

    async def reconnect(
        self,
        transport: Transport | None = None,
        *,
        channel: URI = _ROOT_CHANNEL,
    ) -> ReconnectReplayResult | ReconnectSnapshotResult:
        """Re-establish the session after a dropped connection.

        ``channel`` is the channel we reconnect on (defaults to root).
        ``lastSeenServerSeq`` is taken from local state for that channel.
        The host receives the full subscription list and decides per-channel
        whether to replay actions or resend a snapshot.
        """
        if not self._initialized:
            raise AhpClientError("cannot reconnect before initialize() has completed")

        if transport is not None:
            old_reader_task = self._reader_task
            self._transport = transport
            self._reader_task = None
            if old_reader_task is not None and not old_reader_task.done():
                old_reader_task.cancel()

        params = ReconnectParams(
            channel=channel,
            client_id=self._client_id,
            last_seen_server_seq=self._last_seen_server_seq.get(channel, 0),
            subscriptions=list(self._channel_states.keys()),
        )
        raw_result = await self._send_request("reconnect", params)

        # Parse as the appropriate result variant based on `type` field.
        result_type = (raw_result or {}).get("type")
        if result_type == "snapshot":
            result = ReconnectSnapshotResult.model_validate(raw_result)
            for snap in result.snapshots:
                state_model, _reducer = _channel_binding(snap.resource)
                state = state_model.model_validate(snap.state)
                self._channel_states[snap.resource] = state
                self._last_seen_server_seq[snap.resource] = snap.from_seq
        else:
            result = ReconnectReplayResult.model_validate(raw_result)
            # Replayed channels: actions arrive as normal notifications; no
            # special handling needed here.

        return result

    async def dispatch_action(self, channel: URI, action: StateAction) -> None:
        """Dispatch ``action`` against ``channel`` (fire-and-forget notification).

        Applies the action to local state immediately (write-ahead), then
        sends a ``dispatchAction`` JSON-RPC *notification* (no id, no response).
        The host will echo the action back as an ``action`` notification;
        our reader loop recognises our own client_seq and skips re-applying it.
        """
        _state_model, reducer = _channel_binding(channel)
        current = self._channel_states.get(channel)
        if current is None:
            raise AhpClientError(
                f"cannot dispatch an action to a channel that hasn't been "
                f"subscribed yet: {channel!r}"
            )

        client_seq = self._next_client_seq()
        self._own_pending_client_seqs.add(client_seq)

        # Write-ahead: apply locally before sending.
        self._channel_states[channel] = reducer(current, action)

        params = DispatchActionParams(
            channel=channel,
            client_seq=client_seq,
            action=action.model_dump(by_alias=True),
        )
        await self._send_notification("dispatchAction", params)

    def get_state(self, channel: URI) -> AnyChannelState | None:
        """Return last known state for ``channel``, or ``None`` if not subscribed."""
        return self._channel_states.get(channel)

    async def ping(self, *, channel: URI = _ROOT_CHANNEL) -> None:
        """Send a ping to the host (liveness check)."""
        await self._send_request("ping", PingParams(channel=channel))

    async def authenticate(self, resource: str, token: str) -> None:
        """Authenticate with the host for ``resource`` using ``token``."""
        params = AuthenticateParams(resource=resource, token=token)
        await self._send_request("authenticate", params)

    async def resource_read(self, uri: URI, *, channel: URI = _ROOT_CHANNEL) -> ResourceReadResult:
        """Ask the host to read a resource."""
        raw_result = await self._send_request(
            "resourceRead", ResourceReadParams(channel=channel, uri=uri)
        )
        return ResourceReadResult.model_validate(raw_result)

    async def resource_write(
        self,
        uri: URI,
        data: str,
        encoding: str = "utf-8",
        *,
        channel: URI = _ROOT_CHANNEL,
    ) -> None:
        """Ask the host to write ``data`` to ``uri``."""
        await self._send_request(
            "resourceWrite",
            ResourceWriteParams(channel=channel, uri=uri, data=data, encoding=encoding),
        )

    async def resource_list(self, uri: URI, *, channel: URI = _ROOT_CHANNEL) -> ResourceListResult:
        """Ask the host to list entries under ``uri``."""
        raw_result = await self._send_request(
            "resourceList", ResourceListParams(channel=channel, uri=uri)
        )
        return ResourceListResult.model_validate(raw_result)

    async def create_session(
        self,
        *,
        provider: str | None = None,
        working_directory: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> URI:
        """Ask the host to create a new session; returns the client-chosen session URI.

        The session URI is generated client-side (per canonical protocol); result is null.
        """
        session_uri = f"ahp-session:/{uuid.uuid4()}"
        params = CreateSessionParams(
            channel=session_uri,
            provider=provider,
            working_directory=working_directory,
            config=config,
        )
        await self._send_request("createSession", params)
        return session_uri

    async def dispose_session(self, session_channel: URI) -> None:
        """Ask the host to dispose of a session and forget its local state."""
        await self._send_request(
            "disposeSession", DisposeSessionParams(channel=session_channel)
        )
        self._channel_states.pop(session_channel, None)
        self._last_seen_server_seq.pop(session_channel, None)

    async def list_sessions(self) -> ListSessionsResult:
        """Ask the host for the list of current sessions."""
        raw_result = await self._send_request("listSessions", ListSessionsParams())
        return ListSessionsResult.model_validate(raw_result)

    async def create_chat(
        self,
        session_channel: URI,
        *,
        initial_message: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
    ) -> URI:
        """Ask the host to create a new chat; returns the client-chosen chat URI.

        The chat URI is generated client-side (per canonical protocol); result is null.
        """
        chat_uri = f"ahp-chat:/{uuid.uuid4()}"
        params = CreateChatParams(
            channel=session_channel,
            chat=chat_uri,
            initial_message=initial_message,
            source=source,
        )
        await self._send_request("createChat", params)
        return chat_uri

    async def dispose_chat(self, chat_channel: URI) -> None:
        """Ask the host to dispose of a chat and forget its local state."""
        await self._send_request("disposeChat", DisposeChatParams(channel=chat_channel))
        self._channel_states.pop(chat_channel, None)
        self._last_seen_server_seq.pop(chat_channel, None)

    async def fetch_turns(
        self, chat_channel: URI, *, cursor: str | None = None
    ) -> None:
        """Ask the host to (re)deliver a page of a chat's turn history.

        Per canonical protocol, fetchTurns result is empty — turns arrive via the
        ``chat/turnsLoaded`` action on the subscribed chat channel.
        """
        params = FetchTurnsParams(channel=chat_channel, cursor=cursor)
        await self._send_request("fetchTurns", params)

    async def create_terminal(
        self,
        claim: dict[str, Any],
        *,
        name: str | None = None,
        cwd: str | None = None,
        cols: int | None = None,
        rows: int | None = None,
    ) -> URI:
        """Ask the host to create a new terminal; returns the client-chosen terminal URI.

        The terminal URI is generated client-side (per canonical protocol); result is null.
        ``claim`` identifies the initial owner of the terminal.
        """
        terminal_uri = f"ahp-terminal:/{uuid.uuid4()}"
        params = CreateTerminalParams(
            channel=terminal_uri, claim=claim, name=name, cwd=cwd, cols=cols, rows=rows
        )
        await self._send_request("createTerminal", params)
        return terminal_uri

    async def dispose_terminal(self, terminal_channel: URI) -> None:
        """Ask the host to dispose of a terminal and forget its local state."""
        await self._send_request(
            "disposeTerminal", DisposeTerminalParams(channel=terminal_channel)
        )
        self._channel_states.pop(terminal_channel, None)
        self._last_seen_server_seq.pop(terminal_channel, None)

    async def completions(
        self, channel: URI, *, kind: str, text: str, offset: int
    ) -> CompletionsResult:
        """Ask the host for completion suggestions."""
        params = CompletionsParams(kind=kind, channel=channel, text=text, offset=offset)
        raw_result = await self._send_request("completions", params)
        return CompletionsResult.model_validate(raw_result)

    async def invoke_changeset_operation(
        self,
        changeset_channel: URI,
        operation_id: str,
        *,
        target: dict[str, Any] | None = None,
    ) -> InvokeChangesetOperationResult:
        """Invoke a named operation against a changeset."""
        params = InvokeChangesetOperationParams(
            channel=changeset_channel, operation_id=operation_id, target=target
        )
        raw_result = await self._send_request("invokeChangesetOperation", params)
        return InvokeChangesetOperationResult.model_validate(raw_result)

    def register_resource_provider(self, provider: ResourceProvider | None) -> None:
        """Register (or clear) the handler for host-initiated ``resource*`` calls."""
        self._resource_provider = provider

    # -- wire plumbing -------------------------------------------------------

    def _next_request_id(self) -> int:
        self._next_request_id_counter += 1
        return self._next_request_id_counter

    def _next_client_seq(self) -> int:
        self._next_client_seq_counter += 1
        return self._next_client_seq_counter

    def _ensure_reader_started(self) -> None:
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._reader_loop())

    async def _send_request(self, method: str, params: AhpModel) -> dict[str, Any]:
        self._ensure_reader_started()

        request_id = self._next_request_id()
        loop = asyncio.get_running_loop()
        future: "asyncio.Future[Any]" = loop.create_future()
        self._pending_requests[request_id] = future

        request = JsonRpcRequest(
            id=request_id,
            method=method,
            params=params.model_dump(by_alias=True, exclude_none=True),
        )
        await self._transport.send(request.model_dump_json(by_alias=True, exclude_none=True))
        return await future

    async def _send_notification(self, method: str, params: AhpModel) -> None:
        """Send a fire-and-forget JSON-RPC notification (no id, no response)."""
        self._ensure_reader_started()
        notification = JsonRpcNotification(
            method=method,
            params=params.model_dump(by_alias=True, exclude_none=True),
        )
        await self._transport.send(
            notification.model_dump_json(by_alias=True, exclude_none=True)
        )

    async def _reader_loop(self) -> None:
        try:
            while True:
                try:
                    raw = await self._transport.receive()
                except TransportClosedError:
                    return

                try:
                    parsed = json.loads(raw)
                    message = parse_protocol_message(parsed)
                except Exception:
                    _log.warning("ahp: malformed message from host, skipping: %r", raw, exc_info=True)
                    continue

                if isinstance(message, JsonRpcResponseSuccess):
                    self._resolve_request(message.id, result=message.result)
                elif isinstance(message, JsonRpcResponseError):
                    self._resolve_request(message.id, error=message.error)
                elif isinstance(message, JsonRpcNotification):
                    self._handle_notification(message)
                elif isinstance(message, JsonRpcRequest):
                    await self._handle_host_request(message)
        finally:
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(
                        TransportClosedError("transport closed while a request was in flight")
                    )
            self._pending_requests.clear()

    def _resolve_request(self, request_id: Any, *, result: Any = None, error: Any = None) -> None:
        future = self._pending_requests.pop(request_id, None)
        if future is None or future.done():
            return
        if error is not None:
            future.set_exception(AhpError(error))
        else:
            future.set_result(result)

    def _handle_notification(self, message: JsonRpcNotification) -> None:
        if message.method == "action":
            self._handle_action_notification(message.params or {})

    def _handle_action_notification(self, params: dict[str, Any]) -> None:
        notification = ActionNotification.model_validate(params)
        channel = notification.channel
        origin = notification.origin

        if (
            origin is not None
            and origin.client_id == self._client_id
            and origin.client_seq in self._own_pending_client_seqs
        ):
            # Echo of our own write-ahead action; skip re-applying.
            self._own_pending_client_seqs.discard(origin.client_seq)
            self._last_seen_server_seq[channel] = notification.server_seq
            return

        current = self._channel_states.get(channel)
        if current is None:
            return

        _state_model, reducer = _channel_binding(channel)
        action = _state_action_adapter.validate_python(notification.action)
        self._channel_states[channel] = reducer(current, action)
        self._last_seen_server_seq[channel] = notification.server_seq

    async def _handle_host_request(self, message: JsonRpcRequest) -> None:
        """Handle host-initiated resource* requests (symmetric direction)."""
        try:
            result = await self._dispatch_host_request(message.method, message.params or {})
        except AhpClientError as exc:
            _log.warning("ahp: host request %r not handled: %s", message.method, exc)
            await self._send_host_error_response(
                message.id, code=JsonRpcErrorCode.METHOD_NOT_FOUND, message=str(exc)
            )
            return
        except Exception as exc:  # noqa: BLE001
            _log.error("ahp: error handling host request %r", message.method, exc_info=True)
            await self._send_host_error_response(
                message.id, code=JsonRpcErrorCode.INTERNAL_ERROR, message=str(exc)
            )
            return
        await self._send_host_success_response(message.id, result)

    async def _dispatch_host_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._resource_provider is None:
            raise AhpClientError(
                f"received host-initiated {method!r} but no resource provider is registered"
            )

        if method == "resourceRead":
            p = ResourceReadParams.model_validate(params)
            res = await self._resource_provider.read(p.uri)
            return res.model_dump(by_alias=True)

        if method == "resourceWrite":
            p = ResourceWriteParams.model_validate(params)
            await self._resource_provider.write(p.uri, p.data, p.encoding)
            return ResourceWriteResult().model_dump(by_alias=True)

        if method == "resourceList":
            p = ResourceListParams.model_validate(params)
            res = await self._resource_provider.list(p.uri)
            return res.model_dump(by_alias=True)

        raise AhpClientError(f"unsupported host-initiated method: {method!r}")

    async def _send_host_success_response(self, request_id: Any, result: dict[str, Any]) -> None:
        response = JsonRpcResponseSuccess(id=request_id, result=result)
        await self._transport.send(response.model_dump_json(by_alias=True, exclude_none=True))

    async def _send_host_error_response(
        self, request_id: Any, *, code: int, message: str
    ) -> None:
        response = JsonRpcResponseError(
            id=request_id, error=JsonRpcErrorObject(code=code, message=message)
        )
        await self._transport.send(response.model_dump_json(by_alias=True, exclude_none=True))
