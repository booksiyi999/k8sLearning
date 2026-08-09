"""Chapter 9: RBAC（权限管理）（5 关）

Q9.1 创建 Role
Q9.2 创建 RoleBinding
Q9.3 创建 ClusterRole
Q9.4 创建 ClusterRoleBinding
Q9.5 集群实战 - 为 ServiceAccount 授权
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError, simulate_rbac_check


# ==================== Q9.1 创建 Role ====================

def _check_91_create_role(user_yaml: str) -> CheckResult:
    """Q9.1 创建 Role，允许读取 Pod 和 Service"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.roles:
        return CheckResult(
            ok=False,
            error="没有创建任何 Role",
            hints=["你需要 apply 一个 kind: Role 的 YAML"],
        )

    role_name = next(iter(state.roles))
    role = state.roles[role_name]

    # 验证 rules 非空
    rules = role.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Role 的 rules 为空或格式错误",
            hints=["在 rules 下定义权限规则，包含 apiGroups、resources、verbs"],
        )

    # 检查是否包含 pods 和 services 资源
    rule = rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    resources = rule.get("resources", [])
    if not isinstance(resources, list):
        return CheckResult(ok=False, error="rules[0].resources 必须是列表", hints=[])

    if "pods" not in resources or "services" not in resources:
        return CheckResult(
            ok=False,
            error=f"rules[0].resources 应包含 pods 和 services，实际为 {resources}",
            hints=["resources 应包含: pods, services"],
        )

    # 检查 verbs 包含 get 和 list
    verbs = rule.get("verbs", [])
    if not isinstance(verbs, list):
        return CheckResult(ok=False, error="rules[0].verbs 必须是列表", hints=[])

    if "get" not in verbs or "list" not in verbs:
        return CheckResult(
            ok=False,
            error=f"rules[0].verbs 应包含 get 和 list，实际为 {verbs}",
            hints=["verbs 应包含: get, list"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Role 创建成功！它定义了命名空间级别的权限规则 🔐"],
    )


LEVEL_Q9_1 = Level(
    id="Q9.1",
    chapter="ch09",
    title="创建 Role",
    description="""
# 创建 Role 🔐

**Role** 是 Kubernetes RBAC 中的命名空间级权限对象，定义了在某个命名空间内允许执行的操作。

## 任务

创建一个 Role，允许读取（get、list）Pod 和 Service：
- `kind: Role`
- `apiVersion: rbac.authorization.k8s.io/v1`
- `rules` 中包含对 `pods` 和 `services` 的 `get`、`list` 权限

## 提示

Role 的 rules 结构：
```yaml
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
```

- `apiGroups: [""]` 表示核心 API 组（Pod、Service 属于核心组）
- `verbs` 常用值：get、list、watch、create、update、delete
""",
    starter_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
# rules: 定义权限规则
""",
    check_fn=_check_91_create_role,
    lesson=Lesson(
        concept="""\
## 什么是 Role？

**Role** 是 Kubernetes RBAC（Role-Based Access Control，基于角色的访问控制）中的核心对象。它定义了一组权限规则，指定在某个**命名空间**内允许对哪些资源执行哪些操作。

### RBAC 四大对象

| 对象 | 作用域 | 说明 |
|------|--------|------|
| Role | 命名空间 | 定义命名空间内权限 |
| RoleBinding | 命名空间 | 将 Role 绑定到用户/组/SA |
| ClusterRole | 集群 | 定义集群范围权限 |
| ClusterRoleBinding | 集群 | 将 ClusterRole 绑定到用户/组/SA |

### rules 规则结构

每条规则由三部分组成：

1. **apiGroups** - API 组列表，核心组用空字符串 `""` 表示
2. **resources** - 资源类型列表，如 `pods`、`services`、`deployments`
3. **verbs** - 允许的操作列表，如 `get`、`list`、`create`、`delete`

### 常用 verbs

- `get` - 获取单个资源
- `list` - 列出资源列表
- `watch` - 监听资源变化
- `create` - 创建资源
- `update` / `patch` - 修改资源
- `delete` - 删除资源
- `*` - 所有操作（慎用）

### apiGroups 示例

- `""` - 核心组（Pod、Service、ConfigMap 等）
- `apps` - Deployment、StatefulSet 等
- `batch` - Job、CronJob
- `rbac.authorization.k8s.io` - RBAC 资源本身
""",
        key_fields=[
            {"name": "apiVersion", "description": "RBAC API 版本", "required": True, "example": "rbac.authorization.k8s.io/v1"},
            {"name": "rules", "description": "权限规则列表", "required": True, "example": "[{apiGroups: [\"\"], resources: [pods], verbs: [get, list]}]"},
            {"name": "rules[].apiGroups", "description": "API 组列表，核心组为空字符串", "required": True, "example": "[\"\"]"},
            {"name": "rules[].resources", "description": "资源类型列表", "required": True, "example": "[pods, services]"},
            {"name": "rules[].verbs", "description": "允许的操作列表", "required": True, "example": "[get, list]"},
        ],
        diagram="""\
  RBAC: Role 权限模型

  ┌─────────────────────────────────┐
  │  Role (pod-reader)              │
  │  namespace: default             │
  │  rules:                         │
  │  - apiGroups: [""]              │
  │    resources: ["pods","services"]│
  │    verbs: ["get","list"]        │
  └───────────────┬─────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
  ┌──────┐   ┌──────────┐  ┌──────────┐
  │ get  │   │   list   │  │ (watch)  │
  │ pod  │   │   pods   │  │  未授权  │
  └──────┘   └──────────┘  └──────────┘

  作用域: 仅限当前命名空间 (default)
  Role 不能控制集群级资源 (如 Node、PV)
""",
        example_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: Role                                 # 资源类型: Role
metadata:                                  # 元数据
  name: pod-reader                         # Role 名称
  namespace: default                       # 命名空间（可选，默认 default）
rules:                                     # 权限规则
- apiGroups: [""]                          # 核心 API 组
  resources: ["pods", "services"]          # 允许操作 Pod 和 Service
  verbs: ["get", "list"]                   # 允许 get 和 list 操作
""",
        common_errors=[
            "apiVersion 写成 v1 而非 rbac.authorization.k8s.io/v1",
            "rules 写成了单数 rule",
            "apiGroups 忘记写空字符串（核心组）",
            "verbs 写成了 read 而非 get/list",
        ],
        tips=[
            "用 kubectl get roles 查看已创建的 Role",
            "用 kubectl describe role <name> 查看权限详情",
            "Role 只控制命名空间级权限，集群级权限用 ClusterRole",
        ],
    ),
)


