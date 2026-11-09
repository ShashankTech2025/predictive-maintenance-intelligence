from flask import jsonify
from app.api import api_bp
from app.database.connection import get_db
from app.database.queries import get_fleet_summary

@api_bp.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """
    Returns aggregated fleet statistics and recent events.
    Calculates current machine status based on the LATEST prediction per machine.
    """
    conn = get_db()
    summary = get_fleet_summary(conn)
    return jsonify({
        "status": "success",
        "data": summary
    }), 200

