import io
import csv
import datetime
from typing import List, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ReportService:
    """
    Generates downloadable CSV and PDF Machine Health & Maintenance Reports.
    """

    @staticmethod
    def generate_fleet_csv(machine_rows: List[Dict[str, Any]]) -> str:
        """Generates RFC-4180 compliant CSV string of fleet machine health."""
        output = io.StringIO()
        fieldnames = [
            "Machine ID",
            "Machine Name",
            "Machine Type",
            "Failure Probability (%)",
            "Machine Status",
            "Risk Level",
            "Air Temperature [K]",
            "Process Temperature [K]",
            "Rotational Speed [rpm]",
            "Torque [Nm]",
            "Tool Wear [min]",
            "Last Predicted At",
            "Maintenance Recommendations"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for m in machine_rows:
            writer.writerow({
                "Machine ID": m.get("machine_id", ""),
                "Machine Name": m.get("machine_name", ""),
                "Machine Type": m.get("machine_type", ""),
                "Failure Probability (%)": f"{m.get('failure_probability', 0.0):.2f}" if m.get("failure_probability") is not None else "N/A",
                "Machine Status": m.get("machine_status", "NOT_ASSESSED"),
                "Risk Level": m.get("risk_level", "UNMONITORED"),
                "Air Temperature [K]": m.get("air_temperature", ""),
                "Process Temperature [K]": m.get("process_temperature", ""),
                "Rotational Speed [rpm]": m.get("rotational_speed", ""),
                "Torque [Nm]": m.get("torque", ""),
                "Tool Wear [min]": m.get("tool_wear", ""),
                "Last Predicted At": m.get("predicted_at", ""),
                "Maintenance Recommendations": m.get("recommendations", "")
            })

        return output.getvalue()

    @staticmethod
    def generate_machine_pdf(
        machine_info: Dict[str, Any],
        prediction: Dict[str, Any],
        recommendations: Dict[str, Any],
        sensor_data: Dict[str, Any],
        xai_data: Dict[str, Any] = None
    ) -> bytes:
        """
        Generates an executive-grade PDF Machine Health Certificate using ReportLab.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0F172A")
        accent_blue = colors.HexColor("#1E3A8A")
        
        risk_level = recommendations.get("risk_level", "LOW")
        if risk_level == "HIGH":
            status_color = colors.HexColor("#DC2626")
        elif risk_level == "MEDIUM":
            status_color = colors.HexColor("#D97706")
        else:
            status_color = colors.HexColor("#16A34A")

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=primary_color,
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=accent_blue,
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155")
        )

        elements = []

        # 1. Header & Branding
        elements.append(Paragraph("PREDICTIVE MAINTENANCE INTELLIGENCE", title_style))
        elements.append(Paragraph(
            f"Official Machine Health & Failure Risk Assessment Report &bull; Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceAfter=14))

        # 2. Executive Assessment Summary Card
        prob_pct = prediction.get("failure_probability", 0.0)
        status_text = prediction.get("machine_status", "NORMAL")
        summary_table_data = [
            [
                Paragraph("<b>Machine Identifier:</b>", body_style),
                Paragraph(f"{machine_info.get('machine_name', 'Unknown')} (Type {machine_info.get('machine_type', 'L')})", body_style),
                Paragraph("<b>Assessment Status:</b>", body_style),
                Paragraph(f"<b><font color='{status_color}'>{status_text}</font></b>", body_style)
            ],
            [
                Paragraph("<b>Failure Probability:</b>", body_style),
                Paragraph(f"<b>{prob_pct:.2f}%</b> (Threshold: 40.00%)", body_style),
                Paragraph("<b>Assigned Risk Tier:</b>", body_style),
                Paragraph(f"<b><font color='{status_color}'>{risk_level}</font></b>", body_style)
            ]
        ]
        summary_table = Table(summary_table_data, colWidths=[1.8*inch, 2.2*inch, 1.6*inch, 1.8*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        # 3. Telemetry & Engineered Features
        elements.append(Paragraph("OPERATIONAL SENSOR TELEMETRY", section_style))
        sensor_table_data = [
            [Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Observed Reading</b>", body_style), Paragraph("<b>Industrial Reference Spec</b>", body_style)],
            [Paragraph("Air Temperature", body_style), Paragraph(f"{sensor_data.get('air_temperature', 0.0):.1f} K", body_style), Paragraph("Ambient factory air temperature", body_style)],
            [Paragraph("Process Temperature", body_style), Paragraph(f"{sensor_data.get('process_temperature', 0.0):.1f} K", body_style), Paragraph("Machining chamber process temperature", body_style)],
            [Paragraph("Temperature Gradient (&Delta;T)", body_style), Paragraph(f"{prediction.get('temperature_difference', 0.0):.1f} K", body_style), Paragraph("Minimum &ge; 8.0 K required for dissipation", body_style)],
            [Paragraph("Rotational Speed", body_style), Paragraph(f"{sensor_data.get('rotational_speed', 0.0):.0f} rpm", body_style), Paragraph("Nominal operating range: &gt; 1300 rpm", body_style)],
            [Paragraph("Torque Load", body_style), Paragraph(f"{sensor_data.get('torque', 0.0):.1f} Nm", body_style), Paragraph("Nominal torque threshold: &lt; 55.0 Nm", body_style)],
            [Paragraph("Mechanical Power Output", body_style), Paragraph(f"{prediction.get('mechanical_power', 0.0):.2f} kW", body_style), Paragraph("Spindle mechanical power dissipation", body_style)],
            [Paragraph("Cumulative Tool Wear", body_style), Paragraph(f"{sensor_data.get('tool_wear', 0.0):.0f} min", body_style), Paragraph("Replacement alert threshold: &ge; 200 min", body_style)],
        ]
        sensor_table = Table(sensor_table_data, colWidths=[2.2*inch, 2.0*inch, 3.2*inch])
        sensor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sensor_table)
        elements.append(Spacer(1, 12))

        # 4. Actionable Maintenance Directives
        elements.append(Paragraph("RECOMMENDED MAINTENANCE ACTIONS", section_style))
        recs_list = recommendations.get("recommendations", ["No active recommendations."])
        for idx, rec in enumerate(recs_list, 1):
            elements.append(Paragraph(f"<b>{idx}.</b> {rec}", body_style))
            elements.append(Spacer(1, 3))

        elements.append(Spacer(1, 8))
        disclaimer = recommendations.get("threshold_disclaimer", "Verify against OEM machine datasheets before executing physical maintenance.")
        elements.append(Paragraph(f"<i>Note: {disclaimer}</i>", ParagraphStyle("Disclaimer", parent=styles["Italic"], fontSize=8, textColor=colors.HexColor("#64748B"))))

        # 5. XAI Top Risk Drivers (if available)
        if xai_data and xai_data.get("available") and xai_data.get("top_risk_drivers"):
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("EXPLAINABLE AI &bull; KEY CONTRIBUTING FACTORS (SHAP)", section_style))
            xai_table_data = [[
                Paragraph("<b>Feature Factor</b>", body_style),
                Paragraph("<b>Impact</b>", body_style),
                Paragraph("<b>Attribution Value</b>", body_style),
                Paragraph("<b>Engineering Interpretation</b>", body_style)
            ]]
            for driver in xai_data["top_risk_drivers"][:3]:
                xai_table_data.append([
                    Paragraph(driver["display_name"], body_style),
                    Paragraph("<font color='#DC2626'>INCREASES RISK</font>", body_style),
                    Paragraph(f"+{driver['shap_value']:.4f}", body_style),
                    Paragraph(driver["description"], body_style)
                ])
            xai_table = Table(xai_table_data, colWidths=[1.8*inch, 1.4*inch, 1.2*inch, 3.0*inch])
            xai_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FEF2F2")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#FCA5A5")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(xai_table)

        doc.build(elements)
        return buffer.getvalue()

