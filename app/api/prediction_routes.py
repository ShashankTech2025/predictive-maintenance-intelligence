from flask import request, jsonify
from app.api import api_bp
from app.database.connection import get_db
from app.database.queries import (
    get_machine_by_id,
    get_machine_by_name,
    register_machine,
    save_telemetry_and_prediction_transaction,
    get_all_predictions
)
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService
from app.services.xai_service import XAIService

pred_service = PredictionService()
rec_service = RecommendationService()
xai_service = XAIService()

@api_bp.route("/predict", methods=["POST"])
def predict():
    """
    Primary equipment failure prediction endpoint.
    Performs validation, feature engineering, ML inference,
    rule-based recommendations, and optional SHAP attributions.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON request body."
        }), 400

    required_fields = [
        "air_temperature",
        "process_temperature",
        "rotational_speed",
        "torque",
        "tool_wear"
    ]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return jsonify({
            "status": "error",
            "message": f"Missing required telemetry fields: {', '.join(missing)}"
        }), 400

    try:
        air_temp = float(payload["air_temperature"])
        proc_temp = float(payload["process_temperature"])
        speed = float(payload["rotational_speed"])
        torque = float(payload["torque"])
        tool_wear = float(payload["tool_wear"])
    except (ValueError, TypeError) as e:
        return jsonify({
            "status": "error",
            "message": f"Sensor parameters must be valid numbers: {str(e)}"
        }), 400

    conn = get_db()
    machine_id = payload.get("machine_id")
    machine_name = payload.get("machine_name")
    machine_type = payload.get("machine_type")

    # Resolve machine registration
    resolved_machine = None
    if machine_id:
        try:
            resolved_machine = get_machine_by_id(conn, int(machine_id))
        except (ValueError, TypeError):
            pass
        if not resolved_machine:
            return jsonify({
                "status": "error",
                "message": f"Specified machine_id {machine_id} does not exist."
            }), 404
        if machine_type and machine_type.upper() != resolved_machine["machine_type"]:
            return jsonify({
                "status": "error",
                "message": f"Machine type mismatch. Machine ID {machine_id} is registered as '{resolved_machine['machine_type']}'."
            }), 400
        machine_type = resolved_machine["machine_type"]
        machine_name = resolved_machine["machine_name"]
    elif machine_name:
        machine_name = str(machine_name).strip()
        resolved_machine = get_machine_by_name(conn, machine_name)
        if resolved_machine:
            if machine_type and machine_type.upper() != resolved_machine["machine_type"]:
                return jsonify({
                    "status": "error",
                    "message": f"Machine '{machine_name}' is registered as type '{resolved_machine['machine_type']}'."
                }), 400
            machine_type = resolved_machine["machine_type"]
            machine_id = resolved_machine["machine_id"]
        else:
            if not machine_type or str(machine_type).upper() not in ["L", "M", "H"]:
                return jsonify({
                    "status": "error",
                    "message": "New machine registration requires a valid 'machine_type' (L, M, H)."
                }), 400
            machine_type = str(machine_type).upper()
            machine_id = register_machine(conn, machine_name, machine_type)
    else:
        # Default machine metadata if neither id nor name provided
        machine_name = "Quick Diagnostic Machine"
        machine_type = str(machine_type or "L").upper()
        if machine_type not in ["L", "M", "H"]:
            return jsonify({"status": "error", "message": "Machine type must be L, M, or H."}), 400
        existing = get_machine_by_name(conn, machine_name)
        if existing:
            machine_id = existing["machine_id"]
        else:
            machine_id = register_machine(conn, machine_name, machine_type)

    # 1. Execute ML prediction
    try:
        prediction_result = pred_service.predict(
            air_temperature=air_temp,
            process_temperature=proc_temp,
            rotational_speed=speed,
            torque=torque,
            tool_wear=tool_wear,
            machine_type=machine_type
        )
    except ValueError as ve:
        return jsonify({
            "status": "error",
            "message": str(ve)
        }), 400

    # 2. Generate maintenance recommendations
    rec_result = rec_service.generate_recommendations(
        failure_probability=prediction_result["failure_probability"],
        tool_wear=tool_wear,
        torque=torque,
        rotational_speed=speed,
        temperature_difference=prediction_result["temperature_difference"]
    )

    # 3. Optional Explainable AI calculation
    include_xai = payload.get("include_xai", True)
    xai_result = None
    if include_xai:
        try:
            xai_result = xai_service.explain_instance(prediction_result["processed_df"])
        except Exception as e:
            xai_result = {"available": False, "error": str(e)}

    # 4. Save to database transactionally
    save_to_db = payload.get("save_to_db", True)
    inserted_ids = {}
    if save_to_db:
        sensor_data = {
            "air_temperature": air_temp,
            "process_temperature": proc_temp,
            "rotational_speed": speed,
            "torque": torque,
            "tool_wear": tool_wear
        }
        inserted_ids = save_telemetry_and_prediction_transaction(
            conn=conn,
            machine_id=machine_id,
            sensor_data=sensor_data,
            prediction_result=prediction_result,
            recommendation_result=rec_result
        )

    # Build response payload
    response_data = {
        "machine_id": machine_id,
        "machine_name": machine_name,
        "machine_type": machine_type,
        "prediction_id": inserted_ids.get("prediction_id"),
        "reading_id": inserted_ids.get("reading_id"),
        "failure_probability": prediction_result["failure_probability"],
        "classification_threshold": prediction_result["threshold"],
        "machine_status": prediction_result["machine_status"],
        "risk_level": rec_result["risk_level"],
        "temperature_difference": prediction_result["temperature_difference"],
        "mechanical_power": prediction_result["mechanical_power"],
        "recommendations": rec_result["recommendations"],
        "action_items": rec_result["action_items"],
        "threshold_disclaimer": rec_result["threshold_disclaimer"]
    }
    if xai_result:
        response_data["xai"] = xai_result

    return jsonify({
        "status": "success",
        "data": response_data
    }), 200


@api_bp.route("/predictions", methods=["GET"])
def list_predictions():
    """Returns paginated history of fleet failure predictions."""
    limit = max(1, min(100, int(request.args.get("limit", 50))))
    offset = max(0, int(request.args.get("offset", 0)))
    conn = get_db()
    predictions = get_all_predictions(conn, limit=limit, offset=offset)
    return jsonify({
        "status": "success",
        "count": len(predictions),
        "data": predictions
    }), 200

