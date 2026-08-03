"""Chapter 10: HPA（自动伸缩）（5 关）

Q10.1 创建 HPA（CPU 阈值）
Q10.2 HPA 扩缩容配置
Q10.3 HPA 多指标
Q10.4 HPA 行为配置
Q10.5 集群实战 - 对 Deployment 配置 HPA
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q10.1 创建 HPA（CPU 阈值） ====================

def _check_101_create_hpa(user_yaml: str) -> CheckResult:
    """Q10.1 创建 HPA，目标 CPU 50%，maxReplicas=10"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.horizontalpodautoscalers:
        return CheckResult(
            ok=False,
            error="没有创建任何 HorizontalPodAutoscaler",
            hints=["你需要 apply 一个 kind: HorizontalPodAutoscaler 的 YAML"],
        )

    hpa_name = next(iter(state.horizontalpodautoscalers))
    hpa = state.horizontalpodautoscalers[hpa_name]
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="HPA 缺少 spec", hints=[])

    # 检查 maxReplicas == 10
    max_replicas = spec.get("maxReplicas")
    if not isinstance(max_replicas, int):
        return CheckResult(
            ok=False,
            error=f"spec.maxReplicas 应为整数，实际为 {type(max_replicas).__name__}",
            hints=["设置 spec.maxReplicas: 10"],
        )
    if max_replicas != 10:
        return CheckResult(
            ok=False,
            error=f"spec.maxReplicas 应为 10，实际为 {max_replicas}",
            hints=["设置 spec.maxReplicas: 10"],
        )

    # 检查 scaleTargetRef 存在
    target = spec.get("scaleTargetRef")
    if not isinstance(target, dict):
        return CheckResult(
            ok=False,
            error="HPA 缺少 spec.scaleTargetRef",
            hints=["scaleTargetRef 指定要伸缩的目标资源"],
        )

    # 检查 CPU 指标
    metrics = spec.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return CheckResult(
            ok=False,
            error="HPA 缺少 spec.metrics（需要定义 CPU 指标）",
            hints=["添加 metrics，type: Resource，resource: cpu"],
        )

    # 检查是否有 CPU 指标且目标为 50%
    cpu_found = False
    cpu_target = None
    for m in metrics:
        if not isinstance(m, dict):
            continue
        if m.get("type") == "Resource":
            resource = m.get("resource", {})
            if isinstance(resource, dict) and resource.get("name") == "cpu":
                cpu_found = True
                cpu_target = resource.get("target", {})

    if not cpu_found:
        return CheckResult(
            ok=False,
            error="metrics 中没有找到 CPU 资源指标",
            hints=["添加 metrics，type: Resource，resource.name: cpu"],
        )

    # 检查目标 CPU 利用率为 50%
    if isinstance(cpu_target, dict):
        avg_util = cpu_target.get("averageUtilization")
        if avg_util is not None and avg_util != 50:
            return CheckResult(
                ok=False,
                error=f"CPU 目标利用率应为 50，实际为 {avg_util}",
                hints=["设置 resource.target.averageUtilization: 50"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=["HPA 创建成功！它将根据 CPU 利用率自动伸缩 📈"],
    )


LEVEL_Q10_1 = Level(
    id="Q10.1",
    chapter="ch10",
    title="创建 HPA（CPU 阈值）",
    description="""
# 创建 HPA（CPU 阈值）📈

**HorizontalPodAutoscaler（HPA）** 根据 CPU/Memory 等指标自动伸缩 Pod 副本数量。

## 任务

创建一个 HPA：
- `kind: HorizontalPodAutoscaler`
- `apiVersion: autoscaling/v2`
- 目标 CPU 利用率 50%
- `maxReplicas: 10`
- `scaleTargetRef` 指向一个 Deployment

## 提示

HPA 的核心配置：
```yaml
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
```
""",
    starter_yaml="""\
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  # maxReplicas: 10
  # metrics: 定义 CPU 指标
""",
    check_fn=_check_101_create_hpa,
    lesson=Lesson(
        concept="""\
## 什么是 HPA？

**HorizontalPodAutoscaler（HPA）** 是 Kubernetes 的自动伸缩控制器。它根据 CPU 利用率、内存利用率或自定义指标，自动增加或减少 Pod 的副本数量。

### HPA 工作原理

```
┌──────────────────────────────────────────────┐
│  HPA Controller (每 15s 轮询一次)             │
│                                              │
│  1. 读取 Metrics Server 获取 Pod CPU/Memory  │
│  2. 计算期望副本数 = 当前副本 × (实际/目标)   │
│  3. 更新 Deployment 的 replicas 字段          │
└──────────────────────────────────────────────┘
```

### 伸缩计算公式

```
期望副本数 = ceil(当前副本数 × (当前指标值 / 目标指标值))
```

例如：当前 3 个副本，CPU 使用率 100%，目标 50%：
```
期望副本数 = ceil(3 × (100/50)) = ceil(6) = 6
```

### autoscaling/v2 的优势

- 支持多指标（CPU + Memory + 自定义）
- 支持 behavior 字段控制扩缩容行为
- 更精细的指标选择（Utilization / AverageValue / Value）

### 前置条件

1. **Metrics Server** 必须安装（提供 CPU/Memory 指标）
2. **Deployment 必须设置 resources.requests**（HPA 基于 requests 计算 CPU 利用率）
3. 目标 Deployment 的 replicas 字段会被 HPA 覆盖
""",
        key_fields=[
            {"name": "spec.scaleTargetRef", "description": "伸缩目标资源引用", "required": True, "example": "{apiVersion: apps/v1, kind: Deployment, name: web}"},
            {"name": "spec.maxReplicas", "description": "最大副本数", "required": True, "example": "10"},
            {"name": "spec.metrics", "description": "伸缩指标列表", "required": True, "example": "[{type: Resource, resource: {name: cpu, target: {type: Utilization, averageUtilization: 50}}}]", },
            {"name": "spec.metrics[].resource.target.averageUtilization", "description": "目标 CPU/Memory 利用率百分比", "required": True, "example": "50"},
        ],
        diagram="""\
  HPA 自动伸缩模型

  ┌─────────────────────────────────────────┐
  │  HPA (web-hpa)                          │
  │  scaleTargetRef: Deployment/web         │
  │  maxReplicas: 10                        │
  │  metrics:                               │
  │    CPU target: 50%                      │
  └────────────────┬────────────────────────┘
                   │
                   ▼
  ┌────────────────────────────────────────┐
  │  Metrics Server                        │
  │  收集 Pod CPU/Memory 使用数据           │
  └────────────────┬───────────────────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
    ┌──────────┐      ┌──────────┐
    │ 扩容      │      │ 缩容      │
    │ CPU > 50% │      │ CPU < 50% │
    │ 增加副本  │      │ 减少副本  │
    └──────────┘      └──────────┘
          │                 │
          ▼                 ▼
    ┌────────────┐   ┌────────────┐
    │ 6 个 Pod   │   │ 2 个 Pod   │
    └────────────┘   └────────────┘
""",
        example_yaml="""\
apiVersion: autoscaling/v2                    # HPA API 版本
kind: HorizontalPodAutoscaler                 # 资源类型: HPA
metadata:                                     # 元数据
  name: web-hpa                               # HPA 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1                       # 目标 API 版本
    kind: Deployment                          # 目标类型
    name: web                                 # 目标名称
  maxReplicas: 10                             # 最大副本数
  metrics:                                    # 伸缩指标
  - type: Resource                            # 指标类型: 资源指标
    resource:                                 # 资源配置
      name: cpu                               # CPU 指标
      target:                                 # 目标值
        type: Utilization                     # 利用率类型
        averageUtilization: 50                # 目标 50% 利用率
""",
        common_errors=[
            "Deployment 没有设置 resources.requests.cpu，HPA 无法计算 CPU 利用率",
            "没有安装 Metrics Server，HPA 无法获取指标",
            "maxReplicas 设为 0 或负数（必须 >= 1）",
            "apiVersion 写成 autoscaling/v1（旧版不支持多指标和 behavior）",
        ],
        tips=[
            "用 kubectl get hpa 查看 HPA 状态和当前指标",
            "用 kubectl describe hpa <name> 查看伸缩事件历史",
            "HPA 默认 15 秒轮询一次指标，扩容快但缩容有冷却期",
        ],
    ),
)


# ==================== Q10.2 HPA 扩缩容配置 ====================

def _check_102_scale_config(user_yaml: str) -> CheckResult:
    """Q10.2 创建 HPA，minReplicas=2, maxReplicas=20"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.horizontalpodautoscalers:
        return CheckResult(
            ok=False,
            error="没有创建任何 HorizontalPodAutoscaler",
            hints=["你需要 apply 一个 kind: HorizontalPodAutoscaler 的 YAML"],
        )

    hpa_name = next(iter(state.horizontalpodautoscalers))
    hpa = state.horizontalpodautoscalers[hpa_name]
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="HPA 缺少 spec", hints=[])

    # 检查 minReplicas
    min_replicas = spec.get("minReplicas")
    if not isinstance(min_replicas, int):
        return CheckResult(
            ok=False,
            error=f"spec.minReplicas 应为整数，实际为 {type(min_replicas).__name__}",
            hints=["设置 spec.minReplicas: 2"],
        )
    if min_replicas != 2:
        return CheckResult(
            ok=False,
            error=f"spec.minReplicas 应为 2，实际为 {min_replicas}",
            hints=["设置 spec.minReplicas: 2"],
        )

    # 检查 maxReplicas
    max_replicas = spec.get("maxReplicas")
    if not isinstance(max_replicas, int):
        return CheckResult(
            ok=False,
            error=f"spec.maxReplicas 应为整数，实际为 {type(max_replicas).__name__}",
            hints=["设置 spec.maxReplicas: 20"],
        )
    if max_replicas != 20:
        return CheckResult(
            ok=False,
            error=f"spec.maxReplicas 应为 20，实际为 {max_replicas}",
            hints=["设置 spec.maxReplicas: 20"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["HPA 扩缩容范围配置正确：2-20 个副本 📊"],
    )


LEVEL_Q10_2 = Level(
    id="Q10.2",
    chapter="ch10",
    title="HPA 扩缩容配置",
    description="""
# HPA 扩缩容配置 📊

通过 `minReplicas` 和 `maxReplicas` 控制 HPA 的伸缩范围，避免副本过少（影响可用性）或过多（浪费资源）。

## 任务

创建一个 HPA：
- `minReplicas: 2`
- `maxReplicas: 20`
- `scaleTargetRef` 指向一个 Deployment

## 提示

```yaml
spec:
  minReplicas: 2
  maxReplicas: 20
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```
""",
    starter_yaml="""\
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  # minReplicas: 2
  # maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
""",
    check_fn=_check_102_scale_config,
    lesson=Lesson(
        concept="""\
## HPA 扩缩容范围配置

`minReplicas` 和 `maxReplicas` 是 HPA 的两个关键边界字段，控制自动伸缩的上下限。

### minReplicas

- 定义最小副本数，保证应用始终有足够的实例处理流量
- 默认值为 1（不推荐用于生产）
- 生产环境建议设为 2 或更高，确保高可用
- HPA 不会将副本数缩容到 minReplicas 以下

### maxReplicas

- 定义最大副本数，防止资源无限扩张
- 必须设置且 >= minReplicas
- 受集群资源上限约束（Node 数量、CPU/Memory 总量）
- 建议根据预算和集群容量合理设置

### 伸缩范围的选择策略

| 场景 | minReplicas | maxReplicas | 理由 |
|------|-------------|-------------|------|
| 开发环境 | 1 | 3 | 节省资源 |
| 生产环境 | 2-3 | 10-20 | 高可用 + 弹性 |
| 高流量服务 | 5-10 | 50-100 | 应对突发流量 |
| 批处理 | 1 | 5 | 按需扩容 |

### HPA 伸缩冷却期

HPA 默认的伸缩行为：
- **扩容**：快速响应，通常 30 秒内完成
- **缩容**：保守策略，默认等待 5 分钟才缩容（防止抖动）

这是为了防止"抖动"（thrashing）--频繁扩缩容导致系统不稳定。

### 与 VPA 的区别

- **HPA**（Horizontal Pod Autoscaler）：调整 Pod **数量**（水平伸缩）
- **VPA**（Vertical Pod Autoscaler）：调整 Pod **资源请求**（垂直伸缩）
- 两者不能同时对同一资源的 CPU/Memory 使用
""",
        key_fields=[
            {"name": "spec.minReplicas", "description": "最小副本数，保证基础可用性", "required": True, "example": "2"},
            {"name": "spec.maxReplicas", "description": "最大副本数，限制资源上限", "required": True, "example": "20"},
            {"name": "spec.scaleTargetRef", "description": "伸缩目标资源", "required": True, "example": "{kind: Deployment, name: web}"},
            {"name": "spec.metrics", "description": "伸缩指标", "required": True, "example": "[{type: Resource, resource: {name: cpu, ...}}]"},
        ],
        diagram="""\
  HPA 扩缩容范围

  副本数
   20 ┤ ★ maxReplicas (上限)
      │     ╱──╲
   15 ┤    ╱    ╲
      │   ╱      ╲
   10 ┤  ╱        ╲
      │ ╱          ╲──╱──╲
    5 ┤╱                 ╲
      │
    2 ┤★ minReplicas (下限)
      │
    0 ┼────────────────────────── 时间
      │  流量增大 → 扩容      流量减少 → 缩容

  规则:
  ├── 副本数 >= minReplicas (2) 始终保持
  ├── 副本数 <= maxReplicas (20) 不会超过
  └── 缩容有 5 分钟冷却期 (默认)
""",
        example_yaml="""\
apiVersion: autoscaling/v2                    # HPA API 版本
kind: HorizontalPodAutoscaler                 # 资源类型: HPA
metadata:                                     # 元数据
  name: web-hpa                               # HPA 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1                       # 目标 API 版本
    kind: Deployment                          # 目标类型
    name: web                                 # 目标名称
  minReplicas: 2                              # 最小副本数
  maxReplicas: 20                             # 最大副本数
  metrics:                                    # 伸缩指标
  - type: Resource                            # 资源指标
    resource:                                 # 资源配置
      name: cpu                               # CPU 指标
      target:                                 # 目标值
        type: Utilization                     # 利用率
        averageUtilization: 50                # 目标 50%
""",
        common_errors=[
            "minReplicas 大于 maxReplicas（会导致 HPA 异常）",
            "忘记设置 minReplicas（默认为 1，生产环境不安全）",
            "maxReplicas 设得过高导致集群资源耗尽",
            "Deployment 的 replicas 手动设为 0，HPA 无法扩容",
        ],
        tips=[
            "生产环境 minReplicas 至少设为 2，保证高可用",
            "maxReplicas 应考虑集群资源总量的 80% 以内",
            "用 kubectl get hpa -w 持续观察副本变化",
        ],
    ),
)


# ==================== Q10.3 HPA 多指标 ====================

def _check_103_multi_metrics(user_yaml: str) -> CheckResult:
    """Q10.3 创建带 metrics 的 HPA，验证多指标"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.horizontalpodautoscalers:
        return CheckResult(
            ok=False,
            error="没有创建任何 HorizontalPodAutoscaler",
            hints=["你需要 apply 一个 kind: HorizontalPodAutoscaler 的 YAML"],
        )

    hpa_name = next(iter(state.horizontalpodautoscalers))
    hpa = state.horizontalpodautoscalers[hpa_name]
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="HPA 缺少 spec", hints=[])

    # 验证 metrics 存在且是列表
    metrics = spec.get("metrics")
    if not isinstance(metrics, list):
        return CheckResult(
            ok=False,
            error="HPA 缺少 spec.metrics（必须是列表）",
            hints=["在 spec.metrics 下定义指标列表"],
        )

    if len(metrics) < 2:
        return CheckResult(
            ok=False,
            error=f"多指标 HPA 应至少有 2 个指标，实际 {len(metrics)} 个",
            hints=["添加 CPU 和 Memory 两个指标"],
        )

    # 检查指标类型有效
    valid_types = {"Resource", "Pods", "Object", "External"}
    for i, m in enumerate(metrics):
        if not isinstance(m, dict):
            return CheckResult(ok=False, error=f"metrics[{i}] 格式错误", hints=[])
        m_type = m.get("type")
        if m_type not in valid_types:
            return CheckResult(
                ok=False,
                error=f"metrics[{i}].type 应为 {valid_types} 之一，实际为 '{m_type}'",
                hints=[f"设置 type: Resource / Pods / Object / External"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=["多指标 HPA 创建成功！综合 CPU 和 Memory 进行伸缩决策 📊"],
    )


LEVEL_Q10_3 = Level(
    id="Q10.3",
    chapter="ch10",
    title="HPA 多指标",
    description="""
# HPA 多指标 📊

HPA 支持同时使用多个指标进行伸缩决策。当有多个指标时，HPA 会取每个指标计算出的最大副本数，确保满足所有指标的需求。

## 任务

创建一个 HPA，同时使用 CPU 和 Memory 两个指标：
- `spec.metrics` 列表包含至少 2 个指标
- CPU 目标利用率 50%
- Memory 目标利用率 60%

## 提示

```yaml
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
```
""",
    starter_yaml="""\
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
  # metrics: 添加 CPU 和 Memory 两个指标
""",
    check_fn=_check_103_multi_metrics,
    lesson=Lesson(
        concept="""\
## HPA 多指标伸缩

Kubernetes HPA（autoscaling/v2）支持同时配置多个伸缩指标，综合判断所需的副本数量。

### 指标类型

| 类型 | 说明 | 数据来源 |
|------|------|---------|
| Resource | CPU/Memory 资源指标 | Metrics Server |
| Pods | 自定义 Pod 指标 | 自定义指标 API |
| Object | 集群对象指标（如 Ingress QPS） | 自定义指标 API |
| External | 外部指标（如 SQS 队列长度） | 外部指标 API |

### 多指标决策逻辑

当配置多个指标时，HPA 分别计算每个指标的期望副本数，取**最大值**：

```
CPU 指标计算: 需要扩容到 8 个副本
Memory 指标计算: 需要扩容到 5 个副本

最终决策: max(8, 5) = 8 个副本
```

这确保了所有指标的需求都被满足。

### Resource 指标详解

Resource 指标基于 Pod 的 CPU/Memory 使用量，有三种 target 类型：

1. **Utilization** - 利用率百分比（相对于 requests）
   - `averageUtilization: 50` 表示目标 50% 利用率
2. **AverageValue** - 每个 Pod 的平均值
   - `averageValue: 500m` 表示每个 Pod 平均使用 500m CPU
3. **Value** - 总值（仅 Object/External 指标支持）

### 自定义指标

通过安装 Prometheus Adapter 或其他自定义指标适配器，HPA 可以基于业务指标伸缩：

- HTTP 请求速率（QPS）
- 消息队列长度
- 数据库连接数
- 自定义应用指标
""",
        key_fields=[
            {"name": "spec.metrics", "description": "指标列表，可包含多个不同类型的指标", "required": True, "example": "[{type: Resource, ...}, {type: Resource, ...}]"},
            {"name": "spec.metrics[].type", "description": "指标类型: Resource/Pods/Object/External", "required": True, "example": "Resource"},
            {"name": "spec.metrics[].resource.name", "description": "资源名称: cpu/memory", "required": False, "example": "cpu"},
            {"name": "spec.metrics[].resource.target.averageUtilization", "description": "目标利用率百分比", "required": False, "example": "50"},
        ],
        diagram="""\
  HPA 多指标决策模型

  ┌─────────────────────────────────────────────┐
  │  HPA Controller                             │
  │                                             │
  │  指标 1: CPU  ──→ 计算期望副本: 8           │
  │  指标 2: Memory ──→ 计算期望副本: 5         │
  │                                             │
  │  最终决策: max(8, 5) = 8 个副本             │
  └──────────────────┬──────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Metrics  │ │ Metrics  │ │ Custom   │
  │ Server   │ │ Server   │ │ Metrics  │
  │ (CPU)    │ │ (Memory) │ │ Adapter  │
  └──────────┘ └──────────┘ └──────────┘

  多指标取最大值，确保所有指标需求都被满足
""",
        example_yaml="""\
apiVersion: autoscaling/v2                    # HPA API 版本 (v2 支持多指标)
kind: HorizontalPodAutoscaler                 # 资源类型: HPA
metadata:                                     # 元数据
  name: web-hpa                               # HPA 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2                              # 最小副本数
  maxReplicas: 20                             # 最大副本数
  metrics:                                    # 多指标列表
  - type: Resource                            # 指标 1: CPU
    resource:
      name: cpu                               # CPU 资源
      target:
        type: Utilization                     # 利用率类型
        averageUtilization: 50                # 目标 50%
  - type: Resource                            # 指标 2: Memory
    resource:
      name: memory                            # Memory 资源
      target:
        type: Utilization                     # 利用率类型
        averageUtilization: 60                # 目标 60%
""",
        common_errors=[
            "apiVersion 使用 autoscaling/v1（不支持多指标，必须用 v2）",
            "metrics 写成了单个字典而非列表",
            "自定义指标未安装 Prometheus Adapter，导致 HPA 无法获取指标",
            "Deployment 未设置 resources.requests，导致 Utilization 计算失败",
        ],
        tips=[
            "多指标 HPA 取最大期望副本数，确保所有指标需求被满足",
            "用 kubectl describe hpa <name> 查看各指标的当前值和目标值",
            "自定义指标伸缩需要安装 Prometheus Adapter 或类似组件",
        ],
    ),
)


# ==================== Q10.4 HPA 行为配置 ====================

def _check_104_behavior(user_yaml: str) -> CheckResult:
    """Q10.4 创建带 behavior 的 HPA"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.horizontalpodautoscalers:
        return CheckResult(
            ok=False,
            error="没有创建任何 HorizontalPodAutoscaler",
            hints=["你需要 apply 一个 kind: HorizontalPodAutoscaler 的 YAML"],
        )

    hpa_name = next(iter(state.horizontalpodautoscalers))
    hpa = state.horizontalpodautoscalers[hpa_name]
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="HPA 缺少 spec", hints=[])

    # 验证 behavior 存在
    behavior = spec.get("behavior")
    if not isinstance(behavior, dict):
        return CheckResult(
            ok=False,
            error="HPA 缺少 spec.behavior（必须是映射）",
            hints=["添加 spec.behavior 配置扩缩容行为"],
        )

    # 至少包含 scaleDown 或 scaleUp
    has_scale_down = "scaleDown" in behavior
    has_scale_up = "scaleUp" in behavior
    if not has_scale_down and not has_scale_up:
        return CheckResult(
            ok=False,
            error="behavior 应至少包含 scaleDown 或 scaleUp 配置",
            hints=["在 behavior 下添加 scaleDown 或 scaleUp"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["HPA 行为配置成功！精确控制扩缩容的速度和策略 ⚙️"],
    )


LEVEL_Q10_4 = Level(
    id="Q10.4",
    chapter="ch10",
    title="HPA 行为配置",
    description="""
# HPA 行为配置 ⚙️

`spec.behavior` 字段（autoscaling/v2 引入）允许精确控制 HPA 的扩容和缩容行为，包括速度限制和策略选择。

## 任务

创建一个带 `behavior` 配置的 HPA：
- `spec.behavior` 包含 `scaleDown` 配置
- `scaleDown` 中设置稳定窗口（stabilizationWindowSeconds）

## 提示

```yaml
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
```
""",
    starter_yaml="""\
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
  # behavior: 配置扩缩容行为
""",
    check_fn=_check_104_behavior,
    lesson=Lesson(
        concept="""\
## HPA Behavior（行为配置）

`spec.behavior` 是 autoscaling/v2 引入的高级特性，允许你精确控制 HPA 的扩容和缩容行为，避免默认策略可能带来的问题（如缩容太快导致服务中断）。

### 两大子配置

1. **scaleDown** - 控制缩容行为
   - `stabilizationWindowSeconds` - 稳定窗口（默认 300 秒）
   - `policies` - 缩容策略列表
   - `selectPolicy` - 策略选择方式（Min/Max/Disabled）

2. **scaleUp** - 控制扩容行为
   - `stabilizationWindowSeconds` - 稳定窗口（默认 0 秒）
   - `policies` - 扩容策略列表
   - `selectPolicy` - 策略选择方式

### 策略类型

| 类型 | 说明 | 示例 |
|------|------|------|
| Percent | 按当前副本的百分比 | value: 10 = 最多缩容 10% |
| Pods | 固定 Pod 数量 | value: 4 = 最多增减 4 个 Pod |

### 策略选择

- **Max**（默认）- 取所有策略中变化最大的（扩容快/缩容慢）
- **Min** - 取所有策略中变化最小的（保守）
- **Disabled** - 禁用该方向的伸缩

### 常见行为配置模式

1. **保守缩容** - 防止流量恢复时来不及扩容
   ```yaml
   scaleDown:
     stabilizationWindowSeconds: 600  # 10 分钟稳定期
     policies:
     - type: Percent
       value: 10
       periodSeconds: 60  # 每分钟最多缩 10%
   ```

2. **快速扩容** - 应对突发流量
   ```yaml
   scaleUp:
     stabilizationWindowSeconds: 0  # 无延迟
     policies:
     - type: Percent
       value: 100
       periodSeconds: 15  # 每 15s 可翻倍
   ```

3. **完全禁用缩容** - 保持峰值容量
   ```yaml
   scaleDown:
     selectPolicy: Disabled
   ```
""",
        key_fields=[
            {"name": "spec.behavior.scaleDown", "description": "缩容行为配置", "required": False, "example": "{stabilizationWindowSeconds: 300, policies: [...]}"},
            {"name": "spec.behavior.scaleUp", "description": "扩容行为配置", "required": False, "example": "{stabilizationWindowSeconds: 0, policies: [...]}"},
            {"name": "scaleDown.stabilizationWindowSeconds", "description": "缩容稳定窗口（秒），防止抖动", "required": False, "example": "300"},
            {"name": "scaleDown.policies[].type", "description": "策略类型: Percent/Pods", "required": False, "example": "Percent"},
            {"name": "scaleDown.selectPolicy", "description": "策略选择: Max/Min/Disabled", "required": False, "example": "Max"},
        ],
        diagram="""\
  HPA Behavior 扩缩容控制

  扩容 (scaleUp):
  ┌──────────────────────────────────────┐
  │ stabilizationWindowSeconds: 0 (立即) │
  │ policies:                            │
  │ - Percent: 100% / 15s (可翻倍)       │
  │ selectPolicy: Max (取最大)           │
  └──────────────────────────────────────┘
         │ 快速扩容
         ▼
  2 个 Pod ──> 4 个 Pod ──> 8 个 Pod
  (每 15s 可翻倍)

  缩容 (scaleDown):
  ┌──────────────────────────────────────┐
  │ stabilizationWindowSeconds: 300 (5m) │
  │ policies:                            │
  │ - Percent: 10% / 60s (每分钟缩 10%)  │
  │ selectPolicy: Min (保守)             │
  └──────────────────────────────────────┘
         │ 缓慢缩容
         ▼
  8 个 Pod ──等5分钟──> 7 个 Pod ──等1m──> 6 个 Pod
  (有冷却期，防止抖动)
""",
        example_yaml="""\
apiVersion: autoscaling/v2                    # HPA API 版本
kind: HorizontalPodAutoscaler                 # 资源类型
metadata:                                     # 元数据
  name: web-hpa                               # 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2                              # 最小副本
  maxReplicas: 20                             # 最大副本
  metrics:                                    # 指标
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  behavior:                                   # ← 行为配置
    scaleDown:                                # 缩容行为
      stabilizationWindowSeconds: 300         # 5 分钟稳定窗口
      policies:                               # 策略列表
      - type: Percent                         # 按百分比
        value: 10                             # 最多缩 10%
        periodSeconds: 60                     # 每 60 秒一次
      selectPolicy: Min                       # 选最小变化（保守）
    scaleUp:                                  # 扩容行为
      stabilizationWindowSeconds: 0           # 无延迟，立即扩容
      policies:
      - type: Percent
        value: 100                            # 可翻倍扩容
        periodSeconds: 15                     # 每 15 秒一次
""",
        common_errors=[
            "apiVersion 使用 autoscaling/v1（不支持 behavior，必须用 v2）",
            "stabilizationWindowSeconds 设为 0 导致缩容过快、服务抖动",
            "policies 的 type 写错（应为 Percent 或 Pods）",
            "忘记 selectPolicy 导致策略选择不符合预期",
        ],
        tips=[
            "scaleDown 的稳定窗口默认 300 秒，生产环境可适当增大",
            "scaleUp 的稳定窗口默认 0 秒，确保快速响应流量增长",
            "用 kubectl describe hpa <name> 查看行为配置和伸缩事件",
        ],
    ),
)


# ==================== Q10.5 集群实战 - 对 Deployment 配置 HPA ====================

def _check_105_deploy_hpa(user_yaml: str) -> CheckResult:
    """Q10.5 集群实战 - 对 Deployment 配置 HPA"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查有 HPA
    if not state.horizontalpodautoscalers:
        return CheckResult(
            ok=False,
            error="没有创建任何 HorizontalPodAutoscaler",
            hints=["你需要 apply 一个 kind: HorizontalPodAutoscaler 的 YAML"],
        )

    hpa_name = next(iter(state.horizontalpodautoscalers))
    hpa = state.horizontalpodautoscalers[hpa_name]
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="HPA 缺少 spec", hints=[])

    # 检查 scaleTargetRef
    target = spec.get("scaleTargetRef")
    if not isinstance(target, dict):
        return CheckResult(
            ok=False,
            error="HPA 缺少 spec.scaleTargetRef",
            hints=["scaleTargetRef 指定要伸缩的 Deployment"],
        )

    # 检查 maxReplicas
    max_replicas = spec.get("maxReplicas")
    if not isinstance(max_replicas, int) or max_replicas < 1:
        return CheckResult(
            ok=False,
            error="HPA 缺少有效的 spec.maxReplicas（正整数）",
            hints=["设置 spec.maxReplicas 为正整数"],
        )

    # 检查 metrics
    metrics = spec.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return CheckResult(
            ok=False,
            error="HPA 缺少 spec.metrics",
            hints=["添加 metrics 定义伸缩指标"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get hpa -w",
            "  kubectl describe hpa <name>",
            "  # 生成负载测试: kubectl run load-generator --image=busybox ...",
        ],
    )


