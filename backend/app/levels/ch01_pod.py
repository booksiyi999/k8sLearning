"""Chapter 1: Pod 基础（4 关）"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, ClusterState, K8sError


# ==================== Q1.1 创建第一个 Pod ====================

def _check_01_create_pod(user_yaml: str) -> CheckResult:
    """Q1.1 创建第一个 Pod"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建任何 Pod", hints=["你需要 apply 一个 kind: Pod 的 YAML"])

    # 找名为 nginx-pod 的 Pod
    if "nginx-pod" not in state.pods:
        names = list(state.pods.keys())
        return CheckResult(
            ok=False,
            error=f"没找到名为 'nginx-pod' 的 Pod，当前 Pod 名字：{names}",
            hints=["Pod 的名字由 metadata.name 决定"],
        )

    pod = state.pods["nginx-pod"]
    containers = pod.get("spec", {}).get("containers", [])
    if not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    image = containers[0].get("image", "")
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"镜像不对，期望 nginx:1.25，实际 {image}",
            hints=["检查 spec.containers[0].image"],
        )

    return CheckResult(ok=True, state=state, hints=["干得漂亮！第一个 Pod 已经起飞了 🚀"])


LEVEL_Q1_1 = Level(
    id="Q1.1",
    chapter="ch01",
    title="创建第一个 Pod",
    description="""
# 创建第一个 Pod 🐾

欢迎来到 k8s-quest！你的第一个任务：在 K8s 集群里创建一个运行 nginx 的 Pod。

## 要求

写一个 YAML，apply 后产生：
- `kind: Pod`
- 名字叫 `nginx-pod`
- container 镜像是 `nginx:1.25`

## 提示

K8s 的 Pod 最少需要这几个字段：
- `apiVersion: v1`
- `kind: Pod`
- `metadata.name`
- `spec.containers[].name` 和 `.image`
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    # 在这里补全 container 定义
""",
    check_fn=_check_01_create_pod,
    lesson=Lesson(
        concept="""\
## 什么是 Pod？

**Pod** 是 Kubernetes 中最小的可部署计算单元。一个 Pod 可以包含一个或多个容器，这些容器共享网络和存储资源，并被作为一个整体调度到某个 Node 上。

### 为什么 K8s 不直接管容器而要管 Pod？

在现代容器化应用中，多个容器经常需要紧密协作（例如主进程 + 日志收集 sidecar）。如果 K8s 直接管理单个容器，协调它们的网络、存储和生命周期将极其复杂。Pod 作为"容器组"的抽象层，让多个容器天然共享同一个网络命名空间（IP、端口空间）和存储卷，简化了协作。

### Pod 的生命周期

Pod 是**短暂的（ephemeral）**，不是持久的实体：
1. **Pending** — 已提交，等待调度
2. **Running** — 已绑定到 Node，容器已启动
3. **Succeeded / Failed** — 所有容器正常退出 / 有容器异常退出
4. **CrashLoopBackOff** — 容器反复崩溃重启

Pod 不会"自愈"——如果 Node 挂了，Pod 就消失了。这正是 Deployment 存在的原因。

### Pod 内多容器共享网络和存储

同一 Pod 内的容器：
- **共享网络**：同一 IP、同一端口空间（容器间通过 localhost 通信）
- **共享存储卷**：可以挂载同一个 volume
- **不共享**：文件系统（各自独立）、CPU/内存限制（各自设置）

### Pod 是 K8s 最小调度单元

K8s 调度器（kube-scheduler）的调度粒度是 Pod，不是单个容器。一个 Pod 内的所有容器必定被调度到同一个 Node 上，不可能拆分。
""",
        key_fields=[
            {"name": "apiVersion", "description": "K8s API 版本，Pod 用 v1", "required": True, "example": "v1"},
            {"name": "kind", "description": "资源类型，这里是 Pod", "required": True, "example": "Pod"},
            {"name": "metadata.name", "description": "Pod 的名字，全局唯一", "required": True, "example": "nginx-pod"},
            {"name": "spec.containers", "description": "容器列表，至少一个", "required": True, "example": "[{name: nginx, image: nginx:1.25}]"},
            {"name": "spec.containers[].image", "description": "容器镜像地址", "required": True, "example": "nginx:1.25"},
        ],
        diagram="""\
┌─────────────── Pod (nginx-pod) ───────────────┐
│  ┌──────────────────────────────────────────┐ │
│  │ Container: nginx                          │ │
│  │ Image: nginx:1.25                         │ │
│  │ Port: 80                                  │ │
│  │ ┌──────────────────────────────────────┐ │ │
│  │ │     共享网络 (10.244.1.5)             │ │ │
│  │ │     共享存储 (volumes)                │ │ │
│  │ └──────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────┘ │
└───────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1          # K8s API 版本
kind: Pod               # 资源类型: Pod
metadata:               # 元数据
  name: nginx-pod       # Pod 名称（唯一标识）
  labels:               # 标签（可选，用于选择）
    app: nginx
spec:                   # 规格定义
  containers:           # 容器列表
  - name: nginx         # 容器名
    image: nginx:1.25   # 镜像
    ports:              # 端口（可选）
    - containerPort: 80
""",
        common_errors=[
            "忘记写 apiVersion 或 kind",
            "metadata.name 包含大写字母（K8s 要求小写）",
            "image 标签写错（nginx:latest vs nginx:1.25）",
            "containers 写成单数 container",
        ],
        tips=[
            "先理解 Pod 再学 Deployment",
            "用 kubectl get pods 查看运行状态",
            "用 kubectl describe pod <name> 排查问题",
        ],
    ),
)


