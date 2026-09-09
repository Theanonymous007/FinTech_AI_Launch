from __future__ import annotations

from html import escape
from textwrap import dedent

import streamlit as st



def _render_html(markup: str) -> None:
    """Render custom markup without Markdown interpreting it as source code."""
    cleaned = " ".join(
        line.strip()
        for line in dedent(markup).splitlines()
        if line.strip()
    )
    if not cleaned:
        return
    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(cleaned)
    else:
        st.markdown(cleaned, unsafe_allow_html=True)


def inject_enterprise_theme(mode: str = "Dark") -> None:
    """Apply the V3 product design system.

    The app switches the complete visual system, not only the page canvas.
    Light mode uses dark text on light surfaces; dark mode uses light text on
    dark surfaces across cards, forms, tables, charts and navigation.
    """
    is_light = (mode or "Dark").casefold() == "light"
    palette = {
        # Canvas and navigation
        "page_bg": "#F4F7F8" if is_light else "#07141D",
        "page_bg_2": "#EAF1F3" if is_light else "#091B26",
        "sidebar": "#FFFFFF" if is_light else "#081823",
        "sidebar_text": "#172B35" if is_light else "#F1F8FA",
        "sidebar_muted": "#667A84" if is_light else "#9CB0B9",
        "page_text": "#10242E" if is_light else "#F5FBFC",
        "page_muted": "#60747E" if is_light else "#A9BDC6",

        # Elevated surfaces switch with the selected mode. This is the key V3.3
        # change: light mode always uses dark text, dark mode always uses light text.
        "surface": "#FFFFFF" if is_light else "#10242E",
        "surface_alt": "#F0F5F6" if is_light else "#132C38",
        "surface_hover": "#F7FAFB" if is_light else "#17313D",
        "card_text": "#10242E" if is_light else "#F3FAFC",
        "card_muted": "#61757F" if is_light else "#A9BDC6",
        "meta_text": "#7A8D96" if is_light else "#8FA6B0",
        "input_bg": "#FFFFFF" if is_light else "#0D202B",
        "upload_bg": "#F8FBFC" if is_light else "#0D202B",
        "secondary_button_bg": "#FFFFFF" if is_light else "#102A36",
        "secondary_button_text": "#0C6570" if is_light else "#EAF8FA",
        "plot_bg": "#FFFFFF" if is_light else "#10242E",
        "placeholder": "#8799A1" if is_light else "#78909B",
        "line_soft": "rgba(57,92,106,.12)" if is_light else "rgba(155,199,208,.16)",
        "border": "rgba(71,102,116,.17)" if is_light else "rgba(153,202,211,.22)",
        "shadow": "0 18px 50px rgba(35,72,84,.09)" if is_light else "0 20px 55px rgba(0,0,0,.24)",
        "hover_shadow": "0 24px 58px rgba(10,40,50,.14)" if is_light else "0 24px 58px rgba(0,0,0,.30)",
        "header": "rgba(244,247,248,.88)" if is_light else "rgba(7,20,29,.88)",
        "color_scheme": "light" if is_light else "dark",

        # Tone surfaces and readable tone text for both modes
        "success_soft": "#E8F7F1" if is_light else "rgba(35,154,114,.18)",
        "warning_soft": "#FFF5E3" if is_light else "rgba(200,137,39,.18)",
        "danger_soft": "#FFF0F0" if is_light else "rgba(215,84,84,.18)",
        "info_soft": "#EBF6F8" if is_light else "rgba(41,200,216,.15)",
        "neutral_soft": "#EFF4F5" if is_light else "rgba(148,163,184,.12)",
        "success_text": "#176D52" if is_light else "#7DE0B8",
        "warning_text": "#98610E" if is_light else "#F4C979",
        "danger_text": "#AA3939" if is_light else "#FF9C9C",
        "info_text": "#176E7E" if is_light else "#79E3EC",
        "neutral_text": "#5D7079" if is_light else "#B6C8CF",
        "accent_icon_bg": "#E5F8FA" if is_light else "rgba(41,200,216,.16)",
        "accent_icon_text": "#0B6571" if is_light else "#75E5EE",
    }

    css = r"""
<style>
:root {
    --page-bg: __PAGE_BG__;
    --page-bg-2: __PAGE_BG_2__;
    --sidebar-bg: __SIDEBAR__;
    --sidebar-text: __SIDEBAR_TEXT__;
    --sidebar-muted: __SIDEBAR_MUTED__;
    --page-text: __PAGE_TEXT__;
    --page-muted: __PAGE_MUTED__;
    --surface: __SURFACE__;
    --surface-alt: __SURFACE_ALT__;
    --card-text: __CARD_TEXT__;
    --card-muted: __CARD_MUTED__;
    --border: __BORDER__;
    --shadow: __SHADOW__;
    --header-bg: __HEADER__;
    --surface-hover: __SURFACE_HOVER__;
    --meta-text: __META_TEXT__;
    --input-bg: __INPUT_BG__;
    --upload-bg: __UPLOAD_BG__;
    --secondary-button-bg: __SECONDARY_BUTTON_BG__;
    --secondary-button-text: __SECONDARY_BUTTON_TEXT__;
    --plot-bg: __PLOT_BG__;
    --placeholder: __PLACEHOLDER__;
    --line-soft: __LINE_SOFT__;
    --hover-shadow: __HOVER_SHADOW__;
    --mode-color-scheme: __COLOR_SCHEME__;
    /* Streamlit native widgets also read these theme variables. */
    --primary-color: #29C8D8;
    --background-color: __PAGE_BG__;
    --secondary-background-color: __SURFACE__;
    --text-color: __PAGE_TEXT__;
    --accent: #29C8D8;
    --accent-strong: #12AFC0;
    --accent-soft: rgba(41, 200, 216, 0.12);
    --success: #239A72;
    --success-soft: __SUCCESS_SOFT__;
    --warning: #C88927;
    --warning-soft: __WARNING_SOFT__;
    --danger: #D75454;
    --danger-soft: __DANGER_SOFT__;
    --info: #397C91;
    --info-soft: __INFO_SOFT__;
    --neutral-soft: __NEUTRAL_SOFT__;
    --success-text: __SUCCESS_TEXT__;
    --warning-text: __WARNING_TEXT__;
    --danger-text: __DANGER_TEXT__;
    --info-text: __INFO_TEXT__;
    --neutral-text: __NEUTRAL_TEXT__;
    --accent-icon-bg: __ACCENT_ICON_BG__;
    --accent-icon-text: __ACCENT_ICON_TEXT__;
    --radius-sm: 10px;
    --radius: 16px;
    --radius-lg: 22px;
    --ease: cubic-bezier(.2,.8,.2,1);
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
html { scroll-behavior: smooth; color-scheme: var(--mode-color-scheme); }

.stApp {
    background:
        radial-gradient(circle at 72% -10%, rgba(41,200,216,.08), transparent 27%),
        linear-gradient(180deg, var(--page-bg) 0%, var(--page-bg-2) 100%);
    color: var(--page-text);
    color-scheme: var(--mode-color-scheme);
}

[data-testid="stHeader"] {
    background: var(--header-bg);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid var(--border);
}

.block-container,
[data-testid="stMainBlockContainer"] {
    max-width: 1280px;
    padding-top: 1.8rem;
    padding-bottom: 5rem;
    animation: fta-enter 220ms var(--ease) both;
}

h1, h2, h3, h4, h5, h6 { color: var(--page-text); letter-spacing: -0.025em; }
p, .stCaption, [data-testid="stCaptionContainer"] { color: var(--page-muted) !important; }
[data-testid="stMarkdownContainer"],
[data-testid="stText"],
[data-testid="stWidgetLabel"],
.stMarkdown { color: var(--page-text); }
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] b { color: var(--page-text); }
label { color: var(--page-text) !important; font-weight: 650 !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border);
    box-shadow: 12px 0 38px rgba(0,0,0,.08);
}
[data-testid="stSidebar"] > div:first-child { padding-top: .9rem; }

.fta-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 3px 14px;
}
.fta-logo {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 11px;
    background: var(--accent);
    color: #062029;
    font-weight: 950;
    box-shadow: 0 10px 22px rgba(41,200,216,.18);
}
.fta-brand-name { color: var(--sidebar-text); font-size: .98rem; font-weight: 850; }
.fta-brand-meta { margin-top: 1px; color: var(--sidebar-muted); font-size: .68rem; }

.nav-label {
    margin: 18px 3px 7px;
    color: var(--sidebar-muted);
    font-size: .61rem;
    font-weight: 850;
    letter-spacing: .14em;
    text-transform: uppercase;
}
.sidebar-divider { height: 1px; margin: 16px 0; background: var(--border); }
.sidebar-note {
    padding: 11px 12px;
    border: 1px solid var(--border);
    border-radius: 13px;
    color: var(--sidebar-muted);
    background: rgba(41,200,216,.035);
    font-size: .68rem;
    line-height: 1.5;
}
.sidebar-note strong { display: block; color: var(--sidebar-text); font-size: .78rem; margin-bottom: 2px; }

[data-testid="stSidebar"] .stButton { margin-bottom: 3px; }
[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start;
    min-height: 40px;
    width: 100%;
    padding: 7px 10px;
    border: 1px solid transparent;
    border-radius: 11px;
    color: var(--sidebar-text);
    background: transparent;
    box-shadow: none;
    font-size: .78rem;
    font-weight: 680;
}
[data-testid="stSidebar"] .stButton > button:hover {
    transform: none;
    border-color: rgba(41,200,216,.16);
    background: rgba(41,200,216,.08);
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    color: #062029;
    background: var(--accent);
    border-color: transparent;
    font-weight: 820;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover { background: #42D4E2; }

/* Page header */
.page-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    padding: 4px 0 18px;
    margin-bottom: 23px;
}
.page-title {
    color: var(--page-text);
    font-size: clamp(2.05rem, 3.5vw, 3rem);
    font-weight: 820;
    line-height: 1.04;
    letter-spacing: -.05em;
}
.page-subtitle {
    max-width: 760px;
    margin-top: 9px;
    color: var(--page-muted);
    font-size: .96rem;
    line-height: 1.6;
}
.page-kicker { display: none; }
.page-chip { display: none; }

/* Section hierarchy */
.fta-section-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px;
    margin: 38px 0 15px;
}
.fta-section-head-compact { margin-top: 25px; margin-bottom: 11px; }
.fta-section-eyebrow {
    margin-bottom: 5px;
    color: var(--accent);
    font-size: .63rem;
    font-weight: 850;
    letter-spacing: .13em;
    text-transform: uppercase;
}
.fta-section-title {
    color: var(--page-text);
    font-size: 1.22rem;
    font-weight: 790;
    letter-spacing: -.025em;
}
.fta-section-subtitle {
    max-width: 760px;
    margin-top: 4px;
    color: var(--page-muted);
    font-size: .82rem;
    line-height: 1.55;
}
.fta-section-head-compact .fta-section-title { font-size: 1.08rem; }
.fta-section-head-compact .fta-section-subtitle { font-size: .77rem; }

/* Custom cards */
.fta-kpi-card,
.fta-insight-card,
.fta-priority-card,
.fta-todo,
.fta-alert-card,
.fta-definition-item,
.fta-empty-state,
.fta-confidence-list,
.fta-stat-strip {
    color: var(--card-text);
    background: var(--surface);
    border: 1px solid var(--line-soft);
    box-shadow: var(--shadow);
}

.fta-kpi-card {
    min-height: 145px;
    padding: 20px 20px 18px;
    border-radius: var(--radius-lg);
    transition: transform 170ms var(--ease), box-shadow 170ms var(--ease);
}
.fta-kpi-card:hover { transform: translateY(-2px); box-shadow: var(--hover-shadow); }
.fta-kpi-topline { display: flex; align-items: center; gap: 9px; }
.fta-kpi-icon {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    color: var(--accent-icon-text);
    background: var(--accent-icon-bg);
    font-size: .72rem;
    font-weight: 900;
}
.fta-kpi-label { color: var(--card-muted); font-size: .73rem; font-weight: 760; }
.fta-kpi-value {
    margin-top: 18px;
    color: var(--card-text);
    font-size: clamp(1.7rem, 2.8vw, 2.2rem);
    font-weight: 850;
    letter-spacing: -.05em;
}
.fta-kpi-context { margin-top: 7px; color: var(--card-muted); font-size: .7rem; line-height: 1.45; }
.fta-kpi-success .fta-kpi-icon { color: #147857; background: var(--success-soft); }
.fta-kpi-warning .fta-kpi-icon { color: #A26811; background: var(--warning-soft); }
.fta-kpi-danger .fta-kpi-icon { color: #B63F3F; background: var(--danger-soft); }
.fta-kpi-info .fta-kpi-icon { color: #177383; background: var(--info-soft); }

.fta-stat-strip {
    display: grid;
    grid-template-columns: repeat(4,minmax(0,1fr));
    overflow: hidden;
    border-radius: var(--radius);
    box-shadow: none;
}
.fta-stat-item { padding: 14px 16px; border-right: 1px solid var(--line-soft); }
.fta-stat-item:last-child { border-right: 0; }
.fta-stat-label { color: var(--card-muted); font-size: .66rem; font-weight: 760; }
.fta-stat-value { margin-top: 4px; color: var(--card-text); font-size: 1.04rem; font-weight: 810; }
.fta-stat-context { margin-top: 2px; color: var(--meta-text); font-size: .63rem; }

.fta-insight-card {
    padding: 18px 19px;
    border-radius: var(--radius);
    box-shadow: none;
    border-left: 4px solid var(--accent);
}
.fta-insight-eyebrow { color: var(--info-text); font-size: .62rem; font-weight: 850; letter-spacing: .08em; text-transform: uppercase; }
.fta-insight-title { margin-top: 7px; color: var(--card-text); font-size: .98rem; font-weight: 810; }
.fta-insight-body { margin-top: 6px; color: var(--card-muted); font-size: .76rem; line-height: 1.55; }
.fta-insight-meta { margin-top: 10px; color: var(--meta-text); font-size: .65rem; }
.fta-insight-success { border-left-color: var(--success); }
.fta-insight-warning { border-left-color: var(--warning); }
.fta-insight-danger { border-left-color: var(--danger); }
.fta-insight-neutral { border-left-color: #9AABB2; }

.fta-priority-card {
    padding: 18px 19px;
    border-radius: var(--radius);
    box-shadow: none;
}
.fta-priority-topline { margin-bottom: 8px; }
.fta-priority-title { color: var(--card-text); font-size: .98rem; font-weight: 810; }
.fta-priority-row { display: grid; grid-template-columns: 56px 1fr; gap: 8px; margin-top: 10px; }
.fta-priority-row span { color: var(--meta-text); font-size: .64rem; font-weight: 800; text-transform: uppercase; }
.fta-priority-row p { margin: 0; color: var(--card-muted); font-size: .74rem; line-height: 1.48; }
.fta-priority-amount { margin-top: 11px; color: var(--card-muted); font-size: .67rem; }

.fta-todo {
    display: flex;
    gap: 14px;
    padding: 16px 17px;
    margin-bottom: 10px;
    border-radius: 15px;
    box-shadow: none;
}
.fta-todo-marker { width: 18px; height: 18px; flex: 0 0 18px; margin-top: 2px; border: 2px solid var(--meta-text); border-radius: 50%; }
.fta-todo-copy { min-width: 0; flex: 1; }
.fta-todo-topline { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.fta-todo-title { margin-top: 6px; color: var(--card-text); font-size: .9rem; font-weight: 800; }
.fta-todo-detail { margin-top: 4px; color: var(--card-muted); font-size: .72rem; line-height: 1.48; }
.fta-todo-amount { color: var(--card-muted); font-size: .68rem; font-weight: 760; }
.fta-todo-success .fta-todo-marker { border-color: var(--success); }
.fta-todo-warning .fta-todo-marker { border-color: var(--warning); }
.fta-todo-danger .fta-todo-marker { border-color: var(--danger); }
.fta-todo-info .fta-todo-marker { border-color: var(--accent-strong); }

.fta-alert-card {
    padding: 18px 19px;
    margin-bottom: 12px;
    border-radius: var(--radius);
    box-shadow: none;
}
.fta-alert-head { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.fta-alert-level { color: var(--meta-text); font-size: .62rem; font-weight: 850; letter-spacing: .08em; text-transform: uppercase; }
.fta-alert-title { margin-top: 5px; color: var(--card-text); font-size: 1rem; font-weight: 820; }
.fta-alert-subtitle { margin-top: 2px; color: var(--card-muted); font-size: .68rem; }
.fta-alert-amount { color: var(--card-text); font-size: 1rem; font-weight: 830; }
.fta-alert-reason { margin-top: 13px; color: var(--card-muted); font-size: .75rem; line-height: 1.5; }
.fta-alert-meta { margin-top: 9px; color: var(--meta-text); font-size: .64rem; }
.fta-alert-danger { border-left: 4px solid var(--danger); }
.fta-alert-warning { border-left: 4px solid var(--warning); }
.fta-alert-info { border-left: 4px solid var(--accent-strong); }

.fta-badge {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: .61rem;
    font-weight: 820;
}
.fta-badge-success { color: var(--success-text); background: var(--success-soft); }
.fta-badge-warning { color: var(--warning-text); background: var(--warning-soft); }
.fta-badge-danger { color: var(--danger-text); background: var(--danger-soft); }
.fta-badge-info { color: var(--info-text); background: var(--info-soft); }
.fta-badge-neutral { color: var(--neutral-text); background: var(--neutral-soft); }

/* Banners and empty states */
.fta-banner {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 13px 15px;
    margin: 13px 0;
    border-radius: 14px;
    border: 1px solid var(--line-soft);
    color: var(--card-text);
    background: var(--surface);
}
.fta-banner-icon {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    border-radius: 50%;
    color: var(--info-text);
    background: var(--info-soft);
    font-weight: 900;
}
.fta-banner-title { color: var(--card-text); font-size: .78rem; font-weight: 800; }
.fta-banner-message { margin-top: 2px; color: var(--card-muted); font-size: .69rem; line-height: 1.5; }
.fta-banner-success .fta-banner-icon { color: var(--success-text); background: var(--success-soft); }
.fta-banner-warning .fta-banner-icon { color: var(--warning-text); background: var(--warning-soft); }
.fta-banner-danger .fta-banner-icon { color: var(--danger-text); background: var(--danger-soft); }
.fta-banner-neutral .fta-banner-icon { color: var(--neutral-text); background: var(--neutral-soft); }

.fta-empty-state {
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 24px;
    border-radius: var(--radius-lg);
}
.fta-empty-icon {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border-radius: 15px;
    color: var(--accent-icon-text);
    background: var(--accent-icon-bg);
    font-size: 1.25rem;
    font-weight: 850;
}
.fta-empty-title { color: var(--card-text); font-size: 1rem; font-weight: 820; }
.fta-empty-message { max-width: 680px; margin-top: 5px; color: var(--card-muted); font-size: .76rem; line-height: 1.55; }

/* Stepper */
.fta-stepper {
    display: grid;
    grid-template-columns: repeat(3,minmax(0,1fr));
    gap: 10px;
    margin: 5px 0 24px;
}
.fta-step {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid var(--border);
    color: var(--page-muted);
    background: rgba(41,200,216,.035);
}
.fta-step-marker { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 50%; border: 1px solid var(--border); font-size: .67rem; font-weight: 850; }
.fta-step-label { font-size: .71rem; font-weight: 740; }
.fta-step-active { border-color: rgba(41,200,216,.48); color: var(--page-text); background: rgba(41,200,216,.10); }
.fta-step-active .fta-step-marker { color: #062029; background: var(--accent); border-color: transparent; }
.fta-step-complete .fta-step-marker { color: white; background: var(--success); border-color: transparent; }

/* Definition / confidence */
.fta-definition-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 9px; margin: 10px 0; }
.fta-definition-item { padding: 12px 13px; border-radius: 12px; box-shadow: none; }
.fta-definition-item span { display: block; color: var(--meta-text); font-size: .61rem; font-weight: 820; letter-spacing: .06em; text-transform: uppercase; }
.fta-definition-item strong { display: block; overflow: hidden; margin-top: 4px; color: var(--card-text); font-size: .77rem; text-overflow: ellipsis; white-space: nowrap; }

.fta-confidence-list { overflow: hidden; border-radius: var(--radius); box-shadow: none; }
.fta-confidence-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 11px 14px; border-bottom: 1px solid rgba(57,92,106,.10); }
.fta-confidence-row:last-child { border-bottom: 0; }
.fta-confidence-row strong { display: block; color: var(--card-text); font-size: .72rem; }
.fta-confidence-row span { display: block; margin-top: 2px; color: var(--card-muted); font-size: .65rem; }
.fta-confidence-state { margin: 0 !important; padding: 4px 8px; border-radius: 999px; font-weight: 780; white-space: nowrap; }
.fta-confidence-ready { color: var(--success-text) !important; background: var(--success-soft); }
.fta-confidence-review { color: var(--warning-text) !important; background: var(--warning-soft); }
.fta-confidence-check-carefully { color: var(--danger-text) !important; background: var(--danger-soft); }

/* Native Streamlit cards/widgets */
[data-testid="stMetric"] {
    padding: 16px;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius);
    color: var(--card-text);
    background: var(--surface);
    box-shadow: none;
}
[data-testid="stMetricLabel"] { color: var(--card-muted); }
[data-testid="stMetricValue"] { color: var(--card-text); }

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    min-height: 44px;
    border: 1px solid rgba(41,200,216,.33);
    border-radius: 12px;
    color: var(--secondary-button-text);
    background: var(--secondary-button-bg);
    box-shadow: none;
    font-weight: 770;
    transition: transform 150ms var(--ease), border-color 150ms var(--ease), box-shadow 150ms var(--ease);
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    border-color: var(--accent-strong);
    box-shadow: 0 10px 24px rgba(7,54,64,.10);
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stFormSubmitButton > button {
    color: #062029;
    border-color: transparent;
    background: var(--accent);
    font-weight: 850;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover { background: #42D4E2; }
.stButton > button p, .stDownloadButton > button p, .stFormSubmitButton > button p { color: inherit !important; font-weight: inherit !important; }

[data-baseweb="input"] > div,
[data-baseweb="textarea"],
[data-baseweb="select"] > div,
[data-testid="stFileUploaderDropzone"] {
    color: var(--card-text) !important;
    border-color: rgba(57,92,106,.18) !important;
    border-radius: 13px !important;
    background: var(--input-bg) !important;
}
input, textarea { color: var(--card-text) !important; }
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
[data-testid="stDateInput"] input,
[data-testid="stNumberInput"] input {
    color: var(--card-text) !important;
    -webkit-text-fill-color: var(--card-text) !important;
    opacity: 1 !important;
}
input::placeholder, textarea::placeholder { color: var(--placeholder) !important; -webkit-text-fill-color: var(--placeholder) !important; }
[data-testid="stFileUploaderFile"],
[data-testid="stFileUploaderFile"] * {
    color: var(--card-text) !important;
}
[data-testid="stFileUploaderFile"] {
    border-color: rgba(57,92,106,.14) !important;
    background: var(--surface-alt) !important;
}
[data-testid="stFileUploaderDropzone"] {
    min-height: 170px;
    padding: 30px !important;
    border: 1.5px dashed rgba(41,200,216,.55) !important;
    background: var(--upload-bg) !important;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--card-text) !important; }

[data-testid="stDataFrame"], [data-testid="stTable"] {
    overflow: hidden;
    border: 1px solid rgba(57,92,106,.14);
    border-radius: var(--radius);
    background: var(--surface);
    box-shadow: none;
}
[data-testid="stPlotlyChart"] {
    overflow: hidden;
    padding: 8px;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius-lg);
    background: var(--plot-bg);
    box-shadow: var(--shadow);
}
[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 13px;
    background: var(--surface-alt);
}
[data-testid="stExpander"] summary { color: var(--page-text); }
[data-testid="stAlert"] { border-radius: 13px; }
[data-testid="stProgress"] > div > div { background: var(--accent); }

/* Theme-aware native widget text */
[data-baseweb="select"] *,
[data-baseweb="input"] *,
[data-baseweb="textarea"] *,
[data-baseweb="base-input"] *,
[data-testid="stDateInput"] *,
[data-testid="stNumberInput"] *,
[data-testid="stTextInput"] *,
[data-testid="stTextArea"] *,
[data-testid="stSelectbox"] *,
[data-testid="stMultiSelect"] *,
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label,
[data-testid="stToggle"] label {
    color: var(--card-text) !important;
    -webkit-text-fill-color: var(--card-text) !important;
}
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"] {
    color: var(--card-text) !important;
    background: var(--surface) !important;
}
[role="option"] { color: var(--card-text) !important; background: var(--surface) !important; }
[role="option"]:hover, [aria-selected="true"][role="option"] { background: var(--surface-hover) !important; }
[data-testid="stTabs"] button { color: var(--page-muted) !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: var(--page-text) !important; }
[data-baseweb="select"] svg,
[data-testid="stDateInput"] svg,
[data-testid="stNumberInput"] svg,
[data-testid="stTextInput"] svg,
[data-testid="stFileUploader"] svg {
    color: var(--card-text) !important;
    fill: var(--card-text) !important;
}
[data-testid="stDataFrame"], [data-testid="stDataFrame"] * { color-scheme: var(--mode-color-scheme); }
[data-testid="stCode"], code, pre { color: var(--card-text); background: var(--surface-alt); }

/* Chat */
[data-testid="stChatMessage"] {
    max-width: 900px;
    padding: 17px 18px;
    margin: 10px 0;
    border: 1px solid var(--line-soft);
    border-radius: 18px;
    color: var(--card-text);
    background: var(--surface);
    box-shadow: none;
    animation: fta-message 180ms var(--ease) both;
}
[data-testid="stChatMessage"] p { color: var(--card-text); }
[data-testid="stChatInput"] {
    border: 1px solid rgba(41,200,216,.40);
    border-radius: 18px;
    background: var(--surface);
    box-shadow: 0 12px 32px rgba(0,0,0,.10);
}

.fta-footer {
    margin-top: 46px;
    padding: 15px 0 4px;
    border-top: 1px solid var(--border);
    color: var(--page-muted);
    font-size: .65rem;
    text-align: center;
}

@keyframes fta-enter { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:translateY(0); } }
@keyframes fta-message { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }

@media (max-width: 1050px) {
    .fta-stat-strip { grid-template-columns: repeat(2,minmax(0,1fr)); }
    .fta-stat-item:nth-child(2) { border-right: 0; }
    .fta-stat-item:nth-child(-n+2) { border-bottom: 1px solid var(--line-soft); }
}
@media (max-width: 760px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1.2rem; }
    .page-title { font-size: 2rem; }
    .page-head, .fta-section-head { flex-direction: column; align-items: flex-start; }
    .fta-stepper { grid-template-columns: 1fr; }
    .fta-priority-row { grid-template-columns: 1fr; gap: 2px; }
    .fta-alert-head { flex-direction: column; gap: 8px; }
    [data-testid="stFileUploaderDropzone"] { min-height: 140px; padding: 20px !important; }
}
@media (max-width: 500px) {
    .fta-stat-strip, .fta-definition-grid { grid-template-columns: 1fr; }
    .fta-stat-item { border-right: 0; border-bottom: 1px solid var(--line-soft); }
    .fta-stat-item:last-child { border-bottom: 0; }
    .fta-kpi-card { min-height: 128px; }
}
@media (prefers-reduced-motion: reduce) {
    *,*::before,*::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; scroll-behavior:auto !important; }
}

#MainMenu, footer { visibility: hidden; }
</style>
"""
    replacements = {
        "__PAGE_BG__": palette["page_bg"],
        "__PAGE_BG_2__": palette["page_bg_2"],
        "__SIDEBAR__": palette["sidebar"],
        "__SIDEBAR_TEXT__": palette["sidebar_text"],
        "__SIDEBAR_MUTED__": palette["sidebar_muted"],
        "__PAGE_TEXT__": palette["page_text"],
        "__PAGE_MUTED__": palette["page_muted"],
        "__SURFACE__": palette["surface"],
        "__SURFACE_ALT__": palette["surface_alt"],
        "__SURFACE_HOVER__": palette["surface_hover"],
        "__CARD_TEXT__": palette["card_text"],
        "__CARD_MUTED__": palette["card_muted"],
        "__META_TEXT__": palette["meta_text"],
        "__INPUT_BG__": palette["input_bg"],
        "__UPLOAD_BG__": palette["upload_bg"],
        "__SECONDARY_BUTTON_BG__": palette["secondary_button_bg"],
        "__SECONDARY_BUTTON_TEXT__": palette["secondary_button_text"],
        "__PLOT_BG__": palette["plot_bg"],
        "__PLACEHOLDER__": palette["placeholder"],
        "__LINE_SOFT__": palette["line_soft"],
        "__BORDER__": palette["border"],
        "__SHADOW__": palette["shadow"],
        "__HOVER_SHADOW__": palette["hover_shadow"],
        "__HEADER__": palette["header"],
        "__COLOR_SCHEME__": palette["color_scheme"],
        "__SUCCESS_SOFT__": palette["success_soft"],
        "__WARNING_SOFT__": palette["warning_soft"],
        "__DANGER_SOFT__": palette["danger_soft"],
        "__INFO_SOFT__": palette["info_soft"],
        "__NEUTRAL_SOFT__": palette["neutral_soft"],
        "__SUCCESS_TEXT__": palette["success_text"],
        "__WARNING_TEXT__": palette["warning_text"],
        "__DANGER_TEXT__": palette["danger_text"],
        "__INFO_TEXT__": palette["info_text"],
        "__NEUTRAL_TEXT__": palette["neutral_text"],
        "__ACCENT_ICON_BG__": palette["accent_icon_bg"],
        "__ACCENT_ICON_TEXT__": palette["accent_icon_text"],
    }
    for token, value in replacements.items():
        css = css.replace(token, value)
    _render_html(css)


def render_sidebar_brand(version: str = "UX V3.3") -> None:
    with st.sidebar:
        _render_html(
            f"""
            <div class="fta-brand">
                <div class="fta-logo">F</div>
                <div>
                    <div class="fta-brand-name">FinTech AI</div>
                    <div class="fta-brand-meta">Simple financial intelligence · {escape(version)}</div>
                </div>
            </div>
            """
        )


def render_page_header(
    title: str,
    subtitle: str,
    page: str = "",
    *,
    kicker: str = "",
    chip: str = "",
) -> None:
    _render_html(
        f"""
        <section class="page-head">
            <div>
                <div class="page-title">{escape(title)}</div>
                <div class="page-subtitle">{escape(subtitle)}</div>
            </div>
        </section>
        """
    )


def render_app_hero() -> None:
    render_page_header(
        "Financial overview",
        "Understand your verified spending, payments and next actions at a glance.",
    )


def render_footer() -> None:
    _render_html(
        """
        <div class="fta-footer">
            FinTech AI · TRL Level 2 concept demo · Human verification remains required · Use synthetic or non-confidential data
        </div>
        """
    )
