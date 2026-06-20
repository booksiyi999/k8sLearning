from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_levels_endpoint():
    r = client.get("/api/levels")
    assert r.status_code == 200
    data = r.json()
    assert "levels" in data
    assert len(data["levels"]) > 0

def test_check_endpoint_correct():
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n    - name: nginx\n      image: nginx:1.25\n"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True

def test_check_endpoint_wrong():
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": "this is not yaml"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
