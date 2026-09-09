from __future__ import annotations

from html import escape
from textwrap import dedent
from typing import Any, Iterable

import plotly.graph_objects as go
import streamlit as st




def _render_html(markup: str) -> None:
    """Render custom UI markup as HTML instead of Markdown code.

    Streamlit Markdown treats indented multiline HTML as a code block in some
    versions. Normalising the markup and using st.html prevents raw <div>
    source from appearing in the interface.
    """
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


def _light_mode_enabled() -> bool:
    """Return the user-selected appearance mode without failing in tests."""
    try:
        return bool(st.session_state.get("ui_light_mode", False))
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


def navigate_to(page: str) -> None:
    """Queue a navigation change for app.py and rerun safely."""
    st.session_state["pending_navigation"] = page
    st.rerun()


# ---------------------------------------------------------------------------
# Shared visual helpers
# ---------------------------------------------------------------------------


def _normalise_tone(tone: str) -> str:
    return {
        "positive": "success",
        "success": "success",
        "info": "info",
        "accent": "info",
        "warning": "warning",
        "danger": "danger",
        "neutral": "neutral",
    }.get((tone or "neutral").casefold(), "neutral")


def render_section_header(
    title: str,
    subtitle: str | None = None,
    *,
    eyebrow: str | None = None,
    badge: str | None = None,
    compact: bool = False,
) -> None:
    eyebrow_html = (
        f'<div class="fta-section-eyebrow">{escape(eyebrow)}</div>'
        if eyebrow
        else ""
    )
    subtitle_html = (
        f'<div class="fta-section-subtitle">{escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    badge_html = (
        f'<span class="fta-badge fta-badge-neutral">{escape(badge)}</span>'
        if badge
        else ""
    )
    compact_class = " fta-section-head-compact" if compact else ""
    _render_html(
        f"""
        <section class="fta-section-head{compact_class}">
            <div>
                {eyebrow_html}
                <div class="fta-section-title">{escape(title)}</div>
                {subtitle_html}
            </div>
            {badge_html}
        </section>
        """
    )


def render_empty_state(
    title: str,
    message: str,
    *,
    icon: str = "○",
    action_label: str | None = None,
    action_page: str | None = None,
    key: str | None = None,
) -> None:
    _render_html(
        f"""
        <div class="fta-empty-state">
            <div class="fta-empty-icon" aria-hidden="true">{escape(icon)}</div>
            <div>
                <div class="fta-empty-title">{escape(title)}</div>
                <div class="fta-empty-message">{escape(message)}</div>
            </div>
        </div>
        """
    )
    if action_label and action_page:
        if st.button(
            action_label,
            type="primary",
            key=key or f"empty_state_{action_page}_{action_label}",
        ):
            navigate_to(action_page)


def render_banner(
    title: str,
    message: str,
    *,
    tone: str = "info",
    icon: str | None = None,
) -> None:
    resolved_tone = _normalise_tone(tone)
    default_icons = {
        "info": "i",
        "success": "✓",
        "warning": "!",
        "danger": "!",
        "neutral": "i",
    }
    resolved_icon = icon or default_icons[resolved_tone]
    _render_html(
        f"""
        <div class="fta-banner fta-banner-{resolved_tone}">
            <div class="fta-banner-icon" aria-hidden="true">{escape(resolved_icon)}</div>
            <div>
                <div class="fta-banner-title">{escape(title)}</div>
                <div class="fta-banner-message">{escape(message)}</div>
            </div>
        </div>
        """
    )


def render_status_banner(
    title: str,
    message: str,
    *,
    tone: str = "neutral",
    icon: str | None = None,
) -> None:
    render_banner(title, message, tone=tone, icon=icon)


def render_stepper(steps: list[str], current: int) -> None:
    if not steps:
        return
    current = max(1, min(len(steps), int(current)))
    items: list[str] = []
    for index, step in enumerate(steps, start=1):
        if index < current:
            state, marker = "complete", "✓"
        elif index == current:
            state, marker = "active", str(index)
        else:
            state, marker = "pending", str(index)
        items.append(
            f"""
            <div class="fta-step fta-step-{state}">
                <div class="fta-step-marker">{escape(marker)}</div>
                <div class="fta-step-label">{escape(step)}</div>
            </div>
            """
        )
    _render_html(
        '<div class="fta-stepper">' + "".join(items) + "</div>"
    )


