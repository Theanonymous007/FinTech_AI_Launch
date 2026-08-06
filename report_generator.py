from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ai_engine import analyse_finances


def _money(value: Any) -> str:
    try:
        return f"INR {float(value):,.0f}"
    except (TypeError, ValueError):
        return "INR 0"


def _percentage(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "0%"


def _safe_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return str(value)


def _risk_summary(anomalies: pd.DataFrame) -> dict[str, Any]:
    if anomalies.empty:
        return {
            "status": "Low",
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0,
            "reviewable": 0.0,
        }

    high = int(anomalies["risk_level"].eq("High").sum())
    medium = int(anomalies["risk_level"].eq("Medium").sum())
    low = int(anomalies["risk_level"].eq("Low").sum())

    return {
        "status": "High" if high else "Medium" if medium else "Low",
        "high": high,
        "medium": medium,
        "low": low,
        "total": high + medium + low,
        "reviewable": float(anomalies["total"].sum()),
    }


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#4B5563"),
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#111827"),
            spaceBefore=8,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "SmallText",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#4B5563"),
        ),
        "warning": ParagraphStyle(
            "WarningText",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#991B1B"),
            backColor=colors.HexColor("#FEE2E2"),
            borderPadding=7,
            spaceBefore=8,
            spaceAfter=8,
        ),
    }


def _table(data: list[list[Any]], widths: list[float] | None = None) -> Table:
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F9FAFB"),
                ]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _header_footer(canvas, document) -> None:
    canvas.saveState()
    width, height = A4

    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(
        18 * mm,
        9 * mm,
        "FinTech AI - Explainable Financial Intelligence",
    )
    canvas.drawRightString(
        width - 18 * mm,
        9 * mm,
        f"Page {document.page}",
    )
    canvas.restoreState()


