from __future__ import annotations

from datetime import date, timedelta

from database import add_invoice


def load_sample_data() -> tuple[int, int]:
    """Insert anonymous synthetic demo records. Safe to repeat."""
    today = date.today()

    records = [
        ("Alpha Packaging", "DEMO-001", 165, "Raw Materials", 42000, 7560, "Paid"),
        ("City Power Services", "DEMO-002", 145, "Utilities", 13500, 2430, "Paid"),
        ("Metro Logistics", "DEMO-003", 123, "Transport", 18500, 3330, "Paid"),
        ("Alpha Packaging", "DEMO-004", 105, "Raw Materials", 48000, 8640, "Paid"),
        ("Workspace Rentals", "DEMO-005", 92, "Rent", 55000, 9900, "Paid"),
        ("Digital Reach Studio", "DEMO-006", 75, "Marketing", 16000, 2880, "Pending"),
        ("City Power Services", "DEMO-007", 61, "Utilities", 14800, 2664, "Paid"),
        ("Prime Machines", "DEMO-008", 44, "Equipment", 85000, 15300, "Pending"),
        ("Metro Logistics", "DEMO-009", 30, "Transport", 22800, 4104, "Paid"),
        ("Alpha Packaging", "DEMO-010", 21, "Raw Materials", 52000, 9360, "Pending"),
        ("Office Mart", "DEMO-011", 12, "Office Expenses", 9200, 1656, "Paid"),
        ("Rapid Repair Works", "DEMO-012", 4, "Maintenance", 27000, 4860, "Overdue"),
    ]

    added = 0
    skipped = 0

    for (
        vendor,
        number,
        days_ago,
        category,
        subtotal,
        tax,
        status,
    ) in records:
        success, _ = add_invoice(
            {
                "vendor": vendor,
                "invoice_number": number,
                "invoice_date": (
                    today - timedelta(days=days_ago)
                ).isoformat(),
                "gst": f"DEMO-TAX-{number[-3:]}",
                "category": category,
                "subtotal": subtotal,
                "tax": tax,
                "total": subtotal + tax,
                "status": status,
                "file_name": "",
                "file_path": "",
                "file_hash": "",
                "ocr_text": "",
                "ocr_confidence": 0,
                "ocr_seconds": 0,
                "extraction_mode": "Synthetic demo",
                "remember_vendor": True,
            }
        )

        if success:
            added += 1
        else:
            skipped += 1

    return added, skipped
