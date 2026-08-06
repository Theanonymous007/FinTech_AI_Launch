from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from PIL import Image

from database import (
    UPLOADS_DIR,
    add_invoice,
    find_duplicate,
    get_vendor_memory,
)
from ocr_engine import (
    ocr_is_available,
    pdf_support_is_available,
    run_ocr,
)

CATEGORIES = [
    "Raw Materials",
    "Utilities",
    "Rent",
    "Transport",
    "Equipment",
    "Maintenance",
    "Marketing",
    "Office Expenses",
    "Taxes",
    "Other",
]

STATUSES = ["Paid", "Pending", "Overdue"]

FIELD_LABELS = {
    "vendor": "Vendor",
    "invoice_number": "Invoice number",
    "invoice_date": "Invoice date",
    "gst": "GST / Tax number",
    "category": "Category",
    "subtotal": "Subtotal",
    "tax": "Tax",
    "total": "Total",
}


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    return cleaned.strip("._") or "invoice"


def _file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _save_uploaded_file(filename: str, file_bytes: bytes) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = (
        f"{datetime.now():%Y%m%d_%H%M%S}_"
        f"{uuid.uuid4().hex[:8]}_{_safe_filename(filename)}"
    )
    path = UPLOADS_DIR / unique_name
    path.write_bytes(file_bytes)
    return path


def _reset_for_new_document(document_hash: str) -> None:
    if st.session_state.get("active_document_hash") == document_hash:
        return

    keys_to_clear = [
        "ocr_result",
        "invoice_vendor",
        "invoice_number",
        "invoice_date",
        "invoice_gst",
        "invoice_category",
        "invoice_subtotal",
        "invoice_tax",
        "invoice_total",
        "invoice_status",
        "remember_vendor",
        "vendor_memory_note",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)

    st.session_state["active_document_hash"] = document_hash


def _apply_suggestions(ocr_result: dict[str, Any]) -> None:
    suggestions = ocr_result["suggestions"]

    st.session_state["invoice_vendor"] = suggestions.get(
        "vendor", ""
    )
    st.session_state["invoice_number"] = suggestions.get(
        "invoice_number", ""
    )
    st.session_state["invoice_date"] = suggestions.get(
        "invoice_date", date.today()
    )
    st.session_state["invoice_gst"] = suggestions.get("gst", "")
    st.session_state["invoice_category"] = suggestions.get(
        "category", "Other"
    )
    st.session_state["invoice_subtotal"] = float(
        suggestions.get("subtotal", 0)
    )
    st.session_state["invoice_tax"] = float(
        suggestions.get("tax", 0)
    )
    st.session_state["invoice_total"] = float(
        suggestions.get("total", 0)
    )
    st.session_state.setdefault("invoice_status", "Pending")
    st.session_state.setdefault("remember_vendor", True)

    vendor = suggestions.get("vendor", "")
    memory = get_vendor_memory(vendor) if vendor else None

    if memory:
        if memory.get("gst"):
            st.session_state["invoice_gst"] = memory["gst"]

        preferred_category = memory.get("preferred_category")
        if preferred_category in CATEGORIES:
            st.session_state["invoice_category"] = preferred_category

        st.session_state["vendor_memory_note"] = (
            f"Recurring vendor recognised. Applied verified memory from "
            f"{memory['times_seen']} previous record(s)."
        )
    else:
        st.session_state.pop("vendor_memory_note", None)


def _confidence_status(confidence: float) -> str:
    if confidence >= 0.85:
        return "High"
    if confidence >= 0.60:
        return "Review"
    return "Low"


