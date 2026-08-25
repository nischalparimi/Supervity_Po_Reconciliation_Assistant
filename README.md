# PO Reconciliation Assistant

A production-quality, chat-based **Purchase Order reconciliation tool** for enterprise procurement teams. Ask natural-language questions about purchase orders, goods receipts, and invoices — the system translates them into SQL queries against a live SQLite database and returns auditable, source-grounded answers.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  React Frontend (Vite)                          │
│  ┌──────────────────┐  ┌──────────────────────┐ │
│  │  Chat Panel      │  │  Data Panel          │ │
│  │  (query assistant│  │  (PO table, live     │ │
│  │  + SQL expander) │  │  mismatch flags)     │ │
│  └──────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────┘
                    │ HTTP (REST)
┌─────────────────────────────────────────────────┐
│  FastAPI Backend                                │
│  ┌──────────────────────────────────────────┐   │
│  │  LangGraph Agent                         │   │
│  │  User Question → LLM (GPT-4o) →         │   │
│  │  run_sql_query tool → SQLite execute →   │   │
│  │  LLM formats answer                      │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  SQLite DB (po_reconciliation.db)        │   │
│  │  Tables: purchase_orders, receipts       │   │
│  │  View:   reconciliation                  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenAI API key with access to `gpt-4o` (or `gpt-4-turbo`)

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
# Load .env
set -a && source ../.env && set +a   # Linux/Mac
# or on Windows PowerShell:
# Get-Content ..\.env | ForEach-Object { if ($_ -match '^([^#][^=]*)=(.*)$') { [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim()) } }

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The SQLite database is created automatically at startup by loading the CSVs from `/data`.

### 3. Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
# Open http://localhost:5173
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/chat` | POST | NL question → answer + SQL + rows |
| `/summary` | GET | Dashboard stats (totals, flagged value) |
| `/pos` | GET | Full reconciliation view (filterable) |
| `/duplicate-invoices` | GET | Invoice numbers appearing >1 time |

### `/chat` request/response

```json
// Request
{ "question": "Which POs have unmatched receipts over $1,000?" }

// Response
{
  "answer": "There are 8 POs with invoice totals exceeding $1,000 that do not reconcile...",
  "sql": "SELECT po_number, vendor, total_invoiced, reconciliation_status FROM reconciliation WHERE total_invoiced > 1000 AND reconciliation_status != 'Matched'",
  "rows": [...],
  "columns": ["po_number", "vendor", "total_invoiced", "reconciliation_status"],
  "row_count": 8
}
```

---

## Sample Questions to Try

1. **"Which POs have unmatched receipts with invoices over $1,000?"**
2. **"Show all quantity mismatches"**
3. **"Are there any duplicate invoice numbers?"**
4. **"What is the total invoice variance for Grainger across all POs?"**
5. **"Which POs are still pending receipt?"**
6. **"Show all partially received POs and their shortfall quantities"**
7. **"What is the total value of all flagged POs?"**
8. **"Which vendor has the most mismatches?"**
9. **"Show POs where we were over-invoiced"**
10. **"What's the largest single invoice discrepancy?"**

---

## Data Scenarios in the Mock Dataset

The CSVs were hand-crafted with deliberate anomalies for realistic reconciliation testing:

| Scenario | Examples |
|---|---|
| Exact matches | PO-2024-0004, PO-2024-0037 |
| Quantity shortfall | PO-2024-0002 (15 ordered, 13 received across 2 receipts) |
| Partially received | PO-2024-0011, PO-2024-0019, PO-2024-0030, PO-2024-0045 |
| Missing receipts | PO-2024-0005, 0008, 0014, 0020, 0025, 0032, 0035, 0041, 0047 |
| Amount mismatch >$1k | PO-2024-0006 (duplicate receipt row), PO-2024-0034, PO-2024-0043 |
| Duplicate invoices | INV-GRN-2293, INV-CNT-2281, INV-HP-5503, INV-3M-779x |

---

## Design Tradeoff: SQLite over Raw Pandas In-Memory Filtering

**The chosen approach** loads both CSVs into a SQLite database at startup and routes every data question through a SQL query executed against that database.

**The alternative** would be to load DataFrames into memory with pandas and have the LLM generate pandas filtering code (or use a hybrid approach like PandasAI).

**Why SQL/SQLite was chosen:**

1. **Auditability**: Every answer produced by the agent is backed by an exact, logged SQL statement that can be reproduced, reviewed, or audited independently of the LLM. The `/chat` response always includes the SQL that was run. With pandas, the "query" would be opaque Python code that is harder to audit in a finance/procurement context.

2. **Closer to production**: Real enterprise procurement data lives in relational systems (SAP, Oracle ERP, NetSuite). Using SQL as the query layer means the same agent architecture can be pointed at a production Postgres or SQL Server database with near-zero changes — just swap the connection string. Pandas DataFrames are a dead end for production scale.

3. **Correctness for aggregation**: SQL's declarative GROUP BY / HAVING / JOIN semantics are unambiguous and well-tested. LLM-generated pandas is prone to silent bugs (e.g., wrong merge keys, mishandled NaN values) that are hard to detect without running the code against known test cases.

4. **The reconciliation VIEW**: By defining a `reconciliation` view in SQLite, the agent can use a single clean abstraction that encapsulates the join, aggregation, and status derivation logic — reducing the surface area for SQL generation errors.

**Trade-off accepted**: For a prototype with <10k rows, SQLite adds no meaningful latency. For true production scale (millions of rows), you'd replace SQLite with a real RDBMS and add connection pooling, but the agent layer remains unchanged.

---

## Repo Structure

```
/
├── backend/
│   ├── main.py          # FastAPI app, endpoints, lifespan
│   ├── agent.py         # LangGraph agent, SQL tool, system prompt
│   ├── db.py            # SQLite loader, schema, execute_query
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css    # Full enterprise design system
│   │   ├── api.js       # Backend API client
│   │   └── components/
│   │       ├── DashboardHeader.jsx
│   │       ├── ChatPanel.jsx
│   │       ├── MessageBubble.jsx
│   │       ├── SqlExpander.jsx
│   │       └── DataPanel.jsx
│   ├── vite.config.js
│   └── package.json
├── data/
│   ├── purchase_orders.csv
│   ├── receipts.csv
│   └── generate_data.py
├── .env.example
└── README.md
```
