"""Chapter 13: DaemonSet（守护进程集）（5 关）

Q13.1 创建第一个 DaemonSet
Q13.2 DaemonSet 节点选择器
Q13.3 DaemonSet 滚动更新
Q13.4 DaemonSet vs Deployment 对比
Q13.5 集群实战 - 部署日志采集 DaemonSet (Fluent Bit)
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q13.1 创建第一个 DaemonSet ====================

def _check_131_create_daemonset(user_yaml: str) -> CheckResult:
    """Q13.1 创建一个在每个节点上运行 Pod 的 DaemonSet"""
    try:
        state = ClusterState()
        # 预置 3 个节点
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-a
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-b
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-c
  labels:
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.daemonsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 DaemonSet",
            hints=["你需要 apply 一个 kind: DaemonSet 的 YAML 🛡️"],
        )

    ds_name = next(iter(state.daemonsets))
    ds = state.daemonsets[ds_name]
    spec = ds.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec.containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    if not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["spec.template.spec.containers[0].image 必须指定 📦"],
        )

    if not c.get("name"):
        return CheckResult(
            ok=False,
            error="容器缺少 name",
            hints=["spec.template.spec.containers[0].name 必须指定"],
        )

    # 验证为每个 Node 创建了 Pod
    ds_pods = [pn for pn, p in state.pods.items()
               if isinstance(p.get("metadata", {}).get("labels", {}), dict)
               and p["metadata"]["labels"].get("daemonset") == ds_name]
    if len(ds_pods) < 3:
        return CheckResult(
            ok=False,
            error=f"DaemonSet '{ds_name}' 应在 3 个节点上各创建一个 Pod，实际创建了 {len(ds_pods)} 个",
            hints=["DaemonSet 会自动在每个节点上运行一个 Pod 副本 🔄"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！DaemonSet 确保每个节点都运行一个 Pod 副本 🛡️"],
    )


LEVEL_Q13_1 = Level(
    id="Q13.1",
    chapter="ch13",
    title="创建第一个 DaemonSet",
    description="""
# 创建第一个 DaemonSet 🛡️

**DaemonSet** 确保所有（或某些）节点上运行一个 Pod 副本。当节点加入集群时，DaemonSet 会自动在新节点上创建 Pod；当节点移除时，Pod 会被回收。

## 任务

创建一个在每个节点上运行 `nginx:1.25` 的 DaemonSet：
- `kind: DaemonSet`
- `apiVersion: apps/v1`
- 容器使用 `nginx:1.25`

## 提示

DaemonSet 的结构与 Deployment 非常相似，但**不需要 replicas 字段**（它会自动在所有节点上运行）：
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        # image 在这里补全
""",
    check_fn=_check_131_create_daemonset,
    lesson=Lesson(
        concept="""\
## 什么是 DaemonSet？

**DaemonSet** 是 Kubernetes 中确保**每个节点上运行一个 Pod 副本**的工作负载控制器。它与 Deployment 的最大区别是：不需要指定 replicas 数量，它会自动在所有符合条件的节点上各部署一个 Pod。

### DaemonSet 的核心行为

1. **自动覆盖所有节点**：集群中有 N 个节点，就运行 N 个 Pod
2. **新节点自动部署**：当新节点加入集群时，自动在该节点上创建 Pod
3. **节点移除自动清理**：当节点从集群移除时，Pod 自动被回收
4. **无需 replicas**：与 Deployment 不同，DaemonSet 没有 replicas 字段

### 典型使用场景

- **日志采集**：Fluentd / Fluent Bit / Filebeat
- **监控代理**：Prometheus Node Exporter / cAdvisor
- **网络插件**：Calico / Flannel CNI
- **存储插件**：Ceph / GlusterFS 客户端
- **安全代理**：安全扫描 / 入侵检测

### DaemonSet vs Deployment

| 特性 | Deployment | DaemonSet |
|------|-----------|-----------|
| Pod 数量 | 由 replicas 控制 | 每节点一个 |
| 新节点行为 | 不受影响 | 自动部署 Pod |
| 典型场景 | Web 服务 | 系统级守护进程 |
| replicas 字段 | 需要 | 不需要 |
""",
        key_fields=[
            {"name": "spec.selector", "description": "标签选择器，匹配 Pod 模板的 labels", "required": True, "example": "matchLabels: {app: nginx}"},
            {"name": "spec.template", "description": "Pod 模板，定义每个节点上运行的 Pod", "required": True, "example": "template: { metadata: {...}, spec: {...} }"},
            {"name": "spec.template.spec.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
            {"name": "spec.template.spec.nodeSelector", "description": "节点选择器，限定 Pod 只在特定节点运行", "required": False, "example": "disktype: ssd"},
            {"name": "spec.updateStrategy", "description": "更新策略: RollingUpdate 或 OnDelete", "required": False, "example": "type: RollingUpdate"},
        ],
        diagram="""\
  DaemonSet (nginx-daemon)
  ┌─────────────────────────────────────┐
  │  spec:                              │
  │    selector:                        │
  │      matchLabels:                   │
  │        app: nginx                   │
  │    template:                        │
  │      metadata:                      │
  │        labels: {app: nginx}         │
  │      spec:                          │
  │        containers:                  │
  │        - name: nginx                │
  │          image: nginx:1.25          │
  └───────────────┬─────────────────────┘
                  │ 自动在每个节点部署
      ┌───────────┼───────────┐
      ▼           ▼           ▼
  ┌────────┐ ┌────────┐ ┌────────┐
  │ Node-A │ │ Node-B │ │ Node-C │
  │ Pod    │ │ Pod    │ │ Pod    │
  │ nginx  │ │ nginx  │ │ nginx  │
  └────────┘ └────────┘ └────────┘
  每个节点恰好一个 Pod 副本
