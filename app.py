from __future__ import annotations

import streamlit as st

from advisor import render_financial_advisor
from ai_engine import analyse_finances
from ask_ai import render_ask_fintech_ai
from dashboard import (
    render_dashboard,
    render_invoice_records,
    render_vendor_intelligence,
    render_vendor_memory,
)
from database import clear_all_invoices, create_database
from ocr_engine import ocr_is_available
from report_generator import render_report_page
from risk_center import render_risk_centre
from sample_data import load_sample_data
from theme import inject_enterprise_theme, render_footer, render_page_header, render_sidebar_brand
from ui_components import navigate_to, render_empty_state, render_section_header, render_stat_strip, render_status_banner
from upload import render_upload_page


def _sidebar_html(markup: str) -> None:
    cleaned = " ".join(line.strip() for line in markup.splitlines() if line.strip())
    with st.sidebar:
        html_renderer = getattr(st, "html", None)
        if callable(html_renderer):
            html_renderer(cleaned)
        else:
            st.markdown(cleaned, unsafe_allow_html=True)


st.set_page_config(
    page_title="FinTech AI",
    page_icon="F",
    layout="wide",
    initial_sidebar_state="expanded",
)

create_database()
st.session_state.setdefault("ui_light_mode", False)
st.session_state.setdefault("active_page", "Overview")

pending_page = st.session_state.pop("pending_navigation", None)
if pending_page:
    st.session_state["active_page"] = pending_page

inject_enterprise_theme("Light" if st.session_state["ui_light_mode"] else "Dark")
render_sidebar_brand("UX V3.3")


PAGES = {
    "Overview": {
        "title": "Financial overview",
        "subtitle": "See your verified spending, open payments and next actions without digging through reports.",
        "route": "dashboard",
    },
    "Capture invoice": {
        "title": "Capture invoice",
        "subtitle": "Upload, verify and save an invoice in three simple steps.",
        "route": "capture",
    },
    "Invoice records": {
        "title": "Invoice records",
        "subtitle": "Find and review the verified invoices in your financial ledger.",
        "route": "records",
    },
    "Financial advisor": {
        "title": "Financial advisor",
        "subtitle": "Understand what needs attention and what to do next.",
        "route": "advisor",
    },
    "Ask FinTech AI": {
        "title": "Ask FinTech AI",
        "subtitle": "Ask simple questions about your verified spending, payments, vendors and forecast.",
        "route": "ask",
    },
    "Risk review": {
        "title": "Risk review",
        "subtitle": "Review unusual invoice patterns with clear reasons and human control.",
        "route": "risk",
    },
    "Vendors": {
        "title": "Vendors",
        "subtitle": "See who receives the most money and where supplier dependency may be growing.",
        "route": "vendor_intelligence",
    },
    "Vendor memory": {
        "title": "Vendor memory",
        "subtitle": "Review confirmed details remembered for recurring vendors.",
        "route": "vendor_memory",
    },
    "Executive report": {
        "title": "Create financial report",
        "subtitle": "Generate a clear management PDF from the current verified ledger.",
        "route": "report",
    },
    "Demo workspace": {
        "title": "Demo workspace",
        "subtitle": "Load or reset safe sample data for an end-to-end demonstration.",
        "route": "demo",
    },
}

NAV_GROUPS = [
    ("Home", [("Overview", "⌂")]),
    ("Invoices", [("Capture invoice", "＋"), ("Invoice records", "▤")]),
    ("Intelligence", [("Financial advisor", "✓"), ("Ask FinTech AI", "✦"), ("Risk review", "!")]),
    ("Vendors", [("Vendors", "◇"), ("Vendor memory", "◎")]),
    ("Reports", [("Executive report", "⇩")]),
    ("Demo", [("Demo workspace", "⚙")]),
]


if st.sidebar.button("＋  Upload invoice", type="primary", use_container_width=True, key="sidebar_primary_capture"):
    navigate_to("Capture invoice")

