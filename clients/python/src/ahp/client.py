"""``AhpClient`` — a single-host AHP client: JSON-RPC dispatch over a pluggable
:class:`~ahp.transport.base.Transport`, channel subscription bookkeeping, and
write-ahead reconciliation against the pure reducers in ``ahp.reducers``.

Scope for this pass (see SPEC.md §6): ``initialize``, ``subscribe``,
``dispatch_action`` + the ``action`` notification reconciliation loop,
``reconnect`` (replay vs. resnapshot), ``close``, the client-initiated
``authenticate``/``resource*`` commands, and the host-initiated
``resource*`` direction (via a registered :class:`ResourceProvider`). Not yet
implemented: ``unsubscribe`` and ``MultiHostClient`` — the next phase.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Protocol, runtime_checkable

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
    AuthenticateResult,
    DispatchActionParams,
    DispatchActionResult,
    InitializeParams,
    InitializeResult,
    ReconnectParams,
    ReconnectResult,
    ResourceListParams,
    ResourceListResult,
    ResourceReadParams,
    ResourceReadResult,
    ResourceStatParams,
    ResourceStatResult,
    ResourceWriteParams,
    ResourceWriteResult,
    SubscribeParams,
    SubscribeResult,
)
from .types.jsonrpc import (
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponseError,
    JsonRpcResponseSuccess,
    parse_protocol_message,
)
from .types.notifications import ActionNotification

__version_client_name__ = "ahp-python"


class AhpClientError(Exception):
    """Raised for local, protocol-adjacent misuse that isn't a JSON-RPC error
    from the host — e.g. dispatching an action against a channel this client
    never subscribed to.
    """


@runtime_checkable
class ResourceProvider(Protocol):
    """What a client must implement to serve host-initiated ``resource*``
    calls (the symmetric direction: the host asking *this* client to
    read/write/list/stat a resource it has access to, e.g. a local file).

    Register an implementation via :meth:`AhpClient.register_resource_provider`.
    """

    async def read(self, uri: URI) -> ResourceReadResult: ...

    async def write(self, uri: URI, data: str) -> None: ...

    async def list(self, uri: URI) -> ResourceListResult: ...

    async def stat(self, uri: URI) -> ResourceStatResult: ...


# Channel URI scheme -> (state model, pure reducer). The scheme is everything
# before the first ':' (e.g. "ahp-session" in "ahp-session:/abc-123").
_CHANNEL_BINDINGS: dict[str, tuple[type[AhpModel], Callable[[Any, StateAction], Any]]] = {
    "agenthost": (RootState, root_reducer),
    "ahp-session": (SessionState, session_reducer),
    "ahp-chat": (ChatState, chat_reducer),
    "ahp-terminal": (TerminalState, terminal_reducer),
    "ahp-changeset": (ChangesetState, changeset_reducer),
    "ahp-annotations": (AnnotationsState, annotations_reducer),
}

_state_action_adapter: TypeAdapter[StateAction] = TypeAdapter(StateAction)


def _channel_scheme(channel: URI) -> str:
    return channel.split(":", 1)[0]


def _channel_binding(channel: URI) -> tuple[type[AhpModel], Callable[[Any, StateAction], Any]]:
    scheme = _channel_scheme(channel)
    try:
        return _CHANNEL_BINDINGS[scheme]
    except KeyError as exc:
        raise AhpClientError(f"unrecognized channel scheme: {scheme!r} (channel={channel!r})") from exc


class AhpClient:
    """A single-host AHP client bound to one :class:`Transport`.

    Usage::

        async with AhpClient(transport) as client:
            root_state = await client.initialize()
            session_state = await client.subscribe(some_session_uri)
            await client.dispatch_action(some_session_uri, SessionTitleChangedAction(title="Hi"))
    """

    def __init__(
        self,
        transport: Transport,
        *,
        client_name: str = __version_client_name__,
        client_version: str = "0.1.0",
    ) -> None:
        self._transport = transport
        self._client_name = client_name
        self._client_version = client_version

        self._client_id: str | None = None
        self._root_channel: URI | None = None

        self._channel_states: dict[URI, AnyChannelState] = {}
        self._last_seen_server_seq: dict[URI, int] = {}

        self._next_request_id_counter = 0
        self._next_client_seq_counter = 0
        self._pending_requests: dict[int, "asyncio.Future[Any]"] = {}
        self._own_pending_client_seqs: set[int] = set()

        self._reader_task: "asyncio.Task[None] | None" = None
        self._resource_provider: ResourceProvider | None = None

    # -- properties ----------------------------------------------------

    @property
    def client_id(self) -> str | None:
        """The client id assigned by the host during ``initialize``, or
        ``None`` if ``initialize`` hasn't completed yet."""
        return self._client_id

    @property
    def root_channel(self) -> URI | None:
        return self._root_channel

    # -- lifecycle -------------------------------------------------------

    async def __aenter__(self) -> "AhpClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying transport and stop the background reader
        loop. Idempotent.
        """
        await self._transport.close()
        if self._reader_task is not None:
            await self._reader_task

    # -- commands ----------------------------------------------------------

    async def initialize(self) -> RootState:
        """Perform the AHP handshake: negotiate protocol version, obtain a
        client id, and return the root channel's initial state.
        """
        params = InitializeParams(
            protocol_version=1,
            client_name=self._client_name,
            client_version=self._client_version,
        )
        raw_result = await self._send_request("initialize", params)
        result = InitializeResult.model_validate(raw_result)

        self._client_id = result.client_id
        self._root_channel = result.root_snapshot.channel

        root_state = RootState.model_validate(result.root_snapshot.state)
        self._channel_states[result.root_snapshot.channel] = root_state
        self._last_seen_server_seq[result.root_snapshot.channel] = result.root_snapshot.server_seq
        return root_state

    async def subscribe(self, channel: URI) -> AnyChannelState:
        """Subscribe to ``channel`` and return its current (snapshot) state."""
        state_model, _reducer = _channel_binding(channel)

        params = SubscribeParams(channel=channel)
        raw_result = await self._send_request("subscribe", params)
        result = SubscribeResult.model_validate(raw_result)

        state = state_model.model_validate(result.snapshot.state)
        self._channel_states[channel] = state
        self._last_seen_server_seq[channel] = result.snapshot.server_seq
        return state

    async def reconnect(self, transport: Transport | None = None) -> ReconnectResult:
        """Re-establish the session after a dropped connection.

        If ``transport`` is given, it replaces the current (presumably dead)
        transport — the old background reader task (if still running) is
        cancelled rather than awaited, since the old transport may not be
        cleanly closed. If omitted, the existing transport is reused as-is
        (e.g. the caller already swapped in a fresh connection object without
        creating a new ``AhpClient``).

        Sends the host this client's ``last_seen_server_seq`` per channel; the
        host decides, per channel, whether to **replay** the missed ``action``
        notifications (left for the normal notification handler to apply) or
        to **resnapshot** (this method overwrites local state for those
        channels immediately with the fresh snapshot).
        """
        if self._client_id is None:
            raise AhpClientError("cannot reconnect before initialize() has completed")

        if transport is not None:
            old_reader_task = self._reader_task
            self._transport = transport
            self._reader_task = None
            if old_reader_task is not None and not old_reader_task.done():
                old_reader_task.cancel()

        params = ReconnectParams(
            client_id=self._client_id,
            last_seen_server_seq=dict(self._last_seen_server_seq),
        )
        raw_result = await self._send_request("reconnect", params)
        result = ReconnectResult.model_validate(raw_result)

        for snapshot in result.resnapshotted:
            state_model, _reducer = _channel_binding(snapshot.channel)
            state = state_model.model_validate(snapshot.state)
            self._channel_states[snapshot.channel] = state
            self._last_seen_server_seq[snapshot.channel] = snapshot.server_seq

        # Replayed channels are intentionally left untouched here: the host
        # will follow up with ordinary `action` notifications for whatever
        # was missed, and _handle_action_notification() applies those exactly
        # as it would for any other notification (including correctly
        # recognizing echoes of this client's own not-yet-acknowledged
        # actions from before the drop).
        return result

    async def dispatch_action(self, channel: URI, action: StateAction) -> int:
        """Dispatch ``action`` against ``channel``.

        Applies the action to local state immediately (write-ahead), before
        the round trip to the host completes, then sends ``dispatchAction``
        and returns the ``serverSeq`` the host assigned to the mutation. The
        corresponding ``action`` notification the host later broadcasts (which
        echoes this same mutation back, including to this client) is matched
        against the pending client_seq recorded here and is *not* re-applied —
        see :meth:`_handle_action_notification`.
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

        # Write-ahead: apply locally before awaiting anything from the host.
        self._channel_states[channel] = reducer(current, action)

        params = DispatchActionParams(
            channel=channel,
            client_seq=client_seq,
            action=action.model_dump(by_alias=True),
        )
        raw_result = await self._send_request("dispatchAction", params)
        result = DispatchActionResult.model_validate(raw_result)
        return result.server_seq

    def get_state(self, channel: URI) -> AnyChannelState | None:
        """Return the last known state for ``channel``, or ``None`` if this
        client has never subscribed to (or initialized) it.
        """
        return self._channel_states.get(channel)

    async def authenticate(self, scheme: str, credentials: dict[str, Any] | None = None) -> bool:
        """Ask the host to authenticate ``credentials`` under ``scheme``.

        Typically called in response to an ``auth/required`` notification
        (e.g. an expired token mid-session), but can also be called
        proactively.
        """
        params = AuthenticateParams(scheme=scheme, credentials=credentials or {})
        raw_result = await self._send_request("authenticate", params)
        result = AuthenticateResult.model_validate(raw_result)
        return result.authenticated

    async def resource_read(self, uri: URI) -> ResourceReadResult:
        """Ask the host to read a resource it owns."""
        raw_result = await self._send_request("resourceRead", ResourceReadParams(uri=uri))
        return ResourceReadResult.model_validate(raw_result)

    async def resource_write(self, uri: URI, data: str) -> None:
        """Ask the host to write ``data`` to a resource it owns."""
        await self._send_request("resourceWrite", ResourceWriteParams(uri=uri, data=data))

    async def resource_list(self, uri: URI) -> ResourceListResult:
        """Ask the host to list entries under ``uri``."""
        raw_result = await self._send_request("resourceList", ResourceListParams(uri=uri))
        return ResourceListResult.model_validate(raw_result)

    async def resource_stat(self, uri: URI) -> ResourceStatResult:
        """Ask the host whether/what a resource is, without reading it."""
        raw_result = await self._send_request("resourceStat", ResourceStatParams(uri=uri))
        return ResourceStatResult.model_validate(raw_result)

    def register_resource_provider(self, provider: ResourceProvider | None) -> None:
        """Register the object that serves host-initiated ``resource*``
        calls against this client (the symmetric direction — see
        :class:`ResourceProvider`). Replaces any previously registered
        provider. Pass ``None`` to unregister.
        """
        self._resource_provider = provider

    # -- wire plumbing -------------------------------------------------

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
                    # Malformed/unrecognized message: don't crash the reader
                    # loop over a single bad frame.
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
            # Don't leave any in-flight caller awaiting forever if the
            # transport went away mid-request.
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
        # Other notification methods (root/sessionAdded, auth/required,
        # otlp/*, ...) are out of scope for this pass — see SPEC.md.

    def _handle_action_notification(self, params: dict[str, Any]) -> None:
        notification = ActionNotification.model_validate(params)
        channel = notification.channel
        origin = notification.origin

        if (
            origin is not None
            and self._client_id is not None
            and origin.client_id == self._client_id
            and origin.client_seq in self._own_pending_client_seqs
        ):
            # This is the host echoing back a mutation we already applied
            # optimistically in dispatch_action(). Don't re-apply it — just
            # advance the last-seen server sequence for the channel.
            self._own_pending_client_seqs.discard(origin.client_seq)
            self._last_seen_server_seq[channel] = notification.server_seq
            return

        current = self._channel_states.get(channel)
        if current is None:
            # Not subscribed to this channel (or haven't initialized it) —
            # nothing local to reconcile against.
            return

        _state_model, reducer = _channel_binding(channel)
        action = _state_action_adapter.validate_python(notification.action)
        self._channel_states[channel] = reducer(current, action)
        self._last_seen_server_seq[channel] = notification.server_seq

    async def _handle_host_request(self, message: JsonRpcRequest) -> None:
        """Handle a host-initiated JSON-RPC *request* (as opposed to a
        response or notification) — currently the ``resource*`` family, the
        symmetric direction where the host calls back into this client.

        Always replies with either a success or an error response; never lets
        an exception escape into the reader loop, since a single misbehaving
        provider call must not take down the whole connection.
        """
        try:
            result = await self._dispatch_host_request(message.method, message.params or {})
        except AhpClientError as exc:
            await self._send_host_error_response(
                message.id, code=JsonRpcErrorCode.METHOD_NOT_FOUND, message=str(exc)
            )
            return
        except Exception as exc:  # noqa: BLE001 - a provider's own bug must not kill the loop
            await self._send_host_error_response(
                message.id, code=JsonRpcErrorCode.INTERNAL_ERROR, message=str(exc)
            )
            return
        await self._send_host_success_response(message.id, result)

    async def _dispatch_host_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._resource_provider is None:
            raise AhpClientError(
                f"received host-initiated {method!r} but no resource provider "
                f"is registered (see AhpClient.register_resource_provider)"
            )

        if method == "resourceRead":
            read_params = ResourceReadParams.model_validate(params)
            read_result = await self._resource_provider.read(read_params.uri)
            return read_result.model_dump(by_alias=True)

        if method == "resourceWrite":
            write_params = ResourceWriteParams.model_validate(params)
            await self._resource_provider.write(write_params.uri, write_params.data)
            return ResourceWriteResult().model_dump(by_alias=True)

        if method == "resourceList":
            list_params = ResourceListParams.model_validate(params)
            list_result = await self._resource_provider.list(list_params.uri)
            return list_result.model_dump(by_alias=True)

        if method == "resourceStat":
            stat_params = ResourceStatParams.model_validate(params)
            stat_result = await self._resource_provider.stat(stat_params.uri)
            return stat_result.model_dump(by_alias=True)

        raise AhpClientError(f"unsupported host-initiated method: {method!r}")

    async def _send_host_success_response(self, request_id: Any, result: dict[str, Any]) -> None:
        response = JsonRpcResponseSuccess(id=request_id, result=result)
        await self._transport.send(response.model_dump_json(by_alias=True, exclude_none=True))

    async def _send_host_error_response(self, request_id: Any, *, code: int, message: str) -> None:
        response = JsonRpcResponseError(
            id=request_id, error=JsonRpcErrorObject(code=code, message=message)
        )
        await self._transport.send(response.model_dump_json(by_alias=True, exclude_none=True))