""",
        example_yaml="""\
apiVersion: apps/v1            # DaemonSet API 版本
kind: DaemonSet               # 资源类型: DaemonSet
metadata:                     # 元数据
  name: nginx-daemon          # DaemonSet 名称
spec:                         # 规格定义
  selector:                   # 标签选择器
    matchLabels:
      app: nginx              # 必须与 template.labels 一致
  template:                   # Pod 模板
    metadata:
      labels:
        app: nginx
    spec:                     # Pod 规格
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.25     # 镜像
""",
        common_errors=[
            "忘记写 selector 或 selector 与 template.labels 不匹配",
            "误加了 replicas 字段（DaemonSet 不支持 replicas）",
            "apiVersion 写成了 extensions/v1beta1（已废弃，应使用 apps/v1）",
            "把 kind 写成了 DaemonSet 的缩写 DS（必须写完整 DaemonSet）",
        ],
        tips=[
            "用 kubectl get daemonsets 查看 DESIRED/CURRENT/READY 列确认 Pod 数量",
            "用 kubectl get pods -o wide 查看 Pod 分布在哪些节点上",
            "DaemonSet 不需要 replicas，Pod 数量 = 匹配的节点数量",
        ],
    ),
)


# ==================== Q13.2 DaemonSet 节点选择器 ====================

def _check_132_node_selector(user_yaml: str) -> CheckResult:
    """Q13.2 创建带有 nodeSelector 的 DaemonSet，只在 SSD 节点上运行"""
    try:
        state = ClusterState()
        # 预置 3 个节点：1 个 SSD，2 个 HDD
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-ssd-1
  labels:
    disktype: ssd
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-hdd-1
  labels:
    disktype: hdd
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-hdd-2
  labels:
    disktype: hdd
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.daemonsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 DaemonSet",
            hints=["你需要 apply 一个 kind: DaemonSet 的 YAML 🛡️"],
        )

    ds_name = next(iter(state.daemonsets))
    ds = state.daemonsets[ds_name]
    spec = ds.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec", hints=[])

    # 检查 nodeSelector
    node_selector = tmpl_spec.get("nodeSelector")
    if not isinstance(node_selector, dict) or not node_selector:
        return CheckResult(
            ok=False,
            error="DaemonSet 缺少 spec.template.spec.nodeSelector",
            hints=["添加 nodeSelector 来限定 Pod 只在特定节点上运行 🎯"],
        )

    if node_selector.get("disktype") != "ssd":
        return CheckResult(
            ok=False,
            error=f"nodeSelector.disktype 应为 'ssd'，实际为 '{node_selector.get('disktype')}'",
            hints=["设置 nodeSelector: { disktype: ssd } 来选择 SSD 节点"],
        )

    # 验证只在 SSD 节点上创建了 Pod
    ds_pods = [pn for pn, p in state.pods.items()
               if isinstance(p.get("metadata", {}).get("labels", {}), dict)
               and p["metadata"]["labels"].get("daemonset") == ds_name]
    if len(ds_pods) != 1:
        return CheckResult(
            ok=False,
            error=f"使用 nodeSelector disktype=ssd 后，应只在 1 个 SSD 节点上创建 Pod，实际创建了 {len(ds_pods)} 个",
            hints=["nodeSelector 会过滤目标节点，只有标签匹配的节点才会运行 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["nodeSelector 生效！DaemonSet 只在 SSD 节点上部署了 Pod 🎯"],
    )


LEVEL_Q13_2 = Level(
    id="Q13.2",
    chapter="ch13",
    title="DaemonSet 节点选择器",
    description="""
# DaemonSet 节点选择器 🎯

有时你不想在**所有**节点上运行 DaemonSet，而是只在特定节点上运行。使用 `nodeSelector` 可以实现这一点。

## 任务

集群中有 3 个节点：1 个 SSD（`disktype: ssd`）和 2 个 HDD（`disktype: hdd`）。

创建一个 DaemonSet，**只在 SSD 节点上运行**：
- `kind: DaemonSet`
- 容器使用 `nginx:1.25`
- 在 Pod 模板中添加 `nodeSelector: { disktype: ssd }`

## 提示

