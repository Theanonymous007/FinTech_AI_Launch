from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_engine import analyse_finances
from database import get_all_vendor_memory
from ui_components import (
    apply_plotly_theme,
    navigate_to,
    render_definition_grid,
    render_empty_state,
    render_insight_card,
    render_kpi_card,
    render_section_header,
    render_stat_strip,
    render_status_banner,
    render_todo_item,
)


def _money(value: Any) -> str:
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
    return "—" if pd.isna(parsed) else parsed.strftime("%d %b %Y")


def _risk_overview(anomalies: pd.DataFrame) -> dict[str, Any]:
    if anomalies.empty:
        return {
            "label": "Low",
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
        "label": "High" if high else "Medium" if medium else "Low",
        "high": high,
        "medium": medium,
        "low": low,
        "total": high + medium + low,
        "reviewable": float(anomalies["total"].sum()),
    }


def _plotly_config() -> dict[str, Any]:
    return {"displayModeBar": False, "responsive": True, "scrollZoom": False}


def _recent_invoice_table(dataframe: pd.DataFrame, limit: int = 5) -> None:
    recent = dataframe.sort_values(["invoice_date", "id"], ascending=[False, False]).head(limit)
    display = recent[["invoice_date", "vendor", "invoice_number", "category", "status", "total"]].copy()
    display["invoice_date"] = display["invoice_date"].map(_safe_date)
    display["total"] = display["total"].map(_money_precise)
    display.columns = ["Date", "Vendor", "Invoice No.", "Category", "Status", "Total"]
    st.dataframe(display, use_container_width=True, hide_index=True, height=230)


def _monthly_chart(monthly: pd.DataFrame, forecast: dict[str, Any]) -> go.Figure:
    chart = monthly[["month", "total_spend"]].copy()
    chart["month"] = pd.to_datetime(chart["month"], errors="coerce")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=chart["month"],
            y=chart["total_spend"],
            mode="lines+markers",
            name="Recorded spend",
            line={"color": "#23C7D7", "width": 3},
            marker={"size": 7, "color": "#23C7D7"},
            fill="tozeroy",
            fillcolor="rgba(35,199,215,0.10)",
            hovertemplate="%{x|%b %Y}<br><b>₹%{y:,.0f}</b><extra></extra>",
        )
    )
    if forecast.get("next_month") is not None:
        figure.add_trace(
            go.Scatter(
                x=[pd.to_datetime(forecast["next_month"])],
                y=[forecast["base_estimate"]],
                mode="markers",
                name="Next estimate",
                marker={"size": 11, "color": "#0B6B80", "symbol": "diamond"},
                hovertemplate="Next estimate<br><b>₹%{y:,.0f}</b><extra></extra>",
            )
        )
    apply_plotly_theme(figure, height=350, show_legend=True)
    figure.update_xaxes(title_text="")
    figure.update_yaxes(title_text="Amount (₹)", rangemode="tozero")
    return figure


def _category_chart(categories: pd.DataFrame) -> go.Figure:
    figure = px.pie(
        categories.head(7),
        names="category",
        values="total_spend",
        hole=0.68,
        color_discrete_sequence=[
            "#23C7D7",
            "#0B6B80",
            "#35B58A",
            "#E4A84E",
            "#6F79D8",
            "#8ABEC7",
            "#E56565",
        ],
    )
    figure.update_traces(
        textinfo="percent",
        textposition="inside",
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
        marker={"line": {"color": "#FFFFFF", "width": 2}},
    )
    apply_plotly_theme(figure, height=350, show_legend=True, horizontal_legend=False)
    figure.update_layout(
        legend={
            "orientation": "v",
            "yanchor": "middle",
            "y": 0.5,
            "xanchor": "left",
            "x": 1.0,
        }
    )
    return figure


