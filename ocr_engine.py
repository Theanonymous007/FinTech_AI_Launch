from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageOps, ImageFilter

try:
    from rapidocr import RapidOCR
except ImportError:
    RapidOCR = None

try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None


@dataclass
class OCRLine:
    text: str
    confidence: float


@dataclass
class OCRDocumentResult:
    raw_text: str
    lines: list[dict[str, Any]]
    average_confidence: float
    processing_seconds: float
    suggestions: dict[str, Any]
    field_confidence: dict[str, float]
    page_count: int
    pages_processed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ocr_is_available() -> bool:
    return RapidOCR is not None


def pdf_support_is_available() -> bool:
    return pdfium is not None


@lru_cache(maxsize=1)
def get_engine():
    if RapidOCR is None:
        raise RuntimeError(
            "RapidOCR is not installed. Run install_ocr.bat first."
        )

    return RapidOCR()


def _normalise_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")

    # Upscale smaller invoices to improve character visibility.
    longest_side = max(image.size)
    if longest_side < 1800:
        scale = 1800 / longest_side
        image = image.resize(
            (
                max(1, round(image.width * scale)),
                max(1, round(image.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )

    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.12)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def _document_to_images(
    file_bytes: bytes,
    filename: str,
    max_pdf_pages: int = 3,
) -> tuple[list[Image.Image], int]:
    lower_name = filename.casefold()

    if lower_name.endswith(".pdf"):
        if pdfium is None:
            raise RuntimeError(
                "PDF OCR requires pypdfium2. Run install_ocr.bat."
            )

        pdf = pdfium.PdfDocument(file_bytes)
        page_count = len(pdf)
        images: list[Image.Image] = []

        try:
            for page_index in range(min(page_count, max_pdf_pages)):
                page = pdf[page_index]
                bitmap = page.render(scale=2.2)
                image = bitmap.to_pil()
                images.append(_normalise_image(image))
                page.close()
        finally:
            pdf.close()

        return images, page_count

    image = Image.open(io.BytesIO(file_bytes))
    return [_normalise_image(image)], 1


def _score_at(scores: Sequence[float], index: int) -> float:
    if index < len(scores):
        try:
            return max(0.0, min(1.0, float(scores[index])))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


# Money parsing is intentionally conservative. OCR may correctly read account,
# phone, GST, reference or other identifier numbers; those must never become
# invoice amounts simply because they are numerically large.
_CURRENCY_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR|AED|USD|EUR|GBP|\$|€|£)",
    flags=re.IGNORECASE,
)

_BLOCKED_AMOUNT_CONTEXT = (
    "account number",
    "account no",
    "account #",
    "a/c no",
    "a/c number",
    "acc no",
    "bank a/c",
    "bank account",
    "ifsc",
    "iban",
    "swift",
    "phone",
    "mobile",
    "contact",
    "gstin",
    "gst no",
    "gst number",
    "pan no",
    "pan number",
    "invoice no",
    "invoice number",
    "bill no",
    "bill number",
    "order no",
    "order number",
    "reference no",
    "reference number",
    "ref no",
    "hsn",
    "sac",
    "pincode",
    "pin code",
    "postal code",
)

_MONEY_LABEL_HINTS = (
    "subtotal",
    "sub total",
    "taxable amount",
    "basic amount",
    "grand total",
    "net total",
    "invoice total",
    "amount payable",
    "amount due",
    "total amount",
    "balance due",
    "total tax",
    "tax amount",
    "gst amount",
    "total gst",
)


def _has_currency_marker(value: str) -> bool:
    return _CURRENCY_PATTERN.search(value) is not None


def _looks_like_blocked_identifier_line(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in _BLOCKED_AMOUNT_CONTEXT)