nodeSelector 写在 Pod 模板的 spec 中：
```yaml
spec:
  template:
    spec:
      nodeSelector:
        disktype: ssd
      containers:
      - name: nginx
        image: nginx:1.25
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ssd-monitor
spec:
  selector:
    matchLabels:
      app: ssd-monitor
  template:
    metadata:
      labels:
        app: ssd-monitor
    spec:
      # 在这里添加 nodeSelector
      containers:
      - name: nginx
        image: nginx:1.25
""",
    check_fn=_check_132_node_selector,
    lesson=Lesson(
        concept="""\
## DaemonSet 节点选择器

默认情况下，DaemonSet 会在**所有节点**上部署 Pod。但在实际场景中，你可能只需要在特定节点上运行：

- 只在 GPU 节点上运行 GPU 监控代理
- 只在 SSD 节点上运行磁盘性能监控
- 只在特定区域的节点上运行区域服务

### nodeSelector

`nodeSelector` 是最简单的节点选择方式。它指定一组 key-value，只有标签**全部匹配**的节点才会被选中。

```yaml
spec:
  template:
    spec:
      nodeSelector:
        disktype: ssd      # 只在有 disktype=ssd 标签的节点上运行
        gpu: "true"        # 且有 gpu=true 标签的节点
      containers:
      - name: app
        image: nginx
```

### nodeSelector 的工作流程

```
1. DaemonSet Controller 获取所有节点列表
2. 对每个节点，检查其 labels 是否匹配 nodeSelector
3. 在匹配的节点上创建 Pod
4. 不匹配的节点跳过
```

### nodeSelector vs nodeAffinity

| 特性 | nodeSelector | nodeAffinity |
|------|-------------|-------------|
| 复杂度 | 简单 | 复杂 |
| 操作符 | 仅等于 | In/NotIn/Exists/DoesNotExist/Gt/Lt |
| 软约束 | 不支持 | preferred（尽量满足） |
| 推荐度 | 简单场景 | 复杂调度需求 |
""",
        key_fields=[
            {"name": "spec.template.spec.nodeSelector", "description": "节点选择器，key-value 必须全部匹配节点标签", "required": True, "example": "disktype: ssd"},
            {"name": "spec.selector", "description": "DaemonSet 的标签选择器", "required": True, "example": "matchLabels: {app: ssd-monitor}"},
            {"name": "spec.template", "description": "Pod 模板", "required": True, "example": "..."},
        ],
        diagram="""\
  集群节点:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  node-ssd-1  │  │  node-hdd-1  │  │  node-hdd-2  │
  │  disktype:   │  │  disktype:   │  │  disktype:   │
  │    ssd  ✓    │  │    hdd  ✗    │  │    hdd  ✗    │
  └──────┬───────┘  └──────────────┘  └──────────────┘
         │
         ▼  nodeSelector: {disktype: ssd}

  DaemonSet Pod 只部署在匹配节点:
  ┌──────────────┐
  │  node-ssd-1  │
  │  ┌────────┐  │
  │  │  Pod   │  │  ← 唯一匹配的节点
  │  │ nginx  │  │
  │  └────────┘  │
  └──────────────┘
""",
        example_yaml="""\
apiVersion: apps/v1            # DaemonSet API 版本
kind: DaemonSet               # 资源类型
metadata:                     # 元数据
  name: ssd-monitor           # DaemonSet 名称
spec:                         # 规格定义
  selector:                   # 标签选择器
    matchLabels:
      app: ssd-monitor
  template:                   # Pod 模板
    metadata:
      labels:
        app: ssd-monitor
    spec:                     # Pod 规格
      nodeSelector:           # 节点选择器
        disktype: ssd         # 只在 SSD 节点上运行
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.25     # 镜像
""",
        common_errors=[
            "nodeSelector 写在了 spec 下而不是 spec.template.spec 下",
            "nodeSelector 的值写成数字而不是字符串（YAML 中 ssd 不需要引号，但 true/false 需要）",
            "忘记先给节点打标签（kubectl label node <name> disktype=ssd）",
            "selector.matchLabels 和 template.metadata.labels 不一致导致 DaemonSet 无法创建",
        ],
        tips=[
            "用 kubectl get nodes --show-labels 查看节点标签",
            "用 kubectl label node <name> <key>=<value> 给节点打标签",
            "nodeSelector 是硬约束，不匹配的节点绝对不会运行 Pod",
        ],
    ),
)


# ==================== Q13.3 DaemonSet 滚动更新 ====================

def _check_133_rolling_update(user_yaml: str) -> CheckResult:
    """Q13.3 创建带有 RollingUpdate 策略的 DaemonSet"""
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-a
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-b
  labels:
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.daemonsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 DaemonSet",
            hints=["你需要 apply 一个 kind: DaemonSet 的 YAML 🛡️"],
        )

    ds_name = next(iter(state.daemonsets))
    ds = state.daemonsets[ds_name]
    spec = ds.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec", hints=[])

    # 检查 updateStrategy
    update_strategy = spec.get("updateStrategy")
    if not isinstance(update_strategy, dict):
        return CheckResult(
            ok=False,
            error="DaemonSet 缺少 spec.updateStrategy",
            hints=["添加 spec.updateStrategy 来配置更新策略 🔄"],
        )

    strategy_type = update_strategy.get("type")
    if strategy_type != "RollingUpdate":
        return CheckResult(
            ok=False,
            error=f"updateStrategy.type 应为 'RollingUpdate'，实际为 '{strategy_type}'",
            hints=["设置 spec.updateStrategy.type: RollingUpdate"],
        )

    # 检查 rollingUpdate 配置
    rolling_update = update_strategy.get("rollingUpdate")
    if not isinstance(rolling_update, dict):
        return CheckResult(
            ok=False,
            error="缺少 spec.updateStrategy.rollingUpdate 配置",
            hints=["添加 rollingUpdate 配置: maxUnavailable 等"],
        )

    if "maxUnavailable" not in rolling_update:
        return CheckResult(
            ok=False,
            error="缺少 spec.updateStrategy.rollingUpdate.maxUnavailable",
            hints=["设置 maxUnavailable 来控制每次更新的最大不可用 Pod 数"],
        )

    # 验证容器配置
    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="DaemonSet 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict) or not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["spec.template.spec.containers[0].image 必须指定 📦"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["RollingUpdate 策略配置正确！更新时 Pod 会逐个滚动更新 🔄"],
    )


LEVEL_Q13_3 = Level(
    id="Q13.3",
    chapter="ch13",
    title="DaemonSet 滚动更新",
    description="""
# DaemonSet 滚动更新 🔄

当 DaemonSet 的 Pod 模板更新时（如镜像版本升级），可以使用 `updateStrategy` 控制更新行为。

## 任务

创建一个带有 `RollingUpdate` 策略的 DaemonSet：
- `kind: DaemonSet`
- `spec.updateStrategy.type: RollingUpdate`
- `spec.updateStrategy.rollingUpdate.maxUnavailable: 1`
- 容器使用 `nginx:1.26`

## 提示

DaemonSet 的更新策略有两种：
- `RollingUpdate`（默认）：自动滚动更新，逐个替换 Pod
- `OnDelete`：手动删除 Pod 后才会创建新版本

```yaml
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon-v2
spec:
  selector:
    matchLabels:
      app: nginx
  # 在这里添加 updateStrategy
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.26
""",
    check_fn=_check_133_rolling_update,
    lesson=Lesson(
        concept="""\
