"""Tests for notification field shapes against canonical types/*.ts."""
import pytest
from ahp.types.notifications import (
    NOTIFICATIONS,
    ActionNotification,
    AuthRequiredNotification,
    OtlpExportLogsNotification,
    OtlpExportMetricsNotification,
    OtlpExportTracesNotification,
    ProgressNotification,
    SessionAddedNotification,
    SessionRemovedNotification,
    SessionSummaryChangedNotification,
)


# ── auth/required ────────────────────────────────────────────────────────────

def test_auth_required_has_channel():
    n = AuthRequiredNotification(channel="ahp-root://", resource="https://api.example.com")
    assert n.channel == "ahp-root://"


def test_auth_required_has_reason_optional():
    n = AuthRequiredNotification(channel="ahp-root://", resource="https://api.example.com", reason="expired")
    assert n.reason == "expired"
    n2 = AuthRequiredNotification(channel="ahp-root://", resource="https://api.example.com")
    assert n2.reason is None


def test_auth_required_parses_camel_case():
    raw = {"channel": "ahp-root://", "resource": "https://api.example.com", "reason": "required"}
    n = AuthRequiredNotification.model_validate(raw)
    assert n.reason == "required"


# ── root/sessionRemoved ──────────────────────────────────────────────────────

def test_session_removed_has_channel():
    n = SessionRemovedNotification(channel="ahp-root://", session="ahp-session:/abc")
    assert n.channel == "ahp-root://"
    assert n.session == "ahp-session:/abc"


# ── root/sessionSummaryChanged ───────────────────────────────────────────────

def test_session_summary_changed_has_session_uri():
    n = SessionSummaryChangedNotification(
        channel="ahp-root://",
        session="ahp-session:/abc",
        changes={"title": "new title"},
    )
    assert n.session == "ahp-session:/abc"


# ── root/progress ────────────────────────────────────────────────────────────

def test_progress_is_registered_under_root_progress():
    assert "root/progress" in NOTIFICATIONS
    assert "$/progress" not in NOTIFICATIONS


def test_progress_has_canonical_fields():
    n = ProgressNotification(
        channel="ahp-root://",
        progress_token="tok-1",
        progress=100,
        total=500,
        message="Downloading...",
    )
    assert n.channel == "ahp-root://"
    assert n.progress_token == "tok-1"
    assert n.progress == 100
    assert n.total == 500
    assert n.message == "Downloading..."


def test_progress_total_and_message_are_optional():
    n = ProgressNotification(channel="ahp-root://", progress_token="tok-1", progress=0)
    assert n.total is None
    assert n.message is None


def test_progress_parses_camel_case():
    raw = {"channel": "ahp-root://", "progressToken": "tok-1", "progress": 18874368, "total": 41957498}
    n = ProgressNotification.model_validate(raw)
    assert n.progress_token == "tok-1"
    assert n.total == 41957498


# ── otlp/export* ─────────────────────────────────────────────────────────────

def test_otlp_logs_has_channel_and_payload():
    n = OtlpExportLogsNotification(
        channel="ahp-otlp://logs",
        payload={"resourceLogs": []},
    )
    assert n.channel == "ahp-otlp://logs"
    assert n.payload == {"resourceLogs": []}


def test_otlp_traces_has_channel_and_payload():
    n = OtlpExportTracesNotification(
        channel="ahp-otlp://traces",
        payload={"resourceSpans": []},
    )
    assert n.channel == "ahp-otlp://traces"


def test_otlp_metrics_has_channel_and_payload():
    n = OtlpExportMetricsNotification(
        channel="ahp-otlp://metrics",
        payload={"resourceMetrics": []},
    )
    assert n.channel == "ahp-otlp://metrics"


def test_otlp_logs_no_flattened_resource_logs_field():
    n = OtlpExportLogsNotification(channel="ahp-otlp://logs", payload={"resourceLogs": [1, 2]})
    assert not hasattr(n, "resource_logs")


# ── registry completeness ─────────────────────────────────────────────────────

def test_notifications_registry_keys():
    expected = {
        "action",
        "root/sessionAdded",
        "root/sessionRemoved",
        "root/sessionSummaryChanged",
        "auth/required",
        "root/progress",
        "otlp/exportLogs",
        "otlp/exportTraces",
        "otlp/exportMetrics",
    }
    assert expected == set(NOTIFICATIONS.keys())
