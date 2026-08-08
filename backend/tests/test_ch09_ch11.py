"""Chapter 9 (RBAC), Chapter 10 (HPA), Chapter 11 (Ingress) 测试

测试覆盖:
- 每关的正确答案能通过 check_fn
- 每关的错误答案不能通过
- RBAC 资源正确存储到 state
- HPA 字段验证
- Ingress 路由规则验证
"""
import pytest
from app.simulator import ClusterState, apply_manifest, preset_state, K8sError
from app.validator import get_level, list_levels


# ===== Chapter 9: RBAC =====

class TestQ91CreateRole:
    """Q9.1 创建 Role"""

    def test_correct(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
"""
        r = get_level("Q9.1").check_fn(yaml)
        assert r.ok, r.error

    def test_role_stored_in_state(self):
        """Role 正确存储到 state.roles"""
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
"""
        r = get_level("Q9.1").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "pod-reader" in r.state.roles

    def test_empty_rules(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: empty-role
rules: []
"""
        r = get_level("Q9.1").check_fn(yaml)
        assert not r.ok

    def test_missing_pods_resource(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
"""
        r = get_level("Q9.1").check_fn(yaml)
        assert not r.ok
        assert "services" in r.error

    def test_missing_get_verb(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["list"]
"""
        r = get_level("Q9.1").check_fn(yaml)
        assert not r.ok
        assert "get" in r.error

    def test_empty_yaml(self):
        r = get_level("Q9.1").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: not-a-role
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
        r = get_level("Q9.1").check_fn(yaml)
        assert not r.ok


class TestQ92CreateRoleBinding:
    """Q9.2 创建 RoleBinding"""

    def test_correct(self):
        yaml = """
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
        r = get_level("Q9.2").check_fn(yaml)
        assert r.ok, r.error

    def test_rolebinding_stored_in_state(self):
        yaml = """
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
        r = get_level("Q9.2").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "pod-reader-binding" in r.state.rolebindings

    def test_missing_role_ref(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: no-role-ref
subjects:
- kind: ServiceAccount
  name: my-sa
"""
        r = get_level("Q9.2").check_fn(yaml)
        assert not r.ok

    def test_missing_subjects(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: no-subjects
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
"""
        r = get_level("Q9.2").check_fn(yaml)
        assert not r.ok

    def test_no_service_account(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: no-sa
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: User
  name: admin
  apiGroup: rbac.authorization.k8s.io
"""
        r = get_level("Q9.2").check_fn(yaml)
        assert not r.ok
        assert "ServiceAccount" in r.error

    def test_empty_yaml(self):
        r = get_level("Q9.2").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: not-a-rolebinding
spec:
  containers:
  - name: nginx
    image: nginx:1.25
"""
        r = get_level("Q9.2").check_fn(yaml)
        assert not r.ok


class TestQ93CreateClusterRole:
    """Q9.3 创建 ClusterRole"""

    def test_correct(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-manager
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
"""
        r = get_level("Q9.3").check_fn(yaml)
        assert r.ok, r.error

    def test_clusterrole_stored_in_state(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-manager
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
"""
        r = get_level("Q9.3").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "node-manager" in r.state.clusterroles

    def test_missing_nodes_resource(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-manager
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
"""
        r = get_level("Q9.3").check_fn(yaml)
        assert not r.ok
        assert "nodes" in r.error

    def test_empty_yaml(self):
        r = get_level("Q9.3").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: not-a-clusterrole
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list"]
"""
        r = get_level("Q9.3").check_fn(yaml)
        assert not r.ok


class TestQ94CreateClusterRoleBinding:
    """Q9.4 创建 ClusterRoleBinding"""

    def test_correct(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: node-manager-binding
roleRef:
  kind: ClusterRole
  name: node-manager
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: node-sa
  namespace: default
"""
        r = get_level("Q9.4").check_fn(yaml)
        assert r.ok, r.error

    def test_crb_stored_in_state(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: node-manager-binding
roleRef:
  kind: ClusterRole
  name: node-manager
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: node-sa
  namespace: default
"""
        r = get_level("Q9.4").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "node-manager-binding" in r.state.clusterrolebindings

    def test_wrong_roleRef_kind(self):
        """ClusterRoleBinding 只能引用 ClusterRole"""
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: wrong-kind
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
"""
        r = get_level("Q9.4").check_fn(yaml)
        assert not r.ok
        assert "ClusterRole" in r.error

    def test_missing_roleRef(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: no-role-ref
subjects:
- kind: ServiceAccount
  name: my-sa
"""
        r = get_level("Q9.4").check_fn(yaml)
        assert not r.ok

    def test_missing_subjects(self):
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: no-subjects
roleRef:
  kind: ClusterRole
  name: node-manager
  apiGroup: rbac.authorization.k8s.io
"""
        r = get_level("Q9.4").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q9.4").check_fn("")
        assert not r.ok


class TestQ95SAAuthorization:
    """Q9.5 集群实战 - 为 ServiceAccount 授权"""

    def test_correct(self):
        yaml = """
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
        r = get_level("Q9.5").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_role(self):
        yaml = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
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
"""
        r = get_level("Q9.5").check_fn(yaml)
        assert not r.ok

    def test_missing_rolebinding(self):
        yaml = """
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
  verbs: ["get"]
"""
        r = get_level("Q9.5").check_fn(yaml)
        assert not r.ok

    def test_rolebinding_ref_wrong_role(self):
        """RoleBinding 引用不存在的 Role"""
        yaml = """
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: binding
roleRef:
  kind: Role
  name: non-existent
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
"""
        r = get_level("Q9.5").check_fn(yaml)
        assert not r.ok
        assert "non-existent" in r.error

    def test_empty_yaml(self):
        r = get_level("Q9.5").check_fn("")
        assert not r.ok

    def test_permission_not_effective_wrong_verb(self):
        """Role 只有 get 没有 list -> simulate_rbac_check 返回 False -> 假阳性修复"""
        yaml = """
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
        r = get_level("Q9.5").check_fn(yaml)
        assert not r.ok
        assert "权限未生效" in r.error

    def test_permission_not_effective_wrong_resource(self):
        """Role 不包含 pods 资源 -> simulate_rbac_check 返回 False"""
        yaml = """
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
        r = get_level("Q9.5").check_fn(yaml)
        assert not r.ok
        assert "权限未生效" in r.error

    def test_wildcard_verb_passes(self):
        """Role 使用 verbs: ['*'] -> simulate_rbac_check 返回 True"""
        yaml = """
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
        r = get_level("Q9.5").check_fn(yaml)
        assert r.ok, r.error


# ===== Chapter 10: HPA =====

class TestQ101CreateHPA:
    """Q10.1 创建 HPA（CPU 阈值）"""

    def test_correct(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.1").check_fn(yaml)
        assert r.ok, r.error

    def test_hpa_stored_in_state(self):
        """HPA 正确存储到 state.horizontalpodautoscalers"""
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.1").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "web-hpa" in r.state.horizontalpodautoscalers

    def test_wrong_max_replicas(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.1").check_fn(yaml)
        assert not r.ok
        assert "10" in r.error

    def test_missing_metrics(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
"""
        r = get_level("Q10.1").check_fn(yaml)
        assert not r.ok

    def test_wrong_cpu_target(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
"""
        r = get_level("Q10.1").check_fn(yaml)
        assert not r.ok
        assert "50" in r.error

    def test_empty_yaml(self):
        r = get_level("Q10.1").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: not-hpa
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
        r = get_level("Q10.1").check_fn(yaml)
        assert not r.ok


class TestQ102ScaleConfig:
    """Q10.2 HPA 扩缩容配置"""

    def test_correct(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.2").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_min_replicas(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 1
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.2").check_fn(yaml)
        assert not r.ok
        assert "minReplicas" in r.error

    def test_wrong_max_replicas(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.2").check_fn(yaml)
        assert not r.ok
        assert "maxReplicas" in r.error

    def test_empty_yaml(self):
        r = get_level("Q10.2").check_fn("")
        assert not r.ok


class TestQ103MultiMetrics:
    """Q10.3 HPA 多指标"""

    def test_correct(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 60
"""
        r = get_level("Q10.3").check_fn(yaml)
        assert r.ok, r.error

    def test_single_metric(self):
        """只有一个指标应该失败"""
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.3").check_fn(yaml)
        assert not r.ok
        assert "2" in r.error

    def test_missing_metrics(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
"""
        r = get_level("Q10.3").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q10.3").check_fn("")
        assert not r.ok


class TestQ104Behavior:
    """Q10.4 HPA 行为配置"""

    def test_correct(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
"""
        r = get_level("Q10.4").check_fn(yaml)
        assert r.ok, r.error

    def test_only_scale_down(self):
        """只有 scaleDown 也可以"""
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
"""
        r = get_level("Q10.4").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_behavior(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.4").check_fn(yaml)
        assert not r.ok
        assert "behavior" in r.error

    def test_empty_behavior(self):
        """behavior 为空字典"""
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  behavior: {}
"""
        r = get_level("Q10.4").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q10.4").check_fn("")
        assert not r.ok


class TestQ105DeployHPA:
    """Q10.5 集群实战 - 对 Deployment 配置 HPA"""

    def test_correct(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
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
        resources:
          requests:
            cpu: 100m
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
"""
        r = get_level("Q10.5").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_hpa(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
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
        r = get_level("Q10.5").check_fn(yaml)
        assert not r.ok

    def test_hpa_missing_metrics(self):
        yaml = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  maxReplicas: 10
"""
        r = get_level("Q10.5").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q10.5").check_fn("")
        assert not r.ok


# ===== Chapter 11: Ingress =====

class TestQ111CreateIngress:
    """Q11.1 创建 Ingress（单路由）"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.1").check_fn(yaml)
        assert r.ok, r.error

    def test_ingress_stored_in_state(self):
        """Ingress 正确存储到 state.ingresses"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.1").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "web-ingress" in r.state.ingresses

    def test_wrong_service_name(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wrong-svc
            port:
              number: 80
"""
        r = get_level("Q11.1").check_fn(yaml)
        assert not r.ok
        assert "web-svc" in r.error

    def test_missing_host(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.1").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q11.1").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: not-ingress
spec:
  selector:
    app: web
  ports:
  - port: 80
"""
        r = get_level("Q11.1").check_fn(yaml)
        assert not r.ok


class TestQ112MultiHost:
    """Q11.2 Ingress 多域名"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-host-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
"""
        r = get_level("Q11.2").check_fn(yaml)
        assert r.ok, r.error

    def test_single_host(self):
        """只有一个 host 应该失败"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: single-host
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.2").check_fn(yaml)
        assert not r.ok
        assert "2" in r.error

    def test_duplicate_hosts(self):
        """重复的 host 应该失败"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dup-host
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.2").check_fn(yaml)
        assert not r.ok
        assert "重复" in r.error

    def test_empty_yaml(self):
        r = get_level("Q11.2").check_fn("")
        assert not r.ok


class TestQ113PathRouting:
    """Q11.3 Ingress 路径路由"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.3").check_fn(yaml)
        assert r.ok, r.error

    def test_single_path(self):
        """只有一个路径应该失败"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: single-path
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
"""
        r = get_level("Q11.3").check_fn(yaml)
        assert not r.ok

    def test_missing_web_path(self):
        """缺少 /web 路径"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: missing-web
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-svc
            port:
              number: 80
"""
        r = get_level("Q11.3").check_fn(yaml)
        assert not r.ok
        assert "/web" in r.error

    def test_empty_yaml(self):
        r = get_level("Q11.3").check_fn("")
        assert not r.ok


class TestQ114TLS:
    """Q11.4 Ingress TLS"""

    def test_correct(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - example.com
    secretName: tls-secret
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.4").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_tls(self):
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: no-tls
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.4").check_fn(yaml)
        assert not r.ok
        assert "tls" in r.error

    def test_tls_without_secret_name(self):
        """TLS 配置缺少 secretName"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: no-secret
spec:
  tls:
  - hosts:
    - example.com
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.4").check_fn(yaml)
        assert not r.ok
        assert "secretName" in r.error

    def test_empty_yaml(self):
        r = get_level("Q11.4").check_fn("")
        assert not r.ok


class TestQ115DeployNginxIngress:
    """Q11.5 集群实战 - 部署 Nginx Ingress"""

    def test_correct(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
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
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
"""
        r = get_level("Q11.5").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_ingress(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
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
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
"""
        r = get_level("Q11.5").check_fn(yaml)
        assert not r.ok

    def test_ingress_without_backend(self):
        """Ingress 没有 backend 配置"""
        yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: no-backend
spec:
  rules:
  - host: example.com
"""
        r = get_level("Q11.5").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q11.5").check_fn("")
        assert not r.ok


# ===== 集成测试: 章节注册验证 =====

class TestChapterRegistration:
    """验证新章节正确注册到 validator"""

    def test_list_levels_ch09(self):
        levels = list_levels("ch09")
        assert len(levels) == 5
        ids = [lv["id"] for lv in levels]
        assert ids == ["Q9.1", "Q9.2", "Q9.3", "Q9.4", "Q9.5"]

    def test_list_levels_ch10(self):
        levels = list_levels("ch10")
        assert len(levels) == 5
        ids = [lv["id"] for lv in levels]
        assert ids == ["Q10.1", "Q10.2", "Q10.3", "Q10.4", "Q10.5"]

    def test_list_levels_ch11(self):
        levels = list_levels("ch11")
        assert len(levels) == 5
        ids = [lv["id"] for lv in levels]
        assert ids == ["Q11.1", "Q11.2", "Q11.3", "Q11.4", "Q11.5"]

    def test_get_level_q91(self):
        lv = get_level("Q9.1")
        assert lv is not None
        assert lv.chapter == "ch09"
        assert lv.lesson is not None

    def test_get_level_q101(self):
        lv = get_level("Q10.1")
        assert lv is not None
        assert lv.chapter == "ch10"
        assert lv.lesson is not None

    def test_get_level_q111(self):
        lv = get_level("Q11.1")
        assert lv is not None
        assert lv.chapter == "ch11"
        assert lv.lesson is not None

    def test_all_levels_have_lessons(self):
        """所有新关卡都有 lesson 教学文档"""
        for level_id in [
            "Q9.1", "Q9.2", "Q9.3", "Q9.4", "Q9.5",
            "Q10.1", "Q10.2", "Q10.3", "Q10.4", "Q10.5",
            "Q11.1", "Q11.2", "Q11.3", "Q11.4", "Q11.5",
        ]:
            lv = get_level(level_id)
            assert lv is not None, f"Level {level_id} not found"
            assert lv.lesson is not None, f"Level {level_id} missing lesson"
            assert len(lv.lesson.concept) >= 200, f"Level {level_id} concept too short"
            assert len(lv.lesson.key_fields) >= 3, f"Level {level_id} too few key_fields"
            assert len(lv.lesson.common_errors) >= 3, f"Level {level_id} too few common_errors"
            assert len(lv.lesson.tips) >= 2, f"Level {level_id} too few tips"
