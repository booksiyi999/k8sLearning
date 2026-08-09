"""Chapter 26: 高级调度 - Topology Spread/Descheduler（5 关）

Q26.1 Topology Spread Constraints - 拓扑分布约束
Q26.2 PodAntiAffinity 进阶 - 反亲和性高级用法
Q26.3 Descheduler 概念 - 重新调度策略
Q26.4 调度器配置 - 调度器策略配置
Q26.5 集群实战 - 高可用工作负载调度
"""
import yaml
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


def _parse_yaml_docs(user_yaml: str) -> list[dict]:
    """安全解析多文档 YAML，返回非 None 文档列表。"""
    docs = []
    for doc in yaml.safe_load_all(user_yaml):
        if doc is not None:
            docs.append(doc)
    return docs


# ==================== Q26.1 Topology Spread Constraints ====================

def _check_261_topology_spread(user_yaml: str) -> CheckResult:
    """Q26.1 创建带 Topology Spread Constraints 的 Deployment"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Deployment 的 YAML"],
        )

    deploy_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Deployment":
            deploy_doc = doc
            break

    if not deploy_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Deployment",
            hints=["你需要创建一个 kind: Deployment 的 YAML 🎯"],
        )

    spec = deploy_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    pod_spec = template.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    # 检查 topologySpreadConstraints
    tsc = pod_spec.get("topologySpreadConstraints")
    if not isinstance(tsc, list) or not tsc:
        return CheckResult(
            ok=False,
            error="缺少 topologySpreadConstraints",
            hints=["添加 spec.template.spec.topologySpreadConstraints"],
        )

    constraint = tsc[0]
    if not isinstance(constraint, dict):
        return CheckResult(ok=False, error="topologySpreadConstraints[0] 格式错误", hints=[])

    # 检查 maxSkew
    max_skew = constraint.get("maxSkew")
    if max_skew is None:
        return CheckResult(
            ok=False,
            error="topologySpreadConstraints[0] 缺少 maxSkew",
            hints=["设置 maxSkew: 1，表示拓扑域之间最大允许偏差"],
        )
    if not isinstance(max_skew, int) or max_skew < 1:
        return CheckResult(
            ok=False,
            error=f"maxSkew 应为正整数，实际为 {max_skew}",
            hints=["maxSkew: 1 是最常用的值"],
        )

    # 检查 topologyKey
    topology_key = constraint.get("topologyKey")
    if not topology_key:
        return CheckResult(
            ok=False,
            error="topologySpreadConstraints[0] 缺少 topologyKey",
            hints=["设置 topologyKey: kubernetes.io/hostname 或 topology.kubernetes.io/zone"],
        )

    # 检查 whenUnsatisfiable
    when_unsat = constraint.get("whenUnsatisfiable")
    if when_unsat not in ("DoNotSchedule", "ScheduleAnyway"):
        return CheckResult(
            ok=False,
            error=f"whenUnsatisfiable 应为 'DoNotSchedule' 或 'ScheduleAnyway'，实际为 '{when_unsat}'",
            hints=["DoNotSchedule: 不满足约束时不调度; ScheduleAnyway: 仍然调度但优先满足约束"],
        )

    # 检查 labelSelector
    label_selector = constraint.get("labelSelector")
    if not isinstance(label_selector, dict):
        return CheckResult(
            ok=False,
            error="topologySpreadConstraints[0] 缺少 labelSelector",
            hints=["需要 labelSelector 来匹配要分布的 Pod"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Topology Spread Constraints 确保 Pod 在拓扑域间均匀分布 🌐"],
    )


LEVEL_Q26_1 = Level(
    id="Q26.1",
    chapter="ch26",
    title="Topology Spread Constraints - 拓扑分布约束",
    description="""
# Topology Spread Constraints - 拓扑分布约束 🌐

**Topology Spread Constraints** 确保 Pod 在不同拓扑域（如节点、可用区）之间均匀分布，提高高可用性。

## 任务

创建一个带 Topology Spread Constraints 的 Deployment：
- `kind: Deployment`，名称 `web-spread`
- replicas: 4
- 容器 `web`，镜像 `nginx:1.25`
- topologySpreadConstraints:
  - maxSkew: 1
  - topologyKey: kubernetes.io/hostname
  - whenUnsatisfiable: DoNotSchedule
  - labelSelector 匹配 app: web-spread

## 提示

```yaml
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-spread
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-spread
spec:
  replicas: 4
  selector:
    matchLabels:
      app: web-spread
  template:
    metadata:
      labels:
        app: web-spread
    spec:
      containers:
      - name: web
        image: nginx:1.25
      # 添加 topologySpreadConstraints
""",
    check_fn=_check_261_topology_spread,
    lesson=Lesson(
        concept="""\
## Topology Spread Constraints

**Topology Spread Constraints** 是 K8s 1.19+ 的高级调度特性，控制 Pod 在**拓扑域**（节点、区域、可用区）之间的分布，确保高可用性。

### 核心字段

- **maxSkew**：拓扑域之间允许的最大 Pod 数量偏差
- **topologyKey**：拓扑域的标签键（如 hostname、zone）
- **whenUnsatisfiable**：约束不满足时的行为
  - `DoNotSchedule`：不调度（硬约束）
  - `ScheduleAnyway`：仍然调度（软约束，优先满足）
- **labelSelector**：选择要分布的 Pod

### 分布效果示例

```
maxSkew: 1, topologyKey: kubernetes.io/hostname

4 个 Pod, 3 个节点:
  node-a: 2 Pods  ─┐
  node-b: 1 Pod   ─┤ skew = 2-1 = 1 ≤ maxSkew ✓
  node-c: 1 Pod   ─┘

如果 node-a 有 3 Pods, node-b 有 0:
  skew = 3-0 = 3 > maxSkew(1) -> DoNotSchedule 拒绝
