"""模拟器升级测试：RBAC 权限检查 & NetworkPolicy 流量模拟

测试覆盖:
- simulate_rbac_check: SA + Role + RoleBinding 场景下的权限判定
- simulate_traffic: NetworkPolicy 流量模拟（默认允许/默认拒绝/白名单放行/端口不匹配）
"""
import pytest
from app.simulator import (
    ClusterState,
    apply_manifest,
    simulate_rbac_check,
    simulate_traffic,
)


# ===== RBAC 权限检查测试 =====


class TestSimulateRbacCheck:
    """simulate_rbac_check 测试"""

    def test_rbac_check(self):
        """创建 SA + Role + RoleBinding，验证 simulate_rbac_check 返回正确结果"""
        yaml_text = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: default
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # SA 被授予了 pods 的 get 权限
        assert simulate_rbac_check(state, "my-sa", "get", "pods") is True
        # SA 被授予了 services 的 list 权限
        assert simulate_rbac_check(state, "my-sa", "list", "services") is True
        # SA 没有被授予 pods 的 create 权限
        assert simulate_rbac_check(state, "my-sa", "create", "pods") is False
        # SA 没有被授予 deployments 的 get 权限
        assert simulate_rbac_check(state, "my-sa", "get", "deployments") is False

    def test_rbac_check_no_binding(self):
        """无绑定时返回 False"""
        yaml_text = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: lonely-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # Role 存在但没有 RoleBinding 绑定到 lonely-sa
        assert simulate_rbac_check(state, "lonely-sa", "get", "pods") is False

    def test_rbac_check_wildcard(self):
        """rules 含 '*' 时返回 True"""
        yaml_text = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-binding
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: admin-sa
  namespace: default
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # 通配符 '*' 匹配任何 verb 和 resource
        assert simulate_rbac_check(state, "admin-sa", "get", "pods") is True
        assert simulate_rbac_check(state, "admin-sa", "create", "deployments") is True
        assert simulate_rbac_check(state, "admin-sa", "delete", "nodes") is True
        assert simulate_rbac_check(state, "admin-sa", "watch", "secrets") is True


# ===== NetworkPolicy 流量模拟测试 =====


class TestSimulateTraffic:
    """simulate_traffic 测试"""

    def test_traffic_no_policy(self):
        """无 NetworkPolicy 时默认允许"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # 没有 NetworkPolicy -> 默认允许所有流量
        result = simulate_traffic(state, "web-pod", "db-pod", 5432)
        assert result["allowed"] is True
        assert result["matched_policies"] == []

    def test_traffic_default_deny(self):
        """有策略但不匹配时拒绝"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Ingress
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # 默认拒绝策略选择所有 Pod，但没有 ingress 规则 -> 拒绝所有入站
        result = simulate_traffic(state, "web-pod", "db-pod", 5432)
        assert result["allowed"] is False
        assert "default-deny" in result["matched_policies"]

    def test_traffic_allow(self):
        """策略匹配时允许"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-db
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    ports:
    - protocol: TCP
      port: 5432
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # web-pod -> db-pod:5432 被策略允许
        result = simulate_traffic(state, "web-pod", "db-pod", 5432)
        assert result["allowed"] is True
        assert "allow-web-to-db" in result["matched_policies"]

    def test_traffic_port_mismatch(self):
        """端口不匹配时拒绝"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-db
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    ports:
    - protocol: TCP
      port: 5432
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # web-pod -> db-pod:8080 端口不匹配 -> 拒绝
        result = simulate_traffic(state, "web-pod", "db-pod", 8080)
        assert result["allowed"] is False
        assert "allow-web-to-db" in result["matched_policies"]

    def test_traffic_wrong_source(self):
        """来源 Pod 不匹配 from 选择器时拒绝"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: rogue-pod
  labels:
    app: rogue
spec:
  containers:
  - name: alpine
    image: alpine
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-db
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    ports:
    - protocol: TCP
      port: 5432
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # rogue-pod 不匹配 from 的 podSelector (app: web) -> 拒绝
        result = simulate_traffic(state, "rogue-pod", "db-pod", 5432)
        assert result["allowed"] is False
        assert "allow-web-to-db" in result["matched_policies"]

    def test_traffic_policy_not_selecting_dst(self):
        """NetworkPolicy 不选择 dst_pod 时不影响该 Pod（默认允许）"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: cache-pod
  labels:
    app: cache
spec:
  containers:
  - name: redis
    image: redis
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: protect-db
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
    ports:
    - protocol: TCP
      port: 5432
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # 策略只保护 db-pod，cache-pod 不受影响 -> 默认允许
        result = simulate_traffic(state, "web-pod", "cache-pod", 6379)
        assert result["allowed"] is True
        assert result["matched_policies"] == []

    def test_traffic_allow_all_sources_no_ports(self):
        """from 缺失（允许所有来源）+ ports 缺失（允许所有端口）时允许"""
        yaml_text = """
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: api-pod
  labels:
    app: api
spec:
  containers:
  - name: httpd
    image: httpd
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-ingress
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - {}
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)

        # ingress 规则为空 {} -> 允许所有来源和端口
        result = simulate_traffic(state, "web-pod", "api-pod", 8080)
        assert result["allowed"] is True
        assert "allow-all-ingress" in result["matched_policies"]
