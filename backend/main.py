"""
main.py — FastAPI application for PO Reconciliation Assistant.
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import execute_query, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database...")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PO Reconciliation Assistant API",
    version="1.0.0",
    description="Chat-based Purchase Order reconciliation tool backed by LangGraph + SQLite.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int


class SummaryStats(BaseModel):
    total_pos: int
    total_matched: int
    total_mismatched: int
    total_missing_receipt: int
    flagged_value: float
    total_po_value: float
    total_invoiced: float


class PORow(BaseModel):
    po_number: str
    vendor: str
    item: str
    quantity_ordered: int
    unit_price: float
    total_value: float
    order_date: str
    status: str
    total_qty_received: int
    total_invoiced: float
    receipt_count: int
    qty_shortfall: int
    invoice_variance: float
    reconciliation_status: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Accept a natural-language question about PO reconciliation.
    Returns the answer, the SQL that was executed, and the raw result rows.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Lazy import to avoid loading LangGraph/OpenAI at module level during health checks
    try:
        from agent import ask
        result = ask(request.question.strip())
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(exc)}")

    return ChatResponse(
        answer=result.answer,
        sql=result.sql,
        rows=result.rows,
        columns=result.columns,
        row_count=len(result.rows),
    )


@app.get("/summary", response_model=SummaryStats)
def get_summary():
    """Dashboard summary statistics computed directly from SQLite."""
    rows, _ = execute_query("""
        SELECT
            COUNT(*)                                                            AS total_pos,
            SUM(CASE WHEN reconciliation_status = 'Matched' THEN 1 ELSE 0 END) AS total_matched,
            SUM(CASE WHEN reconciliation_status != 'Matched'
                      AND reconciliation_status != 'Missing Receipt' THEN 1 ELSE 0 END) AS total_mismatched,
            SUM(CASE WHEN reconciliation_status = 'Missing Receipt' THEN 1 ELSE 0 END) AS total_missing_receipt,
            ROUND(SUM(CASE WHEN reconciliation_status != 'Matched'
                      THEN po_total_value ELSE 0 END), 2)                       AS flagged_value,
            ROUND(SUM(po_total_value), 2)                                       AS total_po_value,
            ROUND(SUM(total_invoiced), 2)                                       AS total_invoiced
        FROM reconciliation
    """)
    r = rows[0] if rows else {}
    return SummaryStats(
        total_pos=r.get("total_pos", 0),
        total_matched=r.get("total_matched", 0),
        total_mismatched=r.get("total_mismatched", 0),
        total_missing_receipt=r.get("total_missing_receipt", 0),
        flagged_value=r.get("flagged_value", 0.0),
        total_po_value=r.get("total_po_value", 0.0),
        total_invoiced=r.get("total_invoiced", 0.0),
    )


@app.get("/pos", response_model=list[PORow])
def get_pos(status: str | None = None, vendor: str | None = None):
    """
    Return the full reconciliation view, optionally filtered by
    reconciliation_status or vendor name (partial, case-insensitive match).
    """
    where_clauses = []
    if status:
        where_clauses.append(f"reconciliation_status = '{status}'")
    if vendor:
        safe_vendor = vendor.replace("'", "''")
        where_clauses.append(f"LOWER(vendor) LIKE LOWER('%{safe_vendor}%')")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT
            po_number,
            vendor,
            po_item AS item,
            quantity_ordered,
            unit_price,
            po_total_value AS total_value,
            order_date,
            status,
            total_qty_received,
            total_invoiced,
            receipt_count,
            qty_shortfall,
            invoice_variance,
            reconciliation_status
        FROM reconciliation
        {where_sql}
        ORDER BY po_number
    """
    rows, _ = execute_query(sql)
    return [PORow(**r) for r in rows]


@app.get("/duplicate-invoices")
def get_duplicate_invoices():
    """Return invoice numbers that appear more than once in the receipts table."""
    rows, cols = execute_query("""
        SELECT invoice_number, COUNT(*) AS occurrence_count,
               GROUP_CONCAT(po_number, ', ') AS po_numbers,
               ROUND(SUM(invoice_amount), 2) AS total_amount
        FROM receipts
        GROUP BY invoice_number
        HAVING COUNT(*) > 1
        ORDER BY occurrence_count DESC
    """)
    return {"duplicate_invoices": rows, "count": len(rows)}
