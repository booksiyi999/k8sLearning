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
