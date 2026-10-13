import json
import logging
import os
import re
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END
from .agent_tools import READ_TOOLS, WRITE_ACTIONS

logger = logging.getLogger("ai_crew.graph")


class CompanyState(TypedDict, total=False):
    agent: str
    objective: str
    context: dict[str, Any]
    conversation: list[dict[str, str]]
    result: dict[str, Any]


AGENT_GUIDANCE = {
    "CEO": """You are the CEO AI of AI-Crew. Think like an executive responsible for the whole company. Turn objectives into strategy, priorities, trade-offs, measurable outcomes, risks and decisions. Use company context when available. Delegate to other AI employees when useful.""",
    "MANAGER": """You are the Manager AI of AI-Crew. Turn strategy into execution. Break work into initiatives, projects, tasks, owners, dependencies, milestones and operating cadence. Use the current project/task state and propose concrete work.""",
    "BUSINESS_ANALYST": """You are the Business Analyst AI of AI-Crew. Think in metrics, evidence and business drivers. Define KPIs, baselines, targets, data requirements, segmentation, hypotheses and decisions. Use existing business metrics and finance data when available.""",
    "SOFTWARE_ENGINEER": """You are the Software Engineer AI of AI-Crew. Act as a senior full-stack engineer. Translate business requirements into architecture, APIs, data models, implementation steps, testing, observability, security and deployment considerations.""",
    "RESEARCH": """You are the Research AI of AI-Crew. Structure research before conclusions. Use company knowledge where relevant. Separate verified internal facts, assumptions, questions and research plans. Never invent external findings.""",
}


def _mock_response(agent: str, objective: str) -> str:
    objective = objective.strip()
    if agent == "CEO":
        return f"""## Executive assessment\n\nThe objective is to **{objective}**.\n\nI would treat this as a company outcome rather than a single task. Establish the baseline, identify the highest-leverage drivers, then execute a small number of measurable initiatives.\n\n### Priority initiatives\n1. **Establish the baseline** — document the current value, target, deadline and main drivers.\n2. **Identify the highest-leverage opportunity** — use company data before adding new initiatives.\n3. **Run focused execution cycles** — assign owners, milestones and weekly reviews.\n4. **Measure and adjust** — stop low-impact work and reallocate effort.\n\n### Recommended next move\nCreate the approved goal/project structure in AI-Crew, then delegate KPI definition to the Business Analyst AI and execution planning to the Manager AI."""
    if agent == "MANAGER":
        return f"""## Execution plan\n\nObjective: **{objective}**\n\n### Workstreams\n- Baseline and requirements\n- Primary initiative\n- Supporting execution\n\n### 30-day cadence\n- Week 1: baseline and prioritization\n- Week 2: execution\n- Week 3: measurement and blocker removal\n- Week 4: review and next-cycle decision\n\n### Recommended next move\nCreate a project and break it into owner-assigned tasks."""
    if agent == "BUSINESS_ANALYST":
        return f"""## Business analysis\n\nObjective: **{objective}**\n\n### KPI framework\n- Baseline value\n- Target value\n- Rate of change\n- Driver metrics\n- Cost / effort\n\n### Analysis plan\n1. Collect recent data.\n2. Segment by meaningful business dimensions.\n3. Identify positive and negative contributors.\n4. Test hypotheses.\n5. Recommend initiatives based on impact and confidence.\n\n### Recommended next move\nStore the agreed KPI definitions in Business so the dashboard becomes measurable."""
    if agent == "SOFTWARE_ENGINEER":
        return f"""## Engineering assessment\n\nBusiness objective: **{objective}**\n\n### Technical process\n1. Define acceptance criteria.\n2. Identify affected frontend, backend, database and integrations.\n3. Design the smallest useful change.\n4. Add automated tests and observability.\n5. Deploy incrementally and compare against baseline.\n\n### Recommended next move\nCreate engineering tasks only after the business hypothesis and acceptance criteria are explicit."""
    return f"""## Research brief\n\nObjective: **{objective}**\n\n### Research questions\n1. What market, customer or technology factors affect the objective?\n2. Which alternatives or competitors matter?\n3. What evidence could confirm or reject the assumptions?\n4. Which findings would change the decision?\n\n### Evidence plan\nSeparate verified findings, internal knowledge, assumptions and open questions.\n\n### Recommended next move\nStore validated findings in Knowledge so every AI employee can reuse them."""


