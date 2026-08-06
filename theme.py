from __future__ import annotations

from html import escape
import streamlit as st


def inject_enterprise_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #07111f;
            --surface: rgba(14, 27, 43, 0.86);
            --border: rgba(148, 163, 184, 0.18);
            --border-strong: rgba(34, 211, 238, 0.34);
            --text: #f8fafc;
            --muted: #94a3b8;
            --cyan: #22d3ee;
            --blue: #6366f1;
            --green: #10b981;
            --amber: #f59e0b;
            --red: #ef4444;
            --shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
        }

        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 4%, rgba(34, 211, 238, 0.11), transparent 26%),
                radial-gradient(circle at 82% 0%, rgba(99, 102, 241, 0.12), transparent 30%),
                linear-gradient(180deg, #07111f 0%, #091522 52%, #07111f 100%);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(7, 17, 31, 0.60);
            backdrop-filter: blur(18px);
            border-bottom: 1px solid rgba(148, 163, 184, 0.08);
        }

        [data-testid="stMainBlockContainer"],
        .block-container {
            max-width: 1500px;
            padding-top: 1.6rem;
            padding-bottom: 4rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10, 24, 40, 0.98), rgba(7, 17, 31, 0.99));
            border-right: 1px solid var(--border);
            box-shadow: 16px 0 48px rgba(0, 0, 0, 0.18);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        h1, h2, h3 {
            color: var(--text);
            letter-spacing: -0.02em;
        }

        h1 {
            font-weight: 800;
        }

        p, label, .stCaption {
            color: var(--muted);
        }

        a {
            color: var(--cyan);
        }

        .fta-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 26px 28px;
            margin: 0 0 24px 0;
            background: linear-gradient(135deg, rgba(15, 31, 51, 0.94), rgba(10, 24, 40, 0.88));
            box-shadow: var(--shadow);
        }

        .fta-hero::after {
            content: "";
            position: absolute;
            width: 280px;
            height: 280px;
            right: -90px;
            top: -120px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(34, 211, 238, 0.24), transparent 68%);
            pointer-events: none;
        }

        .fta-eyebrow {
            display: inline-flex;
            padding: 6px 10px;
            border: 1px solid rgba(34, 211, 238, 0.26);
            border-radius: 999px;
            color: #a5f3fc;
            background: rgba(34, 211, 238, 0.08);
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .fta-title {
            margin: 14px 0 6px;
            color: #ffffff;
            font-size: clamp(2rem, 3.2vw, 3.25rem);
            line-height: 1.04;
            font-weight: 850;
            letter-spacing: -0.045em;
        }

        .fta-title .accent {
            background: linear-gradient(90deg, #67e8f9, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .fta-subtitle {
            max-width: 900px;
            color: #aebed1;
            font-size: 0.98rem;
            line-height: 1.6;
        }

        .fta-brand {
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 14px;
            margin: 0 0 16px 0;
            background: linear-gradient(145deg, rgba(18, 37, 59, 0.95), rgba(10, 24, 40, 0.92));
        }

        .fta-brand-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .fta-logo {
            display: grid;
            place-items: center;
            width: 42px;
            height: 42px;
            flex: 0 0 42px;
            border-radius: 13px;
            color: #06111f;
            font-size: 1.2rem;
            font-weight: 900;
            background: linear-gradient(135deg, #67e8f9, #818cf8);
            box-shadow: 0 10px 28px rgba(34, 211, 238, 0.18);
        }

        .fta-brand-name {
            color: #ffffff;
            font-size: 1.02rem;
            font-weight: 800;
        }

        .fta-brand-meta {
            margin-top: 2px;
            color: #8496ab;
            font-size: 0.72rem;
        }

        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 6px;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            min-height: 43px;
            padding: 8px 10px;
            border: 1px solid transparent;
            border-radius: 12px;
            transition: 160ms ease;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(34, 211, 238, 0.065);
            border-color: rgba(34, 211, 238, 0.12);
            transform: translateX(2px);
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(90deg, rgba(34, 211, 238, 0.14), rgba(99, 102, 241, 0.10));
            border-color: rgba(34, 211, 238, 0.24);
            box-shadow: inset 3px 0 0 #22d3ee;
        }

        [data-testid="stMetric"] {
            min-height: 125px;
            padding: 18px;
            border: 1px solid var(--border);
            border-radius: 20px;
            background: linear-gradient(145deg, rgba(16, 31, 51, 0.90), rgba(11, 23, 39, 0.88));
            box-shadow: 0 16px 38px rgba(0, 0, 0, 0.18);
            transition: 160ms ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: var(--border-strong);
            box-shadow: 0 20px 46px rgba(0, 0, 0, 0.24);
        }

        [data-testid="stMetricLabel"] {
            color: #91a5bb;
            font-size: 0.78rem;
        }

        [data-testid="stMetricValue"] {
            color: #ffffff;
            font-size: 1.65rem;
            font-weight: 800;
        }

        [data-baseweb="tab-list"] {
            padding: 5px;
            gap: 5px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(11, 23, 39, 0.82);
        }

        [data-baseweb="tab"] {
            border-radius: 10px;
            color: #94a3b8;
            font-weight: 650;
        }

        [aria-selected="true"][data-baseweb="tab"] {
            color: #ecfeff;
            background: linear-gradient(90deg, rgba(34, 211, 238, 0.14), rgba(99, 102, 241, 0.12));
        }

        .stButton > button,
        .stDownloadButton > button {
            min-height: 42px;
            border: 1px solid rgba(34, 211, 238, 0.26);
            border-radius: 12px;
            color: #ecfeff;
            font-weight: 750;
            background: linear-gradient(135deg, rgba(34, 211, 238, 0.17), rgba(99, 102, 241, 0.20));
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.16);
            transition: 150ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.10);
        }

        .stButton > button[kind="primary"],
        .stFormSubmitButton > button {
            border: 0;
            color: #06111f;
            background: linear-gradient(90deg, #67e8f9, #818cf8);
            font-weight: 850;
        }

        [data-baseweb="input"] > div,
        [data-baseweb="textarea"],
        [data-baseweb="select"] > div,
        [data-testid="stFileUploaderDropzone"] {
            border-color: var(--border);
            border-radius: 13px;
            background: rgba(10, 24, 40, 0.72);
        }

        input, textarea {
            color: #f8fafc !important;
        }

        [data-testid="stAlert"] {
            border: 1px solid var(--border);
            border-radius: 14px;
            backdrop-filter: blur(10px);
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            overflow: hidden;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: rgba(10, 24, 40, 0.72);
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(10, 24, 40, 0.62);
        }

        [data-testid="stChatMessage"] {
            padding: 15px 16px;
            margin: 8px 0;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: rgba(14, 27, 43, 0.76);
        }

        [data-testid="stChatInput"] {
            border: 1px solid var(--border-strong);
            border-radius: 16px;
            background: rgba(10, 24, 40, 0.94);
        }

        [data-testid="stPlotlyChart"] {
            padding: 8px;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: rgba(10, 24, 40, 0.55);
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.14);
        }

        .fta-footer {
            margin-top: 34px;
            padding: 16px 0 4px;
            border-top: 1px solid var(--border);
            color: #71849a;
            font-size: 0.74rem;
            text-align: center;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .fta-hero {
                padding: 22px 20px;
            }
            .fta-title {
                font-size: 2rem;
            }
        }

        #MainMenu, footer {
            visibility: hidden;
        }
        /* Fix button-label visibility */
.stButton > button p,
.stDownloadButton > button p,
.stFormSubmitButton > button p {
    color: inherit !important;
    font-weight: 800 !important;
}

.stButton > button[kind="primary"] p,
.stFormSubmitButton > button p {
    color: #06111f !important;
}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand(version: str = "v3.6") -> None:
    st.sidebar.markdown(
        f"""
        <div class="fta-brand">
            <div class="fta-brand-row">
                <div class="fta-logo">F</div>
                <div>
                    <div class="fta-brand-name">FinTech AI</div>
                    <div class="fta-brand-meta">
                        Financial intelligence · {escape(version)}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_hero() -> None:
    st.markdown(
        """
        <section class="fta-hero">
            <span class="fta-eyebrow">AI-powered finance operations</span>
            <div class="fta-title">
                FinTech AI — <span class="accent">Financial Intelligence</span>
            </div>
            <div class="fta-subtitle">
                From verified invoice capture to explainable risk detection,
                vendor intelligence, expense forecasting, grounded financial
                guidance and management-ready reporting.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="fta-footer">
            FinTech AI prototype · Local OCR · Local SQLite · Explainable AI ·
            Human-verified financial decision support
        </div>
        """,
        unsafe_allow_html=True,
    )
