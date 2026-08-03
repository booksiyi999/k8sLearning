"""QA Attack tests for K8s Quest v0.4 new endpoints.

Tests /api/lesson, /api/deploy, /api/resources, /api/logs, /api/test-connectivity, /api/cluster/status
with malicious/edge-case inputs.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestLessonAttack:
    """攻击 /api/lesson/{level_id}"""

    def test_lesson_nonexistent_level(self):
        r = client.get("/api/lesson/Q9.9")
        assert r.status_code == 200
        assert "error" in r.json()

    def test_lesson_sql_injection(self):
        r = client.get("/api/lesson/Q1.1'; DROP TABLE--")
        assert r.status_code == 200
        assert "error" in r.json()

    def test_lesson_empty_id(self):
        r = client.get("/api/lesson/")
        assert r.status_code in (404, 422)

    def test_lesson_path_traversal(self):
        r = client.get("/api/lesson/../../../etc/passwd")
        assert r.status_code in (200, 404, 422)

    def test_lesson_all_30_levels_have_content(self):
        """所有30关都应有教学文档。"""
        for i in range(1, 7):
            for j in range(1, 6):
                lid = f"Q{i}.{j}"
                r = client.get(f"/api/lesson/{lid}")
                data = r.json()
                assert data.get("has_lesson") is True, f"{lid} missing lesson"


class TestDeployAttack:
    """攻击 /api/deploy"""

    def test_deploy_nonexistent_level(self):
        r = client.post("/api/deploy", json={
            "level_id": "Q9.9", "user_yaml": "apiVersion: v1\nkind: Pod"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_deploy_empty_yaml(self):
        r = client.post("/api/deploy", json={"level_id": "Q1.1", "user_yaml": ""})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_deploy_invalid_yaml(self):
        r = client.post("/api/deploy", json={
            "level_id": "Q1.1", "user_yaml": "not: valid: yaml: at: all"
        })
        assert r.status_code == 200

    def test_deploy_missing_fields(self):
        r = client.post("/api/deploy", json={"level_id": "Q1.1"})
        assert r.status_code in (200, 422)

    def test_deploy_simulator_mode(self):
        """模拟器模式下 deploy 应等价于 check。"""
        r = client.post("/api/deploy", json={
            "level_id": "Q1.1",
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n  - name: nginx\n    image: nginx:1.25"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "simulator"
        assert data["ok"] is True


class TestClusterEndpointsAttack:
    """攻击集群端点（模拟器模式下应优雅返回）。"""

    def test_resources_simulator_mode(self):
        r = client.get("/api/resources")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "simulator"

    def test_logs_nonexistent_pod(self):
        r = client.get("/api/logs/nonexistent-pod-12345")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "simulator"

    def test_logs_with_special_chars(self):
        r = client.get("/api/logs/pod;rm -rf")
        assert r.status_code == 200

    def test_connectivity_simulator_mode(self):
        r = client.post("/api/test-connectivity", json={
            "service_name": "web-svc", "port": 80
        })
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "simulator"

    def test_connectivity_invalid_port(self):
        r = client.post("/api/test-connectivity", json={
            "service_name": "web-svc", "port": -1
        })
        assert r.status_code == 200

    def test_connectivity_missing_service(self):
        r = client.post("/api/test-connectivity", json={"port": 80})
        assert r.status_code in (200, 422)

    def test_cluster_status_structure(self):
        r = client.get("/api/cluster/status")
        assert r.status_code == 200
        data = r.json()
        assert "mode" in data
        assert "kubectl" in data
        assert "namespace" in data


class TestClusterPracticeLevels:
    """测试6个集群实战关卡的校验逻辑。"""

    def test_q15_valid_pod(self):
        r = client.post("/api/deploy", json={
            "level_id": "Q1.5",
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-web\nspec:\n  containers:\n  - name: nginx\n    image: nginx:1.25"
        })
        assert r.status_code == 200

    def test_q15_invalid_pod(self):
        r = client.post("/api/deploy", json={
            "level_id": "Q1.5", "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test"
        })
        assert r.json()["ok"] is False

    def test_q25_valid_deployment(self):
        r = client.post("/api/deploy", json={
            "level_id": "Q2.5",
            "user_yaml": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-deploy\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: nginx\n        image: nginx:1.25"
        })
        assert r.status_code == 200

    def test_q35_valid_service_deployment(self):
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.25"""
        r = client.post("/api/deploy", json={
            "level_id": "Q3.5", "user_yaml": yaml_text
        })
        assert r.status_code == 200

    def test_all_cluster_levels_have_lessons(self):
        for i in range(1, 7):
            lid = f"Q{i}.5"
            r = client.get(f"/api/lesson/{lid}")
            data = r.json()
            assert data.get("has_lesson") is True, f"{lid} missing lesson"

    def test_all_cluster_levels_listed(self):
        r = client.get("/api/levels")
        levels = r.json()["levels"]
        for i in range(1, 7):
            assert any(l["id"] == f"Q{i}.5" for l in levels), f"Q{i}.5 not in level list"
