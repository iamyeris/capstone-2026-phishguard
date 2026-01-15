from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_analyze_login_returns_phishing():
    resp = client.post("/analyze", json={"url": "https://example.com/login"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "PHISHING"
    assert data["risk_score"] >= 70
    assert "checks" in data
