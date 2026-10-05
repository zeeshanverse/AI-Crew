import json
import os
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END
from .agent_tools import READ_TOOLS, WRITE_ACTIONS


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


def _extract_tool_calls(message: Any) -> list[dict[str, Any]]:
    calls = getattr(message, "tool_calls", None) or []
    actions = []
    for call in calls:
        name = call.get("name")
        args = call.get("args", {})
        if name in WRITE_ACTIONS:
            actions.append({
                "id": call.get("id", f"action-{len(actions)+1}"),
                "tool": name,
                "description": WRITE_ACTIONS[name]["description"],
                "arguments": args,
                "requires_approval": True,
            })
    return actions


def _build_llm(agent: str):
    from langchain_openai import ChatOpenAI
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    return ChatOpenAI(model=model, temperature=0.2).bind_tools(READ_TOOLS + _write_tool_schemas())


def _write_tool_schemas():
    from langchain_core.tools import StructuredTool
    from pydantic import create_model, Field
    tools = []
    for name, meta in WRITE_ACTIONS.items():
        fields = {field: (Any, Field(default=None)) for field in meta["fields"]}
        schema = create_model(f"{name.title()}Args", **fields)
        def proposal(**kwargs):
            return {"requires_approval": True, "tool": name, "arguments": kwargs}
        tools.append(StructuredTool.from_function(
            func=proposal,
            name=name,
            description=meta["description"],
            args_schema=schema,
        ))
    return tools


def real_result(agent: str, objective: str, context: dict[str, Any], conversation: list[dict[str, str]]):
    llm = _build_llm(agent)
    system_prompt = f"""
You are an AI employee inside AI-Crew, a company operating system.
{AGENT_GUIDANCE.get(agent, 'Act as a specialized company employee.')}

Your response must feel like a professional assistant, not an API dump. Use Markdown.
You have read-only tools for company state and knowledge. You may propose write actions
using tools, but every write action MUST be treated as a proposal requiring human approval.
Never say a record was created/updated unless the user has approved the proposed action.
When proposing actions, make them concrete and explain why they are useful.
Maintain the conversation context. Do not invent company facts.
"""
    messages = [{"role": "system", "content": system_prompt}]
    for item in conversation[-16:]:
        role, content = item.get("role"), item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": f"Current request:\n{objective}\n\nKnown context supplied by the application:\n{json.dumps(context or {}, default=str)}"})

    first = llm.invoke(messages)
    # Execute only read-only tool calls automatically, then ask the model to synthesize.
    tool_messages = []
    read_calls = [c for c in (getattr(first, "tool_calls", None) or []) if c.get("name") in {t.name for t in READ_TOOLS}]
    if read_calls:
        tool_map = {t.name: t for t in READ_TOOLS}
        for call in read_calls:
            try:
                output = tool_map[call["name"]].invoke(call.get("args", {}))
                tool_messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(output, default=str)})
            except Exception as exc:
                tool_messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": f"Tool error: {exc}"})
        messages.append(first)
        messages.extend(tool_messages)
        messages.append({"role": "user", "content": "Now synthesize the answer using the retrieved company information. Keep any write operations as approval-required proposals."})
        final = llm.invoke(messages)
    else:
        final = first

    actions = _extract_tool_calls(final)
    # Some models may put action calls on the first message.
    if not actions:
        actions = _extract_tool_calls(first)
    content = _normalise_content(final.content)
    if not content.strip() and actions:
        bullets = "\n".join(f"- **{a['tool'].replace('_',' ')}** — {a['description']}" for a in actions)
        content = "## Proposed actions\n\nI have prepared the following changes for your approval. No company data has been changed yet.\n\n" + bullets
    return {
        "agent": agent,
        "status": "completed",
        "mode": "openai",
        "response": content,
        "summary": content,
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
    mode = os.getenv("AI_MODE", "mock").lower()
    if mode in {"openai", "live"} and os.getenv("OPENAI_API_KEY"):
        return {"result": real_result(agent, state["objective"], state.get("context", {}), state.get("conversation", []))}
    return {"result": mock_result(agent, state["objective"], state.get("conversation", []))}


def build_graph():
    graph = StateGraph(CompanyState)
    graph.add_node("specialist", specialist_node)
    graph.set_entry_point("specialist")
    graph.add_edge("specialist", END)
    return graph.compile()

GRAPH = build_graph()


def run_company_graph(agent: str, objective: str, context: dict[str, Any], conversation: list[dict[str, str]] | None = None):
    state: CompanyState = {"agent": agent.upper(), "objective": objective, "context": context or {}, "conversation": conversation or []}
    return specialist_node(state)["result"]