# ==================== Q1.2 带标签的 Pod ====================

def _check_02_labeled_pod(user_yaml: str) -> CheckResult:
    """Q1.2 带标签的 Pod"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "redis-pod" not in state.pods:
        return CheckResult(
            ok=False,
            error="没找到名为 'redis-pod' 的 Pod",
            hints=["Pod 的名字应该是 redis-pod"],
        )

    pod = state.pods["redis-pod"]
    containers = pod.get("spec", {}).get("containers", [])
    if not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    image = containers[0].get("image", "")
    if image != "redis:7-alpine":
        return CheckResult(
            ok=False,
            error=f"镜像不对，期望 redis:7-alpine，实际 {image}",
            hints=["检查 spec.containers[0].image"],
        )

    labels = pod.get("metadata", {}).get("labels", {})
    expected = {"app": "cache", "tier": "backend"}
    missing = []
    for k, v in expected.items():
        if labels.get(k) != v:
            missing.append(f"{k}={v}")

    if missing:
        return CheckResult(
            ok=False,
            error=f"缺少 labels：{', '.join(missing)}",
            hints=["labels 写在 metadata.labels 下，格式如 app: cache"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["太棒了！标签是后续 Service / Deployment 选择 Pod 的关键 🏷️"],
    )


LEVEL_Q1_2 = Level(
    id="Q1.2",
    chapter="ch01",
    title="带标签的 Pod",
    description="""
# 带标签的 Pod 🏷️

在 K8s 里，**labels（标签）** 是给资源打分类标记的方式。后续 Service 和 Deployment 都靠 labels 来"选"Pod。

## 要求

创建一个 Redis Pod：
- `kind: Pod`，名字叫 `redis-pod`
- 镜像 `redis:7-alpine`
- 打两个 labels：
  - `app: cache`
  - `tier: backend`

## 提示