```

### 多维度拓扑分布

可以同时按 zone 和 hostname 分布：
- 先确保跨 zone 均匀（机房级容灾）
- 再确保跨 node 均匀（节点级容灾）

### Node Affinity vs Node Selector 对比

在 K8s 调度中，控制 Pod 调度到哪些节点有多种方式。Node Selector 是最简单的，Node Affinity 是其增强版：

| 特性 | Node Selector | Node Affinity |
|------|--------------|---------------|
| 语法 | `nodeSelector: {disk: ssd}` | `affinity.nodeAffinity: ...` |
| 约束类型 | 仅硬约束 | 硬约束 + 软约束 |
| 操作符 | 仅相等匹配 | In, NotIn, Exists, Gt, Lt |
| 多条件 | AND（全部满足） | 可配置多条件 + 软约束权重 |
| 版本 | v1 初始 | 1.2+（beta），1.19+（GA） |

**Node Selector 示例**（简单但功能有限）：

```yaml
spec:
  nodeSelector:
    disktype: ssd        # 必须调度到有 disktype=ssd 标签的节点
    zone: us-east-1a     # 且必须在 us-east-1a 区域
```

**Node Affinity 示例**（支持软约束和多种操作符）：

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:   # 硬约束
        nodeSelectorTerms:
        - matchExpressions:
          - key: disktype
            operator: In
            values: ["ssd", "nvme"]
      preferredDuringSchedulingIgnoredDuringExecution:  # 软约束
      - weight: 80
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values: ["us-east-1a"]
```

> **建议**：新项目直接使用 Node Affinity。Node Selector 保留仅为向后兼容，不支持软约束和复杂匹配。

### 与 Topology Spread 的配合

Node Affinity 控制"调度到哪些节点"，Topology Spread 控制"在这些节点间如何分布"：

```yaml
spec:
  affinity:
    nodeAffinity:                    # 先筛选符合条件的节点
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: node-role
            operator: In
            values: ["worker"]
  topologySpreadConstraints:         # 再在符合条件节点间均匀分布
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web-spread
```
""",
        key_fields=[
            {"name": "topologySpreadConstraints[].maxSkew", "description": "拓扑域间最大允许偏差", "required": True, "example": "1"},
            {"name": "topologySpreadConstraints[].topologyKey", "description": "拓扑域标签键", "required": True, "example": "kubernetes.io/hostname"},
            {"name": "topologySpreadConstraints[].whenUnsatisfiable", "description": "约束不满足时行为: DoNotSchedule 或 ScheduleAnyway", "required": True, "example": "DoNotSchedule"},
            {"name": "topologySpreadConstraints[].labelSelector", "description": "选择要分布的 Pod", "required": True, "example": "{matchLabels: {app: web}}"},
        ],
        diagram="""\
  Topology Spread: maxSkew=1, topologyKey=kubernetes.io/hostname

  ┌─────────── Deployment (web-spread, replicas: 4) ───────────┐
  │  topologySpreadConstraints:                                │
  │    maxSkew: 1                                              │
  │    topologyKey: kubernetes.io/hostname                     │
  │    whenUnsatisfiable: DoNotSchedule                        │
  └─────────────────────────┬──────────────────────────────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │ node-a  │   │ node-b  │   │ node-c  │
        │ Pod-0   │   │ Pod-1   │   │ Pod-2   │
        │ Pod-3   │   │         │   │         │
        │ (2)     │   │ (1)     │   │ (1)     │
        └─────────┘   └─────────┘   └─────────┘
         skew = 2-1 = 1 ≤ maxSkew(1) ✓
""",
        example_yaml="""\
apiVersion: apps/v1                       # Deployment API
kind: Deployment                          # 资源类型
metadata:                                 # 元数据
  name: web-spread                        # Deployment 名称
spec:                                     # 规格
  replicas: 4                             # 4 个副本
  selector:                               # 标签选择器
    matchLabels:
      app: web-spread
  template:                               # Pod 模板
    metadata:
      labels:
        app: web-spread
    spec:                                 # Pod 规格
      containers:                         # 容器列表
      - name: web                         # 容器名
        image: nginx:1.25                 # 镜像
      topologySpreadConstraints:          # 拓扑分布约束
      - maxSkew: 1                        # 最大偏差 1
        topologyKey: kubernetes.io/hostname  # 按节点分布
        whenUnsatisfiable: DoNotSchedule  # 不满足则不调度
        labelSelector:                    # 选择 Pod
          matchLabels:
            app: web-spread
