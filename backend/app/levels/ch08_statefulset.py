"""Chapter 8: StatefulSet（有状态应用）（5 关）

Q8.1 创建 StatefulSet
Q8.2 StatefulSet 扩缩容
Q8.3 Headless Service + StatefulSet
Q8.4 StatefulSet 持久化
Q8.5 集群实战 - 部署 MySQL StatefulSet
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q8.1 创建 StatefulSet ====================

def _check_81_create_statefulset(user_yaml: str) -> CheckResult:
    """Q8.1 创建 3 副本 StatefulSet"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.statefulsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 StatefulSet",
            hints=["你需要 apply 一个 kind: StatefulSet 的 YAML"],
        )

    sts_name = next(iter(state.statefulsets))
    sts = state.statefulsets[sts_name]
    spec = sts.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="StatefulSet 缺少 spec", hints=[])

    # 检查 replicas
    replicas = spec.get("replicas", 1)
    if replicas != 3:
        return CheckResult(
            ok=False,
            error=f"spec.replicas 应为 3，实际为 {replicas}",
            hints=["设置 spec.replicas: 3"],
        )

    # 检查 serviceName
    service_name = spec.get("serviceName", "")
    if not service_name:
        return CheckResult(
            ok=False,
            error="StatefulSet 缺少 spec.serviceName",
            hints=["spec.serviceName 指定关联的 Headless Service 名称"],
        )

    # 检查 template
    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="StatefulSet 缺少 spec.template", hints=[])

    # 验证有序 Pod 存在 (name-0, name-1, name-2)
    expected_pods = [f"{sts_name}-{i}" for i in range(3)]
    missing_pods = [p for p in expected_pods if p not in state.pods]

    if missing_pods:
        return CheckResult(
            ok=False,
            error=f"缺少有序 Pod: {missing_pods}，当前 Pod: {list(state.pods.keys())}",
            hints=["StatefulSet 应创建有序命名的 Pod: name-0, name-1, name-2"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["StatefulSet 创建的 Pod 有稳定的网络标识和有序的命名 🏗️"],
    )


LEVEL_Q8_1 = Level(
    id="Q8.1",
    chapter="ch08",
    title="创建 StatefulSet",
    description="""
# 创建 StatefulSet 🏗️

**StatefulSet** 用于管理**有状态应用**。与 Deployment 不同，它为每个 Pod 提供稳定的、有序的标识（名称、网络、存储）。

## 任务

创建一个 3 副本的 StatefulSet：
- `kind: StatefulSet`
- `spec.replicas: 3`
- `spec.serviceName: web`（关联的 Headless Service 名称）
- 容器使用 `nginx:1.25`

## 提示

StatefulSet 与 Deployment 的关键区别：
- 必须指定 `spec.serviceName`（关联 Headless Service）
- Pod 命名有序：`web-0`, `web-1`, `web-2`（而非随机后缀）
- Pod 创建/删除是**有序**的（0→1→2 创建，2→1→0 删除）
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  # replicas: 3
  # serviceName: web
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
""",
    check_fn=_check_81_create_statefulset,
    lesson=Lesson(
        concept="""\
## 什么是 StatefulSet？

**StatefulSet** 是 Kubernetes 中管理**有状态应用**的工作负载控制器。与 Deployment 管理无状态应用不同，StatefulSet 为每个 Pod 提供：

1. **稳定的网络标识**：Pod 名字有序且固定（web-0, web-1, web-2）
2. **稳定的持久化存储**：每个 Pod 绑定独立的 PVC，不会因 Pod 重建而丢失
3. **有序的部署和扩缩容**：Pod 按 0→1→2 顺序创建，按 2→1→0 顺序删除

### StatefulSet vs Deployment

| 特性 | Deployment | StatefulSet |
|------|-----------|-------------|
| Pod 命名 | 随机后缀 (web-abc123) | 有序编号 (web-0, web-1) |
| Pod 身份 | 可替换，无个体差异 | 每个有独立身份 |
| 存储 | 共享或无 | 每个 Pod 独立 PVC |
| 创建顺序 | 并行 | 顺序（0→1→2） |
| 删除顺序 | 并行 | 逆序（2→1→0） |
| 典型场景 | Web 服务 | 数据库、消息队列 |

### Pod 的稳定网络标识

StatefulSet 的 Pod 配合 Headless Service 可以获得稳定的 DNS 名称：
```
<pod-name>.<service-name>.<namespace>.svc.cluster.local
例如: web-0.web.default.svc.cluster.local
```

即使 Pod 重建，新 Pod 仍会获得相同的名字和 DNS 记录。

### 必须指定 serviceName

StatefulSet 的 `spec.serviceName` 字段是**必填**的，它指向一个已存在的 Headless Service，用于为 Pod 提供稳定 DNS。
""",
        key_fields=[
            {"name": "spec.replicas", "description": "副本数量", "required": True, "example": "3"},
            {"name": "spec.serviceName", "description": "关联的 Headless Service 名称（必填）", "required": True, "example": "web"},
            {"name": "spec.selector.matchLabels", "description": "标签选择器，匹配 Pod 模板标签", "required": True, "example": "{app: web}"},
            {"name": "spec.template", "description": "Pod 模板", "required": True, "example": "..."},
            {"name": "spec.volumeClaimTemplates", "description": "持久化存储模板（每个 Pod 独立 PVC）", "required": False, "example": "..."},
        ],
        diagram="""\
  StatefulSet (web) - replicas: 3

  ┌─────────────────────────────────────────┐
  │  StatefulSet                             │
  │  spec:                                   │
  │    serviceName: web   ◄── Headless Svc   │
  │    replicas: 3                           │
  │    template: ...                         │
  └──────────────────┬──────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ web-0  │  │ web-1  │  │ web-2  │  ← 有序命名
    │ nginx  │  │ nginx  │  │ nginx  │
    └────────┘  └────────┘  └────────┘
        │            │            │
        ▼            ▼            ▼
    web-0.web    web-1.web    web-2.web   ← 稳定 DNS
    (Headless Service 提供解析)
""",
        example_yaml="""\
apiVersion: apps/v1           # StatefulSet API 版本
kind: StatefulSet             # 资源类型
metadata:                     # 元数据
  name: web                   # StatefulSet 名称
spec:                         # 规格定义
  serviceName: web            # 关联的 Headless Service (必填)
  replicas: 3                 # 3 个副本
  selector:                   # 标签选择器
    matchLabels:              # 必须与 template labels 匹配
      app: web
  template:                   # Pod 模板
    metadata:                 # Pod 元数据
      labels:                 # Pod 标签
        app: web
    spec:                     # Pod 规格
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.25     # 镜像
        ports:                # 端口
        - containerPort: 80
""",
        common_errors=[
            "忘记写 spec.serviceName（StatefulSet 必填字段，指向 Headless Service）",
            "selector.matchLabels 与 template.labels 不匹配",
            "把 StatefulSet 当 Deployment 用（无状态应用不需要 StatefulSet）",
            "apiVersion 写成了 v1 而非 apps/v1",
        ],
        tips=[
            "用 kubectl get statefulsets 查看 StatefulSet 状态",
            "用 kubectl get pods -l app=web -w 观察有序创建过程",
            "StatefulSet 的 Pod 创建是顺序的：web-0 完成后才会创建 web-1",
        ],
    ),
)


# ==================== Q8.2 StatefulSet 扩缩容 ====================

def _check_82_scale_statefulset(user_yaml: str) -> CheckResult:
    """Q8.2 预置 3 副本 StatefulSet，扩容到 5"""
    try:
        state = ClusterState()
        # 预置 3 副本 StatefulSet
        state = preset_state(state, """\
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
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
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.statefulsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 StatefulSet",
            hints=["你需要 apply 一个 kind: StatefulSet 的 YAML"],
        )

    sts_name = next(iter(state.statefulsets))
    sts = state.statefulsets[sts_name]
    spec = sts.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="StatefulSet 缺少 spec", hints=[])

    replicas = spec.get("replicas", 1)
    if replicas != 5:
        return CheckResult(
            ok=False,
            error=f"spec.replicas 应为 5（扩容后），实际为 {replicas}",
            hints=["将 spec.replicas 从 3 改为 5"],
        )

    # 验证有 5 个 Pod
    sts_pods = [name for name in state.pods if name.startswith(f"{sts_name}-")]
    if len(sts_pods) != 5:
        return CheckResult(
            ok=False,
            error=f"期望 5 个 Pod，实际有 {len(sts_pods)} 个: {sts_pods}",
            hints=["扩容后应创建 5 个有序 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["StatefulSet 扩容是顺序的：web-3 → web-4 依次创建 📈"],
    )


LEVEL_Q8_2 = Level(
    id="Q8.2",
    chapter="ch08",
    title="StatefulSet 扩缩容",
    description="""
# StatefulSet 扩缩容 📈

集群中已有一个 3 副本的 StatefulSet（web-0, web-1, web-2）。现在需要扩容到 5 副本。

## 任务

编写 StatefulSet YAML，将 `replicas` 设为 5：
- `kind: StatefulSet`
- 名字保持 `web`
- `spec.replicas: 5`
- 其他字段与原有配置一致

## 提示

扩容时 StatefulSet 会**按顺序**创建新 Pod：
```
已有: web-0  web-1  web-2
扩容: web-3 (先) → web-4 (后)
```

缩容时则**逆序**删除：
```
缩容: web-4 (先删) → web-3 (后删)
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
  # replicas: 5  # 扩容到 5
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
""",
    check_fn=_check_82_scale_statefulset,
    lesson=Lesson(
        concept="""\
## StatefulSet 扩缩容

StatefulSet 的扩缩容与 Deployment 有本质区别：它是**有序的**。

### 扩容过程（3 → 5）

```
初始状态: web-0  web-1  web-2  (3 个 Pod)

步骤 1: 创建 web-3
  - 等待 web-3 Ready 后
  - 再创建 web-4

步骤 2: 创建 web-4
  - 等待 web-4 Ready
  - 扩容完成

最终状态: web-0  web-1  web-2  web-3  web-4  (5 个 Pod)
```

### 缩容过程（5 → 3）

```
初始状态: web-0  web-1  web-2  web-3  web-4

步骤 1: 删除 web-4 (逆序)
步骤 2: 删除 web-3

最终状态: web-0  web-1  web-2  (3 个 Pod)
```

### podManagementPolicy

- **`OrderedReady`**（默认）：严格顺序，一个 Ready 后才创建下一个
- **`Parallel`**：并行创建/删除所有 Pod（适合无严格顺序要求的场景）

### 为什么 StatefulSet 要有序？

1. **数据一致性**：数据库主从复制，需要先启动 master 再启动 slave
2. **选举机制**：如 ZooKeeper、etcd 需要有序初始化集群
3. **依赖关系**：后启动的 Pod 可能依赖先启动的 Pod 提供的服务

### PVC 与扩缩容

- 扩容时：为每个新 Pod 创建新的 PVC
- 缩容时：PVC **不会被自动删除**（数据保留）
- 再次扩容时：新 Pod 会绑定到之前的 PVC（数据恢复）
""",
        key_fields=[
            {"name": "spec.replicas", "description": "期望副本数", "required": True, "example": "5"},
            {"name": "spec.serviceName", "description": "Headless Service 名称", "required": True, "example": "web"},
            {"name": "spec.podManagementPolicy", "description": "Pod 管理策略: OrderedReady/Parallel", "required": False, "example": "OrderedReady"},
            {"name": "spec.updateStrategy", "description": "更新策略: RollingUpdate/OnDelete", "required": False, "example": "RollingUpdate"},
        ],
        diagram="""\
  StatefulSet 扩容 (3 → 5)

  扩容前 (replicas=3):
  ┌──────┐ ┌──────┐ ┌──────┐
  │web-0 │ │web-1 │ │web-2 │
  └──────┘ └──────┘ └──────┘

  修改 replicas=3 → replicas=5
            │
            ▼  有序创建
  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
  │web-0 │ │web-1 │ │web-2 │ │web-3 │ │web-4 │
  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
                               ↑       ↑
                           先创建   后创建

  缩容 (5 → 3):
  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
  │web-0 │ │web-1 │ │web-2 │ │web-3 │ │web-4 │
  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
                               ↑       ↑
                           后删除   先删除(逆序)
""",
        example_yaml="""\
apiVersion: apps/v1           # StatefulSet API 版本
kind: StatefulSet             # 资源类型
metadata:                     # 元数据
  name: web                   # 名称（与原有一致）
spec:                         # 规格定义
  serviceName: web            # Headless Service
  replicas: 5                 # 扩容到 5 副本
  selector:                   # 标签选择器
    matchLabels:
      app: web
  template:                   # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.25     # 镜像
        ports:
        - containerPort: 80
""",
        common_errors=[
            "扩容时 replicas 改了但 StatefulSet 名字与原来不一致（会被当作新资源）",
            "忘记写 serviceName 导致 apply 失败",
            "缩容后 PVC 不会删除，再次扩容时数据会恢复（不是全新 Pod）",
            "误以为扩容是并行的（默认 OrderedReady 是顺序的）",
        ],
        tips=[
            "用 kubectl scale statefulset web --replicas=5 快速扩缩容",
            "用 kubectl get pods -l app=web -w 观察有序创建过程",
            "缩容不会删除 PVC，保护数据不丢失",
        ],
    ),
)


# ==================== Q8.3 Headless Service + StatefulSet ====================

def _check_83_headless_service(user_yaml: str) -> CheckResult:
    """Q8.3 创建 Headless Service + StatefulSet 组合"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查有 Headless Service
    headless_svc = None
    for svc_name, svc in state.services.items():
        cluster_ip = svc.get("spec", {}).get("clusterIP")
        if cluster_ip == "None":
            headless_svc = svc_name
            break

    if not headless_svc:
        return CheckResult(
            ok=False,
            error="没有找到 Headless Service（clusterIP: None）",
            hints=["创建一个 Service，设置 spec.clusterIP: None"],
        )

    # 检查有 StatefulSet
    if not state.statefulsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 StatefulSet",
            hints=["创建一个 StatefulSet，spec.serviceName 指向 Headless Service"],
        )

    sts_name = next(iter(state.statefulsets))
    sts = state.statefulsets[sts_name]
    sts_spec = sts.get("spec", {})

    # 检查 serviceName 指向 Headless Service
    sts_service_name = sts_spec.get("serviceName", "")
    if sts_service_name != headless_svc:
        return CheckResult(
            ok=False,
            error=f"StatefulSet 的 serviceName '{sts_service_name}' 与 Headless Service '{headless_svc}' 不匹配",
            hints=["StatefulSet.spec.serviceName 必须指向 Headless Service 的名称"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Headless Service + StatefulSet 是有状态应用的标准组合 🔗"],
    )


LEVEL_Q8_3 = Level(
    id="Q8.3",
    chapter="ch08",
    title="Headless Service + StatefulSet",
    description="""
# Headless Service + StatefulSet 🔗

StatefulSet 必须配合 **Headless Service** 使用。Headless Service 不分配 ClusterIP，而是直接返回每个 Pod 的 DNS 记录，让客户端能直接访问特定 Pod。

## 任务

用多文档 YAML 创建 Headless Service + StatefulSet 组合：
1. **Headless Service**：`spec.clusterIP: None`，selector 匹配 Pod 标签
2. **StatefulSet**：`spec.serviceName` 指向 Headless Service

## 提示

用 `---` 分隔多个 YAML 文档：
```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None     # ← 这就是 Headless
  selector:
    app: nginx
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx
spec:
  serviceName: nginx  # ← 指向上面的 Service
  ...
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  # clusterIP: None  # Headless Service
  selector:
    app: nginx
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx
spec:
  serviceName: nginx
  replicas: 3
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
""",
    check_fn=_check_83_headless_service,
    lesson=Lesson(
        concept="""\
## Headless Service 与 StatefulSet 的关系

**Headless Service**（`clusterIP: None`）是 StatefulSet 的关键配套组件。它不提供负载均衡，而是直接暴露每个 Pod 的 DNS 记录。

### 普通 Service vs Headless Service

| 特性 | ClusterIP Service | Headless Service |
|------|-------------------|------------------|
| clusterIP | 自动分配 (如 10.96.x.x) | None |
| DNS 解析 | 返回 Service IP | 返回所有 Pod IP |
| 负载均衡 | kube-proxy 轮询 | 客户端自行选择 |
| 用途 | 无状态应用访问 | 有状态应用直接访问 Pod |

### DNS 解析对比

**普通 Service**：
```
nslookup nginx.default.svc.cluster.local
→ 10.96.0.10  (Service IP，负载均衡到随机 Pod)
```

**Headless Service**：
```
nslookup nginx.default.svc.cluster.local
→ 10.244.0.5  (web-0 的 IP)
→ 10.244.0.6  (web-1 的 IP)
→ 10.244.0.7  (web-2 的 IP)

# 还可以直接解析单个 Pod:
nslookup web-0.nginx.default.svc.cluster.local
→ 10.244.0.5  (web-0 的 IP)
```

### 为什么 StatefulSet 需要 Headless Service？

1. **稳定的 Pod DNS**：`web-0.nginx` 这个 DNS 名称永远指向 web-0 Pod
2. **直接访问特定副本**：数据库客户端可以连接到 master Pod
3. **Pod 间发现**：集群内的 Pod 可以通过 DNS 发现其他 Pod

### 典型架构

```
StatefulSet + Headless Service = 有状态应用标准架构

  Headless Service (nginx, clusterIP: None)
       │
       ├── web-0.nginx  → 10.244.0.5
       ├── web-1.nginx  → 10.244.0.6
       └── web-2.nginx  → 10.244.0.7
```
""",
        key_fields=[
            {"name": "spec.clusterIP", "description": "设为 None 即为 Headless Service", "required": True, "example": "None"},
            {"name": "spec.selector", "description": "选择 StatefulSet 创建的 Pod", "required": True, "example": "{app: nginx}"},
            {"name": "spec.serviceName", "description": "StatefulSet 中指向 Headless Service 名称", "required": True, "example": "nginx"},
            {"name": "spec.ports", "description": "Service 端口配置", "required": True, "example": "[{port: 80}]"},
        ],
        diagram="""\
  Headless Service + StatefulSet 架构

  ┌─────────────────────────────────────┐
  │  Headless Service (nginx)            │
  │  clusterIP: None                     │
  │  selector: {app: nginx}              │
  └───────────────┬─────────────────────┘
                  │ DNS 解析返回所有 Pod IP
     ┌────────────┼────────────┐
     ▼            ▼            ▼
  ┌────────┐  ┌────────┐  ┌────────┐
  │ web-0  │  │ web-1  │  │ web-2  │
  │nginx   │  │nginx   │  │nginx   │
  │10.244.5│  │10.244.6│  │10.244.7│
  └────────┘  └────────┘  └────────┘

  DNS 记录:
  ├── nginx.default.svc.cluster.local → [10.244.5, 10.244.6, 10.244.7]
  ├── web-0.nginx.default.svc.cluster.local → 10.244.5
  ├── web-1.nginx.default.svc.cluster.local → 10.244.6
  └── web-2.nginx.default.svc.cluster.local → 10.244.7
""",
        example_yaml="""\
# Headless Service                         # 无 ClusterIP 的 Service
apiVersion: v1                             # API 版本
kind: Service                              # 资源类型: Service
metadata:                                  # 元数据
  name: nginx                              # Service 名称
spec:                                      # 规格定义
  clusterIP: None                          # ← Headless: 不分配 ClusterIP
  selector:                                # 选择 Pod
    app: nginx
  ports:                                   # 端口配置
  - port: 80                               # Service 端口
    name: web
---                                        # 多文档分隔
apiVersion: apps/v1                        # StatefulSet API 版本
kind: StatefulSet                          # 资源类型
metadata:                                  # 元数据
  name: nginx                              # StatefulSet 名称
spec:                                      # 规格定义
  serviceName: nginx                       # ← 指向 Headless Service
  replicas: 3                              # 3 个副本
  selector:                                # 标签选择器
    matchLabels:
      app: nginx
  template:                                # Pod 模板
    metadata:
      labels:
        app: nginx
    spec:
      containers:                          # 容器列表
      - name: nginx                        # 容器名
        image: nginx:1.25                  # 镜像
        ports:
        - containerPort: 80
""",
        common_errors=[
            "忘记设 clusterIP: None，变成了普通 ClusterIP Service",
            "StatefulSet 的 serviceName 与 Service 名称不一致",
            "Service 的 selector 与 StatefulSet 的 Pod 标签不匹配",
            "只创建了 StatefulSet 没创建 Service（或反之）",
        ],
        tips=[
            "用 kubectl get svc 确认 clusterIP 列显示 None",
            "在 Pod 内用 nslookup <svc-name> 验证 Headless DNS 解析",
            "Headless Service 是 StatefulSet 的必要组件，不可省略",
        ],
    ),
)


# ==================== Q8.4 StatefulSet 持久化 ====================

def _check_84_persistent_storage(user_yaml: str) -> CheckResult:
    """Q8.4 创建带 volumeClaimTemplates 的 StatefulSet"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.statefulsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 StatefulSet",
            hints=["你需要 apply 一个 kind: StatefulSet 的 YAML"],
        )

    sts_name = next(iter(state.statefulsets))
    sts = state.statefulsets[sts_name]
    spec = sts.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="StatefulSet 缺少 spec", hints=[])

    vct = spec.get("volumeClaimTemplates")
    if not isinstance(vct, list) or not vct:
        return CheckResult(
            ok=False,
            error="StatefulSet 缺少 spec.volumeClaimTemplates",
            hints=["添加 volumeClaimTemplates 为每个 Pod 提供独立 PVC"],
        )

    # 检查 PVC 模板有 storage 请求
    pvc = vct[0]
    if not isinstance(pvc, dict):
        return CheckResult(ok=False, error="volumeClaimTemplates[0] 格式错误", hints=[])

    pvc_spec = pvc.get("spec", {})
    if not isinstance(pvc_spec, dict):
        return CheckResult(ok=False, error="PVC 模板缺少 spec", hints=[])

    resources = pvc_spec.get("resources", {})
    requests = resources.get("requests", {}) if isinstance(resources, dict) else {}
    if not requests.get("storage"):
        return CheckResult(
            ok=False,
            error="PVC 模板缺少 resources.requests.storage",
            hints=["在 volumeClaimTemplates 中设置 storage 请求量"],
        )

    # 检查 accessModes
    access_modes = pvc_spec.get("accessModes")
    if not isinstance(access_modes, list) or not access_modes:
        return CheckResult(
            ok=False,
            error="PVC 模板缺少 spec.accessModes",
            hints=["添加 accessModes: [ReadWriteOnce]"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["volumeClaimTemplates 为每个 Pod 创建独立 PVC，即使 Pod 重建数据也不丢失 💾"],
    )


LEVEL_Q8_4 = Level(
    id="Q8.4",
    chapter="ch08",
    title="StatefulSet 持久化",
    description="""
# StatefulSet 持久化 💾

StatefulSet 的核心优势之一：通过 `volumeClaimTemplates` 为**每个 Pod 自动创建独立的 PVC**，实现持久化存储。

## 任务

创建一个带 `volumeClaimTemplates` 的 StatefulSet：
- `kind: StatefulSet`
- `spec.volumeClaimTemplates` 中定义 PVC 模板
- 每个 Pod 有独立的 1Gi 存储
- 容器挂载该存储到 `/data`

## 提示

```yaml
spec:
  volumeClaimTemplates:
  - metadata:
      name: data        # PVC 模板名
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 1Gi
  template:
    spec:
      containers:
      - name: app
        volumeMounts:
        - name: data     # 引用 PVC 模板名
          mountPath: /data
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: data-app
spec:
  serviceName: data-app
  replicas: 3
  selector:
    matchLabels:
      app: data-app
  template:
    metadata:
      labels:
        app: data-app
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
        # volumeMounts: 挂载存储到 /data
  # volumeClaimTemplates: 定义 PVC 模板
""",
    check_fn=_check_84_persistent_storage,
    lesson=Lesson(
        concept="""\
## StatefulSet 持久化存储

StatefulSet 通过 `volumeClaimTemplates` 为每个 Pod 自动创建独立的 PVC（PersistentVolumeClaim），确保数据持久化。

### 每个 Pod 的独立 PVC

```
StatefulSet (data-app, replicas=3)
├── data-app-0 → PVC: data-data-app-0 (1Gi)
├── data-app-1 → PVC: data-data-app-1 (1Gi)
└── data-app-2 → PVC: data-data-app-2 (1Gi)
```

PVC 命名规则：`<volumeClaimTemplate.name>-<statefulset.name>-<pod-index>`

### 与 Deployment 存储的区别

| 特性 | Deployment | StatefulSet |
|------|-----------|-------------|
| 存储 | 所有 Pod 共享 PVC 或无存储 | 每个 Pod 独立 PVC |
| Pod 重建 | 数据可能丢失（除非用共享存储） | 数据保留（绑定同一 PVC） |
| 扩容 | 新 Pod 共享已有存储 | 新 Pod 创建新 PVC |
| 缩容 | PVC 可能被回收 | PVC **保留**（不删除） |

### volumeClaimTemplates 工作机制

1. StatefulSet 创建 Pod-0 时，根据模板创建 PVC `data-data-app-0`
2. Pod-0 挂载该 PVC
3. Pod-0 被删除重建时，新 Pod-0 仍绑定到同一个 PVC（数据恢复）
4. 缩容时 Pod 被删除，但 PVC 保留（数据不丢失）
5. 再次扩容时，新 Pod 绑定到之前的 PVC

### 数据安全注意事项

- 缩容不删除 PVC：保护数据，但可能产生"孤儿" PVC
- 需手动删除 PVC 才能释放存储
- `volumeClaimTemplates` 的 storageClassName 决定使用哪个 StorageClass
""",
        key_fields=[
            {"name": "spec.volumeClaimTemplates", "description": "PVC 模板列表，每个 Pod 创建独立 PVC", "required": True, "example": "[{metadata: {name: data}, spec: {...}}]"},
            {"name": "volumeClaimTemplates[].spec.resources.requests.storage", "description": "请求的存储容量", "required": True, "example": "1Gi"},
            {"name": "volumeClaimTemplates[].spec.accessModes", "description": "访问模式: ReadWriteOnce/ReadOnlyMany/ReadWriteMany", "required": True, "example": "[ReadWriteOnce]"},
            {"name": "spec.template.spec.containers[].volumeMounts", "description": "容器挂载点，引用 PVC 模板名", "required": True, "example": "[{name: data, mountPath: /data}]"},
            {"name": "volumeClaimTemplates[].spec.storageClassName", "description": "指定 StorageClass", "required": False, "example": "standard"},
        ],
        diagram="""\
  StatefulSet 持久化架构

  ┌──────────── StatefulSet (data-app) ──────────────┐
  │  spec:                                           │
  │    volumeClaimTemplates:                         │
  │    - metadata: { name: data }                    │
  │      spec:                                       │
  │        accessModes: [ReadWriteOnce]              │
  │        resources.requests.storage: 1Gi           │
  └───────────────────┬─────────────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   ┌────────┐     ┌────────┐     ┌────────┐
   │data-app│     │data-app│     │data-app│
   │  -0    │     │  -1    │     │  -2    │
   └───┬────┘     └───┬────┘     └───┬────┘
       │              │              │
       ▼              ▼              ▼
   ┌────────┐     ┌────────┐     ┌────────┐
   │PVC:    │     │PVC:    │     │PVC:    │
   │data-   │     │data-   │     │data-   │  独立 PVC
   │data-app│     │data-app│     │data-app│
   │  -0    │     │  -1    │     │  -2    │
   │ (1Gi)  │     │ (1Gi)  │     │ (1Gi)  │
   └────────┘     └────────┘     └────────┘
       │              │              │
       ▼              ▼              ▼
   ┌────────┐     ┌────────┐     ┌────────┐
   │  PV 0  │     │  PV 1  │     │  PV 2  │  独立 PV
   └────────┘     └────────┘     └────────┘
""",
        example_yaml="""\
apiVersion: apps/v1                    # StatefulSet API 版本
kind: StatefulSet                     # 资源类型
metadata:                             # 元数据
  name: data-app                      # StatefulSet 名称
spec:                                 # 规格定义
  serviceName: data-app               # Headless Service
  replicas: 3                         # 3 个副本
  selector:                           # 标签选择器
    matchLabels:
      app: data-app
  volumeClaimTemplates:               # ← PVC 模板
  - metadata:                         # PVC 元数据
      name: data                      # PVC 模板名
    spec:                             # PVC 规格
      accessModes: [ReadWriteOnce]    # 访问模式
      resources:                      # 资源请求
        requests:
          storage: 1Gi                # 请求 1Gi 存储
  template:                           # Pod 模板
    metadata:
      labels:
        app: data-app
    spec:
      containers:                     # 容器列表
      - name: app                     # 容器名
        image: busybox:1.36           # 镜像
        command: [sleep, "3600"]      # 保持运行
        volumeMounts:                 # 挂载存储
        - name: data                  # 引用 PVC 模板名
          mountPath: /data            # 挂载路径
""",
        common_errors=[
            "volumeMounts 的 name 与 volumeClaimTemplates 的 name 不匹配",
            "忘记写 accessModes 或 resources.requests.storage",
            "误以为缩容会删除 PVC（实际上 PVC 保留，需手动清理）",
            "volumeClaimTemplates 写在了 template.spec 下（应在 spec 下与 template 平级）",
        ],
        tips=[
            "用 kubectl get pvc 查看自动创建的 PVC（命名: 模板名-sts名-序号）",
            "缩容后 PVC 仍在，扩容时新 Pod 会绑定旧 PVC 恢复数据",
            "生产环境中应配合 StorageClass 实现动态供给",
        ],
    ),
)


# ==================== Q8.5 集群实战 - 部署 MySQL StatefulSet ====================

def _check_85_deploy_mysql(user_yaml: str) -> CheckResult:
    """Q8.5 集群实战 - 部署真实 MySQL StatefulSet"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.statefulsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 StatefulSet",
            hints=["你需要 apply 一个 kind: StatefulSet 的 YAML"],
        )

    sts_name = next(iter(state.statefulsets))
    sts = state.statefulsets[sts_name]
    spec = sts.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="StatefulSet 缺少 spec", hints=[])

    # 检查 serviceName
    service_name = spec.get("serviceName", "")
    if not service_name:
        return CheckResult(
            ok=False,
            error="StatefulSet 缺少 spec.serviceName",
            hints=["spec.serviceName 指向 Headless Service"],
        )

    # 检查 template 有 containers
    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="StatefulSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="template 缺少 spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="template.spec 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["spec.template.spec.containers[0].image 必须指定"],
        )

    # 检查是否有 mysql 镜像
    if "mysql" not in image.lower():
        return CheckResult(
            ok=False,
            error=f"镜像应为 mysql 系列，实际为 '{image}'",
            hints=["使用 mysql:8.0 或类似的 MySQL 镜像"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get statefulsets",
            "  kubectl get pods -w  # 观察有序创建",
            "  kubectl exec mysql-0 -- mysql -uroot -p",
        ],
    )


LEVEL_Q8_5 = Level(
    id="Q8.5",
    chapter="ch08",
    title="集群实战: 部署 MySQL StatefulSet",
    description="""
# 集群实战: 部署 MySQL StatefulSet 🏗️

来真实集群上部署一个 MySQL StatefulSet，体验有状态应用的完整部署流程！

## 任务

1. 编写 MySQL StatefulSet YAML（包含 Headless Service）
2. 部署到集群，观察有序创建过程
3. 验证每个 MySQL Pod 有独立的数据存储
4. 连接 MySQL 验证服务可用

## 要求

- `kind: StatefulSet` + `kind: Service`（Headless）
- 容器镜像使用 `mysql` 系列（如 `mysql:8.0`）
- `spec.serviceName` 指向 Headless Service
- 配置 MySQL root 密码（环境变量）

## 验证步骤

```bash
# 1. 部署
kubectl apply -f mysql-statefulset.yaml

# 2. 观察有序创建
kubectl get pods -w
# mysql-0 → Ready → mysql-1 → Ready → mysql-2

# 3. 查看 PVC
kubectl get pvc

# 4. 连接 MySQL
kubectl exec mysql-0 -- mysql -uroot -p<password> -e "SHOW DATABASES;"

# 5. 写入数据测试持久化
kubectl exec mysql-0 -- mysql -uroot -p<password> -e \
  "CREATE DATABASE testdb;"

# 6. 删除 Pod 验证数据持久化
kubectl delete pod mysql-0
kubectl exec mysql-0 -- mysql -uroot -p<password> -e \
  "SHOW DATABASES;"  # testdb 仍在！
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  # clusterIP: None  # Headless Service
  selector:
    app: mysql
  ports:
  - port: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        # image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "password123"
        ports:
        - containerPort: 3306
  # volumeClaimTemplates: 为 MySQL 提供持久化存储
""",
    check_fn=_check_85_deploy_mysql,
    lesson=Lesson(
        concept="""\
## MySQL StatefulSet 部署实战

MySQL 是典型的有状态应用，每个实例有独立的数据目录。StatefulSet 是部署 MySQL 集群（主从复制）的理想选择。

### 为什么 MySQL 用 StatefulSet？

1. **稳定网络标识**：`mysql-0.mysql` 永远指向主节点
2. **独立存储**：每个 MySQL 实例的 data 目录绑定独立 PVC
3. **有序启动**：主节点先启动，从节点后启动（复制依赖主节点）
4. **数据持久化**：Pod 重建后数据不丢失

### MySQL StatefulSet 完整架构

```
Headless Service (mysql, clusterIP: None)
    │
    ├── mysql-0.mysql  → master (读写)
    ├── mysql-1.mysql  → slave  (只读复制)
    └── mysql-2.mysql  → slave  (只读复制)
         │
         ▼
    ┌─────────────┐
    │ PVC (data)   │  每个实例独立存储
    │ /var/lib/mysql│
    └─────────────┘
```

### 生产环境注意事项

1. **密码管理**：使用 Secret 而非明文环境变量
2. **配置管理**：使用 ConfigMap 管理 my.cnf
3. **主从复制**：需要初始化脚本配置复制关系
4. **备份策略**：定期对 PVC 做快照备份
5. **资源限制**：MySQL 是资源密集型应用，需合理设置 requests/limits

### 常见部署模式

- **单节点 StatefulSet**：适合开发/测试环境
- **主从复制集群**：mysql-0 为 master，其他为 slave
- **Galera Cluster**：多主写入集群（需特殊配置）
""",
        key_fields=[
            {"name": "spec.serviceName", "description": "Headless Service 名称", "required": True, "example": "mysql"},
            {"name": "spec.template.spec.containers[].image", "description": "MySQL 镜像", "required": True, "example": "mysql:8.0"},
            {"name": "spec.template.spec.containers[].env", "description": "环境变量，设置 MySQL 密码等", "required": True, "example": "[{name: MYSQL_ROOT_PASSWORD, value: password}]"},
            {"name": "spec.volumeClaimTemplates", "description": "MySQL 数据持久化 PVC 模板", "required": False, "example": "[{name: data, spec: {storage: 5Gi}}]"},
            {"name": "spec.template.spec.containers[].volumeMounts", "description": "挂载到 /var/lib/mysql", "required": False, "example": "[{name: data, mountPath: /var/lib/mysql}]"},
        ],
        diagram="""\
  MySQL StatefulSet 部署架构

  ┌──────── Headless Service (mysql) ──────────┐
  │  clusterIP: None                            │
  │  port: 3306                                 │
  └────────────────┬───────────────────────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
  ┌────────┐  ┌────────┐  ┌────────┐
  │mysql-0 │  │mysql-1 │  │mysql-2 │
  │master  │  │slave   │  │slave   │
  │        │  │        │  │        │
  │  env:  │  │  env:  │  │  env:  │
  │ MYSQL_ │  │ MYSQL_ │  │ MYSQL_ │
  │ ROOT_  │  │ ROOT_  │  │ ROOT_  │
  │ PWD    │  │ PWD    │  │ PWD    │
  └───┬────┘  └───┬────┘  └───┬────┘
      │           │           │
      ▼           ▼           ▼
  ┌────────┐  ┌────────┐  ┌────────┐
  │PVC:    │  │PVC:    │  │PVC:    │
  │data-   │  │data-   │  │data-   │
  │mysql-0 │  │mysql-1 │  │mysql-2 │
  │(5Gi)   │  │(5Gi)   │  │(5Gi)   │
  └────────┘  └────────┘  └────────┘
      │           │           │
      ▼           ▼           ▼
  /var/lib/mysql 持久化 MySQL 数据
""",
        example_yaml="""\
# Headless Service
apiVersion: v1                             # API 版本
kind: Service                              # 资源类型
metadata:                                  # 元数据
  name: mysql                              # Service 名称
spec:                                      # 规格定义
  clusterIP: None                          # Headless Service
  selector:                                # 选择 MySQL Pod
    app: mysql
  ports:                                   # 端口配置
  - port: 3306                             # MySQL 端口
    name: mysql
---                                        # 多文档分隔
apiVersion: apps/v1                        # StatefulSet API 版本
kind: StatefulSet                          # 资源类型
metadata:                                  # 元数据
  name: mysql                              # StatefulSet 名称
spec:                                      # 规格定义
  serviceName: mysql                       # 指向 Headless Service
  replicas: 3                              # 3 个副本
  selector:                                # 标签选择器
    matchLabels:
      app: mysql
  template:                                # Pod 模板
    metadata:
      labels:
        app: mysql
    spec:
      containers:                          # 容器列表
      - name: mysql                        # 容器名
        image: mysql:8.0                   # MySQL 镜像
        env:                               # 环境变量
        - name: MYSQL_ROOT_PASSWORD        # root 密码
          value: "password123"
        ports:                             # 端口
        - containerPort: 3306
        volumeMounts:                      # 挂载存储
        - name: data                       # 引用 PVC 模板
          mountPath: /var/lib/mysql        # MySQL 数据目录
  volumeClaimTemplates:                    # PVC 模板
  - metadata:
      name: data                           # PVC 模板名
    spec:
      accessModes: [ReadWriteOnce]         # 访问模式
      resources:
        requests:
          storage: 5Gi                     # 请求 5Gi 存储
""",
        common_errors=[
            "密码用明文环境变量而非 Secret（生产环境应使用 Secret）",
            "忘记挂载 volumeMounts 到 /var/lib/mysql，导致数据不持久化",
            "serviceName 与 Headless Service 名称不匹配",
            "MySQL Pod 启动失败：检查 MYSQL_ROOT_PASSWORD 是否设置",
        ],
        tips=[
            "用 kubectl get pods -w 观察 MySQL Pod 的有序创建过程",
            "用 kubectl exec mysql-0 -- mysql -uroot -p 连接 MySQL",
            "删除 Pod 后重新创建，验证数据是否通过 PVC 恢复",
            "生产环境建议使用 Secret 管理 MySQL 密码",
        ],
    ),
)


CHAPTER_8_LEVELS: list[Level] = [
    LEVEL_Q8_1, LEVEL_Q8_2, LEVEL_Q8_3, LEVEL_Q8_4, LEVEL_Q8_5,
]
