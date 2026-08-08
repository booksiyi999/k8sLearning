"""Tests for Chapter 0: K8s 架构总览 (Q0.1 - Q0.3)."""
import pytest
from app.validator import get_level, list_levels, CheckResult


# ---------------- 关卡存在性测试 ----------------

def test_chapter_0_has_3_levels():
    """Chapter 0 应该有 3 个关卡"""
    levels = list_levels(chapter="ch00")
    assert len(levels) == 3, f"Expected 3 ch00 levels, got {len(levels)}"


def test_all_chapter_0_levels_exist():
    """所有 Q0.x 关卡都应该可获取"""
    for lid in ["Q0.1", "Q0.2", "Q0.3"]:
        lv = get_level(lid)
        assert lv is not None, f"Level {lid} should exist"
        assert lv.chapter == "ch00"


def test_ch00_metadata_exists():
    """ch00 元数据应该存在"""
    from app.metadata import CHAPTERS_META, LEVEL_XP, KNOWLEDGE_POINTS, KNOWLEDGE_DOMAINS
    assert "ch00" in CHAPTERS_META
    assert CHAPTERS_META["ch00"]["title"] == "K8s 架构总览"
    assert CHAPTERS_META["ch00"]["icon"] == "🏗️"
    assert CHAPTERS_META["ch00"]["color"] == "#6366f1"
    assert CHAPTERS_META["ch00"]["difficulty"] == "入门"
    for lid in ["Q0.1", "Q0.2", "Q0.3"]:
        assert lid in LEVEL_XP
        assert lid in KNOWLEDGE_POINTS
    assert "架构基础" in KNOWLEDGE_DOMAINS
    assert KNOWLEDGE_DOMAINS["架构基础"] == ["Q0.1", "Q0.2", "Q0.3"]


# ---------------- Q0.1 测试 ----------------

_Q0_1_CORRECT = """\
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    node-role.kubernetes.io/control-plane: ""
---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    node-role.kubernetes.io/worker: ""
"""


def test_q0_1_correct_answer_passes():
    """两个 Node + 正确标签 -> 通过"""
    lv = get_level("Q0.1")
    result = lv.check_fn(_Q0_1_CORRECT)
    assert result.ok is True
    assert "control-plane-node" in result.state.nodes
    assert "worker-node-1" in result.state.nodes


def test_q0_1_missing_worker_node_fails():
    """只创建一个 Node -> 失败"""
    lv = get_level("Q0.1")
    yaml = """\
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    node-role.kubernetes.io/control-plane: ""
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "2" in result.error


def test_q0_1_missing_control_plane_label_fails():
    """控制面节点缺少角色标签 -> 失败"""
    lv = get_level("Q0.1")
    yaml = """\
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    foo: bar
---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    node-role.kubernetes.io/worker: ""
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "control-plane" in result.error.lower() or "角色" in result.error


def test_q0_1_missing_worker_label_fails():
    """工作节点缺少角色标签 -> 失败"""
    lv = get_level("Q0.1")
    yaml = """\
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    node-role.kubernetes.io/control-plane: ""
---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    foo: bar
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "worker" in result.error.lower() or "角色" in result.error


def test_q0_1_wrong_node_name_fails():
    """Node 名称不对 -> 失败"""
    lv = get_level("Q0.1")
    yaml = """\
apiVersion: v1
kind: Node
metadata:
  name: master-node
  labels:
    node-role.kubernetes.io/control-plane: ""
---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    node-role.kubernetes.io/worker: ""
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "control-plane-node" in result.error


# ---------------- Q0.2 测试 ----------------

_Q0_2_CORRECT = """\
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


def test_q0_2_correct_answer_passes():
    """Deployment replicas=3 + nginx:1.25 -> 通过，且 K8s 自动创建 3 个 Pod"""
    lv = get_level("Q0.2")
    result = lv.check_fn(_Q0_2_CORRECT)
    assert result.ok is True
    assert "web-deploy" in result.state.deployments
    # K8s 应自动创建 3 个 Pod（声明式的体现）
    deploy_pods = [
        name for name, pod in result.state.pods.items()
        if pod.get("metadata", {}).get("labels", {}).get("pod-template-hash") == "web-deploy"
    ]
    assert len(deploy_pods) == 3


def test_q0_2_wrong_replicas_fails():
    """replicas != 3 -> 失败"""
    lv = get_level("Q0.2")
    yaml = _Q0_2_CORRECT.replace("replicas: 3", "replicas: 2")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "3" in result.error


def test_q0_2_wrong_image_fails():
    """镜像不对 -> 失败"""
    lv = get_level("Q0.2")
    yaml = _Q0_2_CORRECT.replace("nginx:1.25", "nginx:1.24")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.25" in result.error


def test_q0_2_missing_deployment_fails():
    """没有创建 Deployment -> 失败"""
    lv = get_level("Q0.2")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: web-deploy
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "web-deploy" in result.error
    assert "Deployment" in result.error


# ---------------- Q0.3 测试 ----------------

_Q0_3_CORRECT = """\
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod
  labels:
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc
spec:
  selector:
    app: api-demo
  ports:
  - port: 80
    targetPort: 80
"""


def test_q0_3_correct_answer_passes():
    """Pod + Service 都正确 -> 通过"""
    lv = get_level("Q0.3")
    result = lv.check_fn(_Q0_3_CORRECT)
    assert result.ok is True
    assert "api-demo-pod" in result.state.pods
    assert "api-demo-svc" in result.state.services


def test_q0_3_missing_service_fails():
    """只有 Pod 没有 Service -> 失败"""
    lv = get_level("Q0.3")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod
  labels:
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "api-demo-svc" in result.error


def test_q0_3_missing_pod_fails():
    """只有 Service 没有 Pod -> 失败"""
    lv = get_level("Q0.3")
    yaml = """\
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc
spec:
  selector:
    app: api-demo
  ports:
  - port: 80
    targetPort: 80
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "api-demo-pod" in result.error


def test_q0_3_selector_mismatch_fails():
    """Service selector 与 Pod labels 不匹配 -> 失败"""
    lv = get_level("Q0.3")
    yaml = _Q0_3_CORRECT.replace(
        "selector:\n    app: api-demo",
        "selector:\n    app: wrong-app"
    )
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "api-demo" in result.error
    assert "selector" in result.error.lower()


def test_q0_3_wrong_pod_label_fails():
    """Pod 标签不对 -> 失败"""
    lv = get_level("Q0.3")
    yaml = _Q0_3_CORRECT.replace(
        "labels:\n    app: api-demo\nspec:\n  containers:\n  - name: nginx\n    image: nginx:1.25",
        "labels:\n    app: wrong\nspec:\n  containers:\n  - name: nginx\n    image: nginx:1.25"
    )
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "api-demo" in result.error


def test_q0_3_wrong_image_fails():
    """Pod 镜像不对 -> 失败"""
    lv = get_level("Q0.3")
    yaml = _Q0_3_CORRECT.replace("nginx:1.25", "nginx:1.24")
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "nginx:1.25" in result.error


def test_q0_3_missing_ports_fails():
    """Service 缺少 ports -> 失败"""
    lv = get_level("Q0.3")
    yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod
  labels:
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc
spec:
  selector:
    app: api-demo
"""
    result = lv.check_fn(yaml)
    assert result.ok is False
    assert "ports" in result.error.lower()
