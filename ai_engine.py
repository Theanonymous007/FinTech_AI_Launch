from __future__ import annotations

"""
FinTech AI — Explainable Financial Intelligence Engine (V3.1)

This module reads verified invoice records from database.py and produces:
- Financial summaries
- Monthly and category intelligence
- Vendor intelligence
- Explainable anomaly alerts
- A transparent financial-health score
- A next-month expense forecast
- Prioritised recommendations
- Grounded answers to common finance questions

V3.1 intentionally uses explainable statistical rules and does not require
scikit-learn. Once this stable layer works, an Isolation Forest model can be
added as a second opinion in a later version.
"""

from datetime import date
from typing import Any, Iterable

import numpy as np
import pandas as pd


EXPECTED_COLUMNS = [
    "id",
    "vendor",
    "invoice_number",
    "invoice_date",
    "gst",
    "category",
    "subtotal",
    "tax",
    "total",
    "status",
    "file_name",
    "file_path",
    "file_hash",
    "ocr_text",
    "ocr_confidence",
    "ocr_seconds",
    "extraction_mode",
    "created_at",
]

STRING_COLUMNS = [
    "vendor",
    "invoice_number",
    "gst",
    "category",
    "status",
    "file_name",
    "file_path",
    "file_hash",
    "ocr_text",
    "extraction_mode",
    "created_at",
]

NUMERIC_COLUMNS = [
    "id",
    "subtotal",
    "tax",
    "total",
    "ocr_confidence",
    "ocr_seconds",
]


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def _empty_invoice_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame that still contains every required column."""
    dataframe = pd.DataFrame(columns=EXPECTED_COLUMNS)
    dataframe["invoice_date"] = pd.to_datetime(
        dataframe["invoice_date"],
        errors="coerce",
    )

    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    return dataframe


def prepare_invoice_dataframe(
    rows: Iterable[dict[str, Any]] | None,
) -> pd.DataFrame:
    """
    Convert database rows into one predictable, analysis-ready DataFrame.

    This function is deliberately defensive. Even when the database is empty
    or an older database does not contain newer columns, downstream functions
    still receive a valid DataFrame and will not raise KeyError.
    """
    rows_list = list(rows or [])
    if not rows_list:
        return _empty_invoice_dataframe()

    dataframe = pd.DataFrame(rows_list).copy()

    defaults: dict[str, Any] = {
        "id": 0,
        "vendor": "",
        "invoice_number": "",
        "invoice_date": pd.NaT,
        "gst": "",
        "category": "Other",
        "subtotal": 0.0,
        "tax": 0.0,
        "total": 0.0,
        "status": "Pending",
        "file_name": "",
        "file_path": "",
        "file_hash": "",
        "ocr_text": "",
        "ocr_confidence": 0.0,
        "ocr_seconds": 0.0,
        "extraction_mode": "Manual verification",
        "created_at": "",
    }

    for column in EXPECTED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = defaults[column]

    dataframe = dataframe[EXPECTED_COLUMNS].copy()

    for column in STRING_COLUMNS:
        dataframe[column] = (
            dataframe[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).fillna(0.0)

    dataframe["invoice_date"] = pd.to_datetime(
        dataframe["invoice_date"],
        errors="coerce",
    )

    dataframe["vendor"] = dataframe["vendor"].replace("", "Unknown Vendor")
    dataframe["category"] = dataframe["category"].replace("", "Other")
    dataframe["status"] = (
        dataframe["status"]
        .replace("", "Pending")
        .str.title()
    )

    # Keep totals non-negative. Financial corrections should happen in the UI.
    for column in ["subtotal", "tax", "total"]:
        dataframe[column] = dataframe[column].clip(lower=0)

    return dataframe


def load_invoice_dataframe() -> pd.DataFrame:
    """Load verified invoices from the existing V2 database module."""
    try:
        from database import get_all_invoices
    except ImportError as error:
        raise RuntimeError(
            "database.py could not be imported. Keep ai_engine.py in the "
            "same MSME_AI_Project folder as database.py."
        ) from error

    return prepare_invoice_dataframe(get_all_invoices())


# ---------------------------------------------------------------------------
# Core summaries
# ---------------------------------------------------------------------------

def financial_summary(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Calculate top-level financial indicators."""
    if dataframe.empty:
        return {
            "invoice_count": 0,
            "total_spend": 0.0,
            "paid_amount": 0.0,
            "pending_amount": 0.0,
            "overdue_amount": 0.0,
            "average_invoice": 0.0,
            "largest_invoice": 0.0,
            "vendor_count": 0,
            "category_count": 0,
            "date_from": None,
            "date_to": None,
        }

    paid_amount = float(
        dataframe.loc[dataframe["status"].eq("Paid"), "total"].sum()
    )
    pending_amount = float(
        dataframe.loc[dataframe["status"].eq("Pending"), "total"].sum()
    )
    overdue_amount = float(
        dataframe.loc[dataframe["status"].eq("Overdue"), "total"].sum()
    )

    valid_dates = dataframe["invoice_date"].dropna()

    return {
        "invoice_count": int(len(dataframe)),
        "total_spend": float(dataframe["total"].sum()),
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "overdue_amount": overdue_amount,
        "average_invoice": float(dataframe["total"].mean()),
        "largest_invoice": float(dataframe["total"].max()),
        "vendor_count": int(dataframe["vendor"].nunique()),
        "category_count": int(dataframe["category"].nunique()),
        "date_from": (
            valid_dates.min().date().isoformat()
            if not valid_dates.empty
            else None
        ),
        "date_to": (
            valid_dates.max().date().isoformat()
            if not valid_dates.empty
            else None
        ),
    }


