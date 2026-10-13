import json

import pytest
from fastapi.testclient import TestClient

from app import graph
from app.main import app

client = TestClient(app)


class FakeQuotaError(Exception):
    """Mimics openai.RateLimitError with insufficient_quota."""


class FakeReply:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return FakeReply(self.content)


def action_block(*actions):
    return "```json\n" + json.dumps({"actions": list(actions)}) + "\n```"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("AI_MODE", "OPENAI_API_KEY", "OPENAI_MODEL", "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setattr(graph, "_retrieve_context", lambda objective: {})


# ---------- provider failures never become a 500 ----------

def test_provider_failure_falls_back_to_mock_instead_of_500(monkeypatch):
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def boom(*args, **kwargs):
        raise FakeQuotaError("Error code: 429 - insufficient_quota: You have no credits remaining")

    monkeypatch.setattr(graph, "live_result", boom)
    r = client.post("/agents/run", json={"agent": "CEO", "objective": "Increase MRR by 20%"})
    assert r.status_code == 200
    body = r.json()
    assert body["fallback"] is True
    assert "Live AI unavailable" in body["response"]
    assert "credits" in body["warning"]
    assert body["actions"]


def test_every_agent_survives_provider_failure(monkeypatch):
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(graph, "live_result", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    for agent in ("CEO", "MANAGER", "BUSINESS_ANALYST", "SOFTWARE_ENGINEER", "RESEARCH"):
        r = client.post("/agents/run", json={"agent": agent, "objective": "Test"})
        assert r.status_code == 200, agent
        assert r.json()["fallback"] is True


def test_mock_mode_unchanged_without_key():
    r = client.post("/agents/run", json={"agent": "MANAGER", "objective": "Ship v1"})
    assert r.status_code == 200
    assert r.json()["mode"] == "mock"
    assert "fallback" not in r.json()


# ---------- live pipeline ----------

def test_live_answer_and_valid_actions(live, monkeypatch):
    reply = "## Plan\nDo the thing.\n\n" + action_block(
        {"tool": "create_goal", "arguments": {"title": "Grow MRR 20%", "description": "90 days", "bogus": 1}},
        {"tool": "delete_everything", "arguments": {"title": "x"}},
        {"tool": "create_metric", "arguments": {"metricName": "MRR"}},  # missing required value
        {"tool": "create_metric", "arguments": {"metricName": "MRR", "value": 120000, "unit": "INR"}},
    )
    fake = FakeLLM(reply)
    monkeypatch.setattr(graph, "_chat_model", lambda: fake)
    result = graph.live_result("CEO", "Grow MRR", {}, [])
    assert result["mode"] == "live"
    assert "```" not in result["response"] and "Do the thing." in result["response"]
    tools = [a["tool"] for a in result["actions"]]
    assert tools == ["create_goal", "create_metric"]
    assert result["actions"][0]["arguments"] == {"title": "Grow MRR 20%", "description": "90 days"}
    assert all(a["requires_approval"] for a in result["actions"])
    assert len(fake.calls) == 1, "one model call, no tool-calling loop"


def test_actions_capped_and_bad_json_ignored(live, monkeypatch):
    many = [{"tool": "create_goal", "arguments": {"title": f"g{i}"}} for i in range(6)]
    _, actions = graph._parse_actions("text\n" + action_block(*many))
    assert len(actions) == graph.MAX_ACTIONS
    clean, actions = graph._parse_actions("text\n```json\n{not json}\n```")
    assert actions == [] and clean == "text"


def test_first_turn_gets_drafted_proposal_followup_does_not(live, monkeypatch):
    monkeypatch.setattr(graph, "_chat_model", lambda: FakeLLM("Just advice, no json."))
    first = graph.live_result("CEO", "Increase MRR by 20%", {}, [])
    assert [a["tool"] for a in first["actions"]] == ["create_goal"]
    assert first["actions"][0]["arguments"]["title"] == "Increase MRR by 20%"
    followup = graph.live_result("CEO", "Challenge this", {}, [{"role": "user", "content": "hi"}])
    assert followup["actions"] == []


def test_task_with_unknown_project_id_loses_it(live, monkeypatch):
    reply = action_block({"tool": "create_task", "arguments": {"title": "Audit", "projectId": 999}})
    monkeypatch.setattr(graph, "_chat_model", lambda: FakeLLM(reply))
    monkeypatch.setattr(graph, "_retrieve_context",
                        lambda o: {"company_snapshot": {"projects": [{"id": 1, "name": "P"}]}})
    result = graph.live_result("SOFTWARE_ENGINEER", "Audit", {}, [])
    assert "projectId" not in result["actions"][0]["arguments"]


def test_empty_model_answer_falls_back_cleanly(monkeypatch):
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setattr(graph, "_retrieve_context", lambda o: {})
    monkeypatch.setattr(graph, "_chat_model", lambda: FakeLLM("   "))
    r = client.post("/agents/run", json={"agent": "CEO", "objective": "Test"})
    assert r.status_code == 200 and r.json()["fallback"] is True


def test_retrieve_context_survives_backend_down(monkeypatch):
    class Down:
        def __init__(self, name):
            self.name = name

        def invoke(self, _):
            raise ConnectionError("backend unreachable")

    monkeypatch.setattr(graph, "READ_TOOLS", [Down("get_company_snapshot"), Down("search_company_knowledge")])
    assert graph._retrieve_context("anything") == {}


# ---------- wiring ----------

def test_run_goes_through_compiled_langgraph(monkeypatch):
    calls = []
    original = graph.GRAPH.invoke
    monkeypatch.setattr(graph.GRAPH, "invoke", lambda state, *a, **k: (calls.append(1), original(state, *a, **k))[1], raising=False)
    result = graph.run_company_graph("CEO", "Test", {}, [])
    assert result["agent"] == "CEO"
    assert calls


def test_health_reports_live_only_when_key_present(monkeypatch):
    assert client.get("/health").json()["live_enabled"] is False
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setenv("LLM_MODEL", "some-model")
    h = client.get("/health").json()
    assert h["live_enabled"] is True and h["model"] == "some-model" and h["provider"] == "custom"


def test_chat_model_settings(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "gpt-5-mini")
    llm = graph._chat_model()
    assert "example.test" in str(llm.openai_api_base)
    assert llm.temperature is None or llm.temperature == 1
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    assert graph._chat_model().temperature is None or graph._chat_model().temperature == 1
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    assert graph._chat_model().temperature == 0.2


def test_friendly_error_messages():
    assert "credits" in graph._friendly_error(FakeQuotaError("insufficient_quota"))
    assert "API key" in graph._friendly_error(RuntimeError("Incorrect API key provided"))