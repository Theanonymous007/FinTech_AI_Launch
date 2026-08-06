from __future__ import annotations

from typing import Any

import streamlit as st

from ai_engine import analyse_finances, answer_finance_question


SUGGESTED_QUESTIONS = [
    "What is my total spend?",
    "Which vendor received the most money?",
    "Where am I spending the most?",
    "Which invoices look unusual?",
    "Why is my health score low?",
    "What may expenses be next month?",
    "What should I do first?",
]


def _money(value: Any) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def _assistant_intro(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    health = analysis["health"]
    forecast = analysis["forecast"]

    return (
        f"I reviewed {summary['invoice_count']} verified invoice(s) worth "
        f"{_money(summary['total_spend'])}. Your financial-health indicator is "
        f"{health['score']}/100 ({health['status']}), and the next-month "
        f"invoice-expense estimate is {_money(forecast['base_estimate'])}."
    )


def render_ask_fintech_ai() -> None:
    st.header("💬 Ask FinTech AI")
    st.caption(
        "Ask grounded financial questions using your verified invoice database."
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

    if "fintech_chat_messages" not in st.session_state:
        st.session_state["fintech_chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your grounded financial assistant. "
                    + _assistant_intro(analysis)
                ),
            }
        ]

    st.subheader("Suggested questions")

    cols = st.columns(3)
    for index, question in enumerate(SUGGESTED_QUESTIONS):
        if cols[index % 3].button(
            question,
            key=f"suggested_question_{index}",
            width="stretch",
        ):
            st.session_state["fintech_pending_question"] = question
            st.rerun()

    st.divider()

    for message in st.session_state["fintech_chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    pending_question = st.session_state.pop(
        "fintech_pending_question",
        None,
    )

    user_question = st.chat_input(
        "Ask about spending, vendors, risks, health score or forecast..."
    )

    question = pending_question or user_question

    if question:
        st.session_state["fintech_chat_messages"].append(
            {
                "role": "user",
                "content": question,
            }
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("FinTech AI is analysing verified records..."):
                answer = answer_finance_question(
                    question,
                    analysis,
                )
                st.markdown(answer)

        st.session_state["fintech_chat_messages"].append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

    st.divider()

    left, right = st.columns(2)

    with left:
        if st.button(
            "Clear conversation",
            width="stretch",
        ):
            st.session_state.pop(
                "fintech_chat_messages",
                None,
            )
            st.rerun()

    with right:
        st.caption(
            "Answers are generated only from verified local invoice records."
        )

    st.warning(
        "FinTech AI provides decision support, not legal, tax, audit or "
        "investment advice. Suspicious-pattern alerts require human review."
    )
