"""Chapter 6: Scheduling 调度（4 关）

Q6.1 nodeSelector 节点选择
Q6.2 nodeAffinity 节点亲和性
Q6.3 Taints & Tolerations 污点与容忍
Q6.4 资源限制与调度
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


def _check_01_node_selector(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-ssd
  labels:
    disktype: ssd
    cpu: x86
---
apiVersion: v1
kind: Node
metadata:
  name: node-hdd
  labels:
    disktype: hdd
    cpu: x86
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，使用 nodeSelector 调度到 SSD 节点"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    selector = spec.get("nodeSelector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(ok=False, error="Pod 缺少 nodeSelector", hints=["添加 nodeSelector: { disktype: ssd }"])

    if selector.get("disktype") != "ssd":
        return CheckResult(ok=False, error=f"nodeSelector.disktype 应为 'ssd'，实际 '{selector.get('disktype')}'", hints=[])

    return CheckResult(ok=True, state=state, hints=["nodeSelector 调度成功！Pod 被调度到有 disktype=ssd 标签的节点"])


def _check_02_node_affinity(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: gpu-node
  labels:
    gpu: "true"
    zone: us-east-1a
---
apiVersion: v1
kind: Node
metadata:
  name: cpu-node
  labels:
    gpu: "false"
    zone: us-east-1b
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，使用 nodeAffinity 调度到 GPU 节点"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    affinity = spec.get("affinity")
    if not isinstance(affinity, dict):
        return CheckResult(ok=False, error="Pod 缺少 affinity", hints=["添加 affinity.nodeAffinity"])

    node_affinity = affinity.get("nodeAffinity")
    if not isinstance(node_affinity, dict):
        return CheckResult(ok=False, error="缺少 affinity.nodeAffinity", hints=[])

    required = node_affinity.get("requiredDuringSchedulingIgnoredDuringExecution")
    if not isinstance(required, dict):
        return CheckResult(ok=False, error="缺少 requiredDuringSchedulingIgnoredDuringExecution", hints=[])

    terms = required.get("nodeSelectorTerms")
    if not isinstance(terms, list) or not terms:
        return CheckResult(ok=False, error="缺少 nodeSelectorTerms", hints=[])

    # 检查是否有匹配 gpu=true 的 matchExpressions
    found_gpu = False
    for term in terms:
        if not isinstance(term, dict):
            continue
        exprs = term.get("matchExpressions", [])
        if isinstance(exprs, list):
            for expr in exprs:
                if isinstance(expr, dict) and expr.get("key") == "gpu":
                    found_gpu = True
                    break

    if not found_gpu:
        return CheckResult(ok=False, error="nodeAffinity 中没有匹配 'gpu' 标签的表达式", hints=["使用 matchExpressions 匹配 gpu: true"])

    return CheckResult(ok=True, state=state, hints=["nodeAffinity 调度成功！比 nodeSelector 更灵活的调度方式"])


def _check_03_taints_tolerations(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，添加 toleration 容忍节点的污点"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    tolerations = spec.get("tolerations")
    if not isinstance(tolerations, list) or not tolerations:
        return CheckResult(ok=False, error="Pod 缺少 tolerations", hints=["添加 tolerations 来容忍节点污点"])

    found_toleration = False
    for t in tolerations:
        if isinstance(t, dict):
            key = t.get("key", "")
            operator = t.get("operator", "Equal")
            effect = t.get("effect", "")
            if key == "dedicated" or (operator == "Exists" and effect in ["NoSchedule", "NoExecute"]):
                found_toleration = True
                break

    if not found_toleration:
        return CheckResult(ok=False, error="没有找到有效的 toleration", hints=["toleration 需要匹配节点的 taint (key/effect)"])

    return CheckResult(ok=True, state=state, hints=["Toleration 配置成功！让 Pod 可以被调度到有污点的节点"])


def _check_04_resource_limits(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，设置 resources requests 和 limits"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    resources = c.get("resources")
    if not isinstance(resources, dict):
        return CheckResult(ok=False, error="容器缺少 resources", hints=["添加 resources.requests 和 resources.limits"])

    requests = resources.get("requests")
    if not isinstance(requests, dict) or not requests:
        return CheckResult(ok=False, error="缺少 resources.requests", hints=["requests 用于调度决策"])

    if "cpu" not in requests:
        return CheckResult(ok=False, error="requests 中缺少 cpu", hints=["添加 cpu request，如 cpu: 100m"])

    if "memory" not in requests:
        return CheckResult(ok=False, error="requests 中缺少 memory", hints=["添加 memory request，如 memory: 128Mi"])

    limits = resources.get("limits")
    if not isinstance(limits, dict) or not limits:
        return CheckResult(ok=False, error="缺少 resources.limits", hints=["limits 用于限制容器最大资源使用"])

    if "cpu" not in limits:
        return CheckResult(ok=False, error="limits 中缺少 cpu", hints=["添加 cpu limit"])

    if "memory" not in limits:
        return CheckResult(ok=False, error="limits 中缺少 memory", hints=["添加 memory limit"])

    return CheckResult(ok=True, state=state, hints=["资源限制配置成功！requests 调度用，limits 限流用"])


CHAPTER_6_LEVELS: list[Level] = [
    Level(id="Q6.1", chapter="ch06", title="nodeSelector 节点选择",
          description="集群有 node-ssd(disktype=ssd) 和 node-hdd(disktype=hdd) 两个节点。创建 Pod，用 nodeSelector 调度到 SSD 节点",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n    - name: nginx\n      image: nginx\n  # nodeSelector",
          check_fn=_check_01_node_selector,
          lesson=Lesson(
              concept="""\