def _raw_amount_tokens(value: str) -> list[tuple[str, int, int]]:
    """Return numeric-looking tokens with their positions in the source line."""
    # Supports plain, western-grouped and Indian-grouped numbers.
    pattern = re.compile(
        r"(?<![A-Za-z0-9])"
        r"[-+]?"
        r"(?:\d{1,3}(?:,\d{2,3})+|\d+)"
        r"(?:\.\d{1,2})?"
        r"(?![A-Za-z0-9])"
    )
    return [
        (match.group(0), match.start(), match.end())
        for match in pattern.finditer(value)
    ]


def _is_plausible_money_token(
    raw_token: str,
    source_line: str,
    start: int,
    end: int,
    *,
    labelled: bool = False,
) -> bool:
    """Reject identifier-like values before converting them to money."""
    compact = raw_token.replace(",", "").lstrip("+-")
    digits_only = re.sub(r"\D", "", compact)

    if not digits_only:
        return False

    # A percentage is a rate, not a money amount.
    after = source_line[end : min(len(source_line), end + 3)]
    # A percent sign after this token marks it as a tax/rate percentage.
    # Do not inspect characters before the token because a previous token may
    # legitimately be a rate (e.g. "CGST 9% 450.00").
    if "%" in after:
        return False

    # Common year values should not become monetary fallbacks.
    if (
        "." not in compact
        and "," not in raw_token
        and len(digits_only) == 4
    ):
        try:
            year_value = int(digits_only)
        except ValueError:
            year_value = 0
        if 1900 <= year_value <= 2100 and not _has_currency_marker(source_line):
            return False

    # Long uninterrupted integers are much more likely to be account,
    # phone, reference or identifier numbers. If an invoice truly has such a
    # large total, require explicit currency formatting and human verification.
    if (
        len(digits_only) >= 9
        and "." not in compact
        and "," not in raw_token
        and not _has_currency_marker(source_line)
    ):
        return False

    # Extremely long digit runs are never accepted automatically.
    if len(digits_only) >= 13:
        return False

    # In blocked contexts, accept a value only if the same line also contains
    # an explicit monetary label and the candidate is not a long identifier.
    if _looks_like_blocked_identifier_line(source_line):
        lowered = source_line.casefold()
        has_money_label = any(label in lowered for label in _MONEY_LABEL_HINTS)
        if not (labelled and has_money_label):
            return False

    return True


def _amounts_in_line(
    value: str,
    *,
    labelled: bool = False,
) -> list[float]:
    """Extract plausible monetary values while excluding identifier numbers."""
    amounts: list[float] = []

    for raw_token, start, end in _raw_amount_tokens(value):
        if not _is_plausible_money_token(
            raw_token,
            value,
            start,
            end,
            labelled=labelled,
        ):
            continue

        cleaned = raw_token.replace(",", "")
        try:
            amount = float(cleaned)
        except ValueError:
            continue

        if amount < 0:
            continue

        amounts.append(amount)

    return amounts


def _parse_amount(value: str) -> float | None:
    amounts = _amounts_in_line(value)
    return amounts[-1] if amounts else None



