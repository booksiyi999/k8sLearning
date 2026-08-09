"""Ch28 集群模式验证测试。"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCh28ClusterVerify:
    """测试 Ch28 双轨制: 模拟器认知级 + 集群实战级。"""

    def test_ch28_level_returns_track(self):
        """Ch28 关卡应返回 track 字段（实战级）。"""
        r = client.get("/api/level/Q28.1")
        assert r.status_code == 200
        data = r.json()
        assert "id" in data

    def test_ch28_cluster_check_simulator_mode(self):
        """模拟器模式下 /api/check/cluster 返回未启用提示。"""
        r = client.post("/api/check/cluster", json={
            "level_id": "Q28.1",
            "user_input": "kubectl get pods"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert "集群模式未启用" in data.get("error", "") or data.get("mode") == "simulator"

    def test_ch28_cluster_check_invalid_level(self):
        """无效关卡ID返回错误。"""
        r = client.post("/api/check/cluster", json={
            "level_id": "Q99.9",
            "user_input": "kubectl get pods"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False

    def test_ch28_cluster_check_non_ch28_level(self):
        """非 Ch28 关卡调用集群验证端点返回错误。"""
        r = client.post("/api/check/cluster", json={
            "level_id": "Q1.1",
            "user_input": "kubectl get pods"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert "Ch28" in data.get("error", "")

    def test_ch28_simulator_check_still_works(self):
        """模拟器模式下 Ch28 的常规 check 仍然可用（关键词匹配）。"""
        r = client.post("/api/check", json={
            "level_id": "Q28.1",
            "user_yaml": "kubectl run nginx --image=nginx\nkubectl expose pod nginx --port=80\nkubectl scale deployment nginx --replicas=3"
        })
        assert r.status_code == 200
        data = r.json()
        assert "ok" in data

    def test_cluster_status_endpoint(self):
        """集群状态端点正常工作。"""
        r = client.get("/api/cluster/status")
        assert r.status_code == 200
        data = r.json()
        assert "mode" in data
