"""Tests for Chapter 1 levels (Q1.1 - Q1.3)."""
import pytest
from app.validator import get_level, list_levels, CheckResult


# ---------------- 关卡存在性测试 ----------------

def test_chapter_1_has_4_levels():
    """Chapter 1 应该有 4 个关卡"""
    levels = list_levels()
    assert len(levels) == 4, f"Expected 4 levels, got {len(levels)}"


def test_all_chapter_1_levels_exist():
    """所有 Q1.x 关卡都应该可获取"""
    for lid in ["Q1.1", "Q1.2", "Q1.3", "Q1.4"]:
        lv = get_level(lid)
        assert lv is not None, f"Level {lid} should exist"
        assert lv.chapter == "ch01"


# ---------------- Q1.1 测试 ----------------

def test_q1_1_correct_answer_passes():
    lv = get_level("Q1.1")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is True
    assert "nginx-pod" in result.state.pods


def test_q1_1_wrong_image_fails():
    lv = get_level("Q1.1")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.24
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.25" in result.error


def test_q1_1_wrong_name_fails():
    lv = get_level("Q1.1")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx-pod" in result.error


# ---------------- Q1.2 测试 ----------------

def test_q1_2_correct_answer_passes():
    lv = get_level("Q1.2")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels:
    app: cache
    tier: backend
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""
    result = lv.check_fn(yaml)
    assert result.ok is True


def test_q1_2_missing_labels_fails():
    lv = get_level("Q1.2")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "labels" in result.error.lower()


def test_q1_2_wrong_image_fails():
    lv = get_level("Q1.2")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels:
    app: cache
    tier: backend
spec:
  containers:
    - name: redis
      image: redis:latest
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "redis:7-alpine" in result.error


def test_q1_2_partial_labels_fails():
    """只打了一个 label，应该失败"""
    lv = get_level("Q1.2")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels:
    app: cache
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "tier=backend" in result.error


# ---------------- Q1.3 测试 ----------------

def test_q1_3_correct_answer_passes():
    lv = get_level("Q1.3")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  containers:
    - name: web
      image: nginx:1.25
    - name: logger
      image: busybox:1.36
"""
    result = lv.check_fn(yaml)
    assert result.ok is True


def test_q1_3_single_container_fails():
    """只放一个容器，应该失败"""
    lv = get_level("Q1.3")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  containers:
    - name: web
      image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "2" in result.error  # "需要 2 个容器"


def test_q1_3_wrong_container_name_fails():
    """容器名字不对"""
    lv = get_level("Q1.3")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  containers:
    - name: web
      image: nginx:1.25
    - name: log
      image: busybox:1.36
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "logger" in result.error


def test_q1_3_wrong_logger_image_fails():
    """logger 镜像不对"""
    lv = get_level("Q1.3")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  containers:
    - name: web
      image: nginx:1.25
    - name: logger
      image: alpine:3.18
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "busybox:1.36" in result.error


# ---------------- Q1.4 测试 ----------------

_Q1_4_CORRECT = """\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      resources:
        requests:
          cpu: "100m"
          memory: "128Mi"
        limits:
          cpu: "500m"
          memory: "256Mi"
"""


def test_q1_4_correct_answer_passes():
    """完整的 requests/limits 都正确 → 通过"""
    lv = get_level("Q1.4")
    result = lv.check_fn(_Q1_4_CORRECT)
    assert result.ok is True
    assert "resource-pod" in result.state.pods


def test_q1_4_missing_resources_fails():
    """完全没有 resources 字段 → 失败"""
    lv = get_level("Q1.4")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "resources" in result.error


def test_q1_4_wrong_cpu_request_fails():
    """CPU request 不是 100m → 失败"""
    lv = get_level("Q1.4")
    yaml = _Q1_4_CORRECT.replace('cpu: "100m"\n          memory: "128Mi"',
                                 'cpu: "200m"\n          memory: "128Mi"')
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "requests.cpu" in result.error
    assert "100m" in result.error


def test_q1_4_wrong_memory_request_fails():
    """memory request 不是 128Mi → 失败"""
    lv = get_level("Q1.4")
    yaml = _Q1_4_CORRECT.replace('memory: "128Mi"\n        limits:',
                                 'memory: "256Mi"\n        limits:')
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "requests.memory" in result.error
    assert "128Mi" in result.error


def test_q1_4_wrong_cpu_limit_fails():
    """CPU limit 不是 500m → 失败"""
    lv = get_level("Q1.4")
    yaml = _Q1_4_CORRECT.replace('cpu: "500m"\n          memory: "256Mi"',
                                 'cpu: "1000m"\n          memory: "256Mi"')
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "limits.cpu" in result.error
    assert "500m" in result.error


def test_q1_4_wrong_memory_limit_fails():
    """memory limit 不是 256Mi → 失败"""
    lv = get_level("Q1.4")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      resources:
        requests:
          cpu: "100m"
          memory: "128Mi"
        limits:
          cpu: "500m"
          memory: "512Mi"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "limits.memory" in result.error
    assert "256Mi" in result.error


def test_q1_4_missing_limits_fails():
    """只有 requests 没有 limits → 失败"""
    lv = get_level("Q1.4")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      resources:
        requests:
          cpu: "100m"
          memory: "128Mi"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "limits" in result.error


def test_q1_4_resources_is_string_does_not_crash():
    """resources 是字符串而非 dict → 失败但不崩溃（边界 B2）"""
    lv = get_level("Q1.4")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      resources: "not-a-dict"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "resources" in result.error


def test_q1_4_resources_is_list_does_not_crash():
    """resources 是列表而非 dict → 失败但不崩溃（边界 B3）"""
    lv = get_level("Q1.4")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      resources:
        - "not-a-dict"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "resources" in result.error
