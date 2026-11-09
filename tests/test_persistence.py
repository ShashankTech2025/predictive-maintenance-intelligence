import os
import sqlite3
import shutil
from pathlib import Path
from config import Config
from app.database.connection import ensure_database_ready, init_db
from app.database.queries import register_machine, get_machines

def test_seed_database_copied_only_when_target_missing(tmp_path):
    """
    Verifies that if target persistent database does not exist,
    it is initialized from the tracked seed database with all initial records intact.
    """
    persistent_dir = tmp_path / "persistent_storage"
    target_db = persistent_dir / "predictive_maintenance.db"
    seed_db = Config.BASE_DIR / "database" / "predictive_maintenance.db"

    assert not target_db.exists()

    # Call ensure_database_ready
    ensure_database_ready(target_db_path=target_db, seed_db_path=seed_db)

    assert target_db.exists()

    # Verify seed records were copied
    conn = sqlite3.connect(str(target_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM machines;")
    m_count = cur.fetchone()[0]
    conn.close()

    assert m_count >= 3


def test_persistent_database_never_overwritten_on_restart(tmp_path):
    """
    CRITICAL REQUIREMENT:
    Simulates container restart and redeployment:
    1. Creates target persistent database.
    2. Inserts new machine record during runtime.
    3. Simulates container restart calling ensure_database_ready again.
    4. Confirms the new record was NEVER overwritten or lost.
    """
    persistent_dir = tmp_path / "persistent_storage_2"
    target_db = persistent_dir / "predictive_maintenance.db"
    seed_db = Config.BASE_DIR / "database" / "predictive_maintenance.db"

    # First boot
    ensure_database_ready(target_db_path=target_db, seed_db_path=seed_db)

    # Runtime modification: Add new machine
    conn = sqlite3.connect(str(target_db))
    new_mid = register_machine(conn, "Custom CNC Milling Machine X99", "M")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM machines;")
    count_after_insert = cur.fetchone()[0]
    conn.close()

    # Second boot (simulated redeployment / app restart)
    ensure_database_ready(target_db_path=target_db, seed_db_path=seed_db)

    # Verify data survived
    conn2 = sqlite3.connect(str(target_db))
    conn2.row_factory = sqlite3.Row
    machines = get_machines(conn2)
    cur2 = conn2.cursor()
    cur2.execute("SELECT COUNT(*) FROM machines;")
    count_after_restart = cur2.fetchone()[0]
    conn2.close()

    assert count_after_restart == count_after_insert
    assert any(m["machine_name"] == "Custom CNC Milling Machine X99" for m in machines)


def test_migrations_idempotency_and_safety(tmp_path):
    """Verifies running migrations multiple times causes zero errors and zero record changes."""
    target_db = tmp_path / "migration_test.db"
    seed_db = Config.BASE_DIR / "database" / "predictive_maintenance.db"
    
    ensure_database_ready(target_db_path=target_db, seed_db_path=seed_db)

    from app.database.migrations import run_migrations

    # Run migration a second time
    result2 = run_migrations(target_db)
    assert result2["status"] == "SUCCESS"

    # Run migration a third time
    result3 = run_migrations(target_db)
    assert result3["status"] == "SUCCESS"
    assert result3["pre_migration_counts"] == result3["post_migration_counts"]

