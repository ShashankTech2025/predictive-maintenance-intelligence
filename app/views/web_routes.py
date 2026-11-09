from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
@web_bp.route("/dashboard")
def dashboard_view():
    """Overview dashboard page."""
    return render_template("dashboard.html", active_page="dashboard")

@web_bp.route("/machines")
def machines_view():
    """Fleet machine monitoring and inventory page."""
    return render_template("machines.html", active_page="machines")

@web_bp.route("/predict")
def predict_view():
    """Failure prediction & sensor diagnostics form page."""
    return render_template("predict.html", active_page="predict")

@web_bp.route("/maintenance")
@web_bp.route("/recommendations")
def maintenance_view():
    """Active maintenance directives and task management page."""
    return render_template("recommendations.html", active_page="maintenance")

@web_bp.route("/history")
def history_view():
    """Historical predictions and sensor telemetry audit trail."""
    return render_template("history.html", active_page="history")

@web_bp.route("/reports")
def reports_view():
    """Reports generation and export portal."""
    return render_template("reports.html", active_page="reports")

@web_bp.route("/settings")
def settings_view():
    """System configuration and ML diagnostics page."""
    return render_template("settings.html", active_page="settings")