def _show_ocr_result(ocr_result: dict[str, Any]) -> None:
    st.subheader("🤖 OCR review")

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric(
        "Average text confidence",
        f"{ocr_result['average_confidence']:.0%}",
    )
    metric_2.metric(
        "OCR processing time",
        f"{ocr_result['processing_seconds']:.2f} sec",
    )
    metric_3.metric(
        "Pages processed",
        (
            f"{ocr_result['pages_processed']}/"
            f"{ocr_result['page_count']}"
        ),
    )

    if ocr_result["page_count"] > ocr_result["pages_processed"]:
        st.info(
            "For speed, this prototype processes the first "
            f"{ocr_result['pages_processed']} PDF pages."
        )

    confidence_rows = []
    for field_name, confidence in ocr_result[
        "field_confidence"
    ].items():
        value = ocr_result["suggestions"].get(field_name, "")
        confidence_rows.append(
            {
                "Field": FIELD_LABELS.get(field_name, field_name),
                "Suggested value": str(value),
                "Confidence": f"{confidence:.0%}",
                "Action": _confidence_status(confidence),
            }
        )

    st.dataframe(
        pd.DataFrame(confidence_rows),
        width="stretch",
        hide_index=True,
    )

    memory_note = st.session_state.get("vendor_memory_note")
    if memory_note:
        st.success(f"🧠 {memory_note}")

    with st.expander("View recognised text and line confidence"):
        st.text_area(
            "Recognised text",
            value=ocr_result["raw_text"],
            height=240,
            disabled=True,
        )

        lines = pd.DataFrame(ocr_result["lines"])
        if not lines.empty:
            lines["confidence"] = lines["confidence"].map(
                lambda score: f"{score:.0%}"
            )
            lines.columns = ["Recognised line", "Confidence"]
            st.dataframe(lines, width="stretch", hide_index=True)


def _default_widget_state() -> None:
    st.session_state.setdefault("invoice_vendor", "")
    st.session_state.setdefault("invoice_number", "")
    st.session_state.setdefault("invoice_date", date.today())
    st.session_state.setdefault("invoice_gst", "")
    st.session_state.setdefault("invoice_category", "Other")
    st.session_state.setdefault("invoice_subtotal", 0.0)
    st.session_state.setdefault("invoice_tax", 0.0)
    st.session_state.setdefault("invoice_total", 0.0)
    st.session_state.setdefault("invoice_status", "Pending")
    st.session_state.setdefault("remember_vendor", True)