def create_executive_report(
    business_name: str = "Demo MSME",
    report_period: str = "Current verified records",
) -> bytes:
    analysis = analyse_finances()

    if not analysis["has_data"]:
        raise ValueError("No verified invoice data is available.")

    summary = analysis["summary"]
    health = analysis["health"]
    forecast = analysis["forecast"]
    anomalies = analysis["anomalies"]
    vendors = analysis["vendors"]
    categories = analysis["categories"]
    recommendations = analysis["recommendations"]
    dataframe = analysis["dataframe"]

    risk = _risk_summary(anomalies)
    styles = _styles()

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="FinTech AI Executive Financial Intelligence Report",
        author="FinTech AI",
    )

    story = []

    story.append(
        Paragraph(
            "FinTech AI Executive Financial Intelligence Report",
            styles["title"],
        )
    )
    story.append(
        Paragraph(
            f"{business_name}<br/>{report_period}<br/>"
            f"Generated {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            styles["subtitle"],
        )
    )

    story.append(
        Paragraph(
            "This report converts verified invoice records into explainable "
            "financial-health indicators, vendor intelligence, anomaly alerts, "
            "expense forecasts and recommended management actions.",
            styles["body"],
        )
    )

    story.append(Paragraph("1. Executive Summary", styles["heading"]))

    kpi_data = [
        ["Metric", "Result", "Interpretation"],
        [
            "Recorded spend",
            _money(summary["total_spend"]),
            f"Across {summary['invoice_count']} verified invoice(s)",
        ],
        [
            "Financial health",
            f"{health['score']}/100",
            _safe_text(health["status"]),
        ],
        [
            "Pending amount",
            _money(summary["pending_amount"]),
            "Awaiting payment or settlement",
        ],
        [
            "Overdue amount",
            _money(summary["overdue_amount"]),
            "Requires priority verification",
        ],
        [
            "Active vendors",
            str(summary["vendor_count"]),
            "Suppliers represented in the verified dataset",
        ],
        [
            "AI risk status",
            risk["status"],
            f"{risk['total']} open statistical alert(s)",
        ],
        [
            "Next-month estimate",
            _money(forecast["base_estimate"]),
            f"{forecast['confidence']}% model confidence",
        ],
    ]
    story.append(_table(kpi_data, [42 * mm, 38 * mm, 76 * mm]))
    story.append(Spacer(1, 8))

    if summary["overdue_amount"] > 0:
        story.append(
            Paragraph(
                f"Top priority: Verify and resolve {_money(summary['overdue_amount'])} "
                "in overdue invoice exposure. Confirm due dates, supplier criticality "
                "and the payment plan before approving avoidable expenditure.",
                styles["warning"],
            )
        )

    story.append(Paragraph("2. Financial Health Explanation", styles["heading"]))

    components = health.get("components", [])
    health_rows = [["Component", "Score", "Evidence", "Improvement"]]

    for component in components:
        health_rows.append(
            [
                _safe_text(component.get("component")),
                f"{component.get('score', 0)}/{component.get('maximum', 0)}",
                Paragraph(
                    _safe_text(component.get("evidence")),
                    styles["small"],
                ),
                Paragraph(
                    _safe_text(component.get("improvement")),
                    styles["small"],
                ),
            ]
        )

    story.append(
        _table(
            health_rows,
            [34 * mm, 20 * mm, 50 * mm, 52 * mm],
        )
    )

    story.append(Paragraph("3. Vendor Intelligence", styles["heading"]))

    vendor_rows = [
        [
            "Vendor",
            "Spend",
            "Share",
            "Invoices",
            "Open Amount",
            "Score",
            "Dependency",
        ]
    ]

    for _, vendor in vendors.head(8).iterrows():
        vendor_rows.append(
            [
                _safe_text(vendor["vendor"]),
                _money(vendor["total_spend"]),
                _percentage(vendor["spend_share"]),
                str(int(vendor["invoice_count"])),
                _money(vendor["open_amount"]),
                f"{int(vendor['vendor_score'])}/100",
                _safe_text(vendor["dependency_risk"]),
            ]
        )

    story.append(
        _table(
            vendor_rows,
            [34 * mm, 26 * mm, 18 * mm, 18 * mm, 25 * mm, 17 * mm, 27 * mm],
        )
    )

    story.append(Paragraph("4. Expense Categories", styles["heading"]))

    category_rows = [["Category", "Recorded Spend", "Share", "Invoice Count"]]

    for _, category in categories.head(10).iterrows():
        category_rows.append(
            [
                _safe_text(category["category"]),
                _money(category["total_spend"]),
                _percentage(category["spend_share"]),
                str(int(category["invoice_count"])),
            ]
        )

    story.append(
        _table(
            category_rows,
            [52 * mm, 42 * mm, 30 * mm, 32 * mm],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("5. Risk and Anomaly Review", styles["heading"]))

    risk_data = [
        ["Risk Metric", "Result"],
        ["Overall status", risk["status"]],
        ["High-risk alerts", str(risk["high"])],
        ["Medium-risk alerts", str(risk["medium"])],
        ["Low-risk alerts", str(risk["low"])],
        ["Invoice value requiring review", _money(risk["reviewable"])],
    ]
    story.append(_table(risk_data, [75 * mm, 75 * mm]))
    story.append(Spacer(1, 8))

    if anomalies.empty:
        story.append(
            Paragraph(
                "No open statistical invoice anomaly was identified in the "
                "current verified dataset.",
                styles["body"],
            )
        )
    else:
        anomaly_rows = [
            [
                "Vendor",
                "Invoice",
                "Amount",
                "Risk",
                "Explanation",
            ]
        ]

        for _, alert in anomalies.head(10).iterrows():
            anomaly_rows.append(
                [
                    _safe_text(alert["vendor"]),
                    _safe_text(alert["invoice_number"]),
                    _money(alert["total"]),
                    f"{alert['risk_level']} ({int(alert['risk_score'])}/100)",
                    Paragraph(_safe_text(alert["reasons"]), styles["small"]),
                ]
            )

        story.append(
            _table(
                anomaly_rows,
                [31 * mm, 27 * mm, 25 * mm, 27 * mm, 50 * mm],
            )
        )

    story.append(Paragraph("6. Forecast", styles["heading"]))

    forecast_rows = [
        ["Forecast Metric", "Result"],
        ["Forecast month", _safe_text(forecast.get("next_month"))],
        ["Low estimate", _money(forecast["low_estimate"])],
        ["Base estimate", _money(forecast["base_estimate"])],
        ["High estimate", _money(forecast["high_estimate"])],
        ["Confidence", f"{forecast['confidence']}%"],
        ["Method", _safe_text(forecast.get("method"))],
    ]
    story.append(_table(forecast_rows, [75 * mm, 75 * mm]))

    story.append(Paragraph("7. Recommended Management Actions", styles["heading"]))

    if not recommendations:
        story.append(
            Paragraph(
                "No urgent action was generated from the current verified records.",
                styles["body"],
            )
        )
    else:
        recommendation_rows = [["Priority", "Issue", "Evidence", "Action"]]

        for item in recommendations[:8]:
            recommendation_rows.append(
                [
                    _safe_text(item.get("priority")),
                    _safe_text(item.get("title")),
                    Paragraph(_safe_text(item.get("evidence")), styles["small"]),
                    Paragraph(_safe_text(item.get("action")), styles["small"]),
                ]
            )

        story.append(
            _table(
                recommendation_rows,
                [20 * mm, 35 * mm, 50 * mm, 55 * mm],
            )
        )

    story.append(Paragraph("8. Recent Verified Invoices", styles["heading"]))

    invoice_rows = [
        ["Date", "Vendor", "Invoice No.", "Category", "Status", "Total"]
    ]

    recent = dataframe.sort_values(
        "invoice_date",
        ascending=False,
    ).head(12)

    for _, invoice in recent.iterrows():
        date_value = pd.to_datetime(
            invoice.get("invoice_date"),
            errors="coerce",
        )
        date_text = (
            "-"
            if pd.isna(date_value)
            else date_value.strftime("%d %b %Y")
        )

        invoice_rows.append(
            [
                date_text,
                _safe_text(invoice.get("vendor")),
                _safe_text(invoice.get("invoice_number")),
                _safe_text(invoice.get("category")),
                _safe_text(invoice.get("status")),
                _money(invoice.get("total")),
            ]
        )

    story.append(
        _table(
            invoice_rows,
            [23 * mm, 35 * mm, 27 * mm, 31 * mm, 20 * mm, 24 * mm],
        )
    )

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Important: FinTech AI provides explainable decision support. "
            "Anomaly alerts are potential fraud indicators requiring human review, "
            "not proof of fraud. The financial-health indicator is not a bank "
            "credit score. Forecasts are estimates based on the available verified "
            "invoice history and should not be treated as guaranteed outcomes.",
            styles["warning"],
        )
    )

    document.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)
    return buffer.getvalue()


