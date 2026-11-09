import pytest
import numpy as np
import pandas as pd
from config import Config
from app.services.ml_service import MLModelService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService
from app.services.xai_service import XAIService


class TestMLParity:
    """
    Validates exact mathematical parity between the modular backend services
    and the reference implementations in Notebooks 03 and 04.
    """

    @pytest.fixture(autouse=True)
    def setup_services(self):
        self.ml_service = MLModelService()
        self.pred_service = PredictionService(self.ml_service)
        self.rec_service = RecommendationService()
        self.xai_service = XAIService(self.ml_service)

    def test_ml_artifacts_loading(self):
        """Verifies all serialized artifacts are correctly loaded and configured."""
        summary = self.ml_service.get_model_summary()
        
        assert summary["model_type"] == "XGBClassifier"
        assert summary["preprocessor_type"] == "ColumnTransformer"
        assert summary["decision_threshold"] == pytest.approx(0.40, rel=1e-5)
        assert summary["expected_feature_count"] == 10
        assert summary["shap_explainer_loaded"] is True
        assert summary["shap_base_value"] == pytest.approx(0.419427, rel=1e-4)

    def test_feature_engineering_exact_formulas(self):
        """Verifies feature engineering math matches Notebook 02 & 04."""
        air_temp = 300.1
        proc_temp = 310.2
        speed = 1500.0
        torque = 40.0

        eng = self.pred_service.calculate_engineered_features(
            air_temperature=air_temp,
            process_temperature=proc_temp,
            rotational_speed=speed,
            torque=torque
        )

        expected_temp_diff = 310.2 - 300.1  # 10.1
        expected_mech_power = (40.0 * 1500.0 * (2.0 * np.pi / 60.0)) / 1000.0  # 6.283185...

        assert eng["temperature_difference"] == pytest.approx(expected_temp_diff, abs=1e-6)
        assert eng["mechanical_power"] == pytest.approx(expected_mech_power, abs=1e-6)

    def test_machine_a_parity(self):
        """
        Notebook 04 Cell 13 & 16: Machine A
        Inputs: air_temp=300.1, proc_temp=310.2, rpm=1500, torque=40, tool_wear=50, type='L'
        Expected: failure_probability=0.05%, status='NORMAL', risk='LOW'
        """
        result = self.pred_service.predict(
            air_temperature=300.1,
            process_temperature=310.2,
            rotational_speed=1500,
            torque=40,
            tool_wear=50,
            machine_type="L"
        )
        
        rec = self.rec_service.generate_recommendations(
            failure_probability=result["failure_probability"],
            tool_wear=50,
            torque=40,
            rotational_speed=1500,
            temperature_difference=result["temperature_difference"]
        )

        # Numerical tolerance of 0.001%
        assert result["failure_probability"] == pytest.approx(0.05, abs=1e-3)
        assert result["prediction"] == 0
        assert result["machine_status"] == "NORMAL"
        assert rec["risk_level"] == "LOW"
        assert rec["recommendations"] == ["Low failure risk: Continue routine monitoring."]

    def test_machine_b_parity(self):
        """
        Notebook 04 Cell 13 & 16: Machine B
        Inputs: air_temp=302.0, proc_temp=311.0, rpm=1400, torque=55, tool_wear=220, type='M'
        Expected: failure_probability=85.46%, status='FAILURE RISK', risk='HIGH'
        """
        result = self.pred_service.predict(
            air_temperature=302.0,
            process_temperature=311.0,
            rotational_speed=1400,
            torque=55,
            tool_wear=220,
            machine_type="M"
        )

        rec = self.rec_service.generate_recommendations(
            failure_probability=result["failure_probability"],
            tool_wear=220,
            torque=55,
            rotational_speed=1400,
            temperature_difference=result["temperature_difference"]
        )

        # Numerical tolerance of 0.001%
        assert result["failure_probability"] == pytest.approx(85.46, abs=1e-2)
        assert result["prediction"] == 1
        assert result["machine_status"] == "FAILURE RISK"
        assert rec["risk_level"] == "HIGH"
        
        expected_recs = [
            "High failure risk: Arrange prompt machine inspection.",
            "High tool wear: Inspect the cutting tool and assess replacement.",
            "Elevated torque: Inspect mechanical load and drive components."
        ]
        assert rec["recommendations"] == expected_recs

    def test_single_sample_parity_notebook_04_cell_12(self):
        """
        Notebook 04 Cell 12: Single reference sample
        Inputs: air_temp=300.1, proc_temp=310.2, rpm=1500, torque=40, tool_wear=120, type='L'
        Expected: failure_probability=0.07%, prediction=0, status='NORMAL',
                  temperature_difference=10.1, mechanical_power=6.28
        """
        result = self.pred_service.predict(
            air_temperature=300.1,
            process_temperature=310.2,
            rotational_speed=1500,
            torque=40,
            tool_wear=120,
            machine_type="L"
        )

        assert result["failure_probability"] == pytest.approx(0.07, abs=1e-3)
        assert result["prediction"] == 0
        assert result["machine_status"] == "NORMAL"
        assert result["temperature_difference"] == pytest.approx(10.1, abs=1e-2)
        assert result["mechanical_power"] == pytest.approx(6.28, abs=1e-2)

    def test_machine_c_type_h_parity(self):
        """
        Notebook 05 Cell 15: Machine C (Type H)
        Inputs: air_temp=300.1, proc_temp=310.2, rpm=1500, torque=40, tool_wear=120, type='H'
        Expected: failure_probability=0.07%, status='NORMAL', risk='LOW'
        """
        result = self.pred_service.predict(
            air_temperature=300.1,
            process_temperature=310.2,
            rotational_speed=1500.0,
            torque=40.0,
            tool_wear=120.0,
            machine_type="H"
        )

        rec = self.rec_service.generate_recommendations(
            failure_probability=result["failure_probability"],
            tool_wear=120.0,
            torque=40.0,
            rotational_speed=1500.0,
            temperature_difference=result["temperature_difference"]
        )

        assert result["failure_probability"] == pytest.approx(0.07, abs=1e-3)
        assert result["prediction"] == 0
        assert result["machine_status"] == "NORMAL"
        assert rec["risk_level"] == "LOW"

    def test_risk_classification_thresholds(self):
        """Validates risk tiers: LOW (<20%), MEDIUM (20-39.99%), HIGH (>=40%)."""
        assert self.rec_service.classify_risk(0.0) == "LOW"
        assert self.rec_service.classify_risk(19.99) == "LOW"
        assert self.rec_service.classify_risk(20.0) == "MEDIUM"
        assert self.rec_service.classify_risk(39.99) == "MEDIUM"
        assert self.rec_service.classify_risk(40.0) == "HIGH"
        assert self.rec_service.classify_risk(85.46) == "HIGH"
        assert self.rec_service.classify_risk(100.0) == "HIGH"

    def test_sensor_rule_triggers(self):
        """Validates all 4 sensor condition trigger rules."""
        # Tool wear >= 200
        rec_tw = self.rec_service.generate_recommendations(
            failure_probability=5.0, tool_wear=200.0, torque=40.0, rotational_speed=1500.0, temperature_difference=10.0
        )
        assert "High tool wear: Inspect the cutting tool and assess replacement." in rec_tw["recommendations"]

        # Torque >= 55
        rec_tq = self.rec_service.generate_recommendations(
            failure_probability=5.0, tool_wear=50.0, torque=55.0, rotational_speed=1500.0, temperature_difference=10.0
        )
        assert "Elevated torque: Inspect mechanical load and drive components." in rec_tq["recommendations"]

        # Rotational speed <= 1300
        rec_rpm = self.rec_service.generate_recommendations(
            failure_probability=5.0, tool_wear=50.0, torque=40.0, rotational_speed=1300.0, temperature_difference=10.0
        )
        assert "Low rotational speed: Inspect motor and operating conditions." in rec_rpm["recommendations"]

        # Temperature difference <= 8
        rec_td = self.rec_service.generate_recommendations(
            failure_probability=5.0, tool_wear=50.0, torque=40.0, rotational_speed=1500.0, temperature_difference=8.0
        )
        assert "Low temperature difference: Verify operating temperature sensors." in rec_td["recommendations"]

    def test_input_validation(self):
        """Verifies out-of-bound sensor inputs raise ValueError."""
        # Invalid machine type
        with pytest.raises(ValueError, match="Machine type must be"):
            self.pred_service.predict(300, 310, 1500, 40, 50, "X")

        # Negative / zero temperatures
        with pytest.raises(ValueError, match="Temperatures must be positive"):
            self.pred_service.predict(-10, 310, 1500, 40, 50, "L")

        with pytest.raises(ValueError, match="Temperatures must be positive"):
            self.pred_service.predict(300, 0, 1500, 40, 50, "L")

        # Non-positive rotational speed
        with pytest.raises(ValueError, match="Rotational speed must be strictly positive"):
            self.pred_service.predict(300, 310, 0, 40, 50, "L")

        # Negative torque or tool wear
        with pytest.raises(ValueError, match="cannot be negative"):
            self.pred_service.predict(300, 310, 1500, -5, 50, "L")

        with pytest.raises(ValueError, match="cannot be negative"):
            self.pred_service.predict(300, 310, 1500, 40, -10, "L")

    def test_shap_explainer_parity(self):
        """Verifies local SHAP values match expected directions for Machine B."""
        pred = self.pred_service.predict(
            air_temperature=302.0,
            process_temperature=311.0,
            rotational_speed=1400,
            torque=55,
            tool_wear=220,
            machine_type="M"
        )
        
        explanation = self.xai_service.explain_instance(pred["processed_df"])

        assert explanation["available"] is True
        assert len(explanation["feature_contributions"]) == 10
        assert explanation["base_value"] == pytest.approx(0.4194, abs=1e-3)
        
        # Verify that Tool Wear and Torque are prominent risk drivers for Machine B
        driver_features = [d["feature"] for d in explanation["top_risk_drivers"]]
        assert "numerical__Tool_wear_min" in driver_features or "numerical__Torque_Nm" in driver_features