## nodeSelector 节点选择

**nodeSelector** 是 K8s 中最简单的 Pod 调度约束方式。通过指定键值对，要求 Pod 只能被调度到拥有匹配标签的 Node 上。

### 工作原理

```
Pod spec.nodeSelector: {disktype: ssd}
  → kube-scheduler 过滤所有 Node
  → 只保留 labels 中有 disktype=ssd 的 Node
  → 在候选 Node 中选择资源最充足的
```

如果没有任何 Node 的标签匹配 nodeSelector，Pod 会一直处于 **Pending** 状态。

### nodeSelector vs nodeAffinity

| 特性 | nodeSelector | nodeAffinity |
|------|-------------|--------------|
| 复杂度 | 简单键值对 | 支持多种操作符 |
| 灵活性 | 必须完全匹配 | 支持 In/NotIn/Exists 等 |
| 软约束 | 不支持 | 支持 preferred（尽量满足） |
| 场景 | 简单调度 | 复杂调度需求 |

### Node 标签

K8s 自动为 Node 打一些内置标签：
- `kubernetes.io/hostname`：Node 主机名
- `kubernetes.io/os`：操作系统
- `kubernetes.io/arch`：CPU 架构
- `topology.kubernetes.io/zone`：可用区

也可以用 `kubectl label node <name> key=value` 手动打标签。

### 使用场景

- GPU 任务调度到 GPU 节点
- SSD 存储需求调度到 SSD 节点
- 特定架构（arm/amd64）调度到对应节点
""",
              key_fields=[
                  {"name": "spec.nodeSelector", "description": "节点标签选择器，键值对必须完全匹配", "required": True, "example": "{disktype: ssd}"},
                  {"name": "Node metadata.labels", "description": "Node 上的标签，nodeSelector 匹配此字段", "required": True, "example": "{disktype: ssd, cpu: x86}"},
              ],
              diagram="""\
  nodeSelector 调度过程

  ┌──── Pod (nginx-pod) ────────┐
  │  spec:                      │
  │    nodeSelector:            │
  │      disktype: ssd   ◄── 要求 Node 有此标签
  │    containers:              │
  │    - name: nginx            │
  └──────────┬──────────────────┘
             │
             ▼  kube-scheduler 过滤 Node

  ┌── Node: node-ssd ────┐   ┌── Node: node-hdd ────┐
  │  labels:              │   │  labels:              │
  │    disktype: ssd  ✓  │   │    disktype: hdd  ✗  │
  │    cpu: x86           │   │    cpu: x86           │
  │  状态: 可调度         │   │  状态: 不匹配         │
  └───────────────────────┘   └───────────────────────┘
             │
             ▼
  Pod 被调度到 node-ssd
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: nginx-pod               # Pod 名称
spec:                           # 规格定义
  nodeSelector:                 # 节点选择器
    disktype: ssd               # 只调度到 disktype=ssd 的节点
  containers:                   # 容器列表
  - name: nginx                 # 容器名
    image: nginx                # 镜像
