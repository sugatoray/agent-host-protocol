"""Server -> client notification payloads (JSON-RPC notifications, no response).

Reconciled against canonical notification method names:
  - ``action``: ActionEnvelope broadcast
  - ``root/sessionAdded``: new session with channel URI + summary
  - ``root/sessionRemoved``: session gone (field: ``session`` URI)
  - ``root/sessionSummaryChanged``: existing session summary updated
  - ``auth/required``: host needs client to authenticate (field: ``resource``)
  - ``$/progress``: long-running operation progress
  - ``otlp/exportLogs``, ``otlp/exportTraces``, ``otlp/exportMetrics``: telemetry
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
    summary: dict[str, Any]  # ChatSummary / SessionSummary


class SessionRemovedNotification(AhpModel):
    """``root/sessionRemoved``."""

    session: URI  # NOT sessionUri — canonical field name


class SessionSummaryChangedNotification(AhpModel):
    """``root/sessionSummaryChanged`` — metadata on an existing session changed."""

    channel: URI
    changes: dict[str, Any]


class AuthRequiredNotification(AhpModel):
    """``auth/required`` — host is asking client to (re)authenticate.

    ``resource`` is the protected resource URI per RFC 9728.
    """

    resource: str  # NOT scheme — canonical field name


class ProgressNotification(AhpModel):
    """``$/progress`` — progress update for a long-running operation."""

    token: str | int
    value: dict[str, Any]


class OtlpExportLogsNotification(AhpModel):
    """``otlp/exportLogs`` — OpenTelemetry log records."""

    resource_logs: list[Any] = Field(default_factory=list, alias="resourceLogs")


class OtlpExportTracesNotification(AhpModel):
    """``otlp/exportTraces`` — OpenTelemetry trace spans."""

    resource_spans: list[Any] = Field(default_factory=list, alias="resourceSpans")


class OtlpExportMetricsNotification(AhpModel):
    """``otlp/exportMetrics`` — OpenTelemetry metric data points."""

    resource_metrics: list[Any] = Field(default_factory=list, alias="resourceMetrics")


NOTIFICATIONS: dict[str, type[AhpModel]] = {
    "action": ActionNotification,
    "root/sessionAdded": SessionAddedNotification,
    "root/sessionRemoved": SessionRemovedNotification,
    "root/sessionSummaryChanged": SessionSummaryChangedNotification,
    "auth/required": AuthRequiredNotification,
    "$/progress": ProgressNotification,
    "otlp/exportLogs": OtlpExportLogsNotification,
    "otlp/exportTraces": OtlpExportTracesNotification,
    "otlp/exportMetrics": OtlpExportMetricsNotification,
}