def _normalise_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
    return str(content)


def llm_settings() -> tuple[str, str | None, str]:
    """Return (api_key, base_url, model).

    LLM_* variables take priority; OPENAI_* are kept for backward compatibility.
    Any OpenAI-compatible provider works by setting LLM_BASE_URL
    (for example Gemini, Groq, OpenRouter or a local Ollama server).
    """
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    base_url = os.getenv("LLM_BASE_URL") or None
    model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5-mini"
    return api_key, base_url, model


def live_enabled() -> bool:
    mode = os.getenv("AI_MODE", "mock").lower()
    return mode in {"openai", "live", "llm"} and bool(llm_settings()[0])


def _friendly_error(exc: Exception) -> str:
    """Turn a provider exception into a short, user-facing reason."""
    name = type(exc).__name__
    text = str(exc).lower()
    if "insufficient_quota" in text or "no credits" in text or "quota" in text:
        return "the AI provider reports no remaining credits or quota"
    if name in {"AuthenticationError", "PermissionDeniedError"} or "api key" in text:
        return "the AI provider rejected the API key"
    if name == "RateLimitError":
        return "the AI provider is rate limiting requests"
    if name in {"APIConnectionError", "APITimeoutError"}:
        return "the AI provider could not be reached"
    if name == "NotFoundError" or ("model" in text and "not found" in text):
        return "the configured model name was not found for this provider"
    return f"the AI provider returned an error ({name})"


def _chat_model():
    """Plain chat model for any OpenAI-compatible provider (no tool binding)."""
    from langchain_openai import ChatOpenAI
    api_key, base_url, model = llm_settings()
    kwargs: dict[str, Any] = {"model": model, "api_key": api_key, "timeout": 60, "max_retries": 2}
    if base_url:
        kwargs["base_url"] = base_url
    # GPT-5 / o-series reasoning models and Gemini 3 models work best with the provider's default temperature.
    if not model.lower().startswith(("gpt-5", "o1", "o3", "o4", "gemini-3")):
        kwargs["temperature"] = 0.2
    return ChatOpenAI(**kwargs)


def _build_llm(agent: str):
    return _chat_model()


# Fields the backend requires before it will execute each approved action.
REQUIRED_FIELDS = {
    "create_goal": ["title"],
    "create_project": ["name"],
    "create_task": ["title"],
    "create_metric": ["metricName", "value"],
    "create_vendor": ["name"],
    "record_transaction": ["type", "amount"],
    "create_knowledge_document": ["title", "content"],
}
MAX_ACTIONS = 3
CONTEXT_CHAR_LIMIT = 12000
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _retrieve_context(objective: str) -> dict[str, Any]:
    """Read company state and matching knowledge before reasoning.

    Runs in the service itself (not as model tool calls), so it works with any provider
    and a backend hiccup never blocks the answer.
    """
    tools = {t.name: t for t in READ_TOOLS}
    context: dict[str, Any] = {}
    try:
        context["company_snapshot"] = tools["get_company_snapshot"].invoke({})
    except Exception as exc:
        logger.warning("Could not read the company snapshot: %s", exc)
    try:
        matches = tools["search_company_knowledge"].invoke({"query": objective[:200]})
        if matches:
            context["knowledge_matches"] = matches
    except Exception as exc:
        logger.warning("Could not search company knowledge: %s", exc)
    return context


