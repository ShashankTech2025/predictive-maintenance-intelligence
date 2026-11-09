import sqlite3
from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.app_errorhandler(400)
def bad_request(error):
    return jsonify({
        "status": "error",
        "code": 400,
        "message": getattr(error, "description", "Bad Request")
    }), 400

@api_bp.app_errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "code": 404,
        "message": getattr(error, "description", "Resource Not Found")
    }), 404

@api_bp.app_errorhandler(409)
def conflict(error):
    return jsonify({
        "status": "error",
        "code": 409,
        "message": getattr(error, "description", "Conflict: Resource already exists")
    }), 409

@api_bp.app_errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "status": "error",
        "code": 500,
        "message": "Internal Server Error"
    }), 500

# Import routes after Blueprint is defined to avoid circular imports
from app.api import (
    health_routes,
    dashboard_routes,
    machine_routes,
    prediction_routes,
    maintenance_routes,
    report_routes
)

