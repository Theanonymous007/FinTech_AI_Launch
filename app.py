import streamlit as st

from advisor import render_financial_advisor
from ask_ai import render_ask_fintech_ai
from dashboard import (
    render_dashboard,
    render_invoice_records,
    render_vendor_memory,
)
from database import clear_all_invoices, create_database
from ocr_engine import ocr_is_available
from report_generator import render_report_page
from risk_center import render_risk_centre
from sample_data import load_sample_data
from theme import (
    inject_enterprise_theme,
    render_app_hero,
    render_footer,
    render_sidebar_brand,
)
from upload import render_upload_page


st.set_page_config(
    page_title="FinTech AI",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded",
)

create_database()
inject_enterprise_theme()
render_sidebar_brand("v3.6")

st.sidebar.markdown("### Workspace")

page = st.sidebar.radio(
    "Select module",
    [
        "📤 AI Invoice Capture",
        "📊 Dashboard",
        "🤖 Financial Advisor",
        "💬 Ask FinTech AI",
        "🚨 Fraud & Risk Centre",
        "📄 Executive Report",
        "🧾 Invoice Records",
        "🧠 Vendor Memory",
        "🧪 Demo Data",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()

if ocr_is_available():
    st.sidebar.success("OCR engine ready")
else:
    st.sidebar.warning("OCR not installed")

st.sidebar.success("AI intelligence engine ready")
st.sidebar.caption(
    "Python 3.11 · Local SQLite · Local OCR · Explainable AI"
)

render_app_hero()

if page == "📊 Dashboard":
    render_dashboard()

elif page == "🤖 Financial Advisor":
    render_financial_advisor()

elif page == "💬 Ask FinTech AI":
    render_ask_fintech_ai()

elif page == "🚨 Fraud & Risk Centre":
    render_risk_centre()

elif page == "📄 Executive Report":
    render_report_page()

elif page == "📤 AI Invoice Capture":
    render_upload_page()

elif page == "🧾 Invoice Records":
    render_invoice_records()

elif page == "🧠 Vendor Memory":
    render_vendor_memory()

else:
    st.header("🧪 Synthetic Demo Data")
    st.caption(
        "Populate the prototype with anonymous sample invoices for a complete "
        "dashboard, advisor, risk, chat and report demonstration."
    )

    st.warning(
        "The sample records are synthetic and must not be presented as real "
        "business data."
    )

    if st.button(
        "Load synthetic demo invoices",
        type="primary",
        use_container_width=True,
    ):
        added, skipped = load_sample_data()

        if added:
            st.success(f"Added {added} synthetic invoice records.")

        if skipped:
            st.info(
                f"Skipped {skipped} record(s) because they already existed."
            )

        st.info(
            "Open Dashboard, Financial Advisor, Risk Centre, Ask FinTech AI "
            "or Executive Report to explore the results."
        )

    st.divider()

    confirm_clear = st.checkbox(
        "I understand that this removes every invoice record "
        "from the local database."
    )

    clear_memory = st.checkbox(
        "Also clear adaptive vendor memory."
    )

    if st.button(
        "Clear prototype records",
        disabled=not confirm_clear,
        use_container_width=True,
    ):
        clear_all_invoices(
            clear_vendor_memory=clear_memory
        )
        st.success("Selected prototype data was removed.")

render_footer()
