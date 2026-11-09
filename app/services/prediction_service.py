import numpy as np
import pandas as pd
from typing import Dict, Any, Union
from app.services.ml_service import MLModelService

class PredictionService:
    """
    Handles telemetry validation, feature engineering,
    preprocessing, and XGBoost failure prediction.
    """
    def __init__(self, ml_service: MLModelService = None):
        self.ml = ml_service or MLModelService()

    @staticmethod
    def validate_inputs(
        air_temperature: float,
        process_temperature: float,
        rotational_speed: float,
        torque: float,
        tool_wear: float,
        machine_type: str
    ) -> None:
        """Validates physical constraints on input sensor telemetry."""
        if machine_type not in ["L", "M", "H"]:
            raise ValueError(f"Machine type must be 'L', 'M', or 'H'. Received: '{machine_type}'")

        if air_temperature <= 0 or process_temperature <= 0:
            raise ValueError(f"Temperatures must be positive in Kelvin. Air: {air_temperature}, Process: {process_temperature}")

        if rotational_speed <= 0:
            raise ValueError(f"Rotational speed must be strictly positive (> 0 rpm). Received: {rotational_speed}")

        if torque < 0 or tool_wear < 0:
            raise ValueError(f"Torque ({torque}) and tool wear ({tool_wear}) cannot be negative.")

    @staticmethod
    def calculate_engineered_features(
        air_temperature: float,
        process_temperature: float,
        rotational_speed: float,
        torque: float
    ) -> Dict[str, float]:
        """
        Calculates exact engineered features:
        - Temperature Difference [K] = Process temperature - Air temperature
        - Mechanical Power [kW] = Torque * Rotational speed * (2 * pi / 60) / 1000
        """
        temp_diff = float(process_temperature - air_temperature)
        mech_power = float((torque * rotational_speed * (2.0 * np.pi / 60.0)) / 1000.0)
        return {
            "temperature_difference": temp_diff,
            "mechanical_power": mech_power
        }

    def prepare_feature_dataframe(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: float,
        torque: float,
        tool_wear: float,
        machine_type: str,
        temperature_difference: float,
        mechanical_power: float
    ) -> pd.DataFrame:
        """Prepares raw DataFrame formatted for preprocessor_fe."""
        return pd.DataFrame([{
            "Air temperature [K]": float(air_temperature),
            "Process temperature [K]": float(process_temperature),
            "Rotational speed [rpm]": float(rotational_speed),
            "Torque [Nm]": float(torque),
            "Tool wear [min]": float(tool_wear),
            "Temperature Difference [K]": float(temperature_difference),
            "Mechanical Power [kW]": float(mechanical_power),
            "Type": str(machine_type)
        }])

    def predict(
        self,
        air_temperature: float,
        process_temperature: float,
        rotational_speed: float,
        torque: float,
        tool_wear: float,
        machine_type: str
    ) -> Dict[str, Any]:
        """
        Full inference pipeline executing exact math from Notebook 04.
        """
        # 1. Validate inputs
        self.validate_inputs(
            air_temperature=air_temperature,
            process_temperature=process_temperature,
            rotational_speed=rotational_speed,
            torque=torque,
            tool_wear=tool_wear,
            machine_type=machine_type
        )

        # 2. Compute engineered features
        engineered = self.calculate_engineered_features(
            air_temperature=air_temperature,
            process_temperature=process_temperature,
            rotational_speed=rotational_speed,
            torque=torque
        )
        temp_diff = engineered["temperature_difference"]
        mech_power = engineered["mechanical_power"]

        # 3. Create raw feature DataFrame
        raw_df = self.prepare_feature_dataframe(
            air_temperature=air_temperature,
            process_temperature=process_temperature,
            rotational_speed=rotational_speed,
            torque=torque,
            tool_wear=tool_wear,
            machine_type=machine_type,
            temperature_difference=temp_diff,
            mechanical_power=mech_power
        )

        # 4. Apply saved preprocessing pipeline
        processed_data = self.ml.preprocessor.transform(raw_df)

        # 5. Format DataFrame matching XGBoost booster column order
        processed_df = pd.DataFrame(
            processed_data,
            columns=self.ml.expected_features
        )

        # 6. Predict failure probability
        raw_probability = float(self.ml.model.predict_proba(processed_df)[0][1])

        # 7. Apply saved decision threshold (0.4)
        threshold = self.ml.threshold
        prediction = int(raw_probability >= threshold)

        failure_probability_pct = round(raw_probability * 100.0, 2)

        return {
            "failure_probability": failure_probability_pct,
            "raw_probability": raw_probability,
            "prediction": prediction,
            "threshold": threshold,
            "machine_status": "FAILURE RISK" if prediction == 1 else "NORMAL",
            "temperature_difference": round(temp_diff, 2),
            "raw_temperature_difference": temp_diff,
            "mechanical_power": round(mech_power, 2),
            "raw_mechanical_power": mech_power,
            "machine_type": machine_type,
            "processed_df": processed_df
        }

