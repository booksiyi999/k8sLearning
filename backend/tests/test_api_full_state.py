"""测试 /api/check 的 cluster_state 返回全部资源类型。

架构师 D04: /api/check 和 /api/deploy 的响应中 cluster_state 只返回
pods/deployments/services 三种资源，其余 28 种资源对前端不可见。

修复后 cluster_state 应动态遍历 ClusterState 的所有非空字段。
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_check_returns_configmap():
    """提交 ConfigMap YAML -> cluster_state 包含 configmaps。"""
    r = client.post("/api/check", json={
        "level_id": "Q4.1",
        "user_yaml": (
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            "metadata:\n"
            "  name: app-config\n"
            "data:\n"
            "  APP_MODE: production\n"
            "  LOG_LEVEL: info\n"
        ),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    cs = data["cluster_state"]
    assert cs is not None
    assert "configmaps" in cs
    assert "app-config" in cs["configmaps"]


def test_check_returns_networkpolicy():
    """提交 NetworkPolicy YAML -> cluster_state 包含 networkpolicies。"""
    r = client.post("/api/check", json={
        "level_id": "Q12.1",
        "user_yaml": (
            "apiVersion: networking.k8s.io/v1\n"
            "kind: NetworkPolicy\n"
            "metadata:\n"
            "  name: default-deny\n"
            "spec:\n"
            "  podSelector: {}\n"
            "  policyTypes:\n"
            "    - Ingress\n"
        ),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    cs = data["cluster_state"]
    assert cs is not None
    assert "networkpolicies" in cs
    assert "default-deny" in cs["networkpolicies"]


def test_check_returns_multiple():
    """提交多文档 YAML -> cluster_state 包含多种资源。"""
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": (
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n"
            "  name: nginx-pod\n"
            "spec:\n"
            "  containers:\n"
            "    - name: nginx\n"
            "      image: nginx:1.25\n"
            "---\n"
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            "metadata:\n"
            "  name: extra-config\n"
            "data:\n"
            "  key: value\n"
        ),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    cs = data["cluster_state"]
    assert cs is not None
    # Pod 和 ConfigMap 都应该出现
    assert "pods" in cs
    assert "nginx-pod" in cs["pods"]
    assert "configmaps" in cs
    assert "extra-config" in cs["configmaps"]
    # 空的资源类型不应出现
    assert "deployments" not in cs
    assert "services" not in cs


def test_check_empty_state():
    """无资源的关卡 (校验失败, 无 state) -> cluster_state 为 None。"""
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": "this is not valid yaml",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    # 校验失败时 result.state 为 None -> cluster_state 应为 None
    assert data["cluster_state"] is None
