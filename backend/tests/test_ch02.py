"""Tests for Chapter 2 levels (Q2.1 - Q2.4)."""
import pytest
from app.validator import get_level, list_levels, CheckResult


# ---------------- Q2.1 测试 ----------------

_Q2_1_CORRECT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
"""


def test_q2_1_correct_answer_passes():
    lv = get_level("Q2.1")
    result = lv.check_fn(_Q2_1_CORRECT)
    assert result.ok is True
    assert "nginx-deploy" in result.state.deployments


def test_q2_1_wrong_replicas_fails():
    lv = get_level("Q2.1")
    yaml = _Q2_1_CORRECT.replace("replicas: 3", "replicas: 2")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "replicas" in result.error
    assert "3" in result.error


def test_q2_1_wrong_image_fails():
    lv = get_level("Q2.1")
    yaml = _Q2_1_CORRECT.replace("nginx:1.25", "nginx:1.24")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.25" in result.error


def test_q2_1_missing_selector_fails():
    lv = get_level("Q2.1")
    yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "selector" in result.error.lower()


def test_q2_1_wrong_name_fails():
    lv = get_level("Q2.1")
    yaml = _Q2_1_CORRECT.replace("name: nginx-deploy", "name: my-deploy")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx-deploy" in result.error


def test_q2_1_containers_is_string_does_not_crash():
    """template.spec.containers 是字符串而非 list → 失败但不崩溃（类型守卫）"""
    lv = get_level("Q2.1")
    yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers: "not-a-list"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "containers" in result.error.lower()


def test_q2_1_template_spec_is_string_does_not_crash():
    """spec.template.spec 是字符串而非 dict → 失败但不崩溃（类型守卫）"""
    lv = get_level("Q2.1")
    yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec: "broken"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False


def test_q2_1_pod_count_matches_replicas():
    """simulator 应按 replicas 实例化 3 个 Pod"""
    lv = get_level("Q2.1")
    result = lv.check_fn(_Q2_1_CORRECT)
    assert result.ok is True
    deploy_pods = [n for n in result.state.pods if n.startswith("nginx-deploy-")]
    assert len(deploy_pods) == 3


# ---------------- Q2.2 测试 ----------------

_Q2_2_CORRECT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deploy
spec:
  replicas: 5
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: python:3.11-slim
"""


def test_q2_2_correct_answer_passes():
    lv = get_level("Q2.2")
    result = lv.check_fn(_Q2_2_CORRECT)
    assert result.ok is True
    assert "api-deploy" in result.state.deployments


def test_q2_2_wrong_replicas_fails():
    lv = get_level("Q2.2")
    yaml = _Q2_2_CORRECT.replace("replicas: 5", "replicas: 3")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "replicas" in result.error
    assert "5" in result.error


def test_q2_2_wrong_image_fails():
    lv = get_level("Q2.2")
    yaml = _Q2_2_CORRECT.replace("python:3.11-slim", "python:3.12-slim")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "python:3.11-slim" in result.error


def test_q2_2_wrong_name_fails():
    lv = get_level("Q2.2")
    yaml = _Q2_2_CORRECT.replace("name: api-deploy", "name: web-deploy")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "api-deploy" in result.error


def test_q2_2_replicas_as_string_rejected_by_simulator():
    """replicas: \"5\" 字符串 → simulator 校验拒绝 → check_fn 返回失败但不崩溃"""
    lv = get_level("Q2.2")
    yaml = _Q2_2_CORRECT.replace("replicas: 5", 'replicas: "5"')
    result = lv.check_fn(yaml)
    assert result.ok is False


def test_q2_2_pod_count_matches_replicas():
    """simulator 应按 replicas 实例化 5 个 Pod"""
    lv = get_level("Q2.2")
    result = lv.check_fn(_Q2_2_CORRECT)
    assert result.ok is True
    deploy_pods = [n for n in result.state.pods if n.startswith("api-deploy-")]
    assert len(deploy_pods) == 5


# ---------------- Q2.3 测试 ----------------

_Q2_3_UPGRADE = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 3
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
          image: nginx:1.25
"""


def test_q2_3_correct_upgrade_passes():
    """升级到 nginx:1.25 → 通过"""
    lv = get_level("Q2.3")
    result = lv.check_fn(_Q2_3_UPGRADE)
    assert result.ok is True
    # 所有 Pod 都应该是 nginx:1.25
    web_pods = [p for p in result.state.pods.values()
                if isinstance(p.get("metadata", {}).get("labels"), dict)
                and p["metadata"]["labels"].get("pod-template-hash") == "web-deploy"]
    assert len(web_pods) == 3
    for p in web_pods:
        assert p["spec"]["containers"][0]["image"] == "nginx:1.25"


def test_q2_3_image_not_changed_fails():
    """玩家没改 image（还是 nginx:1.24）→ 失败"""
    lv = get_level("Q2.3")
    yaml = _Q2_3_UPGRADE.replace("nginx:1.25", "nginx:1.24")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.24" in result.error


def test_q2_3_wrong_new_image_fails():
    """改成了错误的版本（nginx:1.26）→ 失败"""
    lv = get_level("Q2.3")
    yaml = _Q2_3_UPGRADE.replace("nginx:1.25", "nginx:1.26")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.25" in result.error


def test_q2_3_wrong_deployment_name_fails():
    """玩家新建了别的 Deployment（没更新 web-deploy）→ 失败"""
    lv = get_level("Q2.3")
    yaml = _Q2_3_UPGRADE.replace("name: web-deploy", "name: my-deploy")
    result = lv.check_fn(yaml)
    assert result.ok is False
    # web-deploy 还停在 nginx:1.24
    assert "nginx:1.24" in result.error or "web-deploy" in result.error


def test_q2_3_revision_history_recorded():
    """升级后应有 ≥2 个 revision（v1 + v2）"""
    lv = get_level("Q2.3")
    result = lv.check_fn(_Q2_3_UPGRADE)
    assert result.ok is True
    revs = result.state.revisions.get("web-deploy", [])
    assert len(revs) >= 2
    # 第一个 revision 是 v1 (nginx:1.24), 最后一个是升级后的
    assert revs[0]["image"] == "nginx:1.24"
    assert revs[-1]["image"] == "nginx:1.25"


def test_q2_3_preset_state_isolated():
    """每关的 preset 不应泄漏到其他关（独立 ClusterState）"""
    lv = get_level("Q2.3")
    result = lv.check_fn(_Q2_3_UPGRADE)
    assert result.ok is True
    # Q2.3 的 state 里只有 web-deploy，不应有 nginx-deploy / api-deploy
    assert "nginx-deploy" not in result.state.deployments
    assert "api-deploy" not in result.state.deployments


# ---------------- Q2.4 测试 ----------------

_Q2_4_ROLLBACK = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    k8s-quest/rollback: "true"
spec:
  replicas: 3
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
          image: nginx:1.24
"""


