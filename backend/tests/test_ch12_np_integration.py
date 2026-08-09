"""Chapter 12 NetworkPolicy: simulate_traffic 集成测试

专门测试 simulate_traffic 与 ch12 关卡的集成行为:
- test_q125_allow_traffic: Policy 允许 frontend->backend:80 -> allowed=True
- test_q125_deny_traffic: 默认拒绝策略 -> allowed=False
- test_q125_wrong_port: Policy 允许 80 但检查 443 -> allowed=False

同时验证 Q12.5 check_fn 与 simulate_traffic 的端到端集成。
"""
import pytest
from app.simulator import (
    ClusterState,
    apply_manifest,
    preset_state,
    simulate_traffic,
)
from app.validator import get_level


# ===== 测试用 Pod 预设 =====

PODS_FRONTEND_BACKEND = """\
apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
  labels:
    app: frontend
spec:
  containers:
  - name: web
    image: nginx:1.25
---
apiVersion: v1
kind: Pod
metadata:
  name: backend-pod
  labels:
    app: backend
spec:
  containers:
  - name: app
    image: nginx:1.25
"""

PODS_WITH_DATABASE = """\
apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
  labels:
    app: frontend
spec:
  containers:
  - name: web
    image: nginx:1.25
---
apiVersion: v1
kind: Pod
metadata:
  name: backend-pod
  labels:
    app: backend
spec:
  containers:
  - name: app
    image: nginx:1.25
---
apiVersion: v1
kind: Pod
metadata:
  name: database-pod
  labels:
    app: database
spec:
  containers:
  - name: db
    image: postgres:15
"""


# ===== simulate_traffic 直接测试 =====

class TestSimulateTrafficAllow:
    """test_q125_allow_traffic: Policy 允许 frontend->backend:80 -> allowed=True"""

    def test_allow_with_port(self):
        """NetworkPolicy 允许 frontend Pod 访问 backend Pod 端口 80"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
"""
        state = apply_manifest(state, policy_yaml)

        result = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result["allowed"] is True
        assert len(result["matched_policies"]) > 0

    def test_allow_without_port_restriction(self):
        """NetworkPolicy 无端口限制时，任意端口都允许"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-no-ports
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
"""
        state = apply_manifest(state, policy_yaml)

        result = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result["allowed"] is True

    def test_allow_with_namespace_selector(self):
        """通过 namespaceSelector + podSelector 组合放行"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        # 设置 frontend-pod 的 namespace 为 frontend
        state.pods["frontend-pod"]["metadata"]["namespace"] = "frontend"
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-frontend-ns
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
      podSelector:
        matchLabels:
          app: frontend
"""
        state = apply_manifest(state, policy_yaml)

        result = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result["allowed"] is True


class TestSimulateTrafficDeny:
    """test_q125_deny_traffic: 默认拒绝或无匹配策略 -> allowed=False"""

    def test_default_deny_policy(self):
        """默认拒绝策略: podSelector 选择 backend，无 ingress 规则 -> 全部拒绝"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
"""
        state = apply_manifest(state, policy_yaml)

        result = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result["allowed"] is False
        assert len(result["matched_policies"]) > 0

    def test_deny_wrong_source_pod(self):
        """Policy 只允许 app: frontend，但源 Pod 标签是 app: other -> 拒绝"""
        state = ClusterState()
        # 添加一个 other-pod
        pods = PODS_FRONTEND_BACKEND + """\
---
apiVersion: v1
kind: Pod
metadata:
  name: other-pod
  labels:
    app: other
spec:
  containers:
  - name: misc
    image: nginx:1.25
"""
        state = preset_state(state, pods)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-only
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
"""
        state = apply_manifest(state, policy_yaml)

        # other-pod 不在白名单中 -> 拒绝
        result = simulate_traffic(state, "other-pod", "backend-pod", 80)
        assert result["allowed"] is False

    def test_deny_pod_not_selected_by_policy(self):
        """Policy 选择 app: database，但目标 Pod 是 app: backend -> 不受策略管控 -> 默认允许"""
        state = ClusterState()
        state = preset_state(state, PODS_WITH_DATABASE)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: protect-database-only
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
          app: backend
    ports:
    - protocol: TCP
      port: 5432
"""
        state = apply_manifest(state, policy_yaml)

        # backend-pod 不被任何策略选择 -> K8s 默认允许
        result = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result["allowed"] is True
        assert len(result["matched_policies"]) == 0

    def test_deny_nonexistent_dst_pod(self):
        """目标 Pod 不存在 -> allowed=False"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        result = simulate_traffic(state, "frontend-pod", "nonexistent-pod", 80)
        assert result["allowed"] is False

    def test_deny_nonexistent_src_pod(self):
        """源 Pod 不存在 -> allowed=False"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-src
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - {}
"""
        state = apply_manifest(state, policy_yaml)
        result = simulate_traffic(state, "nonexistent-pod", "backend-pod", 80)
        assert result["allowed"] is False


class TestSimulateTrafficWrongPort:
    """test_q125_wrong_port: Policy 允许 80 但检查 443 -> allowed=False"""

    def test_wrong_port_denied(self):
        """Policy 只允许端口 80，检查端口 443 -> 拒绝"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-port-80-only
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
"""
        state = apply_manifest(state, policy_yaml)

        # 端口 80 -> 允许
        result_80 = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result_80["allowed"] is True

        # 端口 443 -> 拒绝
        result_443 = simulate_traffic(state, "frontend-pod", "backend-pod", 443)
        assert result_443["allowed"] is False

    def test_multiple_ports_one_matches(self):
        """Policy 允许 80 和 443，检查 443 -> 允许"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-80-and-443
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
    - protocol: TCP
      port: 443
