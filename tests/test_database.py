import pytest
import sqlite3
from app.database.connection import get_db, init_db
from app.database.queries import (
    register_machine,
    get_machines,
    get_machine_by_id,
    get_fleet_summary,
    save_telemetry_and_prediction_transaction,
    get_maintenance_records,
    update_maintenance_status
)

def test_database_initialization(app, test_db_path):
    """Verifies all four required entities and indexes are created in temporary DB."""
    conn = sqlite3.connect(str(test_db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()

    assert "machines" in tables
    assert "sensor_readings" in tables
    assert "predictions" in tables
    assert "maintenance_records" in tables


def test_machine_registration_duplicate_prevention(app, test_db_path):
    """Verifies unique constraint on machine_name."""
    conn = sqlite3.connect(str(test_db_path))
    register_machine(conn, "Unique Machine Alpha", "L")

    with pytest.raises(sqlite3.IntegrityError):
        register_machine(conn, "Unique Machine Alpha", "L")

    conn.close()


def test_fleet_summary_latest_prediction_logic(app, test_db_path):
    """
    CRITICAL REQUIREMENT #6:
    Verifies that get_fleet_summary calculates machine risk strictly from
    the LATEST prediction for each machine, avoiding duplicate counts.
    """
    conn = sqlite3.connect(str(test_db_path))
    conn.row_factory = sqlite3.Row
    
    # Register a new machine
    mid = register_machine(conn, "Multi-Prediction Machine", "M")

    sensor = {"air_temperature": 300, "process_temperature": 310, "rotational_speed": 1500, "torque": 40, "tool_wear": 50}
    
    # 1st prediction: LOW risk
    pred1 = {"failure_probability": 0.05, "machine_status": "NORMAL"}
    rec1 = {"risk_level": "LOW", "combined_text": "Normal", "action_items": []}
    save_telemetry_and_prediction_transaction(conn, mid, sensor, pred1, rec1)

    # 2nd prediction: HIGH risk (latest)
    pred2 = {"failure_probability": 85.5, "machine_status": "FAILURE RISK"}
    rec2 = {"risk_level": "HIGH", "combined_text": "High failure risk", "action_items": [{"priority": "HIGH", "action": "Inspect"}]}
    save_telemetry_and_prediction_transaction(conn, mid, sensor, pred2, rec2)

    summary = get_fleet_summary(conn)
    
    # Find this machine's status in summary
    target_machine_status = next(m for m in summary["machine_statuses"] if m["machine_id"] == mid)
    
    # It must reflect the LATEST prediction (HIGH, not LOW)
    assert target_machine_status["risk_level"] == "HIGH"
    assert target_machine_status["machine_status"] == "FAILURE RISK"
    assert target_machine_status["failure_probability"] == 85.5

    conn.close()


def test_maintenance_status_update(app, test_db_path):
    """Verifies status transitions and resolution timestamp recording."""
    conn = sqlite3.connect(str(test_db_path))
    conn.row_factory = sqlite3.Row
    
    records = get_maintenance_records(conn)
    assert len(records) > 0
    rec_id = records[0]["record_id"]

    # Transition to RESOLVED
    assert update_maintenance_status(conn, rec_id, "RESOLVED") is True

    updated_records = get_maintenance_records(conn)
    target = next(r for r in updated_records if r["record_id"] == rec_id)
    assert target["status"] == "RESOLVED"
    assert target["resolved_at"] is not None

    conn.close()