def monthly_spending(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate invoice spend and payment exposure by calendar month."""
    columns = [
        "month",
        "total_spend",
        "invoice_count",
        "paid_amount",
        "pending_amount",
        "overdue_amount",
    ]

    if dataframe.empty or "invoice_date" not in dataframe.columns:
        return pd.DataFrame(columns=columns)

    valid = dataframe.dropna(subset=["invoice_date"]).copy()
    if valid.empty:
        return pd.DataFrame(columns=columns)

    valid["month"] = (
        valid["invoice_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    valid["paid_amount"] = np.where(
        valid["status"].eq("Paid"),
        valid["total"],
        0.0,
    )
    valid["pending_amount"] = np.where(
        valid["status"].eq("Pending"),
        valid["total"],
        0.0,
    )
    valid["overdue_amount"] = np.where(
        valid["status"].eq("Overdue"),
        valid["total"],
        0.0,
    )

    monthly = (
        valid.groupby("month", as_index=False)
        .agg(
            total_spend=("total", "sum"),
            invoice_count=("id", "count"),
            paid_amount=("paid_amount", "sum"),
            pending_amount=("pending_amount", "sum"),
            overdue_amount=("overdue_amount", "sum"),
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    return monthly[columns]


def category_intelligence(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Summarise category spend, share, average and recent movement."""
    columns = [
        "category",
        "total_spend",
        "spend_share",
        "invoice_count",
        "average_invoice",
        "latest_month_spend",
        "previous_month_spend",
        "monthly_change",
    ]

    if dataframe.empty:
        return pd.DataFrame(columns=columns)

    grouped = (
        dataframe.groupby("category", as_index=False)
        .agg(
            total_spend=("total", "sum"),
            invoice_count=("id", "count"),
            average_invoice=("total", "mean"),
        )
    )

    total_spend = float(grouped["total_spend"].sum())
    grouped["spend_share"] = np.where(
        total_spend > 0,
        grouped["total_spend"] / total_spend,
        0.0,
    )

    monthly = monthly_spending_by_category(dataframe)
    grouped["latest_month_spend"] = 0.0
    grouped["previous_month_spend"] = 0.0
    grouped["monthly_change"] = np.nan

    if not monthly.empty:
        available_months = sorted(monthly["month"].unique())
        latest_month = available_months[-1]
        previous_month = (
            available_months[-2]
            if len(available_months) >= 2
            else None
        )

        latest_map = (
            monthly.loc[monthly["month"].eq(latest_month)]
            .set_index("category")["total_spend"]
            .to_dict()
        )
        previous_map = (
            monthly.loc[monthly["month"].eq(previous_month)]
            .set_index("category")["total_spend"]
            .to_dict()
            if previous_month is not None
            else {}
        )

        grouped["latest_month_spend"] = (
            grouped["category"].map(latest_map).fillna(0.0)
        )
        grouped["previous_month_spend"] = (
            grouped["category"].map(previous_map).fillna(0.0)
        )

        grouped["monthly_change"] = np.where(
            grouped["previous_month_spend"] > 0,
            (
                grouped["latest_month_spend"]
                - grouped["previous_month_spend"]
            )
            / grouped["previous_month_spend"],
            np.nan,
        )

    return (
        grouped[columns]
        .sort_values("total_spend", ascending=False)
        .reset_index(drop=True)
    )


def monthly_spending_by_category(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Return monthly category totals for charts and forecasting."""
    columns = ["month", "category", "total_spend", "invoice_count"]

    if dataframe.empty:
        return pd.DataFrame(columns=columns)

    valid = dataframe.dropna(subset=["invoice_date"]).copy()
    if valid.empty:
        return pd.DataFrame(columns=columns)

    valid["month"] = (
        valid["invoice_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    return (
        valid.groupby(["month", "category"], as_index=False)
        .agg(
            total_spend=("total", "sum"),
            invoice_count=("id", "count"),
        )
        .sort_values(["month", "total_spend"], ascending=[True, False])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Explainable anomaly detection
# ---------------------------------------------------------------------------

def _median_absolute_deviation(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 0.0

    median = float(clean.median())
    return float((clean - median).abs().median())


def _tax_rate(row: pd.Series) -> float:
    subtotal = float(row.get("subtotal", 0) or 0)
    tax = float(row.get("tax", 0) or 0)
    return tax / subtotal if subtotal > 0 else 0.0


def detect_anomalies(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Detect unusual invoices using transparent statistical rules.

    An alert is a request for human review. It is not proof of fraud.
    """
    columns = [
        "id",
        "invoice_date",
        "vendor",
        "invoice_number",
        "category",
        "total",
        "risk_score",
        "risk_level",
        "reasons",
    ]

    if dataframe.empty:
        return pd.DataFrame(columns=columns)

    records: list[dict[str, Any]] = []

    # Global robust threshold.
    global_median = float(dataframe["total"].median())
    global_mad = _median_absolute_deviation(dataframe["total"])
    global_q1 = float(dataframe["total"].quantile(0.25))
    global_q3 = float(dataframe["total"].quantile(0.75))
    global_iqr = max(0.0, global_q3 - global_q1)

    duplicate_mask = dataframe.duplicated(
        subset=["vendor", "invoice_number"],
        keep=False,
    )

    for index, row in dataframe.iterrows():
        score = 0
        reasons: list[str] = []
        amount = float(row["total"])
        vendor = str(row["vendor"])
        category = str(row["category"])

        if bool(duplicate_mask.loc[index]):
            score += 80
            reasons.append(
                "The vendor and invoice number appear more than once."
            )

        if amount <= 0:
            score += 35
            reasons.append("The final invoice total is zero.")

        # Compare against the vendor's other invoices.
        vendor_history = dataframe.loc[
            dataframe["vendor"].eq(vendor)
            & (dataframe.index != index),
            "total",
        ]

        if len(vendor_history) >= 3:
            vendor_median = float(vendor_history.median())
            vendor_mad = _median_absolute_deviation(vendor_history)
            vendor_limit = vendor_median + max(
                2.8 * 1.4826 * vendor_mad,
                vendor_median * 0.65,
            )

            if (
                vendor_median > 0
                and amount > vendor_limit
                and amount / vendor_median >= 1.60
            ):
                ratio = amount / vendor_median
                score += min(45, 20 + round((ratio - 1.6) * 18))
                reasons.append(
                    f"Amount is {ratio:.1f}× this vendor's median invoice."
                )

        # Compare against the category's other invoices.
        category_history = dataframe.loc[
            dataframe["category"].eq(category)
            & (dataframe.index != index),
            "total",
        ]

        if len(category_history) >= 4:
            category_median = float(category_history.median())
            category_mad = _median_absolute_deviation(category_history)
            category_limit = category_median + max(
                3.0 * 1.4826 * category_mad,
                category_median * 0.80,
            )

            if (
                category_median > 0
                and amount > category_limit
                and amount / category_median >= 1.80
            ):
                ratio = amount / category_median
                score += min(30, 12 + round((ratio - 1.8) * 10))
                reasons.append(
                    f"Amount is {ratio:.1f}× the category median."
                )

        # Global IQR/MAD rule, only when enough history exists.
        if len(dataframe) >= 8:
            global_limit = max(
                global_q3 + 1.5 * global_iqr,
                global_median + 3.5 * 1.4826 * global_mad,
            )

            if global_limit > 0 and amount > global_limit:
                score += 15
                reasons.append(
                    "Amount exceeds the robust high-value limit "
                    "for the full invoice history."
                )

        # Tax-rate consistency for recurring vendors.
        row_tax_rate = _tax_rate(row)
        vendor_rows = dataframe.loc[
            dataframe["vendor"].eq(vendor)
            & (dataframe.index != index)
        ].copy()

        if len(vendor_rows) >= 3:
            vendor_tax_rates = vendor_rows.apply(_tax_rate, axis=1)
            vendor_tax_rates = vendor_tax_rates[vendor_tax_rates > 0]

            if not vendor_tax_rates.empty and row_tax_rate > 0:
                usual_tax_rate = float(vendor_tax_rates.median())
                difference = abs(row_tax_rate - usual_tax_rate)

                if difference >= 0.06:
                    score += min(30, 15 + round(difference * 100))
                    reasons.append(
                        "Tax rate differs materially from this vendor's "
                        f"usual rate ({usual_tax_rate:.1%})."
                    )

        score = min(100, score)

        if score >= 70:
            risk_level = "High"
        elif score >= 40:
            risk_level = "Medium"
        elif score >= 20:
            risk_level = "Low"
        else:
            continue

        records.append(
            {
                "id": int(row["id"]),
                "invoice_date": row["invoice_date"],
                "vendor": vendor,
                "invoice_number": str(row["invoice_number"]),
                "category": category,
                "total": amount,
                "risk_score": score,
                "risk_level": risk_level,
                "reasons": " ".join(reasons),
            }
        )

    if not records:
        return pd.DataFrame(columns=columns)

    risk_order = {"High": 0, "Medium": 1, "Low": 2}
    result = pd.DataFrame(records)
    result["_risk_order"] = result["risk_level"].map(risk_order)

    return (
        result.sort_values(
            ["_risk_order", "risk_score", "total"],
            ascending=[True, False, False],
        )
        .drop(columns="_risk_order")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Vendor intelligence
# ---------------------------------------------------------------------------

def vendor_intelligence(
    dataframe: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Create explainable profiles for every recorded vendor."""
    columns = [
        "vendor",
        "total_spend",
        "spend_share",
        "invoice_count",
        "average_invoice",
        "median_invoice",
        "highest_invoice",
        "latest_invoice",
        "last_invoice_date",
        "paid_ratio",
        "open_amount",
        "consistency_score",
        "open_anomaly_count",
        "vendor_score",
        "vendor_risk",
        "dependency_risk",
    ]

    if dataframe.empty:
        return pd.DataFrame(columns=columns)

    total_business_spend = float(dataframe["total"].sum())
    anomaly_counts: dict[str, int] = {}

    if anomalies is not None and not anomalies.empty:
        anomaly_counts = (
            anomalies.groupby("vendor")
            .size()
            .astype(int)
            .to_dict()
        )

    records: list[dict[str, Any]] = []

    for vendor, group in dataframe.groupby("vendor"):
        group = group.sort_values("invoice_date")
        total_spend = float(group["total"].sum())
        average_invoice = float(group["total"].mean())
        median_invoice = float(group["total"].median())
        standard_deviation = float(group["total"].std(ddof=0) or 0.0)
        coefficient_of_variation = (
            standard_deviation / average_invoice
            if average_invoice > 0
            else 0.0
        )

        consistency_score = max(
            0,
            min(100, round(100 - coefficient_of_variation * 65)),
        )

        invoice_count = len(group)
        paid_ratio = float(group["status"].eq("Paid").mean())
        open_amount = float(
            group.loc[
                group["status"].isin(["Pending", "Overdue"]),
                "total",
            ].sum()
        )
        spend_share = (
            total_spend / total_business_spend
            if total_business_spend > 0
            else 0.0
        )
        open_anomaly_count = int(anomaly_counts.get(vendor, 0))
        anomaly_ratio = (
            open_anomaly_count / invoice_count
            if invoice_count
            else 0.0
        )

        payment_score = paid_ratio * 100
        anomaly_score = max(0.0, 100 - anomaly_ratio * 120)

        vendor_score = round(
            consistency_score * 0.45
            + payment_score * 0.30
            + anomaly_score * 0.25
        )

        if vendor_score >= 80:
            vendor_risk = "Low"
        elif vendor_score >= 60:
            vendor_risk = "Medium"
        else:
            vendor_risk = "High"

        if spend_share >= 0.50:
            dependency_risk = "High"
        elif spend_share >= 0.30:
            dependency_risk = "Medium"
        else:
            dependency_risk = "Low"

        dated_group = group.dropna(subset=["invoice_date"])
        latest_row = (
            dated_group.iloc[-1]
            if not dated_group.empty
            else group.iloc[-1]
        )

        records.append(
            {
                "vendor": vendor,
                "total_spend": total_spend,
                "spend_share": spend_share,
                "invoice_count": int(invoice_count),
                "average_invoice": average_invoice,
                "median_invoice": median_invoice,
                "highest_invoice": float(group["total"].max()),
                "latest_invoice": float(latest_row["total"]),
                "last_invoice_date": latest_row["invoice_date"],
                "paid_ratio": paid_ratio,
                "open_amount": open_amount,
                "consistency_score": consistency_score,
                "open_anomaly_count": open_anomaly_count,
                "vendor_score": vendor_score,
                "vendor_risk": vendor_risk,
                "dependency_risk": dependency_risk,
            }
        )

    return (
        pd.DataFrame(records)[columns]
        .sort_values("total_spend", ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Explainable financial-health score
# ---------------------------------------------------------------------------

def _component_status(score: float, maximum: float) -> str:
    ratio = score / maximum if maximum else 0.0
    if ratio >= 0.80:
        return "Strong"
    if ratio >= 0.60:
        return "Watch"
    return "Attention"


def calculate_health_score(
    dataframe: pd.DataFrame,
    anomalies: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Calculate an internal, explainable 0–100 prototype health indicator.

    This is not a bank credit score and must not be presented as one.
    """
    components: list[dict[str, Any]] = []

    if dataframe.empty:
        return {
            "score": 0,
            "status": "No data",
            "components": [],
            "weakest_components": [],
            "disclaimer": (
                "Internal prototype indicator; not a credit score "
                "or lending decision."
            ),
        }

    total_spend = float(dataframe["total"].sum())

    # 1. Payment discipline — 25 points.
    overdue_amount = float(
        dataframe.loc[dataframe["status"].eq("Overdue"), "total"].sum()
    )
    pending_amount = float(
        dataframe.loc[dataframe["status"].eq("Pending"), "total"].sum()
    )
    overdue_ratio = overdue_amount / total_spend if total_spend else 0.0
    pending_ratio = pending_amount / total_spend if total_spend else 0.0
    payment_penalty = min(
        1.0,
        overdue_ratio * 1.7 + pending_ratio * 0.45,
    )
    payment_score = round(25 * (1 - payment_penalty), 1)
    components.append(
        {
            "component": "Payment discipline",
            "score": payment_score,
            "maximum": 25,
            "status": _component_status(payment_score, 25),
            "evidence": (
                f"Overdue exposure: ₹{overdue_amount:,.0f}; "
                f"pending exposure: ₹{pending_amount:,.0f}."
            ),
            "improvement": (
                "Prioritise overdue invoices and review pending payment dates."
            ),
        }
    )

    # 2. Expense stability — 20 points.
    monthly = monthly_spending(dataframe)
    if len(monthly) < 3:
        stability_score = 12.0
        stability_evidence = (
            "Fewer than three months of history; stability is provisional."
        )
    else:
        monthly_mean = float(monthly["total_spend"].mean())
        monthly_std = float(monthly["total_spend"].std(ddof=0) or 0.0)
        coefficient_of_variation = (
            monthly_std / monthly_mean if monthly_mean > 0 else 0.0
        )
        recent_change = 0.0

        if monthly.iloc[-2]["total_spend"] > 0:
            recent_change = (
                monthly.iloc[-1]["total_spend"]
                - monthly.iloc[-2]["total_spend"]
            ) / monthly.iloc[-2]["total_spend"]

        variability_penalty = min(12.0, coefficient_of_variation * 14)
        growth_penalty = min(
            8.0,
            max(0.0, abs(recent_change) - 0.10) * 16,
        )
        stability_score = round(
            max(0.0, 20 - variability_penalty - growth_penalty),
            1,
        )
        stability_evidence = (
            f"Monthly variability: {coefficient_of_variation:.0%}; "
            f"latest change: {recent_change:+.0%}."
        )

    components.append(
        {
            "component": "Expense stability",
            "score": stability_score,
            "maximum": 20,
            "status": _component_status(stability_score, 20),
            "evidence": stability_evidence,
            "improvement": (
                "Investigate sharp month-to-month changes and large "
                "category increases."
            ),
        }
    )

    # 3. Vendor diversification — 15 points.
    vendor_spend = dataframe.groupby("vendor")["total"].sum()
    largest_vendor_share = (
        float(vendor_spend.max() / vendor_spend.sum())
        if not vendor_spend.empty and vendor_spend.sum() > 0
        else 0.0
    )

    if largest_vendor_share <= 0.25:
        diversification_score = 15.0
    elif largest_vendor_share >= 0.75:
        diversification_score = 0.0
    else:
        diversification_score = round(
            15 * (0.75 - largest_vendor_share) / 0.50,
            1,
        )

    largest_vendor_name = (
        str(vendor_spend.idxmax())
        if not vendor_spend.empty
        else "None"
    )
    components.append(
        {
            "component": "Vendor diversification",
            "score": diversification_score,
            "maximum": 15,
            "status": _component_status(diversification_score, 15),
            "evidence": (
                f"{largest_vendor_name} represents "
                f"{largest_vendor_share:.0%} of recorded spending."
            ),
            "improvement": (
                "Benchmark alternative suppliers when one vendor "
                "dominates spending."
            ),
        }
    )

    # 4. Anomaly control — 15 points.
    anomalies = (
        anomalies
        if anomalies is not None
        else detect_anomalies(dataframe)
    )

    if anomalies.empty:
        anomaly_score = 15.0
        anomaly_evidence = "No open statistical invoice alerts were found."
    else:
        high_count = int(anomalies["risk_level"].eq("High").sum())
        medium_count = int(anomalies["risk_level"].eq("Medium").sum())
        low_count = int(anomalies["risk_level"].eq("Low").sum())
        risk_weight = high_count * 3 + medium_count * 1.5 + low_count * 0.5
        penalty_ratio = min(
            1.0,
            risk_weight / max(3.0, len(dataframe) * 0.30),
        )
        anomaly_score = round(15 * (1 - penalty_ratio), 1)
        anomaly_evidence = (
            f"Open alerts — High: {high_count}, Medium: {medium_count}, "
            f"Low: {low_count}."
        )

    components.append(
        {
            "component": "Anomaly control",
            "score": anomaly_score,
            "maximum": 15,
            "status": _component_status(anomaly_score, 15),
            "evidence": anomaly_evidence,
            "improvement": (
                "Review unusual invoices and record whether each alert "
                "is valid or requires correction."
            ),
        }
    )

    # 5. Record completeness — 15 points.
    required_checks = pd.DataFrame(
        {
            "vendor": dataframe["vendor"].ne("Unknown Vendor"),
            "invoice_number": dataframe["invoice_number"].ne(""),
            "invoice_date": dataframe["invoice_date"].notna(),
            "category": dataframe["category"].ne("Other"),
            "positive_total": dataframe["total"].gt(0),
        }
    )
    core_completeness = float(required_checks.mean().mean())
    gst_completeness = float(dataframe["gst"].ne("").mean())
    completeness_ratio = core_completeness * 0.85 + gst_completeness * 0.15
    completeness_score = round(15 * completeness_ratio, 1)

    components.append(
        {
            "component": "Record completeness",
            "score": completeness_score,
            "maximum": 15,
            "status": _component_status(completeness_score, 15),
            "evidence": (
                f"Core-field completeness: {core_completeness:.0%}; "
                f"GST/tax-field completeness: {gst_completeness:.0%}."
            ),
            "improvement": (
                "Verify missing dates, invoice numbers, categories "
                "and GST details."
            ),
        }
    )

    # 6. Data maturity and OCR quality — 10 points.
    valid_months = int(
        dataframe["invoice_date"]
        .dropna()
        .dt.to_period("M")
        .nunique()
    )
    count_score = min(4.0, len(dataframe) / 5)
    month_score = min(3.0, valid_months)
    ocr_mask = dataframe["extraction_mode"].str.contains(
        "OCR",
        case=False,
        na=False,
    )

    if ocr_mask.any():
        average_ocr_confidence = float(
            dataframe.loc[ocr_mask, "ocr_confidence"].mean()
        )
        ocr_score = min(3.0, max(0.0, average_ocr_confidence * 3))
        ocr_evidence = (
            f"{int(ocr_mask.sum())} OCR-assisted records with "
            f"{average_ocr_confidence:.0%} average text confidence."
        )
    else:
        ocr_score = 1.5
        ocr_evidence = "No OCR-assisted records are available yet."

    maturity_score = round(
        min(10.0, count_score + month_score + ocr_score),
        1,
    )
    components.append(
        {
            "component": "Data maturity",
            "score": maturity_score,
            "maximum": 10,
            "status": _component_status(maturity_score, 10),
            "evidence": (
                f"{len(dataframe)} invoices across {valid_months} month(s). "
                + ocr_evidence
            ),
            "improvement": (
                "Continue capturing verified invoices across more months "
                "to improve forecast reliability."
            ),
        }
    )

    total_score = round(sum(item["score"] for item in components))
    total_score = max(0, min(100, total_score))

    if total_score >= 80:
        status = "Healthy"
    elif total_score >= 60:
        status = "Watch"
    else:
        status = "Attention"

    weakest = sorted(
        components,
        key=lambda item: item["score"] / item["maximum"],
    )[:3]

    return {
        "score": total_score,
        "status": status,
        "components": components,
        "weakest_components": weakest,
        "disclaimer": (
            "Internal prototype indicator based on recorded invoices; "
            "not a credit score or lending decision."
        ),
    }


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

def forecast_expenses(dataframe: pd.DataFrame) -> dict[str, Any]:
    """
    Forecast next-month invoice expense/cash outflow.

    The forecast blends a weighted recent average with a linear trend and
    reports an uncertainty range. It is not a full net cash-flow forecast.
    """
    monthly = monthly_spending(dataframe)

    empty_result = {
        "next_month": None,
        "base_estimate": 0.0,
        "low_estimate": 0.0,
        "high_estimate": 0.0,
        "confidence": 0,
        "historical_error": None,
        "method": "Insufficient data",
        "monthly_history": monthly,
    }

    if monthly.empty:
        return empty_result

    values = monthly["total_spend"].astype(float).to_numpy()
    next_month_timestamp = (
        monthly["month"].max() + pd.offsets.MonthBegin(1)
    )
    number_of_months = len(values)

    if number_of_months == 1:
        base = float(values[-1])
        uncertainty = max(base * 0.20, 1.0)
        confidence = 30
        historical_error = None
        method = "Single-month baseline"

    elif number_of_months == 2:
        recent_average = float(values.mean())
        recent_trend = float(values[-1] - values[-2])
        base = max(0.0, recent_average + recent_trend * 0.35)
        uncertainty = max(abs(recent_trend) * 0.80, base * 0.15, 1.0)
        confidence = 45
        historical_error = None
        method = "Two-month average with moderated trend"

    else:
        recent_values = values[-3:]
        weights = np.array([0.20, 0.30, 0.50])
        weighted_recent_average = float(
            np.average(recent_values, weights=weights)
        )

        x_values = np.arange(number_of_months, dtype=float)
        slope, intercept = np.polyfit(x_values, values, 1)
        trend_projection = max(
            0.0,
            float(intercept + slope * number_of_months),
        )

        base = max(
            0.0,
            weighted_recent_average * 0.70
            + trend_projection * 0.30,
        )

        # Back-test the same three-month weighted-average rule.
        errors: list[float] = []
        for position in range(3, number_of_months):
            predicted = float(
                np.average(
                    values[position - 3:position],
                    weights=weights,
                )
            )
            actual = float(values[position])

            if actual > 0:
                errors.append(abs(predicted - actual) / actual)

        historical_error = (
            float(np.mean(errors))
            if errors
            else None
        )

        recent_std = float(np.std(recent_values, ddof=0))
        error_component = (
            base * historical_error
            if historical_error is not None
            else 0.0
        )
        uncertainty = max(
            recent_std,
            error_component,
            base * 0.12,
            1.0,
        )

        confidence = 55 + min(20, number_of_months * 3)
        if historical_error is not None:
            confidence -= min(30, round(historical_error * 50))
        confidence = max(25, min(90, confidence))
        method = (
            "Weighted recent average blended with linear trend"
        )

    return {
        "next_month": next_month_timestamp.date().isoformat(),
        "base_estimate": round(base, 2),
        "low_estimate": round(max(0.0, base - uncertainty), 2),
        "high_estimate": round(base + uncertainty, 2),
        "confidence": int(confidence),
        "historical_error": (
            round(historical_error, 4)
            if historical_error is not None
            else None
        ),
        "method": method,
        "monthly_history": monthly,
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def generate_recommendations(
    dataframe: pd.DataFrame,
    summary: dict[str, Any],
    anomalies: pd.DataFrame,
    vendors: pd.DataFrame,
    categories: pd.DataFrame,
    health: dict[str, Any],
    forecast: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate prioritised, evidence-based actions."""
    if dataframe.empty:
        return [
            {
                "priority": "Setup",
                "title": "Build a verified invoice history",
                "evidence": "No invoice records are available.",
                "action": (
                    "Upload and verify invoices before relying on financial "
                    "analytics or forecasting."
                ),
                "reviewable_amount": 0.0,
            }
        ]

    recommendations: list[dict[str, Any]] = []

    high_anomalies = anomalies.loc[
        anomalies["risk_level"].eq("High")
    ] if not anomalies.empty else pd.DataFrame()
    medium_anomalies = anomalies.loc[
        anomalies["risk_level"].eq("Medium")
    ] if not anomalies.empty else pd.DataFrame()

    if not high_anomalies.empty:
        reviewable_amount = float(high_anomalies["total"].sum())
        recommendations.append(
            {
                "priority": "High",
                "title": "Review high-risk invoice anomalies",
                "evidence": (
                    f"{len(high_anomalies)} high-risk alert(s) represent "
                    f"₹{reviewable_amount:,.0f}."
                ),
                "action": (
                    "Compare each alert with purchase orders, vendor history "
                    "and approved tax treatment."
                ),
                "reviewable_amount": reviewable_amount,
            }
        )
    elif not medium_anomalies.empty:
        reviewable_amount = float(medium_anomalies["total"].sum())
        recommendations.append(
            {
                "priority": "Medium",
                "title": "Review unusual invoice patterns",
                "evidence": (
                    f"{len(medium_anomalies)} medium-risk alert(s) represent "
                    f"₹{reviewable_amount:,.0f}."
                ),
                "action": (
                    "Confirm whether the amount, tax rate or vendor pattern "
                    "has a valid business explanation."
                ),
                "reviewable_amount": reviewable_amount,
            }
        )

    overdue_amount = float(summary["overdue_amount"])
    if overdue_amount > 0:
        recommendations.append(
            {
                "priority": "High",
                "title": "Resolve overdue payment exposure",
                "evidence": f"₹{overdue_amount:,.0f} is marked overdue.",
                "action": (
                    "Verify due dates, prioritise critical vendors and record "
                    "a payment plan."
                ),
                "reviewable_amount": overdue_amount,
            }
        )

    if not vendors.empty:
        top_vendor = vendors.iloc[0]
        if float(top_vendor["spend_share"]) >= 0.40:
            recommendations.append(
                {
                    "priority": "Medium",
                    "title": "Reduce supplier concentration risk",
                    "evidence": (
                        f"{top_vendor['vendor']} represents "
                        f"{float(top_vendor['spend_share']):.0%} of spend."
                    ),
                    "action": (
                        "Benchmark alternative suppliers and negotiate "
                        "volume-linked pricing or backup supply."
                    ),
                    "reviewable_amount": float(top_vendor["total_spend"]),
                }
            )

    if not categories.empty:
        top_category = categories.iloc[0]
        if float(top_category["spend_share"]) >= 0.35:
            recommendations.append(
                {
                    "priority": "Medium",
                    "title": "Review the largest expense category",
                    "evidence": (
                        f"{top_category['category']} represents "
                        f"{float(top_category['spend_share']):.0%} "
                        "of recorded spend."
                    ),
                    "action": (
                        "Inspect the category's largest invoices and compare "
                        "supplier rates before the next purchasing cycle."
                    ),
                    "reviewable_amount": float(top_category["total_spend"]),
                }
            )

        growing = categories.loc[
            categories["monthly_change"].notna()
            & (categories["monthly_change"] >= 0.20)
        ]
        if not growing.empty:
            fastest = growing.sort_values(
                "monthly_change",
                ascending=False,
            ).iloc[0]

            recommendations.append(
                {
                    "priority": "Medium",
                    "title": "Investigate rapid category growth",
                    "evidence": (
                        f"{fastest['category']} increased "
                        f"{float(fastest['monthly_change']):.0%} "
                        "versus the previous recorded month."
                    ),
                    "action": (
                        "Review volume changes, unit prices and one-off "
                        "purchases driving the increase."
                    ),
                    "reviewable_amount": float(
                        fastest["latest_month_spend"]
                    ),
                }
            )

    for weak_component in health.get("weakest_components", [])[:2]:
        component_name = weak_component["component"]
        if any(
            recommendation["title"].casefold().find(
                component_name.casefold()
            ) >= 0
            for recommendation in recommendations
        ):
            continue

        recommendations.append(
            {
                "priority": "Improvement",
                "title": f"Improve {component_name.lower()}",
                "evidence": weak_component["evidence"],
                "action": weak_component["improvement"],
                "reviewable_amount": 0.0,
            }
        )

    if forecast["confidence"] < 55:
        recommendations.append(
            {
                "priority": "Data",
                "title": "Increase forecast reliability",
                "evidence": (
                    f"Current forecast confidence is "
                    f"{forecast['confidence']}%."
                ),
                "action": (
                    "Capture verified invoices consistently across at least "
                    "three to six months."
                ),
                "reviewable_amount": 0.0,
            }
        )

    priority_order = {
        "High": 0,
        "Medium": 1,
        "Improvement": 2,
        "Data": 3,
        "Setup": 4,
    }

    return sorted(
        recommendations,
        key=lambda item: priority_order.get(item["priority"], 99),
    )[:8]


# ---------------------------------------------------------------------------
# Complete analysis and grounded Q&A
# ---------------------------------------------------------------------------

def analyse_finances(
    rows: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Run the complete FinTech AI intelligence pipeline.

    Pass rows only for testing. In the real application, call with no argument
    so the function reads the verified local SQLite invoice database.
    """
    dataframe = (
        prepare_invoice_dataframe(rows)
        if rows is not None
        else load_invoice_dataframe()
    )

    summary = financial_summary(dataframe)
    monthly = monthly_spending(dataframe)
    categories = category_intelligence(dataframe)
    anomalies = detect_anomalies(dataframe)
    vendors = vendor_intelligence(dataframe, anomalies)
    health = calculate_health_score(dataframe, anomalies)
    forecast = forecast_expenses(dataframe)
    recommendations = generate_recommendations(
        dataframe=dataframe,
        summary=summary,
        anomalies=anomalies,
        vendors=vendors,
        categories=categories,
        health=health,
        forecast=forecast,
    )

    return {
        "has_data": not dataframe.empty,
        "dataframe": dataframe,
        "summary": summary,
        "monthly": monthly,
        "categories": categories,
        "anomalies": anomalies,
        "vendors": vendors,
        "health": health,
        "forecast": forecast,
        "recommendations": recommendations,
    }


# American-spelling alias for convenience.
analyze_finances = analyse_finances


def answer_finance_question(
    question: str,
    analysis: dict[str, Any] | None = None,
) -> str:
    """
    Answer common finance questions using only the local analysis result.

    This is a grounded conversational analytics layer, not a general-purpose
    language model. It will not invent figures that are absent from the data.
    """
    analysis = analysis or analyse_finances()
    question_text = (question or "").strip().casefold()

    if not analysis["has_data"]:
        return (
            "No verified invoices are available yet. Upload an invoice or "
            "load synthetic demo data before asking financial questions."
        )

    summary = analysis["summary"]
    vendors = analysis["vendors"]
    categories = analysis["categories"]
    anomalies = analysis["anomalies"]
    health = analysis["health"]
    forecast = analysis["forecast"]
    recommendations = analysis["recommendations"]

    if any(term in question_text for term in ["total spend", "spent", "expense total"]):
        return (
            f"Recorded spending is ₹{summary['total_spend']:,.0f} across "
            f"{summary['invoice_count']} invoice(s)."
        )

    if "overdue" in question_text:
        return (
            f"₹{summary['overdue_amount']:,.0f} is currently marked overdue."
        )

    if "pending" in question_text:
        return (
            f"₹{summary['pending_amount']:,.0f} is currently marked pending."
        )

    if any(term in question_text for term in ["top vendor", "highest vendor", "most money", "largest vendor"]):
        if vendors.empty:
            return "No vendor profile is available."
        top = vendors.iloc[0]
        return (
            f"{top['vendor']} has the highest recorded spend at "
            f"₹{float(top['total_spend']):,.0f}, representing "
            f"{float(top['spend_share']):.0%} of total spending."
        )

    if any(term in question_text for term in ["top category", "highest category", "largest category", "where am i spending"]):
        if categories.empty:
            return "No expense category analysis is available."
        top = categories.iloc[0]
        return (
            f"{top['category']} is the largest category at "
            f"₹{float(top['total_spend']):,.0f}, or "
            f"{float(top['spend_share']):.0%} of recorded spending."
        )

    if any(term in question_text for term in ["unusual", "anomaly", "suspicious", "risk invoice"]):
        if anomalies.empty:
            return (
                "No statistical invoice alerts are currently open. "
                "This does not guarantee that every invoice is correct."
            )
        high_count = int(anomalies["risk_level"].eq("High").sum())
        medium_count = int(anomalies["risk_level"].eq("Medium").sum())
        first = anomalies.iloc[0]
        return (
            f"There are {high_count} high-risk and {medium_count} medium-risk "
            f"alert(s). The highest-ranked alert is "
            f"{first['vendor']} / {first['invoice_number']}: "
            f"{first['reasons']}"
        )

    if any(term in question_text for term in ["health", "score", "financial condition"]):
        weakest = health.get("weakest_components", [])
        explanation = (
            weakest[0]["evidence"]
            if weakest
            else "No major weakness is currently identified."
        )
        return (
            f"The internal prototype financial-health score is "
            f"{health['score']}/100 ({health['status']}). "
            f"The weakest evidence is: {explanation}"
        )

    if any(term in question_text for term in ["forecast", "next month", "future expense", "cash outflow"]):
        if forecast["next_month"] is None:
            return "There is not enough dated invoice history to make a forecast."
        return (
            f"The next-month invoice-expense estimate is "
            f"₹{forecast['base_estimate']:,.0f}. The current uncertainty "
            f"range is ₹{forecast['low_estimate']:,.0f} to "
            f"₹{forecast['high_estimate']:,.0f}, with "
            f"{forecast['confidence']}% model confidence."
        )

    if any(term in question_text for term in ["recommend", "what should", "action", "do first"]):
        if not recommendations:
            return "No prioritised recommendation is available."
        first = recommendations[0]
        return (
            f"{first['priority']} priority — {first['title']}. "
            f"{first['evidence']} Recommended action: {first['action']}"
        )

    # Vendor-name lookup.
    for _, vendor_row in vendors.iterrows():
        vendor_name = str(vendor_row["vendor"])
        if vendor_name.casefold() in question_text:
            return (
                f"{vendor_name} has {int(vendor_row['invoice_count'])} "
                f"invoice(s), ₹{float(vendor_row['total_spend']):,.0f} "
                f"in recorded spend, a vendor score of "
                f"{int(vendor_row['vendor_score'])}/100 and "
                f"{vendor_row['dependency_risk'].lower()} dependency risk."
            )

    return (
        "I can answer grounded questions about total spend, pending or overdue "
        "amounts, top vendors, top categories, unusual invoices, the health "
        "score, the next-month forecast and recommended actions."
    )


# ---------------------------------------------------------------------------
# Local self-test
# ---------------------------------------------------------------------------

def _build_self_test_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    vendors = [
        ("Alpha Packaging", "Raw Materials", 18000.0),
        ("Metro Logistics", "Transport", 9500.0),
        ("City Power", "Utilities", 6200.0),
    ]

    identifier = 1
    for month in range(1, 7):
        for vendor, category, base_amount in vendors:
            amount = base_amount * (1 + month * 0.025)
            subtotal = amount / 1.18
            tax = amount - subtotal

            rows.append(
                {
                    "id": identifier,
                    "vendor": vendor,
                    "invoice_number": f"TEST-{identifier:03d}",
                    "invoice_date": f"2026-{month:02d}-10",
                    "gst": f"TESTGST{identifier:03d}",
                    "category": category,
                    "subtotal": subtotal,
                    "tax": tax,
                    "total": amount,
                    "status": "Paid" if identifier % 5 else "Pending",
                    "ocr_confidence": 0.91,
                    "extraction_mode": "RapidOCR + human verification",
                }
            )
            identifier += 1

    # Deliberate high-value invoice for anomaly testing.
    rows.append(
        {
            "id": identifier,
            "vendor": "Alpha Packaging",
            "invoice_number": "TEST-ANOMALY",
            "invoice_date": "2026-06-22",
            "gst": "TESTGST999",
            "category": "Raw Materials",
            "subtotal": 135000.0,
            "tax": 24300.0,
            "total": 159300.0,
            "status": "Overdue",
            "ocr_confidence": 0.89,
            "extraction_mode": "RapidOCR + human verification",
        }
    )

    return rows


def run_self_test() -> None:
    """Run a small deterministic test without touching the user's database."""
    analysis = analyse_finances(_build_self_test_rows())

    assert analysis["has_data"] is True
    assert analysis["summary"]["invoice_count"] == 19
    assert "invoice_date" in analysis["dataframe"].columns
    assert not analysis["monthly"].empty
    assert not analysis["vendors"].empty
    assert analysis["health"]["score"] >= 0
    assert analysis["forecast"]["base_estimate"] > 0
    assert not analysis["anomalies"].empty
    assert analysis["recommendations"]

    print("FinTech AI engine self-test passed.")
    print(
        f"Health score: {analysis['health']['score']}/100 "
        f"({analysis['health']['status']})"
    )
    print(
        f"Anomaly alerts: {len(analysis['anomalies'])}; "
        f"next-month estimate: "
        f"₹{analysis['forecast']['base_estimate']:,.0f}"
    )


if __name__ == "__main__":
    run_self_test()