"""
agent.py — LangGraph agent for PO Reconciliation Assistant.

Architecture:
  User question → LLM (with schema context) → SQL tool call → execute query → LLM formats answer
  The LLM NEVER answers from its own knowledge — every data answer must come from an executed query.
"""
import json
import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from db import execute_query, get_schema_info

logger = logging.getLogger(__name__)

# ── Tool definition ────────────────────────────────────────────────────────────

@tool
def run_sql_query(sql: str) -> str:
    """
    Execute a SQL SELECT query against the PO reconciliation SQLite database.
    Always use this tool to answer any question about purchase orders, receipts,
    mismatches, vendors, amounts, or any other data. Never answer from your own inference.

    Args:
        sql: A valid SQLite SELECT statement.

    Returns:
        JSON string with keys: rows (list of dicts), columns (list of str), row_count (int).
    """
    try:
        rows, cols = execute_query(sql)
        return json.dumps({"rows": rows, "columns": cols, "row_count": len(rows)})
    except Exception as e:
        return json.dumps({"error": str(e), "rows": [], "columns": [], "row_count": 0})


TOOLS = [run_sql_query]

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a precise financial reconciliation assistant for an enterprise procurement system.
Your job is to answer questions about Purchase Orders (POs) and Goods Receipts/Invoices by querying a live SQLite database.

CRITICAL RULES:
1. You MUST call the run_sql_query tool for every data question. Never answer from memory or inference.
2. If a question is ambiguous, state your interpretation explicitly at the start of your answer before providing results.
3. If a query returns no rows, say so clearly and suggest why that might be.
4. Format monetary amounts with $ and commas (e.g., $1,234.56).
5. Format your final answer in clean, concise prose followed by a summary table if multiple rows are returned.
6. For aggregate questions (totals, counts, averages), always use SQL aggregation — never compute in your head.
7. Flag any assumptions you make about filtering thresholds or date ranges.

DATABASE SCHEMA:
{get_schema_info()}

QUERY GUIDELINES:
- Use the 'reconciliation' VIEW for most questions about matching status, variances, shortfalls.
- For duplicate invoice detection: SELECT invoice_number, COUNT(*) FROM receipts GROUP BY invoice_number HAVING COUNT(*) > 1
- For "over $1,000 invoices that don't reconcile": filter reconciliation WHERE total_invoiced > 1000 AND reconciliation_status != 'Matched'
- Always use explicit column aliases for clarity in results.
- When joining, use po_number as the key.
"""

# ── LangGraph State ────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    # Carries the last SQL query and raw rows for the API response
    last_sql: str
    last_rows: list[dict]
    last_columns: list[str]


# ── Graph nodes ────────────────────────────────────────────────────────────────

def build_llm(model: str = "openai/gpt-oss-120b") -> ChatGroq:
    return ChatGroq(model=model, temperature=0).bind_tools(TOOLS)


def call_model(state: AgentState) -> dict:
    """Invoke the LLM with current message history."""
    llm = build_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def call_tools(state: AgentState) -> dict:
    """Execute any tool calls requested by the LLM."""
    last_message = state["messages"][-1]
    tool_messages = []
    last_sql = state.get("last_sql", "")
    last_rows: list[dict] = state.get("last_rows", [])
    last_columns: list[str] = state.get("last_columns", [])

    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "run_sql_query":
            sql = tool_call["args"].get("sql", "")
            result_str = run_sql_query.invoke({"sql": sql})
            result = json.loads(result_str)

            # Track for API response
            last_sql = sql
            last_rows = result.get("rows", [])
            last_columns = result.get("columns", [])

            tool_messages.append(
                ToolMessage(
                    content=result_str,
                    tool_call_id=tool_call["id"],
                )
            )
        else:
            tool_messages.append(
                ToolMessage(
                    content=json.dumps({"error": f"Unknown tool: {tool_call['name']}"}),
                    tool_call_id=tool_call["id"],
                )
            )

    return {
        "messages": tool_messages,
        "last_sql": last_sql,
        "last_rows": last_rows,
        "last_columns": last_columns,
    }


def should_continue(state: AgentState) -> str:
    """Route: if last message has tool calls, go to tools; else end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ── Build graph ────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")
    return graph.compile()


GRAPH = build_graph()


# ── Public interface ───────────────────────────────────────────────────────────

class ReconciliationAnswer:
    def __init__(self, answer: str, sql: str, rows: list[dict], columns: list[str]):
        self.answer = answer
        self.sql = sql
        self.rows = rows
        self.columns = columns


def ask(question: str) -> ReconciliationAnswer:
    """
    Run a user question through the LangGraph agent.
    Returns a ReconciliationAnswer with answer text, SQL run, and raw rows.
    """
    initial_state: AgentState = {
        "messages": [HumanMessage(content=question)],
        "last_sql": "",
        "last_rows": [],
        "last_columns": [],
    }

    final_state = GRAPH.invoke(initial_state)

    # Extract final AI message
    ai_messages = [m for m in final_state["messages"] if isinstance(m, AIMessage)]
    answer_text = ai_messages[-1].content if ai_messages else "No answer generated."

    return ReconciliationAnswer(
        answer=answer_text,
        sql=final_state.get("last_sql", ""),
        rows=final_state.get("last_rows", []),
        columns=final_state.get("last_columns", []),
    )
