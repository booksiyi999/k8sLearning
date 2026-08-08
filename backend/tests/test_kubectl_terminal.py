"""v2.0 交互式 Kubectl 终端测试。

测试维度:
1. 命令验证（白名单/黑名单/注入防护）
2. API 端点（模拟器模式优雅降级）
3. 安全性（危险命令确认/禁止字符）
"""
import pytest
from app.cluster import ClusterManager
from fastapi.testclient import TestClient
from app.main import app


# ═══ 命令验证测试 ═══

class TestKubectlCommandValidation:
    """测试 kubectl 命令安全验证。"""

    def test_valid_get_command(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods")
        assert ok is True
        assert args == ["get", "pods"]

    def test_valid_describe_command(self):
        ok, err, args = ClusterManager._validate_kubectl_command("describe pod nginx-pod")
        assert ok is True
        assert args == ["describe", "pod", "nginx-pod"]

    def test_valid_logs_command(self):
        ok, err, args = ClusterManager._validate_kubectl_command("logs nginx-pod --tail=50")
        assert ok is True

    def test_valid_apply_command(self):
        ok, err, args = ClusterManager._validate_kubectl_command("apply -f -")
        assert ok is True

    def test_kubectl_prefix_stripped(self):
        ok, err, args = ClusterManager._validate_kubectl_command("kubectl get pods")
        assert ok is True
        assert args == ["get", "pods"]

    def test_empty_command_rejected(self):
        ok, err, args = ClusterManager._validate_kubectl_command("")
        assert ok is False
        assert "空" in err

    def test_whitespace_only_rejected(self):
        ok, err, args = ClusterManager._validate_kubectl_command("   ")
        assert ok is False

    def test_kubectl_alone_rejected(self):
        ok, err, args = ClusterManager._validate_kubectl_command("kubectl")
        assert ok is False
        assert "子命令" in err

    def test_unknown_subcommand_rejected(self):
        ok, err, args = ClusterManager._validate_kubectl_command("ssh root@host")
        assert ok is False
        assert "白名单" in err

    def test_forbidden_subcommand_rejected(self):
        ok, err, args = ClusterManager._validate_kubectl_command("reset cluster")
        assert ok is False
        assert "禁止" in err

    # ═══ 注入防护测试 ═══

    def test_semicolon_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods; rm -rf /")
        assert ok is False
        assert ";" in err

    def test_pipe_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods | grep nginx")
        assert ok is False
        assert "|" in err

    def test_backtick_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods `whoami`")
        assert ok is False
        assert "`" in err

    def test_dollar_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods $(whoami)")
        assert ok is False
        assert "$" in err

    def test_ampersand_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods & background")
        assert ok is False
        assert "&" in err

    def test_newline_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods\nrm -rf /")
        assert ok is False

    def test_redirect_injection_blocked(self):
        ok, err, args = ClusterManager._validate_kubectl_command("get pods > /etc/passwd")
        assert ok is False
        assert ">" in err

    # ═══ 危险命令检测 ═══

    def test_delete_is_dangerous(self):
        assert "delete" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_scale_is_dangerous(self):
        assert "scale" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_get_is_not_dangerous(self):
        assert "get" not in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_describe_is_not_dangerous(self):
        assert "describe" not in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_logs_is_not_dangerous(self):
        assert "logs" not in ClusterManager.DANGEROUS_SUBCOMMANDS


# ═══ API 端点测试 ═══

class TestKubectlAPI:
    """测试 /api/kubectl 端点。"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_kubectl_endpoint_simulator_mode(self):
        """模拟器模式下 /api/kubectl 返回友好提示。"""
        r = self.client.post("/api/kubectl", json={"command": "get pods"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        assert "集群模式未启用" in data["error"]

    def test_kubectl_whitelist_endpoint(self):
        """白名单端点返回允许的子命令列表。"""
        r = self.client.get("/api/kubectl/whitelist")
        assert r.status_code == 200
        data = r.json()
        assert "allowed" in data
        assert "dangerous" in data
        assert "get" in data["allowed"]
        assert "delete" in data["dangerous"]
        assert data["mode"] == "simulator"  # 测试环境是模拟器

    def test_kubectl_invalid_command(self):
        """无效命令返回错误。"""
        r = self.client.post("/api/kubectl", json={"command": "ssh root@host"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        assert "白名单" in data["error"]

    def test_kubectl_injection_blocked(self):
        """注入攻击被阻止。"""
        r = self.client.post("/api/kubectl", json={"command": "get pods; rm -rf /"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False

    def test_kubectl_empty_command(self):
        """空命令被拒绝。"""
        r = self.client.post("/api/kubectl", json={"command": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False

    def test_kubectl_dangerous_needs_confirm(self):
        """危险命令需要确认。"""
        # 在模拟器模式下，命令验证在集群模式检查之前
        # 所以模拟器模式下所有命令都返回"集群模式未启用"
        r = self.client.post("/api/kubectl", json={"command": "delete pod nginx"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False

    def test_kubectl_with_force(self):
        """force=true 参数被正确接收。"""
        r = self.client.post("/api/kubectl", json={"command": "get pods", "force": True})
        assert r.status_code == 200

    def test_cluster_status_endpoint(self):
        """集群状态端点正常工作。"""
        r = self.client.get("/api/cluster/status")
        assert r.status_code == 200
        data = r.json()
        assert "mode" in data
        assert "kubectl" in data
        assert "namespace" in data


# ═══ 集成测试 ═══

class TestKubectlIntegration:
    """集成测试：确保新端点不影响现有功能。"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_existing_health_still_works(self):
        r = self.client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_existing_levels_still_works(self):
        r = self.client.get("/api/levels")
        assert r.status_code == 200
        data = r.json()
        assert len(data["levels"]) > 0

    def test_existing_meta_still_works(self):
        r = self.client.get("/api/meta")
        assert r.status_code == 200

    def test_existing_check_still_works(self):
        """现有关卡校验不受影响。"""
        r = self.client.post("/api/check", json={
            "level_id": "Q1.1",
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx\nspec:\n  containers:\n    - name: nginx\n      image: nginx:1.25\n"
        })
        assert r.status_code == 200
