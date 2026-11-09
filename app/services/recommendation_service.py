from typing import Dict, List, Any
from config import Config

class RecommendationService:
    """
    Evaluates failure probability and sensor thresholds
    to generate actionable maintenance directives.
    """
    def __init__(
        self,
        tool_wear_threshold: float = Config.TOOL_WEAR_ALERT_THRESHOLD,
        torque_threshold: float = Config.TORQUE_ALERT_THRESHOLD,
        rotational_speed_threshold: float = Config.ROTATIONAL_SPEED_LOW_THRESHOLD,
        temp_diff_threshold: float = Config.TEMP_DIFF_LOW_THRESHOLD,
        risk_low_ceiling: float = Config.RISK_LOW_CEILING,
        risk_medium_ceiling: float = Config.RISK_MEDIUM_CEILING
    ):
        self.tool_wear_threshold = tool_wear_threshold
        self.torque_threshold = torque_threshold
        self.rotational_speed_threshold = rotational_speed_threshold
        self.temp_diff_threshold = temp_diff_threshold
        self.risk_low_ceiling = risk_low_ceiling
        self.risk_medium_ceiling = risk_medium_ceiling

    def classify_risk(self, probability_pct: float) -> str:
        """
        Classifies risk level based on failure probability percentage:
        - LOW: < 20%
        - MEDIUM: 20% to < 40%
        - HIGH: >= 40%
        """
        if probability_pct < self.risk_low_ceiling:
            return "LOW"
        elif probability_pct < self.risk_medium_ceiling:
            return "MEDIUM"
        else:
            return "HIGH"

    def generate_recommendations(
        self,
        failure_probability: float,
        tool_wear: float,
        torque: float,
        rotational_speed: float,
        temperature_difference: float
    ) -> Dict[str, Any]:
        """
        Generates risk-level and sensor-based recommendations
        strictly adhering to Notebook 04 rules.
        """
        risk = self.classify_risk(failure_probability)
        recommendations: List[str] = []
        action_items: List[Dict[str, str]] = []

        # 1. Primary Risk Directive
        if risk == "HIGH":
            rec = "High failure risk: Arrange prompt machine inspection."
            recommendations.append(rec)
            action_items.append({
                "priority": "HIGH",
                "category": "Failure Risk",
                "action": "Arrange prompt machine inspection immediately."
            })
        elif risk == "MEDIUM":
            rec = "Moderate failure risk: Schedule a maintenance inspection."
            recommendations.append(rec)
            action_items.append({
                "priority": "MEDIUM",
                "category": "Failure Risk",
                "action": "Schedule a routine maintenance inspection within 24-48 hours."
            })
        else:
            rec = "Low failure risk: Continue routine monitoring."
            recommendations.append(rec)
            action_items.append({
                "priority": "LOW",
                "category": "Routine Monitoring",
                "action": "Continue normal operating parameters and routine monitoring."
            })

        # 2. Sensor-based Component Directives
        if tool_wear >= self.tool_wear_threshold:
            rec = "High tool wear: Inspect the cutting tool and assess replacement."
            recommendations.append(rec)
            action_items.append({
                "priority": "HIGH" if risk == "HIGH" else "MEDIUM",
                "category": "Tool Wear",
                "action": f"Inspect cutting tool (wear is {tool_wear:.1f} min >= {self.tool_wear_threshold:.1f} min limit) and assess replacement."
            })

        if torque >= self.torque_threshold:
            rec = "Elevated torque: Inspect mechanical load and drive components."
            recommendations.append(rec)
            action_items.append({
                "priority": "HIGH" if risk == "HIGH" else "MEDIUM",
                "category": "Drive System",
                "action": f"Inspect mechanical load and drive components (torque is {torque:.1f} Nm >= {self.torque_threshold:.1f} Nm limit)."
            })

        if rotational_speed <= self.rotational_speed_threshold:
            rec = "Low rotational speed: Inspect motor and operating conditions."
            recommendations.append(rec)
            action_items.append({
                "priority": "MEDIUM",
                "category": "Motor Assembly",
                "action": f"Inspect motor and power supply conditions (speed is {rotational_speed:.1f} rpm <= {self.rotational_speed_threshold:.1f} rpm limit)."
            })

        if temperature_difference <= self.temp_diff_threshold:
            rec = "Low temperature difference: Verify operating temperature sensors."
            recommendations.append(rec)
            action_items.append({
                "priority": "MEDIUM",
                "category": "Thermal Dissipation",
                "action": f"Verify heat dissipation and calibration of temperature sensors (temp diff is {temperature_difference:.1f} K <= {self.temp_diff_threshold:.1f} K limit)."
            })

        return {
            "risk_level": risk,
            "recommendations": recommendations,
            "action_items": action_items,
            "combined_text": " | ".join(recommendations),
            "threshold_disclaimer": "Thresholds represent industrial reference defaults and must be validated against OEM equipment specifications before operational deployment."
        }