def test_q2_4_correct_rollback_passes():
    """回滚 annotation → image 回到 nginx:1.24 → 通过"""
    lv = get_level("Q2.4")
    result = lv.check_fn(_Q2_4_ROLLBACK)
    assert result.ok is True
    # 所有 Pod 都应该是 nginx:1.24
    web_pods = [p for p in result.state.pods.values()
                if isinstance(p.get("metadata", {}).get("labels"), dict)
                and p["metadata"]["labels"].get("pod-template-hash") == "web-deploy"]
    assert len(web_pods) == 3
    for p in web_pods:
        assert p["spec"]["containers"][0]["image"] == "nginx:1.24"


def test_q2_4_no_rollback_annotation_fails():
    """没加回滚 annotation（重提交坏版本）→ 还停在 nginx:9.99.99 → 失败"""
    lv = get_level("Q2.4")
    yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 3
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
          image: nginx:9.99.99
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:9.99.99" in result.error


def test_q2_4_no_rollback_annotation_but_correct_image_fails():
    """绕过修复: 直接提交 image=nginx:1.24（无 rollback annotation）→ 应回滚失败。

    旧实现只校验最终 image/pods/revisions, 不校验是否用了 rollback
    annotation。玩家不学回滚也能过关（静默 false-pass）。
    修复后必须 ok=False, 因为 Q2.4 的教学目标是"用 annotation 触发回滚"。
    """
    lv = get_level("Q2.4")
    yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 3
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
          image: nginx:1.24
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "rollback" in result.error.lower() or "annotation" in result.error.lower()


def test_q2_4_wrong_target_image_fails():
    """回滚到了错误版本（升级到 nginx:1.25 而非回滚到 1.24）→ 失败"""
    lv = get_level("Q2.4")
    yaml = _Q2_4_ROLLBACK.replace("image: nginx:1.24", "image: nginx:1.25")
    # 去掉 rollback annotation（让这变成普通升级而非回滚）
    yaml = yaml.replace('    k8s-quest/rollback: "true"\n', "")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.24" in result.error


def test_q2_4_revision_history_recorded():
    """回滚后应有 ≥3 个 revision（v1 → bad v2 → rollback v3）"""
    lv = get_level("Q2.4")
    result = lv.check_fn(_Q2_4_ROLLBACK)
    assert result.ok is True
    revs = result.state.revisions.get("web-deploy", [])
    assert len(revs) >= 3
    # revision 序列: 1.24 → 9.99.99 → 1.24(rollback)
    assert revs[0]["image"] == "nginx:1.24"
    assert revs[1]["image"] == "nginx:9.99.99"
    assert revs[-1]["image"] == "nginx:1.24"


def test_q2_4_rollback_wrong_name_caught():
    """回滚 YAML 写了别的 deployment 名 → simulator 报错 → check_fn 不崩溃"""
    lv = get_level("Q2.4")
    yaml = _Q2_4_ROLLBACK.replace("name: web-deploy", "name: other-deploy")
    result = lv.check_fn(yaml)
    assert result.ok is False


# ---------------- 关卡存在性测试（全部 4 关就绪后）----------------

def test_chapter_2_has_4_levels():
    """Chapter 2 应该有 4 个关卡"""
    levels = list_levels(chapter="ch02")
    assert len(levels) == 5, f"Expected 5 ch02 levels, got {len(levels)}"


def test_all_chapter_2_levels_exist():
    """所有 Q2.x 关卡都应该可获取"""
    for lid in ["Q2.1", "Q2.2", "Q2.3", "Q2.4", "Q2.5"]:
        lv = get_level(lid)
        assert lv is not None, f"Level {lid} should exist"
        assert lv.chapter == "ch02"


def test_list_levels_returns_all_chapters():
    """list_levels() 返回 ch01 + ch02 全部 8 关"""
    levels = list_levels()
    assert len(levels) == 60
    chapters = {lv["chapter"] for lv in levels}
    assert "ch01" in chapters
    assert "ch02" in chapters
    assert "ch03" in chapters
    assert "ch04" in chapters
    assert "ch05" in chapters
    assert "ch06" in chapters
