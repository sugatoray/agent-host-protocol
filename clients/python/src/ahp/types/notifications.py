"""Server -> client notification payloads (JSON-RPC notifications, no response).

These are the ``params`` shapes carried by ``JsonRpcNotification.method`` values
such as ``action``, ``root/sessionAdded``, ``root/sessionRemoved``,
``auth/required``, and the ``otlp/*`` telemetry family.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .common import URI, ActionOrigin, AhpModel, ServerSeq


class ActionNotification(AhpModel):
    """The host's echo of a mutation to a channel — either one this client
    itself dispatched (matched via ``origin``) or one from another client /
    the host itself (``origin`` absent or a different client_id).

    This is the notification the write-ahead reconciliation logic in
    ``ahp.client.AhpClient`` keys off of.
    """

    channel: URI
    server_seq: ServerSeq = Field(alias="serverSeq")
    action: dict[str, Any]
    origin: ActionOrigin | None = None


class SessionAddedNotification(AhpModel):
    """``root/sessionAdded`` — a new session appeared on the host, from any
    client (including out-of-band creation not initiated via this connection).
    """

    session_uri: URI = Field(alias="sessionUri")


class SessionRemovedNotification(AhpModel):
    """``root/sessionRemoved``."""

    session_uri: URI = Field(alias="sessionUri")


class AuthRequiredNotification(AhpModel):
    """``auth/required`` — the host is asking this client to (re)authenticate,
    e.g. because a token expired mid-session. The client is expected to respond
    by calling the ``authenticate`` command.
    """

    scheme: str
    reason: str | None = None


class OtlpLogNotification(AhpModel):
    """``otlp/log`` — host-emitted structured log/telemetry line, following the
    OpenTelemetry log data model loosely (see RFC: Channels discussion for the
    ``ahp-log://`` resource-subscription pattern this complements)."""

    level: str
    message: str
    attributes: dict[str, Any] = Field(default_factory=dict)


NOTIFICATIONS: dict[str, type[AhpModel]] = {
    "action": ActionNotification,
    "root/sessionAdded": SessionAddedNotification,
    "root/sessionRemoved": SessionRemovedNotification,
    "auth/required": AuthRequiredNotification,
    "otlp/log": OtlpLogNotification,
}
"""Wire method name -> params model, for generic notification dispatch."""