labels 写在 `metadata.labels` 下：
```yaml
metadata:
  name: redis-pod
  labels:
    app: cache
    tier: backend
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  # 在这里加 labels
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""",
    check_fn=_check_02_labeled_pod,
    lesson=Lesson(
        concept="""\
## Labels（标签）

**Labels** 是 K8s 中用于给资源打标记的键值对（key-value）。它们是 K8s 核心的组织机制——几乎所有资源选择操作都基于 labels。

### Labels 的作用

- **Service** 通过 `selector` 匹配 labels 来决定流量转发到哪些 Pod
- **Deployment** 通过 labels 管理它创建的 Pod 副本
- 用户可以用 `kubectl get pods -l app=cache` 快速筛选资源

### Labels vs Annotations

| 特性 | Labels | Annotations |
|------|--------|-------------|
| 用途 | 标识和选择资源 | 附加任意元数据 |
| 查询 | 支持 selector 查询 | 不可查询 |
| 数据 | 简短键值对 | 可存 JSON/长文本 |
| 示例 | `app: cache` | `last-updated-by: admin` |

### Label 命名规范

- 键格式：`前缀/名称`（前缀可选，如 `app.kubernetes.io/name`）
- 值：必须是小写字母、数字、`-`、`.`、`_` 组成
- **不能**包含大写字母
- 常见约定：`app`、`tier`、`version`、`environment`

### 常用 Label 模式

- `app: <应用名>` — 标识应用
- `tier: frontend/backend` — 架构分层
- `env: dev/staging/prod` — 环境区分
- `version: v1.2.3` — 版本标记
""",
        key_fields=[
            {"name": "metadata.labels", "description": "标签字典，键值对形式", "required": False, "example": "{app: cache, tier: backend}"},
            {"name": "metadata.labels.app", "description": "应用标识标签", "required": True, "example": "cache"},
            {"name": "metadata.labels.tier", "description": "架构层标识标签", "required": True, "example": "backend"},
        ],
        diagram="""\
┌──────── Pod (redis-pod) ─────────┐
│  metadata:                       │
│    name: redis-pod               │
│    labels:                       │
│      app: cache      ◄───────────┼── Service selector: app=cache
│      tier: backend   ◄───────────┼── Service selector: tier=backend
│  spec:                           │
│    containers:                   │
│    - name: redis                 │
│      image: redis:7-alpine       │
└──────────────────────────────────┘
         │
         ▼
  labels 决定了哪些 Service / Deployment
  会"选中"这个 Pod
""",
        example_yaml="""\
apiVersion: v1              # K8s API 版本
kind: Pod                   # 资源类型: Pod
metadata:                   # 元数据
  name: redis-pod           # Pod 名称
  labels:                   # 标签区
    app: cache              # 应用标识
    tier: backend           # 架构层标识
spec:                       # 规格定义
  containers:               # 容器列表
  - name: redis             # 容器名
    image: redis:7-alpine   # Redis 镜像
""",
        common_errors=[
            "labels 写在了 spec 下而不是 metadata 下",
            "label 值包含大写字母（如 app: Cache）",
            "把 labels 和 annotations 混淆",
            "label 键使用了 K8s 保留前缀 kubernetes.io/ 但不符合规范",
        ],
        tips=[
            "labels 是后续学习 Service 和 Deployment 的基础，务必理解",
            "用 kubectl get pods --show-labels 查看所有标签",
            "用 kubectl label pod <name> key=value 可以动态添加标签",
            "标签要简洁、有意义，避免过多无意义的标签",
        ],
    ),
)


# ==================== Q1.3 多容器 Pod（sidecar） ====================

def _check_03_multi_container(user_yaml: str) -> CheckResult:
    """Q1.3 多容器 Pod（sidecar 模式）"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "web-with-logger" not in state.pods:
        return CheckResult(
            ok=False,
            error="没找到名为 'web-with-logger' 的 Pod",
            hints=[],
        )

    pod = state.pods["web-with-logger"]
    containers = pod.get("spec", {}).get("containers", [])

    if len(containers) < 2:
        return CheckResult(
            ok=False,
            error=f"需要 2 个容器（web + logger sidecar），实际 {len(containers)} 个",
            hints=["在 spec.containers 下再加一个容器"],
        )

    by_name = {c.get("name"): c for c in containers}
    if "web" not in by_name:
        return CheckResult(ok=False, error="缺少名为 'web' 的主容器", hints=[])
    if "logger" not in by_name:
        return CheckResult(ok=False, error="缺少名为 'logger' 的 sidecar 容器", hints=[])

    if by_name["web"].get("image") != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"web 容器镜像应为 nginx:1.25，实际 {by_name['web'].get('image')}",
            hints=[],
        )

    if by_name["logger"].get("image") != "busybox:1.36":
        return CheckResult(
            ok=False,
            error=f"logger 容器镜像应为 busybox:1.36，实际 {by_name['logger'].get('image')}",
            hints=[],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["完美！sidecar 模式是 K8s 的精髓之一——Pod 内多容器共享网络和存储 🔍"],
    )


LEVEL_Q1_3 = Level(
    id="Q1.3",
    chapter="ch01",
    title="多容器 Pod（sidecar）",
    description="""
# 多容器 Pod（sidecar 模式）🔍

Pod 是 K8s 的**原子调度单位**——一个 Pod 可以包含多个容器，它们共享网络和存储。

经典场景：**主容器 + sidecar（日志收集器）**。

## 要求

创建一个 Pod：
- 名字 `web-with-logger`
- 主容器：`name: web`, `image: nginx:1.25`
- sidecar 容器：`name: logger`, `image: busybox:1.36`

## 提示

在 `spec.containers` 下加两个容器：
```yaml
spec:
  containers:
    - name: web
      image: nginx:1.25
    - name: logger
      image: busybox:1.36
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  containers:
    - name: web
      image: nginx:1.25
    # 在这里加 logger sidecar