## DaemonSet 滚动更新

当更新 DaemonSet 的 Pod 模板（如升级镜像版本）时，`updateStrategy` 决定如何将旧版本 Pod 替换为新版本。

### 两种更新策略

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| **RollingUpdate**（默认） | 自动滚动更新，逐个替换旧 Pod | 大多数场景 |
| **OnDelete** | 手动删除旧 Pod 后才创建新 Pod | 需要精细控制更新时机 |

### RollingUpdate 参数

```yaml
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1      # 每次最多不可用的 Pod 数量
      maxSurge: 0            # 每次最多超出期望数量的 Pod（DaemonSet 默认 0）
```

- **maxUnavailable**：可以是整数或百分比。设为 1 表示每次最多有 1 个节点上的 Pod 不可用。
- **maxSurge**：DaemonSet 通常为 0（因为每个节点最多一个 Pod，无法超出）。

### 更新流程

```
3 个节点，maxUnavailable: 1

Step 1: Node-A 旧 Pod 终止 → 新 Pod 创建
        Node-B 旧 Pod 运行中
        Node-C 旧 Pod 运行中

Step 2: Node-A 新 Pod Ready
        Node-B 旧 Pod 终止 → 新 Pod 创建
        Node-C 旧 Pod 运行中

Step 3: Node-B 新 Pod Ready
        Node-C 旧 Pod 终止 → 新 Pod 创建

Step 4: 所有节点更新完成 ✓
```

### 与 Deployment 滚动更新的区别

| 特性 | Deployment | DaemonSet |
|------|-----------|-----------|
| maxUnavailable | 控制 Pod 数量 | 控制节点数 |
| maxSurge | 可以 > 0 | 通常为 0 |
| 更新单位 | Pod | 节点上的 Pod |
""",
        key_fields=[
            {"name": "spec.updateStrategy.type", "description": "更新策略: RollingUpdate 或 OnDelete", "required": True, "example": "RollingUpdate"},
            {"name": "spec.updateStrategy.rollingUpdate.maxUnavailable", "description": "更新时最大不可用 Pod 数（整数或百分比）", "required": True, "example": "1"},
            {"name": "spec.updateStrategy.rollingUpdate.maxSurge", "description": "更新时最大超出 Pod 数（通常为 0）", "required": False, "example": "0"},
        ],
        diagram="""\
  DaemonSet 滚动更新 (maxUnavailable: 1)

  时间轴:
  ┌─────────┬─────────┬─────────┬─────────┐
  │  Step 1  │  Step 2  │  Step 3  │  Done   │
  ├─────────┼─────────┼─────────┼─────────┤
  │ Node-A   │ Node-A   │ Node-A   │ Node-A   │
  │ v1→v2 🔄 │ v2 ✓     │ v2 ✓     │ v2 ✓     │
  ├─────────┼─────────┼─────────┼─────────┤
  │ Node-B   │ Node-B   │ Node-B   │ Node-B   │
  │ v1 ✓     │ v1→v2 🔄 │ v2 ✓     │ v2 ✓     │
  ├─────────┼─────────┼─────────┼─────────┤
  │ Node-C   │ Node-C   │ Node-C   │ Node-C   │
  │ v1 ✓     │ v1 ✓     │ v1→v2 🔄 │ v2 ✓     │
  └─────────┴─────────┴─────────┴─────────┘

  每次只有 1 个节点在更新 (maxUnavailable: 1)
