import os
from typing import Any
import httpx
from langchain_core.tools import tool

BASE = os.getenv("INTERNAL_API_BASE_URL", "http://backend:8080")
TOKEN = os.getenv("INTERNAL_API_TOKEN", "ai-crew-internal")


def _headers():
    return {"X-AI-Crew-Internal": TOKEN}


def _get(path: str, params: dict[str, Any] | None = None):
    with httpx.Client(timeout=10) as client:
        r = client.get(f"{BASE}{path}", params=params, headers=_headers())
        r.raise_for_status()
        return r.json()


@tool
def get_company_snapshot() -> dict[str, Any]:
    """Read the current company operating state: goals, projects, open tasks, vendors, KPIs, finance summary, and knowledge documents."""
    return _get("/api/ai/internal/company-context")


@tool
def search_company_knowledge(query: str) -> list[dict[str, Any]]:
    """Search the company's stored knowledge documents for relevant internal information."""
    return _get("/api/knowledge/search", {"q": query})


READ_TOOLS = [get_company_snapshot, search_company_knowledge]

# These are schemas for proposed actions. They are intentionally not executed by the LLM.
WRITE_ACTIONS = {
    "create_goal": {
        "description": "Create a company goal after human approval.",
        "fields": ["title", "description"],
    },
    "create_project": {
        "description": "Create a company project after human approval.",
        "fields": ["name", "description", "status"],
    },
    "create_task": {
        "description": "Create an execution task after human approval.",
        "fields": ["title", "description", "status", "assignedAgent", "projectId"],
    },
    "create_metric": {
        "description": "Create a business KPI after human approval.",
        "fields": ["metricName", "value", "unit", "period", "notes"],
    },
    "create_vendor": {
        "description": "Create a vendor record after human approval.",
        "fields": ["name", "category", "contact", "status", "notes"],
    },
    "record_transaction": {
        "description": "Record an income or expense after human approval.",
        "fields": ["type", "category", "amount", "description", "transactionDate"],
    },
    "create_knowledge_document": {
        "description": "Store a company knowledge document after human approval.",
        "fields": ["title", "content"],
    },
}