LEVEL_Q10_5 = Level(
    id="Q10.5",
    chapter="ch10",
    title="集群实战: 对 Deployment 配置 HPA",
    description="""
# 集群实战: 对 Deployment 配置 HPA 🏗️

来真实集群上为 Deployment 配置 HPA，体验自动伸缩的完整流程！

## 任务

1. 创建一个带 resources.requests 的 Deployment
2. 创建 HPA 指向该 Deployment
3. 生成负载观察自动伸缩

## 要求

- `kind: Deployment`（容器需设置 `resources.requests.cpu`）
- `kind: HorizontalPodAutoscaler`
  - `scaleTargetRef` 指向 Deployment
  - `maxReplicas` 设为合理值（如 10）
  - `metrics` 定义 CPU 指标

## 验证步骤

```bash
# 1. 部署
kubectl apply -f deploy-hpa.yaml

# 2. 查看 HPA 状态
kubectl get hpa -w

# 3. 生成负载
kubectl run load-generator --image=busybox \
  -- /bin/sh -c "while true; do wget -q -O- http://web; done"

# 4. 观察 HPA 扩容
kubectl get hpa -w
# TARGETS 列会显示当前/目标 CPU

# 5. 停止负载
kubectl delete pod load-generator

# 6. 观察缩容（有冷却期）
kubectl get hpa -w
```
""",
    starter_yaml="""\
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
  # minReplicas: 2
  # maxReplicas: 10
  # metrics: 定义 CPU 指标
""",
    check_fn=_check_105_deploy_hpa,
    lesson=Lesson(
        concept="""\
## HPA 实战：完整自动伸缩流程

在真实集群中配置 HPA 需要多个组件配合工作，理解完整流程对生产运维至关重要。

### 前置条件检查

1. **Metrics Server 已安装**
   ```bash
   kubectl top pods  # 能正常输出说明已安装
   ```

2. **Deployment 设置了 resources.requests**
   ```yaml
   resources:
     requests:
       cpu: 100m   # HPA 基于 requests 计算 Utilization
   ```

### HPA 工作流程

```
1. HPA Controller 每 15s 轮询 Metrics API
   ↓
2. Metrics Server 从各 Node 的 cAdvisor 收集 CPU/Memory
   ↓
3. HPA 计算期望副本数:
   期望 = ceil(当前副本 × 当前CPU / 目标CPU)
   ↓
4. 更新 Deployment.spec.replicas
   ↓
5. Deployment Controller 创建/删除 Pod
```

### 常见问题排查

1. **TARGETS 显示 `<unknown>`**
   - Metrics Server 未安装或异常
   - Deployment 未设置 resources.requests

2. **HPA 不扩容**
   - 当前 CPU 低于目标值
   - 负载不足以触发扩容
   - maxReplicas 已达到

3. **HPA 不缩容**
   - 在稳定窗口期内（默认 5 分钟）
   - 缩容策略限制了速度

### 生产环境最佳实践

1. **合理设置 requests** - 过低导致过早扩容，过高导致不扩容
2. **配置 behavior** - 防止抖动，平滑伸缩
3. **监控 HPA 事件** - 用 `kubectl describe hpa` 查看伸缩历史
4. **结合 Cluster Autoscaler** - Pod 扩容但 Node 不够时，CA 自动加 Node
""",
        key_fields=[
            {"name": "Deployment.resources.requests.cpu", "description": "CPU 请求值，HPA 计算基准", "required": True, "example": "100m"},
            {"name": "HPA.spec.scaleTargetRef", "description": "指向要伸缩的 Deployment", "required": True, "example": "{kind: Deployment, name: web}"},
            {"name": "HPA.spec.maxReplicas", "description": "最大副本数", "required": True, "example": "10"},
            {"name": "HPA.spec.metrics", "description": "伸缩指标", "required": True, "example": "[{type: Resource, ...}]"},
        ],
        diagram="""\
  HPA 实战：自动伸缩完整流程

  ┌───────────┐     ┌──────────────┐     ┌──────────────┐
  │Deployment │     │     HPA      │     │Metrics Server│
  │ (web)     │◄────┤ scaleTargetRef│────►│ (CPU 数据)   │
  │ replicas:2│     │ maxRep: 10   │     └──────────────┘
  │ req: 100m │     │ CPU: 50%     │
  └─────┬─────┘     └──────┬───────┘
        │                  │
        │    ┌─────────────┘
        ▼    ▼
  ┌──────────────────────────────┐
  │  负载增大 (CPU > 50%)        │
  │  HPA 计算: 2 × (90/50) = 4  │
  │  → 更新 replicas: 4          │
  └──────────────┬───────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
  ┌──────┐  ┌──────┐  ┌──────┐
  │web-0 │  │web-1 │  │web-2 │  ← 新增 Pod
  │      │  │      │  │web-3 │
  └──────┘  └──────┘  └──────┘

  验证: kubectl get hpa -w
        kubectl describe hpa web-hpa
""",
        example_yaml="""\
# Deployment                              # 被伸缩的目标
apiVersion: apps/v1                      # Deployment API 版本
kind: Deployment                         # 资源类型
metadata:                                # 元数据
  name: web                              # 名称
spec:                                    # 规格
  replicas: 2                            # 初始副本数
  selector:                              # 标签选择器
    matchLabels:
      app: web
  template:                              # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:                        # 容器列表
      - name: nginx                      # 容器名
        image: nginx:1.25               # 镜像
        resources:                       # 资源设置（关键！）
          requests:                      # 请求值
            cpu: 100m                    # HPA 基于 requests 计算
---                                      # 多文档分隔
# HorizontalPodAutoscaler                # 自动伸缩器
apiVersion: autoscaling/v2               # HPA API 版本
kind: HorizontalPodAutoscaler            # 资源类型
metadata:                                # 元数据
  name: web-hpa                          # 名称
spec:                                    # 规格
  scaleTargetRef:                        # 伸缩目标
    apiVersion: apps/v1
    kind: Deployment
    name: web                            # 指向 Deployment
  minReplicas: 2                         # 最小副本
  maxReplicas: 10                        # 最大副本
  metrics:                               # 伸缩指标
  - type: Resource                       # 资源指标
    resource:
      name: cpu                          # CPU
      target:
        type: Utilization                # 利用率
        averageUtilization: 50           # 目标 50%
""",
        common_errors=[
            "Deployment 未设置 resources.requests.cpu，HPA 显示 <unknown>",
            "Metrics Server 未安装，HPA 无法获取 CPU 数据",
            "初始 replicas 与 minReplicas 冲突（HPA 会覆盖 replicas）",
            "忘记用多文档 YAML（---）分隔 Deployment 和 HPA",
        ],
        tips=[
            "用 kubectl top pods 验证 Metrics Server 是否正常工作",
            "用 kubectl run load-generator 生成测试负载观察扩容",
            "HPA 缩容有 5 分钟冷却期，不要期望立即缩容",
        ],
    ),
)


CHAPTER_10_LEVELS: list[Level] = [
    LEVEL_Q10_1, LEVEL_Q10_2, LEVEL_Q10_3, LEVEL_Q10_4, LEVEL_Q10_5,
]