""",
              common_errors=[
                  "nodeSelector 的标签值与 Node 标签不匹配（Pod 一直 Pending）",
                  "把 nodeSelector 写成了 matchLabels（那是 Deployment selector 的语法）",
                  "nodeSelector 写在了 spec.containers 下（应在 spec 下）",
                  "忘记先给 Node 打标签（用 kubectl label node 打标签）",
              ],
              tips=[
                  "nodeSelector 是最简单的调度约束，复杂需求用 nodeAffinity",
                  "用 kubectl get nodes --show-labels 查看所有节点标签",
                  "用 kubectl label node <name> disktype=ssd 手动打标签",
              ],
          ),
    ),
    Level(id="Q6.2", chapter="ch06", title="nodeAffinity 节点亲和性",
          description="集群有 gpu-node(gpu=true) 和 cpu-node(gpu=false)。创建 Pod，用 nodeAffinity 的 required 规则调度到 GPU 节点",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: ml-pod\nspec:\n  containers:\n    - name: app\n      image: tensorflow:latest\n  # affinity.nodeAffinity",
          check_fn=_check_02_node_affinity,
          lesson=Lesson(
              concept="""\
## nodeAffinity 节点亲和性

**nodeAffinity** 是比 nodeSelector 更强大的调度约束，支持多种匹配操作符和软约束（preferred），是生产环境推荐的调度方式。

### 两种亲和性

1. **requiredDuringSchedulingIgnoredDuringExecution**（硬约束）
   - 必须满足，否则 Pod 一直 Pending
   - 类似 nodeSelector 但更灵活

2. **preferredDuringSchedulingIgnoredDuringExecution**（软约束）
   - 尽量满足，不满足也能调度
   - 按权重排序，优先调度到高分节点
   - 适合"最好调度到 GPU 节点，没有也行"的场景

### matchExpressions 操作符

| 操作符 | 含义 | 示例 |
|--------|------|------|
| In | 值在列表中 | gpu In [true] |
| NotIn | 值不在列表中 | disktype NotIn [hdd] |
| Exists | 标签存在 | gpu Exists |
| DoesNotExist | 标签不存在 | gpu DoesNotExist |
| Gt | 大于（数值） | cpu Gt 4 |
| Lt | 小于（数值） | cpu Lt 16 |

### nodeAffinity vs nodeSelector

- nodeSelector 只能精确匹配键值对
- nodeAffinity 支持 In/NotIn/Exists 等操作符
- nodeAffinity 支持 preferred（软约束）
- nodeAffinity 支持多个 nodeSelectorTerms（OR 关系）

### IgnoredDuringExecution 的含义

