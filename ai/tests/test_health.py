from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_ceo():
    r = client.post("/agents/run", json={"agent":"CEO","objective":"Increase revenue"})
    assert r.status_code == 200
    assert r.json()["agent"] == "CEO"
