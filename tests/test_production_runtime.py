import os
import io
import pytest
import sqlite3
from pathlib import Path
from config import Config
from app import create_app
from app.database.connection import ensure_database_ready

def test_simulated_container_production_runtime(tmp_path):
    """
    Simulates production container runtime:
    - Dedicated persistent storage volume path
    - Production configuration (DEBUG=False, TESTING=False)
    - Full end-to-end verification of health, inference, DB persistence, CSV and PDF streaming.
    """
    simulated_persistent_volume = tmp_path / "var_data"
    simulated_persistent_volume.mkdir(parents=True, exist_ok=True)
    target_db = simulated_persistent_volume / "predictive_maintenance.db"

    # Set production environment variables
    os.environ["FLASK_ENV"] = "production"
    os.environ["SECRET_KEY"] = "production-runtime-verification-secret-key-32chars"
    os.environ["DATABASE_PATH"] = str(target_db)

    # Initialize production app with explicit target_db path
    app = create_app("production")
    app.config["DATABASE_PATH"] = target_db
    assert app.config["DEBUG"] is False
    assert app.config["TESTING"] is False

    with app.app_context():
        ensure_database_ready(target_db)

    with app.test_client() as client:
        # 1. Health check probe
        res_health = client.get("/api/health")
        assert res_health.status_code == 200
        health_data = res_health.get_json()
        assert health_data["status"] == "healthy"
        assert health_data["database"] == "healthy"
        assert health_data["machine_learning"]["model_type"] == "XGBClassifier"
        assert health_data["machine_learning"]["shap_explainer_loaded"] is True

        # 2. Test prediction execution and persistence to target DB
        pred_payload = {
            "machine_name": "Container Test Press 01",
            "machine_type": "M",
            "air_temperature": 302.0,
            "process_temperature": 311.0,
            "rotational_speed": 1400.0,
            "torque": 55.0,
            "tool_wear": 220.0,
            "save_to_db": True,
            "include_xai": True
        }
        res_pred = client.post("/api/predict", json=pred_payload)
        assert res_pred.status_code == 200
        pred_data = res_pred.get_json()["data"]
        assert pred_data["failure_probability"] == pytest.approx(85.46, abs=1e-2)
        assert pred_data["machine_status"] == "FAILURE RISK"
        assert pred_data["risk_level"] == "HIGH"
        new_mid = pred_data["machine_id"]

        # 3. Verify data physically written to persistent target database
        conn = sqlite3.connect(str(target_db))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM machines WHERE machine_id = ?;", (new_mid,))
        machine_row = cur.fetchone()
        assert machine_row is not None
        assert machine_row["machine_name"] == "Container Test Press 01"

        cur.execute("SELECT * FROM predictions WHERE machine_id = ?;", (new_mid,))
        pred_row = cur.fetchone()
        assert pred_row is not None
        assert pred_row["failure_probability"] == pytest.approx(85.46, abs=1e-2)

        cur.execute("SELECT * FROM maintenance_records WHERE machine_id = ?;", (new_mid,))
        maint_rows = cur.fetchall()
        assert len(maint_rows) >= 2  # Action items recorded
        conn.close()

        # 4. Verify CSV fleet export
        res_csv = client.get("/api/reports/csv")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.content_type
        assert b"Container Test Press 01" in res_csv.data

        # 5. Verify PDF certificate generation
        res_pdf = client.get(f"/api/reports/pdf/{new_mid}")
        assert res_pdf.status_code == 200
        assert "application/pdf" in res_pdf.content_type
        assert res_pdf.data.startswith(b"%PDF")