# ==================== Q9.2 创建 RoleBinding ====================

def _check_92_create_rolebinding(user_yaml: str) -> CheckResult:
    """Q9.2 创建 RoleBinding 绑定 Role 到 ServiceAccount"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.rolebindings:
        return CheckResult(
            ok=False,
            error="没有创建任何 RoleBinding",
            hints=["你需要 apply 一个 kind: RoleBinding 的 YAML"],
        )

    rb_name = next(iter(state.rolebindings))
    rb = state.rolebindings[rb_name]

    # 验证 roleRef 存在
    role_ref = rb.get("roleRef")
    if not isinstance(role_ref, dict):
        return CheckResult(
            ok=False,
            error="RoleBinding 缺少 roleRef（必须是映射）",
            hints=["roleRef 指定要绑定的 Role，包含 kind 和 name"],
        )

    # 验证 roleRef 有 kind 和 name
    if "kind" not in role_ref or "name" not in role_ref:
        return CheckResult(
            ok=False,
            error="roleRef 缺少 kind 或 name 字段",
            hints=["roleRef.kind 应为 Role，roleRef.name 为 Role 名称"],
        )

    # 验证 subjects 存在
    subjects = rb.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        return CheckResult(
            ok=False,
            error="RoleBinding 缺少 subjects（必须是非空列表）",
            hints=["subjects 指定绑定的用户/组/ServiceAccount"],
        )

    # 检查 subjects 包含 ServiceAccount
    has_sa = any(
        isinstance(s, dict) and s.get("kind") == "ServiceAccount"
        for s in subjects
    )
    if not has_sa:
        return CheckResult(
            ok=False,
            error="subjects 中应包含 ServiceAccount 类型的主体",
            hints=["添加 subjects，kind 为 ServiceAccount"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["RoleBinding 将 Role 的权限授予了 ServiceAccount 🔗"],
    )


LEVEL_Q9_2 = Level(
    id="Q9.2",
    chapter="ch09",
    title="创建 RoleBinding",
    description="""
# 创建 RoleBinding 🔗

**RoleBinding** 将 Role 中定义的权限绑定到具体的用户、组或 ServiceAccount。

## 任务

创建一个 RoleBinding，将 pod-reader Role 绑定到一个 ServiceAccount：
- `kind: RoleBinding`
- `roleRef` 指向上一步创建的 Role（如 `pod-reader`）
- `subjects` 包含一个 ServiceAccount（如 `my-sa`）

## 提示