"""
        state = apply_manifest(state, policy_yaml)

        result = simulate_traffic(state, "frontend-pod", "backend-pod", 443)
        assert result["allowed"] is True

    def test_no_port_restriction_allows_any_port(self):
        """Policy 无端口限制时，任意端口都允许"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-port-restriction
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
"""
        state = apply_manifest(state, policy_yaml)

        # 任意端口都应允许
        for port in [80, 443, 8080, 5432]:
            result = simulate_traffic(state, "frontend-pod", "backend-pod", port)
            assert result["allowed"] is True, f"Port {port} should be allowed"


# ===== Q12.5 check_fn 端到端集成测试 =====

class TestQ125CheckFnIntegration:
    """Q12.5 check_fn 与 simulate_traffic 端到端集成"""

    def test_correct_policy_passes_check_fn(self):
        """正确的 NetworkPolicy（允许 backend -> database:5432）通过 check_fn"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-isolation
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
          app: backend
    ports:
    - protocol: TCP
      port: 5432
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert r.ok, r.error

    def test_check_fn_presets_pods_in_state(self):
        """check_fn 返回的 state 中包含预设的 Pod"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-isolation
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
          app: backend
    ports:
    - protocol: TCP
      port: 5432
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "backend-pod" in r.state.pods
        assert "database-pod" in r.state.pods
        assert "frontend-pod" in r.state.pods

    def test_check_fn_catches_wrong_from_label(self):
        """check_fn 检测到 from 标签错误（允许 frontend 而非 backend）"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: wrong-from
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
          app: frontend
    ports:
    - protocol: TCP
      port: 5432
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok
        # 错误信息应提及 backend 被拒绝
        assert "backend" in r.error.lower() or "拒绝" in r.error

    def test_check_fn_catches_allow_all_from(self):
        """check_fn 检测到 from: [{}]（允许所有来源）"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - {}
    ports:
    - protocol: TCP
      port: 5432
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok
        assert "frontend" in r.error or "过于宽松" in r.error

    def test_check_fn_catches_wrong_port(self):
        """check_fn 检测到端口不匹配（只允许 8080 而非 5432）"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: wrong-port
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
          app: backend
    ports:
    - protocol: TCP
      port: 8080
"""
        r = get_level("Q12.5").check_fn(yaml)
        # backend -> database:5432 被拒绝（因为只允许 8080）
        assert not r.ok
        assert "5432" in r.error or "端口" in r.error or "backend" in r.error.lower()

    def test_check_fn_without_ports_still_passes(self):
        """没有端口限制的策略也能通过（所有端口都允许）"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-ports
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
          app: backend
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert r.ok, r.error


# ===== Q12.4 check_fn 集成测试（可选增强） =====

class TestQ124CheckFnIntegration:
    """Q12.4 check_fn 与 simulate_traffic 集成"""

    def test_correct_policy_passes(self):
        """正确的 ingress+egress 策略通过 check_fn"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-egress-policy
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert r.ok, r.error

    def test_check_fn_presets_pods(self):
        """check_fn 返回的 state 中包含预设的 Pod"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-egress-policy
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "frontend-pod" in r.state.pods
        assert "backend-pod" in r.state.pods

    def test_check_fn_with_ports(self):
        """带端口限制的策略也能通过"""
        yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: with-ports
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert r.ok, r.error


# ===== Namespace 感知集成测试 =====


class TestSimulateTrafficNamespaceIsolation:
    """NetworkPolicy 跨 namespace 隔离测试"""

    def test_networkpolicy_only_affects_same_namespace_pod(self):
        """NetworkPolicy 只影响同 namespace 的 Pod"""
        pods_yaml = """\
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  namespace: ns-a
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
  namespace: ns-a
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
---
apiVersion: v1
kind: Pod
metadata:
  name: db-pod-other
  namespace: ns-b
  labels:
    app: database
spec:
  containers:
  - name: postgres
    image: postgres
"""
        state = ClusterState()
        state = preset_state(state, pods_yaml)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ns-a
  namespace: ns-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
"""
        state = apply_manifest(state, policy_yaml)

        # ns-a 中的 db-pod 被 NetworkPolicy 管控 -> 拒绝
        result_a = simulate_traffic(state, "web-pod", "db-pod", 5432)
        assert result_a["allowed"] is False
        assert "default-deny-ns-a" in result_a["matched_policies"]

        # ns-b 中的 db-pod-other 不被 ns-a 的 NetworkPolicy 管控 -> 默认允许
        result_b = simulate_traffic(state, "web-pod", "db-pod-other", 5432)
        assert result_b["allowed"] is True
        assert result_b["matched_policies"] == []

    def test_default_namespace_backward_compatible(self):
        """Pod 和 NetworkPolicy 都在 default namespace（不指定）时正常工作"""
        state = ClusterState()
        state = preset_state(state, PODS_FRONTEND_BACKEND)
        policy_yaml = """\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
"""
        state = apply_manifest(state, policy_yaml)

        # 默认 namespace 下策略正常生效
        result = simulate_traffic(state, "frontend-pod", "backend-pod", 80)
        assert result["allowed"] is True
        assert "allow-frontend-to-backend" in result["matched_policies"]