def _find_labelled_amount(
    lines: list[OCRLine],
    labels: Sequence[str],
    exclude_labels: Sequence[str] = (),
    *,
    lookahead: int = 3,
    skip_small_same_line: bool = False,
) -> tuple[float | None, float]:
    """Find a plausible monetary value near a financial label.

    OCR frequently places the label and value on separate lines. For example:
        Total
        Rs
        211,196.00

    The search therefore looks ahead a few lines, while still applying the
    identifier protections in _amounts_in_line().
    """
    lowered_labels = tuple(label.casefold() for label in labels)
    lowered_excludes = tuple(label.casefold() for label in exclude_labels)

    for index, line in enumerate(lines):
        lowered = line.text.casefold()

        matched_label = next(
            (label for label in lowered_labels if label in lowered),
            None,
        )
        if matched_label is None:
            continue

        if any(excluded in lowered for excluded in lowered_excludes):
            if matched_label in {"total", "tax"}:
                continue

        label_position = lowered.find(matched_label)
        tail = line.text[label_position + len(matched_label) :]

        tail_amounts = _amounts_in_line(tail, labelled=True)
        if skip_small_same_line:
            tail_amounts = [value for value in tail_amounts if value > 100]

        if tail_amounts:
            return tail_amounts[0], line.confidence

        # Look ahead several OCR lines because labels/currency/value may be
        # vertically separated. Stop if another obvious financial label is hit
        # before finding a value.
        for offset in range(1, lookahead + 1):
            candidate_index = index + offset
            if candidate_index >= len(lines):
                break

            candidate_line = lines[candidate_index]
            candidate_lowered = candidate_line.text.casefold().strip()

            # Currency-only lines such as "Rs" are expected and should be skipped.
            if candidate_lowered in {"rs", "rs.", "inr", "₹", "aed", "usd", "$"}:
                continue

            # Avoid wandering from one financial label into a different field.
            if any(
                other_label in candidate_lowered
                for other_label in _MONEY_LABEL_HINTS
                if other_label != matched_label
            ):
                break

            candidate_amounts = _amounts_in_line(
                candidate_line.text,
                labelled=True,
            )
            if not candidate_amounts:
                continue

            confidence = min(
                line.confidence,
                candidate_line.confidence,
            )
            return candidate_amounts[0], confidence

    return None, 0.0



def _find_tax(lines: list[OCRLine]) -> tuple[float | None, float]:
    total_tax, total_tax_conf = _find_labelled_amount(
        lines,
        [
            "total tax",
            "tax amount",
            "gst amount",
            "total gst",
        ],
        exclude_labels=["gstin", "gst no", "gst number"],
        lookahead=3,
    )
    if total_tax is not None:
        return total_tax, total_tax_conf

    component_values: list[float] = []
    component_scores: list[float] = []
    seen_component_lines: set[int] = set()

    for index, line in enumerate(lines):
        lowered = line.text.casefold()

        if any(
            marker in lowered
            for marker in ["cgst", "sgst", "igst", "vat"]
        ):
            if any(
                blocked in lowered
                for blocked in ["gstin", "gst no", "gst number"]
            ):
                continue

            amounts = _amounts_in_line(line.text, labelled=True)

            # "CGST 9%" should not contribute 9 as money. If no amount survives
            # on the label line, look directly below for the tax amount.
            if not amounts:
                for offset in (1, 2):
                    candidate_index = index + offset
                    if candidate_index >= len(lines):
                        break

                    candidate_line = lines[candidate_index]
                    candidate_lowered = candidate_line.text.casefold()

                    # Stop if we reached a new tax component before finding money.
                    if any(
                        marker in candidate_lowered
                        for marker in ["cgst", "sgst", "igst", "vat"]
                    ):
                        break

                    candidate_amounts = _amounts_in_line(
                        candidate_line.text,
                        labelled=True,
                    )
                    if candidate_amounts:
                        amounts = candidate_amounts
                        component_scores.append(
                            min(line.confidence, candidate_line.confidence)
                        )
                        break

            if amounts and index not in seen_component_lines:
                component_values.append(amounts[-1])
                if len(component_scores) < len(component_values):
                    component_scores.append(line.confidence)
                seen_component_lines.add(index)

    if component_values:
        return sum(component_values), min(component_scores)

    tax, confidence = _find_labelled_amount(
        lines,
        ["tax"],
        exclude_labels=[
            "tax invoice",
            "tax id",
            "tax number",
            "gstin",
        ],
        lookahead=2,
    )
    return tax, confidence


def _parse_date_value(value: str) -> date | None:
    value = value.strip().replace(".", "/").replace("-", "/")
    value = re.sub(r"\s+", "", value)

    for date_format in (
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%b/%Y",
        "%d/%B/%Y",
    ):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return None


