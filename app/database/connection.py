import sqlite3
import os
import shutil
from pathlib import Path
from flask import g, current_app
from config import Config

def get_db(db_path: Path = None) -> sqlite3.Connection:
    """
    Retrieves or establishes a database connection.
    If running within Flask application context, uses `g`.
    Otherwise, returns an independent connection.
    """
    if db_path is None:
        try:
            db_path = current_app.config.get("DATABASE_PATH")
        except RuntimeError:
            db_path = None
        if not db_path:
            _env = os.environ.get("DATABASE_PATH")
            db_path = Path(_env) if _env else Config.DATABASE_PATH

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if "g" in globals() and g is not None:
            if not hasattr(g, "_database"):
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                g._database = conn
            return g._database
    except (RuntimeError, AttributeError):
        pass

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def close_db(e=None):
    """Closes the current request's database connection."""
    try:
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()
            g._database = None
    except (RuntimeError, AttributeError):
        pass


def init_db(db_path: Path = None):
    """Initializes the database schema if creating a fresh database."""
    conn = get_db(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            machine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_name TEXT NOT NULL UNIQUE,
            machine_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            air_temperature REAL NOT NULL,
            process_temperature REAL NOT NULL,
            rotational_speed REAL NOT NULL,
            torque REAL NOT NULL,
            tool_wear REAL NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            failure_probability REAL NOT NULL,
            machine_status TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            recommendations TEXT,
            predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            prediction_id INTEGER,
            priority TEXT NOT NULL,
            action_item TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (machine_id) REFERENCES machines(machine_id),
            FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_machine ON sensor_readings(machine_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_predictions_machine ON predictions(machine_id, predicted_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_machine ON maintenance_records(machine_id, status);")

    conn.commit()
    if not ("g" in globals() and g is not None and hasattr(g, "_database")):
        conn.close()


def ensure_database_ready(target_db_path: Path = None, seed_db_path: Path = None):
    """
    Guarantees persistent database readiness:
    1. Copies tracked seed database to persistent storage ONLY IF target does not exist.
    2. NEVER overwrites an existing persistent database.
    3. Runs non-destructive migrations safely.
    """
    target = Path(target_db_path or Config.DATABASE_PATH)
    seed = Path(seed_db_path or (Config.BASE_DIR / "database" / "predictive_maintenance.db"))
    target.parent.mkdir(parents=True, exist_ok=True)

    from app.database.migrations import run_migrations

    if not target.exists():
        if seed.exists() and seed.resolve() != target.resolve():
            shutil.copy2(seed, target)
        else:
            init_db(target)
    
    # Run safe non-destructive migration on the target database
    run_migrations(target)
