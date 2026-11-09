import os
import joblib
from pathlib import Path
from typing import Tuple, Any, List
from config import Config

class MLModelService:
    """
    Singleton service responsible for loading and managing
    the trained XGBoost model, feature preprocessor, decision threshold,
    and SHAP explainer.
    """
    _instance = None
    _model = None
    _preprocessor = None
    _threshold = None
    _explainer = None
    _expected_features = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLModelService, cls).__new__(cls)
            cls._instance._load_artifacts()
        return cls._instance

    def _load_artifacts(self):
        """Loads and validates all serialized ML artifacts."""
        model_path = Config.MODEL_PATH
        preprocessor_path = Config.PREPROCESSOR_PATH
        threshold_path = Config.THRESHOLD_PATH
        explainer_path = Config.SHAP_EXPLAINER_PATH

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at: {model_path}")
        if not preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor file not found at: {preprocessor_path}")
        if not threshold_path.exists():
            raise FileNotFoundError(f"Threshold file not found at: {threshold_path}")

        # Load artifacts using joblib
        self._model = joblib.load(model_path)
        self._preprocessor = joblib.load(preprocessor_path)
        self._threshold = float(joblib.load(threshold_path))

        # Expected booster feature names (10 features)
        self._expected_features = list(self._model.get_booster().feature_names)

        # Load SHAP explainer if available
        if explainer_path.exists():
            try:
                self._explainer = joblib.load(explainer_path)
            except Exception as e:
                self._explainer = None
                print(f"Warning: Failed to load SHAP explainer from {explainer_path}: {e}")
        else:
            self._explainer = None

    @property
    def model(self):
        return self._model

    @property
    def preprocessor(self):
        return self._preprocessor

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def explainer(self):
        return self._explainer

    @property
    def expected_features(self) -> List[str]:
        return self._expected_features

    def get_model_summary(self) -> dict:
        """Returns metadata about the loaded ML system."""
        return {
            "model_type": type(self._model).__name__,
            "preprocessor_type": type(self._preprocessor).__name__,
            "decision_threshold": self._threshold,
            "expected_feature_count": len(self._expected_features),
            "expected_features": self._expected_features,
            "shap_explainer_loaded": self._explainer is not None,
            "shap_base_value": float(self._explainer.expected_value) if self._explainer is not None else None
        }

