from flask import request, jsonify
from app.api import api_bp
from app.database.connection import get_db
from app.database.queries import get_maintenance_records, update_maintenance_status

@api_bp.route("/maintenance", methods=["GET"])
def list_maintenance():
    """Retrieves fleet maintenance records with optional filtering."""
    machine_id = request.args.get("machine_id", type=int)
    status = request.args.get("status", "").strip().upper() or None
    limit = max(1, min(200, int(request.args.get("limit", 100))))

    if status and status not in ["PENDING", "IN_PROGRESS", "RESOLVED"]:
        return jsonify({
            "status": "error",
            "message": "Status must be 'PENDING', 'IN_PROGRESS', or 'RESOLVED'."
        }), 400

    conn = get_db()
    records = get_maintenance_records(conn, machine_id=machine_id, status=status, limit=limit)
    return jsonify({
        "status": "success",
        "count": len(records),
        "data": records
    }), 200


@api_bp.route("/maintenance/<int:record_id>/status", methods=["PUT"])
def set_maintenance_status(record_id: int):
    """Updates the execution status of a maintenance directive."""
    payload = request.get_json(silent=True) or {}
    new_status = str(payload.get("status", "")).strip().upper()

    if new_status not in ["PENDING", "IN_PROGRESS", "RESOLVED"]:
        return jsonify({
            "status": "error",
            "message": "Field 'status' must be 'PENDING', 'IN_PROGRESS', or 'RESOLVED'."
        }), 400

    conn = get_db()
    updated = update_maintenance_status(conn, record_id, new_status)
    if not updated:
        return jsonify({
            "status": "error",
            "message": f"Maintenance record ID {record_id} not found."
        }), 404

    return jsonify({
        "status": "success",
        "message": f"Maintenance record {record_id} status updated to '{new_status}'."
    }), 200