RoleBinding 的结构：
```yaml
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: default
```
""",
    starter_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
# roleRef: 指定要绑定的 Role
# subjects: 指定绑定的主体
""",
    check_fn=_check_92_create_rolebinding,
    lesson=Lesson(
        concept="""\
## 什么是 RoleBinding？

**RoleBinding** 是 RBAC 中的"绑定"对象，它将一个 Role 的权限授予指定的主体（Subject）。主体可以是用户、组或 ServiceAccount。

### RoleBinding 的作用

Role 定义了"有什么权限"，RoleBinding 回答了"谁拥有这些权限"。没有 RoleBinding，Role 就只是一个权限定义，不会被任何主体使用。

### 三个核心字段

1. **roleRef** - 引用要绑定的 Role
   - `kind`: Role（命名空间级）或 ClusterRole（集群级，但作用范围限制在 RoleBinding 所在命名空间）
   - `name`: Role 的名称
   - `apiGroup`: rbac.authorization.k8s.io

2. **subjects** - 被授权的主体列表
   - `kind`: User / Group / ServiceAccount
   - `name`: 主体名称
   - `apiGroup`: User/Group 用 rbac.authorization.k8s.io，ServiceAccount 用空字符串

3. **metadata.namespace** - RoleBinding 的命名空间决定权限的作用域

### ServiceAccount

ServiceAccount（SA）是 K8s 中 Pod 使用的身份标识。每个命名空间自动有一个 `default` ServiceAccount。Pod 通过挂载 SA 的 token 来访问 API Server，RoleBinding 决定了该 SA 拥有哪些权限。

### RoleBinding 引用 ClusterRole

RoleBinding 可以引用 ClusterRole（而非 Role），这样可以在多个命名空间中复用同一个 ClusterRole 定义，但权限限制在 RoleBinding 所在的命名空间。
""",
        key_fields=[
            {"name": "roleRef", "description": "引用的 Role/ClusterRole", "required": True, "example": "{kind: Role, name: pod-reader, apiGroup: rbac.authorization.k8s.io}"},
            {"name": "roleRef.kind", "description": "Role 或 ClusterRole", "required": True, "example": "Role"},
            {"name": "roleRef.name", "description": "Role 名称", "required": True, "example": "pod-reader"},
            {"name": "subjects", "description": "被授权的主体列表", "required": True, "example": "[{kind: ServiceAccount, name: my-sa}]"},
            {"name": "subjects[].kind", "description": "主体类型: User/Group/ServiceAccount", "required": True, "example": "ServiceAccount"},
        ],
        diagram="""\
  RBAC: RoleBinding 绑定模型

  ┌──────────────┐      ┌──────────────────┐      ┌───────────────┐
  │   Role       │      │  RoleBinding     │      │  Subject      │
  │ (pod-reader) │◄─────┤  roleRef:        │─────►│  ServiceAcct  │
  │              │      │    kind: Role    │      │  (my-sa)      │
  │ rules:       │      │    name:         │      │               │
  │  pods: get   │      │      pod-reader  │      │  Pod 使用此   │
  │  pods: list  │      │  subjects:       │      │  SA 访问 API  │
  └──────────────┘      │  - kind: SA      │      └───────────────┘
                        │    name: my-sa   │
                        └──────────────────┘

  权限流向: Role ──> RoleBinding ──> ServiceAccount ──> Pod
""",
        example_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: RoleBinding                          # 资源类型: RoleBinding
metadata:                                  # 元数据
  name: pod-reader-binding                 # RoleBinding 名称
  namespace: default                       # 命名空间
roleRef:                                   # 引用的 Role
  kind: Role                               # 角色类型: Role
  name: pod-reader                         # Role 名称
  apiGroup: rbac.authorization.k8s.io      # API 组
subjects:                                  # 被授权的主体
- kind: ServiceAccount                     # 主体类型: ServiceAccount
  name: my-sa                              # SA 名称
  namespace: default                       # SA 所在命名空间
""",
        common_errors=[
            "roleRef 中忘记写 apiGroup 字段",
            "subjects 的 apiGroup 写错（ServiceAccount 应为空字符串或不写）",
            "roleRef.name 与实际 Role 名称不匹配",
            "把 roleRef 写在 spec 下（应在顶层）",
        ],
        tips=[
            "RoleBinding 的命名空间决定了权限生效的命名空间",
            "一个 Role 可以被多个 RoleBinding 引用",
            "用 kubectl get rolebindings 查看绑定关系",
        ],
    ),
)


# ==================== Q9.3 创建 ClusterRole ====================

def _check_93_create_clusterrole(user_yaml: str) -> CheckResult:
    """Q9.3 创建 ClusterRole 管理节点"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.clusterroles:
        return CheckResult(
            ok=False,
            error="没有创建任何 ClusterRole",
            hints=["你需要 apply 一个 kind: ClusterRole 的 YAML"],
        )

    cr_name = next(iter(state.clusterroles))
    cr = state.clusterroles[cr_name]

    # 验证 rules 非空
    rules = cr.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="ClusterRole 的 rules 为空或格式错误",
            hints=["在 rules 下定义集群级权限规则"],
        )

    # 检查是否包含 nodes 资源
    rule = rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    resources = rule.get("resources", [])
    if not isinstance(resources, list):
        return CheckResult(ok=False, error="rules[0].resources 必须是列表", hints=[])

    if "nodes" not in resources:
        return CheckResult(
            ok=False,
            error=f"rules[0].resources 应包含 nodes，实际为 {resources}",
            hints=["ClusterRole 应管理 nodes 资源"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["ClusterRole 创建成功！它定义了集群范围的权限规则 🌐"],
    )


LEVEL_Q9_3 = Level(
    id="Q9.3",
    chapter="ch09",
    title="创建 ClusterRole",
    description="""
# 创建 ClusterRole 🌐

**ClusterRole** 与 Role 类似，但作用域是**整个集群**而非单个命名空间。它用于管理集群级资源（如 Node、PV、Namespace）或跨命名空间的权限。

## 任务

创建一个 ClusterRole，允许管理节点（nodes）：
- `kind: ClusterRole`
- `rules` 中包含对 `nodes` 资源的权限

## 提示

ClusterRole 与 Role 的区别：
- 作用域：集群级 vs 命名空间级
- 可管理资源：Node、PV、Namespace 等集群级资源
- 可被 ClusterRoleBinding（集群级绑定）或 RoleBinding（命名空间级绑定）引用
""",
    starter_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-manager
# rules: 定义集群级权限规则
""",
    check_fn=_check_93_create_clusterrole,
    lesson=Lesson(
        concept="""\
## 什么是 ClusterRole？

**ClusterRole** 是集群范围的权限定义。与 Role 的命名空间级权限不同，ClusterRole 可以管理：

1. **集群级资源** - Node、PersistentVolume、Namespace、ClusterRole 等
2. **跨命名空间的资源** - 可授权访问所有命名空间的 Pod、Service 等
3. **非资源型 URL** - 如 `/healthz`、`/metrics` 等健康检查端点

### Role vs ClusterRole

| 特性 | Role | ClusterRole |
|------|------|-------------|
| 作用域 | 单个命名空间 | 整个集群 |
| 可管理集群级资源 | 否 | 是 |
| 可被 RoleBinding 引用 | 是 | 是（权限限制在该命名空间） |
| 可被 ClusterRoleBinding 引用 | 否 | 是 |
| 典型用途 | 命名空间内细粒度权限 | 节点管理、全局查看权限 |

### ClusterRole 的复用性

ClusterRole 的一个重要优势是**可复用**。你可以定义一个 ClusterRole（如 `pod-reader`），然后在多个命名空间中通过 RoleBinding 引用它，实现跨命名空间的统一权限定义，但各自独立授权。

### 聚合 ClusterRole

K8s 支持 ClusterRole 聚合（aggregation），通过 `aggregationRule` 将多个 ClusterRole 的权限合并：
```yaml
aggregationRule:
  clusterRoleSelectors:
  - matchLabels:
      rbac.example.com/aggregate-to-monitoring: "true"
```

这让监控、管理面板等工具可以动态收集权限。
""",
        key_fields=[
            {"name": "rules", "description": "集群级权限规则列表", "required": True, "example": "[{apiGroups: [\"\"], resources: [nodes], verbs: [get, list]}]"},
            {"name": "rules[].resources", "description": "集群级资源，如 nodes、persistentvolumes", "required": True, "example": "[nodes]"},
            {"name": "rules[].verbs", "description": "允许的操作", "required": True, "example": "[get, list, watch]"},
            {"name": "aggregationRule", "description": "聚合规则（高级用法）", "required": False, "example": "{clusterRoleSelectors: [...]}"},
        ],
        diagram="""\
  RBAC: ClusterRole 集群级权限

  ┌──────────────────────────────────┐
  │  ClusterRole (node-manager)       │
  │  作用域: 整个集群                  │
  │  rules:                           │
  │  - apiGroups: [""]                │
  │    resources: ["nodes"]           │
  │    verbs: ["get","list","watch"]  │
  └────────────────┬─────────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
  ┌──────┐    ┌──────────┐  ┌──────────┐
  │ Node │    │   Node   │  │   Node   │
  │  1   │    │    2     │  │    3     │
  └──────┘    └──────────┘  └──────────┘

  ClusterRole 可被:
  ├── ClusterRoleBinding -> 全集群生效
  └── RoleBinding -> 仅限该命名空间生效
""",
        example_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: ClusterRole                          # 资源类型: ClusterRole
metadata:                                  # 元数据
  name: node-manager                       # ClusterRole 名称
rules:                                     # 权限规则
- apiGroups: [""]                          # 核心 API 组
  resources: ["nodes"]                     # 管理节点资源
  verbs: ["get", "list", "watch"]          # 允许查看节点
""",
        common_errors=[
            "apiVersion 写成 v1 而非 rbac.authorization.k8s.io/v1",
            "把 ClusterRole 用于命名空间级权限（应该用 Role）",
            "rules 中 resources 写成了 node（单数），应为 nodes（复数）",
            "忘记 rules 是列表，写成了单个字典",
        ],
        tips=[
            "ClusterRole 可被 RoleBinding 引用，实现跨命名空间权限复用",
            "用 kubectl get clusterroles 查看所有 ClusterRole",
            "系统内置的 ClusterRole（如 cluster-admin）可直接引用",
        ],
    ),
)


