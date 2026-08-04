import pytest
from app.main import app
from fastapi.testclient import TestClient
client = TestClient(app)

def check(level_id, yaml_text):
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    assert r.status_code == 200, f"{level_id} returned HTTP {r.status_code}"
    return r.json()

LEVEL_IDS = [f"Q{ch}.{lv}" for ch in range(23,29) for lv in range(1,6)]

class TestCrash:
    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_empty(self, level_id):
        assert check(level_id, "")["ok"] is False

    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_garbage(self, level_id):
        assert check(level_id, "{{{not yaml")["ok"] is False

    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_null(self, level_id):
        assert check(level_id, "null")["ok"] is False

    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_list(self, level_id):
        assert check(level_id, "- a\n- b")["ok"] is False

    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_string(self, level_id):
        assert check(level_id, "hello")["ok"] is False

class TestWrongKind:
    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_pod(self, level_id):
        y = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: x\nspec:\n  containers:\n  - name: x\n    image: nginx\n"
        assert check(level_id, y)["ok"] is False

class TestMissingFields:
    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_minimal(self, level_id):
        y = "kind: ConfigMap\nmetadata:\n  name: x\n"
        assert check(level_id, y)["ok"] is False

class TestMultiDoc:
    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_empty_docs(self, level_id):
        assert check(level_id, "---\n---\n")["ok"] is False

class TestStatePollution:
    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_twice(self, level_id):
        y = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: t\nspec:\n  containers:\n  - name: x\n    image: nginx\n"
        d1 = check(level_id, y)
        d2 = check(level_id, y)
        assert d1["ok"] == d2["ok"]

class TestTypeConfusion:
    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_spec_as_string(self, level_id):
        y = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: x\nspec: notadict\n"
        assert check(level_id, y)["ok"] is False

    @pytest.mark.parametrize("level_id", LEVEL_IDS)
    def test_containers_as_int(self, level_id):
        y = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: x\nspec:\n  containers: 42\n"
        assert check(level_id, y)["ok"] is False