""",
    check_fn=_check_03_multi_container,
    lesson=Lesson(
        concept="""\
## 多容器 Pod（Sidecar 模式）

一个 Pod 可以包含**多个容器**，它们共享同一个网络命名空间（IP、端口）和存储卷。这是 Pod 抽象的核心价值——让紧密协作的容器天然协同。

### 为什么需要多容器 Pod？

在传统架构中，日志收集、监控代理、配置同步等功能往往嵌入主应用代码。K8s 的多容器 Pod 提供了一种更优雅的方案：将这些辅助功能拆分成独立的 sidecar 容器。

### 经典多容器设计模式

1. **Sidecar** — 主容器 + 辅助容器（如日志收集器）
2. **Ambassador** — 代理容器，负责外部服务连接
3. **Adapter** — 标准化输出格式（如监控数据转换）

### Sidecar 模式详解

```
Pod
├── 主容器: 处理核心业务逻辑
└── Sidecar: 辅助功能（日志/监控/代理）
```

- 两个容器可以独立更新，互不影响
- Sidecar 可以被复用到不同的应用中
- 容器间通过 `localhost` 或共享 volume 通信

### 多容器 Pod 的注意事项

- 容器间共享网络，但**端口不能冲突**
- 所有容器会被调度到同一个 Node
- Pod 的状态取决于所有容器——任一容器 CrashLoopBackOff 会影响整个 Pod
- 可以通过 `shareProcessNamespace: true` 让容器间共享 PID 命名空间
""",
        key_fields=[
            {"name": "spec.containers", "description": "容器列表，多容器时为多个元素", "required": True, "example": "[{name: web}, {name: logger}]"},
            {"name": "spec.containers[].name", "description": "每个容器的名称，Pod 内唯一", "required": True, "example": "web"},
            {"name": "spec.containers[].image", "description": "容器镜像地址", "required": True, "example": "nginx:1.25"},
            {"name": "spec.volumes", "description": "共享存储卷定义（多容器共享时常用）", "required": False, "example": "[{name: shared-data, emptyDir: {}}]"},
            {"name": "spec.shareProcessNamespace", "description": "是否共享 PID 命名空间", "required": False, "example": "true"},
        ],
        diagram="""\
┌──────────── Pod (web-with-logger) ────────────┐
│                                                │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │ Container: web    │  │ Container: logger │   │
│  │ Image: nginx:1.25 │  │ Image: busybox   │   │
│  │ Port: 80          │  │ (sidecar)        │   │
│  └────────┬─────────┘  └────────┬─────────┘   │
│           │                      │              │
│           └──────┬───────────────┘              │
│                  ▼                              │
│  ┌──────────────────────────────────────────┐  │
│  │        共享网络 (localhost)               │  │
│  │        共享存储 (volumes)                 │  │
│  │        同一个 IP: 10.244.1.5              │  │
│  └──────────────────────────────────────────┘  │
│                                                │
└────────────────────────────────────────────────┘
  web 容器产生日志 → logger 容器通过共享卷读取并处理