def render_dashboard() -> None:
    try:
        analysis = analyse_finances()
    except Exception as error:
        render_status_banner(
            "We could not open your financial overview",
            "Your records are unchanged. Check that the database files are available and try again.",
            tone="danger",
        )
        with st.expander("Technical details"):
            st.code(str(error))
        return

    if not analysis["has_data"]:
        render_empty_state(
            "No invoices yet",
            "Upload your first invoice to start building a clear financial overview, or load the safe demo workspace.",
            icon="＋",
        )
        action_1, action_2, spacer = st.columns([1, 1, 2])
        if action_1.button("Upload invoice", type="primary", use_container_width=True):
            navigate_to("Capture invoice")
        if action_2.button("Load demo data", use_container_width=True):
            navigate_to("Demo workspace")
        del spacer
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

    open_exposure = float(summary["pending_amount"] + summary["overdue_amount"])
    health_tone = "success" if health["score"] >= 80 else "warning" if health["score"] >= 60 else "danger"
    exposure_tone = "danger" if summary["overdue_amount"] else "warning" if open_exposure else "success"
    risk_tone = "danger" if risk["label"] == "High" else "warning" if risk["label"] == "Medium" else "success"

    # Only the four values a non-technical owner needs first.
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        render_kpi_card(
            "Total spend",
            _money(summary["total_spend"]),
            f"{summary['invoice_count']} verified invoice(s)",
            tone="info",
            icon="₹",
        )
    with k2:
        render_kpi_card(
            "Pending and overdue",
            _money(open_exposure),
            f"Pending {_money(summary['pending_amount'])} · Overdue {_money(summary['overdue_amount'])}",
            tone=exposure_tone,
            icon="◷",
        )
    with k3:
        render_kpi_card(
            "Financial health",
            f"{health['score']}/100",
            f"{health['status']} · Open for a simple explanation",
            tone=health_tone,
            icon="♥",
        )
    with k4:
        render_kpi_card(
            "Next month estimate",
            _money(forecast["base_estimate"]),
            f"{forecast['confidence']}% confidence · Invoice expenses",
            tone="info",
            icon="↗",
        )

    render_stat_strip(
        [
            ("Active vendors", f"{summary['vendor_count']:,}", "Suppliers in the ledger"),
            ("Categories", f"{summary['category_count']:,}", "Expense groups"),
            ("Risk status", risk["label"], f"{risk['total']} open alert(s)"),
            ("Verified period", _safe_date(summary["date_from"]), f"to {_safe_date(summary['date_to'])}"),
        ]
    )

    render_section_header(
        "Spending overview",
        "Two simple views of how much you spent and where the money went.",
    )
    chart_1, chart_2 = st.columns([1.35, 1], gap="large")
    with chart_1:
        if monthly.empty:
            render_empty_state("More history is needed", "Add dated invoices across multiple months to see the spending trend.", icon="↗")
        else:
            st.plotly_chart(_monthly_chart(monthly, forecast), use_container_width=True, config=_plotly_config())
    with chart_2:
        if categories.empty:
            render_empty_state("No category data", "Verified expense categories will appear here.", icon="◫")
        else:
            st.plotly_chart(_category_chart(categories), use_container_width=True, config=_plotly_config())

    render_section_header(
        "Needs your attention",
        "Only the most useful next actions are shown here.",
    )
    if recommendations:
        for item in recommendations[:3]:
            amount = (
                _money(item.get("reviewable_amount", 0))
                if float(item.get("reviewable_amount", 0) or 0) > 0
                else None
            )
            priority = str(item.get("priority", "Action"))
            tone = "danger" if priority == "High" else "warning" if priority == "Medium" else "info"
            render_todo_item(
                str(item["title"]),
                f"{item['evidence']} Next: {item['action']}",
                priority=priority,
                tone=tone,
                amount=amount,
            )
    else:
        render_status_banner(
            "Nothing urgent is open",
            "Continue verifying invoices normally. The system will show an action here when something needs attention.",
            tone="success",
        )

    if risk["total"]:
        if st.button(f"Review {risk['total']} alert(s)", key="overview_review_alerts"):
            navigate_to("Risk review")

    render_section_header("Quick actions", "The three tasks used most often.")
    q1, q2, q3 = st.columns(3, gap="medium")
    if q1.button("＋  Upload invoice", type="primary", use_container_width=True):
        navigate_to("Capture invoice")
    if q2.button("⇩  Generate report", use_container_width=True):
        navigate_to("Executive report")
    if q3.button("✦  Ask FinTech AI", use_container_width=True):
        navigate_to("Ask FinTech AI")

    render_section_header("Recent activity", "Your latest verified invoices.")
    _recent_invoice_table(dataframe, limit=5)
    if st.button("View all invoices", key="overview_view_records"):
        navigate_to("Invoice records")


