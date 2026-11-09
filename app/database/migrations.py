import shutil
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any
from config import Config

def backup_database(db_path: Path = None) -> Path:
    """
    Creates a verified, timestamped backup of the SQLite database.
    """
    db_path = Path(db_path or Config.DATABASE_PATH)
    if not db_path.exists():
        raise FileNotFoundError(f"Cannot backup non-existent database: {db_path}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    backup_path = db_path.parent / backup_filename

    # Copy database file
    shutil.copy2(db_path, backup_path)

    # Verify backup integrity
    conn = sqlite3.connect(str(backup_path))
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA integrity_check;")
        result = cur.fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"Backup integrity check failed: {result}")

        # Check existing table counts
        cur.execute("SELECT COUNT(*) FROM machines;")
        m_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sensor_readings;")
        s_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM predictions;")
        p_cnt = cur.fetchone()[0]

        print(f"[BACKUP VERIFIED] Saved to: {backup_path.name}")
        print(f"  Records: {m_cnt} machines, {s_cnt} sensor readings, {p_cnt} predictions")
    finally:
        conn.close()

    return backup_path


def run_migrations(db_path: Path = None) -> Dict[str, Any]:
    """
    Applies non-destructive schema migrations:
    - Adds `maintenance_records` table if not exists.
    - Adds foreign key performance indexes.
    - Backfills initial maintenance records from existing predictions if empty.
    - Verifies zero data loss and migration idempotency.
    """
    db_path = Path(db_path or Config.DATABASE_PATH)
    if not db_path.exists():
        raise FileNotFoundError(f"Target database not found: {db_path}")

    # Step 1: Pre-migration count audit
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM machines;")
    pre_m_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sensor_readings;")
    pre_s_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM predictions;")
    pre_p_cnt = cur.fetchone()[0]

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='maintenance_records';")
    has_maint_tbl = cur.fetchone() is not None
    pre_maint_cnt = 0
    if has_maint_tbl:
        cur.execute("SELECT COUNT(*) FROM maintenance_records;")
        pre_maint_cnt = cur.fetchone()[0]

    # Step 2: Apply Non-Destructive DDL
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

    # Step 3: Non-destructive backfill for historical predictions
    cur.execute("SELECT COUNT(*) FROM maintenance_records;")
    maint_count = cur.fetchone()[0]
    backfilled_count = 0

    if maint_count == 0 and pre_p_cnt > 0:
        cur.execute("""
            SELECT prediction_id, machine_id, risk_level, recommendations, predicted_at
            FROM predictions
            ORDER BY prediction_id ASC;
        """)
        predictions = cur.fetchall()
        for p in predictions:
            rec_text = p["recommendations"] or ""
            items = [item.strip() for item in rec_text.split(" | ") if item.strip()]
            for item in items:
                cur.execute("""
                    INSERT INTO maintenance_records
                    (machine_id, prediction_id, priority, action_item, status, created_at)
                    VALUES (?, ?, ?, ?, 'PENDING', ?)
                """, (p["machine_id"], p["prediction_id"], p["risk_level"], item, p["predicted_at"]))
                backfilled_count += 1

    conn.commit()

    # Step 4: Post-migration verification
    cur.execute("SELECT COUNT(*) FROM machines;")
    post_m_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sensor_readings;")
    post_s_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM predictions;")
    post_p_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM maintenance_records;")
    post_maint_cnt = cur.fetchone()[0]

    conn.close()

    # Integrity assertions
    assert pre_m_cnt == post_m_cnt, f"Machine count changed: {pre_m_cnt} -> {post_m_cnt}"
    assert pre_s_cnt == post_s_cnt, f"Sensor readings count changed: {pre_s_cnt} -> {post_s_cnt}"
    assert pre_p_cnt == post_p_cnt, f"Predictions count changed: {pre_p_cnt} -> {post_p_cnt}"

    return {
        "status": "SUCCESS",
        "pre_migration_counts": {
            "machines": pre_m_cnt,
            "sensor_readings": pre_s_cnt,
            "predictions": pre_p_cnt,
            "maintenance_records": pre_maint_cnt
        },
        "post_migration_counts": {
            "machines": post_m_cnt,
            "sensor_readings": post_s_cnt,
            "predictions": post_p_cnt,
            "maintenance_records": post_maint_cnt
        },
        "backfilled_records": backfilled_count
    }
