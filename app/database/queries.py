import sqlite3
import datetime
from typing import Dict, List, Any, Optional

def get_fleet_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Computes fleet KPIs, ensuring current machine status is derived
    strictly from the LATEST prediction per machine.
    """
    cur = conn.cursor()

    # Total counts
    cur.execute("SELECT COUNT(*) FROM machines;")
    total_machines = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM predictions;")
    total_predictions = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sensor_readings;")
    total_sensor_readings = cur.fetchone()[0]

    # Query latest prediction per machine
    cur.execute("""
        SELECT 
            m.machine_id,
            m.machine_name,
            m.machine_type,
            m.created_at,
            p.prediction_id,
            p.failure_probability,
            p.machine_status,
            p.risk_level,
            p.recommendations,
            p.predicted_at
        FROM machines m
        LEFT JOIN predictions p ON p.prediction_id = (
            SELECT MAX(p2.prediction_id)
            FROM predictions p2
            WHERE p2.machine_id = m.machine_id
        )
        ORDER BY m.machine_id ASC;
    """)
    machine_status_rows = [dict(row) for row in cur.fetchall()]

    # Calculate risk distribution and active failure alerts across current machine statuses
    risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNMONITORED": 0}
    high_risk_alerts = 0
    failure_risk_machines = 0

    for m in machine_status_rows:
        risk = m["risk_level"]
        if risk in risk_distribution:
            risk_distribution[risk] += 1
        else:
            risk_distribution["UNMONITORED"] += 1

        if m["machine_status"] == "FAILURE RISK":
            failure_risk_machines += 1
        if risk == "HIGH":
            high_risk_alerts += 1

    # Recent 10 predictions
    cur.execute("""
        SELECT 
            p.prediction_id,
            p.machine_id,
            m.machine_name,
            m.machine_type,
            p.failure_probability,
            p.machine_status,
            p.risk_level,
            p.recommendations,
            p.predicted_at
        FROM predictions p
        JOIN machines m ON m.machine_id = p.machine_id
        ORDER BY p.prediction_id DESC
        LIMIT 10;
    """)
    recent_predictions = [dict(row) for row in cur.fetchall()]

    # Recent 10 maintenance records
    cur.execute("""
        SELECT 
            mr.record_id,
            mr.machine_id,
            m.machine_name,
            mr.priority,
            mr.action_item,
            mr.status,
            mr.created_at,
            mr.resolved_at
        FROM maintenance_records mr
        JOIN machines m ON m.machine_id = mr.machine_id
        ORDER BY mr.record_id DESC
        LIMIT 10;
    """)
    recent_maintenance = [dict(row) for row in cur.fetchall()]

    return {
        "total_machines": total_machines,
        "total_predictions": total_predictions,
        "total_sensor_readings": total_sensor_readings,
        "high_risk_alerts": high_risk_alerts,
        "failure_risk_machines": failure_risk_machines,
        "risk_distribution": risk_distribution,
        "machine_statuses": machine_status_rows,
        "recent_predictions": recent_predictions,
        "recent_maintenance": recent_maintenance
    }


def get_machines(conn: sqlite3.Connection, machine_type: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all registered machines with their latest health telemetry."""
    cur = conn.cursor()
    query = """
        SELECT 
            m.machine_id,
            m.machine_name,
            m.machine_type,
            m.created_at,
            p.prediction_id,
            p.failure_probability,
            p.machine_status,
            p.risk_level,
            p.recommendations,
            p.predicted_at,
            sr.air_temperature,
            sr.process_temperature,
            sr.rotational_speed,
            sr.torque,
            sr.tool_wear,
            sr.recorded_at
        FROM machines m
        LEFT JOIN predictions p ON p.prediction_id = (
            SELECT MAX(p2.prediction_id)
            FROM predictions p2
            WHERE p2.machine_id = m.machine_id
        )
        LEFT JOIN sensor_readings sr ON sr.reading_id = (
            SELECT MAX(sr2.reading_id)
            FROM sensor_readings sr2
            WHERE sr2.machine_id = m.machine_id
        )
        WHERE 1=1
    """
    params = []
    if machine_type:
        query += " AND m.machine_type = ?"
        params.append(machine_type)
    if search:
        query += " AND m.machine_name LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY m.machine_id ASC;"
    cur.execute(query, params)
    return [dict(row) for row in cur.fetchall()]


def get_machine_by_id(conn: sqlite3.Connection, machine_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves machine metadata by ID."""
    cur = conn.cursor()
    cur.execute("SELECT machine_id, machine_name, machine_type, created_at FROM machines WHERE machine_id = ?;", (machine_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_machine_by_name(conn: sqlite3.Connection, machine_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves machine metadata by unique machine name."""
    cur = conn.cursor()
    cur.execute("SELECT machine_id, machine_name, machine_type, created_at FROM machines WHERE machine_name = ?;", (machine_name,))
    row = cur.fetchone()
    return dict(row) if row else None


def register_machine(conn: sqlite3.Connection, machine_name: str, machine_type: str) -> int:
    """Registers a new machine. Enforces UNIQUE machine_name."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO machines (machine_name, machine_type) VALUES (?, ?);",
        (machine_name.strip(), machine_type.strip().upper())
    )
    conn.commit()
    return cur.lastrowid


def update_machine(conn: sqlite3.Connection, machine_id: int, machine_name: str, machine_type: str) -> bool:
    """Updates machine details."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE machines SET machine_name = ?, machine_type = ? WHERE machine_id = ?;",
        (machine_name.strip(), machine_type.strip().upper(), machine_id)
    )
    conn.commit()
    return cur.rowcount > 0