调度时生效，运行时忽略--如果 Node 标签变了，已运行的 Pod 不会被驱逐（required 模式下）。
""",
              key_fields=[
                  {"name": "spec.affinity.nodeAffinity", "description": "节点亲和性配置", "required": True, "example": "nodeAffinity config"},
                  {"name": "requiredDuringSchedulingIgnoredDuringExecution", "description": "硬约束：必须满足的调度条件", "required": True, "example": "nodeSelectorTerms config"},
                  {"name": "preferredDuringSchedulingIgnoredDuringExecution", "description": "软约束：尽量满足的调度条件", "required": False, "example": "preferred terms with weight"},
                  {"name": "matchExpressions[].operator", "description": "匹配操作符: In/NotIn/Exists/DoesNotExist/Gt/Lt", "required": True, "example": "In"},
              ],
              diagram="""\
  nodeAffinity 调度过程 (硬约束)

  ┌──── Pod (ml-pod) ──────────────────────────────┐
  │  spec:                                         │
  │    affinity:                                   │
  │      nodeAffinity:                             │
  │        requiredDuringSchedulingIgnoredDuringExecution:│
  │          nodeSelectorTerms:                    │
  │          - matchExpressions:                   │
  │            - key: gpu                          │
  │              operator: In                      │
  │              values: ["true"]                  │
  └──────────┬─────────────────────────────────────┘
             │
             ▼  kube-scheduler 过滤

  ┌── Node: gpu-node ──────┐   ┌── Node: cpu-node ──────┐
  │  labels:                │   │  labels:                │
  │    gpu: "true"    ✓    │   │    gpu: "false"   ✗    │
  │    zone: us-east-1a    │   │    zone: us-east-1b    │
  │  状态: 可调度           │   │  状态: 不匹配           │
  └─────────────────────────┘   └─────────────────────────┘
             │
             ▼
  Pod 被调度到 gpu-node
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: ml-pod                  # Pod 名称
spec:                           # 规格定义
  affinity:                     # 亲和性配置
    nodeAffinity:               # 节点亲和性
      requiredDuringSchedulingIgnoredDuringExecution:  # 硬约束
        nodeSelectorTerms:      # 选择器条件
        - matchExpressions:     # 匹配表达式
          - key: gpu            # 标签 key
            operator: In        # 操作符: 值在列表中
            values:             # 匹配值列表
            - "true"            # gpu=true 的节点
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: tensorflow:latest    # 镜像
""",
              common_errors=[
                  "字段名太长写错（requiredDuringSchedulingIgnoredDuringExecution）",
                  "operator 用了 = 而非 In（nodeAffinity 用 In/NotIn/Exists 等）",
                  "values 写成了字符串而非列表（应为 ['true'] 不是 'true'）",
                  "把 nodeAffinity 写在了 spec 下而非 spec.affinity 下",
              ],
              tips=[
                  "nodeAffinity 比 nodeSelector 更灵活，生产环境推荐使用",
                  "preferred 软约束适合'最好满足但不强制'的场景",
                  "多个 nodeSelectorTerms 是 OR 关系，同一 term 内的 expressions 是 AND 关系",
              ],
          ),
    ),
    Level(id="Q6.3", chapter="ch06", title="Taints & Tolerations",
          description="创建一个 Pod，配置 toleration 容忍节点的 dedicated 污点",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: special-pod\nspec:\n  containers:\n    - name: app\n      image: nginx\n  # tolerations",
          check_fn=_check_03_taints_tolerations,
          lesson=Lesson(
              concept="""\
## Taints & Tolerations（污点与容忍）

**Taint（污点）** 标记 Node 不接受普通 Pod 调度。**Toleration（容忍）** 让 Pod 可以无视 Taint 被调度到该 Node。两者配合实现**精细化调度隔离**。

### Taint 和 Toleration 的关系

```
Node 打 Taint: dedicated=special:NoSchedule
  → 普通 Pod 不会被调度到此 Node
  → Pod 配置 Toleration 容忍此 Taint
  → Pod 可以被调度到此 Node
```

Taint 是 Node 的属性，Toleration 是 Pod 的属性。它们是**互补**的--Taint 排斥，Toleration 包容。

### Taint 的三个 Effect

| Effect | 含义 | 行为 |
|--------|------|------|
| **NoSchedule** | 不调度 | 新 Pod 不会被调度到该 Node，已有 Pod 不受影响 |
| **PreferNoSchedule** | 尽量不调度 | 尽量避免调度，但不是强制（类似 preferred） |
| **NoExecute** | 驱逐 | 新 Pod 不调度，已有 Pod 不容忍则被驱逐 |

### Toleration 配置

```yaml
tolerations:
- key: "dedicated"
  operator: "Equal"       # 或 "Exists"
  value: "special"
  effect: "NoSchedule"
```

- `Equal`：key 和 value 必须完全匹配
- `Exists`：只检查 key 是否存在（不比较 value）
- 省略 operator 默认为 Equal

### 典型场景

1. **专用节点**：GPU 节点打 Taint，只有 ML Pod 有 Toleration
2. **维护模式**：Node 打 NoExecute Taint，驱逐所有 Pod
3. **控制平面隔离**：Master 节点默认有 Taint，普通 Pod 不调度