def _find_date(lines: list[OCRLine]) -> tuple[date | None, float]:
    date_pattern = re.compile(
        r"\b("
        r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
        r"|"
        r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"
        r"|"
        r"\d{1,2}[./-][A-Za-z]{3,9}[./-]\d{2,4}"
        r")\b"
    )

    labelled_candidates: list[tuple[date, float]] = []
    fallback_candidates: list[tuple[date, float]] = []

    for line in lines:
        for match in date_pattern.findall(line.text):
            parsed = _parse_date_value(match)
            if parsed is None:
                continue

            if "date" in line.text.casefold():
                labelled_candidates.append((parsed, line.confidence))
            else:
                fallback_candidates.append((parsed, line.confidence))

    if labelled_candidates:
        return labelled_candidates[0]

    if fallback_candidates:
        return fallback_candidates[0]

    return None, 0.0


def _find_gst(lines: list[OCRLine]) -> tuple[str, float]:
    gst_pattern = re.compile(
        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
        flags=re.IGNORECASE,
    )

    for line in lines:
        compact = re.sub(r"\s+", "", line.text.upper())
        match = gst_pattern.search(compact)
        if match:
            return match.group(0), line.confidence

    return "", 0.0



def _find_invoice_number(lines: list[OCRLine]) -> tuple[str, float]:
    # Same-line formats such as "Invoice No: INV-2026-001".
    patterns = [
        re.compile(
            r"(?:invoice|inv|bill)\s*"
            r"(?:number|no\.?|#)\s*[:\-]?\s*"
            r"([A-Z0-9][A-Z0-9@/_\-\.]{2,})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:document|voucher)\s*"
            r"(?:number|no\.?|#)\s*[:\-]?\s*"
            r"([A-Z0-9][A-Z0-9@/_\-\.]{2,})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:invoice|inv|bill)\s*[:\-]\s*"
            r"([A-Z0-9][A-Z0-9@/_\-\.]{2,})",
            re.IGNORECASE,
        ),
    ]

    blocked_values = {
        "date",
        "total",
        "number",
        "no",
        "invoice",
        "bill",
    }

    for line in lines:
        for pattern in patterns:
            match = pattern.search(line.text)
            if not match:
                continue

            candidate = match.group(1).strip("-_/")
            if candidate.casefold() not in blocked_values:
                return candidate, line.confidence

    # OCR often splits:
    #   InvoiceNo
    #   INV@100
    # across two lines. Handle that format separately.
    for index, line in enumerate(lines):
        compact = re.sub(r"[^a-z]", "", line.text.casefold())
        if compact not in {
            "invoiceno",
            "invoicenumber",
            "invno",
            "billno",
            "billnumber",
        }:
            continue

        for offset in (1, 2):
            candidate_index = index + offset
            if candidate_index >= len(lines):
                break

            candidate = lines[candidate_index].text.strip()
            if not re.fullmatch(
                r"[A-Z0-9][A-Z0-9@/_\-\.]{2,}",
                candidate,
                flags=re.IGNORECASE,
            ):
                continue

            # Require at least one digit so generic words aren't accepted.
            if not re.search(r"\d", candidate):
                continue

            return candidate, min(
                line.confidence,
                lines[candidate_index].confidence,
            )

    return "", 0.0


def _find_vendor(lines: list[OCRLine]) -> tuple[str, float]:
    blocked_terms = {
        "tax invoice",
        "invoice",
        "original",
        "duplicate",
        "bill of supply",
        "cash memo",
        "receipt",
        "gstin",
        "phone",
        "email",
        "date",
        "invoice no",
        "invoice number",
    }

    for line in lines[:12]:
        candidate = _clean_text(line.text)
        lowered = candidate.casefold()

        if len(candidate) < 3 or len(candidate) > 80:
            continue
        if any(term == lowered or lowered.startswith(term + ":")
               for term in blocked_terms):
            continue
        if not re.search(r"[A-Za-z]{3,}", candidate):
            continue

        digit_ratio = sum(character.isdigit() for character in candidate)
        if digit_ratio > max(4, len(candidate) * 0.35):
            continue

        return candidate, line.confidence

    return "", 0.0


