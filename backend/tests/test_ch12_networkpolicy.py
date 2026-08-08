"""Chapter 12 (NetworkPolicy) 测试

测试覆盖:
- 每关的正确答案能通过 check_fn
- 每关的错误答案不能通过
- NetworkPolicy 正确存储到 state.networkpolicies
"""
import pytest
from app.simulator import ClusterState, apply_manifest, K8sError
from app.validator import get_level, list_levels


# ===== Chapter 12: NetworkPolicy =====

class TestQ121DefaultDeny:
    """Q12.1 创建 NetworkPolicy（默认拒绝）"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Ingress
"""
        r = get_level("Q12.1").check_fn(yaml)
        assert r.ok, r.error

    def test_networkpolicy_stored_in_state(self):
        """NetworkPolicy 正确存储到 state.networkpolicies"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Ingress
"""
        r = get_level("Q12.1").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "default-deny" in r.state.networkpolicies

    def test_pod_selector_not_empty(self):
        """podSelector 不为空，不满足默认拒绝所有 Pod"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: not-default-deny
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Ingress
"""
        r = get_level("Q12.1").check_fn(yaml)
        assert not r.ok

    def test_missing_policy_types(self):
        """缺少 policyTypes"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-policy-types
spec:
  podSelector: {}
"""
        r = get_level("Q12.1").check_fn(yaml)
        assert not r.ok

    def test_policy_types_without_ingress(self):
        """policyTypes 不包含 Ingress"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: egress-only
spec:
  podSelector: {}
  policyTypes:
  - Egress
"""
        r = get_level("Q12.1").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q12.1").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: not-a-networkpolicy
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
        r = get_level("Q12.1").check_fn(yaml)
        assert not r.ok