""",
        example_yaml="""\
apiVersion: v1                    # K8s API 版本
kind: Pod                         # 资源类型: Pod
metadata:                         # 元数据
  name: web-with-logger           # Pod 名称
spec:                             # 规格定义
  containers:                     # 容器列表（多个）
  - name: web                     # 主容器
    image: nginx:1.25             # Nginx 镜像
    ports:                        # 端口
    - containerPort: 80
    volumeMounts:                 # 挂载共享卷
    - name: shared-logs
      mountPath: /var/log/nginx
  - name: logger                  # Sidecar 容器
    image: busybox:1.36           # 轻量镜像
    volumeMounts:                 # 挂载同一个共享卷
    - name: shared-logs
      mountPath: /var/log/nginx
    command: ["/bin/sh", "-c"]    # 持续读取日志
    args: ["tail -f /var/log/nginx/access.log"]
  volumes:                        # 定义共享卷
  - name: shared-logs
    emptyDir: {}                  # 临时共享存储
""",
        common_errors=[
            "两个容器使用了相同的 name（Pod 内 name 必须唯一）",
            "两个容器监听同一个端口（共享网络命名空间，端口冲突）",
            "忘记在 spec.containers 下用列表格式，写成了单个对象",
            "sidecar 容器没有正确挂载共享 volume，导致读不到主容器的数据",
        ],
        tips=[
            "Sidecar 模式是 K8s 的精髓之一，理解它后再学 InitContainer",
            "多容器共享网络——容器间用 localhost 通信",
            "用 kubectl logs <pod> -c <container> 查看指定容器日志",
            "emptyDir 卷在 Pod 删除时随之消失，不适合持久化数据",
        ],
    ),
)


# ==================== Q1.4 带 resource requests/limits 的 Pod ====================

# 期望值：CPU request=100m, memory request=128Mi, CPU limit=500m, memory limit=256Mi
_Q1_4_EXPECTED = {
    ("requests", "cpu"): "100m",
    ("requests", "memory"): "128Mi",
    ("limits", "cpu"): "500m",
    ("limits", "memory"): "256Mi",
}


def _check_04_resource_limits(user_yaml: str) -> CheckResult:
    """Q1.4 带 resource requests/limits 的 Pod"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "resource-pod" not in state.pods:
        return CheckResult(
            ok=False,
            error="没找到名为 'resource-pod' 的 Pod",
            hints=["Pod 的名字应该是 resource-pod"],
        )

    pod = state.pods["resource-pod"]
    containers = pod.get("spec", {}).get("containers", [])
    if not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    resources = c.get("resources")
    if not isinstance(resources, dict):
        # 类型守卫：resources 可能是字符串/列表等非 dict 类型，
        # 此时 resources.get() 会抛 AttributeError 导致 /api/check 返回 500。
        # 空值(None)同样被 isinstance 拦截，统一返回缺字段提示。
        return CheckResult(
            ok=False,
            error="容器缺少 resources 字段（需要 requests 和 limits，且必须是字典）",
            hints=["resources 写在 spec.containers[0].resources 下，格式为 requests/limits 字典"],
        )

    # 逐项校验 requests / limits 的 cpu / memory
    for (section, key), want in _Q1_4_EXPECTED.items():
        section_dict = resources.get(section)
        if not isinstance(section_dict, dict):
            # 类型守卫：requests/limits 可能是字符串/列表/数字等 truthy 非 dict 类型，
            # falsy-only 守卫（if not section_dict）会被 truthy 非 dict 绕过，
            # 随后 section_dict.get(key) 抛 AttributeError → /api/check 返回 500。
            # 空值(None)同样被 isinstance 拦截，统一返回缺字段提示。
            return CheckResult(
                ok=False,
                error=f"resources.{section} 缺失或类型错误（必须是包含 cpu 和 memory 的字典）",
                hints=[f"在 resources 下添加 {section}:，下设 cpu 和 memory 两个键"],
            )
        got = section_dict.get(key)
        if got is None:
            return CheckResult(
                ok=False,
                error=f"缺少 resources.{section}.{key}（期望 {want}）",
                hints=[f"在 resources.{section} 下添加 {key}: {want}"],
            )
        if str(got) != want:
            return CheckResult(
                ok=False,
                error=f"resources.{section}.{key} 不对，期望 {want}，实际 {got}",
                hints=[f"检查 resources.{section}.{key}，应为 {want}"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "完美！request 是调度依据（kube-scheduler 只看 request），"
            "limit 是运行时硬上限（kubelet 通过 cgroup 限制）💾",
        ],
    )


