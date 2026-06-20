import pytest
from app.simulator import apply_manifest, ClusterState, K8sError

def test_apply_pod_creates_pod_in_state():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = apply_manifest(state, yaml)
    assert "nginx-pod" in result.pods
    assert result.pods["nginx-pod"]["spec"]["containers"][0]["image"] == "nginx:1.25"

def test_apply_invalid_yaml_raises():
    state = ClusterState()
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, "this: is: not: valid: yaml: :::")
    assert "YAML 解析失败" in str(exc.value)

def test_apply_missing_required_field_raises():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "spec.containers" in str(exc.value)

def test_apply_unsupported_kind_raises():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Widget
metadata:
  name: x
spec:
  containers: []
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "Widget" in str(exc.value)

def test_apply_deployment_creates_replicasets_pods():
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
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
    result = apply_manifest(state, yaml)
    assert "web" in result.deployments
    # Deployment 创建 3 个虚拟 Pod
    pod_count = sum(1 for p in result.pods.values() if p["metadata"]["labels"].get("app") == "web")
    assert pod_count == 3