def render_report_page() -> None:
    st.header("📄 Executive Report Generator")
    st.caption(
        "Generate a management-ready PDF from verified invoice records, "
        "financial-health analysis, vendor intelligence, risk alerts and forecasts."
    )

    business_name = st.text_input(
        "Business name",
        value="Demo MSME",
    )
    report_period = st.text_input(
        "Report period",
        value="Current verified records",
    )

    try:
        analysis = analyse_finances()
    except Exception as error:
        st.error(f"FinTech AI could not analyse the database: {error}")
        return

    if not analysis["has_data"]:
        st.info(
            "No verified invoices are available. Upload invoices or load "
            "synthetic demo data first."
        )
        return

    summary = analysis["summary"]
    health = analysis["health"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Verified invoices", summary["invoice_count"])
    c2.metric("Recorded spend", f"₹{summary['total_spend']:,.0f}")
    c3.metric("Financial health", f"{health['score']}/100")

    if st.button(
        "Generate Executive PDF",
        type="primary",
        width="stretch",
    ):
        with st.spinner("Creating the executive report..."):
            try:
                pdf_bytes = create_executive_report(
                    business_name=business_name.strip() or "Demo MSME",
                    report_period=report_period.strip() or "Current verified records",
                )
                st.session_state["fintech_report_pdf"] = pdf_bytes
                st.success("Executive report generated successfully.")
            except Exception as error:
                st.error(f"Report generation failed: {error}")

    pdf_bytes = st.session_state.get("fintech_report_pdf")
    if pdf_bytes:
        filename = (
            f"FinTech_AI_Executive_Report_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )

        st.download_button(
            "Download Executive Report",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            width="stretch",
        )

    st.warning(
        "The report is generated from verified invoice data. It is a "
        "decision-support document, not a statutory audit, tax filing or "
        "legal opinion."
    )
