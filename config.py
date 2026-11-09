import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "predictive-maintenance-secret-key-change-in-production")
    BASE_DIR = BASE_DIR
    
    # Paths to ML artifacts
    MODELS_DIR = BASE_DIR / "models"
    MODEL_PATH = MODELS_DIR / "final_xgboost_model.pkl"
    PREPROCESSOR_PATH = MODELS_DIR / "preprocessor_fe.pkl"
    THRESHOLD_PATH = MODELS_DIR / "decision_threshold.pkl"
    SHAP_EXPLAINER_PATH = MODELS_DIR / "shap_explainer.pkl"
    
    # Paths to Database & Reports
    DATABASE_DIR = BASE_DIR / "database"
    _env_db = os.environ.get("DATABASE_PATH")
    DATABASE_PATH = Path(_env_db) if _env_db else (DATABASE_DIR / "predictive_maintenance.db")
    REPORTS_DIR = BASE_DIR / "reports"
    
    # Thresholds for maintenance recommendations (configurable)
    TOOL_WEAR_ALERT_THRESHOLD = float(os.environ.get("TOOL_WEAR_ALERT_THRESHOLD", 200.0))  # min
    TORQUE_ALERT_THRESHOLD = float(os.environ.get("TORQUE_ALERT_THRESHOLD", 55.0))         # Nm
    ROTATIONAL_SPEED_LOW_THRESHOLD = float(os.environ.get("ROTATIONAL_SPEED_LOW_THRESHOLD", 1300.0))  # rpm
    TEMP_DIFF_LOW_THRESHOLD = float(os.environ.get("TEMP_DIFF_LOW_THRESHOLD", 8.0))        # K
    
    # Risk categorization boundaries (percentages)
    RISK_LOW_CEILING = float(os.environ.get("RISK_LOW_CEILING", 20.0))
    RISK_MEDIUM_CEILING = float(os.environ.get("RISK_MEDIUM_CEILING", 40.0))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration with temporary database."""
    DEBUG = False
    TESTING = True
    DATABASE_PATH = BASE_DIR / "database" / "test_predictive_maintenance.db"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    _env_db = os.environ.get("DATABASE_PATH")
    if _env_db:
        DATABASE_PATH = Path(_env_db)


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