def _suggest_category(raw_text: str) -> tuple[str, float]:
    lowered = raw_text.casefold()

    keyword_groups = {
        "Utilities": [
            "electricity",
            "power bill",
            "water bill",
            "internet",
            "telephone",
            "utility",
        ],
        "Rent": ["rent", "lease", "premises"],
        "Transport": [
            "transport",
            "logistics",
            "freight",
            "courier",
            "fuel",
            "diesel",
            "petrol",
        ],
        "Equipment": [
            "machine",
            "equipment",
            "computer",
            "laptop",
            "printer",
            "tool",
        ],
        "Maintenance": [
            "repair",
            "maintenance",
            "service charge",
            "spare part",
        ],
        "Marketing": [
            "advertising",
            "marketing",
            "promotion",
            "printing",
            "campaign",
        ],
        "Office Expenses": [
            "stationery",
            "office supplies",
            "paper",
            "cartridge",
            "toner",
        ],
        "Taxes": [
            "professional tax",
            "government fee",
            "tax payment",
        ],
        "Raw Materials": [
            "raw material",
            "packaging",
            "steel",
            "cement",
            "timber",
            "wood",
            "fabric",
            "chemical",
            "component",
        ],
    }

    best_category = "Other"
    best_count = 0

    for category, keywords in keyword_groups.items():
        count = sum(keyword in lowered for keyword in keywords)
        if count > best_count:
            best_category = category
            best_count = count

    return best_category, 0.72 if best_count else 0.35


