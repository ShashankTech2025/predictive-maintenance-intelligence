import os
import pytest
import sqlite3
from pathlib import Path
from app import create_app
from app.database.connection import init_db
from app.database.queries import register_machine, save_telemetry_and_prediction_transaction

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Provides an isolated temporary database path for test execution."""
    db_dir = tmp_path_factory.mktemp("db")
    db_file = db_dir / "test_predictive_maintenance.db"
    return db_file

@pytest.fixture
def app(test_db_path):
    """Creates a Flask test application bound strictly to the temporary test DB."""
    app = create_app("testing")
    app.config["DATABASE_PATH"] = test_db_path
    
    # Initialize schema in temporary DB
    with app.app_context():
        init_db(test_db_path)
        
        # Seed test machines if empty
        conn = sqlite3.connect(str(test_db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM machines;")
        if cur.fetchone()[0] == 0:
            m1_id = register_machine(conn, "Test Lathe 01", "L")
            m2_id = register_machine(conn, "Test CNC Milling 02", "M")
            m3_id = register_machine(conn, "Test Heavy Press 03", "H")
            
            # Seed an initial prediction for Machine 1
            sensor_data = {
                "air_temperature": 300.1,
                "process_temperature": 310.2,
                "rotational_speed": 1500.0,
                "torque": 40.0,
                "tool_wear": 50.0
            }
            pred_data = {
                "failure_probability": 0.05,
                "machine_status": "NORMAL"
            }
            rec_data = {
                "risk_level": "LOW",
                "combined_text": "Low failure risk: Continue routine monitoring.",
                "action_items": [{"priority": "LOW", "action": "Routine inspection"}]
            }
            save_telemetry_and_prediction_transaction(conn, m1_id, sensor_data, pred_data, rec_data)
        conn.close()

    yield app

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

