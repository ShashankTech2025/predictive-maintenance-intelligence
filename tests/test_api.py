import json
import pytest

def test_health_api(client):
    """GET /api/health returns 200 and valid component health statuses."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["machine_learning"]["model_type"] == "XGBClassifier"


def test_dashboard_stats_api(client):
    """GET /api/dashboard/stats returns fleet metrics."""
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    res = response.get_json()
    assert res["status"] == "success"
    data = res["data"]
    assert "total_machines" in data
    assert "total_predictions" in data
    assert "risk_distribution" in data
    assert data["total_machines"] >= 3


def test_machines_crud_api(client):
    """Tests GET /api/machines, POST /api/machines, and duplicate prevention."""
    # 1. List machines
    res = client.get("/api/machines")
    assert res.status_code == 200
    initial_count = res.get_json()["count"]

    # 2. Register new machine
    payload = {"machine_name": "New Milling Line 99", "machine_type": "M"}
    res_post = client.post("/api/machines", json=payload)
    assert res_post.status_code == 201
    mid = res_post.get_json()["data"]["machine_id"]

    # 3. Duplicate registration should return 409 Conflict
    res_dup = client.post("/api/machines", json=payload)
    assert res_dup.status_code == 409

    # 4. Get by ID
    res_get = client.get(f"/api/machines/{mid}")
    assert res_get.status_code == 200
    assert res_get.get_json()["data"]["machine_name"] == "New Milling Line 99"

    # 5. Invalid machine type should return 400
    res_invalid = client.post("/api/machines", json={"machine_name": "Bad Machine", "machine_type": "Z"})
    assert res_invalid.status_code == 400


def test_predict_api_valid_telemetry(client):
    """
    POST /api/predict with Machine B parameters.
    Verifies inference, recommendations, and XAI attributions.
    """
    payload = {
        "machine_name": "Prediction Test Machine B",
        "machine_type": "M",
        "air_temperature": 302.0,
        "process_temperature": 311.0,
        "rotational_speed": 1400.0,
        "torque": 55.0,
        "tool_wear": 220.0,
        "include_xai": True
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()["data"]

    assert data["failure_probability"] == pytest.approx(85.46, abs=1e-2)
    assert data["machine_status"] == "FAILURE RISK"
    assert data["risk_level"] == "HIGH"
    assert data["prediction_id"] is not None
    assert len(data["recommendations"]) >= 2

    # Check XAI block
    assert "xai" in data
    assert data["xai"]["available"] is True
    assert len(data["xai"]["top_risk_drivers"]) > 0


def test_predict_api_validation_errors(client):
    """Verifies input validation triggers 400 Bad Request."""
    # Missing required field
    res_missing = client.post("/api/predict", json={"air_temperature": 300})
    assert res_missing.status_code == 400

    # Negative temperatures
    res_neg_temp = client.post("/api/predict", json={
        "machine_name": "Test",
        "machine_type": "L",
        "air_temperature": -10.0,
        "process_temperature": 310.0,
        "rotational_speed": 1500.0,
        "torque": 40.0,
        "tool_wear": 50.0
    })
    assert res_neg_temp.status_code == 400

    # Zero or negative rotational speed
    res_zero_rpm = client.post("/api/predict", json={
        "machine_name": "Test",
        "machine_type": "L",
        "air_temperature": 300.0,
        "process_temperature": 310.0,
        "rotational_speed": 0.0,
        "torque": 40.0,
        "tool_wear": 50.0
    })
    assert res_zero_rpm.status_code == 400


def test_machine_history_api(client):
    """GET /api/machines/<id>/history returns telemetry and prediction logs."""
    response = client.get("/api/machines/1/history")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert "machine" in data
    assert "prediction_history" in data
    assert "sensor_history" in data

    # Non-existent machine returns 404
    res_404 = client.get("/api/machines/9999/history")
    assert res_404.status_code == 404


def test_maintenance_api(client):
    """GET and PUT on /api/maintenance."""
    # List maintenance records
    res_list = client.get("/api/maintenance")
    assert res_list.status_code == 200
    records = res_list.get_json()["data"]
    assert len(records) > 0
    rec_id = records[0]["record_id"]

    # Update status to IN_PROGRESS
    res_put = client.put(f"/api/maintenance/{rec_id}/status", json={"status": "IN_PROGRESS"})
    assert res_put.status_code == 200

    # Invalid status returns 400
    res_bad = client.put(f"/api/maintenance/{rec_id}/status", json={"status": "INVALID_STATUS"})
    assert res_bad.status_code == 400


def test_reports_api(client):
    """Tests CSV and PDF report streaming endpoints."""
    # CSV fleet export
    res_csv = client.get("/api/reports/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.content_type
    assert b"Machine ID,Machine Name,Machine Type" in res_csv.data

    # PDF machine certificate
    res_pdf = client.get("/api/reports/pdf/1")
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.content_type
    assert res_pdf.data.startswith(b"%PDF")

