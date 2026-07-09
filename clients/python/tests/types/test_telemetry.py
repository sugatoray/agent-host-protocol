"""Tests for TelemetryCapabilities and its presence in InitializeResult."""
from ahp.types.commands import InitializeResult, TelemetryCapabilities


def test_telemetry_capabilities_all_fields_optional():
    t = TelemetryCapabilities()
    assert t.logs is None
    assert t.traces is None
    assert t.metrics is None


def test_telemetry_capabilities_with_uris():
    t = TelemetryCapabilities(
        logs="ahp-otlp://logs/{level}",
        traces="ahp-otlp://traces",
        metrics="ahp-otlp://metrics",
    )
    assert t.logs == "ahp-otlp://logs/{level}"
    assert t.traces == "ahp-otlp://traces"
    assert t.metrics == "ahp-otlp://metrics"


def test_telemetry_capabilities_partial():
    t = TelemetryCapabilities(logs="ahp-otlp://logs")
    assert t.logs == "ahp-otlp://logs"
    assert t.traces is None
    assert t.metrics is None


def test_telemetry_capabilities_round_trips_from_wire():
    raw = {"logs": "ahp-otlp://logs/{level}", "traces": "ahp-otlp://traces"}
    t = TelemetryCapabilities.model_validate(raw)
    assert t.logs == "ahp-otlp://logs/{level}"
    assert t.traces == "ahp-otlp://traces"
    assert t.metrics is None


def test_initialize_result_telemetry_is_typed():
    raw = {
        "protocolVersion": "1.0.0",
        "serverSeq": 0,
        "snapshots": [],
        "telemetry": {"logs": "ahp-otlp://logs", "metrics": "ahp-otlp://metrics"},
    }
    result = InitializeResult.model_validate(raw)
    assert isinstance(result.telemetry, TelemetryCapabilities)
    assert result.telemetry.logs == "ahp-otlp://logs"
    assert result.telemetry.metrics == "ahp-otlp://metrics"
    assert result.telemetry.traces is None


def test_initialize_result_telemetry_absent():
    raw = {"protocolVersion": "1.0.0", "serverSeq": 0, "snapshots": []}
    result = InitializeResult.model_validate(raw)
    assert result.telemetry is None