def parse_invoice_fields(lines: list[OCRLine]) -> tuple[
    dict[str, Any],
    dict[str, float],
]:
    raw_text = "\n".join(line.text for line in lines)

    vendor, vendor_conf = _find_vendor(lines)
    invoice_number, invoice_conf = _find_invoice_number(lines)
    invoice_date, date_conf = _find_date(lines)
    gst, gst_conf = _find_gst(lines)

    subtotal, subtotal_conf = _find_labelled_amount(
        lines,
        ["subtotal", "sub total", "taxable amount", "basic amount"],
        lookahead=3,
    )

    # Some GST invoices print the taxable subtotal as:
    #   GROSS 18
    #   178,980.00
    # where "18" is the GST slab/rate rather than the money value.
    if subtotal is None:
        subtotal, subtotal_conf = _find_labelled_amount(
            lines,
            ["gross"],
            lookahead=2,
            skip_small_same_line=True,
        )

    tax, tax_conf = _find_tax(lines)
    total, total_conf = _find_labelled_amount(
        lines,
        [
            "grand total",
            "net total",
            "invoice total",
            "amount payable",
            "amount due",
            "total amount",
            "balance due",
            "total",
        ],
        exclude_labels=[
            "subtotal",
            "sub total",
            "total tax",
            "total quantity",
        ],
        lookahead=3,
    )

    # Conservative fallback: never choose the largest number in the
    # document. Account numbers, phone numbers and references are often larger
    # than the invoice total. Only consider currency-formatted / grouped values
    # near the bottom of the invoice; otherwise leave the field unresolved for
    # human verification.
    if total is None:
        fallback_candidates: list[tuple[float, float]] = []

        for line in lines[-15:]:
            text_value = line.text
            lowered = text_value.casefold()

            if _looks_like_blocked_identifier_line(text_value):
                continue

            has_currency = _has_currency_marker(text_value)
            has_grouped_number = bool(
                re.search(
                    r"(?<!\d)\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?(?!\d)",
                    text_value,
                )
            )
            has_amount_word = any(
                word in lowered
                for word in ["payable", "amount due", "balance due"]
            )

            if not (has_currency or has_grouped_number or has_amount_word):
                continue

            for amount in _amounts_in_line(text_value):
                if amount >= 1:
                    fallback_candidates.append(
                        (amount, min(line.confidence, 0.38))
                    )

        if fallback_candidates:
            total, total_conf = max(
                fallback_candidates,
                key=lambda item: item[0],
            )

    if subtotal is None and total is not None and tax is not None:
        subtotal = max(0.0, total - tax)
        subtotal_conf = min(total_conf, tax_conf, 0.70)

    if tax is None and subtotal is not None and total is not None:
        difference = total - subtotal
        if difference >= 0:
            tax = difference
            tax_conf = min(total_conf, subtotal_conf, 0.65)

    if total is None and subtotal is not None:
        total = subtotal + (tax or 0)
        total_conf = min(subtotal_conf, tax_conf or subtotal_conf, 0.65)

    # Arithmetic sanity check. If independently extracted values disagree by
    # more than a small tolerance, clear the least reliable field instead of
    # silently storing inconsistent money.
    if subtotal is not None and tax is not None and total is not None:
        expected_total = subtotal + tax
        tolerance = max(2.0, abs(total) * 0.02)

        if abs(expected_total - total) > tolerance:
            confidences = {
                "subtotal": subtotal_conf,
                "tax": tax_conf,
                "total": total_conf,
            }
            weakest = min(confidences, key=confidences.get)

            if weakest == "subtotal":
                subtotal = None
                subtotal_conf = 0.0
            elif weakest == "tax":
                tax = None
                tax_conf = 0.0
            else:
                total = None
                total_conf = 0.0

    category, category_conf = _suggest_category(raw_text)

    suggestions = {
        "vendor": vendor,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date or date.today(),
        "gst": gst,
        "category": category,
        "subtotal": round(float(subtotal or 0), 2),
        "tax": round(float(tax or 0), 2),
        "total": round(float(total or 0), 2),
    }

    field_confidence = {
        "vendor": vendor_conf,
        "invoice_number": invoice_conf,
        "invoice_date": date_conf,
        "gst": gst_conf,
        "category": category_conf,
        "subtotal": subtotal_conf,
        "tax": tax_conf,
        "total": total_conf,
    }

    return suggestions, field_confidence


def run_ocr(
    file_bytes: bytes,
    filename: str,
    max_pdf_pages: int = 3,
) -> OCRDocumentResult:
    """Recognise text and generate editable invoice-field suggestions."""
    engine = get_engine()
    images, page_count = _document_to_images(
        file_bytes,
        filename,
        max_pdf_pages=max_pdf_pages,
    )

    recognised_lines: list[OCRLine] = []
    total_seconds = 0.0

    for image in images:
        result = engine(np.asarray(image))

        texts = list(getattr(result, "txts", ()) or ())
        scores = list(getattr(result, "scores", ()) or ())
        total_seconds += float(getattr(result, "elapse", 0) or 0)

        for index, text in enumerate(texts):
            cleaned = _clean_text(str(text))
            if not cleaned:
                continue
            recognised_lines.append(
                OCRLine(
                    text=cleaned,
                    confidence=_score_at(scores, index),
                )
            )

    if not recognised_lines:
        raise RuntimeError(
            "OCR could not detect readable text. Try a clearer, "
            "straight and well-lit invoice image."
        )

    suggestions, field_confidence = parse_invoice_fields(
        recognised_lines
    )
    average_confidence = sum(
        line.confidence for line in recognised_lines
    ) / len(recognised_lines)

    return OCRDocumentResult(
        raw_text="\n".join(line.text for line in recognised_lines),
        lines=[
            {
                "text": line.text,
                "confidence": line.confidence,
            }
            for line in recognised_lines
        ],
        average_confidence=average_confidence,
        processing_seconds=total_seconds,
        suggestions=suggestions,
        field_confidence=field_confidence,
        page_count=page_count,
        pages_processed=len(images),
    )
