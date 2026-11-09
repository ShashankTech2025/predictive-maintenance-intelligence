import os
from flask import Flask
from config import config_by_name, Config
from app.database.connection import close_db, init_db, ensure_database_ready

def create_app(config_name: str = None) -> Flask:
    """
    Flask Application Factory pattern.
    Configures and initializes all blueprints, database handlers, and services.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development").lower()

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Register database connection teardown
    app.teardown_appcontext(close_db)

    # Register REST API blueprint
    from app.api import api_bp
    app.register_blueprint(api_bp)

    # Register Web Views blueprint
    from app.views import web_bp
    app.register_blueprint(web_bp)

    # Database readiness check
    with app.app_context():
        if app.config.get("TESTING"):
            init_db(app.config["DATABASE_PATH"])
        else:
            ensure_database_ready(app.config.get("DATABASE_PATH"))

    return app