def render_invoice_records() -> None:
    try:
        analysis = analyse_finances()
    except Exception as error:
        render_status_banner("Invoice records could not be loaded", "Your data is unchanged. Try again after checking the local database.", tone="danger")
        with st.expander("Technical details"):
            st.code(str(error))
        return

    if not analysis["has_data"]:
        render_empty_state("No invoice records", "Upload an invoice or load demo data to start the ledger.", icon="▤")
        if st.button("Upload invoice", type="primary"):
            navigate_to("Capture invoice")
        return

    dataframe = analysis["dataframe"].copy()
    anomalies = analysis["anomalies"].copy()

    filters = st.columns([1.5, 1, 1], gap="medium")
    search_text = filters[0].text_input("Search", placeholder="Vendor or invoice number")
    category_options = ["All categories"] + sorted(dataframe["category"].dropna().unique().tolist())
    status_options = ["All statuses"] + sorted(dataframe["status"].dropna().unique().tolist())
    category = filters[1].selectbox("Category", category_options)
    status = filters[2].selectbox("Payment status", status_options)

    filtered = dataframe.copy()
    if search_text.strip():
        needle = search_text.strip()
        filtered = filtered[
            filtered["vendor"].str.contains(needle, case=False, na=False)
            | filtered["invoice_number"].str.contains(needle, case=False, na=False)
        ]
    if category != "All categories":
        filtered = filtered[filtered["category"].eq(category)]
    if status != "All statuses":
        filtered = filtered[filtered["status"].eq(status)]

    if not anomalies.empty:
        risk_columns = anomalies[["id", "risk_level", "risk_score", "reasons"]].drop_duplicates("id")
        filtered = filtered.merge(risk_columns, on="id", how="left")
    else:
        filtered["risk_level"] = ""
        filtered["risk_score"] = 0
        filtered["reasons"] = ""

    filtered["risk_level"] = filtered["risk_level"].fillna("")
    filtered["risk_score"] = filtered["risk_score"].fillna(0)
    filtered["reasons"] = filtered["reasons"].fillna("")
    alert_count = int(filtered["risk_level"].ne("").sum())

    render_stat_strip(
        [
            ("Matching invoices", f"{len(filtered):,}", "Current filters"),
            ("Combined value", _money(filtered["total"].sum()), "Matching invoices"),
            ("Open alerts", str(alert_count), "Needs review" if alert_count else "None"),
            ("Search state", "Filtered" if search_text or category != "All categories" or status != "All statuses" else "All records", "Ledger view"),
        ]
    )

    if filtered.empty:
        render_empty_state("No matching invoices", "Change or clear a filter to see more records.", icon="⌕")
        return

    primary = filtered[["invoice_date", "vendor", "invoice_number", "category", "status", "total", "risk_level"]].copy()
    primary["invoice_date"] = primary["invoice_date"].map(_safe_date)
    primary["total"] = primary["total"].map(_money_precise)
    primary["risk_level"] = primary["risk_level"].replace("", "No alert")
    primary.columns = ["Date", "Vendor", "Invoice No.", "Category", "Status", "Total", "Risk"]
    st.dataframe(primary, use_container_width=True, hide_index=True, height=420)

    render_section_header("Invoice details", "Choose one record only when you need the full information.", compact=True)
    options = {
        f"#{int(row['id'])} · {row['vendor']} · {row['invoice_number']}": row
        for _, row in filtered.sort_values(["invoice_date", "id"], ascending=[False, False]).iterrows()
    }
    selected_label = st.selectbox("Select invoice", list(options.keys()), label_visibility="collapsed")
    selected = options[selected_label]
    render_definition_grid(
        [
            ("Vendor", selected["vendor"]),
            ("Invoice number", selected["invoice_number"]),
            ("Invoice date", _safe_date(selected["invoice_date"])),
            ("GST / Tax number", selected["gst"] or "Not recorded"),
            ("Category", selected["category"]),
            ("Payment status", selected["status"]),
            ("Subtotal", _money_precise(selected["subtotal"])),
            ("Tax", _money_precise(selected["tax"])),
            ("Final total", _money_precise(selected["total"])),
            ("Capture method", selected["extraction_mode"]),
            ("Risk", selected["risk_level"] or "No alert"),
            ("Risk reason", selected["reasons"] or "No unusual pattern is open"),
        ]
    )

    csv_display = filtered.copy()
    download_col, capture_col, spacer = st.columns([1, 1, 2])
    download_col.download_button(
        "Download filtered CSV",
        data=csv_display.to_csv(index=False).encode("utf-8"),
        file_name="fintech_ai_invoice_records.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if capture_col.button("Upload another", use_container_width=True):
        navigate_to("Capture invoice")
    del spacer


def render_vendor_intelligence() -> None:
    try:
        analysis = analyse_finances()
    except Exception as error:
        render_status_banner("Vendor information could not be loaded", "Try again after checking the local database.", tone="danger")
        with st.expander("Technical details"):
            st.code(str(error))
        return

    vendors = analysis.get("vendors", pd.DataFrame()).copy()
    if vendors.empty:
        render_empty_state("No vendor information yet", "Vendor insights appear after verified invoices are saved.", icon="◇")
        if st.button("Upload invoice", type="primary"):
            navigate_to("Capture invoice")
        return

    top = vendors.iloc[0]
    high_dependency = int(vendors["dependency_risk"].eq("High").sum())
    total_open = float(vendors["open_amount"].sum())
    render_stat_strip(
        [
            ("Largest supplier", str(top["vendor"]), _percentage(top["spend_share"]) + " of spend"),
            ("Active vendors", f"{len(vendors):,}", "Verified suppliers"),
            ("Open vendor amount", _money(total_open), "Pending or overdue"),
            ("High dependency", str(high_dependency), "Supplier concentration"),
        ]
    )

    render_section_header("Where the money goes", "A simple view of supplier spend and dependency.")
    chart_data = vendors.head(10).sort_values("total_spend", ascending=True)
    figure = px.bar(
        chart_data,
        x="total_spend",
        y="vendor",
        orientation="h",
        color="dependency_risk",
        color_discrete_map={"Low": "#35B58A", "Medium": "#E4A84E", "High": "#E56565"},
        labels={"total_spend": "Recorded spend (₹)", "vendor": "", "dependency_risk": "Dependency"},
        hover_data={"spend_share": ":.1%", "invoice_count": True},
    )
    apply_plotly_theme(figure, height=430, show_legend=True)
    st.plotly_chart(figure, use_container_width=True, config=_plotly_config())

    tone = "danger" if top["dependency_risk"] == "High" else "warning" if top["dependency_risk"] == "Medium" else "info"
    render_insight_card(
        str(top["vendor"]),
        f"This supplier has {_money(top['total_spend'])} in recorded spend and {_money(top['open_amount'])} currently open.",
        label="Largest supplier",
        tone=tone,
        footer=f"Dependency risk {top['dependency_risk']} · Vendor score {int(top['vendor_score'])}/100",
    )

    render_section_header("Vendor list", "The main information first. Detailed statistics remain available below.")
    display = vendors[["vendor", "total_spend", "spend_share", "invoice_count", "open_amount", "vendor_score", "vendor_risk", "dependency_risk"]].copy()
    display["total_spend"] = display["total_spend"].map(_money)
    display["spend_share"] = display["spend_share"].map(_percentage)
    display["open_amount"] = display["open_amount"].map(_money)
    display.columns = ["Vendor", "Spend", "Share", "Invoices", "Open Amount", "Score", "Vendor Risk", "Dependency"]
    st.dataframe(display, use_container_width=True, hide_index=True, height=390)

    with st.expander("How vendor scores are interpreted"):
        st.write(
            "Vendor scores combine invoice consistency, payment performance and the share of invoices with open anomaly alerts. "
            "Dependency risk is based on how much of total spending is concentrated with one supplier."
        )


def render_vendor_memory() -> None:
    records = get_all_vendor_memory()
    if not records:
        render_empty_state(
            "No vendor memory yet",
            "When you confirm a recurring vendor, FinTech AI can suggest the same GST and category next time. You still approve every field.",
            icon="◎",
        )
        if st.button("Upload invoice", type="primary"):
            navigate_to("Capture invoice")
        return

    dataframe = pd.DataFrame(records)
    dataframe.columns = ["Vendor", "Verified GST / Tax No.", "Preferred Category", "Times Seen", "Last Updated"]

    render_status_banner(
        "Faster recurring invoice review",
        "Vendor memory only suggests previously confirmed details. It never bypasses human verification.",
        tone="info",
    )
    render_stat_strip(
        [
            ("Remembered vendors", str(len(dataframe)), "Recurring suppliers"),
            ("Confirmations", str(int(dataframe["Times Seen"].sum())), "Verified encounters"),
            ("Most common category", str(dataframe["Preferred Category"].mode().iloc[0]), "Confirmed preference"),
            ("Control", "Human verified", "Suggestions remain editable"),
        ]
    )
    st.dataframe(dataframe, use_container_width=True, hide_index=True, height=420)
    if st.button("Upload recurring invoice", type="primary"):
        navigate_to("Capture invoice")
