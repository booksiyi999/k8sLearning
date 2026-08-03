"""Chapter 12: NetworkPolicy（网络策略）（5 关）

Q12.1 创建 NetworkPolicy（默认拒绝）
Q12.2 允许特定命名空间
Q12.3 允许特定 Pod
Q12.4 入站/出站规则
Q12.5 集群实战 - 数据库网络隔离
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q12.1 创建 NetworkPolicy（默认拒绝） ====================

def _check_121_default_deny(user_yaml: str) -> CheckResult:
    """Q12.1 创建默认拒绝所有入站的 NetworkPolicy"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.networkpolicies:
        return CheckResult(
            ok=False,
            error="没有创建任何 NetworkPolicy",
            hints=["你需要 apply 一个 kind: NetworkPolicy 的 YAML"],
        )

    np_name = next(iter(state.networkpolicies))
    np = state.networkpolicies[np_name]
    spec = np.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="NetworkPolicy 缺少 spec", hints=[])

    # 验证 podSelector 为空（选择所有 Pod）
    pod_selector = spec.get("podSelector")
    if pod_selector is None:
        return CheckResult(
            ok=False,
            error="NetworkPolicy 缺少 spec.podSelector",
            hints=["设置 spec.podSelector: {} 来选择命名空间下所有 Pod"],
        )
    if not isinstance(pod_selector, dict) or pod_selector:
        return CheckResult(
            ok=False,
            error="默认拒绝策略的 podSelector 应为空映射 {}（选择所有 Pod）",
            hints=["使用 podSelector: {} 选择命名空间下所有 Pod"],
        )

    # 验证 policyTypes 包含 "Ingress"
    policy_types = spec.get("policyTypes")
    if not isinstance(policy_types, list) or "Ingress" not in policy_types:
        return CheckResult(
            ok=False,
            error="NetworkPolicy 的 policyTypes 必须包含 'Ingress'",
            hints=["设置 spec.policyTypes: ['Ingress']"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["默认拒绝策略创建成功！所有入站流量已被隔离 🛡️"],
    )


LEVEL_Q12_1 = Level(
    id="Q12.1",
    chapter="ch12",
    title="创建 NetworkPolicy（默认拒绝）",
    description="""
# 创建 NetworkPolicy（默认拒绝）🛡️

**NetworkPolicy** 是 Kubernetes 中控制 Pod 间网络通信的防火墙规则。

## 任务

创建一个 NetworkPolicy，实现**默认拒绝所有入站流量**：
- `kind: NetworkPolicy`
- `apiVersion: networking.k8s.io/v1`
- `spec.podSelector: {}`（选择命名空间下所有 Pod）
- `spec.policyTypes: ["Ingress"]`（仅控制入站）

## 提示

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  # podSelector: 选择目标 Pod
  # policyTypes: 指定策略类型
""",
    check_fn=_check_121_default_deny,
    lesson=Lesson(
        concept="""\
## 什么是 NetworkPolicy？

**NetworkPolicy** 是 Kubernetes 的网络防火墙机制，用于控制 Pod 之间以及 Pod 与外部之间的网络通信。它基于标签（labels）选择目标 Pod，并定义允许的入站（ingress）和出站（egress）流量规则。

### CNI 插件要求

NetworkPolicy 不是 K8s 核心组件直接实现的，而是依赖 **CNI（Container Network Interface）插件** 提供支持：

| CNI 插件 | NetworkPolicy 支持 |
|----------|-------------------|
| Calico | ✅ 完整支持 |
| Cilium | ✅ 完整支持 |
| Flannel | ❌ 原生不支持（需配合 Calico） |
| Weave Net | ✅ 支持 |
| AWS VPC CNI | ⚠️ 需配合 Calico 策略 |

如果 CNI 不支持 NetworkPolicy，创建的规则将被忽略，Pod 间通信不受限制。

### 默认行为

K8s 集群**默认允许所有流量**——任何 Pod 都可以访问任何 Pod。这种"默认开放"模型适合开发环境，但在生产环境中存在安全隐患。

### 默认拒绝策略

创建一个 `podSelector: {}`（选择所有 Pod）且不定义 `ingress` 规则的 NetworkPolicy，可以实现**默认拒绝所有入站**：

- `podSelector: {}` = 选择命名空间下所有 Pod
- 不写 `ingress` = 没有允许的入站规则
- `policyTypes: ["Ingress"]` = 声明只管控入站

这是安全加固的第一步，之后再通过"白名单"策略逐条放行需要的流量。
""",
        key_fields=[
            {"name": "spec.podSelector", "description": "选择策略应用的目标 Pod，{} 表示选择所有", "required": True, "example": "{}"},
            {"name": "spec.policyTypes", "description": "策略类型列表: Ingress / Egress", "required": True, "example": "['Ingress']"},
            {"name": "spec.ingress", "description": "入站规则列表，不写则拒绝所有入站", "required": False, "example": "[]"},
            {"name": "spec.egress", "description": "出站规则列表，不写则拒绝所有出站", "required": False, "example": "[]"},
        ],
        diagram="""\
  默认拒绝（Default Deny）策略模型

  ┌─── Namespace: default ───────────────────────┐
  │                                               │
  │   外部流量 (Ingress)                           │
  │        │                                      │
  │        ▼                                      │
  │   ┌─────────────────────┐                     │
  │   │  NetworkPolicy       │                     │
  │   │  podSelector: {}     │  ← 选择所有 Pod     │
  │   │  policyTypes:        │                     │
  │   │  - Ingress           │  ← 只管控入站       │
  │   │  ingress: (未定义)   │  ← 没有允许规则     │
  │   └──────────┬──────────┘                     │
  │              │                                │
  │     ❌ 所有入站流量被拒绝                      │
  │              │                                │
  │   ┌──────┐ ┌──────┐ ┌──────┐                  │
  │   │ Pod A │ │ Pod B │ │ Pod C │               │
  │   └──────┘ └──────┘ └──────┘                  │
  │                                               │
  └───────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型: NetworkPolicy
metadata:                                    # 元数据
  name: default-deny                         # 策略名称
  namespace: default                         # 命名空间（可选，默认 default）
spec:                                        # 规格定义
  podSelector: {}                            # 空选择器 = 所有 Pod
  policyTypes:                               # 策略类型
  - Ingress                                  # 仅控制入站流量
  # 不写 ingress = 拒绝所有入站
""",
        common_errors=[
            "CNI 不支持 NetworkPolicy（如纯 Flannel），规则不生效",
            "podSelector 写成了具体标签而非 {}，只隔离了部分 Pod",
            "忘记写 policyTypes，策略可能不按预期生效",
            "误以为 NetworkPolicy 能跨命名空间直接拒绝（实际是命名空间级别的）",
        ],
        tips=[
            "先用 kubectl get networkpolicy 查看已创建的策略",
            "默认拒绝是安全基线，之后再用白名单策略放行必要流量",
            "用 kubectl describe networkpolicy <name> 查看详细规则",
        ],
    ),
)


# ==================== Q12.2 允许特定命名空间 ====================

def _check_122_allow_namespace(user_yaml: str) -> CheckResult:
    """Q12.2 创建 NetworkPolicy 允许 from 命名空间 frontend 的流量"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.networkpolicies:
        return CheckResult(
            ok=False,
            error="没有创建任何 NetworkPolicy",
            hints=["你需要 apply 一个 kind: NetworkPolicy 的 YAML"],
        )

    np_name = next(iter(state.networkpolicies))
    np = state.networkpolicies[np_name]
    spec = np.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="NetworkPolicy 缺少 spec", hints=[])

    # 验证 policyTypes 包含 "Ingress"
    policy_types = spec.get("policyTypes")
    if not isinstance(policy_types, list) or "Ingress" not in policy_types:
        return CheckResult(
            ok=False,
            error="policyTypes 必须包含 'Ingress'",
            hints=["设置 spec.policyTypes: ['Ingress']"],
        )

    # 验证 ingress 规则存在
    ingress_rules = spec.get("ingress")
    if not isinstance(ingress_rules, list) or not ingress_rules:
        return CheckResult(
            ok=False,
            error="缺少 spec.ingress 规则（需要定义允许的入站规则）",
            hints=["在 spec.ingress 下添加 from 规则"],
        )

    # 验证 ingress.from 中有 namespaceSelector
    found_namespace_selector = False
    for rule in ingress_rules:
        if not isinstance(rule, dict):
            continue
        from_list = rule.get("from")
        if not isinstance(from_list, list):
            continue
        for src in from_list:
            if not isinstance(src, dict):
                continue
            if "namespaceSelector" in src:
                found_namespace_selector = True
                break
        if found_namespace_selector:
            break

    if not found_namespace_selector:
        return CheckResult(
            ok=False,
            error="ingress.from 中缺少 namespaceSelector",
            hints=["在 ingress[].from[] 下添加 namespaceSelector 来选择命名空间"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["命名空间级别放行策略创建成功！frontend 命名空间的流量已被允许 🌐"],
    )


LEVEL_Q12_2 = Level(
    id="Q12.2",
    chapter="ch12",
    title="允许特定命名空间",
    description="""
# 允许特定命名空间 🌐

在默认拒绝的基础上，通过 **namespaceSelector** 放行来自特定命名空间的流量。

## 任务

创建一个 NetworkPolicy，允许来自 `frontend` 命名空间的流量访问当前命名空间的 Pod：
- `spec.policyTypes: ["Ingress"]`
- `spec.ingress` 中定义 `from` 规则
- `from` 中使用 `namespaceSelector` 匹配命名空间标签 `kubernetes.io/metadata.name: frontend`

## 提示

```yaml
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-frontend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  # from: 添加 namespaceSelector 规则
""",
    check_fn=_check_122_allow_namespace,
    lesson=Lesson(
        concept="""\
## namespaceSelector —— 命名空间级别的流量控制

NetworkPolicy 的 `ingress.from` 支持三种来源选择器：

1. **namespaceSelector** —— 按命名空间标签选择整个命名空间
2. **podSelector** —— 按 Pod 标签选择特定 Pod
3. **namespaceSelector + podSelector** —— 同时限定命名空间和 Pod（AND 逻辑）

### namespaceSelector 工作原理

`namespaceSelector` 使用 `matchLabels` 或 `matchExpressions` 匹配命名空间的标签。K8s 1.21+ 会自动为每个命名空间添加标签 `kubernetes.io/metadata.name: <namespace-name>`，这是最常用的匹配方式。

### 白名单模型

NetworkPolicy 采用**白名单模型**：只有明确允许的流量才能通过。这意味着：
- 创建了 NetworkPolicy 后，未匹配规则的流量**全部被拒绝**
- 需要逐条添加 `ingress` 规则来放行必要流量
- 多个 NetworkPolicy 是**叠加（additive）**的——任何一个策略允许的流量都会放行

### 使用场景

- 只允许 `frontend` 命名空间访问 `backend` 的 API
- 只允许 `monitoring` 命名空间（Prometheus）抓取指标
- 只允许 `ingress-nginx` 命名空间的流量进入应用 Pod
""",
        key_fields=[
            {"name": "spec.ingress[].from[]", "description": "入站来源选择器列表", "required": True, "example": "[{namespaceSelector: {matchLabels: {...}}}]"},
            {"name": "spec.ingress[].from[].namespaceSelector", "description": "按命名空间标签选择来源命名空间", "required": True, "example": "{matchLabels: {kubernetes.io/metadata.name: frontend}}"},
            {"name": "spec.ingress[].from[].namespaceSelector.matchLabels", "description": "命名空间标签匹配条件", "required": True, "example": "{kubernetes.io/metadata.name: frontend}"},
            {"name": "spec.policyTypes", "description": "策略类型，Ingress 控制入站", "required": True, "example": "['Ingress']"},
        ],
        diagram="""\
  namespaceSelector 流量控制模型

  ┌─── Namespace: frontend ──────┐
  │  ┌──────┐  ┌──────┐          │
  │  │ Pod A│  │ Pod B│          │
  │  └──┬───┘  └──┬───┘          │
  │     │         │               │
  └─────┼─────────┼──────────────┘
        │         │
        │ namespaceSelector:
        │   matchLabels:
        │     kubernetes.io/metadata.name: frontend
        │         │
        ▼         ▼
  ┌──────────────────────┐
  │  NetworkPolicy        │  ✅ 允许来自 frontend 的流量
  │  ingress:             │
  │  - from:              │
  │    - namespaceSelector│
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │  Namespace: backend   │
  │  ┌──────┐  ┌──────┐   │
  │  │ Pod C│  │ Pod D│   │
  │  └──────┘  └──────┘   │
  └───────────────────────┘

  ❌ 其他命名空间的流量被拒绝
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: allow-from-frontend                  # 策略名称
  namespace: backend                         # 目标命名空间
spec:                                        # 规格
  podSelector: {}                            # 选择所有 Pod
  policyTypes:                               # 策略类型
  - Ingress                                  # 控制入站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - namespaceSelector:                     # 按命名空间选择
        matchLabels:                         # 标签匹配
          kubernetes.io/metadata.name: frontend  # frontend 命名空间
""",
        common_errors=[
            "namespaceSelector 的 matchLabels 写成了命名空间名而非标签键值对",
            "忘记 K8s 1.21+ 自动添加的 kubernetes.io/metadata.name 标签",
            "from 下只写了 podSelector 而非 namespaceSelector，选择了同命名空间的 Pod",
            "误以为 namespaceSelector 可以直接写 namespace: frontend（这是错误语法）",
        ],
        tips=[
            "用 kubectl get ns --show-labels 查看命名空间的标签",
            "namespaceSelector + podSelector 组合使用可实现精确控制",
            "多个 NetworkPolicy 叠加生效，任何一个允许的流量都会放行",
        ],
    ),
)


# ==================== Q12.3 允许特定 Pod ====================

def _check_123_allow_pod(user_yaml: str) -> CheckResult:
    """Q12.3 创建 NetworkPolicy 允许特定标签的 Pod 访问"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.networkpolicies:
        return CheckResult(
            ok=False,
            error="没有创建任何 NetworkPolicy",
            hints=["你需要 apply 一个 kind: NetworkPolicy 的 YAML"],
        )

    np_name = next(iter(state.networkpolicies))
    np = state.networkpolicies[np_name]
    spec = np.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="NetworkPolicy 缺少 spec", hints=[])

    # 验证 policyTypes 包含 "Ingress"
    policy_types = spec.get("policyTypes")
    if not isinstance(policy_types, list) or "Ingress" not in policy_types:
        return CheckResult(
            ok=False,
            error="policyTypes 必须包含 'Ingress'",
            hints=["设置 spec.policyTypes: ['Ingress']"],
        )

    # 验证 ingress 规则存在
    ingress_rules = spec.get("ingress")
    if not isinstance(ingress_rules, list) or not ingress_rules:
        return CheckResult(
            ok=False,
            error="缺少 spec.ingress 规则",
            hints=["在 spec.ingress 下添加 from 规则"],
        )

    # 验证 ingress.from 中有 podSelector
    found_pod_selector = False
    for rule in ingress_rules:
        if not isinstance(rule, dict):
            continue
        from_list = rule.get("from")
        if not isinstance(from_list, list):
            continue
        for src in from_list:
            if not isinstance(src, dict):
                continue
            if "podSelector" in src:
                found_pod_selector = True
                break
        if found_pod_selector:
            break

    if not found_pod_selector:
        return CheckResult(
            ok=False,
            error="ingress.from 中缺少 podSelector",
            hints=["在 ingress[].from[] 下添加 podSelector 来选择特定 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Pod 级别放行策略创建成功！特定标签的 Pod 已被允许访问 🎯"],
    )


LEVEL_Q12_3 = Level(
    id="Q12.3",
    chapter="ch12",
    title="允许特定 Pod",
    description="""
# 允许特定 Pod 🎯

通过 **podSelector** 在 `ingress.from` 中放行特定标签的 Pod。

## 任务

创建一个 NetworkPolicy，允许带有标签 `app: api-client` 的 Pod 访问当前 Pod：
- `spec.policyTypes: ["Ingress"]`
- `spec.ingress` 中定义 `from` 规则
- `from` 中使用 `podSelector` 匹配 `app: api-client`

## 提示

```yaml
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-client
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-client
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  # from: 添加 podSelector 规则
""",
    check_fn=_check_123_allow_pod,
    lesson=Lesson(
        concept="""\
## podSelector —— Pod 级别的流量控制

在 `ingress.from` 中使用 `podSelector` 可以精确控制**哪些 Pod** 可以访问目标 Pod。与 `namespaceSelector` 不同，`podSelector` 默认只选择**同一命名空间**内的 Pod。

### podSelector vs namespaceSelector

| 选择器 | 作用域 | 选择粒度 |
|--------|--------|---------|
| podSelector | 同命名空间 | 按 Pod 标签选择 |
| namespaceSelector | 跨命名空间 | 按命名空间标签选择 |
| 两者组合 | 跨命名空间 | 同时限定命名空间和 Pod |

### 组合使用（AND 逻辑）

当 `from` 的一个元素同时包含 `namespaceSelector` 和 `podSelector` 时，两者是 **AND** 关系——必须同时满足：

```yaml
from:
- namespaceSelector:    # 选择命名空间
    matchLabels:
      kubernetes.io/metadata.name: frontend
  podSelector:          # AND: 同时选择该命名空间内的 Pod
    matchLabels:
      app: web-client
```

### from 列表的 OR 逻辑

`from` 列表中的多个元素是 **OR** 关系——满足任一即可：

```yaml
from:
- podSelector:          # 来源 1: 特定 Pod
    matchLabels:
      app: api-client
- namespaceSelector:    # 来源 2: 特定命名空间
    matchLabels:
      kubernetes.io/metadata.name: monitoring
```

### 端口限制

`ingress` 规则还可以通过 `ports` 限制允许访问的端口：
```yaml
ingress:
- from:
  - podSelector:
      matchLabels:
        app: api-client
  ports:
  - protocol: TCP
    port: 8080
```
""",
        key_fields=[
            {"name": "spec.ingress[].from[].podSelector", "description": "按 Pod 标签选择来源 Pod（同命名空间）", "required": True, "example": "{matchLabels: {app: api-client}}"},
            {"name": "spec.ingress[].from[].podSelector.matchLabels", "description": "Pod 标签匹配条件", "required": True, "example": "{app: api-client}"},
            {"name": "spec.ingress[].ports", "description": "允许访问的端口列表", "required": False, "example": "[{protocol: TCP, port: 8080}]"},
            {"name": "spec.policyTypes", "description": "策略类型", "required": True, "example": "['Ingress']"},
        ],
        diagram="""\
  podSelector 流量控制模型

  ┌─── Namespace: default ───────────────────┐
  │                                           │
  │  ┌──────────┐    ┌──────────┐            │
  │  │ Pod      │    │ Pod      │            │
  │  │ app:     │    │ app:     │            │
  │  │ api-client  │  │ other    │            │
  │  └────┬─────┘    └────┬─────┘            │
  │       │               │                   │
  │       │ ✅ 匹配       │ ❌ 不匹配         │
  │       │ podSelector   │                   │
  │       │ matchLabels:  │                   │
  │       │   app: api-   │                   │
  │       │   client      │                   │
  │       ▼               │                   │
  │  ┌────────────────────┘                   │
  │  │                                        │
  │  ▼                                        │
  │  ┌──────────────────────┐                 │
  │  │  NetworkPolicy        │                 │
  │  │  ingress:             │                 │
  │  │  - from:              │                 │
  │  │    - podSelector:     │                 │
  │  │        matchLabels:   │                 │
  │  │          app: api-    │                 │
  │  │          client       │                 │
  │  └──────────┬───────────┘                 │
  │             │                             │
  │             ▼                             │
  │  ┌──────────────────────┐                 │
  │  │  Target Pod           │                 │
  │  │  (被保护的 Pod)        │                 │
  │  └──────────────────────┘                 │
  └───────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: allow-api-client                     # 策略名称
spec:                                        # 规格
  podSelector:                               # 目标 Pod（被保护的）
    matchLabels:                             # 标签匹配
      app: backend                           # 保护 app=backend 的 Pod
  policyTypes:                               # 策略类型
  - Ingress                                  # 控制入站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - podSelector:                           # 按 Pod 标签选择
        matchLabels:                         # 标签匹配
          app: api-client                    # 只允许 app=api-client 的 Pod
  ports:                                     # 允许端口（可选）
  - protocol: TCP                            # 协议
    port: 8080                               # 端口号
""",
        common_errors=[
            "podSelector 写在了 spec 顶层而非 ingress.from 内部，变成了选择目标 Pod 而非来源 Pod",
            "from 下多个元素误以为是 AND 关系（实际是 OR）",
            "namespaceSelector 和 podSelector 在同一个 from 元素中时误以为是 OR（实际是 AND）",
            "忘记 ports 限制导致所有端口都开放",
        ],
        tips=[
            "from 列表的多个元素是 OR 关系，同一元素内的多个选择器是 AND 关系",
            "podSelector 默认只匹配同命名空间的 Pod，跨命名空间需组合 namespaceSelector",
            "用 kubectl get networkpolicy -o yaml 查看完整策略定义",
        ],
    ),
)


# ==================== Q12.4 入站/出站规则 ====================

def _check_124_ingress_egress(user_yaml: str) -> CheckResult:
    """Q12.4 创建同时配置 ingress 和 egress 的 NetworkPolicy"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.networkpolicies:
        return CheckResult(
            ok=False,
            error="没有创建任何 NetworkPolicy",
            hints=["你需要 apply 一个 kind: NetworkPolicy 的 YAML"],
        )

    np_name = next(iter(state.networkpolicies))
    np = state.networkpolicies[np_name]
    spec = np.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="NetworkPolicy 缺少 spec", hints=[])

    # 验证 policyTypes 同时包含 "Ingress" 和 "Egress"
    policy_types = spec.get("policyTypes")
    if not isinstance(policy_types, list):
        return CheckResult(
            ok=False,
            error="NetworkPolicy 缺少 spec.policyTypes",
            hints=["设置 spec.policyTypes: ['Ingress', 'Egress']"],
        )

    has_ingress = "Ingress" in policy_types
    has_egress = "Egress" in policy_types

    if not has_ingress:
        return CheckResult(
            ok=False,
            error="policyTypes 缺少 'Ingress'",
            hints=["在 policyTypes 中添加 'Ingress'"],
        )
    if not has_egress:
        return CheckResult(
            ok=False,
            error="policyTypes 缺少 'Egress'",
            hints=["在 policyTypes 中添加 'Egress'"],
        )

    # 验证 ingress 和 egress 规则都存在
    ingress = spec.get("ingress")
    if not isinstance(ingress, list):
        return CheckResult(
            ok=False,
            error="缺少 spec.ingress 规则",
            hints=["添加 ingress 规则定义入站白名单"],
        )

    egress = spec.get("egress")
    if not isinstance(egress, list):
        return CheckResult(
            ok=False,
            error="缺少 spec.egress 规则",
            hints=["添加 egress 规则定义出站白名单"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["入站+出站双向策略创建成功！网络隔离已全面配置 🔒"],
    )


LEVEL_Q12_4 = Level(
    id="Q12.4",
    chapter="ch12",
    title="入站/出站规则",
    description="""
# 入站/出站规则 🔒

NetworkPolicy 可以同时控制 **Ingress（入站）** 和 **Egress（出站）** 流量，实现双向网络隔离。

## 任务

创建一个 NetworkPolicy，同时配置 ingress 和 egress：
- `spec.policyTypes: ["Ingress", "Egress"]`
- `spec.ingress` 定义入站白名单规则
- `spec.egress` 定义出站白名单规则

## 提示

```yaml
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
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-egress-policy
spec:
  podSelector: {}
  policyTypes:
  # 添加 Ingress 和 Egress
  # ingress: 添加入站规则
  # egress: 添加出站规则
""",
    check_fn=_check_124_ingress_egress,
    lesson=Lesson(
        concept="""\
## 双向网络隔离：Ingress + Egress

NetworkPolicy 的 `policyTypes` 字段声明策略管控的流量方向：

- **Ingress** —— 控制进入 Pod 的流量（谁能访问我）
- **Egress** —— 控制 Pod 发出的流量（我能访问谁）

当 `policyTypes` 包含某个方向但对应规则为空或未定义时，该方向的所有流量将被**默认拒绝**。

### Egress 规则结构

`egress` 规则与 `ingress` 对称，使用 `to` 代替 `from`：

```yaml
egress:
- to:
  - podSelector:          # 目标 Pod
      matchLabels:
        app: database
  ports:                  # 允许的端口
  - protocol: TCP
    port: 5432
```

### 常见双向隔离场景

**微服务零信任网络**：每个服务只能访问明确允许的下游服务：
- frontend → backend (端口 8080)
- backend → database (端口 5432)
- backend → redis (端口 6379)

### DNS 放行陷阱

配置 Egress 后，Pod 的 DNS 解析也会被阻断。必须放行 DNS 流量：

```yaml
egress:
- to:
  - namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: kube-system
    podSelector:
      matchLabels:
        k8s-app: kube-dns
  ports:
  - protocol: UDP
    port: 53
```

### policyTypes 推断规则

如果未显式声明 `policyTypes`，K8s 会根据 `ingress`/`egress` 字段是否存在自动推断。但最佳实践是**显式声明**，避免歧义。
""",
        key_fields=[
            {"name": "spec.policyTypes", "description": "策略类型，同时包含 Ingress 和 Egress", "required": True, "example": "['Ingress', 'Egress']"},
            {"name": "spec.ingress", "description": "入站规则列表，定义允许的来源流量", "required": True, "example": "[{from: [{podSelector: {...}}]}]"},
            {"name": "spec.egress", "description": "出站规则列表，定义允许的目标流量", "required": True, "example": "[{to: [{podSelector: {...}}]}]"},
            {"name": "spec.egress[].to[].podSelector", "description": "出站目标 Pod 选择器", "required": False, "example": "{matchLabels: {app: database}}"},
            {"name": "spec.egress[].ports", "description": "出站允许的端口", "required": False, "example": "[{protocol: TCP, port: 5432}]"},
        ],
        diagram="""\
  Ingress + Egress 双向隔离模型

         入站流量 (Ingress)
              │
              ▼
  ┌────────────────────────────┐
  │  NetworkPolicy              │
  │  policyTypes:               │
  │  - Ingress                  │
  │  - Egress                   │
  │                             │
  │  ingress:                   │
  │  - from:                    │
  │    - podSelector:           │
  │        app: frontend        │
  │                             │
  │  egress:                    │
  │  - to:                      │
  │    - podSelector:           │
  │        app: database        │
  │    ports:                   │
  │    - TCP 5432               │
  └────────────┬───────────────┘
               │
               ▼
         出站流量 (Egress)

  ✅ frontend Pod ──> 当前 Pod ──> database Pod:5432
  ❌ 其他来源       ──X──> 当前 Pod
  ❌ 当前 Pod ──X──> 其他目标（除了 database:5432）
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: ingress-egress-policy               # 策略名称
spec:                                        # 规格
  podSelector:                               # 目标 Pod
    matchLabels:
      app: backend                           # 保护 app=backend
  policyTypes:                               # 策略类型（双向）
  - Ingress                                  # 控制入站
  - Egress                                   # 控制出站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - podSelector:                           # 按 Pod 标签
        matchLabels:
          app: frontend                      # 只允许 frontend
  ports:                                     # 入站端口
  - protocol: TCP
    port: 8080
  egress:                                    # 出站规则
  - to:                                      # 允许目标
    - podSelector:                           # 按 Pod 标签
        matchLabels:
          app: database                      # 只允许访问 database
    ports:                                   # 出站端口
    - protocol: TCP
      port: 5432                             # PostgreSQL 端口
""",
        common_errors=[
            "配置 Egress 后忘记放行 DNS 流量，导致 Pod 无法解析服务名",
            "policyTypes 只写了 Ingress 忘记 Egress，出站不受控",
            "egress.to 和 ingress.from 语法混淆（to 用于出站，from 用于入站）",
            "egress 规则为空但 policyTypes 包含 Egress，导致所有出站被拒绝",
        ],
        tips=[
            "配置 Egress 时务必放行 kube-system 的 DNS 流量（UDP 53）",
            "显式声明 policyTypes 比依赖自动推断更安全",
            "用 kubectl describe networkpolicy <name> 查看完整的入站和出站规则",
        ],
    ),
)


# ==================== Q12.5 集群实战 - 数据库网络隔离 ====================

def _check_125_db_isolation(user_yaml: str) -> CheckResult:
    """Q12.5 集群实战 - 部署 NetworkPolicy 隔离数据库"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.networkpolicies:
        return CheckResult(
            ok=False,
            error="没有创建任何 NetworkPolicy",
            hints=["你需要 apply 一个 kind: NetworkPolicy 的 YAML"],
        )

    np_name = next(iter(state.networkpolicies))
    np = state.networkpolicies[np_name]
    spec = np.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="NetworkPolicy 缺少 spec", hints=[])

    # 验证 podSelector 选择数据库 Pod（非空）
    pod_selector = spec.get("podSelector")
    if not isinstance(pod_selector, dict):
        return CheckResult(
            ok=False,
            error="NetworkPolicy 缺少 spec.podSelector",
            hints=["设置 podSelector 匹配数据库 Pod 的标签"],
        )
    if not pod_selector:
        return CheckResult(
            ok=False,
            error="podSelector 为空，应选择数据库 Pod（如 matchLabels: {app: database}）",
            hints=["设置 podSelector.matchLabels 匹配数据库 Pod 标签"],
        )

    # 验证 policyTypes 包含 Ingress
    policy_types = spec.get("policyTypes")
    if not isinstance(policy_types, list) or "Ingress" not in policy_types:
        return CheckResult(
            ok=False,
            error="policyTypes 必须包含 'Ingress' 来控制入站",
            hints=["设置 spec.policyTypes: ['Ingress']"],
        )

    # 验证 ingress 规则存在且包含 from
    ingress_rules = spec.get("ingress")
    if not isinstance(ingress_rules, list) or not ingress_rules:
        return CheckResult(
            ok=False,
            error="缺少 ingress 规则（需要定义允许访问数据库的白名单）",
            hints=["添加 ingress 规则，使用 from 限制可访问的来源"],
        )

    # 验证至少有一条 from 规则
    has_from = False
    for rule in ingress_rules:
        if isinstance(rule, dict) and isinstance(rule.get("from"), list) and rule["from"]:
            has_from = True
            break

    if not has_from:
        return CheckResult(
            ok=False,
            error="ingress 规则中缺少 from 定义（需要指定允许访问数据库的来源）",
            hints=["在 ingress[].from[] 中定义允许的来源 Pod 或命名空间"],
        )

    # 验证有端口限制（最佳实践）
    has_ports = False
    for rule in ingress_rules:
        if isinstance(rule, dict) and isinstance(rule.get("ports"), list) and rule["ports"]:
            has_ports = True
            break

    hints = [
        "YAML 校验通过！在真实集群上执行：",
        "  kubectl apply -f <your-yaml>",
        "  kubectl get networkpolicy",
        "  kubectl describe networkpolicy <name>",
    ]
    if not has_ports:
        hints.append("  ⚠️ 建议: 添加 ports 限制只允许数据库端口（如 TCP 5432）")

    return CheckResult(
        ok=True, state=state,
        hints=hints,
    )


LEVEL_Q12_5 = Level(
    id="Q12.5",
    chapter="ch12",
    title="集群实战: 数据库网络隔离",
    description="""
# 集群实战: 数据库网络隔离 🏗️

在真实集群中部署 NetworkPolicy，实现数据库 Pod 的网络隔离——只允许应用层 Pod 访问，拒绝其他所有流量。

## 任务

创建一个 NetworkPolicy 保护数据库 Pod：
- `podSelector` 选择标签 `app: database` 的 Pod
- `policyTypes: ["Ingress"]`
- `ingress` 中定义 `from` 规则，只允许 `app: backend` 的 Pod 访问
- （建议）`ports` 限制只允许 TCP 5432（PostgreSQL 端口）

## 验证步骤

```bash
# 1. 部署 NetworkPolicy
kubectl apply -f db-networkpolicy.yaml

# 2. 查看策略
kubectl get networkpolicy
kubectl describe networkpolicy db-isolation

# 3. 测试连通性
# 从 backend Pod 访问 database（应成功）
kubectl exec -it <backend-pod> -- psql -h database-svc -U user -p 5432

# 从其他 Pod 访问 database（应被拒绝）
kubectl exec -it <random-pod> -- psql -h database-svc -U user -p 5432
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-isolation
spec:
  # podSelector: 选择 app=database 的 Pod
  # policyTypes: 添加 Ingress
  # ingress: 添加 from 规则，只允许 app=backend 的 Pod
""",
    check_fn=_check_125_db_isolation,
    lesson=Lesson(
        concept="""\
## 数据库网络隔离实战

数据库是集群中最敏感的资源之一，通常存储用户数据、业务数据等关键信息。通过 NetworkPolicy 实现网络隔离是保护数据库的核心安全措施。

### 数据库隔离架构

```
                ┌─────────────────────────────┐
                │      Kubernetes Cluster      │
                │                              │
  ┌──────┐     │  ┌──────┐     ┌──────────┐  │
  │用户  │────►│  │frontend│───►│  backend  │  │
  └──────┘     │  └──────┘     └─────┬─────┘  │
                │                      │        │
                │     NetworkPolicy    │        │
                │     ✅ app=backend   │        │
                │     ✅ port 5432     │        │
                │           │          ▼        │
                │           ▼    ┌──────────┐  │
                │     ┌──────────┤ database │  │
                │     │          └──────────┘  │
                │     │                        │
                │  ❌ 其他 Pod 被拒绝          │
                └─────────────────────────────┘
```

### 生产环境最佳实践

1. **最小权限原则**：只允许必要的 Pod 访问数据库，且限制端口
2. **命名空间隔离**：数据库和应用分属不同命名空间，通过 namespaceSelector 控制
3. **Egress 控制**：同时限制数据库的出站流量，防止数据泄露
4. **多层防御**：NetworkPolicy + RBAC + Pod Security Policy 综合防护
5. **监控与审计**：监控 NetworkPolicy 的变更，审计网络流量

### 完整的安全分层

```
安全性从外到内：
  ┌─────────────────────────────┐
  │  Cluster NetworkPolicy      │  ← 集群级网络隔离
  │  ┌───────────────────────┐  │
  │  │  Namespace Policy     │  │  ← 命名空间级隔离
  │  │  ┌─────────────────┐  │  │
  │  │  │  Pod Policy     │  │  │  ← Pod 级隔离
  │  │  │  ┌───────────┐  │  │  │
  │  │  │  │ Database  │  │  │  │
  │  │  │  └───────────┘  │  │  │
  │  │  └─────────────────┘  │  │
  │  └───────────────────────┘  │
  └─────────────────────────────┘
```
""",
        key_fields=[
            {"name": "spec.podSelector", "description": "选择数据库 Pod（非空，按标签匹配）", "required": True, "example": "{matchLabels: {app: database}}"},
            {"name": "spec.policyTypes", "description": "策略类型，至少包含 Ingress", "required": True, "example": "['Ingress']"},
            {"name": "spec.ingress[].from[]", "description": "允许访问数据库的来源白名单", "required": True, "example": "[{podSelector: {matchLabels: {app: backend}}}]"},
            {"name": "spec.ingress[].ports", "description": "允许访问的数据库端口", "required": False, "example": "[{protocol: TCP, port: 5432}]"},
        ],
        diagram="""\
  数据库网络隔离部署架构

  ┌─── Namespace: default ──────────────────────┐
  │                                              │
  │  ┌──────────┐     ┌──────────┐              │
  │  │ frontend │────►│ backend  │              │
  │  │  Pod     │     │  Pod     │              │
  │  └──────────┘     └────┬─────┘              │
  │                        │                    │
  │                        │ ✅ 允许             │
  │                        │ podSelector:        │
  │                        │   app: backend      │
  │                        ▼                    │
  │  ┌──────────────────────────────────────┐   │
  │  │  NetworkPolicy (db-isolation)        │   │
  │  │  podSelector:                        │   │
  │  │    matchLabels:                      │   │
  │  │      app: database                   │   │
  │  │  policyTypes: [Ingress]              │   │
  │  │  ingress:                            │   │
  │  │  - from:                             │   │
  │  │    - podSelector:                    │   │
  │  │        matchLabels:                  │   │
  │  │          app: backend                │   │
  │  │    ports:                            │   │
  │  │    - protocol: TCP                   │   │
  │  │      port: 5432                      │   │
  │  └──────────────┬───────────────────────┘   │
  │                 │                           │
  │                 ▼                           │
  │  ┌──────────────────────┐                   │
  │  │  Database Pod         │                   │
  │  │  app: database        │                   │
  │  │  Port: 5432           │                   │
  │  └──────────────────────┘                   │
  │                                              │
  │  ❌ 其他 Pod 无法访问数据库                   │
  └──────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: db-isolation                         # 策略名称
  namespace: default                         # 命名空间
spec:                                        # 规格
  podSelector:                               # 选择数据库 Pod
    matchLabels:                             # 标签匹配
      app: database                          # 数据库 Pod 标签
  policyTypes:                               # 策略类型
  - Ingress                                  # 控制入站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - podSelector:                           # 按 Pod 标签
        matchLabels:                         # 标签匹配
          app: backend                       # 只允许 backend Pod
    ports:                                   # 端口限制
    - protocol: TCP                          # 协议
      port: 5432                             # PostgreSQL 端口
""",
        common_errors=[
            "podSelector 为空 {}，隔离了所有 Pod 而非只隔离数据库",
            "from 规则写错标签，导致不允许任何 Pod 访问数据库（应用连接失败）",
            "忘记限制 ports，所有端口都对白名单 Pod 开放",
            "CNI 不支持 NetworkPolicy，策略创建了但不生效（如纯 Flannel）",
        ],
        tips=[
            "生产环境建议同时配置 Egress，防止数据库主动外连泄露数据",
            "用 kubectl exec 在不同 Pod 中测试连通性来验证策略效果",
            "数据库和应用分属不同命名空间时，需组合 namespaceSelector + podSelector",
        ],
    ),
)


CHAPTER_12_LEVELS: list[Level] = [
    LEVEL_Q12_1, LEVEL_Q12_2, LEVEL_Q12_3, LEVEL_Q12_4, LEVEL_Q12_5,
]
