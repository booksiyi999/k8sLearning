"""Chapter 25: 多容器模式 - Init/Sidecar/Ambassador/Adapter（5 关）

Q25.1 Init Container - 初始化容器
Q25.2 Sidecar 模式 - 边车容器
Q25.3 Ambassador 模式 - 代理容器
Q25.4 Adapter 模式 - 适配器容器
Q25.5 集群实战 - 完整多容器应用
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


# ==================== Q25.1 Init Container ====================

def _check_251_init_container(user_yaml: str) -> CheckResult:
    """Q25.1 创建带 initContainers 的 Pod"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Pod 的 YAML"],
        )

    pod_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Pod":
            pod_doc = doc
            break

    if not pod_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Pod",
            hints=["你需要创建一个 kind: Pod 的 YAML 📦"],
        )

    spec = pod_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    # 检查 initContainers
    init_containers = spec.get("initContainers")
    if not isinstance(init_containers, list) or not init_containers:
        return CheckResult(
            ok=False,
            error="Pod 缺少 spec.initContainers",
            hints=["添加 spec.initContainers 字段，包含至少一个初始化容器"],
        )

    init_c = init_containers[0]
    if not isinstance(init_c, dict):
        return CheckResult(ok=False, error="initContainers[0] 格式错误", hints=[])

    if not init_c.get("name"):
        return CheckResult(
            ok=False,
            error="initContainers[0] 缺少 name",
            hints=["每个容器都需要 name 字段"],
        )

    if not init_c.get("image"):
        return CheckResult(
            ok=False,
            error="initContainers[0] 缺少 image",
            hints=["初始化容器需要指定 image"],
        )

    if not init_c.get("command"):
        return CheckResult(
            ok=False,
            error="initContainers[0] 缺少 command",
            hints=["初始化容器通常需要指定 command 来执行初始化任务"],
        )

    # 检查主容器
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(
            ok=False,
            error="Pod 缺少 spec.containers（主容器）",
            hints=["initContainers 完成后才启动主容器，你需要同时定义主容器"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Init Container 在主容器启动前运行，完成后才启动主容器 🔧"],
    )


LEVEL_Q25_1 = Level(
    id="Q25.1",
    chapter="ch25",
    title="Init Container - 初始化容器",
    description="""
# Init Container - 初始化容器 🔧

**Init Container**（初始化容器）是一种特殊容器，在 Pod 的主容器启动之前运行。Init Container 必须成功完成后，主容器才会启动。

## 任务

创建一个带 initContainer 的 Pod：
- `kind: Pod`
- Pod 名称为 `init-demo`
- initContainer 名称 `init-mysql`，镜像 `busybox:1.36`
- initContainer 执行命令 `["sh", "-c", "echo 'Initializing...' > /work-dir/index.html"]`
- initContainer 挂载 emptyDir 卷 `workdir` 到 `/work-dir`
- 主容器名称 `web`，镜像 `nginx:1.25`
- 主容器挂载同一个 emptyDir 卷 `workdir` 到 `/usr/share/nginx/html`

## 提示

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
spec:
  initContainers:
  - name: init-mysql
    image: busybox:1.36
    command: ["sh", "-c", "echo 'Initializing...' > /work-dir/index.html"]
    volumeMounts:
    - name: workdir
      mountPath: /work-dir
  containers:
  - name: web
    image: nginx:1.25
    volumeMounts:
    - name: workdir
      mountPath: /usr/share/nginx/html
  volumes:
  - name: workdir
    emptyDir: {}
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
spec:
  # initContainers: 在这里添加初始化容器
  containers:
  - name: web
    image: nginx:1.25
    volumeMounts:
    - name: workdir
      mountPath: /usr/share/nginx/html
  volumes:
  - name: workdir
    emptyDir: {}
""",
    check_fn=_check_251_init_container,
    lesson=Lesson(
        concept="""\
## 什么是 Init Container？

**Init Container**（初始化容器）是 Pod 中在主容器启动之前运行的特殊容器。每个 Init Container 必须成功完成后，下一个 Init Container（或主容器）才会启动。

### Init Container 的核心行为

1. **顺序执行**：多个 Init Container 按定义顺序依次运行
2. **必须成功**：任一 Init Container 失败，整个 Pod 重启（取决于 restartPolicy）
3. **完成后退出**：Init Container 不持续运行，完成任务后退出
4. **资源共享**：Init Container 与主容器共享网络和存储卷

### 与普通容器的区别

| 特性 | Init Container | 普通容器 |
|------|---------------|---------|
| 启动时机 | Pod 启动时最先运行 | 所有 Init Container 完成后 |
| 运行方式 | 运行完成即退出 | 持续运行 |
| 失败处理 | Pod 重启（restartPolicy） | 容器重启 |
| 数量 | 可多个，顺序执行 | 可多个，并行运行 |

### 典型使用场景

- 等待依赖服务就绪（如数据库）
- 初始化配置文件
- 注册服务到服务发现
- 克隆 Git 仓库到共享卷
- 数据库迁移脚本执行
""",
        key_fields=[
            {"name": "spec.initContainers", "description": "初始化容器列表，顺序执行", "required": True, "example": "[{name: init-db, image: busybox:1.36}]"},
            {"name": "spec.initContainers[].name", "description": "容器名称", "required": True, "example": "init-mysql"},
            {"name": "spec.initContainers[].image", "description": "容器镜像", "required": True, "example": "busybox:1.36"},
            {"name": "spec.initContainers[].command", "description": "初始化命令", "required": True, "example": "[sh, -c, echo done]"},
            {"name": "spec.initContainers[].volumeMounts", "description": "卷挂载，可与主容器共享", "required": False, "example": "[{name: workdir, mountPath: /work-dir}]"},
            {"name": "spec.containers", "description": "主容器列表，initContainer 完成后启动", "required": True, "example": "[{name: web, image: nginx:1.25}]"},
        ],
        diagram="""\
  ┌──────────────── Pod (init-demo) ────────────────┐
  │  spec:                                          │
  │    initContainers:        ◄── 先执行，完成即退出  │
  │    - name: init-mysql                           │
  │      image: busybox:1.36                        │
  │      command: [sh, -c, echo ...]                │
  │      volumeMounts:                              │
  │      - name: workdir → /work-dir                │
  │                                                 │
  │    containers:            ◄── init 完成后启动     │
  │    - name: web                                  │
  │      image: nginx:1.25                          │
  │      volumeMounts:                              │
  │      - name: workdir → /usr/share/nginx/html    │
  │                                                 │
  │    volumes:                                     │
  │    - name: workdir (emptyDir)  ◄── 共享存储       │
  └─────────────────────────────────────────────────┘

  时间线:
  t0: init-mysql 启动 → 写入 index.html → exit 0 ✓
  t1: web 启动 → 读取 index.html 提供服务
""",
        example_yaml="""\
apiVersion: v1                # 核心 API
kind: Pod                     # 资源类型: Pod
metadata:                     # 元数据
  name: init-demo             # Pod 名称
spec:                         # 规格
  initContainers:             # 初始化容器列表
  - name: init-mysql          # 容器名
    image: busybox:1.36       # 镜像
    command:                  # 初始化命令
    - sh
    - "-c"
    - "echo 'Initializing...' > /work-dir/index.html"
    volumeMounts:             # 挂载共享卷
    - name: workdir
      mountPath: /work-dir
  containers:                 # 主容器列表
  - name: web                 # 容器名
    image: nginx:1.25         # Nginx 镜像
    volumeMounts:             # 挂载同一个共享卷
    - name: workdir
      mountPath: /usr/share/nginx/html
  volumes:                    # 卷定义
  - name: workdir             # 卷名
    emptyDir: {}              # 临时空目录
""",
        common_errors=[
            "把 initContainers 写成了 init-containers（K8s 使用 camelCase）",
            "忘记在主容器中也挂载 initContainer 写入数据的卷",
            "initContainer 中没有指定 command，导致容器立即退出但没有完成初始化",
            "期望 initContainer 和主容器同时运行（initContainer 必须先完成才启动主容器）",
        ],
        tips=[
            "用 kubectl logs <pod> -c <init-container> 查看 init 容器日志",
            "用 kubectl describe pod <pod> 查看 init 容器状态（Init Status 列）",
            "initContainer 不支持 livenessProbe/readinessProbe（因为它需要运行完成而非持续运行）",
        ],
    ),
)


# ==================== Q25.2 Sidecar 模式 ====================

def _check_252_sidecar(user_yaml: str) -> CheckResult:
    """Q25.2 创建 Sidecar 模式的 Pod"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Pod 的 YAML"],
        )

    pod_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Pod":
            pod_doc = doc
            break

    if not pod_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Pod",
            hints=["你需要创建一个 kind: Pod 的 YAML 📦"],
        )

    spec = pod_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    containers = spec.get("containers", [])
    if not isinstance(containers, list) or len(containers) < 2:
        return CheckResult(
            ok=False,
            error="Sidecar 模式需要至少 2 个容器（主容器 + 边车容器）",
            hints=["在 spec.containers 中定义主容器和一个辅助容器"],
        )

    # 检查是否有共享卷
    volumes = spec.get("volumes", [])
    if not isinstance(volumes, list) or not volumes:
        return CheckResult(
            ok=False,
            error="Sidecar 模式通常需要共享卷来实现容器间通信",
            hints=["添加 spec.volumes，如 emptyDir 用于容器间共享数据"],
        )

    # 检查容器是否都挂载了卷
    vol_names = {v.get("name") for v in volumes if isinstance(v, dict)}
    containers_with_vol = 0
    for c in containers:
        if not isinstance(c, dict):
            continue
        mounts = c.get("volumeMounts", [])
        if isinstance(mounts, list):
            for m in mounts:
                if isinstance(m, dict) and m.get("name") in vol_names:
                    containers_with_vol += 1
                    break

    if containers_with_vol < 2:
        return CheckResult(
            ok=False,
            error="主容器和 Sidecar 容器应挂载同一个共享卷",
            hints=["确保两个容器都 volumeMount 了同一个 volume"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Sidecar 模式让辅助容器与主容器共享生命周期，扩展主容器功能 🛍️"],
    )


LEVEL_Q25_2 = Level(
    id="Q25.2",
    chapter="ch25",
    title="Sidecar 模式 - 边车容器",
    description="""
# Sidecar 模式 - 边车容器 🛍️

**Sidecar 模式**在 Pod 中运行一个辅助容器（边车），与主容器共享网络和存储，扩展主容器的功能而不修改其代码。

## 任务

创建一个 Sidecar 模式的 Pod：
- `kind: Pod`，名称 `sidecar-demo`
- 主容器 `app`，镜像 `nginx:1.25`，挂载共享卷 `shared` 到 `/usr/share/nginx/html`
- Sidecar 容器 `log-sync`，镜像 `busybox:1.36`
- Sidecar 挂载同一个 `shared` 卷到 `/var/log/app`
- Sidecar 命令：定期同步日志文件 `["sh", "-c", "while true; do cp /var/log/app/* /backup/ 2>/dev/null; sleep 30; done"]`
- 定义 emptyDir 卷 `shared`

## 提示

Sidecar 和主容器在同一个 Pod 中，共享网络和存储：
```yaml
spec:
  containers:
  - name: app          # 主容器
    image: nginx:1.25
    volumeMounts:
    - name: shared
      mountPath: /usr/share/nginx/html
  - name: log-sync     # 边车容器
    image: busybox:1.36
    volumeMounts:
    - name: shared
      mountPath: /var/log/app
    command: ["sh", "-c", "while true; do sleep 30; done"]
  volumes:
  - name: shared
    emptyDir: {}
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: sidecar-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: shared
      mountPath: /usr/share/nginx/html
  # 添加 sidecar 容器 log-sync
  volumes:
  - name: shared
    emptyDir: {}
""",
    check_fn=_check_252_sidecar,
    lesson=Lesson(
        concept="""\
## Sidecar 模式

**Sidecar 模式**是 Kubernetes 多容器设计中最常见的模式。一个"边车"容器与主容器在同一个 Pod 中运行，共享网络和存储，为**主容器提供辅助功能**。

### Sidecar 的核心特征

1. **同 Pod 共存**：边车与主容器在同一个 Pod 中
2. **共享网络**：容器间通过 localhost 通信
3. **共享存储**：通过 volume 共享文件
4. **独立生命周期**：各自管理自己的进程，但同生共死
5. **增强不侵入**：不修改主容器代码即可扩展功能

### 常见 Sidecar 场景

| 场景 | 边车功能 | 示例 |
|------|---------|------|
| 日志代理 | 收集主容器日志 | Fluentd/Fluent Bit |
| 监控代理 | 采集指标 | Prometheus exporter |
| 服务代理 | 网络代理 | Envoy/Istio sidecar |
| 配置同步 | 动态更新配置文件 | git-sync |
| TLS 终止 | 代理 HTTPS | nginx sidecar |

### Sidecar 与 Init Container 的区别

- **Init Container**：运行一次后退出，主容器随后启动
- **Sidecar**：与主容器同时运行，持续提供辅助功能
""",
        key_fields=[
            {"name": "spec.containers[]", "description": "至少 2 个容器：主容器 + Sidecar", "required": True, "example": "[{name: app}, {name: log-sync}]"},
            {"name": "spec.volumes", "description": "共享卷，容器间通信桥梁", "required": True, "example": "[{name: shared, emptyDir: {}}]"},
            {"name": "spec.containers[].volumeMounts", "description": "主容器和 Sidecar 都挂载同一卷", "required": True, "example": "[{name: shared, mountPath: /data}]"},
        ],
        diagram="""\
  ┌──────────────── Pod (sidecar-demo) ───────────────┐
  │                                                    │
  │  ┌──────────────┐      ┌──────────────────┐       │
  │  │  主容器 app   │      │ Sidecar log-sync │       │
  │  │  nginx:1.25  │      │  busybox:1.36    │       │
  │  │              │      │                  │       │
  │  │ /usr/share/  │      │ /var/log/app     │       │
  │  │  nginx/html  │      │                  │       │
  │  └──────┬───────┘      └────────┬─────────┘       │
  │         │                       │                  │
  │         │    共享存储             │                  │
  │         ▼                       ▼                  │
  │  ┌──────────────────────────────────────┐         │
  │  │          volume: shared (emptyDir)    │         │
  │  └──────────────────────────────────────┘         │
  │                                                    │
  │  ◄── 共享网络 (localhost) ──►                      │
  └────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                # 核心 API
kind: Pod                     # 资源类型
metadata:                     # 元数据
  name: sidecar-demo          # Pod 名称
spec:                         # 规格
  containers:                 # 容器列表（主+边车）
  - name: app                 # 主容器
    image: nginx:1.25         # Nginx 镜像
    volumeMounts:             # 挂载共享卷
    - name: shared
      mountPath: /usr/share/nginx/html
  - name: log-sync            # Sidecar 边车容器
    image: busybox:1.36       # Busybox 镜像
    command:                  # 持续运行
    - sh
    - "-c"
    - "while true; do cp /var/log/app/* /backup/ 2>/dev/null; sleep 30; done"
    volumeMounts:             # 挂载同一共享卷
    - name: shared
      mountPath: /var/log/app
  volumes:                    # 卷定义
  - name: shared              # 共享卷名
    emptyDir: {}              # 临时空目录
""",
        common_errors=[
            "Sidecar 挂载了不同的 volume，导致无法共享数据",
            "Sidecar 没有持续运行的命令，启动后立即退出",
            "Sidecar 端口与主容器冲突（同 Pod 容器共享网络，不能绑定同一端口）",
            "把 Sidecar 写成了 Init Container（Sidecar 需要持续运行而非运行后退出）",
        ],
        tips=[
            "Sidecar 容器与主容器通过 localhost 互相通信",
            "用 kubectl logs <pod> -c <container> 查看指定容器日志",
            "Sidecar 增加了 Pod 资源消耗，应根据需求合理配置资源限制",
        ],
    ),
)


# ==================== Q25.3 Ambassador 模式 ====================

def _check_253_ambassador(user_yaml: str) -> CheckResult:
    """Q25.3 创建 Ambassador 模式的 Pod"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Pod 的 YAML"],
        )

    pod_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Pod":
            pod_doc = doc
            break

    if not pod_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Pod",
            hints=["你需要创建一个 kind: Pod 的 YAML 📦"],
        )

    spec = pod_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    containers = spec.get("containers", [])
    if not isinstance(containers, list) or len(containers) < 2:
        return CheckResult(
            ok=False,
            error="Ambassador 模式需要至少 2 个容器（主容器 + 代理容器）",
            hints=["在 spec.containers 中定义主容器和代理容器"],
        )

    # 查找代理容器（通常是 redis-proxy 或 envoy 等）
    ambassador_keywords = ["proxy", "ambassador", "envoy", "redis"]
    has_ambassador = False
    for c in containers:
        if not isinstance(c, dict):
            continue
        c_name = (c.get("name") or "").lower()
        c_image = (c.get("image") or "").lower()
        for kw in ambassador_keywords:
            if kw in c_name or kw in c_image:
                has_ambassador = True
                break

    if not has_ambassador:
        return CheckResult(
            ok=False,
            error="未找到代理容器（Ambassador），容器名或镜像应包含 proxy/ambassador/envoy/redis 等关键字",
            hints=["Ambassador 容器通常是代理服务，如 redis-proxy、envoy 等"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Ambassador 模式让主容器通过 localhost 访问外部服务，屏蔽连接复杂性 🌉"],
    )


LEVEL_Q25_3 = Level(
    id="Q25.3",
    chapter="ch25",
    title="Ambassador 模式 - 代理容器",
    description="""
# Ambassador 模式 - 代理容器 🌉

**Ambassador 模式**使用一个代理容器作为主容器与外部服务之间的"大使"。主容器通过 localhost 与 Ambassador 通信，由 Ambassador 处理与外部服务的复杂连接逻辑。

## 任务

创建一个 Ambassador 模式的 Pod：
- `kind: Pod`，名称 `ambassador-demo`
- 主容器 `app`，镜像 `redis:7-alpine`，command 为 `["redis-cli", "-h", "localhost", "ping"]`
- Ambassador 代理容器 `redis-proxy`，镜像 `envoyproxy/envoy:v1.29-latest`
- Ambassador 监听 localhost，代理外部 Redis 连接

## 提示

Ambassador 模式中主容器通过 localhost 连接代理：
```yaml
spec:
  containers:
  - name: app              # 主容器，连接 localhost
    image: redis:7-alpine
    command: ["redis-cli", "-h", "localhost", "ping"]
  - name: redis-proxy      # 代理容器
    image: envoyproxy/envoy:v1.29-latest
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: ambassador-demo
spec:
  containers:
  - name: app
    image: redis:7-alpine
    command: ["redis-cli", "-h", "localhost", "ping"]
  # 添加 Ambassador 代理容器
""",
    check_fn=_check_253_ambassador,
    lesson=Lesson(
        concept="""\
## Ambassador 模式

**Ambassador 模式**使用一个代理容器（"大使"）代表主容器与外部服务通信。主容器只需连接 localhost，由 Ambassador 处理服务发现、负载均衡、TLS 加密等复杂逻辑。

### Ambassador 的核心价值

1. **简化主容器**：主容器只需连接 localhost，无需处理外部连接复杂性
2. **服务发现**：Ambassador 负责查找外部服务地址
3. **连接管理**：处理重连、连接池、负载均衡
4. **安全代理**：TLS 终止、认证等由 Ambassador 处理
5. **环境一致**：开发和生产环境使用相同的 localhost 连接方式

### 典型 Ambassador 场景

| 场景 | Ambassador 功能 | 代理目标 |
|------|----------------|---------|
| Redis 代理 | 连接池管理 | 外部 Redis 集群 |
| Envoy 代理 | 七层路由 + TLS | 多个后端服务 |
| MySQL 代理 | 读写分离 | MySQL 主从 |
| StatsD 代理 | 指标聚合转发 | 监控后端 |

### Ambassador 与 Sidecar 的区别

- **Sidecar**：辅助主容器的功能（日志、监控等），不一定代理外部连接
- **Ambassador**：专门作为代理，转发主容器与外部服务的通信
""",
        key_fields=[
            {"name": "spec.containers[]", "description": "至少 2 个容器：主容器 + Ambassador 代理", "required": True, "example": "[{name: app}, {name: redis-proxy}]"},
            {"name": "spec.containers[0].command", "description": "主容器通过 localhost 连接 Ambassador", "required": False, "example": "[redis-cli, -h, localhost, ping]"},
            {"name": "spec.containers[1].name", "description": "代理容器名称通常含 proxy/ambassador 关键字", "required": True, "example": "redis-proxy"},
        ],
        diagram="""\
  ┌──────────────── Pod (ambassador-demo) ──────────────┐
  │                                                      │
  │  ┌────────────┐    localhost    ┌──────────────┐     │
  │  │ 主容器 app  │ ──────────────► │ Ambassador   │     │
  │  │ redis-cli  │    简单连接      │ redis-proxy  │     │
  │  │            │ ◄────────────── │ envoy        │     │
  │  └────────────┘                 └──────┬───────┘     │
  │                                        │              │
  └────────────────────────────────────────┼──────────────┘
                                           │
                                           │ 复杂连接逻辑
                                           │ (服务发现/TLS/负载均衡)
                                           ▼
                                   ┌───────────────┐
                                   │  外部 Redis    │
                                   │  集群          │
                                   └───────────────┘
""",
        example_yaml="""\
apiVersion: v1                 # 核心 API
kind: Pod                      # 资源类型
metadata:                      # 元数据
  name: ambassador-demo        # Pod 名称
spec:                          # 规格
  containers:                  # 容器列表
  - name: app                  # 主容器
    image: redis:7-alpine      # Redis 客户端
    command:                   # 连接 localhost
    - redis-cli
    - "-h"
    - localhost
    - ping
  - name: redis-proxy          # Ambassador 代理容器
    image: envoyproxy/envoy:v1.29-latest  # Envoy 代理
""",
        common_errors=[
            "主容器直接连接外部服务地址而非 localhost（应通过 Ambassador 代理）",
            "Ambassador 和主容器端口冲突（同 Pod 容器共享网络）",
            "把 Ambassador 写成了独立的 Pod（应在同一 Pod 中通过 localhost 通信）",
            "Ambassador 没有配置代理规则（需要 Envoy 配置文件或环境变量）",
        ],
        tips=[
            "Ambassador 模式的核心优势是主容器无需感知外部服务的复杂性",
            "在 Istio Service Mesh 中，Envoy sidecar 就是 Ambassador 模式的体现",
            "Ambassador 适合需要连接管理、TLS 终止或服务发现的场景",
        ],
    ),
)


# ==================== Q25.4 Adapter 模式 ====================

def _check_254_adapter(user_yaml: str) -> CheckResult:
    """Q25.4 创建 Adapter 模式的 Pod"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Pod 的 YAML"],
        )

    pod_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Pod":
            pod_doc = doc
            break

    if not pod_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Pod",
            hints=["你需要创建一个 kind: Pod 的 YAML 📦"],
        )

    spec = pod_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    containers = spec.get("containers", [])
    if not isinstance(containers, list) or len(containers) < 2:
        return CheckResult(
            ok=False,
            error="Adapter 模式需要至少 2 个容器（主容器 + 适配器容器）",
            hints=["在 spec.containers 中定义主容器和适配器容器"],
        )

    # 查找适配器容器
    adapter_keywords = ["adapter", "formatter", "converter", "exporter", "fluentd", "fluent-bit"]
    has_adapter = False
    for c in containers:
        if not isinstance(c, dict):
            continue
        c_name = (c.get("name") or "").lower()
        c_image = (c.get("image") or "").lower()
        for kw in adapter_keywords:
            if kw in c_name or kw in c_image:
                has_adapter = True
                break

    if not has_adapter:
        return CheckResult(
            ok=False,
            error="未找到适配器容器，容器名或镜像应包含 adapter/formatter/exporter/fluentd 等关键字",
            hints=["Adapter 容器负责格式转换，如日志格式化、指标转换等"],
        )

    # 检查是否有共享卷
    volumes = spec.get("volumes", [])
    has_shared_vol = isinstance(volumes, list) and len(volumes) > 0
    if not has_shared_vol:
        return CheckResult(
            ok=False,
            error="Adapter 模式通常需要共享卷来传递数据",
            hints=["添加 spec.volumes 定义共享卷，如 emptyDir"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Adapter 模式将主容器输出标准化，实现系统间兼容 📎"],
    )


LEVEL_Q25_4 = Level(
    id="Q25.4",
    chapter="ch25",
    title="Adapter 模式 - 适配器容器",
    description="""
# Adapter 模式 - 适配器容器 📎

**Adapter 模式**使用一个适配器容器对主容器的输出进行标准化转换。主容器输出自有格式，适配器将其转换为系统标准格式。

## 任务

创建一个 Adapter 模式的 Pod：
- `kind: Pod`，名称 `adapter-demo`
- 主容器 `app`，镜像 `nginx:1.25`，挂载共享卷 `logs` 到 `/var/log/nginx`
- Adapter 容器 `log-formatter`，镜像 `fluent/fluent-bit:3.0`
- Adapter 挂载同一个 `logs` 卷到 `/var/log/input`
- 定义 emptyDir 卷 `logs`

## 提示

Adapter 通过共享卷读取主容器输出，转换格式后输出：
```yaml
spec:
  containers:
  - name: app              # 主容器，输出自有格式日志
    image: nginx:1.25
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  - name: log-formatter    # 适配器，转换日志格式
    image: fluent/fluent-bit:3.0
    volumeMounts:
    - name: logs
      mountPath: /var/log/input
  volumes:
  - name: logs
    emptyDir: {}
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: adapter-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  # 添加 Adapter 适配器容器 log-formatter
  volumes:
  - name: logs
    emptyDir: {}
""",
    check_fn=_check_254_adapter,
    lesson=Lesson(
        concept="""\
## Adapter 模式

**Adapter 模式**使用适配器容器对主容器的输出进行**标准化转换**。主容器可能输出自有格式的日志或指标，适配器将其转换为系统统一标准格式，使外部系统能够统一消费。

### Adapter 的核心价值

1. **格式标准化**：将异构输出统一为标准格式
2. **解耦转换逻辑**：主容器无需关心输出格式要求
3. **协议适配**：不同协议间的转换（如 JSON→Prometheus metrics）
4. **不侵入主容器**：通过共享卷读取输出，不修改主容器代码

### 典型 Adapter 场景

| 场景 | 主容器输出 | Adapter 转换 |
|------|-----------|-------------|
| 日志标准化 | Nginx 日志格式 | Fluent Bit → JSON |
| 监控指标 | 应用自有指标 | exporter → Prometheus 格式 |
| 消息转换 | 自定义协议 | 适配为标准 HTTP/JSON |
| 数据清洗 | 原始数据 | 格式化+过滤+增强 |

### 四种多容器模式对比

| 模式 | 核心功能 | 典型场景 |
|------|---------|---------|
| Init Container | 初始化环境 | 数据库迁移、配置生成 |
| Sidecar | 增强功能 | 日志收集、监控代理 |
| Ambassador | 代理外部连接 | Redis/MySQL 代理 |
| Adapter | 格式转换 | 日志标准化、指标转换 |
""",
        key_fields=[
            {"name": "spec.containers[]", "description": "至少 2 个容器：主容器 + Adapter", "required": True, "example": "[{name: app}, {name: log-formatter}]"},
            {"name": "spec.volumes", "description": "共享卷，Adapter 读取主容器输出", "required": True, "example": "[{name: logs, emptyDir: {}}]"},
            {"name": "spec.containers[].volumeMounts", "description": "主容器写入，Adapter 读取同一卷", "required": True, "example": "[{name: logs, mountPath: /var/log}]"},
        ],
        diagram="""\
  ┌──────────────── Pod (adapter-demo) ──────────────┐
  │                                                   │
  │  ┌──────────────┐         ┌─────────────────┐     │
  │  │  主容器 app   │         │  Adapter        │     │
  │  │  nginx:1.25  │         │  log-formatter  │     │
  │  │              │         │  fluent-bit     │     │
  │  │ /var/log/    │         │ /var/log/input  │     │
  │  │  nginx       │         │                 │     │
  │  └──────┬───────┘         └────────┬────────┘     │
  │         │ 写入日志                  │ 读取+转换     │
  │         ▼                          ▼               │
  │  ┌───────────────────────────────────────┐        │
  │  │       volume: logs (emptyDir)          │        │
  │  └───────────────────────────────────────┘        │
  │                                                   │
  └───────────────────────────────────────────────────┘

  数据流:
  app → (Nginx 日志) → 共享卷 → Adapter → (JSON 格式) → 外部系统
""",
        example_yaml="""\
apiVersion: v1               # 核心 API
kind: Pod                    # 资源类型
metadata:                    # 元数据
  name: adapter-demo         # Pod 名称
spec:                        # 规格
  containers:                # 容器列表
  - name: app                # 主容器
    image: nginx:1.25        # Nginx 镜像
    volumeMounts:            # 日志输出到共享卷
    - name: logs
      mountPath: /var/log/nginx
  - name: log-formatter      # Adapter 适配器
    image: fluent/fluent-bit:3.0  # Fluent Bit 镜像
    volumeMounts:            # 从共享卷读取日志
    - name: logs
      mountPath: /var/log/input
  volumes:                   # 卷定义
  - name: logs               # 共享卷名
    emptyDir: {}             # 临时空目录
""",
        common_errors=[
            "Adapter 和主容器没有共享卷，导致无法读取主容器输出",
            "Adapter 读取和主容器写入的挂载路径不一致（需要指向同一个卷）",
            "把 Adapter 写成了独立 Pod（应在同 Pod 中通过共享卷通信）",
            "Adapter 和 Sidecar 搞混：Adapter 侧重格式转换，Sidecar 侧重功能增强",
        ],
        tips=[
            "Adapter 模式常用于日志标准化（如 Nginx 日志转 JSON）",
            "Prometheus exporter 就是 Adapter 模式的典型应用",
            "Adapter 与主容器通过共享卷异步通信，互不阻塞",
        ],
    ),
)


# ==================== Q25.5 集群实战 - 完整多容器应用 ====================

def _check_255_multi_container_app(user_yaml: str) -> CheckResult:
    """Q25.5 创建一个完整的多容器应用"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写多文档 YAML，包含多种资源"],
        )

    # 查找 Deployment
    deploy_doc = None
    pod_doc = None
    svc_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Deployment" and deploy_doc is None:
            deploy_doc = doc
        elif kind == "Pod" and pod_doc is None:
            pod_doc = doc
        elif kind == "Service" and svc_doc is None:
            svc_doc = doc

    target_doc = deploy_doc or pod_doc
    if not target_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Deployment 或 Pod",
            hints=["你需要创建一个 Deployment 或 Pod 来运行多容器应用"],
        )

    # 获取 Pod spec
    if deploy_doc:
        spec = deploy_doc.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
    else:
        pod_spec = target_doc.get("spec", {})

    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="缺少 Pod spec", hints=[])

    # 检查 initContainers
    init_containers = pod_spec.get("initContainers", [])
    if not isinstance(init_containers, list) or not init_containers:
        return CheckResult(
            ok=False,
            error="缺少 initContainers（需要 Init Container 进行初始化）",
            hints=["多容器应用应包含 initContainers 做初始化"],
        )

    # 检查 containers（至少 2 个：主容器 + Sidecar）
    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list) or len(containers) < 2:
        return CheckResult(
            ok=False,
            error="containers 中至少需要 2 个容器（主容器 + Sidecar/Ambassador/Adapter）",
            hints=["多容器应用应包含主容器和至少一个辅助容器"],
        )

    # 检查共享卷
    volumes = pod_spec.get("volumes", [])
    if not isinstance(volumes, list) or not volumes:
        return CheckResult(
            ok=False,
            error="缺少 volumes（多容器应用需要共享卷）",
            hints=["定义 emptyDir 等共享卷用于容器间通信"],
        )

    # 检查 Service（可选但推荐）
    if not svc_doc:
        return CheckResult(
            ok=False,
            error="缺少 Service（多容器应用应通过 Service 对外暴露）",
            hints=["添加一个 Service 来暴露应用端口"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["完整的多容器应用 = Init Container + 主容器 + Sidecar + Service 🏗️"],
    )


LEVEL_Q25_5 = Level(
    id="Q25.5",
    chapter="ch25",
    title="集群实战 - 完整多容器应用",
    description="""
# 集群实战 - 完整多容器应用 🏗️

综合运用 Init Container、Sidecar 和 Service 构建一个完整的多容器应用。

## 任务

创建一个完整的多容器应用（多文档 YAML）：
1. **Deployment**（名称 `webapp`，replicas 2）
   - initContainer `init-config`：镜像 `busybox:1.36`，生成配置文件到共享卷
   - 主容器 `web`：镜像 `nginx:1.25`，挂载共享卷提供 Web 服务
   - Sidecar 容器 `metrics-exporter`：镜像 `nginx/nginx-prometheus-exporter:1.1`
   - 共享卷 `config`（emptyDir）
2. **Service**（名称 `webapp-svc`）
   - 端口 80，selector 匹配 `app: webapp`

## 提示

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
    spec:
      initContainers:
      - name: init-config
        image: busybox:1.36
        command: ["sh", "-c", "echo 'server ready' > /config/index.html"]
        volumeMounts:
        - name: config
          mountPath: /config
      containers:
      - name: web
        image: nginx:1.25
        volumeMounts:
        - name: config
          mountPath: /usr/share/nginx/html
      - name: metrics-exporter
        image: nginx/nginx-prometheus-exporter:1.1
      volumes:
      - name: config
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: webapp-svc
spec:
  selector:
    app: webapp
  ports:
  - port: 80
    targetPort: 80
```
""",
    starter_yaml="""\
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
    spec:
      # 添加 initContainers
      containers:
      - name: web
        image: nginx:1.25
      # 添加 sidecar 容器 metrics-exporter
      # 添加共享卷 config
---
apiVersion: v1
kind: Service
metadata:
  name: webapp-svc
spec:
  selector:
    app: webapp
  ports:
  - port: 80
    targetPort: 80
""",
    check_fn=_check_255_multi_container_app,
    lesson=Lesson(
        concept="""\
## 完整多容器应用

在生产环境中，多容器模式通常组合使用。一个典型的应用可能包含：

1. **Init Container**：初始化配置文件或等待依赖
2. **主容器**：运行业务逻辑
3. **Sidecar**：日志收集、监控指标导出
4. **Ambassador**：代理外部数据库连接
5. **Adapter**：标准化日志或指标格式
6. **Service**：对外暴露统一入口

### 生产级多容器架构示例

```
┌── Pod ──────────────────────────────────────┐
│  [init] → 生成配置文件 → 共享卷               │
│  [web]  → 读取配置，提供 HTTP 服务            │
│  [sidecar] → 收集日志 → 共享卷                │
│  [adapter] → 格式化日志 → 发送到日志系统       │
│  [ambassador] → 代理外部数据库连接            │
└─────────────────────────────────────────────┘
```

### 设计原则

1. **单一职责**：每个容器只做一件事
2. **松耦合**：容器间通过共享卷/localhost 通信
3. **独立伸缩**：需要独立伸缩的容器应放在不同 Pod
4. **资源管理**：每个容器都应设置 resources.requests/limits
""",
        key_fields=[
            {"name": "spec.initContainers", "description": "初始化容器，生成配置或等待依赖", "required": True, "example": "[{name: init-config, image: busybox:1.36}]"},
            {"name": "spec.containers", "description": "至少 2 个容器：主容器 + Sidecar", "required": True, "example": "[{name: web}, {name: metrics-exporter}]"},
            {"name": "spec.volumes", "description": "共享卷用于容器间数据传递", "required": True, "example": "[{name: config, emptyDir: {}}]"},
            {"name": "Service", "description": "对外暴露应用", "required": True, "example": "{selector: {app: webapp}, ports: [{port: 80}]}"},
        ],
        diagram="""\
  ┌──────── Deployment (webapp, replicas: 2) ────────────┐
  │  Template:                                           │
  │  spec:                                               │
  │    initContainers:                                   │
  │    - init-config → 生成 index.html → /config (共享卷)  │
  │                                                      │
  │    containers:                                       │
  │    - web (nginx:1.25) ← 读 /config → 提供服务          │
  │    - metrics-exporter (prometheus exporter)           │
  │                                                      │
  │    volumes:                                          │
  │    - config (emptyDir) ◄── 共享存储                   │
  └──────────────────────┬───────────────────────────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Service       │
                 │ webapp-svc    │
                 │ port: 80      │
                 └───────────────┘
""",
        example_yaml="""\
---
apiVersion: apps/v1              # Deployment API
kind: Deployment                 # 资源类型
metadata:                        # 元数据
  name: webapp                   # Deployment 名称
spec:                            # 规格
  replicas: 2                    # 副本数
  selector:                      # 标签选择器
    matchLabels:
      app: webapp
  template:                      # Pod 模板
    metadata:
      labels:
        app: webapp
    spec:                        # Pod 规格
      initContainers:            # 初始化容器
      - name: init-config        # 容器名
        image: busybox:1.36      # 镜像
        command:                 # 生成配置
        - sh
        - "-c"
        - "echo 'server ready' > /config/index.html"
        volumeMounts:            # 挂载共享卷
        - name: config
          mountPath: /config
      containers:                # 主容器列表
      - name: web                # 主容器
        image: nginx:1.25        # Nginx 镜像
        volumeMounts:            # 挂载共享卷
        - name: config
          mountPath: /usr/share/nginx/html
      - name: metrics-exporter   # Sidecar 监控导出
        image: nginx/nginx-prometheus-exporter:1.1
      volumes:                   # 卷定义
      - name: config             # 共享卷名
        emptyDir: {}             # 临时空目录
---
apiVersion: v1                   # Service API
kind: Service                    # 资源类型
metadata:                        # 元数据
  name: webapp-svc               # Service 名称
spec:                            # 规格
  selector:                      # 标签选择器
    app: webapp
  ports:                         # 端口映射
  - port: 80                     # Service 端口
    targetPort: 80               # Pod 端口
""",
        common_errors=[
            "initContainer 和主容器没有共享卷，初始化结果丢失",
            "Sidecar 容器没有设置 resources，可能消耗过多资源",
            "Service selector 与 Pod labels 不匹配",
            "多文档 YAML 忘记用 --- 分隔",
        ],
        tips=[
            "用 kubectl describe pod <pod> 查看所有容器的状态和事件",
            "用 kubectl logs <pod> --all-containers 查看所有容器日志",
            "多容器 Pod 的资源消耗是所有容器之和，注意资源规划",
        ],
    ),
)


# ==================== 章节导出 ====================

CHAPTER_25_LEVELS = [
    LEVEL_Q25_1,
    LEVEL_Q25_2,
    LEVEL_Q25_3,
    LEVEL_Q25_4,
    LEVEL_Q25_5,
]
