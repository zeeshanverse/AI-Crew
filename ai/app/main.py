import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .graph import run_company_graph
import httpx


app = FastAPI(title="AI-Crew Service", version="0.4.0")


class ConversationMessage(BaseModel):
    role: str
    content: str


class AgentRunRequest(BaseModel):
    agent: str = "CEO"
    objective: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    conversation: list[ConversationMessage] = Field(default_factory=list)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai_crew-ai",
        "mode": os.getenv("AI_MODE", "mock"),
        "model": os.getenv("OPENAI_MODEL", ""),
        "live_enabled": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/agents/run")
def run_agent(request: AgentRunRequest):
    return run_company_graph(
        request.agent,
        request.objective,
        request.context,
        [item.model_dump() for item in request.conversation],
    )


class ActionExecuteRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.post("/actions/execute")
def execute_action(request: ActionExecuteRequest):
    base = os.getenv("INTERNAL_API_BASE_URL", "http://backend:8080")
    token = os.getenv("INTERNAL_API_TOKEN", "ai-crew-internal")
    with httpx.Client(timeout=15) as client:
        response = client.post(
            f"{base}/api/ai/internal/actions/execute",
            json={"tool": request.tool, "arguments": request.arguments},
            headers={"X-AI-Crew-Internal": token, "X-AI-Crew-Agent": request.arguments.pop("__agent", "UNKNOWN") if isinstance(request.arguments, dict) else "UNKNOWN"},
        )
        if response.status_code >= 400:
            return {"status": "failed", "tool": request.tool, "error": response.text}
        return {"status": "completed", "tool": request.tool, "result": response.json()}