### tolerationSeconds

配合 NoExecute 使用：Pod 在 Taint 添加后还能运行 N 秒才被驱逐，给应用优雅退出的时间。
""",
              key_fields=[
                  {"name": "spec.tolerations", "description": "容忍列表，让 Pod 可以调度到有 Taint 的 Node", "required": True, "example": "[{key: dedicated, operator: Equal, value: special, effect: NoSchedule}]"},
                  {"name": "tolerations[].key", "description": "匹配的 Taint key", "required": True, "example": "dedicated"},
                  {"name": "tolerations[].operator", "description": "匹配方式: Equal(精确匹配) 或 Exists(key 存在即可)", "required": False, "example": "Equal"},
                  {"name": "tolerations[].effect", "description": "Taint 效果: NoSchedule/PreferNoSchedule/NoExecute", "required": True, "example": "NoSchedule"},
              ],
              diagram="""\
  Taints & Tolerations 机制

  ┌── Node (dedicated-node) ───────────┐
  │  Taints:                            │
  │    key: dedicated                   │
  │    value: special                   │
  │    effect: NoSchedule  ◄── 排斥普通 Pod
  └────────────┬────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
  普通 Pod (无 Toleration)   特殊 Pod (有 Toleration)
  ┌──────────────┐          ┌──────────────────────────┐
  │  spec:       │          │  spec:                   │
  │    (无 tolerations)     │    tolerations:          │
  │              │          │    - key: dedicated      │
  │  状态: 不调度 │          │      operator: Equal     │
  │  (被 Taint 排斥)        │      value: special      │
  └──────────────┘          │      effect: NoSchedule  │
                            │  状态: 可调度             │
                            │  (Toleration 容忍 Taint)  │
                            └──────────────────────────┘
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: special-pod             # Pod 名称
spec:                           # 规格定义
  tolerations:                  # 容忍列表
  - key: "dedicated"            # 匹配的 Taint key
    operator: "Equal"           # 精确匹配 key=value
    value: "special"            # 匹配的 Taint value
    effect: "NoSchedule"        # 匹配的 Taint effect
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx                # 镜像
""",
              common_errors=[
                  "effect 写错（必须与 Node Taint 的 effect 完全一致）",
                  "用 Exists 操作符时还写了 value（Exists 不需要 value）",
                  "tolerations 写在了 spec.containers 下（应在 spec 下）",
                  "以为 Toleration 能让 Pod 调度到任何节点（它只是允许调度到有 Taint 的节点）",
              ],
              tips=[
                  "Taint 排斥 + Toleration 包容 = 精细化调度隔离",
                  "用 kubectl taint node <name> key=value:NoSchedule 打污点",
                  "用 kubectl taint node <name> key:NoSchedule- 删除污点",
              ],
          ),
    ),
    Level(id="Q6.4", chapter="ch06", title="资源限制与调度",
          description="创建一个 Pod，设置 CPU 和 memory 的 requests 和 limits",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: limited-pod\nspec:\n  containers:\n    - name: app\n      image: nginx\n      # resources.requests 和 resources.limits",
          check_fn=_check_04_resource_limits,
          lesson=Lesson(
              concept="""\
## 资源限制与调度

K8s 调度器（kube-scheduler）根据 Pod 的 **resources.requests** 决定将 Pod 调度到哪个 Node。**resources.limits** 则由 kubelet 在运行时通过 cgroup 硬限制容器资源使用。

### requests vs limits

| 属性 | requests | limits |
|------|----------|--------|
| 用途 | 调度依据（scheduler 看这个） | 运行时上限（kubelet 看这个） |
| 调度 | Node 可分配资源 >= 所有 Pod requests 之和 | 不影响调度 |
| 超限 | 不会超（调度时已保证） | CPU: throttled（减速）; Memory: OOMKill |
| 必须设 | 推荐 | 推荐 |

### 调度决策过程