# ==================== Q9.4 创建 ClusterRoleBinding ====================

def _check_94_create_clusterrolebinding(user_yaml: str) -> CheckResult:
    """Q9.4 创建 ClusterRoleBinding 绑定 ClusterRole"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.clusterrolebindings:
        return CheckResult(
            ok=False,
            error="没有创建任何 ClusterRoleBinding",
            hints=["你需要 apply 一个 kind: ClusterRoleBinding 的 YAML"],
        )

    crb_name = next(iter(state.clusterrolebindings))
    crb = state.clusterrolebindings[crb_name]

    # 验证 roleRef 存在
    role_ref = crb.get("roleRef")
    if not isinstance(role_ref, dict):
        return CheckResult(
            ok=False,
            error="ClusterRoleBinding 缺少 roleRef（必须是映射）",
            hints=["roleRef 指定要绑定的 ClusterRole"],
        )

    # 验证 roleRef 有 kind 和 name
    if "kind" not in role_ref or "name" not in role_ref:
        return CheckResult(
            ok=False,
            error="roleRef 缺少 kind 或 name 字段",
            hints=["roleRef.kind 应为 ClusterRole，roleRef.name 为 ClusterRole 名称"],
        )

    # 验证 roleRef.kind 为 ClusterRole
    if role_ref.get("kind") != "ClusterRole":
        return CheckResult(
            ok=False,
            error=f"roleRef.kind 应为 ClusterRole，实际为 {role_ref.get('kind')}",
            hints=["ClusterRoleBinding 只能引用 ClusterRole"],
        )

    # 验证 subjects 存在
    subjects = crb.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        return CheckResult(
            ok=False,
            error="ClusterRoleBinding 缺少 subjects（必须是非空列表）",
            hints=["subjects 指定绑定的用户/组/ServiceAccount"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["ClusterRoleBinding 将 ClusterRole 的权限全集群生效 🌐🔗"],
    )


LEVEL_Q9_4 = Level(
    id="Q9.4",
    chapter="ch09",
    title="创建 ClusterRoleBinding",
    description="""