def render_stat_strip(items: Iterable[tuple[str, str, str | None]]) -> None:
    cards: list[str] = []
    for label, value, context in items:
        context_html = (
            f'<div class="fta-stat-context">{escape(str(context))}</div>'
            if context
            else ""
        )
        cards.append(
            f"""
            <div class="fta-stat-item">
                <div class="fta-stat-label">{escape(str(label))}</div>
                <div class="fta-stat-value">{escape(str(value))}</div>
                {context_html}
            </div>
            """
        )
    _render_html(
        '<div class="fta-stat-strip">' + "".join(cards) + "</div>"
    )


def render_kpi_card(
    label: str,
    value: str,
    context: str = "",
    *,
    tone: str = "neutral",
    icon: str = "",
) -> None:
    resolved_tone = _normalise_tone(tone)
    icon_html = (
        f'<span class="fta-kpi-icon" aria-hidden="true">{escape(icon)}</span>'
        if icon
        else ""
    )
    _render_html(
        f"""
        <article class="fta-kpi-card fta-kpi-{resolved_tone}">
            <div class="fta-kpi-topline">
                {icon_html}<span class="fta-kpi-label">{escape(label)}</span>
            </div>
            <div class="fta-kpi-value">{escape(str(value))}</div>
            <div class="fta-kpi-context">{escape(context)}</div>
        </article>
        """
    )


def render_insight_card(
    title: str,
    body: str,
    *,
    eyebrow: str | None = None,
    label: str | None = None,
    tone: str = "accent",
    meta: str | None = None,
    footer: str | None = None,
) -> None:
    resolved_tone = {
        "positive": "success",
        "success": "success",
        "warning": "warning",
        "danger": "danger",
        "neutral": "neutral",
        "info": "accent",
        "accent": "accent",
    }.get((tone or "accent").casefold(), "accent")
    resolved_label = label or eyebrow or "Key insight"
    resolved_footer = footer or meta
    footer_html = (
        f'<div class="fta-insight-meta">{escape(resolved_footer)}</div>'
        if resolved_footer
        else ""
    )
    _render_html(
        f"""
        <article class="fta-insight-card fta-insight-{resolved_tone}">
            <div class="fta-insight-eyebrow">{escape(resolved_label)}</div>
            <div class="fta-insight-title">{escape(title)}</div>
            <div class="fta-insight-body">{escape(body)}</div>
            {footer_html}
        </article>
        """
    )


def render_priority_card(
    priority: str,
    title: str,
    evidence: str,
    action: str,
    amount: str = "",
) -> None:
    priority_key = (priority or "").casefold()
    if priority_key == "high":
        tone = "danger"
    elif priority_key == "medium":
        tone = "warning"
    elif priority_key in {"improvement", "data", "setup"}:
        tone = "info"
    else:
        tone = "neutral"
    amount_html = (
        f'<div class="fta-priority-amount">Amount in scope <strong>{escape(amount)}</strong></div>'
        if amount
        else ""
    )
    _render_html(
        f"""
        <article class="fta-priority-card fta-priority-{tone}">
            <div class="fta-priority-topline">
                <span class="fta-badge fta-badge-{tone}">{escape(priority)} priority</span>
            </div>
            <div class="fta-priority-title">{escape(title)}</div>
            <div class="fta-priority-row"><span>Why</span><p>{escape(evidence)}</p></div>
            <div class="fta-priority-row"><span>Do next</span><p>{escape(action)}</p></div>
            {amount_html}
        </article>
        """
    )


def render_todo_item(
    title: str,
    detail: str,
    *,
    priority: str = "Action",
    tone: str = "neutral",
    amount: str | None = None,
) -> None:
    resolved = _normalise_tone(tone)
    amount_html = (
        f'<span class="fta-todo-amount">{escape(amount)}</span>' if amount else ""
    )
    _render_html(
        f"""
        <article class="fta-todo fta-todo-{resolved}">
            <div class="fta-todo-marker" aria-hidden="true"></div>
            <div class="fta-todo-copy">
                <div class="fta-todo-topline">
                    <span class="fta-badge fta-badge-{resolved}">{escape(priority)}</span>
                    {amount_html}
                </div>
                <div class="fta-todo-title">{escape(title)}</div>
                <div class="fta-todo-detail">{escape(detail)}</div>
            </div>
        </article>
        """
    )