""",
        common_errors=[
            "maxSkew 设为 0（不合法，最小为 1）",
            "topologyKey 写错（必须是节点上实际存在的标签键）",
            "labelSelector 不匹配 Pod 的 labels（导致约束不生效）",
            "whenUnsatisfiable 拼错或使用了不支持的值",
        ],
        tips=[
            "topologyKey: kubernetes.io/hostname 按节点分布，topology.kubernetes.io/zone 按区域分布",
            "多维度约束可以叠加：先跨 zone 再跨 node",
            "DoNotSchedule 是硬约束，节点不足时 Pod 会 Pending",
        ],
    ),
)


# ==================== Q26.2 PodAntiAffinity 进阶 ====================

def _check_262_anti_affinity(user_yaml: str) -> CheckResult:
    """Q26.2 创建带 PodAntiAffinity 的 Deployment"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Deployment 的 YAML"],
        )

    deploy_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Deployment":
            deploy_doc = doc
            break

    if not deploy_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Deployment",
            hints=["你需要创建一个 kind: Deployment 的 YAML 🎯"],
        )

    spec = deploy_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    pod_spec = template.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    # 检查 affinity
    affinity = pod_spec.get("affinity")
    if not isinstance(affinity, dict):
        return CheckResult(
            ok=False,
            error="缺少 spec.template.spec.affinity",
            hints=["添加 affinity 字段配置亲和/反亲和性"],
        )

    # 检查 podAntiAffinity
    pod_anti_affinity = affinity.get("podAntiAffinity")
    if not isinstance(pod_anti_affinity, dict):
        return CheckResult(
            ok=False,
            error="缺少 affinity.podAntiAffinity",
            hints=["在 affinity 下添加 podAntiAffinity"],
        )

    # 检查 requiredDuringScheduling 或 preferredDuringScheduling
    required = pod_anti_affinity.get("requiredDuringSchedulingIgnoredDuringExecution")
    preferred = pod_anti_affinity.get("preferredDuringSchedulingIgnoredDuringExecution")

    if not required and not preferred:
        return CheckResult(
            ok=False,
            error="podAntiAffinity 需要 requiredDuringSchedulingIgnoredDuringExecution 或 preferredDuringSchedulingIgnoredDuringExecution",
            hints=["添加硬约束或软约束的反亲和性规则"],
        )

    # 检查至少有一个含 topologyKey
    constraints = required if required else preferred
    if not isinstance(constraints, list) or not constraints:
        return CheckResult(
            ok=False,
            error="反亲和性规则列表为空",
            hints=["添加至少一条反亲和性规则"],
        )

    first_constraint = constraints[0]
    if not isinstance(first_constraint, dict):
        return CheckResult(ok=False, error="反亲和性规则格式错误", hints=[])

    # preferred 类型多一层 weight
    if preferred:
        first_constraint = first_constraint.get("podAffinityTerm", first_constraint)

    topology_key = first_constraint.get("topologyKey")
    if not topology_key:
        return CheckResult(
            ok=False,
            error="反亲和性规则缺少 topologyKey",
            hints=["设置 topologyKey: kubernetes.io/hostname"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["PodAntiAffinity 防止同一应用的 Pod 调度到同一节点，提高高可用 🛡️"],
    )


LEVEL_Q26_2 = Level(
    id="Q26.2",
    chapter="ch26",
    title="PodAntiAffinity 进阶 - 反亲和性高级用法",
    description="""
# PodAntiAffinity 进阶 - 反亲和性高级用法 🛡️

**PodAntiAffinity** 确保同一应用的 Pod 不被调度到同一节点或同一拓扑域，是高可用部署的核心手段。

## 任务

创建一个带 PodAntiAffinity 的 Deployment：
- `kind: Deployment`，名称 `ha-app`
- replicas: 3
- 容器 `app`，镜像 `nginx:1.25`
- podAntiAffinity：
  - **硬约束** requiredDuringSchedulingIgnoredDuringExecution：不允许同节点调度相同 label 的 Pod
  - topologyKey: kubernetes.io/hostname
  - labelSelector 匹配 app: ha-app

## 提示

```yaml
spec:
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: ha-app
            topologyKey: kubernetes.io/hostname
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      containers:
      - name: app
        image: nginx:1.25
      # 添加 affinity.podAntiAffinity
""",
    check_fn=_check_262_anti_affinity,
    lesson=Lesson(
        concept="""\
## PodAntiAffinity 进阶

**PodAntiAffinity** 告诉调度器：不要把匹配特定 label 的 Pod 调度到同一拓扑域。与 nodeAffinity 控制节点选择不同，podAntiAffinity 控制 **Pod 之间的关系**。

### 硬约束 vs 软约束

| 类型 | 字段 | 行为 |
|------|------|------|
| 硬约束 | requiredDuringSchedulingIgnoredDuringExecution | 必须满足，否则 Pod 保持 Pending |
| 软约束 | preferredDuringSchedulingIgnoredDuringExecution | 尽量满足，不满足也能调度 |

### 软约束示例（带 weight）

```yaml
preferredDuringSchedulingIgnoredDuringExecution:
- weight: 100
  podAffinityTerm:
    labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

### 典型高可用策略

1. **跨节点反亲和**：topologyKey = kubernetes.io/hostname
2. **跨区域反亲和**：topologyKey = topology.kubernetes.io/zone
3. **硬+软组合**：硬约束跨节点，软约束跨区域

### InterPodAffinity 反亲和性实战案例

**场景**：数据库集群（MySQL Primary + 2 Replica），确保三个 Pod 分布在不同节点，避免单节点故障导致全部数据库实例丢失。

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  replicas: 3
  serviceName: mysql
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      affinity:
        podAntiAffinity:
          # 硬约束：MySQL Pod 不能在同一节点
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values: ["mysql"]
            topologyKey: kubernetes.io/hostname
          # 软约束：尽量分布在不同可用区
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: mysql
              topologyKey: topology.kubernetes.io/zone
```

**调度效果**：
- 3 个 MySQL Pod 分别调度到 3 个不同节点（硬约束保证）
- 优先分布到不同可用区（软约束尽量满足）
- 如果集群只有 2 个节点，第 3 个 Pod 会 Pending

**另一个实战案例**：缓存服务（Redis）与计算服务避免同节点，防止资源争抢：

```yaml
# Redis Deployment 的反亲和性
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 50
    podAffinityTerm:
      labelSelector:
        matchLabels:
          app: compute-worker     # 避免与计算 Pod 同节点
      topologyKey: kubernetes.io/hostname
```

### PodAntiAffinity vs Topology Spread

- **PodAntiAffinity**：控制"不要在一起"
- **Topology Spread**：控制"均匀分布"
- 二者可以组合使用实现更强的高可用保证

| 对比 | PodAntiAffinity | Topology Spread |
|------|----------------|-----------------|
| 控制方式 | 禁止同域 | 控制偏差 |
| 精度 | 二元（同/不同） | maxSkew（允许偏差） |
| 性能 | 大集群开销大 | 相对高效 |
| 适用规模 | 中小集群 | 大集群推荐 |
""",
        key_fields=[
            {"name": "affinity.podAntiAffinity", "description": "Pod 反亲和性配置", "required": True, "example": "{requiredDuringSchedulingIgnoredDuringExecution: [...]}"},
            {"name": "requiredDuringSchedulingIgnoredDuringExecution", "description": "硬约束：必须满足", "required": False, "example": "[{labelSelector: {matchLabels: {app: web}}, topologyKey: kubernetes.io/hostname}]"},
            {"name": "preferredDuringSchedulingIgnoredDuringExecution", "description": "软约束：尽量满足，带 weight", "required": False, "example": "[{weight: 100, podAffinityTerm: {...}}]"},
            {"name": "topologyKey", "description": "拓扑域标签键", "required": True, "example": "kubernetes.io/hostname"},
        ],
        diagram="""\
  PodAntiAffinity: 跨节点硬约束

  ┌─────────── Deployment (ha-app, replicas: 3) ───────────┐
  │  affinity:                                             │
  │    podAntiAffinity:                                    │
  │      requiredDuringSchedulingIgnoredDuringExecution:   │
  │      - labelSelector:                                  │
  │          matchLabels: {app: ha-app}                    │
  │        topologyKey: kubernetes.io/hostname             │
  └──────────────────────────┬─────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
     ┌─────────┐       ┌─────────┐       ┌─────────┐
     │ node-a  │       │ node-b  │       │ node-c  │
     │ Pod-0   │       │ Pod-1   │       │ Pod-2   │
     │  ✅     │       │  ✅     │       │  ✅     │
     └─────────┘       └─────────┘       └─────────┘
     
     反亲和性: 每个 Pod 在不同节点 → 高可用 ✓
""",
        example_yaml="""\
apiVersion: apps/v1                                # Deployment API
kind: Deployment                                   # 资源类型
metadata:                                          # 元数据
  name: ha-app                                     # Deployment 名称
spec:                                              # 规格
  replicas: 3                                      # 3 个副本
  selector:                                        # 标签选择器
    matchLabels:
      app: ha-app
  template:                                        # Pod 模板
    metadata:
      labels:
        app: ha-app
    spec:                                          # Pod 规格
      containers:                                  # 容器列表
      - name: app                                  # 容器名
        image: nginx:1.25                          # 镜像
      affinity:                                    # 亲和性配置
        podAntiAffinity:                           # Pod 反亲和性
          requiredDuringSchedulingIgnoredDuringExecution:  # 硬约束
          - labelSelector:                         # 选择匹配的 Pod
              matchLabels:
                app: ha-app
            topologyKey: kubernetes.io/hostname    # 按节点反亲和
""",
        common_errors=[
            "topologyKey 缺失（反亲和性规则必须有 topologyKey）",
            "labelSelector 不匹配 Pod 自身的 labels（应匹配同一应用的 Pod）",
            "把 podAntiAffinity 写在了 nodeAffinity 下（它们是不同的字段）",
            "只用了硬约束但节点数不够（Pod 会一直 Pending）",
        ],
        tips=[
            "生产环境建议硬约束跨节点 + 软约束跨区域",
            "如果集群节点数少于 replicas，硬约束会导致 Pod Pending",
            "PodAntiAffinity 计算开销大，大集群建议用 Topology Spread 替代",
        ],
    ),
)


# ==================== Q26.3 Descheduler 概念 ====================

def _check_263_descheduler(user_yaml: str) -> CheckResult:
    """Q26.3 配置 Descheduler 策略"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写 Descheduler ConfigMap YAML"],
        )

    cm_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "ConfigMap":
            cm_doc = doc
            break

    if not cm_doc:
        return CheckResult(
            ok=False,
            error="没有找到 ConfigMap",
            hints=["Descheduler 配置通常以 ConfigMap 形式存在，kind: ConfigMap"],
        )

    metadata = cm_doc.get("metadata", {})
    if not isinstance(metadata, dict) or not metadata.get("name"):
        return CheckResult(ok=False, error="ConfigMap 缺少 metadata.name", hints=[])

    # 检查 data 中是否有策略配置
    data = cm_doc.get("data", {})
    if not isinstance(data, dict) or not data:
        return CheckResult(
            ok=False,
            error="ConfigMap 缺少 data（Descheduler 策略配置）",
            hints=["在 data 中添加 Descheduler 策略 YAML"],
        )

    # 查找策略内容
    policy_yaml = None
    for key, val in data.items():
        if isinstance(val, str) and ("strategies" in val or "policy" in val):
            policy_yaml = val
            break

    if not policy_yaml:
        return CheckResult(
            ok=False,
            error="ConfigMap data 中未找到 Descheduler 策略配置",
            hints=["策略 YAML 应包含 strategies 字段"],
        )

    # 解析策略 YAML
    try:
        policy = yaml.safe_load(policy_yaml)
    except yaml.YAMLError:
        return CheckResult(
            ok=False,
            error="策略 YAML 解析失败",
            hints=["确保 data 中的策略是有效的 YAML"],
        )

    if not isinstance(policy, dict):
        return CheckResult(ok=False, error="策略格式错误", hints=[])

    strategies = policy.get("strategies")
    if not isinstance(strategies, dict) or not strategies:
        return CheckResult(
            ok=False,
            error="策略缺少 strategies 字段",
            hints=["添加 strategies 字段配置重新调度策略"],
        )

    # 检查是否包含常见策略
    known_strategies = {
        "RemoveDuplicates", "LowNodeUtilization", "RemovePodsViolatingInterPodAntiAffinity",
        "RemovePodsViolatingNodeAffinity", "RemovePodsViolatingNodeTaints",
        "RemovePodsViolatingTopologySpreadConstraint", "PodLifeTime",
        "RemoveFailedPods", "TooManyRestarts",
    }
    found_strategies = set(strategies.keys())
    matched = found_strategies & known_strategies
    if not matched:
        return CheckResult(
            ok=False,
            error=f"strategies 中未找到有效的 Descheduler 策略，已知策略: {', '.join(sorted(known_strategies))}",
            hints=["使用如 RemoveDuplicates、LowNodeUtilization 等策略"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Descheduler 通过重新调度 Pod 优化集群资源分布 🔄"],
    )


LEVEL_Q26_3 = Level(
    id="Q26.3",
    chapter="ch26",
    title="Descheduler 概念 - 重新调度策略",
    description="""
# Descheduler 概念 - 重新调度策略 🔄

**Descheduler** 是 K8s 的调度优化工具，根据策略驱逐并重新调度 Pod，优化集群资源分布。

## 任务

创建一个 Descheduler 策略 ConfigMap：
- `kind: ConfigMap`，名称 `descheduler-policy`
- 在 data 中定义策略 YAML，包含至少 2 个策略：
  - `RemoveDuplicates`：移除重复 Pod（同一节点上多余的副本）
  - `LowNodeUtilization`：从负载低的节点迁移 Pod 到负载高的节点

## 提示

Descheduler 策略以 ConfigMap 形式配置：
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: descheduler-policy
data:
  policy.yaml: |
    apiVersion: descheduler/v1alpha1
    kind: DeschedulerPolicy
    strategies:
      RemoveDuplicates:
        enabled: true
      LowNodeUtilization:
        enabled: true
        params:
          nodeResourceUtilizationThresholds:
            lowThreshold: 20
            highThreshold: 50
```
""",
    starter_yaml="""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: descheduler-policy
data:
  policy.yaml: |
    # 在这里添加 Descheduler 策略
    apiVersion: descheduler/v1alpha1
    kind: DeschedulerPolicy
    strategies:
      # 添加 RemoveDuplicates 和 LowNodeUtilization 策略
""",
    check_fn=_check_263_descheduler,
    lesson=Lesson(
        concept="""\
## Descheduler

**Descheduler** 是一个 K8s 调度优化工具。K8s 调度器只在 Pod 创建时做一次调度决策，随着节点增减、Pod 变化，集群可能变得不均衡。Descheduler 定期根据策略**驱逐并重新调度** Pod 来优化分布。

### 为什么需要 Descheduler？

K8s 调度器是"一次性调度"——Pod 被调度到某节点后不会自动迁移。但以下情况会导致不均衡：
- 新节点加入集群后旧 Pod 不会迁移
- 节点资源使用率不均
- Pod 被驱逐后重新调度可能堆积

### 核心 Descheduler 策略

| 策略 | 功能 |
|------|------|
| RemoveDuplicates | 移除同节点上的重复 Pod 副本 |
| LowNodeUtilization | 从低负载节点迁移 Pod |
| RemovePodsViolatingInterPodAntiAffinity | 移除违反反亲和性的 Pod |
| RemovePodsViolatingNodeTaints | 移除违反节点污点的 Pod |
| RemovePodsViolatingTopologySpreadConstraint | 移除违反拓扑分布约束的 Pod |
| PodLifeTime | 移除超过存活时间的 Pod |
| TooManyRestarts | 移除重启次数过多的 Pod |

### 运行模式

- **Job/CronJob**：定期运行（如每小时一次）
- **Deployment**：持续运行模式
- 通常以 ClusterRole 授权，能驱逐所有命名空间的 Pod
""",
        key_fields=[
            {"name": "ConfigMap.data", "description": "策略 YAML 以字符串存储在 ConfigMap data 中", "required": True, "example": "policy.yaml: |"},
            {"name": "strategies", "description": "策略字典，每个策略设置 enabled 和 params", "required": True, "example": "{RemoveDuplicates: {enabled: true}}"},
            {"name": "RemoveDuplicates", "description": "移除同节点重复 Pod", "required": False, "example": "{enabled: true}"},
            {"name": "LowNodeUtilization", "description": "低负载节点迁移 Pod", "required": False, "example": "{enabled: true, params: {nodeResourceUtilizationThresholds: {lowThreshold: 20}}}"},
        ],
        diagram="""\
  Descheduler 工作流程

  ┌──────────────────────────────────────────────────┐
  │              Descheduler (CronJob)               │
  │  1. 读取 ConfigMap 中的策略                        │
  │  2. 扫描集群 Pod 分布                              │
  │  3. 根据策略识别需要驱逐的 Pod                       │
  │  4. 驱逐 Pod (eviction API)                       │
  └──────────────────────┬───────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     ┌─────────┐   ┌─────────┐   ┌─────────┐
     │ node-a  │   │ node-b  │   │ node-c  │
     │ 5 Pods  │   │ 1 Pod   │   │ 0 Pod   │
     │ 过载     │   │ 低负载   │   │ 空闲     │
     └────┬────┘   └────┬────┘   └─────────┘
          │ 驱逐         │ 迁移
          ▼              ▼
     ┌─────────┐   ┌─────────┐   ┌─────────┐
     │ node-a  │   │ node-b  │   │ node-c  │
     │ 3 Pods  │   │ 2 Pods  │   │ 2 Pods  │
     │ 均衡 ✓  │   │ 均衡 ✓  │   │ 均衡 ✓  │
     └─────────┘   └─────────┘   └─────────┘
""",
        example_yaml="""\
apiVersion: v1                            # ConfigMap API
kind: ConfigMap                           # 资源类型
metadata:                                 # 元数据
  name: descheduler-policy                # ConfigMap 名称
data:                                     # 数据
  policy.yaml: |                          # 策略文件
    apiVersion: descheduler/v1alpha1      # Descheduler API
    kind: DeschedulerPolicy               # 策略类型
    strategies:                           # 策略列表
      RemoveDuplicates:                   # 移除重复 Pod
        enabled: true                     # 启用
      LowNodeUtilization:                 # 低负载迁移
        enabled: true                     # 启用
        params:                           # 策略参数
          nodeResourceUtilizationThresholds:
            lowThreshold: 20              # 低负载阈值 20%
            highThreshold: 50             # 高负载阈值 50%
""",
        common_errors=[
            "策略名称拼写错误（如 RemoveDuplicate 少了 s）",
            "策略 YAML 没有放在 ConfigMap 的 data 中",
            "忘记 enabled: true 导致策略默认不启用",
            "LowNodeUtilization 缺少 thresholds 参数",
        ],
        tips=[
            "Descheduler 驱逐 Pod 时会遵守 PDB（PodDisruptionBudget）",
            "生产环境建议先以 dry-run 模式测试策略效果",
            "Descheduler 不会驱逐 DaemonSet、静态 Pod 和受 PDB 保护的 Pod",
        ],
    ),
)


# ==================== Q26.4 调度器配置 ====================

def _check_264_scheduler_config(user_yaml: str) -> CheckResult:
    """Q26.4 配置 K8s 调度器策略"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写调度器配置 YAML"],
        )

    config_doc = None
    for doc in docs:
        if isinstance(doc, dict):
            kind = doc.get("kind", "")
            api_version = doc.get("apiVersion", "")
            if kind == "KubeSchedulerConfiguration" or "scheduling" in str(api_version):
                config_doc = doc
                break

    if not config_doc:
        return CheckResult(
            ok=False,
            error="没有找到 KubeSchedulerConfiguration",
            hints=["创建 kind: KubeSchedulerConfiguration 的 YAML，apiVersion: kubescheduler.config.k8s.io/v1"],
        )

    # 检查 apiVersion
    api_version = config_doc.get("apiVersion", "")
    if "kubescheduler" not in api_version:
        return CheckResult(
            ok=False,
            error=f"apiVersion 应为 kubescheduler.config.k8s.io/v1，实际为 '{api_version}'",
            hints=["KubeSchedulerConfiguration 的 apiVersion 是 kubescheduler.config.k8s.io/v1"],
        )

    # 检查 profiles
    profiles = config_doc.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        return CheckResult(
            ok=False,
            error="缺少 profiles（调度器配置需要至少一个 profile）",
            hints=["添加 profiles 列表配置调度器插件"],
        )

    profile = profiles[0]
    if not isinstance(profile, dict):
        return CheckResult(ok=False, error="profiles[0] 格式错误", hints=[])

    # 检查 schedulerName
    scheduler_name = profile.get("schedulerName")
    if not scheduler_name:
        return CheckResult(
            ok=False,
            error="profiles[0] 缺少 schedulerName",
            hints=["设置 schedulerName 如 'my-scheduler'"],
        )

    # 检查 pluginConfig 或 plugins
    plugins = profile.get("plugins")
    plugin_config = profile.get("pluginConfig")

    if not plugins and not plugin_config:
        return CheckResult(
            ok=False,
            error="profiles[0] 缺少 plugins 或 pluginConfig",
            hints=["添加 plugins 配置启用/禁用调度插件，或 pluginConfig 配置插件参数"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["自定义调度器配置让你精确控制调度决策 ⚙️"],
    )


LEVEL_Q26_4 = Level(
    id="Q26.4",
    chapter="ch26",
    title="调度器配置 - 调度器策略配置",
    description="""
# 调度器配置 - 调度器策略配置 ⚙️

**KubeSchedulerConfiguration** 允许你自定义调度器行为，通过配置插件来调整调度决策流程。

## 任务

创建一个 KubeSchedulerConfiguration：
- `kind: KubeSchedulerConfiguration`
- `apiVersion: kubescheduler.config.k8s.io/v1`
- profiles:
  - schedulerName: my-scheduler
  - plugins 启用/禁用某些调度插件

## 提示

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: my-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesFit
        weight: 10
      disabled:
      - name: NodeResourcesLeastAllocated
```
""",
    starter_yaml="""\
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
# 添加 schedulerName 和 plugins 配置
""",
    check_fn=_check_264_scheduler_config,
    lesson=Lesson(
        concept="""\
## KubeSchedulerConfiguration

**KubeSchedulerConfiguration** 是 K8s 调度器的配置文件，允许自定义调度器行为。从 K8s 1.19 起，调度器使用**调度框架（Scheduling Framework）**架构，通过插件扩展调度流程。

### 调度框架阶段

调度过程分为多个阶段，每个阶段可以配置插件：

```
QueueSort → Filter → Score → NormalizeScore → Reserve → Permit → PreBind → Bind
```

### 核心调度插件

| 阶段 | 插件 | 功能 |
|------|------|------|
| Filter | NodeUnschedulable | 过滤不可调度节点 |
| Filter | TaintToleration | 污点容忍过滤 |
| Filter | NodeAffinity | 节点亲和性 |
| Score | NodeResourcesFit | 资源适配评分 |
| Score | InterPodAffinity | Pod 亲和性评分 |
| Score | ImageLocality | 镜像本地化评分 |
| Bind | DefaultBinder | 默认绑定 |

### 多调度器

通过不同 schedulerName 运行多个调度器实例：
- default-scheduler：默认调度器
- my-scheduler：自定义调度器
- Pod 通过 `spec.schedulerName` 选择使用哪个调度器
""",
        key_fields=[
            {"name": "apiVersion", "description": "kubescheduler.config.k8s.io/v1", "required": True, "example": "kubescheduler.config.k8s.io/v1"},
            {"name": "profiles[].schedulerName", "description": "调度器名称，Pod 通过此名称选择调度器", "required": True, "example": "my-scheduler"},
            {"name": "profiles[].plugins", "description": "插件配置，按阶段启用/禁用", "required": True, "example": "{score: {enabled: [{name: NodeResourcesFit, weight: 10}]}}"},
            {"name": "profiles[].pluginConfig", "description": "插件参数配置", "required": False, "example": "[{name: NodeResourcesFit, args: {scoringStrategy: {type: LeastAllocated}}}]"},
        ],
        diagram="""\
  KubeSchedulerConfiguration 架构

  ┌──────── KubeSchedulerConfiguration ──────────┐
  │  profiles:                                   │
  │  - schedulerName: my-scheduler               │
  │    plugins:                                  │
  │      filter:                                 │
  │        enabled:  [NodeUnschedulable, ...]    │
  │      score:                                  │
  │        enabled:  [NodeResourcesFit, ...]     │
  │        disabled: [NodeResourcesLeastAllocated]│
  └──────────────────┬──────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────────┐
  │           调度框架流水线                       │
  │                                              │
  │  QueueSort → Filter → Score → Bind           │
  │     │          │        │       │            │
  │     ▼          ▼        ▼       ▼            │
  │  排序插件    过滤插件   评分插件  绑定插件      │
  └──────────────────────────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────────┐
  │  Pod spec.schedulerName: my-scheduler        │
  │  → 使用自定义调度器                           │
  └──────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: kubescheduler.config.k8s.io/v1   # 调度器配置 API
kind: KubeSchedulerConfiguration            # 资源类型
profiles:                                    # 调度器 profile 列表
- schedulerName: my-scheduler               # 调度器名称
  plugins:                                   # 插件配置
    score:                                   # 评分阶段
      enabled:                               # 启用的插件
      - name: NodeResourcesFit               # 资源适配评分
        weight: 10                           # 权重
      disabled:                              # 禁用的插件
      - name: NodeResourcesLeastAllocated    # 禁用最少分配策略
""",
        common_errors=[
            "apiVersion 写错（应为 kubescheduler.config.k8s.io/v1）",
            "忘记 schedulerName（Pod 需要通过此名称选择调度器）",
            "plugins 中引用了不存在的插件名称",
            "weight 设为 0（权重应大于 0）",
        ],
        tips=[
            "自定义调度器需要在 kube-scheduler 启动参数中指定 --config",
            "多调度器场景下，未指定 schedulerName 的 Pod 使用 default-scheduler",
            "调度框架允许开发自定义插件，实现特殊调度需求",
        ],
    ),
)


# ==================== Q26.5 集群实战 - 高可用工作负载调度 ====================

def _check_265_ha_scheduling(user_yaml: str) -> CheckResult:
    """Q26.5 创建高可用工作负载调度配置"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写多文档 YAML"],
        )

    deploy_doc = None
    pdb_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Deployment" and deploy_doc is None:
            deploy_doc = doc
        elif kind == "PodDisruptionBudget" and pdb_doc is None:
            pdb_doc = doc

    if not deploy_doc:
        return CheckResult(
            ok=False,
            error="缺少 Deployment",
            hints=["创建一个 Deployment 来运行高可用工作负载"],
        )

    spec = deploy_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    # 检查 replicas >= 3
    replicas = spec.get("replicas", 1)
    if not isinstance(replicas, int) or replicas < 3:
        return CheckResult(
            ok=False,
            error=f"高可用部署 replicas 应 >= 3，实际为 {replicas}",
            hints=["设置 replicas: 3 或更多确保跨节点高可用"],
        )

    template = spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    pod_spec = template.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    # 检查 topologySpreadConstraints 或 podAntiAffinity
    has_tsc = isinstance(pod_spec.get("topologySpreadConstraints"), list)
    has_anti_affinity = isinstance(pod_spec.get("affinity", {}), dict) and isinstance(
        pod_spec.get("affinity", {}).get("podAntiAffinity"), dict
    )

    if not has_tsc and not has_anti_affinity:
        return CheckResult(
            ok=False,
            error="缺少 topologySpreadConstraints 或 podAntiAffinity（高可用需要跨节点分布）",
            hints=["添加 topologySpreadConstraints 或 affinity.podAntiAffinity 确保跨节点分布"],
        )

    # 检查 PDB
    if not pdb_doc:
        return CheckResult(
            ok=False,
            error="缺少 PodDisruptionBudget（高可用部署需要 PDB 保护）",
            hints=["添加 PodDisruptionBudget 防止自愿中断导致服务不可用"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["高可用调度 = 多副本 + 跨节点分布 + PDB 保护 = 99.99% 可用性 🏆"],
    )


LEVEL_Q26_5 = Level(
    id="Q26.5",
    chapter="ch26",
    title="集群实战 - 高可用工作负载调度",
    description="""
# 集群实战 - 高可用工作负载调度 🏆

综合运用 Topology Spread、PodAntiAffinity 和 PDB 构建生产级高可用部署。

## 任务

创建一个完整的高可用工作负载配置（多文档 YAML）：
1. **Deployment**（名称 `ha-webapp`，replicas: 3）
   - 容器 `app`，镜像 `nginx:1.25`
   - topologySpreadConstraints: maxSkew=1, topologyKey=kubernetes.io/hostname, whenUnsatisfiable=DoNotSchedule
2. **PodDisruptionBudget**（名称 `ha-webapp-pdb`）
   - minAvailable: 2
   - selector 匹配 app: ha-webapp

## 提示

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-webapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ha-webapp
  template:
    metadata:
      labels:
        app: ha-webapp
    spec:
      containers:
      - name: app
        image: nginx:1.25
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: ha-webapp
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ha-webapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: ha-webapp
```
""",
    starter_yaml="""\
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-webapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ha-webapp
  template:
    metadata:
      labels:
        app: ha-webapp
    spec:
      containers:
      - name: app
        image: nginx:1.25
      # 添加 topologySpreadConstraints
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ha-webapp-pdb
spec:
  # 添加 minAvailable 和 selector
""",
    check_fn=_check_265_ha_scheduling,
    lesson=Lesson(
        concept="""\
## 生产级高可用调度

生产环境的高可用部署需要多层保障：

### 高可用调度三要素

1. **多副本**（replicas >= 3）：确保单 Pod 故障不影响服务
2. **跨节点分布**（Topology Spread / PodAntiAffinity）：防止单节点故障导致全部 Pod 丢失
3. **中断保护**（PDB）：防止自愿中断（如维护）导致服务不可用

### 完整高可用策略

```
层级 1: replicas >= 3          -> Pod 级容错
层级 2: Topology Spread         -> 节点级容灾
层级 3: PodAntiAffinity (zone)  -> 可用区级容灾
层级 4: PDB (minAvailable: 2)   -> 维护期保护
层级 5: Health Check (liveness) -> 自动恢复
层级 6: Rolling Update          -> 零停机更新
```

### Taint/Toleration 与节点维护

Taint（污点）让节点排斥 Pod，Toleration（容忍）让 Pod 可以被调度到有污点的节点。这在节点维护场景中至关重要：

**节点维护流程**：

```bash
# 1. 标记节点不可调度（防止新 Pod 调度上来）
kubectl cordon node-3

# 2. 驱逐节点上的 Pod（触发滚动更新）
kubectl drain node-3 --ignore-daemonsets --delete-emptydir-data

# 3. 执行维护操作（升级内核、更换硬件等）
# ...

# 4. 维护完成后恢复节点
kubectl uncordon node-3
```

`kubectl drain` 会自动给节点添加 `node.kubernetes.io/unschedulable:NoSchedule` 污点，并驱逐 Pod。PDB 会阻止驱逐导致服务不可用。

**Toleration 配置示例**：

```yaml
spec:
  tolerations:
  - key: "node.kubernetes.io/unschedulable"
    operator: "Exists"
    effect: "NoSchedule"
  # 关键服务可以容忍 NotReady 节点
  - key: "node.kubernetes.io/not-ready"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 300    # 节点 NotReady 后最多等 5 分钟
```

**常见 Taint 类型**：

| Taint | 效果 | 说明 |
|-------|------|------|
| `node.kubernetes.io/not-ready` | NoExecute | 节点未就绪 |
| `node.kubernetes.io/unreachable` | NoExecute | 节点不可达 |
| `node.kubernetes.io/unschedulable` | NoSchedule | 节点不可调度 |
| `node.kubernetes.io/disk-pressure` | NoSchedule | 磁盘压力 |
| `node.kubernetes.io/memory-pressure` | NoSchedule | 内存压力 |
| `dedicated=gpu:NoSchedule` | NoSchedule | 专用 GPU 节点 |

**Taint vs Node Affinity**：Taint 是"节点排斥 Pod"（推），Node Affinity 是"Pod 选择节点"（拉）。生产环境通常两者配合使用：Taint 保证专用节点只跑特定 Pod，Node Affinity 保证特定 Pod 只跑在专用节点上。

### 生产配置清单

- ✅ replicas >= 3
- ✅ topologySpreadConstraints (跨节点)
- ✅ podAntiAffinity (跨可用区, 软约束)
- ✅ PodDisruptionBudget (minAvailable: 2)
- ✅ Taint/Toleration (专用节点隔离)
- ✅ resources.requests/limits
- ✅ livenessProbe + readinessProbe
- ✅ rollingUpdate 策略
""",
        key_fields=[
            {"name": "spec.replicas", "description": "高可用至少 3 副本", "required": True, "example": "3"},
            {"name": "topologySpreadConstraints", "description": "拓扑分布约束，确保跨节点", "required": True, "example": "maxSkew: 1, topologyKey: kubernetes.io/hostname"},
            {"name": "PodDisruptionBudget", "description": "中断预算，保护自愿中断", "required": True, "example": "minAvailable: 2"},
        ],
        diagram="""\
  生产级高可用调度架构

  ┌─── Deployment (ha-webapp, replicas: 3) ────┐
  │  topologySpreadConstraints:                │
  │    maxSkew: 1                              │
  │    topologyKey: kubernetes.io/hostname     │
  └──────────────────┬────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
 ┌─────────┐   ┌─────────┐   ┌─────────┐
 │ node-a  │   │ node-b  │   │ node-c  │
 │ Pod-0   │   │ Pod-1   │   │ Pod-2   │
 │  ✅     │   │  ✅     │   │  ✅     │
 └─────────┘   └─────────┘   └─────────┘

  ┌─── PDB (ha-webapp-pdb) ───────────────────┐
  │  minAvailable: 2                          │
  │  selector: {app: ha-webapp}               │
  │  → 维护时至少保留 2 个 Pod 运行            │
  └───────────────────────────────────────────┘

  结果: 99.99% 可用性 🏆
""",
        example_yaml="""\
---                                          # 多文档分隔
apiVersion: apps/v1                          # Deployment API
kind: Deployment                             # 资源类型
metadata:                                    # 元数据
  name: ha-webapp                            # Deployment 名称
spec:                                        # 规格
  replicas: 3                                # 3 副本高可用
  selector:                                  # 标签选择器
    matchLabels:
      app: ha-webapp
  template:                                  # Pod 模板
    metadata:
      labels:
        app: ha-webapp
    spec:                                    # Pod 规格
      containers:                            # 容器列表
      - name: app                            # 容器名
        image: nginx:1.25                    # 镜像
      topologySpreadConstraints:             # 拓扑分布约束
      - maxSkew: 1                           # 最大偏差 1
        topologyKey: kubernetes.io/hostname  # 按节点分布
        whenUnsatisfiable: DoNotSchedule     # 硬约束
        labelSelector:                       # 选择 Pod
          matchLabels:
            app: ha-webapp
---                                          # 多文档分隔
apiVersion: policy/v1                        # PDB API
kind: PodDisruptionBudget                    # 资源类型
metadata:                                    # 元数据
  name: ha-webapp-pdb                        # PDB 名称
spec:                                        # 规格
  minAvailable: 2                            # 最少保留 2 个
  selector:                                  # 标签选择器
    matchLabels:
      app: ha-webapp
""",
        common_errors=[
            "replicas 设为 1（单点故障，无法高可用）",
            "有 Topology Spread 但没有 PDB（维护时可能全部中断）",
            "PDB 的 selector 不匹配 Deployment 的 labels",
            "minAvailable 设为 replicas（等于完全禁止驱逐，维护无法进行）",
        ],
        tips=[
            "生产环境推荐: replicas >= 3 + 跨节点分布 + PDB minAvailable >= 2",
            "Topology Spread 和 PodAntiAffinity 可以组合使用",
            "PDB 只保护自愿中断（如 drain），不保护非自愿中断（如节点故障）",
        ],
    ),
)


# ==================== 章节导出 ====================

CHAPTER_26_LEVELS = [
    LEVEL_Q26_1,
    LEVEL_Q26_2,
    LEVEL_Q26_3,
    LEVEL_Q26_4,
    LEVEL_Q26_5,
]
