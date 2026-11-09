import datetime
from flask import request, Response, jsonify, send_file
from app.api import api_bp
from app.database.connection import get_db
from app.database.queries import get_machines, get_machine_history
from app.services.report_service import ReportService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService
from app.services.xai_service import XAIService

pred_service = PredictionService()
rec_service = RecommendationService()
xai_service = XAIService()

@api_bp.route("/reports/csv", methods=["GET"])
def download_fleet_csv():
    """Generates and downloads a CSV export of current machine health."""
    conn = get_db()
    machines = get_machines(conn)
    csv_data = ReportService.generate_fleet_csv(machines)

    filename = f"machine_health_reports_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_bp.route("/reports/pdf/<int:machine_id>", methods=["GET"])
def download_machine_pdf(machine_id: int):
    """Generates and downloads a PDF health certificate for a specific machine."""
    conn = get_db()
    history = get_machine_history(conn, machine_id)
    if not history:
        return jsonify({"status": "error", "message": f"Machine ID {machine_id} not found."}), 404

    machine_info = history["machine"]
    latest_pred = history["prediction_history"][0] if history["prediction_history"] else {}
    latest_sensor = history["sensor_history"][0] if history["sensor_history"] else {}

    if not latest_sensor:
        return jsonify({"status": "error", "message": "No sensor readings available for this machine."}), 400

    # Generate fresh prediction & recommendation data if needed
    prediction_result = pred_service.predict(
        air_temperature=latest_sensor["air_temperature"],
        process_temperature=latest_sensor["process_temperature"],
        rotational_speed=latest_sensor["rotational_speed"],
        torque=latest_sensor["torque"],
        tool_wear=latest_sensor["tool_wear"],
        machine_type=machine_info["machine_type"]
    )
    rec_result = rec_service.generate_recommendations(
        failure_probability=prediction_result["failure_probability"],
        tool_wear=latest_sensor["tool_wear"],
        torque=latest_sensor["torque"],
        rotational_speed=latest_sensor["rotational_speed"],
        temperature_difference=prediction_result["temperature_difference"]
    )
    xai_result = xai_service.explain_instance(prediction_result["processed_df"])

    pdf_bytes = ReportService.generate_machine_pdf(
        machine_info=machine_info,
        prediction=prediction_result,
        recommendations=rec_result,
        sensor_data=latest_sensor,
        xai_data=xai_result
    )

    filename = f"Health_Certificate_{machine_info['machine_name'].replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