LEVEL_Q1_4 = Level(
    id="Q1.4",
    chapter="ch01",
    title="带 resource requests/limits 的 Pod",
    description="""
# 带 resource requests/limits 的 Pod 💾

在 K8s 里，每个容器都应该设置 **resources** —— 包含 **requests**（请求量）和 **limits**（上限）。

- **request**：kube-scheduler 用它决定 Pod 放到哪个 Node（调度依据）
- **limit**：kubelet 通过 cgroup 硬限制容器最多能用多少（运行时上限）

不设 resources = 容器可以吃光 Node 资源，拖垮整个节点。

## 要求

创建一个 Pod：
- 名字 `resource-pod`
- 镜像 `nginx:1.25`
- 资源配置：
  - CPU request = `100m`，memory request = `128Mi`
  - CPU limit = `500m`，memory limit = `256Mi`

## 提示

resources 写在 `spec.containers[0].resources` 下：
```yaml
resources:
  requests:
    cpu: "100m"        # 100 millicpu = 0.1 核
    memory: "128Mi"    # 128 Mebibyte
  limits:
    cpu: "500m"        # 最多 0.5 核
    memory: "256Mi"    # 最多 256Mi
```

> 💡 `m` = millicpu（毫核），1 CPU = 1000m。`Mi` = Mebibyte（2^20 字节）。
> 注意大小写：`m` 在 CPU 里是毫核，在 memory 里 `M` 是 megabyte（10^6）不是 mebibyte。
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      # 在这里加 resources（requests + limits）
""",
    check_fn=_check_04_resource_limits,
    lesson=Lesson(
        concept="""\
## Resource Requests & Limits

在 K8s 中，每个容器都应该配置 **resources**，包含 **requests**（请求量）和 **limits**（上限）。这是集群稳定运行的基石。

### Requests vs Limits

| 属性 | requests | limits |
|------|----------|--------|
| 用途 | **调度依据**——kube-scheduler 用它决定 Pod 放到哪个 Node | **运行时上限**——kubelet 通过 cgroup 硬限制 |
| 行为 | Node 上所有 Pod 的 request 总和不能超过 Node 容量 | 容器实际使用超过 limit 时会被 OOMKill 或 CPU throttled |
| 必须设置 | 推荐 | 推荐 |

### CPU 单位

- `1` = 1 个 CPU 核心（可以是物理核或虚拟核）
- `100m` = 100 millicpu = 0.1 核
- `500m` = 500 millicpu = 0.5 核
- CPU 是**可压缩资源**——超限时容器被 throttled（减速），不会被杀

### Memory 单位

- `128Mi` = 128 Mebibyte = 128 × 1024² 字节
- `128M` = 128 Megabyte = 128 × 10⁶ 字节（注意区别！）
- `1Gi` = 1 Gibibyte = 1024 MiB
- Memory 是**不可压缩资源**——超限时容器被 OOMKill（直接杀死）

### 调度原理

```
Node 总容量: 4 CPU, 16Gi memory
Pod A request: 1 CPU, 2Gi  →  剩余: 3 CPU, 14Gi
Pod B request: 2 CPU, 4Gi  →  剩余: 1 CPU, 10Gi
Pod C request: 2 CPU, 4Gi  →  3 > 1, 无法调度到此 Node
```

kube-scheduler 只看 **requests**，不看 limits。因此即使 limit 设得很高，request 决定了 Pod 能否被调度。

### 为什么必须设置 Resources？

- 不设 requests → 调度器无法做合理决策，Pod 可能被调度到资源不足的 Node
- 不设 limits → 容器可以吃光 Node 资源，拖垮同节点的其他 Pod
- 生产环境必须设置，这是 Best Practice
""",
        key_fields=[
            {"name": "spec.containers[].resources", "description": "资源配置块，包含 requests 和 limits", "required": True, "example": "{requests: {cpu: 100m, memory: 128Mi}, limits: {cpu: 500m, memory: 256Mi}}"},
            {"name": "spec.containers[].resources.requests.cpu", "description": "CPU 请求量，调度依据", "required": True, "example": "100m"},
            {"name": "spec.containers[].resources.requests.memory", "description": "内存请求量，调度依据", "required": True, "example": "128Mi"},
            {"name": "spec.containers[].resources.limits.cpu", "description": "CPU 上限，运行时硬限制", "required": True, "example": "500m"},
            {"name": "spec.containers[].resources.limits.memory", "description": "内存上限，超出则 OOMKill", "required": True, "example": "256Mi"},
        ],
        diagram="""\
┌─────────── Pod (resource-pod) ────────────────┐
│  Container: app (nginx:1.25)                   │
│                                                │
│  ┌─────────────── resources ─────────────────┐ │
│  │                                            │ │
│  │  requests (调度依据)          limits (运行时上限)  │
│  │  ┌──────────────────┐    ┌──────────────────┐│ │
│  │  │ cpu:    100m     │    │ cpu:    500m     ││ │
│  │  │ memory: 128Mi    │    │ memory: 256Mi    ││ │
│  │  └──────────────────┘    └──────────────────┘│ │
│  │       │                          │          │ │
│  │       ▼                          ▼          │ │
│  │  scheduler 看这个           kubelet 看这个    │ │
│  │  (决定放哪个 Node)         (cgroup 硬限制)    │ │
│  └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘

  CPU 超限 → throttled（减速，不杀进程）
  Memory 超限 → OOMKill（直接杀死容器）
""",
        example_yaml="""\
apiVersion: v1                    # K8s API 版本
kind: Pod                         # 资源类型: Pod
metadata:                         # 元数据
  name: resource-pod              # Pod 名称
spec:                             # 规格定义
  containers:                     # 容器列表
  - name: app                     # 容器名
    image: nginx:1.25             # 镜像
    resources:                    # 资源配置
      requests:                   # 请求量（调度依据）
        cpu: "100m"               # 100 millicpu = 0.1 核
        memory: "128Mi"           # 128 Mebibyte
      limits:                     # 上限（运行时硬限制）
        cpu: "500m"               # 最多 0.5 核
        memory: "256Mi"           # 最多 256Mi
""",
        common_errors=[
            "把 requests 和 limits 写反了（requests 是调度依据，limits 是上限）",
            "CPU 单位写错：用 0.1 而不是 100m（虽然等价，但 millicpu 是惯例）",
            "Memory 单位混淆：Mi（Mebibyte）和 M（Megabyte）不同",
            "resources 写在了 spec 下而不是 spec.containers 下",
            "CPU 值没加引号导致 YAML 解析为数字（如 cpu: 100m 可能被误解析）",
        ],
        tips=[
            "生产环境务必设置 resources，这是稳定运行的基石",
            "request 应接近实际平均用量，limit 应设为峰值用量",
            "用 kubectl describe node <name> 查看 Node 资源分配情况",
            "用 kubectl top pods 查看实际资源使用量（需要 metrics-server）",
            "CPU 是可压缩资源（超限减速），Memory 是不可压缩资源（超限杀进程）",
        ],
    ),
)


# ==================== Chapter 1 关卡汇总 ====================

CHAPTER_1_LEVELS = [LEVEL_Q1_1, LEVEL_Q1_2, LEVEL_Q1_3, LEVEL_Q1_4]
