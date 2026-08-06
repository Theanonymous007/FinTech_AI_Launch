from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = DATABASE_DIR / "finance.db"


def get_connection() -> sqlite3.Connection:
    """Open the local SQLite database."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _add_missing_columns(
    connection: sqlite3.Connection,
    table_name: str,
    migrations: dict[str, str],
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    for column_name, definition in migrations.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {definition}"
            )


def create_database() -> None:
    """Create or safely upgrade the local prototype database."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                gst TEXT DEFAULT '',
                category TEXT NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pending',
                file_name TEXT DEFAULT '',
                file_path TEXT DEFAULT '',
                file_hash TEXT DEFAULT '',
                ocr_text TEXT DEFAULT '',
                ocr_confidence REAL DEFAULT 0,
                ocr_seconds REAL DEFAULT 0,
                extraction_mode TEXT DEFAULT 'Manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Upgrade a Version 1 finance.db without deleting existing records.
        _add_missing_columns(
            connection,
            "invoices",
            {
                "file_name": "TEXT DEFAULT ''",
                "file_path": "TEXT DEFAULT ''",
                "file_hash": "TEXT DEFAULT ''",
                "ocr_text": "TEXT DEFAULT ''",
                "ocr_confidence": "REAL DEFAULT 0",
                "ocr_seconds": "REAL DEFAULT 0",
                "extraction_mode": "TEXT DEFAULT 'Manual'",
                "created_at": "TEXT DEFAULT ''",
            },
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_memory (
                vendor_key TEXT PRIMARY KEY,
                vendor_name TEXT NOT NULL,
                gst TEXT DEFAULT '',
                preferred_category TEXT DEFAULT 'Other',
                times_seen INTEGER DEFAULT 1,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_date "
            "ON invoices(invoice_date)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_vendor "
            "ON invoices(vendor)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_category "
            "ON invoices(category)"
        )


def normalise_vendor_key(vendor_name: str) -> str:
    """Build a stable key for correction-driven vendor memory."""
    return re.sub(r"[^a-z0-9]+", "", vendor_name.casefold())


def find_duplicate(
    vendor: str,
    invoice_number: str,
    file_hash: str | None = None,
) -> dict[str, Any] | None:
    """Find a duplicate by vendor/number or exact document fingerprint."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE lower(trim(vendor)) = lower(trim(?))
              AND lower(trim(invoice_number)) = lower(trim(?))
            LIMIT 1
            """,
            (vendor, invoice_number),
        ).fetchone()

        if row is not None:
            return dict(row)

        if file_hash:
            row = connection.execute(
                """
                SELECT *
                FROM invoices
                WHERE file_hash = ?
                LIMIT 1
                """,
                (file_hash,),
            ).fetchone()

            if row is not None:
                return dict(row)

    return None


def get_vendor_memory(vendor_name: str) -> dict[str, Any] | None:
    vendor_key = normalise_vendor_key(vendor_name)
    if not vendor_key:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM vendor_memory
            WHERE vendor_key = ?
            LIMIT 1
            """,
            (vendor_key,),
        ).fetchone()

    return dict(row) if row is not None else None


def remember_vendor(
    vendor_name: str,
    gst: str,
    preferred_category: str,
) -> None:
    """Store verified corrections for recurring vendors."""
    vendor_key = normalise_vendor_key(vendor_name)
    if not vendor_key:
        return

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT times_seen
            FROM vendor_memory
            WHERE vendor_key = ?
            """,
            (vendor_key,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO vendor_memory (
                    vendor_key,
                    vendor_name,
                    gst,
                    preferred_category,
                    times_seen,
                    last_updated
                )
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """,
                (
                    vendor_key,
                    vendor_name.strip(),
                    gst.strip(),
                    preferred_category,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE vendor_memory
                SET vendor_name = ?,
                    gst = ?,
                    preferred_category = ?,
                    times_seen = times_seen + 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE vendor_key = ?
                """,
                (
                    vendor_name.strip(),
                    gst.strip(),
                    preferred_category,
                    vendor_key,
                ),
            )


def get_all_vendor_memory() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT vendor_name, gst, preferred_category,
                   times_seen, last_updated
            FROM vendor_memory
            ORDER BY times_seen DESC, vendor_name ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def add_invoice(invoice: dict[str, Any]) -> tuple[bool, str]:
    """Insert one verified invoice and return (success, message)."""
    duplicate = find_duplicate(
        invoice["vendor"],
        invoice["invoice_number"],
        invoice.get("file_hash"),
    )
    if duplicate is not None:
        return (
            False,
            "Possible duplicate detected: "
            f"record #{duplicate['id']} already uses this "
            "invoice number or document.",
        )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO invoices (
                    vendor,
                    invoice_number,
                    invoice_date,
                    gst,
                    category,
                    subtotal,
                    tax,
                    total,
                    status,
                    file_name,
                    file_path,
                    file_hash,
                    ocr_text,
                    ocr_confidence,
                    ocr_seconds,
                    extraction_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice["vendor"].strip(),
                    invoice["invoice_number"].strip(),
                    invoice["invoice_date"],
                    invoice.get("gst", "").strip(),
                    invoice["category"],
                    float(invoice["subtotal"]),
                    float(invoice["tax"]),
                    float(invoice["total"]),
                    invoice["status"],
                    invoice.get("file_name", ""),
                    invoice.get("file_path", ""),
                    invoice.get("file_hash", ""),
                    invoice.get("ocr_text", ""),
                    float(invoice.get("ocr_confidence", 0)),
                    float(invoice.get("ocr_seconds", 0)),
                    invoice.get("extraction_mode", "Manual"),
                ),
            )
            invoice_id = cursor.lastrowid

        if invoice.get("remember_vendor", True):
            remember_vendor(
                invoice["vendor"],
                invoice.get("gst", ""),
                invoice["category"],
            )

        return True, f"Invoice saved successfully as record #{invoice_id}."

    except (sqlite3.Error, KeyError, TypeError, ValueError) as error:
        return False, f"The invoice could not be saved: {error}"


def get_all_invoices() -> list[dict[str, Any]]:
    """Return every invoice, newest first."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM invoices
            ORDER BY date(invoice_date) DESC, id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def clear_all_invoices(clear_vendor_memory: bool = False) -> None:
    """Remove prototype records after explicit user confirmation."""
    with get_connection() as connection:
        connection.execute("DELETE FROM invoices")

        if clear_vendor_memory:
            connection.execute("DELETE FROM vendor_memory")
