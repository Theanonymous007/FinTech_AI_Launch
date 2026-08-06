from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st
from ai_engine import analyse_finances


def _money(value: Any) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def _safe_date(value: Any) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return "—" if pd.isna(parsed) else parsed.strftime("%d %b %Y")


def _alert_type(reason: str) -> str:
    text = (reason or "").casefold()
    if "appear more than once" in text or "duplicate" in text:
        return "Possible Duplicate"
    if "tax rate" in text:
        return "Tax Inconsistency"
    if "vendor's median" in text:
        return "Vendor Amount Anomaly"
    if "category median" in text:
        return "Category Amount Anomaly"
    if "high-value limit" in text:
        return "High-Value Outlier"
    if "zero" in text:
        return "Invalid Amount"
    return "Unusual Pattern"


def render_risk_centre() -> None:
    st.header("🚨 FinTech AI Fraud & Risk Centre")
    st.caption(
        "Detects potential fraud indicators, duplicate identities, unusual "
        "invoice amounts and tax inconsistencies for human review."
    )

    try:
        analysis = analyse_finances()
    except Exception as error:
        st.error(f"The Risk Centre could not analyse the database: {error}")
        return

    if not analysis["has_data"]:
        st.info("Upload verified invoices or load synthetic demo data first.")
        return

    anomalies = analysis["anomalies"].copy()
    vendors = analysis["vendors"].copy()
    summary = analysis["summary"]

    high = int(anomalies["risk_level"].eq("High").sum()) if not anomalies.empty else 0
    medium = int(anomalies["risk_level"].eq("Medium").sum()) if not anomalies.empty else 0
    low = int(anomalies["risk_level"].eq("Low").sum()) if not anomalies.empty else 0
    overall = "High" if high else "Medium" if medium else "Low"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall risk status", overall)
    c2.metric("High-risk alerts", high)
    c3.metric("Open alerts", high + medium + low)
    c4.metric(
        "Value requiring review",
        _money(anomalies["total"].sum() if not anomalies.empty else 0),
    )

    if overall == "High":
        st.error("High-priority invoice review is required.")
    elif overall == "Medium":
        st.warning("Moderate anomaly risk is present.")
    else:
        st.success("No high-priority statistical alert is currently open.")

    st.caption(
        "FinTech AI flags suspicious patterns. It does not prove that fraud occurred."
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["⚠️ Invoice Alerts", "📊 Risk Patterns", "🏢 Vendor Risk", "✅ Review Workflow"]
    )

    with tab1:
        if anomalies.empty:
            st.success("No statistical invoice anomaly is currently open.")
        else:
            levels = st.multiselect(
                "Show severity",
                ["High", "Medium", "Low"],
                default=["High", "Medium", "Low"],
            )
            filtered = anomalies[anomalies["risk_level"].isin(levels)].copy()

            for _, alert in filtered.head(8).iterrows():
                title = (
                    f"{alert['risk_level']} — {_alert_type(alert['reasons'])}: "
                    f"{alert['vendor']} / {alert['invoice_number']}"
                )
                body = (
                    f"**Date:** {_safe_date(alert['invoice_date'])}  \n"
                    f"**Amount:** {_money(alert['total'])}  \n"
                    f"**Risk score:** {int(alert['risk_score'])}/100  \n"
                    f"**Reason:** {alert['reasons']}"
                )
                if alert["risk_level"] == "High":
                    st.error(f"**{title}**\n\n{body}")
                elif alert["risk_level"] == "Medium":
                    st.warning(f"**{title}**\n\n{body}")
                else:
                    st.info(f"**{title}**\n\n{body}")

            table = filtered[
                ["invoice_date", "vendor", "invoice_number", "category",
                 "total", "risk_score", "risk_level", "reasons"]
            ].copy()
            table.insert(4, "alert_type", table["reasons"].map(_alert_type))
            table["invoice_date"] = table["invoice_date"].map(_safe_date)
            table["total"] = table["total"].map(_money)
            table.columns = [
                "Date", "Vendor", "Invoice No.", "Category", "Alert Type",
                "Amount", "Risk Score", "Risk Level", "Explanation"
            ]
            st.dataframe(table, width="stretch", hide_index=True)

    with tab2:
        if anomalies.empty:
            st.info("No risk pattern data is available.")
        else:
            patterns = (
                anomalies.assign(alert_type=anomalies["reasons"].map(_alert_type))
                .groupby("alert_type", as_index=False)
                .agg(
                    alerts=("id", "count"),
                    reviewable_value=("total", "sum"),
                    average_risk=("risk_score", "mean"),
                )
                .sort_values("alerts", ascending=False)
            )
            patterns["reviewable_value"] = patterns["reviewable_value"].map(_money)
            patterns["average_risk"] = patterns["average_risk"].map(
                lambda x: f"{float(x):.0f}/100"
            )
            patterns.columns = [
                "Pattern", "Alerts", "Reviewable Value", "Average Risk"
            ]
            st.dataframe(patterns, width="stretch", hide_index=True)

            st.markdown(
                """
- **Possible Duplicate:** Same vendor and invoice number appear more than once.
- **Vendor Amount Anomaly:** Invoice is above that vendor's normal history.
- **Category Amount Anomaly:** Invoice is unusual for its expense category.
- **Tax Inconsistency:** Tax differs from the vendor's normal pattern.
- **High-Value Outlier:** Amount exceeds the dataset's robust threshold.
                """
            )

    with tab3:
        if vendors.empty:
            st.info("No vendor intelligence is available.")
        else:
            display = vendors[
                ["vendor", "total_spend", "spend_share", "invoice_count",
                 "open_amount", "open_anomaly_count", "vendor_score",
                 "vendor_risk", "dependency_risk"]
            ].copy()
            display["total_spend"] = display["total_spend"].map(_money)
            display["spend_share"] = display["spend_share"].map(
                lambda x: f"{float(x):.0%}"
            )
            display["open_amount"] = display["open_amount"].map(_money)
            display.columns = [
                "Vendor", "Recorded Spend", "Spend Share", "Invoices",
                "Open Amount", "Open Alerts", "Vendor Score",
                "Vendor Risk", "Dependency Risk"
            ]
            st.dataframe(display, width="stretch", hide_index=True)

            top = vendors.iloc[0]
            if float(top["spend_share"]) >= 0.40:
                st.warning(
                    f"{top['vendor']} represents {float(top['spend_share']):.0%} "
                    "of total spend, creating supplier concentration risk."
                )

    with tab4:
        st.write(
            "Prototype review decisions are stored for the current session. "
            "Persistent audit storage can be added next."
        )

        if anomalies.empty:
            st.success("There is no open anomaly to review.")
        else:
            options = {
                f"#{int(row['id'])} — {row['vendor']} / {row['invoice_number']}": row
                for _, row in anomalies.iterrows()
            }
            selected_label = st.selectbox("Select an alert", list(options.keys()))
            selected = options[selected_label]

            st.write(f"**Reason:** {selected['reasons']}")
            st.write(f"**Amount:** {_money(selected['total'])}")

            decision = st.radio(
                "Review decision",
                [
                    "Needs further review",
                    "Expected / valid transaction",
                    "Confirmed data-entry issue",
                    "Escalate for investigation",
                ],
            )
            note = st.text_area("Reviewer note")

            if st.button("Save session review", type="primary", width="stretch"):
                st.session_state.setdefault("fintech_risk_reviews", {})
                st.session_state["fintech_risk_reviews"][int(selected["id"])] = {
                    "decision": decision,
                    "note": note.strip(),
                }
                st.success("Review decision saved for this session.")

            reviews = st.session_state.get("fintech_risk_reviews", {})
            if reviews:
                review_rows = [
                    {
                        "Invoice ID": invoice_id,
                        "Decision": review["decision"],
                        "Reviewer Note": review["note"] or "—",
                    }
                    for invoice_id, review in reviews.items()
                ]
                st.dataframe(
                    pd.DataFrame(review_rows),
                    width="stretch",
                    hide_index=True,
                )

    st.divider()
    st.caption(
        f"Database: {summary['invoice_count']} invoice(s), "
        f"{_money(summary['total_spend'])} recorded spend."
    )
