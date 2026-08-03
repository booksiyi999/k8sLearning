"""Chapter 16: PriorityClass & Preemption（优先级与抢占）（5 关）

Q16.1 创建 PriorityClass
Q16.2 高优先级抢占
Q16.3 PriorityClass globalDefault
Q16.4 优先级设计策略
Q16.5 集群实战 - 多优先级工作负载
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, ClusterState, K8sError


# ==================== Q16.1 创建 PriorityClass ====================

def _check_161_create_priority_class(user_yaml: str) -> CheckResult:
    """Q16.1 创建一个 value: 1000000 的 PriorityClass"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.priorityclasses:
        return CheckResult(
            ok=False,
            error="没有创建任何 PriorityClass",
            hints=["你需要 apply 一个 kind: PriorityClass 的 YAML"],
        )

    pc_name = next(iter(state.priorityclasses))
    pc = state.priorityclasses[pc_name]
    value = pc.get("value")
    if value is None:
        return CheckResult(
            ok=False,
            error="PriorityClass 缺少 value",
            hints=["添加 value: 1000000"],
        )

    if not isinstance(value, int) or isinstance(value, bool):
        return CheckResult(
            ok=False,
            error=f"value 必须是整数，实际为 {type(value).__name__}",
            hints=["value 是整数类型，不需要引号"],
        )

    if value != 1000000:
        return CheckResult(
            ok=False,
            error=f"value 应为 1000000，实际为 {value}",
            hints=["设置 value: 1000000"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["PriorityClass 的 value 决定了 Pod 的调度优先级 ⭐"],
    )


LEVEL_Q16_1 = Level(
    id="Q16.1",
    chapter="ch16",
    title="创建 PriorityClass",
    description="""
# 创建 PriorityClass ⭐

**PriorityClass** 是 Kubernetes 中定义 Pod 优先级的资源。优先级高的 Pod 可以**抢占**（preempt）低优先级 Pod 的资源。

## 任务

创建一个 PriorityClass：
- `kind: PriorityClass`
- `apiVersion: scheduling.k8s.io/v1`
- `value: 1000000`（优先级数值）
- `description` 描述用途

## 提示

PriorityClass 的 value 是一个整数，越大优先级越高：
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
description: "High priority for critical workloads"
```
""",
    starter_yaml="""\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
# value: 1000000
description: "High priority for critical workloads"
""",
    check_fn=_check_161_create_priority_class,
    lesson=Lesson(
        concept="""\
## 什么是 PriorityClass？

**PriorityClass** 是 Kubernetes 中用于定义 Pod 优先级的资源。当集群资源不足时，高优先级 Pod 可以**抢占**低优先级 Pod 的资源。

### PriorityClass 的核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `value` | int | 优先级数值，越大优先级越高（10亿为系统保留） |
| `globalDefault` | bool | 是否作为未指定 priorityClassName 的 Pod 的默认值 |
| `description` | string | 人类可读的描述 |
| `preemptionPolicy` | string | 抢占策略：PreemptLowerPriority（默认）或 Never |

### value 数值范围

```
0                    1,000,000              1,000,000,000
├────────────────────────┼──────────────────────────┤
    用户级 Pod             系统关键 Pod           系统保留（不可使用）
    (可自定义)             (cluster-critical)     (kubernetes 内部)
```

- **10 亿（1,000,000,000）**：系统保留上限，用户不可使用
- **100 万 - 10 亿**：系统关键组件
- **0 - 100 万**：用户应用（推荐范围）

### 内置 PriorityClass

Kubernetes 集群自带两个 PriorityClass：

| 名称 | value | 说明 |
|------|-------|------|
| `system-cluster-critical` | 2,000,000,000 | 集群关键组件 |
| `system-node-critical` | 2,000,001,000 | 节点关键组件 |

### 工作流程

1. 创建 PriorityClass 定义优先级
2. Pod 通过 `priorityClassName` 引用 PriorityClass
3. 调度器根据优先级决定调度顺序
4. 资源不足时，高优先级 Pod 抢占低优先级 Pod
""",
        key_fields=[
            {"name": "value", "description": "优先级数值（整数），越大优先级越高", "required": True, "example": "1000000"},
            {"name": "globalDefault", "description": "是否作为全局默认优先级", "required": False, "example": "false"},
            {"name": "description", "description": "人类可读的描述", "required": False, "example": "High priority workloads"},
            {"name": "preemptionPolicy", "description": "抢占策略: PreemptLowerPriority 或 Never", "required": False, "example": "PreemptLowerPriority"},
        ],
        diagram="""\
  ┌─────────── PriorityClass (high-priority) ───────────┐
  │  apiVersion: scheduling.k8s.io/v1                   │
  │  kind: PriorityClass                                │
  │  metadata:                                          │
  │    name: high-priority                              │
  │  value: 1000000          ◄── 优先级数值              │
  │  globalDefault: false    ◄── 非全局默认              │
  │  description: "High priority..."                     │
  └──────────────────────────┬──────────────────────────┘
                             │ 被引用
                             ▼
  ┌─────────── Pod (critical-task) ────────────────────┐
  │  spec:                                             │
  │    priorityClassName: high-priority  ◄── 引用 PC    │
  │    containers:                                     │
  │    - name: critical                                │
  │      image: nginx                                  │
  └────────────────────────────────────────────────────┘
                             │
                             ▼ 调度器决策
  ┌────────────────────────────────────────────────────┐
  │  优先级: 1,000,000                                  │
  │  → 资源不足时可抢占 value < 1,000,000 的 Pod        │
  └────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: scheduling.k8s.io/v1   # PriorityClass API 版本
kind: PriorityClass                # 资源类型
metadata:                          # 元数据
  name: high-priority              # PriorityClass 名称
value: 1000000                     # 优先级数值
globalDefault: false               # 非全局默认
description: "High priority for critical workloads"  # 描述
""",
        common_errors=[
            "value 超过 10 亿（系统保留上限，会被 API Server 拒绝）",
            "value 设为负数（不允许）",
            "apiVersion 写错（应为 scheduling.k8s.io/v1）",
            "把 value 写在 spec 里面（value 是顶层字段，不在 spec 中）",
        ],
        tips=[
            "value 是整数类型，不需要引号",
            "用户应用推荐使用 0 - 1,000,000 范围",
            "用 kubectl get priorityclass 查看集群中所有优先级类",
        ],
    ),
)


# ==================== Q16.2 高优先级抢占 ====================

def _check_162_preemption(user_yaml: str) -> CheckResult:
    """Q16.2 创建高优先级 PriorityClass 并理解抢占"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.priorityclasses:
        return CheckResult(
            ok=False,
            error="没有创建任何 PriorityClass",
            hints=["你需要 apply 一个 kind: PriorityClass 的 YAML"],
        )

    pc_name = next(iter(state.priorityclasses))
    pc = state.priorityclasses[pc_name]
    value = pc.get("value")
    if value is None:
        return CheckResult(
            ok=False,
            error="PriorityClass 缺少 value",
            hints=["添加 value: 1000000"],
        )

    if not isinstance(value, int) or isinstance(value, bool):
        return CheckResult(
            ok=False,
            error=f"value 必须是整数，实际为 {type(value).__name__}",
            hints=["value 是整数类型"],
        )

    # 验证 value 在高优先级范围（>= 100000）
    if value < 100000:
        return CheckResult(
            ok=False,
            error=f"value 应 >= 100000（高优先级），实际为 {value}",
            hints=["高优先级建议 value: 1000000 或更高"],
        )

    # 验证 description 存在
    description = pc.get("description")
    if not description:
        return CheckResult(
            ok=False,
            error="PriorityClass 缺少 description",
            hints=["添加 description 说明此优先级的用途"],
        )

    # 验证 preemptionPolicy（默认 PreemptLowerPriority）
    pp = pc.get("preemptionPolicy", "PreemptLowerPriority")
    if pp not in ("PreemptLowerPriority", "Never"):
        return CheckResult(
            ok=False,
            error=f"preemptionPolicy 应为 PreemptLowerPriority 或 Never，实际为 {pp}",
            hints=["preemptionPolicy: PreemptLowerPriority 允许抢占低优先级 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["高优先级 Pod 可以抢占低优先级 Pod 的资源来获得调度机会 ⚡"],
    )


LEVEL_Q16_2 = Level(
    id="Q16.2",
    chapter="ch16",
    title="高优先级抢占",
    description="""
# 高优先级抢占 ⚡

当集群资源不足时，高优先级 Pod 可以**抢占**低优先级 Pod 的资源——被抢占的 Pod 会被驱逐，释放资源给高优先级 Pod。

## 任务

创建一个高优先级 PriorityClass：
- `value: 1000000`（或更高）
- `description` 描述抢占策略
- `preemptionPolicy: PreemptLowerPriority`（默认值，可显式写出）

## 提示

抢占机制的核心流程：
```
1. 高优先级 Pod 进入调度队列
2. 调度器发现资源不足
3. 查找节点上优先级更低的 Pod
4. 驱逐（抢占）低优先级 Pod
5. 高优先级 Pod 调度到释放的节点
6. 被抢占的 Pod 进入重调度队列
```
""",
    starter_yaml="""\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-priority
# value: 1000000
# description: "Critical workloads that can preempt others"
# preemptionPolicy: PreemptLowerPriority
""",
    check_fn=_check_162_preemption,
    lesson=Lesson(
        concept="""\
## 抢占机制（Preemption）

当高优先级 Pod 无法调度（资源不足）时，调度器会尝试**抢占**低优先级 Pod 的资源。

### 抢占的工作流程

```
初始状态:
  Node-1 (资源已满)
  ├── Pod-A (priority: 1000000)  ← 高优先级
  └── Pod-B (priority: 100)     ← 低优先级

新 Pod-C (priority: 500000) 到达:
  1. 调度器发现所有节点资源不足
  2. 查找可以抢占的节点 → Node-1
  3. Node-1 上 Pod-B (100) < Pod-C (500000)
  4. 驱逐 Pod-B，释放资源
  5. Pod-C 调度到 Node-1

结果:
  Node-1
  ├── Pod-A (priority: 1000000)
  └── Pod-C (priority: 500000)  ← 新调度

  Pod-B (priority: 100) → Pending，等待资源
```

### preemptionPolicy

| 值 | 说明 |
|----|------|
| `PreemptLowerPriority`（默认） | 允许抢占更低优先级的 Pod |
| `Never` | 永不抢占其他 Pod（但自身仍可被更高优先级 Pod 抢占） |

### 抢占的注意事项

1. **优雅终止**：被抢占的 Pod 会收到 SIGTERM，有 `terminationGracePeriodSeconds`（默认 30s）清理
2. **PodDisruptionBudget**：抢占**不受 PDB 约束**（PDB 只保护自愿中断）
3. **反抖动**：调度器有延迟机制避免抢占风暴
4. **PriorityClass 选择**：只有优先级更低的 Pod 才会被抢占

### 什么时候用抢占？

- **关键任务**：CI/CD 流水线、批处理任务需要及时调度
- **弹性集群**：低优先级 Pod 作为"可驱逐"工作负载填充空闲资源
- **资源争抢**：多团队共享集群时按优先级分配

### 什么时候用 preemptionPolicy: Never？

- **后台任务**：不希望影响其他 Pod，自己排队等待
- **开发环境**：避免抢占导致测试中断
- **数据迁移**：低优先级但不可中断的任务
""",
        key_fields=[
            {"name": "value", "description": "优先级数值，越大越优先抢占", "required": True, "example": "1000000"},
            {"name": "preemptionPolicy", "description": "抢占策略: PreemptLowerPriority 或 Never", "required": False, "example": "PreemptLowerPriority"},
            {"name": "description", "description": "描述此优先级的用途和抢占行为", "required": False, "example": "Critical workloads"},
        ],
        diagram="""\
  抢占前:
  ┌─────────────── Node-1 (资源已满) ───────────────┐
  │  Pod-A  (priority: 1000000)  ✅ 运行中           │
  │  Pod-B  (priority: 100)      ✅ 运行中           │
  └─────────────────────────────────────────────────┘

  Pod-C (priority: 500000) 到达 → 资源不足!

  ┌─────────── 调度器抢占决策 ───────────┐
  │  1. 遍历节点找可抢占的 Pod            │
  │  2. Node-1: Pod-B (100) < Pod-C (500k)│
  │  3. Pod-B 被选中抢占                   │
  │  4. 发送 SIGTERM 给 Pod-B             │
  │  5. Pod-B 优雅退出，释放资源           │
  └────────────────────┬─────────────────┘
                       │
                       ▼
  抢占后:
  ┌─────────────── Node-1 ──────────────────────────┐
  │  Pod-A  (priority: 1000000)  ✅ 仍在运行         │
  │  Pod-C  (priority: 500000)   ✅ 新调度           │
  └─────────────────────────────────────────────────┘
  Pod-B  → Pending (等待资源重调度)
""",
        example_yaml="""\
apiVersion: scheduling.k8s.io/v1   # PriorityClass API 版本
kind: PriorityClass                # 资源类型
metadata:                          # 元数据
  name: critical-priority          # 名称
value: 1000000                     # 高优先级数值
description: "Critical workloads that can preempt others"  # 描述
preemptionPolicy: PreemptLowerPriority  # 允许抢占低优先级 Pod
""",
        common_errors=[
            "value 超过 10 亿导致 API 拒绝",
            "preemptionPolicy 拼写错误（注意大小写）",
            "误以为 PDB 能阻止抢占（抢占不受 PDB 约束）",
            "value 设得过高导致频繁抢占其他 Pod",
        ],
        tips=[
            "抢占不受 PodDisruptionBudget 约束",
            "被抢占的 Pod 会优雅终止（SIGTERM + grace period）",
            "用 preemptionPolicy: Never 创建不抢占但可被抢占的 PriorityClass",
            "kubectl describe pod 可以查看 Pod 是否因抢占被驱逐",
        ],
    ),
)


# ==================== Q16.3 PriorityClass globalDefault ====================

def _check_163_global_default(user_yaml: str) -> CheckResult:
    """Q16.3 创建 globalDefault: true 的 PriorityClass"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.priorityclasses:
        return CheckResult(
            ok=False,
            error="没有创建任何 PriorityClass",
            hints=["你需要 apply 一个 kind: PriorityClass 的 YAML"],
        )

    pc_name = next(iter(state.priorityclasses))
    pc = state.priorityclasses[pc_name]
    value = pc.get("value")
    if value is None:
        return CheckResult(
            ok=False,
            error="PriorityClass 缺少 value",
            hints=["添加 value: 100000"],
        )

    if isinstance(value, bool) or not isinstance(value, int):
        return CheckResult(
            ok=False,
            error=f"value 必须是整数，实际为 {type(value).__name__}",
            hints=["value 是整数类型，不需要引号"],
        )

    if value < 0:
        return CheckResult(
            ok=False,
            error="value 不能为负数",
            hints=["value 必须是非负整数"],
        )

    global_default = pc.get("globalDefault")
    if global_default is not True:
        return CheckResult(
            ok=False,
            error="globalDefault 应为 true",
            hints=["设置 globalDefault: true"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["globalDefault: true 使所有未指定 priorityClassName 的 Pod 自动使用此优先级 🌐"],
    )


LEVEL_Q16_3 = Level(
    id="Q16.3",
    chapter="ch16",
    title="PriorityClass globalDefault",
    description="""
# PriorityClass globalDefault 🌐

`globalDefault: true` 的 PriorityClass 会作为所有**未指定 priorityClassName** 的 Pod 的默认优先级。

## 任务

创建一个 globalDefault 为 true 的 PriorityClass：
- `value: 100000`
- `globalDefault: true`
- `description` 说明用途

## 提示

注意：一个集群中只能有一个 PriorityClass 的 globalDefault 为 true：
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: default-priority
value: 100000
globalDefault: true
description: "Default priority for all pods"
```
""",
    starter_yaml="""\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: default-priority
# value: 100000
# globalDefault: true
description: "Default priority for all pods"
""",
    check_fn=_check_163_global_default,
    lesson=Lesson(
        concept="""\
## globalDefault 详解

`globalDefault: true` 的 PriorityClass 会成为集群中所有未显式指定 `priorityClassName` 的 Pod 的默认优先级。

### globalDefault 的作用

```
Pod 创建时:
  ├── spec.priorityClassName 指定了?
  │   ├── 是 → 使用指定的 PriorityClass 的 value
  │   └── 否 → 使用 globalDefault PriorityClass 的 value
  │            （如果没有 globalDefault PC，默认 value = 0）
```

### 关键规则

1. **集群中只能有一个** globalDefault PriorityClass
2. 设置新的 globalDefault 会覆盖旧的（旧的不影响已运行的 Pod）
3. 已运行的 Pod 优先级**不会改变**（只有新建 Pod 受影响）
4. 如果没有 globalDefault PC，未指定的 Pod 优先级为 0

### 使用场景

| 场景 | value | globalDefault | 说明 |
|------|-------|---------------|------|
| 默认优先级 | 100000 | true | 所有普通 Pod 的基线 |
| 高优先级 | 1000000 | false | 关键任务引用 |
| 低优先级 | 10 | false | 可被抢占的后台任务 |

### 典型优先级体系

```
┌─────────────────────────────────────────┐
│  PriorityClass 体系                      │
├─────────────────────────────────────────┤
│  system-node-critical  (2B)   系统级     │
│  system-cluster-critical (2B) 系统级     │
│  high-priority (1M)            关键任务  │
│  default-priority (100k) ← globalDefault │
│  low-priority (10)            后台任务   │
│  (未指定) (0)                 最低优先级 │
└─────────────────────────────────────────┘
```

### 注意事项

- 修改 globalDefault 只影响**之后创建**的 Pod
- 如果已有 globalDefault PC，创建新的会覆盖旧的
- 建议在集群初始化时就设置 globalDefault
""",
        key_fields=[
            {"name": "value", "description": "默认优先级数值", "required": True, "example": "100000"},
            {"name": "globalDefault", "description": "是否作为全局默认（集群中只能有一个为 true）", "required": True, "example": "true"},
            {"name": "description", "description": "描述此默认优先级的用途", "required": False, "example": "Default priority"},
        ],
        diagram="""\
  ┌──── PriorityClass (default-priority) ────┐
  │  value: 100000                           │
  │  globalDefault: true  ◄── 全局默认        │
  └──────────────────┬───────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
  Pod-A            Pod-B            Pod-C
  priorityClassName  priorityClassName  (未指定)
  = high-priority   = low-priority
  value: 1000000    value: 10         value: 100000
                                      ↑ 使用 globalDefault

  所有未指定 priorityClassName 的 Pod
  自动获得 value: 100000 的优先级
""",
        example_yaml="""\
apiVersion: scheduling.k8s.io/v1   # PriorityClass API 版本
kind: PriorityClass                # 资源类型
metadata:                          # 元数据
  name: default-priority           # 名称
value: 100000                      # 默认优先级数值
globalDefault: true                # 设为全局默认
description: "Default priority for all pods"  # 描述
""",
        common_errors=[
            "同时设置多个 globalDefault: true 的 PriorityClass",
            "globalDefault 值不是布尔类型（应为 true/false，不是字符串）",
            "误以为修改 globalDefault 会影响已运行的 Pod（只影响新 Pod）",
            "globalDefault 设得太高导致普通 Pod 抢占其他工作负载",
        ],
        tips=[
            "一个集群只能有一个 globalDefault: true 的 PriorityClass",
            "修改 globalDefault 只影响之后创建的 Pod",
            "建议 globalDefault 的 value 设为中等值（如 100000）",
            "用 kubectl get priorityclass 查看哪个是 globalDefault",
        ],
    ),
)


# ==================== Q16.4 优先级设计策略 ====================

def _check_164_priority_design(user_yaml: str) -> CheckResult:
    """Q16.4 创建两个 PriorityClass：系统级和用户级"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if len(state.priorityclasses) < 2:
        return CheckResult(
            ok=False,
            error="需要创建至少 2 个 PriorityClass（系统级和用户级）",
            hints=["用多文档 YAML（--- 分隔）创建两个 PriorityClass"],
        )

    # 查找系统级（value >= 500000）和用户级（value < 500000）
    system_pc = None
    user_pc = None
    global_default_count = 0
    for name, pc in state.priorityclasses.items():
        value = pc.get("value")
        if not isinstance(value, int) or isinstance(value, bool):
            continue
        # 检查是否多个 globalDefault=true
        if pc.get("globalDefault") is True:
            global_default_count += 1
        if value >= 500000:
            system_pc = pc
        elif value < 500000:
            user_pc = pc

    if global_default_count > 1:
        return CheckResult(
            ok=False,
            error="集群中只能有一个 PriorityClass 设置 globalDefault: true",
            hints=["只保留一个 globalDefault: true 的 PriorityClass"],
        )

    if system_pc is None:
        return CheckResult(
            ok=False,
            error="缺少系统级 PriorityClass（value >= 500000）",
            hints=["创建一个 value: 800000 或更高的系统级 PriorityClass"],
        )

    if user_pc is None:
        return CheckResult(
            ok=False,
            error="缺少用户级 PriorityClass（value < 500000）",
            hints=["创建一个 value: 100000 或更低的用户级 PriorityClass"],
        )

    # 验证用户级有 globalDefault
    if not user_pc.get("globalDefault"):
        return CheckResult(
            ok=False,
            error="用户级 PriorityClass 应设置 globalDefault: true",
            hints=["为用户级 PriorityClass 添加 globalDefault: true"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["合理的优先级分层设计是集群稳定运行的基础 📐"],
    )


LEVEL_Q16_4 = Level(
    id="Q16.4",
    chapter="ch16",
    title="优先级设计策略",
    description="""
# 优先级设计策略 📐

在生产集群中，合理的优先级分层设计确保关键工作负载优先调度，普通任务不互相干扰。

## 任务

用**多文档 YAML** 创建两个 PriorityClass：

1. **系统级**：`name: system-critical`，`value: 800000`
2. **用户级**：`name: user-default`，`value: 100000`，`globalDefault: true`

## 提示

典型的优先级分层：
```yaml
# 系统级（高优先级，可抢占用户级）
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: system-critical
value: 800000
description: "System critical workloads"
---
# 用户级（默认优先级）
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: user-default
value: 100000
globalDefault: true
description: "Default priority for user workloads"
```
""",
    starter_yaml="""\
# --- 系统级 PriorityClass ---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: system-critical
# value: 800000
description: "System critical workloads"
---
# --- 用户级 PriorityClass ---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: user-default
# value: 100000
# globalDefault: true
description: "Default priority for user workloads"
""",
    check_fn=_check_164_priority_design,
    lesson=Lesson(
        concept="""\
## 优先级设计策略

在生产集群中，合理的优先级分层是保障服务稳定性的关键。

### 推荐的优先级分层

```
┌──────────────────────────────────────────────────┐
│  层级            value       说明                  │
├──────────────────────────────────────────────────┤
│  系统保留        2B+         k8s 内置（不可使用）  │
│  系统关键        800,000     核心 Infra 服务       │
│  生产关键        500,000     生产核心应用          │
│  用户默认        100,000     普通应用 (globalDefault)│
│  后台任务        10          批处理/可驱逐         │
│  最低优先级      0           未指定 priorityClass  │
└──────────────────────────────────────────────────┘
```

### 设计原则

1. **系统级 > 用户级**：确保基础设施优先调度
2. **间隔足够大**：不同层级之间 value 差值要大，便于未来插入新层级
3. **globalDefault 设在中低层**：避免默认 Pod 抢占其他工作负载
4. **关键应用显式引用**：不要依赖 globalDefault，显式指定 priorityClassName

### 系统级 vs 用户级

| 维度 | 系统级 | 用户级 |
|------|--------|--------|
| value | 高（500K+） | 低（100K） |
| globalDefault | false | true（可选） |
| preemptionPolicy | PreemptLowerPriority | PreemptLowerPriority |
| 典型应用 | DNS、Ingress、监控 | Web、API、Worker |
| 抢占行为 | 可抢占用户级 Pod | 可抢占更低优先级 |

### 多团队共享集群的优先级设计

```
团队 A (高优先级):
  PriorityClass: team-a-high (value: 600000)
  PriorityClass: team-a-default (value: 100000)

团队 B (低优先级):
  PriorityClass: team-b-default (value: 50000)
  PriorityClass: team-b-batch (value: 10)

效果:
  - 团队 A 的关键 Pod 优先于团队 B
  - 团队 B 的批量任务可被团队 A 抢占
  - 公平性通过 ResourceQuota 保障
```

### 抢占与资源配额的配合

- **PriorityClass**：控制调度优先级和抢占
- **ResourceQuota**：控制资源总量上限
- **LimitRange**：控制单个 Pod 资源上下限

三者配合使用才能实现完善的资源管理。
""",
        key_fields=[
            {"name": "value (系统级)", "description": "系统级优先级，建议 500000+", "required": True, "example": "800000"},
            {"name": "value (用户级)", "description": "用户级优先级，建议 100000", "required": True, "example": "100000"},
            {"name": "globalDefault (用户级)", "description": "用户级设为全局默认", "required": True, "example": "true"},
            {"name": "preemptionPolicy", "description": "抢占策略", "required": False, "example": "PreemptLowerPriority"},
        ],
        diagram="""\
  ┌──────────── 多文档 YAML ────────────┐
  │                                      │
  │  ---                                 │
  │  PriorityClass: system-critical      │
  │    value: 800000                     │
  │    (系统级，可抢占用户级)              │
  │                                      │
  │  ---                                 │
  │  PriorityClass: user-default         │
  │    value: 100000                     │
  │    globalDefault: true               │
  │    (用户级，全局默认)                  │
  │                                      │
  └────────────────┬─────────────────────┘
                   │
                   ▼
  ┌─────────── 优先级体系 ──────────────┐
  │                                      │
  │  800,000  system-critical   系统级   │
  │    ↑ 可抢占                          │
  │  100,000  user-default      用户级   │
  │    ↑ 可抢占                          │
  │    0      (未指定)          最低     │
  │                                      │
  └──────────────────────────────────────┘
""",
        example_yaml="""\
# --- 系统级 PriorityClass ---
apiVersion: scheduling.k8s.io/v1   # PriorityClass API 版本
kind: PriorityClass                # 资源类型
metadata:                          # 元数据
  name: system-critical            # 名称
value: 800000                      # 系统级高优先级
description: "System critical workloads"  # 描述
---
# --- 用户级 PriorityClass ---
apiVersion: scheduling.k8s.io/v1   # PriorityClass API 版本
kind: PriorityClass                # 资源类型
metadata:                          # 元数据
  name: user-default               # 名称
value: 100000                      # 用户级默认优先级
globalDefault: true                # 全局默认
description: "Default priority for user workloads"  # 描述
""",
        common_errors=[
            "所有 PriorityClass 的 value 都很接近（失去分层效果）",
            "globalDefault 设在最高优先级（普通 Pod 会抢占一切）",
            "value 间隔太小，未来无法插入新的优先级层级",
            "忘记为关键应用显式指定 priorityClassName（依赖 globalDefault 不够明确）",
        ],
        tips=[
            "不同层级之间 value 间隔建议至少 100000",
            "globalDefault 应设在中低优先级层级",
            "关键应用应显式指定 priorityClassName，不依赖 globalDefault",
            "配合 ResourceQuota 和 LimitRange 实现完整的资源管理",
        ],
    ),
)


# ==================== Q16.5 集群实战 - 多优先级工作负载 ====================

def _check_165_multi_priority_workload(user_yaml: str) -> CheckResult:
    """Q16.5 多文档 YAML：PriorityClass + Pod 引用 priorityClassName"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 PriorityClass
    if not state.priorityclasses:
        return CheckResult(
            ok=False,
            error="没有创建任何 PriorityClass",
            hints=["多文档 YAML 中应包含 kind: PriorityClass"],
        )

    pc_name = next(iter(state.priorityclasses))
    pc = state.priorityclasses[pc_name]
    value = pc.get("value")
    if value is None:
        return CheckResult(
            ok=False,
            error="PriorityClass 缺少 value",
            hints=["添加 value: 1000000"],
        )

    if isinstance(value, bool) or not isinstance(value, int):
        return CheckResult(
            ok=False,
            error=f"value 必须是整数，实际为 {type(value).__name__}",
            hints=["value 是整数类型，不需要引号"],
        )

    # 检查 Pod
    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["多文档 YAML 中应包含 kind: Pod"],
        )

    # 找到引用了 PriorityClass 的 Pod
    found_ref = False
    for pod_name, pod in state.pods.items():
        pod_spec = pod.get("spec", {})
        if not isinstance(pod_spec, dict):
            continue
        priority_class_name = pod_spec.get("priorityClassName")
        if priority_class_name == pc_name:
            found_ref = True
            break

    if not found_ref:
        return CheckResult(
            ok=False,
            error=f"没有 Pod 引用 PriorityClass '{pc_name}'",
            hints=[f"在 Pod spec 中添加 priorityClassName: {pc_name}"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["PriorityClass + Pod 的组合实现了基于优先级的调度 🎯"],
    )


LEVEL_Q16_5 = Level(
    id="Q16.5",
    chapter="ch16",
    title="集群实战 - 多优先级工作负载",
    description="""
# 集群实战 - 多优先级工作负载 🎯

将 PriorityClass 与 Pod 结合使用，实现基于优先级的调度和抢占。

## 任务

用**多文档 YAML** 创建：
1. **PriorityClass**：`name: critical-pc`，`value: 1000000`
2. **Pod**：引用 `priorityClassName: critical-pc`，使用 `nginx:1.25` 镜像

## 提示

Pod 通过 `spec.priorityClassName` 引用 PriorityClass：
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pc
value: 1000000
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: critical-pc
  containers:
  - name: nginx
    image: nginx:1.25
```
""",
    starter_yaml="""\
# --- PriorityClass ---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pc
# value: 1000000
---
# --- Pod ---
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  # priorityClassName: critical-pc
  containers:
  - name: nginx
    image: nginx:1.25
""",
    check_fn=_check_165_multi_priority_workload,
    lesson=Lesson(
        concept="""\
## 多优先级工作负载实战

在生产环境中，PriorityClass 必须与 Pod/Deployment 结合使用才能发挥作用。

### Pod 引用 PriorityClass

Pod 通过 `spec.priorityClassName` 引用 PriorityClass：

```yaml
spec:
  priorityClassName: critical-pc   # 引用 PriorityClass
  containers:
  - name: app
    image: nginx
```

### 完整的多优先级工作负载示例

```
┌─────────────────────────────────────────────┐
│  PriorityClass + Pod/Deployment 组合         │
├─────────────────────────────────────────────┤
│                                              │
│  1. critical-pc (value: 1000000)             │
│     → Pod: critical-app                      │
│     → 可抢占低优先级 Pod                      │
│                                              │
│  2. default-pc (value: 100000, globalDefault)│
│     → Pod: normal-app                        │
│     → 默认优先级                              │
│                                              │
│  3. batch-pc (value: 10)                     │
│     → Pod: batch-job                         │
│     → 可被抢占的后台任务                      │
│                                              │
└─────────────────────────────────────────────┘
```

### 调度优先级实战流程

```
1. Pod 创建时，调度器读取 priorityClassName
2. 查找对应的 PriorityClass，获取 value
3. 将 Pod 加入调度队列（按 value 排序）
4. 尝试调度：
   a. 资源充足 → 直接调度
   b. 资源不足 → 尝试抢占低优先级 Pod
5. 如果 preemptionPolicy: Never → 排队等待
```

### 生产环境最佳实践

1. **Deployment + PriorityClass**：生产应用应通过 Deployment 引用 PriorityClass
   ```yaml
   spec:
     template:
       spec:
         priorityClassName: critical-pc
   ```

2. **监控抢占事件**：被抢占的 Pod 会记录 Event
   ```
   kubectl get events --field-selector reason=Preempted
   ```

3. **配合 PDB**：PriorityClass 控制调度优先级，PDB 控制驱逐保护
   - PriorityClass：资源不足时的抢占
   - PDB：自愿中断时的保护
   - 两者互不冲突

4. **合理设置 value**：
   - 关键服务：500000 - 1000000
   - 普通服务：100000（globalDefault）
   - 批量任务：10 - 1000
""",
        key_fields=[
            {"name": "PriorityClass value", "description": "优先级数值", "required": True, "example": "1000000"},
            {"name": "Pod spec.priorityClassName", "description": "Pod 引用的 PriorityClass 名称", "required": True, "example": "critical-pc"},
            {"name": "--- (多文档分隔)", "description": "YAML 多文档分隔符", "required": True, "example": "---"},
        ],
        diagram="""\
  ┌─────────────── 多文档 YAML ───────────────┐
  │                                            │
  │  ---                                       │
  │  PriorityClass (critical-pc)               │
  │    value: 1000000                          │
  │                                            │
  │  ---                                       │
  │  Pod (critical-pod)                        │
  │    spec:                                   │
  │      priorityClassName: critical-pc  ◄── 引用│
  │      containers:                           │
  │      - name: nginx                         │
  │        image: nginx:1.25                   │
  │                                            │
  └──────────────────────┬─────────────────────┘
                         │ kubectl apply -f
                         ▼
  ┌─────────── 调度器决策 ─────────────────────┐
  │                                            │
  │  Pod: critical-pod                         │
  │  priority: 1000000                         │
  │                                            │
  │  调度队列:                                 │
  │  [critical-pod (1M)] → [normal-app (100K)] │
  │       ↑ 优先调度                            │
  │                                            │
  │  资源不足时:                                │
  │  → 抢占 value < 1000000 的 Pod             │
  │  → critical-pod 获得资源调度                │
  └────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- PriorityClass ---
apiVersion: scheduling.k8s.io/v1   # PriorityClass API 版本
kind: PriorityClass                # 资源类型
metadata:                          # 元数据
  name: critical-pc                # 名称
value: 1000000                     # 高优先级
description: "Critical priority class"  # 描述
---
# --- Pod ---
apiVersion: v1                     # Pod API 版本
kind: Pod                          # 资源类型
metadata:                          # 元数据
  name: critical-pod               # Pod 名称
spec:                              # 规格定义
  priorityClassName: critical-pc   # 引用 PriorityClass
  containers:                      # 容器列表
  - name: nginx                    # 容器名
    image: nginx:1.25              # 镜像
""",
        common_errors=[
            "Pod 的 priorityClassName 与 PriorityClass 的 name 不匹配",
            "把 priorityClassName 写在 containers 里面（应在 spec 顶层）",
            "多文档 YAML 忘记用 --- 分隔",
            "只创建 Pod 没创建 PriorityClass（priorityClassName 引用不存在的资源）",
        ],
        tips=[
            "Deployment 中通过 spec.template.spec.priorityClassName 引用 PriorityClass",
            "用 kubectl get pod -o wide 查看调度结果",
            "用 kubectl describe pod 查看 Priority 和 QoS 类",
            "kubectl get events --field-selector reason=Preempted 查看抢占事件",
        ],
    ),
)


CHAPTER_16_LEVELS: list[Level] = [
    LEVEL_Q16_1, LEVEL_Q16_2, LEVEL_Q16_3, LEVEL_Q16_4, LEVEL_Q16_5,
]
