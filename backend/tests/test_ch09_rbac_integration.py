"""集成测试：simulate_rbac_check 与 ch09 RBAC 关卡的集成

验证 Q9.5 的 check_fn 正确调用 simulate_rbac_check，消除假阳性问题。

测试场景:
- test_q95_with_valid_rbac: SA+Role+RoleBinding -> simulate_rbac_check 返回 True -> check_fn ok=True
- test_q95_without_rolebinding: 只有 SA 没有 Binding -> check_fn ok=False
- test_q95_wrong_verb: Role 有 get 但检查 list -> simulate_rbac_check 返回 False -> check_fn ok=False
"""
import pytest
from app.simulator import ClusterState, apply_manifest, simulate_rbac_check
from app.validator import get_level


class TestQ95RbacIntegration:
    """Q9.5 与 simulate_rbac_check 的集成测试"""

    # --- 完整的合法 RBAC YAML（SA + Role + RoleBinding） ---
    VALID_YAML = """
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

    # --- 只有 SA，没有 RoleBinding ---
    NO_BINDING_YAML = """
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
  resources: ["pods"]
  verbs: ["get", "list"]
"""

    # --- Role 只有 get，没有 list ---
    WRONG_VERB_YAML = """
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
  verbs: ["get"]
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

    def test_q95_with_valid_rbac(self):
        """SA+Role+RoleBinding -> simulate_rbac_check 返回 True -> check_fn ok=True"""
        # 1. 直接验证 simulate_rbac_check
        state = ClusterState()
        state = apply_manifest(state, self.VALID_YAML)
        assert simulate_rbac_check(state, "my-sa", "list", "pods") is True
        assert simulate_rbac_check(state, "my-sa", "get", "pods") is True
        assert simulate_rbac_check(state, "my-sa", "list", "services") is True

        # 2. 通过 check_fn 验证集成
        r = get_level("Q9.5").check_fn(self.VALID_YAML)
        assert r.ok, r.error
        assert r.state is not None
        assert "my-sa" in r.state.serviceaccounts
        assert "pod-reader" in r.state.roles
        assert "pod-reader-binding" in r.state.rolebindings

    def test_q95_without_rolebinding(self):
        """只有 SA 没有 Binding -> check_fn ok=False"""
        # 1. 直接验证 simulate_rbac_check 返回 False（无绑定）
        state = ClusterState()
        state = apply_manifest(state, self.NO_BINDING_YAML)
        assert simulate_rbac_check(state, "my-sa", "list", "pods") is False

        # 2. 通过 check_fn 验证（应在结构检查阶段就失败）
        r = get_level("Q9.5").check_fn(self.NO_BINDING_YAML)
        assert not r.ok
        assert "RoleBinding" in r.error

    def test_q95_wrong_verb(self):
        """Role 有 get 但检查 list -> simulate_rbac_check 返回 False -> check_fn ok=False

        这是假阳性修复的核心测试：结构校验通过（有 Role、RoleBinding、
        roleRef 正确、subjects 含 SA），但权限实际未生效（Role 的 verbs
        不含 list），simulate_rbac_check 正确检测到并返回 False。
        """
        # 1. 直接验证 simulate_rbac_check
        state = ClusterState()
        state = apply_manifest(state, self.WRONG_VERB_YAML)
        # get 有权限，list 没有权限
        assert simulate_rbac_check(state, "my-sa", "get", "pods") is True
        assert simulate_rbac_check(state, "my-sa", "list", "pods") is False

        # 2. 通过 check_fn 验证（结构校验通过，但 simulate_rbac_check 拒绝）
        r = get_level("Q9.5").check_fn(self.WRONG_VERB_YAML)
        assert not r.ok
        assert "权限未生效" in r.error
        assert "list" in r.error or "pods" in r.error

    def test_q95_wrong_resource(self):
        """Role 不包含 pods 资源 -> simulate_rbac_check 返回 False"""
        yaml_text = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: svc-reader
rules:
- apiGroups: [""]
  resources: ["services"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: svc-reader-binding
roleRef:
  kind: Role
  name: svc-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: default
"""
        # 1. 直接验证 simulate_rbac_check
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        assert simulate_rbac_check(state, "my-sa", "list", "services") is True
        assert simulate_rbac_check(state, "my-sa", "list", "pods") is False

        # 2. 通过 check_fn 验证
        r = get_level("Q9.5").check_fn(yaml_text)
        assert not r.ok
        assert "权限未生效" in r.error

    def test_q95_wildcard_passes(self):
        """Role 使用通配符 verbs: ['*'] -> simulate_rbac_check 返回 True"""
        yaml_text = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-admin
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-admin-binding
roleRef:
  kind: Role
  name: pod-admin
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: default
"""
        # 1. 直接验证 simulate_rbac_check
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        assert simulate_rbac_check(state, "my-sa", "list", "pods") is True
        assert simulate_rbac_check(state, "my-sa", "get", "pods") is True
        assert simulate_rbac_check(state, "my-sa", "delete", "pods") is True

        # 2. 通过 check_fn 验证
        r = get_level("Q9.5").check_fn(yaml_text)
        assert r.ok, r.error

    def test_q95_clusterrole_via_rolebinding(self):
        """RoleBinding 引用 ClusterRole -> simulate_rbac_check 正确验证"""
        yaml_text = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader-cluster
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
roleRef:
  kind: ClusterRole
  name: pod-reader-cluster
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: default
"""
        # 1. 直接验证 simulate_rbac_check
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        assert simulate_rbac_check(state, "my-sa", "list", "pods") is True

        # 2. 通过 check_fn 验证
        # 注意: Q9.5 的 check_fn 要求 state.roles 非空，但这里只有 ClusterRole
        # 所以 check_fn 会在 "没有创建任何 Role" 处失败。
        # 这是预期行为 -- Q9.5 要求创建 Role（而非 ClusterRole）。
        r = get_level("Q9.5").check_fn(yaml_text)
        assert not r.ok
        assert "Role" in r.error
