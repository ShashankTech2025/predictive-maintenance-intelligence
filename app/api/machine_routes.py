import sqlite3
from flask import request, jsonify
from app.api import api_bp
from app.database.connection import get_db
from app.database.queries import (
    get_machines,
    get_machine_by_id,
    register_machine,
    update_machine,
    get_machine_history
)

@api_bp.route("/machines", methods=["GET"])
def list_machines():
    """List registered machines with optional filtering."""
    machine_type = request.args.get("type", "").strip().upper() or None
    search = request.args.get("search", "").strip() or None

    if machine_type and machine_type not in ["L", "M", "H"]:
        return jsonify({
            "status": "error",
            "message": "Invalid machine type filter. Allowed: L, M, H."
        }), 400

    conn = get_db()
    machines = get_machines(conn, machine_type=machine_type, search=search)
    return jsonify({
        "status": "success",
        "count": len(machines),
        "data": machines
    }), 200


@api_bp.route("/machines", methods=["POST"])
def create_machine():
    """Registers a new machine."""
    payload = request.get_json(silent=True) or {}
    machine_name = str(payload.get("machine_name", "")).strip()
    machine_type = str(payload.get("machine_type", "")).strip().upper()

    if not machine_name:
        return jsonify({
            "status": "error",
            "message": "Field 'machine_name' is required and cannot be blank."
        }), 400

    if machine_type not in ["L", "M", "H"]:
        return jsonify({
            "status": "error",
            "message": f"Field 'machine_type' must be 'L', 'M', or 'H'. Received: '{machine_type}'"
        }), 400

    conn = get_db()
    try:
        machine_id = register_machine(conn, machine_name, machine_type)
        return jsonify({
            "status": "success",
            "message": f"Machine '{machine_name}' registered successfully.",
            "data": {
                "machine_id": machine_id,
                "machine_name": machine_name,
                "machine_type": machine_type
            }
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": f"A machine with the name '{machine_name}' already exists."
        }), 409


@api_bp.route("/machines/<int:machine_id>", methods=["GET"])
def get_machine(machine_id: int):
    """Retrieves a single machine by ID."""
    conn = get_db()
    machine = get_machine_by_id(conn, machine_id)
    if not machine:
        return jsonify({
            "status": "error",
            "message": f"Machine with ID {machine_id} not found."
        }), 404

    return jsonify({
        "status": "success",
        "data": machine
    }), 200


@api_bp.route("/machines/<int:machine_id>", methods=["PUT"])
def update_machine_route(machine_id: int):
    """Updates machine details."""
    payload = request.get_json(silent=True) or {}
    machine_name = str(payload.get("machine_name", "")).strip()
    machine_type = str(payload.get("machine_type", "")).strip().upper()

    if not machine_name or machine_type not in ["L", "M", "H"]:
        return jsonify({
            "status": "error",
            "message": "Valid 'machine_name' and 'machine_type' (L, M, H) are required."
        }), 400

    conn = get_db()
    existing = get_machine_by_id(conn, machine_id)
    if not existing:
        return jsonify({
            "status": "error",
            "message": f"Machine with ID {machine_id} not found."
        }), 404

    try:
        success = update_machine(conn, machine_id, machine_name, machine_type)
        return jsonify({
            "status": "success",
            "message": f"Machine ID {machine_id} updated successfully."
        }), 200
    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": f"Another machine with name '{machine_name}' already exists."
        }), 409


@api_bp.route("/machines/<int:machine_id>/history", methods=["GET"])
def get_machine_history_route(machine_id: int):
    """Retrieves comprehensive prediction and sensor telemetry history."""
    conn = get_db()
    history = get_machine_history(conn, machine_id)
    if not history:
        return jsonify({
            "status": "error",
            "message": f"Machine with ID {machine_id} not found."
        }), 404

    return jsonify({
        "status": "success",
        "data": history
    }), 200

