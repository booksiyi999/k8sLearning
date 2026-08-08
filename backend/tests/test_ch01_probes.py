"""Tests for Chapter 1 Probe levels (Q1.6 - livenessProbe, Q1.7 - dual probes)."""
import pytest
from app.validator import get_level, list_levels, CheckResult


# ---------------- 关卡存在性测试 ----------------

def test_ch01_has_7_levels():
    """Chapter 1 应该有 7 个关卡（含集群实战 Q1.5）"""
    levels = list_levels(chapter="ch01")
    assert len(levels) == 7, f"Expected 7 ch01 levels, got {len(levels)}"


def test_q1_6_and_q1_7_exist():
    """Q1.6 和 Q1.7 关卡都应该可获取"""
    for lid in ["Q1.6", "Q1.7"]:
        lv = get_level(lid)
        assert lv is not None, f"Level {lid} should exist"
        assert lv.chapter == "ch01"
        assert lv.lesson is not None, f"Level {lid} should have a lesson"


def test_q1_6_has_lesson_with_all_fields():
    """Q1.6 的 Lesson 对象应包含所有必需字段"""
    lv = get_level("Q1.6")
    assert lv is not None
    lesson = lv.lesson
    assert lesson is not None
    assert len(lesson.concept) > 100
    assert len(lesson.key_fields) >= 5
    assert len(lesson.diagram) > 50
    assert len(lesson.example_yaml) > 50
    assert len(lesson.common_errors) >= 3
    assert len(lesson.tips) >= 3


def test_q1_7_has_lesson_with_all_fields():
    """Q1.7 的 Lesson 对象应包含所有必需字段"""
    lv = get_level("Q1.7")
    assert lv is not None
    lesson = lv.lesson
    assert lesson is not None
    assert len(lesson.concept) > 100
    assert len(lesson.key_fields) >= 5
    assert len(lesson.diagram) > 50
    assert len(lesson.example_yaml) > 50
    assert len(lesson.common_errors) >= 3
    assert len(lesson.tips) >= 3


# ---------------- Q1.6 测试 ----------------

_Q1_6_HTTPGET = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /
          port: 80
        initialDelaySeconds: 5
        periodSeconds: 10
"""

_Q1_6_TCPSOCKET = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        tcpSocket:
          port: 80
        initialDelaySeconds: 3
"""

_Q1_6_EXEC = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        exec:
          command:
            - /bin/sh
            - -c
            - "pgrep nginx"
"""


def test_q1_6_httpget_passes():
    """httpGet 类型 livenessProbe -> 通过"""
    lv = get_level("Q1.6")
    result = lv.check_fn(_Q1_6_HTTPGET)
    assert result.ok is True
    assert "probe-pod" in result.state.pods


def test_q1_6_tcpsocket_passes():
    """tcpSocket 类型 livenessProbe -> 通过"""
    lv = get_level("Q1.6")
    result = lv.check_fn(_Q1_6_TCPSOCKET)
    assert result.ok is True


def test_q1_6_exec_passes():
    """exec 类型 livenessProbe -> 通过"""
    lv = get_level("Q1.6")
    result = lv.check_fn(_Q1_6_EXEC)
    assert result.ok is True


def test_q1_6_missing_liveness_fails():
    """没有 livenessProbe -> 失败"""
    lv = get_level("Q1.6")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "livenessProbe" in result.error


def test_q1_6_missing_probe_type_fails():
    """livenessProbe 存在但没有探针类型 -> 失败"""
    lv = get_level("Q1.6")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        initialDelaySeconds: 5
        periodSeconds: 10
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "探针类型" in result.error


def test_q1_6_wrong_pod_name_fails():
    """Pod 名字不对 -> 失败"""
    lv = get_level("Q1.6")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: wrong-name
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "probe-pod" in result.error


def test_q1_6_multiple_probe_types_fails():
    """同时配置多种探针类型 -> 失败"""
    lv = get_level("Q1.6")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /
          port: 80
        tcpSocket:
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "一种" in result.error


def test_q1_6_liveness_is_string_does_not_crash():
    """livenessProbe 是字符串而非 dict -> 失败但不崩溃"""
    lv = get_level("Q1.6")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe: "not-a-dict"
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "livenessProbe" in result.error


def test_q1_6_invalid_yaml_fails():
    """无效 YAML -> 失败但不崩溃"""
    lv = get_level("Q1.6")
    result = lv.check_fn("this is not: valid: yaml: [")
    assert result.ok is False


# ---------------- Q1.7 测试 ----------------

_Q1_7_CORRECT = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /health
          port: 80
        initialDelaySeconds: 5
        periodSeconds: 10
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /ready
          port: 80
        initialDelaySeconds: 3
        periodSeconds: 5
        failureThreshold: 1
"""

_Q1_7_TCP_BOTH = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        tcpSocket:
          port: 80
      readinessProbe:
        tcpSocket:
          port: 80
"""


def test_q1_7_correct_answer_passes():
    """完整的 liveness + readiness 双探针 -> 通过"""
    lv = get_level("Q1.7")
    result = lv.check_fn(_Q1_7_CORRECT)
    assert result.ok is True
    assert "health-pod" in result.state.pods


def test_q1_7_tcp_both_passes():
    """tcpSocket 类型双探针 -> 通过"""
    lv = get_level("Q1.7")
    result = lv.check_fn(_Q1_7_TCP_BOTH)
    assert result.ok is True


def test_q1_7_missing_readiness_fails():
    """只有 liveness 没有 readiness -> 失败"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "readinessProbe" in result.error


def test_q1_7_missing_liveness_fails():
    """只有 readiness 没有 liveness -> 失败"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      readinessProbe:
        httpGet:
          path: /
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "livenessProbe" in result.error


def test_q1_7_no_probes_fails():
    """两个探针都没有 -> 失败"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "livenessProbe" in result.error


def test_q1_7_wrong_pod_name_fails():
    """Pod 名字不对 -> 失败"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: wrong-name
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /
          port: 80
      readinessProbe:
        httpGet:
          path: /
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "health-pod" in result.error


def test_q1_7_liveness_missing_type_fails():
    """livenessProbe 存在但缺少探针类型 -> 失败"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        initialDelaySeconds: 5
      readinessProbe:
        httpGet:
          path: /
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "livenessProbe" in result.error
    assert "探针类型" in result.error


def test_q1_7_readiness_missing_type_fails():
    """readinessProbe 存在但缺少探针类型 -> 失败"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        httpGet:
          path: /
          port: 80
      readinessProbe:
        initialDelaySeconds: 3
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "readinessProbe" in result.error
    assert "探针类型" in result.error


def test_q1_7_liveness_is_list_does_not_crash():
    """livenessProbe 是列表而非 dict -> 失败但不崩溃"""
    lv = get_level("Q1.7")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      livenessProbe:
        - "not-a-dict"
      readinessProbe:
        httpGet:
          path: /
          port: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "livenessProbe" in result.error


def test_q1_7_invalid_yaml_fails():
    """无效 YAML -> 失败但不崩溃"""
    lv = get_level("Q1.7")
    result = lv.check_fn("{ invalid: yaml: [")
    assert result.ok is False