# 创建 ClusterRoleBinding 🌐🔗

**ClusterRoleBinding** 将 ClusterRole 的权限在全集群范围内绑定到主体。与 RoleBinding 不同，它的权限在所有命名空间中生效。

## 任务

创建一个 ClusterRoleBinding，将 node-manager ClusterRole 绑定到一个 ServiceAccount：
- `kind: ClusterRoleBinding`
- `roleRef.kind` 为 `ClusterRole`
- `roleRef.name` 为 ClusterRole 名称（如 `node-manager`）
- `subjects` 包含一个 ServiceAccount

## 提示

```yaml
roleRef:
  kind: ClusterRole
  name: node-manager
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: node-sa
  namespace: default
```
""",
    starter_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: node-manager-binding
# roleRef: 指定要绑定的 ClusterRole
# subjects: 指定绑定的主体
""",
    check_fn=_check_94_create_clusterrolebinding,
    lesson=Lesson(
        concept="""\
## 什么是 ClusterRoleBinding？

**ClusterRoleBinding** 将 ClusterRole 的权限在全集群范围内授予指定的主体。与 RoleBinding 的关键区别是：ClusterRoleBinding 的权限在**所有命名空间**中生效。

### RoleBinding vs ClusterRoleBinding

| 特性 | RoleBinding | ClusterRoleBinding |
|------|------------|-------------------|
| 作用域 | 单个命名空间 | 全集群（所有命名空间） |
| 可引用 Role | 是 | 否 |
| 可引用 ClusterRole | 是（限该命名空间） | 是（全集群生效） |
| 典型用途 | 命名空间内授权 | 全局管理员、监控代理 |

### 常见使用场景

1. **全局监控代理** - Prometheus 需要跨所有命名空间查看 Pod/Service 指标
2. **集群管理员** - 授予用户 cluster-admin 权限
3. **自动伸缩器** - Cluster Autoscaler 需要管理 Node 资源
4. **存储控制器** - 需要管理 PV/PVC 跨命名空间操作

### roleRef 的不可变性

K8s 中 roleRef 是**不可变**的。如果要修改 RoleBinding/ClusterRoleBinding 引用的 Role，必须删除重建整个 Binding 对象。这是 K8s 的设计约束，防止权限意外变更。

### 安全最佳实践

- 避免使用 `cluster-admin` 等超级权限，遵循最小权限原则
- 优先使用 RoleBinding（命名空间级）而非 ClusterRoleBinding
- 定期审计 ClusterRoleBinding，移除不必要的全局授权
""",
        key_fields=[
            {"name": "roleRef", "description": "引用的 ClusterRole", "required": True, "example": "{kind: ClusterRole, name: node-manager, apiGroup: rbac.authorization.k8s.io}"},
            {"name": "roleRef.kind", "description": "必须为 ClusterRole", "required": True, "example": "ClusterRole"},
            {"name": "roleRef.name", "description": "ClusterRole 名称", "required": True, "example": "node-manager"},
            {"name": "subjects", "description": "被授权的主体列表", "required": True, "example": "[{kind: ServiceAccount, name: node-sa}]"},
        ],
        diagram="""\
  RBAC: ClusterRoleBinding 集群级绑定

  ┌──────────────────┐    ┌─────────────────────┐    ┌───────────────┐
  │  ClusterRole     │    │  ClusterRoleBinding  │    │   Subject     │
  │ (node-manager)   │◄───┤  roleRef:            │───►│ ServiceAccount│
  │                  │    │    kind: ClusterRole │    │  (node-sa)    │
  │ rules:           │    │    name: node-manager│    │               │
  │  nodes: get,list │    │  subjects:           │    │ 权限在所有    │
  │  nodes: watch    │    │  - kind: SA          │    │ 命名空间生效  │
  └──────────────────┘    │    name: node-sa     │    └───────────────┘
                          └─────────────────────┘

  权限范围: 全集群所有命名空间
  ns-1 ✅ ns-2 ✅ ns-3 ✅ ...
""",
        example_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: ClusterRoleBinding                   # 资源类型: ClusterRoleBinding
metadata:                                  # 元数据
  name: node-manager-binding               # 名称
roleRef:                                   # 引用的 ClusterRole
  kind: ClusterRole                        # 必须为 ClusterRole
  name: node-manager                       # ClusterRole 名称
  apiGroup: rbac.authorization.k8s.io      # API 组
subjects:                                  # 被授权的主体
- kind: ServiceAccount                     # 主体类型
  name: node-sa                            # SA 名称
  namespace: default                       # SA 所在命名空间
""",
        common_errors=[
            "roleRef.kind 写成了 Role（ClusterRoleBinding 只能引用 ClusterRole）",
            "忘记写 subjects 字段",
            "误以为 ClusterRoleBinding 可以引用 Role（不行，只能引用 ClusterRole）",
            "roleRef 不可变，修改时需要删除重建",
        ],
        tips=[
            "ClusterRoleBinding 的权限在所有命名空间生效，务必谨慎使用",
            "用 kubectl get clusterrolebindings 查看集群级绑定",
            "遵循最小权限原则，能用 RoleBinding 就不用 ClusterRoleBinding",
        ],
    ),
)


# ==================== Q9.5 集群实战 - 为 ServiceAccount 授权 ====================

def _check_95_sa_authorization(user_yaml: str) -> CheckResult:
    """Q9.5 集群实战 - 为 ServiceAccount 授权"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查有 Role
    if not state.roles:
        return CheckResult(
            ok=False,
            error="没有创建任何 Role",
            hints=["创建一个 Role 定义权限"],
        )

    # 检查有 RoleBinding
    if not state.rolebindings:
        return CheckResult(
            ok=False,
            error="没有创建任何 RoleBinding",
            hints=["创建一个 RoleBinding 将 Role 绑定到 ServiceAccount"],
        )

    # 验证 RoleBinding 的 roleRef 指向已存在的 Role
    rb = next(iter(state.rolebindings.values()))
    role_ref = rb.get("roleRef", {})
    if not isinstance(role_ref, dict):
        return CheckResult(ok=False, error="RoleBinding 缺少 roleRef", hints=[])

    ref_name = role_ref.get("name", "")
    if ref_name not in state.roles:
        return CheckResult(
            ok=False,
            error=f"RoleBinding 引用的 Role '{ref_name}' 不存在",
            hints=["roleRef.name 应指向已创建的 Role 名称"],
        )

    # 验证 subjects 存在且包含 ServiceAccount
    subjects = rb.get("subjects", [])
    if not isinstance(subjects, list) or not subjects:
        return CheckResult(
            ok=False,
            error="RoleBinding 缺少 subjects",
            hints=["添加 subjects 指定 ServiceAccount"],
        )

    has_sa = any(
        isinstance(s, dict) and s.get("kind") == "ServiceAccount"
        for s in subjects
    )
    if not has_sa:
        return CheckResult(
            ok=False,
            error="subjects 中应包含 ServiceAccount",
            hints=["subjects 的 kind 设为 ServiceAccount"],
        )

    # 提取 SA 名称用于权限验证
    sa_name = None
    for s in subjects:
        if isinstance(s, dict) and s.get("kind") == "ServiceAccount":
            sa_name = s.get("name")
            break
    if not sa_name:
        return CheckResult(
            ok=False,
            error="无法提取 ServiceAccount 名称",
            hints=["subjects 中的 ServiceAccount 需要有 name 字段"],
        )

    # P1 修复：调用 simulate_rbac_check 验证权限是否真正生效
    # 模拟 kubectl auth can-i list pods --as=system:serviceaccount:default:<sa_name>
    # 此前 check_fn 只做结构校验（Role/RoleBinding 存在即通过），
    # 但不验证 SA 是否真正获得了对应权限，导致假阳性。
    # Namespace 感知: 从 RoleBinding 的 metadata.namespace 获取 namespace（默认 default）
    rb_meta = rb.get("metadata", {})
    if isinstance(rb_meta, dict):
        rb_namespace = rb_meta.get("namespace", "default")
    else:
        rb_namespace = "default"
    if not simulate_rbac_check(state, sa_name, "list", "pods", namespace=rb_namespace):
        return CheckResult(
            ok=False,
            error=(
                f"权限未生效：ServiceAccount '{sa_name}' 没有 list pods 权限。"
                f"请检查 Role 的 rules 是否包含 pods 资源和 list 操作。"
            ),
            hints=[
                "确保 Role 的 rules 中 resources 包含 'pods'",
                "确保 Role 的 rules 中 verbs 包含 'list'",
                f"模拟命令: kubectl auth can-i list pods "
                f"--as=system:serviceaccount:default:{sa_name}",
            ],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            f"✅ 权限验证通过！ServiceAccount '{sa_name}' 已获得 list pods 权限",
            "在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get role,rolebinding,serviceaccount",
            f"  kubectl auth can-i list pods "
            f"--as=system:serviceaccount:default:{sa_name}",
        ],
    )


