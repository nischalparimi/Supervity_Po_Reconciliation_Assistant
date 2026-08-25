"""
db.py — SQLite loader for PO Reconciliation Assistant.
Loads purchase_orders.csv and receipts.csv into SQLite at startup.
"""
import sqlite3
import csv
import os
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "./po_reconciliation.db")
DATA_DIR = Path(__file__).parent.parent / "data"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and load CSV data into SQLite."""
    conn = get_connection()
    cur = conn.cursor()

    # ── Purchase Orders table ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_number       TEXT NOT NULL,
            vendor          TEXT NOT NULL,
            item            TEXT NOT NULL,
            quantity_ordered INTEGER NOT NULL,
            unit_price      REAL NOT NULL,
            order_date      TEXT NOT NULL,
            status          TEXT NOT NULL,
            total_value     REAL GENERATED ALWAYS AS (quantity_ordered * unit_price) STORED,
            PRIMARY KEY (po_number)
        )
    """)

    # ── Receipts table ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number        TEXT NOT NULL,
            item             TEXT NOT NULL,
            quantity_received INTEGER NOT NULL,
            invoice_amount   REAL NOT NULL,
            receipt_date     TEXT NOT NULL,
            invoice_number   TEXT NOT NULL
        )
    """)

    # ── Reconciliation view ────────────────────────────────────────────────────
    cur.execute("""
        CREATE VIEW IF NOT EXISTS reconciliation AS
        SELECT
            po.po_number,
            po.vendor,
            po.item                                                  AS po_item,
            po.quantity_ordered,
            po.unit_price,
            po.total_value                                           AS po_total_value,
            po.order_date,
            po.status,
            COALESCE(SUM(r.quantity_received), 0)                    AS total_qty_received,
            COALESCE(SUM(r.invoice_amount), 0)                       AS total_invoiced,
            COUNT(r.id)                                              AS receipt_count,
            po.quantity_ordered - COALESCE(SUM(r.quantity_received), 0) AS qty_shortfall,
            ROUND(COALESCE(SUM(r.invoice_amount), 0) - po.total_value, 2) AS invoice_variance,
            CASE
                WHEN COUNT(r.id) = 0 THEN 'Missing Receipt'
                WHEN po.quantity_ordered != COALESCE(SUM(r.quantity_received), 0)
                     AND ABS(COALESCE(SUM(r.invoice_amount), 0) - po.total_value) > 0.01
                     THEN 'Qty & Amount Mismatch'
                WHEN po.quantity_ordered != COALESCE(SUM(r.quantity_received), 0)
                     THEN 'Quantity Mismatch'
                WHEN ABS(COALESCE(SUM(r.invoice_amount), 0) - po.total_value) > 0.01
                     THEN 'Amount Mismatch'
                ELSE 'Matched'
            END AS reconciliation_status
        FROM purchase_orders po
        LEFT JOIN receipts r ON po.po_number = r.po_number
        GROUP BY po.po_number
    """)

    # Only load if tables are empty (idempotent startup)
    if cur.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0] == 0:
        _load_csv(cur, DATA_DIR / "purchase_orders.csv", "purchase_orders",
                  ["po_number", "vendor", "item", "quantity_ordered", "unit_price", "order_date", "status"])

    if cur.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 0:
        _load_csv(cur, DATA_DIR / "receipts.csv", "receipts",
                  ["po_number", "item", "quantity_received", "invoice_amount", "receipt_date", "invoice_number"])

    conn.commit()
    conn.close()
    print(f"[DB] SQLite initialised at {DB_PATH}")


def _load_csv(cur: sqlite3.Cursor, csv_path: Path, table: str, columns: list[str]) -> None:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(columns)
        rows = []
        for row in reader:
            rows.append(tuple(row[c] for c in columns))
        cur.executemany(
            f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})",
            rows,
        )
    print(f"[DB] Loaded {len(rows)} rows into '{table}' from {csv_path.name}")


def execute_query(sql: str) -> tuple[list[dict], list[str]]:
    """Execute a read-only SQL query, return (rows_as_dicts, column_names)."""
    # Basic safety: only allow SELECT statements
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        raise ValueError("Only SELECT queries are permitted.")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return rows, cols
    finally:
        conn.close()


def get_schema_info() -> str:
    """Return schema description for the LLM system prompt."""
    return """
SQLite database with the following tables and view:

TABLE: purchase_orders
  po_number       TEXT PRIMARY KEY   -- e.g. PO-2024-0001
  vendor          TEXT               -- supplier company name
  item            TEXT               -- description of ordered item
  quantity_ordered INTEGER           -- number of units ordered
  unit_price      REAL               -- price per unit in USD
  order_date      TEXT               -- ISO date YYYY-MM-DD
  status          TEXT               -- 'Fully Received', 'Partially Received', 'Pending Receipt'
  total_value     REAL               -- computed: quantity_ordered * unit_price

TABLE: receipts
  id               INTEGER PRIMARY KEY AUTOINCREMENT
  po_number        TEXT              -- references purchase_orders.po_number
  item             TEXT              -- item description on the receipt
  quantity_received INTEGER          -- units actually received
  invoice_amount   REAL              -- total amount on the invoice (USD)
  receipt_date     TEXT              -- ISO date YYYY-MM-DD
  invoice_number   TEXT              -- vendor invoice reference, may have duplicates

VIEW: reconciliation
  (Joins purchase_orders LEFT JOIN receipts, aggregates per PO)
  po_number, vendor, po_item, quantity_ordered, unit_price, po_total_value,
  order_date, status,
  total_qty_received   -- SUM of quantity_received across all receipts for this PO
  total_invoiced       -- SUM of invoice_amount across all receipts for this PO
  receipt_count        -- number of receipt rows for this PO
  qty_shortfall        -- quantity_ordered - total_qty_received
  invoice_variance     -- total_invoiced - po_total_value (positive = over-invoiced)
  reconciliation_status -- 'Matched', 'Quantity Mismatch', 'Amount Mismatch',
                         --  'Qty & Amount Mismatch', 'Missing Receipt'

NOTES:
- Use the 'reconciliation' view for most reconciliation questions.
- Duplicate invoice_number values in receipts indicate potentially duplicate invoices.
- invoice_variance > 0 means vendor charged MORE than the PO value.
- qty_shortfall > 0 means fewer units were received than ordered.
- Dates are stored as TEXT in ISO format; use date comparison operators directly.
"""
