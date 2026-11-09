import pytest

def test_dashboard_view(client):
    """GET / and /dashboard render successfully."""
    for path in ["/", "/dashboard"]:
        res = client.get(path)
        assert res.status_code == 200
        assert b"Fleet Health" in res.data
        assert b"Current Fleet Risk Distribution" in res.data


def test_machines_view(client):
    """GET /machines renders machine monitoring view."""
    res = client.get("/machines")
    assert res.status_code == 200
    assert b"Machine Monitoring" in res.data
    assert b"Register Machine" in res.data


def test_predict_view(client):
    """GET /predict renders failure prediction interface."""
    res = client.get("/predict")
    assert res.status_code == 200
    assert b"Sensor Diagnostics" in res.data
    assert b"Run Predictive Failure Analysis" in res.data


def test_maintenance_view(client):
    """GET /maintenance renders maintenance task board."""
    res = client.get("/maintenance")
    assert res.status_code == 200
    assert b"Maintenance Directives" in res.data
    assert b"Actionable Directives" in res.data


def test_history_view(client):
    """GET /history renders telemetry audit trail."""
    res = client.get("/history")
    assert res.status_code == 200
    assert b"Prediction Logs" in res.data
    assert b"Historical Prediction Records" in res.data


def test_reports_view(client):
    """GET /reports renders reports download hub."""
    res = client.get("/reports")
    assert res.status_code == 200
    assert b"Reports Portal" in res.data
    assert b"Download Fleet CSV Export" in res.data


def test_settings_view(client):
    """GET /settings renders operational configurations view."""
    res = client.get("/settings")
    assert res.status_code == 200
    assert b"System Diagnostics" in res.data
    assert b"Maintenance Alert Thresholds" in res.data