def get_machine_history(conn: sqlite3.Connection, machine_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves complete historical predictions and sensor readings for a machine."""
    machine = get_machine_by_id(conn, machine_id)
    if not machine:
        return None

    cur = conn.cursor()
    # Predictions history
    cur.execute("""
        SELECT prediction_id, failure_probability, machine_status, risk_level, recommendations, predicted_at
        FROM predictions
        WHERE machine_id = ?
        ORDER BY prediction_id DESC;
    """, (machine_id,))
    predictions = [dict(row) for row in cur.fetchall()]

    # Sensor telemetry history
    cur.execute("""
        SELECT reading_id, air_temperature, process_temperature, rotational_speed, torque, tool_wear, recorded_at
        FROM sensor_readings
        WHERE machine_id = ?
        ORDER BY reading_id DESC;
    """, (machine_id,))
    readings = [dict(row) for row in cur.fetchall()]

    # Maintenance history
    cur.execute("""
        SELECT record_id, priority, action_item, status, created_at, resolved_at
        FROM maintenance_records
        WHERE machine_id = ?
        ORDER BY record_id DESC;
    """, (machine_id,))
    maintenance = [dict(row) for row in cur.fetchall()]

    return {
        "machine": machine,
        "prediction_history": predictions,
        "sensor_history": readings,
        "maintenance_history": maintenance
    }


def save_telemetry_and_prediction_transaction(
    conn: sqlite3.Connection,
    machine_id: int,
    sensor_data: Dict[str, float],
    prediction_result: Dict[str, Any],
    recommendation_result: Dict[str, Any]
) -> Dict[str, int]:
    """
    Executes an atomic transaction inserting:
    1. Sensor reading
    2. Prediction log
    3. Itemized maintenance tasks
    """
    cur = conn.cursor()
    try:
        # 1. Insert sensor telemetry
        cur.execute("""
            INSERT INTO sensor_readings 
            (machine_id, air_temperature, process_temperature, rotational_speed, torque, tool_wear)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (
            machine_id,
            sensor_data["air_temperature"],
            sensor_data["process_temperature"],
            sensor_data["rotational_speed"],
            sensor_data["torque"],
            sensor_data["tool_wear"]
        ))
        reading_id = cur.lastrowid

        # 2. Insert prediction
        combined_recs = recommendation_result.get("combined_text", "")
        cur.execute("""
            INSERT INTO predictions
            (machine_id, failure_probability, machine_status, risk_level, recommendations)
            VALUES (?, ?, ?, ?, ?);
        """, (
            machine_id,
            prediction_result["failure_probability"],
            prediction_result["machine_status"],
            recommendation_result["risk_level"],
            combined_recs
        ))
        prediction_id = cur.lastrowid

        # 3. Insert itemized maintenance records
        action_items = recommendation_result.get("action_items", [])
        for item in action_items:
            cur.execute("""
                INSERT INTO maintenance_records
                (machine_id, prediction_id, priority, action_item, status)
                VALUES (?, ?, ?, ?, 'PENDING');
            """, (
                machine_id,
                prediction_id,
                item["priority"],
                item["action"]
            ))

        conn.commit()
        return {
            "reading_id": reading_id,
            "prediction_id": prediction_id
        }
    except Exception:
        conn.rollback()
        raise


def get_all_predictions(conn: sqlite3.Connection, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieves fleet-wide predictions log with machine details."""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            p.prediction_id,
            p.machine_id,
            m.machine_name,
            m.machine_type,
            p.failure_probability,
            p.machine_status,
            p.risk_level,
            p.recommendations,
            p.predicted_at
        FROM predictions p
        JOIN machines m ON m.machine_id = p.machine_id
        ORDER BY p.prediction_id DESC
        LIMIT ? OFFSET ?;
    """, (limit, offset))
    return [dict(row) for row in cur.fetchall()]


def get_maintenance_records(
    conn: sqlite3.Connection,
    machine_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieves maintenance records with optional filters."""
    cur = conn.cursor()
    query = """
        SELECT 
            mr.record_id,
            mr.machine_id,
            m.machine_name,
            m.machine_type,
            mr.prediction_id,
            mr.priority,
            mr.action_item,
            mr.status,
            mr.created_at,
            mr.resolved_at
        FROM maintenance_records mr
        JOIN machines m ON m.machine_id = mr.machine_id
        WHERE 1=1
    """
    params = []
    if machine_id:
        query += " AND mr.machine_id = ?"
        params.append(machine_id)
    if status:
        query += " AND mr.status = ?"
        params.append(status)

    query += " ORDER BY mr.record_id DESC LIMIT ?;"
    params.append(limit)

    cur.execute(query, params)
    return [dict(row) for row in cur.fetchall()]


def update_maintenance_status(conn: sqlite3.Connection, record_id: int, status: str) -> bool:
    """Updates status ('PENDING', 'IN_PROGRESS', 'RESOLVED') and records resolution timestamp."""
    cur = conn.cursor()
    resolved_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "RESOLVED" else None
    cur.execute("""
        UPDATE maintenance_records
        SET status = ?, resolved_at = ?
        WHERE record_id = ?;
    """, (status, resolved_at, record_id))
    conn.commit()
    return cur.rowcount > 0