def _action_catalog() -> str:
    return "\n".join(
        f"- {name}: fields {', '.join(meta['fields'])}. {meta['description']}"
        for name, meta in WRITE_ACTIONS.items()
    )


def _system_prompt(agent: str) -> str:
    return f"""
You are an AI employee inside AI-Crew, a company operating system.
{AGENT_GUIDANCE.get(agent, 'Act as a specialized company employee.')}
Write a professional answer in Markdown. Use the retrieved company data you are given and do not invent company facts.
Every change to company data is only a PROPOSAL that a human must approve. Never say a record was created or updated.

If concrete changes would help, end your reply with ONE fenced json block and nothing after it, in exactly this shape:
```json
{{"actions": [{{"tool": "create_goal", "arguments": {{"title": "...", "description": "..."}}}}]}}
```
Allowed tools (use only these names and fields):
{_action_catalog()}
Rules for the json block: at most {MAX_ACTIONS} actions; metric `value` and transaction `amount` must be numbers; use status PLANNED for projects and TODO for tasks; do not set projectId unless you know it from the retrieved data; omit the json block if no change is warranted.
"""


def _parse_actions(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Split a model reply into (display text, validated action proposals)."""
    matches = list(_JSON_BLOCK.finditer(text))
    if not matches:
        return text.strip(), []
    block = matches[-1]
    clean = (text[:block.start()] + text[block.end():]).strip()
    try:
        data = json.loads(block.group(1))
    except json.JSONDecodeError:
        return clean, []
    raw = data.get("actions", []) if isinstance(data, dict) else []
    actions: list[dict[str, Any]] = []
    for item in raw if isinstance(raw, list) else []:
        if len(actions) >= MAX_ACTIONS:
            break
        if not isinstance(item, dict):
            continue
        tool, args = item.get("tool"), item.get("arguments")
        if tool not in WRITE_ACTIONS or not isinstance(args, dict):
            continue
        allowed = WRITE_ACTIONS[tool]["fields"]
        cleaned = {k: v for k, v in args.items() if k in allowed and v not in (None, "")}
        if any(field not in cleaned for field in REQUIRED_FIELDS.get(tool, [])):
            continue
        actions.append({
            "id": f"action-{len(actions) + 1}",
            "tool": tool,
            "description": WRITE_ACTIONS[tool]["description"],
            "arguments": cleaned,
            "requires_approval": True,
        })
    return clean, actions


def _drop_unknown_project_ids(actions: list[dict[str, Any]], retrieved: dict[str, Any]) -> None:
    """A task pointing at a project that does not exist would fail on approval."""
    projects = (retrieved.get("company_snapshot") or {}).get("projects") or []
    known = {str(p.get("id")) for p in projects if isinstance(p, dict)}
    for action in actions:
        if action["tool"] == "create_task" and str(action["arguments"].get("projectId")) not in known:
            action["arguments"].pop("projectId", None)


def _fallback_action(agent: str, objective: str, answer: str) -> dict[str, Any] | None:
    """First-turn proposal drafted from the answer when the model proposed nothing."""
    title = " ".join(objective.split())[:120]
    summary = " ".join(answer.split())[:300]
    drafts = {
        "CEO": ("create_goal", {"title": title, "description": summary}),
        "MANAGER": ("create_project", {"name": title, "description": summary, "status": "PLANNED"}),
        "SOFTWARE_ENGINEER": ("create_task", {"title": title, "description": summary, "status": "TODO",
                                              "assignedAgent": "SOFTWARE_ENGINEER"}),
        "RESEARCH": ("create_knowledge_document", {"title": f"Research brief: {title}", "content": answer}),
    }
    draft = drafts.get(agent.upper())
    if not draft or not title:
        return None
    tool, args = draft
    return {
        "id": "action-1",
        "tool": tool,
        "description": WRITE_ACTIONS[tool]["description"] + " (drafted from the recommendation)",
        "arguments": {k: v for k, v in args.items() if v},
        "requires_approval": True,
    }


def live_result(agent: str, objective: str, context: dict[str, Any], conversation: list[dict[str, str]]):
    llm = _chat_model()
    retrieved = _retrieve_context(objective)
    messages: list[dict[str, str]] = [{"role": "system", "content": _system_prompt(agent)}]
    for item in conversation[-16:]:
        role, content = item.get("role"), item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    retrieved_text = json.dumps(retrieved, default=str)[:CONTEXT_CHAR_LIMIT]
    messages.append({"role": "user", "content": (
        f"Current request:\n{objective}\n\n"
        f"Context supplied by the application:\n{json.dumps(context or {}, default=str)}\n\n"
        f"Retrieved company data:\n{retrieved_text}"
    )})

    reply = llm.invoke(messages)
    answer, actions = _parse_actions(_normalise_content(reply.content))
    _drop_unknown_project_ids(actions, retrieved)
    if not answer.strip():
        if not actions:
            raise RuntimeError("the model returned an empty answer")
        bullets = "\n".join(f"- **{a['tool'].replace('_', ' ')}** — {a['description']}" for a in actions)
        answer = ("## Proposed actions\n\nI have prepared the following changes for your approval. "
                  "No company data has been changed yet.\n\n" + bullets)
    if not actions and not conversation:
        fallback = _fallback_action(agent, objective, answer)
        if fallback:
            actions = [fallback]

    return {
        "agent": agent,
        "status": "completed",
        "mode": "live",
        "response": answer,
        "summary": answer,
        "actions": actions,
        "next_steps": ["Review the recommendation", "Approve useful actions", "Track outcomes in AI-Crew"],
        "suggested_follow_ups": ["Turn this into an execution plan", "What information do you need from me?", "Challenge this recommendation"],
    }


def mock_result(agent: str, objective: str, conversation: list[dict[str, str]]):
    response = _mock_response(agent, objective)
    actions = []
    if agent == "CEO":
        actions.append({"id":"mock-goal-1","tool":"create_goal","description":"Create the objective as a company goal after approval.","arguments":{"title":objective,"description":"Proposed by CEO AI from the current conversation."},"requires_approval":True})
    return {"agent":agent,"status":"completed","mode":"mock","response":response,"summary":response,"actions":actions,"next_steps":["Review the recommendation","Approve useful actions","Track outcomes in AI-Crew"],"suggested_follow_ups":["Turn this into an execution plan","What information do you need from me?","Challenge this recommendation"]}


def specialist_node(state: CompanyState):
    agent = state["agent"]
    conversation = state.get("conversation", [])
    if live_enabled():
        try:
            return {"result": live_result(agent, state["objective"], state.get("context", {}), conversation)}
        except Exception as exc:  # provider errors must never become a raw 500
            reason = _friendly_error(exc)
            logger.warning("Live LLM call failed (%s: %s); falling back to mock", type(exc).__name__, exc)
            result = mock_result(agent, state["objective"], conversation)
            notice = f"> **Live AI unavailable:** {reason}. Showing the offline mock response instead.\n\n"
            result["response"] = notice + result["response"]
            result["summary"] = result["response"]
            result["fallback"] = True
            result["warning"] = reason
            return {"result": result}
    return {"result": mock_result(agent, state["objective"], conversation)}


def build_graph():
    graph = StateGraph(CompanyState)
    graph.add_node("specialist", specialist_node)
    graph.set_entry_point("specialist")
    graph.add_edge("specialist", END)
    return graph.compile()

GRAPH = build_graph()


def run_company_graph(agent: str, objective: str, context: dict[str, Any], conversation: list[dict[str, str]] | None = None):
    state: CompanyState = {"agent": agent.upper(), "objective": objective, "context": context or {}, "conversation": conversation or []}
    return GRAPH.invoke(state)["result"]