def render_alert_card(
    vendor: str,
    invoice_number: str,
    amount: str,
    level: str,
    reason: str,
    *,
    date_text: str = "",
    score: int | None = None,
) -> None:
    tone = "danger" if level == "High" else "warning" if level == "Medium" else "info"
    meta = " · ".join(
        part for part in [amount, date_text, f"Score {score}/100" if score is not None else ""] if part
    )
    _render_html(
        f"""
        <article class="fta-alert-card fta-alert-{tone}">
            <div class="fta-alert-head">
                <div>
                    <div class="fta-alert-level">{escape(level)} risk</div>
                    <div class="fta-alert-title">{escape(vendor)}</div>
                    <div class="fta-alert-subtitle">Invoice {escape(invoice_number)}</div>
                </div>
                <div class="fta-alert-amount">{escape(amount)}</div>
            </div>
            <div class="fta-alert-reason">{escape(reason)}</div>
            <div class="fta-alert-meta">{escape(meta)}</div>
        </article>
        """
    )


def render_definition_grid(items: Iterable[tuple[str, Any]]) -> None:
    cells: list[str] = []
    for label, value in items:
        cells.append(
            f"""
            <div class="fta-definition-item">
                <span>{escape(str(label))}</span>
                <strong>{escape(str(value))}</strong>
            </div>
            """
        )
    _render_html(
        '<div class="fta-definition-grid">' + "".join(cells) + "</div>"
    )


def render_confidence_summary(items: Iterable[tuple[str, str, str]]) -> None:
    rows: list[str] = []
    for label, value, state in items:
        state_key = state.casefold().replace(" ", "-")
        rows.append(
            f"""
            <div class="fta-confidence-row">
                <div><strong>{escape(label)}</strong><span>{escape(value)}</span></div>
                <span class="fta-confidence-state fta-confidence-{escape(state_key)}">{escape(state)}</span>
            </div>
            """
        )
    _render_html(
        '<div class="fta-confidence-list">' + "".join(rows) + "</div>"
    )


# ---------------------------------------------------------------------------
# Plotly design system
# ---------------------------------------------------------------------------


PLOTLY_COLORS = [
    "#23C7D7",
    "#0B6B80",
    "#35B58A",
    "#E4A84E",
    "#E56565",
    "#7C8D98",
    "#6F79D8",
    "#8ABEC7",
]


def apply_plotly_theme(
    figure: go.Figure,
    *,
    height: int = 360,
    show_legend: bool = True,
    horizontal_legend: bool = True,
) -> go.Figure:
    """Apply a chart palette that follows the active light/dark theme."""
    is_light = _light_mode_enabled()
    surface = "#FFFFFF" if is_light else "#10242E"
    text = "#1D303B" if is_light else "#F3FAFC"
    muted = "#5C6F7A" if is_light else "#A9BDC6"
    axis = "#536873" if is_light else "#9DB2BB"
    grid = "rgba(67,93,106,0.10)" if is_light else "rgba(169,189,198,0.13)"
    line = "rgba(67,93,106,0.12)" if is_light else "rgba(169,189,198,0.18)"
    hover_bg = "#102631" if is_light else "#EAF8FA"
    hover_text = "#FFFFFF" if is_light else "#10242E"

    legend_settings: dict[str, Any] = {
        "title_text": "",
        "font": {"color": muted, "size": 11},
        "bgcolor": "rgba(0,0,0,0)",
    }
    if horizontal_legend:
        legend_settings.update(
            {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "left",
                "x": 0,
            }
        )

    figure.update_layout(
        height=height,
        margin={"l": 22, "r": 18, "t": 34, "b": 24},
        paper_bgcolor=surface,
        plot_bgcolor=surface,
        font={"family": "Inter, Segoe UI, sans-serif", "color": text, "size": 12},
        hoverlabel={
            "bgcolor": hover_bg,
            "font": {"color": hover_text, "size": 12},
            "bordercolor": hover_bg,
        },
        legend=legend_settings,
        showlegend=show_legend,
        colorway=PLOTLY_COLORS,
    )
    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=line,
        tickfont={"color": muted, "size": 11},
        title_font={"color": axis, "size": 11},
    )
    figure.update_yaxes(
        gridcolor=grid,
        zeroline=False,
        linecolor=line,
        tickfont={"color": muted, "size": 11},
        title_font={"color": axis, "size": 11},
    )

    # Pie and donut separators must match the active surface instead of
    # remaining permanently white in dark mode.
    for trace in figure.data:
        if getattr(trace, "type", "") in {"pie", "sunburst", "treemap"}:
            try:
                trace.update(marker={"line": {"color": surface, "width": 2}})
            except Exception:
                pass
    return figure