class TestQ122AllowNamespace:
    """Q12.2 允许特定命名空间"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-frontend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
"""
        r = get_level("Q12.2").check_fn(yaml)
        assert r.ok, r.error

    def test_networkpolicy_stored_in_state(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-frontend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
"""
        r = get_level("Q12.2").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "allow-from-frontend" in r.state.networkpolicies

    def test_missing_namespace_selector(self):
        """from 中没有 namespaceSelector（只有 podSelector）"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-namespace-selector
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web
"""
        r = get_level("Q12.2").check_fn(yaml)
        assert not r.ok

    def test_missing_ingress(self):
        """缺少 ingress 规则"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
"""
        r = get_level("Q12.2").check_fn(yaml)
        assert not r.ok

    def test_missing_policy_types(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-types
spec:
  podSelector: {}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
"""
        r = get_level("Q12.2").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q12.2").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: not-a-networkpolicy
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
        r = get_level("Q12.2").check_fn(yaml)
        assert not r.ok


class TestQ123AllowPod:
    """Q12.3 允许特定 Pod"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-client
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-client
"""
        r = get_level("Q12.3").check_fn(yaml)
        assert r.ok, r.error

    def test_networkpolicy_stored_in_state(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-client
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-client
"""
        r = get_level("Q12.3").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "allow-api-client" in r.state.networkpolicies

    def test_missing_pod_selector_in_from(self):
        """from 中没有 podSelector（只有 namespaceSelector）"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-pod-selector
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
"""
        r = get_level("Q12.3").check_fn(yaml)
        assert not r.ok

    def test_missing_ingress(self):
        """缺少 ingress 规则"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
"""
        r = get_level("Q12.3").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q12.3").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: not-a-networkpolicy
spec:
  selector:
    app: web
  ports:
  - port: 80
"""
        r = get_level("Q12.3").check_fn(yaml)
        assert not r.ok


class TestQ124IngressEgress:
    """Q12.4 入站/出站规则"""

    def test_correct(self):
        yaml = """
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

    def test_networkpolicy_stored_in_state(self):
        yaml = """
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
        assert "ingress-egress-policy" in r.state.networkpolicies

    def test_missing_egress_policy_type(self):
        """policyTypes 只有 Ingress，缺少 Egress"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-only
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert not r.ok

    def test_missing_ingress_policy_type(self):
        """policyTypes 只有 Egress，缺少 Ingress"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: egress-only
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert not r.ok

    def test_missing_egress_rules(self):
        """policyTypes 有 Ingress+Egress 但缺少 egress 规则"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-egress-rules
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
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert not r.ok

    def test_missing_ingress_rules(self):
        """policyTypes 有 Ingress+Egress 但缺少 ingress 规则"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-ingress-rules
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q12.4").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: not-a-networkpolicy
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
        r = get_level("Q12.4").check_fn(yaml)
        assert not r.ok


class TestQ125DbIsolation:
    """Q12.5 集群实战 - 数据库网络隔离"""

    def test_correct(self):
        yaml = """
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

    def test_correct_without_ports(self):
        """没有 ports 限制也应该通过（但有提示）"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-isolation-no-ports
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

    def test_networkpolicy_stored_in_state(self):
        yaml = """
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
        assert "db-isolation" in r.state.networkpolicies

    def test_simulate_traffic_allows_backend(self):
        """simulate_traffic 验证: backend -> database:5432 应该被允许"""
        from app.simulator import simulate_traffic
        yaml = """
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
        # 验证 check_fn 内部预设了 Pod
        assert "backend-pod" in r.state.pods
        assert "database-pod" in r.state.pods
        assert "frontend-pod" in r.state.pods
        # 直接调用 simulate_traffic 确认行为
        result = simulate_traffic(r.state, "backend-pod", "database-pod", 5432)
        assert result["allowed"] is True

    def test_simulate_traffic_denies_frontend(self):
        """simulate_traffic 验证: frontend -> database:5432 应该被拒绝"""
        from app.simulator import simulate_traffic
        yaml = """
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
        result = simulate_traffic(r.state, "frontend-pod", "database-pod", 5432)
        assert result["allowed"] is False

    def test_false_positive_caught_wrong_from_label(self):
        """假阳性捕获: from 允许 app: frontend（而非 backend）-> 应失败"""
        yaml = """
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
        # from 允许 frontend 而非 backend -> backend 无法访问 -> simulate_traffic 检测到
        assert not r.ok
        assert "backend" in r.error or "拒绝" in r.error

    def test_false_positive_caught_allow_all(self):
        """假阳性捕获: from 为 [{}]（允许所有来源）-> frontend 也能访问 -> 应失败"""
        yaml = """
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
        # from: [{}] -> 匹配所有来源 -> frontend 也能访问 -> simulate_traffic 检测到
        assert not r.ok
        assert "frontend" in r.error or "过于宽松" in r.error

    def test_empty_pod_selector(self):
        """podSelector 为空 {}，没有选择数据库 Pod"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: empty-selector
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok

    def test_missing_ingress_from(self):
        """ingress 中缺少 from 定义"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-from
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 5432
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok

    def test_missing_ingress(self):
        """缺少 ingress 规则"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-ingress
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok

    def test_missing_policy_types(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: no-types
spec:
  podSelector:
    matchLabels:
      app: database
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q12.5").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: not-a-networkpolicy
data:
  key: value
"""
        r = get_level("Q12.5").check_fn(yaml)
        assert not r.ok


# ===== 关卡注册验证 =====

class TestChapter12Registration:
    """验证 ch12 关卡正确注册"""

    def test_all_5_levels_exist(self):
        for level_id in ["Q12.1", "Q12.2", "Q12.3", "Q12.4", "Q12.5"]:
            lv = get_level(level_id)
            assert lv is not None, f"{level_id} not found"

    def test_all_levels_have_lessons(self):
        for level_id in ["Q12.1", "Q12.2", "Q12.3", "Q12.4", "Q12.5"]:
            lv = get_level(level_id)
            assert lv.lesson is not None, f"{level_id} missing lesson"

    def test_chapter_filter(self):
        levels = list_levels("ch12")
        assert len(levels) == 5
        ids = [lv["id"] for lv in levels]
        assert ids == ["Q12.1", "Q12.2", "Q12.3", "Q12.4", "Q12.5"]

    def test_level_ids_and_titles(self):
        expected = {
            "Q12.1": "创建 NetworkPolicy（默认拒绝）",
            "Q12.2": "允许特定命名空间",
            "Q12.3": "允许特定 Pod",
            "Q12.4": "入站/出站规则",
            "Q12.5": "集群实战: 数据库网络隔离",
        }
        for level_id, title in expected.items():
            lv = get_level(level_id)
            assert lv is not None
            assert lv.title == title, f"{level_id} title mismatch: {lv.title}"