active_page = st.session_state.get("active_page", "Overview")
if active_page not in PAGES:
    active_page = "Overview"
    st.session_state["active_page"] = active_page

for group, items in NAV_GROUPS:
    _sidebar_html(f'<div class="nav-label">{group}</div>')
    for page_name, icon in items:
        if st.sidebar.button(
            f"{icon}  {page_name}",
            type="primary" if page_name == active_page else "secondary",
            use_container_width=True,
            key=f"nav_{page_name}",
        ):
            navigate_to(page_name)

try:
    sidebar_analysis = analyse_finances()
except Exception:
    sidebar_analysis = {"has_data": False, "summary": {}}

summary = sidebar_analysis.get("summary", {})
invoice_count = int(summary.get("invoice_count", 0) or 0)
total_spend = float(summary.get("total_spend", 0) or 0)

_sidebar_html('<div class="sidebar-divider"></div>')
_sidebar_html(
    f"""
    <div class="sidebar-note">
        <strong>{invoice_count:,} verified invoice{'s' if invoice_count != 1 else ''}</strong>
        ₹{total_spend:,.0f} recorded spend
    </div>
    """
)

st.sidebar.toggle("Light mode", key="ui_light_mode", help="Light mode uses dark text. Dark mode uses light text across cards, forms, tables and charts.")
ocr_label = "OCR ready" if ocr_is_available() else "OCR setup needed"
st.sidebar.caption(f"{ocr_label} · Local SQLite · TRL 2 demo")

meta = PAGES[active_page]
render_page_header(meta["title"], meta["subtitle"], active_page)

route = meta["route"]
if route == "dashboard":
    render_dashboard()
elif route == "capture":
    render_upload_page()
elif route == "records":
    render_invoice_records()
elif route == "advisor":
    render_financial_advisor()
elif route == "ask":
    render_ask_fintech_ai()
elif route == "risk":
    render_risk_centre()
elif route == "vendor_intelligence":
    render_vendor_intelligence()
elif route == "vendor_memory":
    render_vendor_memory()
elif route == "report":
    render_report_page()
else:
    render_status_banner(
        "Use safe demonstration data",
        "The sample workspace contains anonymous records for testing. Do not use confidential documents in a public demo.",
        tone="info",
    )
    render_stat_strip(
        [
            ("Invoices", f"{invoice_count:,}", "Verified records"),
            ("Recorded spend", f"₹{total_spend:,.0f}", "Current workspace"),
            ("OCR", "Ready" if ocr_is_available() else "Setup needed", "Invoice reading"),
            ("Storage", "Local", "SQLite prototype"),
        ]
    )

    load_col, reset_col = st.columns(2, gap="large")
    with load_col:
        render_section_header(
            "Load sample data",
            "Add anonymous invoices across several months so every screen has realistic information.",
            compact=True,
        )
        if st.button("Load synthetic demo invoices", type="primary", use_container_width=True):
            added, skipped = load_sample_data()
            if added:
                render_status_banner(
                    "Sample workspace ready",
                    f"Added {added} invoices. Open the overview to explore the product.",
                    tone="success",
                )
            elif skipped:
                render_status_banner(
                    "Sample data already loaded",
                    "The current workspace already contains the demonstration invoices.",
                    tone="neutral",
                )
            if st.button("Open overview", use_container_width=True, key="demo_open_overview"):
                navigate_to("Overview")

    with reset_col:
        render_section_header(
            "Reset workspace",
            "Remove the current local invoice records before a new demonstration.",
            compact=True,
        )
        confirm_clear = st.checkbox("I understand that this removes all local invoice records")
        clear_memory = st.checkbox("Also clear vendor memory")
        if st.button("Clear local records", disabled=not confirm_clear, use_container_width=True):
            clear_all_invoices(clear_vendor_memory=clear_memory)
            render_status_banner("Workspace cleared", "The selected local records were removed.", tone="success")
            st.rerun()

render_footer()
