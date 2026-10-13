import os

import pytest
from fastapi.testclient import TestClient

from app import graph
from app.main import app

client = TestClient(app)


class FakeQuotaError(Exception):
    """Mimics openai.RateLimitError with insufficient_quota."""


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("AI_MODE", "OPENAI_API_KEY", "OPENAI_MODEL", "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_provider_failure_falls_back_to_mock_instead_of_500(monkeypatch):
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def boom(*args, **kwargs):
        raise FakeQuotaError("Error code: 429 - insufficient_quota: You have no credits remaining")

    monkeypatch.setattr(graph, "real_result", boom)
    r = client.post("/agents/run", json={"agent": "CEO", "objective": "Increase MRR by 20%"})
    assert r.status_code == 200
    body = r.json()
    assert body["fallback"] is True
    assert "Live AI unavailable" in body["response"]
    assert "credits" in body["warning"]
    assert body["actions"]            # mock CEO still proposes the goal


def test_every_agent_survives_provider_failure(monkeypatch):
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(graph, "real_result", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    for agent in ("CEO", "MANAGER", "BUSINESS_ANALYST", "SOFTWARE_ENGINEER", "RESEARCH"):
        r = client.post("/agents/run", json={"agent": agent, "objective": "Test"})
        assert r.status_code == 200, agent
        assert r.json()["fallback"] is True


def test_mock_mode_unchanged_without_key():
    r = client.post("/agents/run", json={"agent": "MANAGER", "objective": "Ship v1"})
    assert r.status_code == 200
    assert r.json()["mode"] == "mock"
    assert "fallback" not in r.json()


def test_run_goes_through_compiled_langgraph(monkeypatch):
    calls = []
    original = graph.GRAPH.invoke
    monkeypatch.setattr(graph.GRAPH, "invoke", lambda state, *a, **k: (calls.append(1), original(state, *a, **k))[1], raising=False)
    result = graph.run_company_graph("CEO", "Test", {}, [])
    assert result["agent"] == "CEO"
    assert calls, "run_company_graph must invoke the compiled graph"


def test_health_reports_live_only_when_key_present(monkeypatch):
    assert client.get("/health").json()["live_enabled"] is False
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setenv("LLM_MODEL", "some-model")
    h = client.get("/health").json()
    assert h["live_enabled"] is True and h["model"] == "some-model" and h["provider"] == "custom"


def test_build_llm_uses_custom_base_url_and_skips_temperature_for_gpt5(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "gpt-5-mini")
    bound = graph._build_llm("CEO")
    llm = bound.bound
    assert "example.test" in str(llm.openai_api_base)
    assert llm.temperature is None or llm.temperature == 1
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    assert graph._build_llm("CEO").bound.temperature == 0.2


def test_friendly_error_messages():
    assert "credits" in graph._friendly_error(FakeQuotaError("insufficient_quota"))
    assert "API key" in graph._friendly_error(RuntimeError("Incorrect API key provided"))