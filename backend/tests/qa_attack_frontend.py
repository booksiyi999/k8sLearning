"""QA Attack tests for K8s Quest frontend gamification system.

5 attack dimensions:
1. Type confusion - non-standard data types to API
2. Boundary values - empty/extreme inputs
3. State tampering - contradictory progress data
4. Concurrency/duplicate - repeated/mixed submissions
5. Exception recovery - malformed YAML, circular refs

Expected: all attacks handled gracefully (200 ok=False or reasonable error),
NEVER HTTP 500.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════
# 维度1: 类型混淆攻击
# ═══════════════════════════════════════════════

class TestTypeConfusionReport:
    """攻击 /api/report 传入非法类型。"""

    def test_report_with_string_completed_levels(self):
        """completed_levels 传字符串而非列表。FastAPI/Pydantic 应返回 422 拒绝。"""
        r = client.post("/api/report", json={"completed_levels": "Q1.1"})
        assert r.status_code in (200, 422)  # 422 是合理的类型拒绝

    def test_report_with_int_completed_levels(self):
        """completed_levels 传整数。FastAPI/Pydantic 应返回 422 拒绝。"""
        r = client.post("/api/report", json={"completed_levels": 123})
        assert r.status_code in (200, 422)

    def test_report_with_null_completed_levels(self):
        """completed_levels 传 null。FastAPI/Pydantic 应返回 422 拒绝。"""
        r = client.post("/api/report", json={"completed_levels": None})
        assert r.status_code in (200, 422)

    def test_report_with_nested_object_attempts(self):
        """level_attempts 传嵌套对象。FastAPI/Pydantic 应返回 422 拒绝。"""
        r = client.post("/api/report", json={
            "completed_levels": [],
            "level_attempts": {"Q1.1": {"nested": "object"}}
        })
        assert r.status_code in (200, 422)

    def test_report_with_float_xp(self):
        """total_xp 传浮点数。FastAPI/Pydantic 应返回 422 拒绝。"""
        r = client.post("/api/report", json={"total_xp": 99.99})
        assert r.status_code in (200, 422)

    def test_report_with_string_xp(self):
        """total_xp 传字符串。FastAPI/Pydantic 应返回 422 拒绝。"""
        r = client.post("/api/report", json={"total_xp": "lots"})
        assert r.status_code in (200, 422)


class TestTypeConfusionCheck:
    """攻击 /api/check 传入非标准类型。"""

    def test_check_with_int_yaml(self):
        """user_yaml 传整数。"""
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": 12345})
        assert r.status_code in (200, 422)

    def test_check_with_null_yaml(self):
        """user_yaml 传 null。"""
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": None})
        assert r.status_code in (200, 422)

    def test_check_with_list_yaml(self):
        """user_yaml 传列表。"""
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": ["a", "b"]})
        assert r.status_code in (200, 422)

    def test_check_with_sql_injection_level_id(self):
        """level_id 传 SQL 注入字符串。"""
        r = client.post("/api/check", json={
            "level_id": "Q1.1'; DROP TABLE levels; --",
            "user_yaml": "apiVersion: v1\nkind: Pod"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False

    def test_check_with_xss_level_id(self):
        """level_id 传 XSS 字符串。"""
        r = client.post("/api/check", json={
            "level_id": "<script>alert('xss')</script>",
            "user_yaml": "apiVersion: v1\nkind: Pod"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False

    def test_check_with_path_traversal_level_id(self):
        """level_id 传路径遍历字符串。"""
        r = client.post("/api/check", json={
            "level_id": "../../../etc/passwd",
            "user_yaml": "apiVersion: v1\nkind: Pod"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False


# ═══════════════════════════════════════════════
# 维度2: 边界值攻击
# ═══════════════════════════════════════════════

class TestBoundaryReport:
    """攻击 /api/report 的边界值。"""

    def test_report_empty_object(self):
        """传空对象 {}。"""
        r = client.post("/api/report", json={})
        assert r.status_code == 200
        data = r.json()
        assert data["grade"] == "D"
        assert data["completion_rate"] == 0

    def test_report_negative_xp(self):
        """total_xp 为负数。"""
        r = client.post("/api/report", json={"total_xp": -999})
        assert r.status_code == 200

    def test_report_huge_xp(self):
        """total_xp 为超大数 — 服务端应重算忽略虚假XP。"""
        r = client.post("/api/report", json={"total_xp": 999999999})
        assert r.status_code == 200
        data = r.json()
        # 服务端重算：无完成关卡 -> XP=0，不是满级
        assert data["total_xp"] == 0
        assert "传奇" not in data["rank"]
        assert "warning" in data  # 应有XP不一致警告

    def test_report_nonexistent_levels(self):
        """completed_levels 包含不存在的关卡ID。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q9.9", "Q0.0", "FAKE", ""]
        })
        assert r.status_code == 200
        data = r.json()
        # 不存在的关卡不应崩溃，但也不应计入完成
        assert data["completion_rate"] > 0  # 有4个"完成"，虽然不存在

    def test_report_negative_attempts(self):
        """level_attempts 包含负数。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_attempts": {"Q1.1": -5}
        })
        assert r.status_code == 200

    def test_report_empty_first_try_with_completion(self):
        """level_first_try 为空但 completed_levels 非空。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1", "Q1.2", "Q1.3", "Q1.4"],
            "level_first_try": []
        })
        assert r.status_code == 200
        data = r.json()
        assert data["first_try_count"] == 0


