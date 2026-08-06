from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ai_engine import analyse_finances, answer_finance_question


def _money(value: Any) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def _percentage(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "0%"


def _risk_summary(anomalies: pd.DataFrame) -> dict[str, Any]:
    if anomalies.empty:
        return {
            "label": "Low",
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0,
            "reviewable_amount": 0.0,
        }

    high = int(anomalies["risk_level"].eq("High").sum())
    medium = int(anomalies["risk_level"].eq("Medium").sum())
    low = int(anomalies["risk_level"].eq("Low").sum())

    if high:
        label = "High"
    elif medium:
        label = "Medium"
    else:
        label = "Low"

    return {
        "label": label,
        "high": high,
        "medium": medium,
        "low": low,
        "total": high + medium + low,
        "reviewable_amount": float(anomalies["total"].sum()),
    }


def _executive_briefing(analysis: dict[str, Any]) -> list[str]:
    summary = analysis["summary"]
    health = analysis["health"]
    forecast = analysis["forecast"]
    vendors = analysis["vendors"]
    categories = analysis["categories"]
    anomalies = analysis["anomalies"]

    paragraphs: list[str] = []

    paragraphs.append(
        f"FinTech AI reviewed **{summary['invoice_count']} verified invoice(s)** "
        f"with a recorded value of **{_money(summary['total_spend'])}**. "
        f"The internal financial-health indicator is "
        f"**{health['score']}/100 ({health['status']})**."
    )

    if summary["overdue_amount"] > 0:
        paragraphs.append(
            f"The most urgent payment issue is **{_money(summary['overdue_amount'])} "
            f"in overdue invoices**. These records should be verified against "
            f"their agreed due dates and prioritised where supplier continuity "
            f"could be affected."
        )
    elif summary["pending_amount"] > 0:
        paragraphs.append(
            f"There is **{_money(summary['pending_amount'])} in pending invoices**. "
            f"Review due dates and expected payment timing before approving "
            f"additional non-essential expenditure."
        )
    else:
        paragraphs.append(
            "No pending or overdue invoice exposure is currently recorded."
        )

    if not vendors.empty:
        top_vendor = vendors.iloc[0]
        paragraphs.append(
            f"**{top_vendor['vendor']}** is the largest recorded supplier at "
            f"**{_money(top_vendor['total_spend'])}**, representing "
            f"**{_percentage(top_vendor['spend_share'])}** of total spending. "
            f"Its dependency risk is **{top_vendor['dependency_risk']}**."
        )

    if not categories.empty:
        top_category = categories.iloc[0]
        paragraphs.append(
            f"The largest expense category is **{top_category['category']}** at "
            f"**{_money(top_category['total_spend'])}** "
            f"({_percentage(top_category['spend_share'])} of recorded spend)."
        )

    if forecast["next_month"] is not None:
        paragraphs.append(
            f"The next-month invoice-expense estimate is "
            f"**{_money(forecast['base_estimate'])}**, with a current range of "
            f"**{_money(forecast['low_estimate'])} to "
            f"{_money(forecast['high_estimate'])}** and "
            f"**{forecast['confidence']}% model confidence**."
        )

    risk = _risk_summary(anomalies)
    if risk["total"]:
        paragraphs.append(
            f"The anomaly engine found **{risk['total']} review alert(s)** "
            f"covering **{_money(risk['reviewable_amount'])}**. These are "
            f"potential fraud indicators or unusual patterns requiring human "
            f"review; they are not proof that fraud occurred."
        )
    else:
        paragraphs.append(
            "No statistical invoice anomalies are currently open. This does "
            "not guarantee that every invoice is correct."
        )

    return paragraphs


def _show_priority_card(recommendation: dict[str, Any]) -> None:
    priority = recommendation["priority"]
    title = recommendation["title"]
    evidence = recommendation["evidence"]
    action = recommendation["action"]
    reviewable_amount = float(recommendation.get("reviewable_amount", 0) or 0)

    body = (
        f"**{priority} priority — {title}**\n\n"
        f"**Evidence:** {evidence}\n\n"
        f"**Recommended action:** {action}"
    )

    if reviewable_amount > 0:
        body += f"\n\n**Amount requiring review:** {_money(reviewable_amount)}"

    if priority == "High":
        st.error(body)
    elif priority == "Medium":
        st.warning(body)
    else:
        st.info(body)


def _show_weakest_health_area(health: dict[str, Any]) -> None:
    weakest = health.get("weakest_components", [])
    if not weakest:
        st.success("No major health-score weakness was identified.")
        return

    st.subheader("Why the score is not higher")

    for component in weakest[:3]:
        ratio = (
            float(component["score"]) / float(component["maximum"])
            if component["maximum"]
            else 0.0
        )

        st.write(
            f"**{component['component']} — "
            f"{component['score']}/{component['maximum']} "
            f"({_percentage(ratio)})**"
        )
        st.caption(component["evidence"])
        st.info(component["improvement"])


def _render_grounded_question_box(analysis: dict[str, Any]) -> None:
    st.subheader("Ask FinTech AI")
    st.caption(
        "Answers are calculated only from the verified local invoice database. "
        "This is a grounded analytics assistant, not a general-purpose chatbot."
    )

    suggested_questions = [
        "What is my total spend?",
        "Which vendor received the most money?",
        "Where am I spending the most?",
        "Which invoices look unusual?",
        "Why is my health score low?",
        "What may expenses be next month?",
        "What should I do first?",
    ]

    button_columns = st.columns(3)
    for index, question in enumerate(suggested_questions):
        if button_columns[index % 3].button(
            question,
            key=f"advisor_suggestion_{index}",
            width="stretch",
        ):
            st.session_state["fintech_ai_question"] = question

    question = st.text_input(
        "Your financial question",
        key="fintech_ai_question",
        placeholder="Example: Which vendor received the most money?",
    )

    if st.button(
        "Ask FinTech AI",
        type="primary",
        width="stretch",
    ):
        if not question.strip():
            st.warning("Type or select a financial question.")
        else:
            answer = answer_finance_question(question, analysis)
            st.session_state["fintech_ai_last_answer"] = answer

    last_answer = st.session_state.get("fintech_ai_last_answer")
    if last_answer:
        st.success(f"**FinTech AI:** {last_answer}")


def render_financial_advisor() -> None:
    st.header("🤖 FinTech AI Financial Advisor")
    st.caption(
        "A grounded decision-support layer that converts verified invoice "
        "records into priorities, explanations, forecasts and recommended actions."
    )

    try:
        analysis = analyse_finances()
    except Exception as error:
        st.error(f"The Financial Advisor could not analyse the database: {error}")
        return

    if not analysis["has_data"]:
        st.info(
            "No verified invoices are available yet. Open AI Invoice Capture "
            "or load synthetic demo data."
        )
        return

    summary = analysis["summary"]
    health = analysis["health"]
    forecast = analysis["forecast"]
    anomalies = analysis["anomalies"]
    recommendations = analysis["recommendations"]
    vendors = analysis["vendors"]

    risk = _risk_summary(anomalies)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Financial health", f"{health['score']}/100")
    metric_2.metric("Risk status", risk["label"])
    metric_3.metric("Open invoice exposure", _money(
        summary["pending_amount"] + summary["overdue_amount"]
    ))
    metric_4.metric("Next-month estimate", _money(forecast["base_estimate"]))

    st.subheader("Executive Briefing")
    for paragraph in _executive_briefing(analysis):
        st.markdown(paragraph)

    st.divider()
    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("Top Priorities")

        if not recommendations:
            st.success(
                "No urgent recommendation was generated from the current records."
            )
        else:
            for recommendation in recommendations[:5]:
                _show_priority_card(recommendation)

    with right:
        _show_weakest_health_area(health)

        if not vendors.empty:
            st.subheader("Supplier Focus")
            top_vendor = vendors.iloc[0]
            st.metric(
                "Largest supplier",
                top_vendor["vendor"],
                delta=f"{_percentage(top_vendor['spend_share'])} of spend",
                delta_color="off",
            )
            st.write(
                f"Vendor score: **{int(top_vendor['vendor_score'])}/100**"
            )
            st.write(
                f"Vendor risk: **{top_vendor['vendor_risk']}**"
            )
            st.write(
                f"Dependency risk: **{top_vendor['dependency_risk']}**"
            )
            st.write(
                f"Open amount: **{_money(top_vendor['open_amount'])}**"
            )

    st.divider()
    _render_grounded_question_box(analysis)

    st.divider()
    st.caption(
        "FinTech AI provides explainable decision support. Anomaly alerts are "
        "potential fraud indicators requiring human review, not proof of fraud. "
        "The health score is not a bank credit score, and the forecast estimates "
        "invoice expense/cash outflow rather than complete net cash flow."
    )