""",
        example_yaml="""\
apiVersion: apps/v1            # DaemonSet API 版本
kind: DaemonSet               # 资源类型
metadata:                     # 元数据
  name: nginx-daemon-v2       # DaemonSet 名称
spec:                         # 规格定义
  selector:                   # 标签选择器
    matchLabels:
      app: nginx
  updateStrategy:             # 更新策略
    type: RollingUpdate       # 滚动更新
    rollingUpdate:
      maxUnavailable: 1       # 每次最多 1 个不可用
  template:                   # Pod 模板
    metadata:
      labels:
        app: nginx
    spec:                     # Pod 规格
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.26     # 新版本镜像
""",
        common_errors=[
            "updateStrategy 写在了 template 下面（应在 spec 下与 template 同级）",
            "maxUnavailable 设得过大导致多个节点同时不可用",
            "误以为 DaemonSet 支持 maxSurge > 0（每个节点最多一个 Pod，无法超出）",
            "把 type 写成了 rollingUpdate（应为 RollingUpdate，首字母大写）",
        ],
        tips=[
            "用 kubectl rollout status daemonset/<name> 查看滚动更新进度",
            "用 kubectl rollout history daemonset/<name> 查看更新历史",
            "maxUnavailable 设为 1 可以确保更新过程中大部分节点仍正常运行",
        ],
    ),
)


# ==================== Q13.4 DaemonSet vs Deployment 对比 ====================

def _check_134_daemonset_vs_deployment(user_yaml: str) -> CheckResult:
    """Q13.4 选择 DaemonSet 来部署节点监控代理"""
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-a
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-b
  labels:
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 场景：部署节点监控代理，应该用 DaemonSet 而非 Deployment
    if not state.daemonsets:
        # 检查是否误用了 Deployment
        if state.deployments:
            return CheckResult(
                ok=False,
                error="场景需要每个节点都运行监控代理，应该使用 DaemonSet 而非 Deployment",
                hints=[
                    "DaemonSet 确保每个节点都运行一个副本 🛡️",
                    "Deployment 无法保证 Pod 均匀分布到每个节点",
                    "把 kind 改为 DaemonSet 试试",
                ],
            )
        return CheckResult(
            ok=False,
            error="没有创建任何 DaemonSet",
            hints=["这个场景适合用 DaemonSet，试试 kind: DaemonSet 🛡️"],
        )

    ds_name = next(iter(state.daemonsets))
    ds = state.daemonsets[ds_name]
    spec = ds.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="DaemonSet 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    if not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["spec.template.spec.containers[0].image 必须指定 📦"],
        )

    # 检查是否设置了 hostNetwork（监控代理常用）
    # 不是必须的，但给出提示
    hints = ["正确选择！节点监控代理需要用 DaemonSet 确保每个节点都有副本 🎯"]
    if tmpl_spec.get("hostNetwork"):
        hints.append("你还设置了 hostNetwork，这是监控代理的常见配置 👍")

    return CheckResult(ok=True, state=state, hints=hints)


LEVEL_Q13_4 = Level(
    id="Q13.4",
    chapter="ch13",
    title="DaemonSet vs Deployment",
    description="""
# DaemonSet vs Deployment 对比 🤔

你需要部署一个**节点监控代理**（如 Node Exporter），它需要在**每个节点**上运行来采集节点指标。

## 任务

选择合适的工作负载类型，部署一个节点监控代理：
- 思考：应该用 Deployment 还是 DaemonSet？
- 容器使用 `prom/node-exporter:latest`
- 确保每个节点都运行一个副本

## 思考要点

- 监控代理需要采集**每个节点**的指标（CPU、内存、磁盘）
- 新节点加入集群时，监控代理应自动部署
- 不需要指定副本数量，节点数 = Pod 数

## 提示

💡 如果你需要"每个节点都跑一个"，DaemonSet 是正确选择。
Deployment 无法保证 Pod 均匀分布到所有节点。
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: # 选择正确的 kind: DaemonSet 还是 Deployment?
metadata:
  name: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
""",
    check_fn=_check_134_daemonset_vs_deployment,
    lesson=Lesson(
        concept="""\
## DaemonSet vs Deployment：何时用哪个？

选择正确的工作负载类型是 K8s 设计的关键决策。

### 核心区别

