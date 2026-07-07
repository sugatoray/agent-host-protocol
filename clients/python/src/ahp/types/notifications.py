"""Server -> client notification payloads (JSON-RPC notifications, no response).

Reconciled against canonical types/*.ts:
  - ``action``: ActionEnvelope broadcast
  - ``root/sessionAdded``: new session with channel URI + summary
  - ``root/sessionRemoved``: session gone (fields: ``channel``, ``session`` URI)
  - ``root/sessionSummaryChanged``: existing session summary updated (fields: ``channel``, ``session``, ``changes``)
  - ``auth/required``: host needs client to authenticate (fields: ``channel``, ``resource``, ``reason?``)
  - ``root/progress``: long-running operation progress (fields: ``channel``, ``progressToken``, ``progress``, ``total?``, ``message?``)
  - ``otlp/exportLogs``, ``otlp/exportTraces``, ``otlp/exportMetrics``: telemetry (fields: ``channel``, ``payload``)
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .common import URI, ActionOrigin, AhpModel, ServerSeq


class ActionNotification(AhpModel):
    """``action`` — host broadcasts a channel mutation to all subscribers."""

    channel: URI
    server_seq: ServerSeq = Field(alias="serverSeq")
    action: dict[str, Any]
    origin: ActionOrigin | None = None
    rejection_reason: str | None = Field(default=None, alias="rejectionReason")


class SessionAddedNotification(AhpModel):
    """``root/sessionAdded`` — a new session appeared on the host."""

    channel: URI
    summary: dict[str, Any]  # SessionSummary


class SessionRemovedNotification(AhpModel):
    """``root/sessionRemoved``."""

    channel: URI
    session: URI


class SessionSummaryChangedNotification(AhpModel):
    """``root/sessionSummaryChanged`` — metadata on an existing session changed."""

    channel: URI
    session: URI
    changes: dict[str, Any]


class AuthRequiredNotification(AhpModel):
    """``auth/required`` — host is asking client to (re)authenticate.

    ``resource`` is the protected resource URI per RFC 9728.
    ``reason`` is one of ``"required"`` | ``"expired"``.
    """

    channel: URI
    resource: str
    reason: str | None = None


class ProgressNotification(AhpModel):
    """``root/progress`` — progress update for a long-running operation."""

    channel: URI
    progress_token: str = Field(alias="progressToken")
    progress: float
    total: float | None = None
    message: str | None = None


class OtlpExportLogsNotification(AhpModel):
    """``otlp/exportLogs`` — OpenTelemetry log records (OTLP/JSON ExportLogsServiceRequest in ``payload``)."""

    channel: URI
    payload: dict[str, Any]


class OtlpExportTracesNotification(AhpModel):
    """``otlp/exportTraces`` — OpenTelemetry trace spans (OTLP/JSON ExportTraceServiceRequest in ``payload``)."""

    channel: URI
    payload: dict[str, Any]


class OtlpExportMetricsNotification(AhpModel):
    """``otlp/exportMetrics`` — OpenTelemetry metric data points (OTLP/JSON ExportMetricsServiceRequest in ``payload``)."""

    channel: URI
    payload: dict[str, Any]


NOTIFICATIONS: dict[str, type[AhpModel]] = {
    "action": ActionNotification,
    "root/sessionAdded": SessionAddedNotification,
    "root/sessionRemoved": SessionRemovedNotification,
    "root/sessionSummaryChanged": SessionSummaryChangedNotification,
    "auth/required": AuthRequiredNotification,
    "root/progress": ProgressNotification,
    "otlp/exportLogs": OtlpExportLogsNotification,
    "otlp/exportTraces": OtlpExportTracesNotification,
    "otlp/exportMetrics": OtlpExportMetricsNotification,
}