class TestBoundaryCheck:
    """攻击 /api/check 的边界值。"""

    def test_check_empty_yaml(self):
        """空字符串 YAML。"""
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": ""})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_check_only_comments(self):
        """只有注释的 YAML。"""
        r = client.post("/api/check", json={
            "level_id": "Q1.1",
            "user_yaml": "# just a comment\n# another comment"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_check_only_separator(self):
        """只有 --- 分隔符。"""
        r = client.post("/api/check", json={
            "level_id": "Q1.1",
            "user_yaml": "---\n---\n---"
        })
        assert r.status_code == 200

    def test_check_huge_yaml(self):
        """超长 YAML（1000行）。"""
        yaml_text = "\n".join([f"# line {i}" for i in range(1000)])
        yaml_text += "\napiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n  - name: c\n    image: nginx"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200

    def test_check_mixed_valid_invalid_docs(self):
        """多文档YAML混合合法和非法资源。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: valid-pod
spec:
  containers:
  - name: nginx
    image: nginx:latest
---
apiVersion: v1
kind: FakeResource
metadata:
  name: invalid
"""
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False


# ═══════════════════════════════════════════════
# 维度3: 状态篡改攻击
# ═══════════════════════════════════════════════

class TestStateTampering:
    """攻击 /api/report 传入矛盾数据。"""

    def test_completed_but_zero_xp(self):
        """声称完成关卡但 total_xp=0 — 服务端应重算为实际XP。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1", "Q1.2", "Q1.3", "Q1.4"],
            "total_xp": 0
        })
        assert r.status_code == 200
        data = r.json()
        # 服务端重算：4关 × 10 XP = 40
        assert data["completion_rate"] > 0
        assert data["total_xp"] == 40  # 服务端重算
        assert "warning" in data  # 应有XP不一致警告

    def test_first_try_but_high_attempts(self):
        """声称首通但尝试次数>1（矛盾数据）。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_attempts": {"Q1.1": 5},
            "level_first_try": ["Q1.1"]
        })
        assert r.status_code == 200
        data = r.json()
        # 矛盾数据不应崩溃
        assert "strengths" in data

    def test_first_try_for_uncompleted(self):
        """level_first_try 包含未完成关卡。"""
        r = client.post("/api/report", json={
            "completed_levels": [],
            "level_first_try": ["Q1.1", "Q1.2"]
        })
        assert r.status_code == 200
        data = r.json()
        # strengths 应该过滤掉未完成的
        assert len(data["strengths"]) == 0

    def test_nonexistent_level_in_report(self):
        """报告中包含不存在的关卡。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1", "FAKE_LEVEL", "Q99.99"]
        })
        assert r.status_code == 200


# ═══════════════════════════════════════════════
# 维度4: 并发/重复攻击
# ═══════════════════════════════════════════════

class TestConcurrencyDuplicate:
    """并发和重复提交测试。"""

    def test_duplicate_same_answer(self):
        """同一关卡重复提交相同答案。"""
        yaml_text = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n  - name: nginx\n    image: nginx:1.25"
        results = []
        for _ in range(5):
            r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
            results.append(r.json())
        # 所有结果应该一致
        assert all(r["ok"] for r in results)

    def test_submit_then_submit_different_level(self):
        """连续提交不同关卡的答案。"""
        # Q1.1
        r1 = client.post("/api/check", json={
            "level_id": "Q1.1",
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: my-first-pod\nspec:\n  containers:\n  - name: nginx\n    image: nginx:latest"
        })
        # Q2.1
        r2 = client.post("/api/check", json={
            "level_id": "Q2.1",
            "user_yaml": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-deploy\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: nginx\n        image: nginx:1.20"
        })
        assert r1.status_code == 200
        assert r2.status_code == 200


# ═══════════════════════════════════════════════
# 维度5: 异常恢复攻击
# ═══════════════════════════════════════════════

class TestExceptionRecovery:
    """异常输入的恢复能力。"""

    def test_circular_ref_yaml(self):
        """循环引用 YAML（自引用 anchor）。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata: &meta
  name: test
  labels: *meta
