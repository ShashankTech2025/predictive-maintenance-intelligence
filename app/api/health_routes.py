from flask import jsonify
from app.api import api_bp
from app.database.connection import get_db
from app.services.ml_service import MLModelService

@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    db_status = "unhealthy"
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        if cur.fetchone()[0] == 1:
            db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    ml_summary = {}
    try:
        ml_service = MLModelService()
        ml_summary = ml_service.get_model_summary()
    except Exception as e:
        ml_summary = {"error": str(e)}

    is_healthy = (db_status == "healthy") and (ml_summary.get("model_type") == "XGBClassifier")

    return jsonify({
        "status": "healthy" if is_healthy else "degraded",
        "database": db_status,
        "machine_learning": ml_summary
    }), 200 if is_healthy else 503