| 维度 | Deployment | DaemonSet |
|------|-----------|-----------|
| **Pod 分布** | 随机调度，可能集中在少数节点 | 每个节点恰好一个 |
| **Pod 数量** | 由 replicas 控制 | 由节点数决定 |
| **新节点** | 不自动部署 | 自动部署 |
| **节点移除** | Pod 可能被重新调度到其他节点 | Pod 自动回收 |
| **使用场景** | 无状态应用（Web/API） | 节点级守护进程 |

### 决策流程图

```
你的应用需要运行在每个节点上吗？
├── 是 ──> DaemonSet
│         （日志采集、监控代理、网络插件）
└── 否 ──> 需要控制副本数量吗？
          ├── 是 ──> Deployment
          │         （Web 服务、API 服务）
          └── 否 ──> 需要稳定身份吗？
                    ├── 是 ──> StatefulSet
                    └── 否 ──> 裸 Pod（不推荐生产使用）
```

### 常见场景对照

| 场景 | 推荐类型 | 原因 |
|------|---------|------|
| Web 前端服务 | Deployment | 需要弹性伸缩，不关心节点位置 |
| 日志采集 (Fluent Bit) | DaemonSet | 需要采集每个节点的日志 |
| 监控代理 (Node Exporter) | DaemonSet | 需要采集每个节点的指标 |
| 数据库 (MySQL) | StatefulSet | 需要稳定身份和持久化 |
| 定时备份 | CronJob | 定期执行，完成即退出 |
| GPU 训练任务 | Job | 一次性任务，运行完退出 |
| 网络插件 (Calico) | DaemonSet | 需要配置每个节点的网络 |

### hostNetwork 选项

节点级守护进程通常使用 `hostNetwork: true`，让 Pod 直接使用节点的网络命名空间：
```yaml
spec:
  template:
    spec:
      hostNetwork: true    # 直接使用节点网络
      containers:
      - name: agent
        image: prom/node-exporter
```
""",
        key_fields=[
            {"name": "kind", "description": "资源类型选择: DaemonSet 适合节点级服务", "required": True, "example": "DaemonSet"},
            {"name": "spec.template.spec.containers[].image", "description": "容器镜像", "required": True, "example": "prom/node-exporter:latest"},
            {"name": "spec.template.spec.hostNetwork", "description": "使用宿主机网络（监控代理常用）", "required": False, "example": "true"},
        ],
        diagram="""\
  决策树: 选择正确的工作负载

  ┌─────────────────────────┐
  │  需要每个节点都运行？    │
  └────────┬────────┬───────┘
           │是      │否
           ▼        ▼
     ┌──────────┐  ┌───────────────────┐
     │ DaemonSet │  │ 需要控制副本数？   │
     └──────────┘  └───────┬─────┬─────┘
                           │是   │否
                           ▼     ▼
                    ┌──────────┐ ┌──────────────┐
                    │Deployment│ │ 需要稳定身份？│
                    └──────────┘ └────┬────┬────┘
                                       │是  │否
                                       ▼    ▼
                                 ┌────────────┐
                                 │StatefulSet │
                                 └────────────┘

  节点监控场景:
  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ Node-A  │  │ Node-B  │  │ Node-C  │
  │ ┌─────┐ │  │ ┌─────┐ │  │ ┌─────┐ │
  │ │ Pod │ │  │ │ Pod │ │  │ │ Pod │ │
  │ │监控 │ │  │ │监控 │ │  │ │监控 │ │
  │ └─────┘ │  │ └─────┘ │  │ └─────┘ │
  └─────────┘  └─────────┘  └─────────┘
  DaemonSet: 每个节点一个监控 Pod
""",
        example_yaml="""\
apiVersion: apps/v1            # DaemonSet API 版本
kind: DaemonSet               # 节点级服务用 DaemonSet
metadata:                     # 元数据
  name: node-exporter         # DaemonSet 名称
spec:                         # 规格定义
  selector:                   # 标签选择器
    matchLabels:
      app: node-exporter
  template:                   # Pod 模板
    metadata:
      labels:
        app: node-exporter
    spec:                     # Pod 规格
      hostNetwork: true       # 使用宿主机网络（监控常用）
      containers:             # 容器列表
      - name: node-exporter   # 容器名
        image: prom/node-exporter:latest  # 镜像
        ports:                # 端口
        - containerPort: 9100 # 暴露端口
          hostPort: 9100      # 宿主机端口