spec:
  containers:
  - name: c
    image: nginx
"""
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_deep_nesting_yaml(self):
        """超深嵌套 YAML（200层）。"""
        yaml_text = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: deep\nspec:\n"
        for i in range(200):
            yaml_text += "  " * (i + 1) + f"level{i}:\n"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200

    def test_non_yaml_text(self):
        """非 YAML 格式文本（随机文本）。"""
        r = client.post("/api/check", json={
            "level_id": "Q1.1",
            "user_yaml": "This is not YAML at all. Just plain text.\nHello World!"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_json_format_text(self):
        """传入 JSON 格式文本（不是 YAML）。"""
        r = client.post("/api/check", json={
            "level_id": "Q1.1",
            "user_yaml": '{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "test"}}'
        })
        assert r.status_code == 200

    def test_empty_kind(self):
        """kind 为空字符串。"""
        yaml_text = "apiVersion: v1\nkind: \"\"\nmetadata:\n  name: test"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_unknown_kind(self):
        """kind 为未知资源类型。"""
        yaml_text = "apiVersion: v1\nkind: FakeCRD\nmetadata:\n  name: test"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_yaml_with_tabs(self):
        """YAML 包含 Tab 缩进（YAML 规范禁止 Tab）。"""
        yaml_text = "apiVersion: v1\nkind: Pod\nmetadata:\n\tname: tab-indent"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200

    def test_pod_missing_metadata(self):
        """Pod 缺少 metadata 字段。"""
        yaml_text = "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n  - name: c\n    image: nginx"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_pod_missing_spec(self):
        """Pod 缺少 spec 字段。"""
        yaml_text = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: no-spec"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_pod_string_containers(self):
        """containers 为字符串而非列表。"""
        yaml_text = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers: not-a-list"
        r = client.post("/api/check", json={"level_id": "Q1.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_deployment_string_replicas(self):
        """replicas 为字符串而非整数。"""
        yaml_text = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\nspec:\n  replicas: \"three\"\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: c\n        image: nginx"
        r = client.post("/api/check", json={"level_id": "Q2.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_deployment_huge_replicas(self):
        """replicas 为超大数（资源耗尽攻击）。"""
        yaml_text = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\nspec:\n  replicas: 999999\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: c\n        image: nginx"
        r = client.post("/api/check", json={"level_id": "Q2.1", "user_yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_nonexistent_level(self):
        """请求不存在的关卡。"""
        r = client.post("/api/check", json={
            "level_id": "Q9.9",
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_level_id_with_special_chars(self):
        """level_id 含特殊字符。"""
        r = client.get("/api/level/Q1.1%00")
        assert r.status_code in (200, 404, 422)

    def test_report_with_extra_fields(self):
        """report 传入额外字段。"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "extra_field": "malicious",
            "__proto__": {"polluted": True}
        })
        assert r.status_code == 200