LEVEL_Q9_5 = Level(
    id="Q9.5",
    chapter="ch09",
    title="集群实战: 为 ServiceAccount 授权",
    description="""
# 集群实战: 为 ServiceAccount 授权 🏗️

来真实集群上完成完整的 RBAC 授权流程！

## 任务

1. 创建一个 ServiceAccount
2. 创建一个 Role，允许读取 Pod 和 Service
3. 创建一个 RoleBinding，将 Role 绑定到 ServiceAccount
4. 验证 ServiceAccount 的权限

## 要求

用多文档 YAML 创建完整的 RBAC 配置：
- `kind: ServiceAccount`（名为 `my-sa`）
- `kind: Role`（如 `pod-reader`，允许 get/list pods 和 services）
- `kind: RoleBinding`（绑定 Role 到 ServiceAccount）

## 验证步骤

```bash
# 1. 部署
kubectl apply -f rbac.yaml

# 2. 查看 RBAC 资源
kubectl get role,rolebinding,serviceaccount

# 3. 验证权限
kubectl auth can-i get pods --as=system:serviceaccount:default:my-sa
# 应返回 yes

# 4. 验证无权限的操作
kubectl auth can-i delete pods --as=system:serviceaccount:default:my-sa
# 应返回 no
```
""",
    starter_yaml="""\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
# rules: 定义权限
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
# roleRef: 引用 Role
# subjects: 绑定到 ServiceAccount (在真实集群中还需创建 SA)
""",
    check_fn=_check_95_sa_authorization,
    lesson=Lesson(
        concept="""\
## RBAC 完整授权流程

在真实集群中为 ServiceAccount 授权是一个完整的流程，涉及创建 SA、定义 Role 和建立绑定关系。

### 授权流程

```
1. 创建 ServiceAccount (my-sa)
   └── Pod 通过挂载 SA token 访问 API Server

2. 创建 Role (pod-reader)
   └── 定义权限: pods/services 的 get/list

3. 创建 RoleBinding (pod-reader-binding)
   └── 将 Role 绑定到 ServiceAccount
   └── Pod 获得 Role 定义的权限
```

### ServiceAccount 与 Pod 的关系

每个 Pod 默认挂载所在命名空间的 `default` ServiceAccount。你可以指定自定义 SA：

```yaml
spec:
  serviceAccountName: my-sa
```

Pod 内的 token 会自动轮换，应用通过该 token 与 API Server 通信。

### kubectl auth can-i 命令

`kubectl auth can-i` 是验证 RBAC 权限的利器：

```bash
# 检查当前用户能否执行操作
kubectl auth can-i create pods

# 模拟其他用户检查权限
kubectl auth can-i get pods --as=system:serviceaccount:default:my-sa

# 检查命名空间权限
kubectl auth can-i get pods -n kube-system --as=system:serviceaccount:default:my-sa
```

### 生产环境安全建议

1. **最小权限原则** - 只授予必要的权限
2. **使用自定义 SA** - 不要用 default SA
3. **定期审计** - 用 `kubectl auth can-i --list` 检查权限
4. **避免 cluster-admin** - 除非确实需要全集群管理权限
5. **Token 轮换** - K8s 1.24+ 使用投影卷 token，自动轮换
""",
        key_fields=[
            {"name": "ServiceAccount", "description": "Pod 使用的身份标识", "required": True, "example": "name: my-sa"},
            {"name": "Role.rules", "description": "权限规则定义", "required": True, "example": "[{apiGroups: [\"\"], resources: [pods, services], verbs: [get, list]}]"},
            {"name": "RoleBinding.roleRef", "description": "引用的 Role", "required": True, "example": "{kind: Role, name: pod-reader}"},
            {"name": "RoleBinding.subjects", "description": "绑定的 ServiceAccount", "required": True, "example": "[{kind: ServiceAccount, name: my-sa}]"},
        ],
        diagram="""\
  RBAC 完整授权流程

  ┌─────────────────┐
  │ ServiceAccount   │
  │   (my-sa)        │
  └────────┬─────────┘
           │
           │ RoleBinding 引用
           ▼
  ┌──────────────────────┐      ┌──────────────────┐
  │  RoleBinding          │      │  Role             │
  │  (pod-reader-binding) │─────►│  (pod-reader)     │
  │  roleRef:             │      │  rules:           │
  │    kind: Role         │      │  - pods: get,list │
  │    name: pod-reader   │      │  - services:      │
  │  subjects:            │      │    get,list       │
  │  - kind: SA           │      └──────────────────┘
  │    name: my-sa        │
  └──────────────────────┘

  Pod (serviceAccountName: my-sa)
  └── 挂载 SA token -> 访问 API Server
      └── RBAC 校验: my-sa 有 pod-reader 的权限
""",
        example_yaml="""\
# Role                                        # 权限定义
apiVersion: rbac.authorization.k8s.io/v1      # RBAC API 版本
kind: Role                                    # 资源类型: Role
metadata:                                     # 元数据
  name: pod-reader                            # Role 名称
rules:                                        # 权限规则
- apiGroups: [""]                             # 核心 API 组
  resources: ["pods", "services"]             # 可操作的资源
  verbs: ["get", "list"]                      # 允许的操作
---                                           # 多文档分隔
# RoleBinding                                 # 权限绑定
apiVersion: rbac.authorization.k8s.io/v1      # RBAC API 版本
kind: RoleBinding                             # 资源类型: RoleBinding
metadata:                                     # 元数据
  name: pod-reader-binding                    # 名称
roleRef:                                      # 引用 Role
  kind: Role                                  # 角色类型
  name: pod-reader                            # Role 名称
  apiGroup: rbac.authorization.k8s.io         # API 组
subjects:                                     # 被授权主体
- kind: ServiceAccount                        # 主体类型
  name: my-sa                                 # SA 名称（真实集群中需先创建 SA）
  namespace: default                          # 命名空间
""",
        common_errors=[
            "RoleBinding 的 roleRef.name 与 Role 名称不匹配",
            "subjects 中 ServiceAccount 的 namespace 写错",
            "忘记创建 ServiceAccount（只创建了 Role 和 RoleBinding）",
            "Role 的 apiGroups 写成了 v1 而非空字符串",
        ],
        tips=[
            "用 kubectl auth can-i --as=system:serviceaccount:default:my-sa 验证权限",
            "Pod 需要指定 serviceAccountName: my-sa 才能使用自定义 SA",
            "用 kubectl auth can-i --list --as=... 查看所有授权的操作",
        ],
    ),
)


CHAPTER_9_LEVELS: list[Level] = [
    LEVEL_Q9_1, LEVEL_Q9_2, LEVEL_Q9_3, LEVEL_Q9_4, LEVEL_Q9_5,
]
