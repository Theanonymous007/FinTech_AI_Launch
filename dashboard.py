from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_engine import analyse_finances
from database import get_all_vendor_memory


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _money(value: Any) -> str:
    """Format a numeric value as Indian-rupee currency."""
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def _money_precise(value: Any) -> str:
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def _percentage(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "0%"


def _safe_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "—"

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return "—"

    return parsed.strftime("%d %b %Y")


def _risk_overview(anomalies: pd.DataFrame) -> dict[str, Any]:
    if anomalies.empty:
        return {
            "label": "Low",
            "message": "No open statistical invoice alerts",
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0,
        }

    high = int(anomalies["risk_level"].eq("High").sum())
    medium = int(anomalies["risk_level"].eq("Medium").sum())
    low = int(anomalies["risk_level"].eq("Low").sum())

    if high:
        label = "High"
        message = f"{high} high-risk invoice alert(s) require review"
    elif medium:
        label = "Medium"
        message = f"{medium} medium-risk invoice alert(s) require review"
    else:
        label = "Low"
        message = f"{low} low-risk invoice alert(s) are open"

    return {
        "label": label,
        "message": message,
        "high": high,
        "medium": medium,
        "low": low,
        "total": high + medium + low,
    }


def _show_risk_banner(risk: dict[str, Any]) -> None:
    if risk["label"] == "High":
        st.error(f"🚨 {risk['message']}")
    elif risk["label"] == "Medium":
        st.warning(f"⚠️ {risk['message']}")
    else:
        st.success(f"✅ {risk['message']}")


def _plotly_config() -> dict[str, Any]:
    return {
        "displayModeBar": False,
        "responsive": True,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def render_dashboard() -> None:
    """
    Render the FinTech AI executive dashboard.

    All calculations are supplied by ai_engine.py. This file only presents
    the results, which keeps the architecture modular and explainable.
    """
    st.header("📊 FinTech AI Financial Intelligence Dashboard")
    st.caption(
        "Verified invoice data is converted into explainable financial "
        "health, anomaly alerts, vendor intelligence, forecasts and actions."
    )

    try:
        analysis = analyse_finances()
    except Exception as error:
        st.error(
            "FinTech AI could not analyse the database. "
            f"Technical detail: {error}"
        )
        st.info(
            "Confirm that ai_engine.py, database.py and dashboard.py are "
            "inside the same project folder."
        )
        return

    if not analysis["has_data"]:
        st.info(
            "No verified invoices are available yet. Open **AI Invoice "
            "Capture** or load the synthetic demo data."
        )
        st.caption(
            "The intelligence engine is ready and will update automatically "
            "after the first invoice is saved."
        )
        return

    summary = analysis["summary"]
    monthly = analysis["monthly"].copy()
    categories = analysis["categories"].copy()
    anomalies = analysis["anomalies"].copy()
    vendors = analysis["vendors"].copy()
    health = analysis["health"]
    forecast = analysis["forecast"]
    recommendations = analysis["recommendations"]
    dataframe = analysis["dataframe"].copy()

    risk = _risk_overview(anomalies)

    # Executive summary -----------------------------------------------------
    st.subheader("Executive Summary")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric(
        "Recorded spend",
        _money(summary["total_spend"]),
        help="Total value of all verified invoices in the database.",
    )
    metric_2.metric(
        "Verified invoices",
        f"{summary['invoice_count']:,}",
        help="Number of saved and verified invoice records.",
    )
    metric_3.metric(
        "Financial health",
        f"{health['score']}/100",
        delta=health["status"],
        delta_color="off",
        help=health["disclaimer"],
    )
    metric_4.metric(
        "AI risk status",
        risk["label"],
        delta=f"{risk['total']} alert(s)",
        delta_color="off",
        help=(
            "Statistical review indicators only. "
            "They are not proof of fraud."
        ),
    )

    metric_5, metric_6, metric_7, metric_8 = st.columns(4)
    metric_5.metric(
        "Pending amount",
        _money(summary["pending_amount"]),
    )
    metric_6.metric(
        "Overdue amount",
        _money(summary["overdue_amount"]),
    )
    metric_7.metric(
        "Active vendors",
        f"{summary['vendor_count']:,}",
    )
    metric_8.metric(
        "Next-month estimate",
        _money(forecast["base_estimate"]),
        delta=f"{forecast['confidence']}% confidence",
        delta_color="off",
        help=(
            "Invoice-expense/cash-outflow estimate, not full net cash flow."
        ),
    )

    _show_risk_banner(risk)

    tab_overview, tab_risk, tab_vendors, tab_health = st.tabs(
        [
            "📈 Overview",
            "🚨 Risk & Anomalies",
            "🏢 Vendor Intelligence",
            "❤️ Health & Forecast",
        ]
    )

    # Overview tab ----------------------------------------------------------
    with tab_overview:
        left, right = st.columns(2)

        with left:
            st.subheader("Monthly Expense Movement")

            if monthly.empty:
                st.info(
                    "Add dated invoices across multiple months to show trends."
                )
            else:
                monthly_chart = monthly.copy()
                monthly_chart["Month"] = pd.to_datetime(
                    monthly_chart["month"],
                    errors="coerce",
                ).dt.strftime("%b %Y")

                monthly_long = monthly_chart.melt(
                    id_vars=["Month"],
                    value_vars=[
                        "total_spend",
                        "pending_amount",
                        "overdue_amount",
                    ],
                    var_name="Series",
                    value_name="Amount",
                )
                monthly_long["Series"] = monthly_long["Series"].map(
                    {
                        "total_spend": "Total spend",
                        "pending_amount": "Pending",
                        "overdue_amount": "Overdue",
                    }
                )

                monthly_figure = px.line(
                    monthly_long,
                    x="Month",
                    y="Amount",
                    color="Series",
                    markers=True,
                    labels={
                        "Amount": "Amount (₹)",
                        "Month": "Month",
                    },
                )
                monthly_figure.update_layout(
                    legend_title_text="",
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(
                    monthly_figure,
                    width="stretch",
                    config=_plotly_config(),
                )

        with right:
            st.subheader("Expense Distribution")

            if categories.empty:
                st.info("No category data is available.")
            else:
                category_figure = px.pie(
                    categories.head(10),
                    names="category",
                    values="total_spend",
                    hole=0.55,
                )
                category_figure.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                )
                category_figure.update_layout(
                    showlegend=False,
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(
                    category_figure,
                    width="stretch",
                    config=_plotly_config(),
                )

        st.subheader("AI Recommendations")

        if not recommendations:
            st.success(
                "No urgent recommendation was generated from current records."
            )
        else:
            for recommendation in recommendations[:5]:
                priority = recommendation["priority"]
                heading = (
                    f"{priority} — {recommendation['title']}"
                )
                body = (
                    f"**Evidence:** {recommendation['evidence']}\n\n"
                    f"**Recommended action:** {recommendation['action']}"
                )

                if recommendation.get("reviewable_amount", 0):
                    body += (
                        "\n\n**Amount requiring review:** "
                        f"{_money(recommendation['reviewable_amount'])}"
                    )

                if priority == "High":
                    st.error(f"**{heading}**\n\n{body}")
                elif priority == "Medium":
                    st.warning(f"**{heading}**\n\n{body}")
                else:
                    st.info(f"**{heading}**\n\n{body}")

        st.subheader("Recent Verified Invoices")

        recent = dataframe.sort_values(
            ["invoice_date", "id"],
            ascending=[False, False],
        ).head(10)

        recent_display = recent[
            [
                "invoice_date",
                "vendor",
                "invoice_number",
                "category",
                "status",
                "total",
                "extraction_mode",
            ]
        ].copy()

        recent_display["invoice_date"] = recent_display[
            "invoice_date"
        ].map(_safe_date)
        recent_display["total"] = recent_display["total"].map(
            _money_precise
        )
        recent_display.columns = [
            "Date",
            "Vendor",
            "Invoice No.",
            "Category",
            "Status",
            "Total",
            "Capture Mode",
        ]

        st.dataframe(
            recent_display,
            width="stretch",
            hide_index=True,
        )

    # Risk tab --------------------------------------------------------------
    with tab_risk:
        st.subheader("Potential Fraud Indicators & Anomaly Review")
        st.caption(
            "FinTech AI identifies unusual financial patterns requiring "
            "human review. An alert does not prove that fraud occurred."
        )

        risk_1, risk_2, risk_3, risk_4 = st.columns(4)
        risk_1.metric("High alerts", risk["high"])
        risk_2.metric("Medium alerts", risk["medium"])
        risk_3.metric("Low alerts", risk["low"])
        risk_4.metric(
            "Reviewable value",
            _money(
                anomalies["total"].sum()
                if not anomalies.empty
                else 0
            ),
        )

        if anomalies.empty:
            st.success(
                "No statistical invoice anomalies are currently open."
            )
        else:
            st.subheader("Highest-Priority Alerts")

            for _, alert in anomalies.head(6).iterrows():
                heading = (
                    f"{alert['risk_level']} risk — "
                    f"{alert['vendor']} / {alert['invoice_number']}"
                )
                message = (
                    f"**Amount:** {_money_precise(alert['total'])}  \n"
                    f"**Date:** {_safe_date(alert['invoice_date'])}  \n"
                    f"**Reason:** {alert['reasons']}"
                )

                if alert["risk_level"] == "High":
                    st.error(f"**{heading}**\n\n{message}")
                elif alert["risk_level"] == "Medium":
                    st.warning(f"**{heading}**\n\n{message}")
                else:
                    st.info(f"**{heading}**\n\n{message}")

            alert_table = anomalies[
                [
                    "invoice_date",
                    "vendor",
                    "invoice_number",
                    "category",
                    "total",
                    "risk_score",
                    "risk_level",
                    "reasons",
                ]
            ].copy()

            alert_table["invoice_date"] = alert_table[
                "invoice_date"
            ].map(_safe_date)
            alert_table["total"] = alert_table["total"].map(
                _money_precise
            )
            alert_table.columns = [
                "Date",
                "Vendor",
                "Invoice No.",
                "Category",
                "Amount",
                "Risk Score",
                "Risk Level",
                "Explanation",
            ]

            st.dataframe(
                alert_table,
                width="stretch",
                hide_index=True,
            )

    # Vendor tab ------------------------------------------------------------
    with tab_vendors:
        st.subheader("Vendor Spend, Stability & Dependency")

        if vendors.empty:
            st.info("No vendor intelligence is available.")
        else:
            left_vendor, right_vendor = st.columns(2)

            with left_vendor:
                top_vendor_chart = vendors.head(10).copy()

                vendor_figure = px.bar(
                    top_vendor_chart.sort_values(
                        "total_spend",
                        ascending=True,
                    ),
                    x="total_spend",
                    y="vendor",
                    orientation="h",
                    labels={
                        "total_spend": "Recorded spend (₹)",
                        "vendor": "Vendor",
                    },
                )
                vendor_figure.update_layout(
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(
                    vendor_figure,
                    width="stretch",
                    config=_plotly_config(),
                )

            with right_vendor:
                score_figure = px.scatter(
                    vendors,
                    x="spend_share",
                    y="vendor_score",
                    size="total_spend",
                    hover_name="vendor",
                    hover_data={
                        "spend_share": ":.1%",
                        "vendor_score": True,
                        "invoice_count": True,
                        "vendor_risk": True,
                        "dependency_risk": True,
                        "total_spend": ":,.0f",
                    },
                    labels={
                        "spend_share": "Share of total spending",
                        "vendor_score": "Vendor score",
                    },
                )
                score_figure.update_layout(
                    xaxis_tickformat=".0%",
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(
                    score_figure,
                    width="stretch",
                    config=_plotly_config(),
                )

            vendor_display = vendors[
                [
                    "vendor",
                    "total_spend",
                    "spend_share",
                    "invoice_count",
                    "average_invoice",
                    "paid_ratio",
                    "open_amount",
                    "consistency_score",
                    "open_anomaly_count",
                    "vendor_score",
                    "vendor_risk",
                    "dependency_risk",
                ]
            ].copy()

            vendor_display["total_spend"] = vendor_display[
                "total_spend"
            ].map(_money)
            vendor_display["spend_share"] = vendor_display[
                "spend_share"
            ].map(_percentage)
            vendor_display["average_invoice"] = vendor_display[
                "average_invoice"
            ].map(_money)
            vendor_display["paid_ratio"] = vendor_display[
                "paid_ratio"
            ].map(_percentage)
            vendor_display["open_amount"] = vendor_display[
                "open_amount"
            ].map(_money)

            vendor_display.columns = [
                "Vendor",
                "Recorded Spend",
                "Spend Share",
                "Invoices",
                "Average Invoice",
                "Paid Ratio",
                "Open Amount",
                "Consistency",
                "Open Alerts",
                "Vendor Score",
                "Vendor Risk",
                "Dependency Risk",
            ]

            st.dataframe(
                vendor_display,
                width="stretch",
                hide_index=True,
            )

    # Health and forecast tab ----------------------------------------------
    with tab_health:
        left_health, right_health = st.columns(2)

        with left_health:
            st.subheader("Explainable Financial Health")

            if health["score"] >= 80:
                st.success(
                    f"Health score: {health['score']}/100 "
                    f"({health['status']})"
                )
            elif health["score"] >= 60:
                st.warning(
                    f"Health score: {health['score']}/100 "
                    f"({health['status']})"
                )
            else:
                st.error(
                    f"Health score: {health['score']}/100 "
                    f"({health['status']})"
                )

            components = pd.DataFrame(health["components"])
            if not components.empty:
                components["Percentage"] = (
                    components["score"]
                    / components["maximum"]
                    * 100
                )

                health_figure = px.bar(
                    components.sort_values(
                        "Percentage",
                        ascending=True,
                    ),
                    x="Percentage",
                    y="component",
                    orientation="h",
                    text="Percentage",
                    labels={
                        "component": "Component",
                        "Percentage": "Score (%)",
                    },
                )
                health_figure.update_traces(
                    texttemplate="%{text:.0f}%",
                    textposition="outside",
                )
                health_figure.update_xaxes(
                    range=[0, 105],
                    ticksuffix="%",
                )
                health_figure.update_layout(
                    margin=dict(l=10, r=20, t=20, b=10),
                )
                st.plotly_chart(
                    health_figure,
                    width="stretch",
                    config=_plotly_config(),
                )

                component_table = components[
                    [
                        "component",
                        "score",
                        "maximum",
                        "status",
                        "evidence",
                        "improvement",
                    ]
                ].copy()
                component_table.columns = [
                    "Component",
                    "Score",
                    "Maximum",
                    "Status",
                    "Evidence",
                    "Improvement Action",
                ]
                st.dataframe(
                    component_table,
                    width="stretch",
                    hide_index=True,
                )

            st.caption(health["disclaimer"])

        with right_health:
            st.subheader("Next-Month Expense Forecast")

            forecast_1, forecast_2, forecast_3 = st.columns(3)
            forecast_1.metric(
                "Low scenario",
                _money(forecast["low_estimate"]),
            )
            forecast_2.metric(
                "Base estimate",
                _money(forecast["base_estimate"]),
            )
            forecast_3.metric(
                "High scenario",
                _money(forecast["high_estimate"]),
            )

            st.metric(
                "Model confidence",
                f"{forecast['confidence']}%",
            )
            st.caption(
                f"Method: {forecast['method']}. "
                "This estimates invoice expense/cash outflow, "
                "not full net cash flow."
            )

            if not monthly.empty:
                forecast_chart = monthly[
                    ["month", "total_spend"]
                ].copy()
                forecast_chart["Type"] = "Recorded"
                forecast_chart = forecast_chart.rename(
                    columns={"total_spend": "Amount"}
                )

                if forecast["next_month"] is not None:
                    forecast_point = pd.DataFrame(
                        [
                            {
                                "month": pd.to_datetime(
                                    forecast["next_month"]
                                ),
                                "Amount": forecast["base_estimate"],
                                "Type": "Forecast",
                            }
                        ]
                    )
                    forecast_chart = pd.concat(
                        [forecast_chart, forecast_point],
                        ignore_index=True,
                    )

                forecast_chart["Month"] = pd.to_datetime(
                    forecast_chart["month"],
                    errors="coerce",
                ).dt.strftime("%b %Y")

                forecast_figure = px.line(
                    forecast_chart,
                    x="Month",
                    y="Amount",
                    color="Type",
                    markers=True,
                    labels={"Amount": "Amount (₹)"},
                )
                forecast_figure.update_layout(
                    legend_title_text="",
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                st.plotly_chart(
                    forecast_figure,
                    width="stretch",
                    config=_plotly_config(),
                )


# ---------------------------------------------------------------------------
# Invoice records page
# ---------------------------------------------------------------------------

def render_invoice_records() -> None:
    st.header("🧾 Invoice Records")
    st.caption(
        "Search, filter and export verified invoices with FinTech AI risk "
        "indicators."
    )

    try:
        analysis = analyse_finances()
    except Exception as error:
        st.error(f"Invoice records could not be loaded: {error}")
        return

    if not analysis["has_data"]:
        st.info("There are no saved invoices.")
        return

    dataframe = analysis["dataframe"].copy()
    anomalies = analysis["anomalies"].copy()

    filters = st.columns(3)
    vendor_search = filters[0].text_input("Search vendor")
    categories = ["All"] + sorted(
        dataframe["category"].dropna().unique().tolist()
    )
    statuses = ["All"] + sorted(
        dataframe["status"].dropna().unique().tolist()
    )
    selected_category = filters[1].selectbox(
        "Category",
        categories,
    )
    selected_status = filters[2].selectbox(
        "Status",
        statuses,
    )

    filtered = dataframe.copy()

    if vendor_search.strip():
        filtered = filtered[
            filtered["vendor"].str.contains(
                vendor_search.strip(),
                case=False,
                na=False,
            )
        ]

    if selected_category != "All":
        filtered = filtered[
            filtered["category"].eq(selected_category)
        ]

    if selected_status != "All":
        filtered = filtered[
            filtered["status"].eq(selected_status)
        ]

    if not anomalies.empty:
        risk_columns = anomalies[
            ["id", "risk_level", "risk_score", "reasons"]
        ].drop_duplicates(subset=["id"])

        filtered = filtered.merge(
            risk_columns,
            on="id",
            how="left",
        )
        filtered["risk_level"] = filtered["risk_level"].fillna("")
        filtered["risk_score"] = filtered["risk_score"].fillna(0)
        filtered["reasons"] = filtered["reasons"].fillna("")
    else:
        filtered["risk_level"] = ""
        filtered["risk_score"] = 0
        filtered["reasons"] = ""

    display = filtered[
        [
            "id",
            "invoice_date",
            "vendor",
            "invoice_number",
            "gst",
            "category",
            "subtotal",
            "tax",
            "total",
            "status",
            "extraction_mode",
            "ocr_confidence",
            "risk_level",
            "risk_score",
            "reasons",
        ]
    ].copy()

    display["invoice_date"] = display["invoice_date"].map(
        _safe_date
    )
    display["subtotal"] = display["subtotal"].map(
        _money_precise
    )
    display["tax"] = display["tax"].map(_money_precise)
    display["total"] = display["total"].map(
        _money_precise
    )
    display["ocr_confidence"] = display.apply(
        lambda row: (
            f"{float(row['ocr_confidence']):.0%}"
            if "OCR" in str(row["extraction_mode"])
            else "—"
        ),
        axis=1,
    )
    display["risk_level"] = display["risk_level"].replace(
        "",
        "No alert",
    )
    display["reasons"] = display["reasons"].replace(
        "",
        "—",
    )

    display.columns = [
        "ID",
        "Date",
        "Vendor",
        "Invoice No.",
        "GST / Tax No.",
        "Category",
        "Subtotal",
        "Tax",
        "Total",
        "Status",
        "Capture Mode",
        "OCR Confidence",
        "AI Risk",
        "Risk Score",
        "Risk Explanation",
    ]

    result_1, result_2, result_3 = st.columns(3)
    result_1.metric("Filtered invoices", len(display))
    result_2.metric(
        "Filtered value",
        _money(filtered["total"].sum()),
    )
    result_3.metric(
        "Invoices with alerts",
        int(filtered["risk_level"].ne("").sum()),
    )

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
    )

    csv_data = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered records as CSV",
        data=csv_data,
        file_name="fintech_ai_invoice_records.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Vendor memory page
# ---------------------------------------------------------------------------

def render_vendor_memory() -> None:
    st.header("🧠 Adaptive Vendor Memory")
    st.write(
        "FinTech AI remembers verified GST details and preferred expense "
        "categories for recurring vendors."
    )

    records = get_all_vendor_memory()
    if not records:
        st.info(
            "No vendor memory exists yet. Save an invoice with vendor "
            "memory enabled."
        )
        return

    dataframe = pd.DataFrame(records)
    dataframe.columns = [
        "Vendor",
        "Verified GST / Tax No.",
        "Preferred Category",
        "Times Seen",
        "Last Updated",
    ]

    st.dataframe(
        dataframe,
        width="stretch",
        hide_index=True,
    )

    st.success(
        "When OCR recognises one of these vendors again, verified GST and "
        "category information are automatically suggested for human review."
    )