```
Pod requests: cpu=500m, memory=512Mi

kube-scheduler:
  1. 过滤: 剔除资源不足的 Node
     Node A: 可分配 cpu=300m → 不够，排除
     Node B: 可分配 cpu=800m → 够，保留
  2. 打分: 选择资源最充裕的 Node
     Node B: 800m - 500m = 300m 剩余 → 候选
  3. 绑定: Pod 调度到 Node B
```

### QoS 等级

K8s 根据 requests/limits 配置自动分配 QoS 等级：

| QoS | 条件 | 行为 |
|-----|------|------|
| **Guaranteed** | requests == limits（CPU 和 memory 都设） | 最后被驱逐 |
| **Burstable** | requests < limits 或只设部分 | 中等优先级 |
| **BestEffort** | 不设 requests 和 limits | 最先被驱逐 |

### 资源碎片化

如果 Node 上有很多小 Pod（requests 很小但 limits 很大），可能导致：
- Node 看起来还有容量（requests 之和未超）
- 但实际运行时资源被 limits 吃光
- 新 Pod 调度成功但运行时资源不足

合理设置 requests 接近实际用量，避免碎片化。

### CPU vs Memory

- **CPU 是可压缩资源**：超限时容器被 throttled（减速），不会被杀
- **Memory 是不可压缩资源**：超限时容器被 OOMKill（直接杀死）
""",
              key_fields=[
                  {"name": "spec.containers[].resources.requests.cpu", "description": "CPU 请求量，调度器据此决策", "required": True, "example": "100m"},
                  {"name": "spec.containers[].resources.requests.memory", "description": "内存请求量，调度器据此决策", "required": True, "example": "128Mi"},
                  {"name": "spec.containers[].resources.limits.cpu", "description": "CPU 上限，超限被 throttled", "required": True, "example": "500m"},
                  {"name": "spec.containers[].resources.limits.memory", "description": "内存上限，超限被 OOMKill", "required": True, "example": "256Mi"},
              ],
              diagram="""\
  资源调度决策过程

  ┌──── Pod (limited-pod) ──────────────────────┐
  │  containers:                                │
  │  - name: app                                │
  │    resources:                               │
  │      requests:    ◄── 调度器看这个           │
  │        cpu: 100m                            │
  │        memory: 128Mi                        │
  │      limits:       ◄── kubelet 看这个        │
  │        cpu: 500m                            │
  │        memory: 256Mi                        │
  └──────────┬──────────────────────────────────┘
             │
             ▼  kube-scheduler 过滤 Node

  ┌── Node A ─────────────┐   ┌── Node B ─────────────┐
  │  总容量: 2 CPU, 4Gi   │   │  总容量: 4 CPU, 8Gi   │
  │  已分配: 1.9 CPU      │   │  已分配: 1 CPU        │
  │  可分配: 0.1 CPU  ✗  │   │  可分配: 3 CPU    ✓  │
  │  (不够 100m)          │   │  (足够 100m)          │
  └───────────────────────┘   └──────────┬────────────┘
                                        │
                                        ▼
  Pod 被调度到 Node B
  运行时: CPU 超 500m → throttled
          Memory 超 256Mi → OOMKill
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: limited-pod             # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx                # 镜像
    resources:                  # 资源配置
      requests:                 # 请求量（调度依据）
        cpu: "100m"             # 100 millicpu = 0.1 核
        memory: "128Mi"         # 128 MiB
      limits:                   # 上限（运行时硬限制）
        cpu: "500m"             # 最多 0.5 核
        memory: "256Mi"         # 最多 256 MiB
""",
              common_errors=[
                  "只设 limits 不设 requests（调度器无依据，可能调度到资源不足的 Node）",
                  "requests > limits（不合理，K8s 允许但无意义）",
                  "CPU 值没加引号（YAML 可能解析为数字导致问题）",
                  "不设任何 resources（BestEffort，资源紧张时最先被驱逐）",
              ],
              tips=[
                  "requests 决定调度，limits 决定运行时上限--两者都要设",
                  "request 应接近实际平均用量，limit 应设为峰值用量",
                  "requests == limits 可以获得 Guaranteed QoS，最后被驱逐",
                  "用 kubectl describe node <name> 查看 Node 资源分配情况",
              ],
          ),
    ),
]
