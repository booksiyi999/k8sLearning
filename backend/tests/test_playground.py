"""实操模块（Playground）API 测试。"""

import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPlaygroundSave:
    """测试 POST /api/playground/save。"""

    def test_save_yaml_success(self):
        r = client.post("/api/playground/save", json={
            "level_id": "Q1.1",
            "yaml_content": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx\nspec:\n  containers:\n  - name: nginx\n    image: nginx:1.25\n"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["filepath"].endswith("Q1_1.yaml")
        assert "kubectl apply -f" in data["apply_command"]

    def test_save_creates_file(self):
        yaml_content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n"
        r = client.post("/api/playground/save", json={
            "level_id": "Q9.5",
            "yaml_content": yaml_content
        })
        data = r.json()
        assert data["ok"] is True
        assert os.path.exists(data["filepath"])
        with open(data["filepath"]) as f:
            assert f.read() == yaml_content

    def test_save_special_chars_in_level_id(self):
        r = client.post("/api/playground/save", json={
            "level_id": "Q28.1",
            "yaml_content": "# test"
        })
        data = r.json()
        assert data["ok"] is True
        assert "Q28_1.yaml" in data["filepath"]

    def test_save_empty_yaml(self):
        r = client.post("/api/playground/save", json={
            "level_id": "Q1.1",
            "yaml_content": ""
        })
        data = r.json()
        assert data["ok"] is True  # 空文件也允许保存


class TestPlaygroundLevels:
    """测试 GET /api/playground/levels。"""

    def test_returns_level_list(self):
        r = client.get("/api/playground/levels")
        assert r.status_code == 200
        data = r.json()
        assert "levels" in data
        assert len(data["levels"]) > 0
        assert "Q1.1" in data["levels"]
        assert "Q28.1" in data["levels"]

    def test_returns_save_dir(self):
        r = client.get("/api/playground/levels")
        data = r.json()
        assert data["save_dir"] == "/tmp/k8s-quest"

    def test_levels_are_sorted(self):
        r = client.get("/api/playground/levels")
        data = r.json()
        levels = data["levels"]
        assert levels == sorted(levels)

    def test_not_all_levels_are_playground(self):
        """不是所有关卡都有实操模块。"""
        r = client.get("/api/playground/levels")
        data = r.json()
        # 应该只有 15 个左右关键关卡，不是全部 150 个
        assert len(data["levels"]) < 30
        assert len(data["levels"]) > 10