def render_upload_page() -> None:
    st.header("📤 AI Invoice Capture and Verification")
    st.caption(
        "Upload an invoice, run local OCR, review uncertain fields, "
        "and save only verified financial data."
    )

    uploaded_file = st.file_uploader(
        "Invoice image or PDF",
        type=["png", "jpg", "jpeg", "pdf"],
    )

    if uploaded_file is None:
        st.info(
            "Use the included sample_invoice.png for your first OCR test."
        )
        return

    file_bytes = uploaded_file.getvalue()
    document_hash = _file_hash(file_bytes)
    _reset_for_new_document(document_hash)

    file_type = uploaded_file.type or ""
    is_pdf = uploaded_file.name.casefold().endswith(".pdf")

    if file_type.startswith("image/"):
        try:
            preview = Image.open(uploaded_file)
            st.image(
                preview,
                caption=uploaded_file.name,
                width=520,
            )
        except Exception:
            st.warning(
                "The image preview could not be opened, "
                "but OCR may still process it."
            )
    elif is_pdf:
        st.info(f"PDF selected: {uploaded_file.name}")

    duplicate_file = find_duplicate("", "", document_hash)
    if duplicate_file is not None:
        st.error(
            "This exact document has already been saved as "
            f"record #{duplicate_file['id']}."
        )
        return

    if not ocr_is_available():
        st.warning(
            "OCR is not installed yet. Stop the app and "
            "double-click install_ocr.bat."
        )
    elif is_pdf and not pdf_support_is_available():
        st.warning(
            "PDF OCR support is not installed. Run install_ocr.bat."
        )
    else:
        if st.button(
            "🤖 Run OCR and suggest invoice fields",
            type="primary",
            width="stretch",
        ):
            try:
                with st.spinner(
                    "Reading the invoice locally. The first run "
                    "can take a little longer..."
                ):
                    result = run_ocr(
                        file_bytes,
                        uploaded_file.name,
                    ).to_dict()

                st.session_state["ocr_result"] = result
                _apply_suggestions(result)

            except Exception as error:
                st.error(f"OCR could not complete: {error}")

    ocr_result = st.session_state.get("ocr_result")
    if ocr_result:
        _show_ocr_result(ocr_result)

    _default_widget_state()

    st.subheader("Human verification")
    st.caption(
        "Fields remain editable because OCR suggestions must be "
        "verified before they enter the financial database."
    )

    with st.form("invoice_entry_form", clear_on_submit=False):
        left, right = st.columns(2)

        with left:
            st.text_input(
                "Vendor name *",
                key="invoice_vendor",
                placeholder="Example: Alpha Packaging",
            )
            st.text_input(
                "Invoice number *",
                key="invoice_number",
                placeholder="Example: INV-2026-001",
            )
            st.date_input(
                "Invoice date *",
                key="invoice_date",
            )
            st.text_input(
                "GST / Tax number",
                key="invoice_gst",
            )

        with right:
            st.selectbox(
                "Expense category *",
                CATEGORIES,
                key="invoice_category",
            )
            st.selectbox(
                "Payment status *",
                STATUSES,
                key="invoice_status",
            )
            st.number_input(
                "Subtotal (₹) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                key="invoice_subtotal",
            )
            st.number_input(
                "Tax amount (₹)",
                min_value=0.0,
                step=10.0,
                format="%.2f",
                key="invoice_tax",
            )
            st.number_input(
                "Final total (₹) *",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                key="invoice_total",
            )

        st.checkbox(
            "Remember verified GST and category for this vendor",
            key="remember_vendor",
            help=(
                "This demonstrates correction-driven adaptation "
                "for recurring vendors."
            ),
        )

        submitted = st.form_submit_button(
            "Save verified invoice",
            type="primary",
            width="stretch",
        )

    calculated_total = round(
        float(st.session_state["invoice_subtotal"])
        + float(st.session_state["invoice_tax"]),
        2,
    )
    entered_total = round(
        float(st.session_state["invoice_total"]),
        2,
    )

    if entered_total and abs(calculated_total - entered_total) > 0.05:
        st.warning(
            f"Verification warning: Subtotal + Tax is "
            f"₹{calculated_total:,.2f}, while Final Total is "
            f"₹{entered_total:,.2f}. Check for a discount, "
            "rounding adjustment or OCR error."
        )

    if not submitted:
        return

    vendor = st.session_state["invoice_vendor"].strip()
    invoice_number = st.session_state["invoice_number"].strip()
    subtotal = float(st.session_state["invoice_subtotal"])
    tax = float(st.session_state["invoice_tax"])
    total = float(st.session_state["invoice_total"])

    errors: list[str] = []
    if not vendor:
        errors.append("Enter or verify the vendor name.")
    if not invoice_number:
        errors.append("Enter or verify the invoice number.")
    if subtotal <= 0:
        errors.append("Subtotal must be greater than zero.")
    if total <= 0:
        errors.append("Final total must be greater than zero.")

    if errors:
        for error in errors:
            st.error(error)
        return

    duplicate = find_duplicate(vendor, invoice_number, document_hash)
    if duplicate is not None:
        st.error(
            "Possible duplicate detected. "
            f"Existing record: #{duplicate['id']} — "
            f"{duplicate['vendor']} / "
            f"{duplicate['invoice_number']}."
        )
        return

    saved_path: Path | None = None

    try:
        saved_path = _save_uploaded_file(
            uploaded_file.name,
            file_bytes,
        )

        active_ocr = st.session_state.get("ocr_result")
        extraction_mode = (
            "RapidOCR + human verification"
            if active_ocr
            else "Manual verification"
        )

        success, message = add_invoice(
            {
                "vendor": vendor,
                "invoice_number": invoice_number,
                "invoice_date": (
                    st.session_state["invoice_date"].isoformat()
                ),
                "gst": st.session_state["invoice_gst"],
                "category": st.session_state["invoice_category"],
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "status": st.session_state["invoice_status"],
                "file_name": uploaded_file.name,
                "file_path": str(saved_path),
                "file_hash": document_hash,
                "ocr_text": (
                    active_ocr["raw_text"] if active_ocr else ""
                ),
                "ocr_confidence": (
                    active_ocr["average_confidence"]
                    if active_ocr
                    else 0
                ),
                "ocr_seconds": (
                    active_ocr["processing_seconds"]
                    if active_ocr
                    else 0
                ),
                "extraction_mode": extraction_mode,
                "remember_vendor": st.session_state[
                    "remember_vendor"
                ],
            }
        )

        if success:
            st.success(message)
            st.balloons()
            st.info(
                "Open Dashboard and Invoice Records to see the "
                "updated analytics."
            )
        else:
            if saved_path.exists():
                saved_path.unlink()
            st.error(message)

    except OSError as error:
        if saved_path is not None and saved_path.exists():
            saved_path.unlink()
        st.error(f"The invoice document could not be saved: {error}")