""",
        common_errors=[
            "节点级服务用了 Deployment，导致部分节点没有监控覆盖",
            "在 DaemonSet 中设置了 replicas（DaemonSet 不支持 replicas）",
            "忘记考虑新节点加入集群时的自动部署需求",
            "用 Deployment + nodeSelector 模拟 DaemonSet（过于复杂且不可靠）",
        ],
        tips=[
            "问自己：'新节点加入集群时，这个应用需要自动部署吗？' 如果是，用 DaemonSet",
            "用 kubectl get ds -A 查看所有命名空间的 DaemonSet",
            "hostNetwork: true 可以减少网络开销，适合监控/网络代理类应用",
        ],
    ),
)


# ==================== Q13.5 集群实战 - 部署日志采集 DaemonSet ====================

def _check_135_fluent_bit(user_yaml: str) -> CheckResult:
    """Q13.5 集群实战 - 部署 Fluent Bit 日志采集 DaemonSet"""
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-a
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-b
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-c
  labels:
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.daemonsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 DaemonSet",
            hints=["你需要 apply 一个 kind: DaemonSet 的 YAML 🛡️"],
        )

    ds_name = next(iter(state.daemonsets))
    ds = state.daemonsets[ds_name]
    spec = ds.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="DaemonSet 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查镜像（Fluent Bit 相关）
    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["使用 fluent/fluent-bit 镜像 📦"],
        )

    image_lower = image.lower()
    if "fluent" not in image_lower:
        return CheckResult(
            ok=False,
            error=f"镜像 '{image}' 不像是日志采集器，应使用 fluent/fluent-bit 或类似镜像",
            hints=["日志采集常用镜像: fluent/fluent-bit, fluent/fluentd, elastic/filebeat"],
        )

    # 检查 volumeMounts（日志采集需要挂载节点日志目录）
    volume_mounts = c.get("volumeMounts", [])
    if not isinstance(volume_mounts, list) or not volume_mounts:
        return CheckResult(
            ok=False,
            error="Fluent Bit 容器缺少 volumeMounts",
            hints=["日志采集需要挂载节点的日志目录: /var/log 和 /var/lib/docker/containers 📁"],
        )

    # 检查是否有挂载 /var/log
    mount_paths = [vm.get("mountPath", "") for vm in volume_mounts if isinstance(vm, dict)]
    has_var_log = any("/var/log" in str(p) for p in mount_paths)
    if not has_var_log:
        return CheckResult(
            ok=False,
            error="缺少挂载 /var/log 目录",
            hints=["日志采集需要读取节点 /var/log 目录下的日志文件 📁"],
        )

    # 检查 volumes
    volumes = tmpl_spec.get("volumes", [])
    if not isinstance(volumes, list) or not volumes:
        return CheckResult(
            ok=False,
            error="DaemonSet 缺少 spec.template.spec.volumes",
            hints=["定义 volumes 来挂载节点的日志目录"],
        )

    # 验证为每个节点创建了 Pod
    ds_pods = [pn for pn, p in state.pods.items()
               if isinstance(p.get("metadata", {}).get("labels", {}), dict)
               and p["metadata"]["labels"].get("daemonset") == ds_name]
    if len(ds_pods) < 3:
        return CheckResult(
            ok=False,
            error=f"应在 3 个节点上各创建一个 Pod，实际创建了 {len(ds_pods)} 个",
            hints=["DaemonSet 会自动在每个节点上运行一个 Pod 🔄"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f fluent-bit.yaml",
            "  kubectl get ds -n kube-system",
            "  kubectl logs -n kube-system <pod-name>",
            "  kubectl get pods -o wide  # 确认每个节点都有 Pod",
        ],
    )


LEVEL_Q13_5 = Level(
    id="Q13.5",
    chapter="ch13",
    title="集群实战: 部署日志采集 DaemonSet",
    description="""
# 集群实战: 部署日志采集 DaemonSet 🏗️

Fluent Bit 是一个轻量级日志处理器和转发器。在 K8s 中，通常以 DaemonSet 方式部署，确保每个节点上的容器日志都能被采集。

## 任务

部署一个 Fluent Bit 日志采集 DaemonSet：
- `kind: DaemonSet`
- 容器使用 `fluent/fluent-bit:3.0`
- 挂载节点的 `/var/log` 目录
- 挂载容器的日志目录 `/var/lib/docker/containers`

## 验证步骤

