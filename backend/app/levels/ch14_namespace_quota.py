"""Chapter 14: Namespace & ResourceQuota（命名空间与资源配额）（5 关）

Q14.1 创建 Namespace
Q14.2 在 Namespace 中部署应用
Q14.3 创建 ResourceQuota
Q14.4 创建 LimitRange
Q14.5 集群实战 - 多团队资源隔离方案
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q14.1 创建 Namespace ====================

def _check_141_create_namespace(user_yaml: str) -> CheckResult:
    """Q14.1 创建一个 Namespace"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.namespaces:
        return CheckResult(
            ok=False,
            error="没有创建任何 Namespace",
            hints=["你需要 apply 一个 kind: Namespace 的 YAML 📦"],
        )

    ns_name = next(iter(state.namespaces))
    ns = state.namespaces[ns_name]

    # 验证 Namespace 结构
    metadata = ns.get("metadata", {})
    if not isinstance(metadata, dict):
        return CheckResult(ok=False, error="Namespace 缺少 metadata", hints=[])

    if not metadata.get("name"):
        return CheckResult(ok=False, error="Namespace 缺少 metadata.name", hints=[])

    # 验证 apiVersion
    api_version = ns.get("apiVersion", "")
    if api_version != "v1":
        return CheckResult(
            ok=False,
            error=f"apiVersion 应为 'v1'，实际为 '{api_version}'",
            hints=["Namespace 的 apiVersion 是 v1"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[f"Namespace '{ns_name}' 创建成功！Namespace 是资源隔离的基础 📦"],
    )


LEVEL_Q14_1 = Level(
    id="Q14.1",
    chapter="ch14",
    title="创建 Namespace",
    description="""
# 创建 Namespace 📦

**Namespace** 是 Kubernetes 中用于在集群内实现资源隔离的逻辑分区。不同的 Namespace 可以包含同名资源，互不冲突。

## 任务

创建一个名为 `dev` 的 Namespace：
- `kind: Namespace`
- `apiVersion: v1`
- `metadata.name: dev`

## 提示

Namespace 是最简单的 K8s 资源之一：
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dev
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Namespace
metadata:
  name: # 在这里填写 Namespace 名称
""",
    check_fn=_check_141_create_namespace,
    lesson=Lesson(
        concept="""\
## 什么是 Namespace？

**Namespace** 是 Kubernetes 集群内的**逻辑隔离单元**。它将一个物理集群划分为多个虚拟集群，不同 Namespace 中的资源相互隔离。

### Namespace 的作用

1. **资源隔离**：不同团队/环境可以使用各自的 Namespace
2. **名称隔离**：不同 Namespace 中可以有同名的 Pod、Service 等
3. **权限控制**：RBAC 可以按 Namespace 授予权限
4. **资源配额**：可以按 Namespace 限制资源使用量

### 系统默认 Namespace

| Namespace | 用途 |
|-----------|------|
| `default` | 默认命名空间，未指定时使用 |
| `kube-system` | K8s 系统组件 |
| `kube-public` | 公共资源（所有用户可读） |
| `kube-node-lease` | 节点心跳信息 |

### Namespace 的特点

- Namespace 是**集群级资源**（不在任何 Namespace 内）
- 删除 Namespace 会删除其中所有资源
- Namespace 名称必须符合 DNS 标签规范（小写字母、数字、连字符）
- 大多数资源都是 Namespace 级（Pod、Service、Deployment 等）
""",
        key_fields=[
            {"name": "apiVersion", "description": "API 版本，Namespace 使用 v1", "required": True, "example": "v1"},
            {"name": "kind", "description": "资源类型", "required": True, "example": "Namespace"},
            {"name": "metadata.name", "description": "Namespace 名称（DNS 标签格式）", "required": True, "example": "dev"},
            {"name": "metadata.labels", "description": "标签（可选，用于分类管理）", "required": False, "example": "env: dev"},
        ],
        diagram="""\
  Kubernetes 集群
  ┌─────────────────────────────────────────────────┐
  │                                                 │
  │  ┌─── Namespace: default ────┐                  │
  │  │  Pod-a  Service-a  Deploy-a│                  │
  │  └───────────────────────────┘                  │
  │                                                 │
  │  ┌─── Namespace: dev ────────┐                  │
  │  │  Pod-a  Service-a  Deploy-a│  ← 同名不冲突!   │
  │  └───────────────────────────┘                  │
  │                                                 │
  │  ┌─── Namespace: kube-system ┐                  │
  │  │  CoreDNS  kube-proxy  etc  │                  │
  │  └───────────────────────────┘                  │
  │                                                 │
  └─────────────────────────────────────────────────┘

  创建 Namespace:
  ┌───────────────────┐
  │  kind: Namespace   │
  │  metadata:         │
  │    name: dev       │  ← 创建逻辑隔离空间
  └───────────────────┘
""",
        example_yaml="""\
apiVersion: v1               # Namespace 使用 v1 API
kind: Namespace              # 资源类型: Namespace
metadata:                    # 元数据
  name: dev                  # Namespace 名称
  labels:                    # 标签（可选）
    env: development         # 环境标识
""",
        common_errors=[
            "Namespace 名称包含大写字母（必须小写）",
            "apiVersion 写成了 apps/v1（Namespace 使用 v1）",
            "在 Namespace 内创建 Namespace（Namespace 是集群级资源）",
            "Namespace 名称包含下划线（只允许连字符）",
        ],
        tips=[
            "用 kubectl get namespaces 查看所有 Namespace",
            "用 kubectl get pods -n <ns> 指定 Namespace 查看 Pod",
            "用 kubectl config set-context --current --namespace=<ns> 切换默认 Namespace",
        ],
    ),
)


# ==================== Q14.2 在 Namespace 中部署应用 ====================

def _check_142_deploy_in_namespace(user_yaml: str) -> CheckResult:
    """Q14.2 创建 Namespace 并在其中部署 Deployment"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 验证创建了 Namespace
    if not state.namespaces:
        return CheckResult(
            ok=False,
            error="没有创建任何 Namespace",
            hints=["先创建一个 Namespace，再在其中部署应用 📦"],
        )

    # 验证创建了 Deployment
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="没有创建任何 Deployment",
            hints=["在 Namespace 中创建一个 Deployment"],
        )

    # 检查 Deployment 是否指定了 namespace
    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_metadata = dep.get("metadata", {})
    if not isinstance(dep_metadata, dict):
        return CheckResult(ok=False, error="Deployment 缺少 metadata", hints=[])

    dep_ns = dep_metadata.get("namespace")
    if not dep_ns:
        return CheckResult(
            ok=False,
            error="Deployment 没有指定 namespace",
            hints=["在 metadata 中添加 namespace 来指定部署到哪个 Namespace 🎯"],
        )

    # 验证 namespace 在已创建的 Namespace 中
    if dep_ns not in state.namespaces:
        return CheckResult(
            ok=False,
            error=f"Deployment 的 namespace '{dep_ns}' 不存在于已创建的 Namespace 中",
            hints=[f"先创建 Namespace '{dep_ns}'，再在其中部署 Deployment"],
        )

    # 验证 Deployment 基本结构
    spec = dep.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Deployment 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict) or not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["spec.template.spec.containers[0].image 必须指定 📦"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            f"成功在 Namespace '{dep_ns}' 中部署了 Deployment '{dep_name}' 🎯",
            "不同 Namespace 中的资源相互隔离，可以安全地使用相同名称",
        ],
    )


LEVEL_Q14_2 = Level(
    id="Q14.2",
    chapter="ch14",
    title="在 Namespace 中部署应用",
    description="""
# 在 Namespace 中部署应用 🎯

创建 Namespace 后，你可以在其中部署应用。只需在资源的 `metadata.namespace` 中指定目标 Namespace。

## 任务

使用多文档 YAML（`---` 分隔）完成以下操作：
1. 创建一个 Namespace `production`
2. 在该 Namespace 中部署一个 `nginx:1.25` 的 Deployment

## 提示

用 `---` 分隔多个 YAML 文档：
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production    # ← 指定 Namespace
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
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Namespace
metadata:
  name: production
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  # 在这里添加 namespace: production
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
        # image 在这里补全
""",
    check_fn=_check_142_deploy_in_namespace,
    lesson=Lesson(
        concept="""\
## Namespace 作用域

在 Kubernetes 中，大多数资源都是 **Namespace 级**的，意味着它们存在于某个 Namespace 内。

### Namespace 级 vs 集群级资源

| 类型 | 资源示例 | 是否需要指定 namespace |
|------|---------|---------------------|
| Namespace 级 | Pod, Deployment, Service, ConfigMap | 是（默认 default） |
| 集群级 | Namespace, Node, ClusterRole, PV | 否 |

### 指定 Namespace 的方式

1. **YAML 中指定**（推荐用于声明式部署）：
```yaml
metadata:
  name: web-app
  namespace: production
```

2. **命令行指定**（适合临时操作）：
```bash
kubectl apply -f deploy.yaml -n production
kubectl get pods -n production
```

3. **设置默认 Namespace**：
```bash
kubectl config set-context --current --namespace=production
```

### DNS 与 Namespace

K8s 中 Service 的 DNS 名称包含 Namespace：
```
<service-name>.<namespace>.svc.cluster.local
```

例如：
- `web-app.default.svc.cluster.local` — default 命名空间
- `web-app.production.svc.cluster.local` — production 命名空间

同一 Namespace 内可以直接用 Service 名访问：`web-app`
跨 Namespace 访问需要完整域名：`web-app.production.svc.cluster.local`
""",
        key_fields=[
            {"name": "metadata.namespace", "description": "指定资源所属的 Namespace", "required": True, "example": "production"},
            {"name": "metadata.name", "description": "资源名称（在同一 Namespace 内唯一）", "required": True, "example": "web-app"},
            {"name": "spec.template.spec.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
        ],
        diagram="""\
  多文档 YAML: Namespace + Deployment

  ┌─────── YAML 文档 1 ───────┐
  │  kind: Namespace           │
  │  metadata:                 │
  │    name: production        │  创建命名空间
  └───────────────────────────┘
               │
            --- (文档分隔)
               │
  ┌─────── YAML 文档 2 ───────┐
  │  kind: Deployment          │
  │  metadata:                 │
  │    name: web-app           │
  │    namespace: production   │  ← 部署到该 Namespace
  │  spec:                     │
  │    template: ...           │
  └───────────────────────────┘
               │
               ▼
  ┌─── Namespace: production ──────────┐
  │  Deployment: web-app               │
  │    Pod-0 (nginx:1.25)              │
  │    Pod-1 (nginx:1.25)              │
  └────────────────────────────────────┘

  同名 Deployment 在不同 Namespace 不冲突:
  ┌─── Namespace: default ─────────────┐
  │  Deployment: web-app (不同实例)     │
  └────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1               # Namespace API 版本
kind: Namespace              # 资源类型
metadata:                    # 元数据
  name: production           # Namespace 名称
---                          # 文档分隔符
apiVersion: apps/v1          # Deployment API 版本
kind: Deployment             # 资源类型
metadata:                    # 元数据
  name: web-app              # Deployment 名称
  namespace: production      # 指定 Namespace
spec:                        # 规格定义
  replicas: 2                # 副本数
  selector:                  # 标签选择器
    matchLabels:
      app: web
  template:                  # Pod 模板
    metadata:
      labels:
        app: web
    spec:                    # Pod 规格
      containers:            # 容器列表
      - name: nginx          # 容器名
        image: nginx:1.25    # 镜像
""",
        common_errors=[
            "忘记在 Deployment 的 metadata 中写 namespace（会部署到 default）",
            "把 namespace 写在了 spec 下面（应在 metadata 下）",
            "Namespace 名称拼写不一致（创建的是 production，部署时写了 prod）",
            "多文档 YAML 忘记用 --- 分隔",
        ],
        tips=[
            "用 kubectl get deploy -n <ns> 查看指定 Namespace 的 Deployment",
            "用 kubectl get all -n <ns> 查看指定 Namespace 的所有资源",
            "跨 Namespace 访问 Service 使用完整 DNS: <svc>.<ns>.svc.cluster.local",
        ],
    ),
)


# ==================== Q14.3 创建 ResourceQuota ====================

def _check_143_create_resourcequota(user_yaml: str) -> CheckResult:
    """Q14.3 创建 ResourceQuota 限制命名空间资源"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.resourcequotas:
        return CheckResult(
            ok=False,
            error="没有创建任何 ResourceQuota",
            hints=["你需要 apply 一个 kind: ResourceQuota 的 YAML 📊"],
        )

    rq_name = next(iter(state.resourcequotas))
    rq = state.resourcequotas[rq_name]
    spec = rq.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="ResourceQuota 缺少 spec", hints=[])

    hard = spec.get("hard", {})
    if not isinstance(hard, dict) or not hard:
        return CheckResult(ok=False, error="ResourceQuota 缺少 spec.hard", hints=[])

    # 检查是否包含 CPU 限制
    has_cpu = any("cpu" in str(k).lower() for k in hard.keys())
    if not has_cpu:
        return CheckResult(
            ok=False,
            error="ResourceQuota 缺少 CPU 限制",
            hints=["在 spec.hard 中添加 requests.cpu 和 limits.cpu"],
        )

    # 检查是否包含 Memory 限制
    has_memory = any("memory" in str(k).lower() for k in hard.keys())
    if not has_memory:
        return CheckResult(
            ok=False,
            error="ResourceQuota 缺少 Memory 限制",
            hints=["在 spec.hard 中添加 requests.memory 和 limits.memory"],
        )

    # 检查是否包含 Pod 数量限制
    has_pods = any("pod" in str(k).lower() for k in hard.keys())
    if not has_pods:
        return CheckResult(
            ok=False,
            error="ResourceQuota 缺少 Pod 数量限制",
            hints=["在 spec.hard 中添加 pods: '10' 来限制 Pod 数量"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["ResourceQuota 创建成功！它将限制 Namespace 中的总资源使用量 📊"],
    )


LEVEL_Q14_3 = Level(
    id="Q14.3",
    chapter="ch14",
    title="创建 ResourceQuota",
    description="""
# 创建 ResourceQuota 📊

**ResourceQuota** 限制一个 Namespace 中可以使用的资源总量，包括 CPU、内存、Pod 数量等。

## 任务

创建一个 ResourceQuota，限制 Namespace 的总资源：
- `kind: ResourceQuota`
- `spec.hard` 包含：
  - `requests.cpu: "4"`
  - `requests.memory: "8Gi"`
  - `limits.cpu: "8"`
  - `limits.memory: "16Gi"`
  - `pods: "10"`

## 提示

ResourceQuota 通过 `spec.hard` 定义资源上限：
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    pods: "10"
```
""",
    starter_yaml="""\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: default
spec:
  hard:
    # 在这里添加 CPU、内存和 Pod 数量限制
    requests.cpu: "4"
    # 补全其他限制...
""",
    check_fn=_check_143_create_resourcequota,
    lesson=Lesson(
        concept="""\
## ResourceQuota 资源配额

**ResourceQuota** 限制了 Namespace 中资源的**总使用量**。它是多团队共享集群时的关键管理工具。

### 可配额的资源类型

| 类别 | 资源 | 示例 |
|------|------|------|
| **计算资源** | requests.cpu, requests.memory | "4", "8Gi" |
| **计算资源** | limits.cpu, limits.memory | "8", "16Gi" |
| **存储资源** | requests.storage | "100Gi" |
| **存储资源** | persistentvolumeclaims | "10" |
| **对象数量** | pods, services, configmaps | "10", "5" |
| **对象数量** | secrets, replicationcontrollers | "5" |

### 配额的工作机制

1. 创建 ResourceQuota 后，该 Namespace 中的 Pod **必须**设置 resources.requests 和 resources.limits
2. 如果没有设置资源请求的 Pod，将被拒绝创建
3. K8s 实时跟踪 Namespace 中的资源使用量
4. 超过配额时，新 Pod 创建请求被拒绝

### 配额示例

```yaml
spec:
  hard:
    requests.cpu: "4"        # 所有 Pod 的 CPU 请求总和不超过 4 核
    requests.memory: "8Gi"   # 所有 Pod 的内存请求总和不超过 8Gi
    limits.cpu: "8"          # 所有 Pod 的 CPU 限制总和不超过 8 核
    limits.memory: "16Gi"    # 所有 Pod 的内存限制总和不超过 16Gi
    pods: "10"               # 最多 10 个 Pod
```

### 使用场景

- **多团队共享集群**：每个团队一个 Namespace + ResourceQuota
- **多环境隔离**：dev/test/prod 各有不同配额
- **防资源浪费**：防止某个 Namespace 创建过多 Pod
""",
        key_fields=[
            {"name": "spec.hard.requests.cpu", "description": "Namespace 中所有 Pod 的 CPU 请求总和上限", "required": True, "example": '"4"'},
            {"name": "spec.hard.requests.memory", "description": "Namespace 中所有 Pod 的内存请求总和上限", "required": True, "example": '"8Gi"'},
            {"name": "spec.hard.limits.cpu", "description": "Namespace 中所有 Pod 的 CPU 限制总和上限", "required": True, "example": '"8"'},
            {"name": "spec.hard.limits.memory", "description": "Namespace 中所有 Pod 的内存限制总和上限", "required": True, "example": '"16Gi"'},
            {"name": "spec.hard.pods", "description": "Namespace 中允许的最大 Pod 数量", "required": True, "example": '"10"'},
        ],
        diagram="""\
  ResourceQuota 工作机制

  ┌──── Namespace: team-a ────────────────────────┐
  │  ResourceQuota:                               │
  │    hard:                                      │
  │      requests.cpu: "4"    ── 已用: 3 ── 剩余: 1 │
  │      requests.memory: "8Gi" ── 已用: 5Gi      │
  │      limits.cpu: "8"      ── 已用: 6          │
  │      pods: "10"           ── 已用: 7          │
  │                                               │
  │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │
  │  │ Pod-1   │ │ Pod-2   │ │ Pod-3   │         │
  │  │ 1 CPU   │ │ 1 CPU   │ │ 1 CPU   │         │
  │  │ 2Gi Mem │ │ 2Gi Mem │ │ 1Gi Mem │         │
  │  └─────────┘ └─────────┘ └─────────┘         │
  │                                               │
  │  新 Pod 请求 2 CPU → 拒绝！剩余只有 1 CPU     │
  └───────────────────────────────────────────────┘

  配额检查流程:
  创建 Pod ──> 检查是否设置 resources ──> 检查总量是否超限
                    │                          │
                    ▼                          ▼
              未设置 → 拒绝              超限 → 拒绝
""",
        example_yaml="""\
apiVersion: v1               # ResourceQuota 使用 v1 API
kind: ResourceQuota          # 资源类型
metadata:                    # 元数据
  name: compute-quota        # ResourceQuota 名称
  namespace: default         # 作用的 Namespace
spec:                        # 规格定义
  hard:                      # 硬限制
    requests.cpu: "4"        # CPU 请求总上限
    requests.memory: "8Gi"   # 内存请求总上限
    limits.cpu: "8"          # CPU 限制总上限
    limits.memory: "16Gi"    # 内存限制总上限
    pods: "10"               # Pod 数量上限
""",
        common_errors=[
            "CPU/内存值没有加引号（YAML 中 '4' 和 4 可能被解析为不同类型）",
            "只设了 limits 没设 requests（两者都需要设置）",
            "忘记设 namespace（ResourceQuota 只对指定 Namespace 生效）",
            "内存单位混淆：Gi 是 GiB（2^30），G 是 GB（10^9），K8s 中推荐用 Gi",
        ],
        tips=[
            "用 kubectl get resourcequota -n <ns> 查看配额和使用情况",
            "用 kubectl describe resourcequota -n <ns> 查看详细用量",
            "设置了 ResourceQuota 后，Pod 必须设置 resources.requests/limits",
            "可以创建多个 ResourceQuota，它们的 hard 限制会合并",
        ],
    ),
)


# ==================== Q14.4 创建 LimitRange ====================

def _check_144_create_limitrange(user_yaml: str) -> CheckResult:
    """Q14.4 创建 LimitRange 限制单个 Pod 的资源"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.limitranges:
        return CheckResult(
            ok=False,
            error="没有创建任何 LimitRange",
            hints=["你需要 apply 一个 kind: LimitRange 的 YAML 📏"],
        )

    lr_name = next(iter(state.limitranges))
    lr = state.limitranges[lr_name]
    spec = lr.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="LimitRange 缺少 spec", hints=[])

    limits = spec.get("limits", [])
    if not isinstance(limits, list) or not limits:
        return CheckResult(ok=False, error="LimitRange 缺少 spec.limits", hints=[])

    limit_item = limits[0]
    if not isinstance(limit_item, dict):
        return CheckResult(ok=False, error="spec.limits[0] 格式错误", hints=[])

    # 检查 type
    limit_type = limit_item.get("type")
    if limit_type != "Container":
        return CheckResult(
            ok=False,
            error=f"limits[0].type 应为 'Container'，实际为 '{limit_type}'",
            hints=["设置 type: Container 来限制容器级别的资源"],
        )

    # 检查 default（limits）
    default = limit_item.get("default")
    if not isinstance(default, dict) or not default:
        return CheckResult(
            ok=False,
            error="缺少 spec.limits[0].default（默认资源限制）",
            hints=["添加 default: { cpu: 500m, memory: 512Mi } 设置默认 limits"],
        )

    if "cpu" not in default or "memory" not in default:
        return CheckResult(
            ok=False,
            error="default 中应同时包含 cpu 和 memory",
            hints=["default: { cpu: '500m', memory: '512Mi' }"],
        )

    # 检查 defaultRequest（requests）
    default_request = limit_item.get("defaultRequest")
    if not isinstance(default_request, dict) or not default_request:
        return CheckResult(
            ok=False,
            error="缺少 spec.limits[0].defaultRequest（默认资源请求）",
            hints=["添加 defaultRequest: { cpu: 100m, memory: 128Mi } 设置默认 requests"],
        )

    if "cpu" not in default_request or "memory" not in default_request:
        return CheckResult(
            ok=False,
            error="defaultRequest 中应同时包含 cpu 和 memory",
            hints=["defaultRequest: { cpu: '100m', memory: '128Mi' }"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["LimitRange 创建成功！它将为没有设置 resources 的 Pod 提供默认值 📏"],
    )


LEVEL_Q14_4 = Level(
    id="Q14.4",
    chapter="ch14",
    title="创建 LimitRange",
    description="""
# 创建 LimitRange 📏

**LimitRange** 限制单个 Pod/Container 的资源使用范围，并为未设置 resources 的 Pod 提供默认值。

## 任务

创建一个 LimitRange，为容器设置默认资源限制：
- `kind: LimitRange`
- `spec.limits[0].type: Container`
- `spec.limits[0].default`：默认 limits（cpu: 500m, memory: 512Mi）
- `spec.limits[0].defaultRequest`：默认 requests（cpu: 100m, memory: 128Mi）

## 提示

LimitRange 与 ResourceQuota 互补：
- ResourceQuota 限制 Namespace 的**总**资源
- LimitRange 限制**单个**容器的资源

```yaml
spec:
  limits:
  - type: Container
    default:           # 默认 limits（未设置时使用）
      cpu: 500m
      memory: 512Mi
    defaultRequest:    # 默认 requests（未设置时使用）
      cpu: 100m
      memory: 128Mi
```
""",
    starter_yaml="""\
apiVersion: v1
kind: LimitRange
metadata:
  name: container-limits
  namespace: default
spec:
  limits:
  - type: Container
    # 在这里添加 default 和 defaultRequest
    default:
      cpu: 500m
      memory: 512Mi
    # 补全 defaultRequest...
""",
    check_fn=_check_144_create_limitrange,
    lesson=Lesson(
        concept="""\
## LimitRange 资源限制范围

**LimitRange** 约束单个 Pod 或 Container 的资源分配，是 ResourceQuota 的补充。

### ResourceQuota vs LimitRange

| 特性 | ResourceQuota | LimitRange |
|------|-------------|------------|
| 作用对象 | Namespace 整体 | 单个 Pod/Container |
| 限制类型 | 总量上限 | 默认值 + 最小/最大值 |
| 典型用途 | 团队资源分配 | 防止单个 Pod 过大/过小 |

### LimitRange 的能力

1. **default**：未设置 limits 时的默认值
2. **defaultRequest**：未设置 requests 时的默认值
3. **max**：单个容器的最大资源限制
4. **min**：单个容器的最小资源请求
5. **maxLimitRequestRatio**：limits/requests 的最大比率（限制超配）

### 工作流程

```
用户创建 Pod（未设置 resources）
        │
        ▼
  LimitRange 准入控制器检查
        │
        ├── Pod 未设置 resources?
        │   └── 是: 注入 default 和 defaultRequest
        │
        ├── resources 超出 max?
        │   └── 是: 拒绝创建
        │
        ├── resources 低于 min?
        │   └── 是: 拒绝创建
        │
        └── 检查通过 → Pod 创建成功
```

### 配置示例

```yaml
spec:
  limits:
  - type: Container
    default:                    # 默认 limits
      cpu: 500m                 # 0.5 核
      memory: 512Mi
    defaultRequest:             # 默认 requests
      cpu: 100m                 # 0.1 核
      memory: 128Mi
    max:                        # 最大限制
      cpu: "2"
      memory: 2Gi
    min:                        # 最小请求
      cpu: 50m
      memory: 64Mi
    maxLimitRequestRatio:       # limits/requests 最大比率
      cpu: "4"
```
""",
        key_fields=[
            {"name": "spec.limits[].type", "description": "限制类型: Container 或 Pod", "required": True, "example": "Container"},
            {"name": "spec.limits[].default", "description": "默认 limits（未设置时使用）", "required": True, "example": "{cpu: 500m, memory: 512Mi}"},
            {"name": "spec.limits[].defaultRequest", "description": "默认 requests（未设置时使用）", "required": True, "example": "{cpu: 100m, memory: 128Mi}"},
            {"name": "spec.limits[].max", "description": "单个容器的最大资源限制", "required": False, "example": "{cpu: '2', memory: 2Gi}"},
            {"name": "spec.limits[].min", "description": "单个容器的最小资源请求", "required": False, "example": "{cpu: 50m, memory: 64Mi}"},
        ],
        diagram="""\
  LimitRange 工作机制

  ┌──── Namespace: default ──────────────────────┐
  │  LimitRange: container-limits                 │
  │  ┌─────────────────────────────────────────┐ │
  │  │  limits:                                │ │
  │  │  - type: Container                      │ │
  │  │    default:    {cpu: 500m, mem: 512Mi}  │ │  ← 默认 limits
  │  │    defaultRequest: {cpu: 100m, mem:128Mi}│ │  ← 默认 requests
  │  │    max:       {cpu: 2,    mem: 2Gi}     │ │  ← 最大限制
  │  │    min:       {cpu: 50m,  mem: 64Mi}    │ │  ← 最小请求
  │  └─────────────────────────────────────────┘ │
  │                                               │
  │  Pod-A (未设置 resources)                     │
  │    → 自动注入: requests={100m,128Mi}          │
  │                limits={500m,512Mi}            │
  │                                               │
  │  Pod-B (requests.cpu: 10)                     │
  │    → 拒绝！超过 max.cpu (2)                   │
  │                                               │
  │  Pod-C (requests.cpu: 10m)                    │
  │    → 拒绝！低于 min.cpu (50m)                 │
  └───────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1               # LimitRange 使用 v1 API
kind: LimitRange            # 资源类型
metadata:                   # 元数据
  name: container-limits    # LimitRange 名称
  namespace: default        # 作用的 Namespace
spec:                       # 规格定义
  limits:                   # 限制列表
  - type: Container         # 限制类型: 容器级
    default:                # 默认 limits
      cpu: 500m             # 0.5 核
      memory: 512Mi         # 512 MiB
    defaultRequest:         # 默认 requests
      cpu: 100m             # 0.1 核
      memory: 128Mi         # 128 MiB
    max:                    # 最大资源限制
      cpu: "2"              # 2 核
      memory: 2Gi           # 2 GiB
    min:                    # 最小资源请求
      cpu: 50m              # 0.05 核
      memory: 64Mi          # 64 MiB
""",
        common_errors=[
            "type 写成了 Pod（通常用 Container，Pod 类型限制所有容器总和）",
            "default 和 defaultRequest 搞混（default 是 limits，defaultRequest 是 requests）",
            "CPU 单位错误：500m 表示 0.5 核，不是 500 核",
            "忘记设 namespace（LimitRange 只对指定 Namespace 生效）",
            "min > max 导致所有 Pod 都无法创建",
        ],
        tips=[
            "用 kubectl get limitrange -n <ns> 查看 LimitRange",
            "用 kubectl describe limitrange -n <ns> 查看详细配置",
            "LimitRange 的 default/defaultRequest 解决了 ResourceQuora 要求 Pod 设置 resources 的问题",
            "1000m = 1 核 CPU，500m = 0.5 核 CPU",
        ],
    ),
)


# ==================== Q14.5 集群实战 - 多团队资源隔离方案 ====================

def _check_145_multi_team(user_yaml: str) -> CheckResult:
    """Q14.5 集群实战 - 多团队资源隔离方案"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 验证创建了 Namespace
    if not state.namespaces:
        return CheckResult(
            ok=False,
            error="没有创建任何 Namespace",
            hints=["多团队隔离方案需要先创建 Namespace 📦"],
        )

    # 验证创建了 ResourceQuota
    if not state.resourcequotas:
        return CheckResult(
            ok=False,
            error="没有创建 ResourceQuota",
            hints=["为 Namespace 创建 ResourceQuota 来限制资源总量 📊"],
        )

    # 验证创建了 LimitRange
    if not state.limitranges:
        return CheckResult(
            ok=False,
            error="没有创建 LimitRange",
            hints=["为 Namespace 创建 LimitRange 来限制单个 Pod 资源 📏"],
        )

    # 验证 ResourceQuota 关联到正确的 Namespace
    rq_name = next(iter(state.resourcequotas))
    rq = state.resourcequotas[rq_name]
    rq_ns = rq.get("metadata", {}).get("namespace", "default")
    if rq_ns not in state.namespaces and rq_ns != "default":
        return CheckResult(
            ok=False,
            error=f"ResourceQuota 的 namespace '{rq_ns}' 不在已创建的 Namespace 中",
            hints=["确保 ResourceQuota 的 namespace 与创建的 Namespace 一致"],
        )

    # 验证 ResourceQuota 有合理的资源配置
    rq_spec = rq.get("spec", {})
    hard = rq_spec.get("hard", {}) if isinstance(rq_spec, dict) else {}
    has_cpu = any("cpu" in str(k).lower() for k in hard.keys())
    has_memory = any("memory" in str(k).lower() for k in hard.keys())
    if not has_cpu or not has_memory:
        return CheckResult(
            ok=False,
            error="ResourceQuota 应同时包含 CPU 和 Memory 限制",
            hints=["确保 spec.hard 中有 requests.cpu/limits.cpu 和 memory"],
        )

    # 验证 LimitRange 有 default 配置
    lr_name = next(iter(state.limitranges))
    lr = state.limitranges[lr_name]
    lr_spec = lr.get("spec", {})
    limits = lr_spec.get("limits", []) if isinstance(lr_spec, dict) else []
    if isinstance(limits, list) and limits and isinstance(limits[0], dict):
        default = limits[0].get("default")
        if not isinstance(default, dict) or not default:
            return CheckResult(
                ok=False,
                error="LimitRange 应包含 default 配置",
                hints=["添加 default: { cpu: ..., memory: ... } 设置默认资源限制"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "多团队资源隔离方案校验通过！🎉",
            "在真实集群上验证：",
            "  kubectl get ns",
            "  kubectl get resourcequota -n <ns>",
            "  kubectl get limitrange -n <ns>",
            "  kubectl describe resourcequota -n <ns>",
        ],
    )


LEVEL_Q14_5 = Level(
    id="Q14.5",
    chapter="ch14",
    title="集群实战: 多团队资源隔离",
    description="""
# 集群实战: 多团队资源隔离 🏗️

在一个共享的 K8s 集群中，多个团队需要各自独立的资源空间。通过 Namespace + ResourceQuota + LimitRange 的组合，可以实现完整的资源隔离方案。

## 任务

使用多文档 YAML 创建一个完整的资源隔离方案：

1. **创建 Namespace** `team-alpha`
2. **创建 ResourceQuota** 限制该 Namespace 的总资源：
   - `requests.cpu: "2"`, `requests.memory: "4Gi"`
   - `limits.cpu: "4"`, `limits.memory: "8Gi"`
   - `pods: "20"`
3. **创建 LimitRange** 设置默认资源：
   - `default: { cpu: 500m, memory: 512Mi }`
   - `defaultRequest: { cpu: 100m, memory: 128Mi }`

## 验证步骤

```bash
# 1. 部署方案
kubectl apply -f team-alpha-quota.yaml

# 2. 查看 Namespace
kubectl get ns team-alpha

# 3. 查看资源配额
kubectl get resourcequota -n team-alpha
kubectl describe resourcequota -n team-alpha

# 4. 查看 LimitRange
kubectl get limitrange -n team-alpha
kubectl describe limitrange -n team-alpha

# 5. 测试：部署一个不设 resources 的 Pod
kubectl run test --image=nginx -n team-alpha
# LimitRange 会自动注入默认 resources
```
""",
    starter_yaml="""\
# 1. 创建 Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
---
# 2. 创建 ResourceQuota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-alpha-quota
  namespace: team-alpha
spec:
  hard:
    # 补全 CPU、内存和 Pod 数量限制
---
# 3. 创建 LimitRange
apiVersion: v1
kind: LimitRange
metadata:
  name: team-alpha-limits
  namespace: team-alpha
spec:
  limits:
  - type: Container
    # 补全 default 和 defaultRequest
""",
    check_fn=_check_145_multi_team,
    lesson=Lesson(
        concept="""\
## 多团队资源隔离方案

在生产环境中，多个团队共享一个 K8s 集群是常见场景。完整的资源隔离方案需要三层配合：

### 三层隔离架构

```
┌─────────────────────────────────────────────────────┐
│              Kubernetes 集群                         │
│                                                     │
│  ┌──── Namespace: team-alpha ──────────────────┐    │
│  │  ResourceQuota: 总量限制 (CPU: 2, Mem: 4Gi) │    │
│  │  LimitRange: 单 Pod 限制 (default: 500m)    │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │    │
│  │  │ Pod-A   │ │ Pod-B   │ │ Pod-C   │       │    │
│  │  │ 500m    │ │ 500m    │ │ 1000m   │       │    │
│  │  └─────────┘ └─────────┘ └─────────┘       │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌──── Namespace: team-beta ───────────────────┐    │
│  │  ResourceQuota: 总量限制 (CPU: 4, Mem: 8Gi) │    │
│  │  LimitRange: 单 Pod 限制 (default: 1000m)   │    │
│  │  ┌─────────┐ ┌─────────┐                    │    │
│  │  │ Pod-D   │ │ Pod-E   │                    │    │
│  │  │ 1000m   │ │ 2000m   │                    │    │
│  │  └─────────┘ └─────────┘                    │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### 各层职责

| 层级 | 资源 | 职责 |
|------|------|------|
| **Namespace** | 逻辑隔离 | 团队/环境隔离，名称隔离 |
| **ResourceQuota** | 总量限制 | 限制 Namespace 总资源使用量 |
| **LimitRange** | 单体限制 | 限制单个 Pod 资源，提供默认值 |

### 完整工作流程

1. **管理员**创建 Namespace 和配额
2. **开发者**在该 Namespace 中创建 Pod
3. **LimitRange** 为未设置 resources 的 Pod 注入默认值
4. **ResourceQuota** 检查总量是否超限
5. **通过检查** → Pod 创建成功
6. **未通过** → Pod 创建被拒绝

### 最佳实践

1. **为每个团队创建独立 Namespace**
2. **设置合理的 ResourceQuota**（根据团队规模和需求）
3. **配置 LimitRange 默认值**（避免 Pod 不设 resources）
4. **配合 RBAC** 控制团队只能访问自己的 Namespace
5. **监控资源使用**（用 kubectl describe resourcequota 定期检查）
""",
        key_fields=[
            {"name": "Namespace", "description": "创建团队专属的命名空间", "required": True, "example": "team-alpha"},
            {"name": "ResourceQuota.spec.hard", "description": "限制 Namespace 总资源", "required": True, "example": "{requests.cpu: '2', pods: '20'}"},
            {"name": "LimitRange.spec.limits[].default", "description": "单个容器的默认 limits", "required": True, "example": "{cpu: 500m, memory: 512Mi}"},
            {"name": "LimitRange.spec.limits[].defaultRequest", "description": "单个容器的默认 requests", "required": True, "example": "{cpu: 100m, memory: 128Mi}"},
        ],
        diagram="""\
  多团队资源隔离方案

  管理员操作:
  ┌──────────────────────────────────────────┐
  │  1. kubectl apply -f team-alpha.yaml    │
  └──────────────────┬───────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
  ┌────────────┐ ┌────────────┐ ┌────────────┐
  │ Namespace  │ │ Resource   │ │ LimitRange │
  │ team-alpha │ │ Quota      │ │            │
  └────────────┘ └────────────┘ └────────────┘
         │           │           │
         └───────────┼───────────┘
                     │
                     ▼
  ┌─── Namespace: team-alpha ────────────────┐
  │                                          │
  │  开发者创建 Pod:                          │
  │  ┌──────────────────────────────────┐   │
  │  │ kubectl run web --image=nginx    │   │
  │  │ (未设置 resources)                │   │
  │  └──────────────┬───────────────────┘   │
  │                 │                        │
  │    LimitRange 注入默认值:                │
  │    requests: {cpu:100m, memory:128Mi}   │
  │    limits:   {cpu:500m, memory:512Mi}   │
  │                 │                        │
  │    ResourceQuota 检查总量:               │
  │    已用 + 新请求 ≤ hard 限制?            │
  │                 │                        │
  │           ┌─────┴─────┐                  │
  │           ▼           ▼                  │
  │        通过 ✓      超限 ✗                │
  │        Pod 创建    Pod 拒绝              │
  └──────────────────────────────────────────┘
""",
        example_yaml="""\
# 1. 创建 Namespace
apiVersion: v1               # Namespace API 版本
kind: Namespace              # 资源类型
metadata:                    # 元数据
  name: team-alpha           # 团队命名空间
---                          # 文档分隔符
# 2. 创建 ResourceQuota
apiVersion: v1               # ResourceQuota API 版本
kind: ResourceQuota          # 资源类型
metadata:                    # 元数据
  name: team-alpha-quota     # 配额名称
  namespace: team-alpha      # 作用命名空间
spec:                        # 规格定义
  hard:                      # 硬限制
    requests.cpu: "2"        # CPU 请求总上限
    requests.memory: "4Gi"   # 内存请求总上限
    limits.cpu: "4"          # CPU 限制总上限
    limits.memory: "8Gi"     # 内存限制总上限
    pods: "20"               # Pod 数量上限
---                          # 文档分隔符
# 3. 创建 LimitRange
apiVersion: v1               # LimitRange API 版本
kind: LimitRange            # 资源类型
metadata:                   # 元数据
  name: team-alpha-limits   # 限制范围名称
  namespace: team-alpha     # 作用命名空间
spec:                       # 规格定义
  limits:                   # 限制列表
  - type: Container         # 容器级限制
    default:                # 默认 limits
      cpu: 500m             # 0.5 核
      memory: 512Mi         # 512 MiB
    defaultRequest:         # 默认 requests
      cpu: 100m             # 0.1 核
      memory: 128Mi         # 128 MiB
""",
        common_errors=[
            "ResourceQuota 或 LimitRange 的 namespace 与创建的 Namespace 不一致",
            "只创建了 ResourceQuota 没创建 LimitRange（导致不设 resources 的 Pod 被拒绝）",
            "ResourceQuota 的 hard 值设得太小，连默认 Pod 都创建不了",
            "多文档 YAML 中忘记用 --- 分隔不同资源",
            "LimitRange 的 default 值超过了 ResourceQuota 的 hard 限制",
        ],
        tips=[
            "用 kubectl describe resourcequota -n <ns> 查看配额使用详情",
            "用 kubectl describe limitrange -n <ns> 查看 LimitRange 配置",
            "创建 Pod 后用 kubectl get pod -o yaml 查看自动注入的 resources",
            "生产环境中配合 RBAC + NetworkPolicy 实现更完整的隔离",
            "定期监控各 Namespace 的资源使用情况，及时调整配额",
        ],
    ),
)


CHAPTER_14_LEVELS: list[Level] = [
    LEVEL_Q14_1, LEVEL_Q14_2, LEVEL_Q14_3, LEVEL_Q14_4, LEVEL_Q14_5,
]
