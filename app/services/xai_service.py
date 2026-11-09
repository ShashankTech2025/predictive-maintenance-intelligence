import numpy as np
import pandas as pd
from typing import Dict, List, Any
from app.services.ml_service import MLModelService

FEATURE_METADATA = {
    "numerical__Air_temperature_K": {
        "display_name": "Air Temperature",
        "unit": "K",
        "description": "Ambient factory air temperature around the machine."
    },
    "numerical__Process_temperature_K": {
        "display_name": "Process Temperature",
        "unit": "K",
        "description": "Operating chamber manufacturing process temperature."
    },
    "numerical__Rotational_speed_rpm": {
        "display_name": "Rotational Speed",
        "unit": "rpm",
        "description": "Spindle rotational speed in revolutions per minute."
    },
    "numerical__Torque_Nm": {
        "display_name": "Torque Load",
        "unit": "Nm",
        "description": "Mechanical resistance torque generated during processing."
    },
    "numerical__Tool_wear_min": {
        "display_name": "Tool Wear Time",
        "unit": "min",
        "description": "Cumulative operating minutes on current cutting tool."
    },
    "numerical__Temperature_Difference_K": {
        "display_name": "Thermal Gradient",
        "unit": "K",
        "description": "Temperature difference between process and ambient air."
    },
    "numerical__Mechanical_Power_kW": {
        "display_name": "Mechanical Power",
        "unit": "kW",
        "description": "Total mechanical power dissipated by the spindle."
    },
    "categorical__Type_H": {
        "display_name": "Machine Type H (Heavy)",
        "unit": "",
        "description": "Heavy duty machine variant."
    },
    "categorical__Type_L": {
        "display_name": "Machine Type L (Light)",
        "unit": "",
        "description": "Light duty machine variant."
    },
    "categorical__Type_M": {
        "display_name": "Machine Type M (Medium)",
        "unit": "",
        "description": "Medium duty machine variant."
    }
}

class XAIService:
    """
    Computes SHAP feature attributions and explains predictions
    in clear terms for factory operators and reliability engineers.
    """
    def __init__(self, ml_service: MLModelService = None):
        self.ml = ml_service or MLModelService()
        self.explainer = self.ml.explainer
        self.expected_features = self.ml.expected_features

    def explain_instance(self, processed_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates local SHAP explanation for a preprocessed sample.
        """
        if self.explainer is None:
            return {
                "available": False,
                "message": "SHAP explainer artifact is not available."
            }

        # Compute SHAP explanation
        explanation = self.explainer(processed_df)
        shap_vals = explanation.values[0]
        base_val = float(explanation.base_values[0])

        feature_contributions = []
        for feature_name, val in zip(self.expected_features, shap_vals):
            meta = FEATURE_METADATA.get(feature_name, {
                "display_name": feature_name,
                "unit": "",
                "description": ""
            })
            shap_val = float(val)
            feature_contributions.append({
                "feature": feature_name,
                "display_name": meta["display_name"],
                "unit": meta["unit"],
                "description": meta["description"],
                "shap_value": round(shap_val, 4),
                "impact": "INCREASES_FAILURE_RISK" if shap_val > 0 else "REDUCES_FAILURE_RISK",
                "abs_impact": abs(shap_val)
            })

        # Sort contributions by absolute impact
        feature_contributions.sort(key=lambda x: x["abs_impact"], reverse=True)

        # Top positive risk drivers and top stabilizing factors
        risk_drivers = [f for f in feature_contributions if f["shap_value"] > 0]
        stabilizing_factors = [f for f in feature_contributions if f["shap_value"] < 0]

        return {
            "available": True,
            "base_value": round(base_val, 4),
            "feature_contributions": feature_contributions,
            "top_risk_drivers": risk_drivers[:3],
            "top_stabilizing_factors": stabilizing_factors[:3],
            "summary": (
                f"Top risk contributor is {risk_drivers[0]['display_name']} "
                f"(+{risk_drivers[0]['shap_value']:.2f})."
                if risk_drivers else "All sensor factors are within safe operational bounds."
            )
        }