```bash
# 1. 部署 DaemonSet
kubectl apply -f fluent-bit.yaml

# 2. 查看 DaemonSet 状态
kubectl get ds

# 3. 确认每个节点都有 Pod
kubectl get pods -o wide

# 4. 查看 Fluent Bit 日志
kubectl logs <pod-name>
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:3.0
        # 补全 volumeMounts: 挂载 /var/log 和 /var/lib/docker/containers
      # 补全 volumes: 使用 hostPath 挂载节点日志目录
""",
    check_fn=_check_135_fluent_bit,
    lesson=Lesson(
        concept="""\
## 日志采集 DaemonSet 实战

在生产环境中，日志采集是 DaemonSet 最经典的使用场景。Fluent Bit、Fluentd、Filebeat 等日志采集器都以 DaemonSet 方式部署。

### 为什么用 DaemonSet？

1. **全节点覆盖**：每个节点上的容器日志都能被采集
2. **自动扩展**：新节点加入集群时自动部署采集器
3. **资源效率**：每个节点一个采集器，避免跨节点传输日志
4. **本地读取**：采集器直接读取节点日志文件，无需远程调用

### Fluent Bit 架构

```
┌──────────── 节点 ────────────┐
│  容器 A    容器 B    容器 C   │
│    │        │        │       │
│    ▼        ▼        ▼       │
│  /var/log/containers/*       │  ← 容器日志文件
│    │                         │
│    ▼                         │
│  ┌─────────────────────┐    │
│  │   Fluent Bit Pod     │    │  ← DaemonSet 部署
│  │   (读取 + 解析 + 转发) │    │
│  └──────────┬──────────┘    │
│             │                │
└─────────────┼────────────────┘
              │ 转发日志
              ▼
    ┌───────────────────┐
    │  Elasticsearch /   │
    │  Loki / Kafka      │
    └───────────────────┘
```

### 关键配置项

1. **hostPath 卷**：挂载节点的日志目录
   - `/var/log` — 系统日志
   - `/var/lib/docker/containers` — Docker 容器日志

2. **volumeMounts**：将 hostPath 卷挂载到容器内

3. ** tolerations**：容忍 master 节点的污点，确保所有节点都部署

4. **resources**：限制采集器资源使用，避免影响业务 Pod
""",
        key_fields=[
            {"name": "spec.template.spec.containers[].image", "description": "日志采集器镜像", "required": True, "example": "fluent/fluent-bit:3.0"},
            {"name": "spec.template.spec.volumes", "description": "挂载节点的日志目录（hostPath）", "required": True, "example": "[{name: varlog, hostPath: {path: /var/log}}]"},
            {"name": "spec.template.spec.containers[].volumeMounts", "description": "将卷挂载到容器内", "required": True, "example": "[{name: varlog, mountPath: /var/log}]"},
            {"name": "spec.template.spec.tolerations", "description": "容忍污点，确保所有节点都部署", "required": False, "example": "[{operator: Exists}]"},
        ],
        diagram="""\
  Fluent Bit DaemonSet 部署架构

  ┌──── Node-A ────┐  ┌──── Node-B ────┐  ┌──── Node-C ────┐
  │ /var/log       │  │ /var/log       │  │ /var/log       │
  │ /var/lib/      │  │ /var/lib/      │  │ /var/lib/      │
  │  docker/...    │  │  docker/...    │  │  docker/...    │
  │     │          │  │     │          │  │     │          │
  │     ▼          │  │     ▼          │  │     ▼          │
  │ ┌────────────┐ │  │ ┌────────────┐ │  │ ┌────────────┐ │
  │ │ Fluent Bit │ │  │ │ Fluent Bit │ │  │ │ Fluent Bit │ │
  │ │   Pod      │ │  │ │   Pod      │ │  │ │   Pod      │ │
  │ │ (DaemonSet)│ │  │ │ (DaemonSet)│ │  │ │ (DaemonSet)│ │
  │ └─────┬──────┘ │  │ └─────┬──────┘ │  │ └─────┬──────┘ │
  └───────┼────────┘  └───────┼────────┘  └───────┼────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                   ┌────────────────────┐
                   │  日志后端           │
                   │  (ES/Loki/Kafka)   │
                   └────────────────────┘
""",
        example_yaml="""\
apiVersion: apps/v1            # DaemonSet API 版本
kind: DaemonSet               # 资源类型
metadata:                     # 元数据
  name: fluent-bit            # DaemonSet 名称
  namespace: kube-system      # 部署到 kube-system 命名空间
spec:                         # 规格定义
  selector:                   # 标签选择器
    matchLabels:
      app: fluent-bit
  template:                   # Pod 模板
    metadata:
      labels:
        app: fluent-bit
    spec:                     # Pod 规格
      containers:             # 容器列表
      - name: fluent-bit      # 容器名
        image: fluent/fluent-bit:3.0  # 镜像
        volumeMounts:         # 卷挂载
        - name: varlog        # 挂载系统日志
          mountPath: /var/log
          readOnly: true
        - name: varlibdockercontainers  # 挂载容器日志
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:                # 卷定义
      - name: varlog          # 系统日志目录
        hostPath:
          path: /var/log
      - name: varlibdockercontainers  # 容器日志目录
        hostPath:
          path: /var/lib/docker/containers
""",
        common_errors=[
            "忘记挂载节点的日志目录，导致采集器读不到日志",
            "hostPath 路径写错（/var/log 不是 /var/logs）",
            "没有设置 readOnly: true，采集器意外修改了日志文件",
            "没有配置 tolerations，master 节点上没有部署采集器",
            "资源限制设置过高，影响业务 Pod 的调度",
        ],
        tips=[
            "用 kubectl get ds -n kube-system 查看 DaemonSet 的 DESIRED/CURRENT 数量",
            "用 kubectl logs -n kube-system <pod> 确认 Fluent Bit 正常运行",
            "生产环境中建议添加 resources.requests/limits 限制采集器资源",
            "添加 tolerations 确保所有节点（包括 master）都部署采集器",
        ],
    ),
)


CHAPTER_13_LEVELS: list[Level] = [
    LEVEL_Q13_1, LEVEL_Q13_2, LEVEL_Q13_3, LEVEL_Q13_4, LEVEL_Q13_5,
]
