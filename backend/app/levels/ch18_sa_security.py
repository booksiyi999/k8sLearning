"""Chapter 18: ServiceAccount & 安全上下文（5 关）

Q18.1 创建 ServiceAccount - 身份基础
Q18.2 Pod 使用 ServiceAccount - 绑定身份到 Pod
Q18.3 SecurityContext - 容器安全上下文
Q18.4 Pod Security Standards - restricted/baseline/privileged
Q18.5 集群实战 - 最小权限应用部署
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q18.1 创建 ServiceAccount ====================

def _check_181_create_sa(user_yaml: str) -> CheckResult:
    """Q18.1 创建一个 ServiceAccount"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.serviceaccounts:
        return CheckResult(
            ok=False,
            error="没有创建任何 ServiceAccount",
            hints=["你需要 apply 一个 kind: ServiceAccount 的 YAML"],
        )

    sa_name = next(iter(state.serviceaccounts))
    sa = state.serviceaccounts[sa_name]
    metadata = sa.get("metadata", {})
    if not isinstance(metadata, dict) or not metadata.get("name"):
        return CheckResult(
            ok=False,
            error="ServiceAccount 缺少 metadata.name",
            hints=[],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["ServiceAccount 创建成功！它是 Pod 在集群中的'身份证' 🪪"],
    )


LEVEL_Q18_1 = Level(
    id="Q18.1",
    chapter="ch18",
    title="创建 ServiceAccount",
    description="""
# 创建 ServiceAccount 🪪

**ServiceAccount（服务账户）** 是 Kubernetes 中 Pod 的身份标识。每个 Pod 都关联一个 ServiceAccount，用于访问 API Server。

## 任务

创建一个 ServiceAccount：
- `kind: ServiceAccount`
- `apiVersion: v1`
- `metadata.name: app-sa`

## 提示

ServiceAccount 是最简单的 K8s 资源之一：
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
```

创建后，K8s 会自动为它生成一个 Secret（包含 token），Pod 可以挂载使用。
""",
    starter_yaml="""\
apiVersion: v1
kind: ServiceAccount
metadata:
  # name: app-sa
  pass: true
""",
    check_fn=_check_181_create_sa,
    lesson=Lesson(
        concept="""\
## 什么是 ServiceAccount？

**ServiceAccount** 是 Kubernetes 中用于**标识进程身份**的资源。当 Pod 中的容器需要访问 API Server 时，它使用关联的 ServiceAccount 进行认证。

### User vs ServiceAccount

| 类型 | 说明 | 使用者 |
|------|------|--------|
| User | 人类用户 | kubectl、Dashboard |
| ServiceAccount | 进程/机器 | Pod 中的容器 |

### 默认 ServiceAccount

每个命名空间创建时，K8s 自动创建一个名为 `default` 的 ServiceAccount。
如果不指定，Pod 默认使用 `default` SA。

```bash
# 查看所有 ServiceAccount
kubectl get sa

# 查看 default 命名空间的 SA
kubectl get sa -n default
# NAME      SECRETS   AGE
# default   1         30d
```

### ServiceAccount 的自动 Token

K8s 1.24+ 的行为：
- 创建 SA 时**不再**自动创建永久 token Secret
- Pod 使用 SA 时，通过 **ProjectedVolume** 注入短期 token
- 如需手动获取 token，创建 TokenRequest 或长期 Secret

```
ServiceAccount (app-sa)
    │
    ├── Pod 引用此 SA
    │     └── K8s 自动挂载 token 到 /var/run/secrets/kubernetes.io/serviceaccount/
    │         ├── token      (JWT 访问令牌)
    │         ├── ca.crt     (CA 证书)
    │         └── namespace  (命名空间名)
    │
    └── RBAC 绑定
          └── RoleBinding/ClusterRoleBinding 赋予权限
```
""",
        key_fields=[
            {"name": "metadata.name", "description": "ServiceAccount 名称", "required": True, "example": "app-sa"},
            {"name": "metadata.namespace", "description": "命名空间（默认 default）", "required": False, "example": "default"},
            {"name": "imagePullSecrets", "description": "拉取私有镜像时使用的 Secret", "required": False, "example": "[{name: regcred}]"},
        ],
        diagram="""\
  ┌─────────── ServiceAccount ────────────┐
  │                                        │
  │  apiVersion: v1                        │
  │  kind: ServiceAccount                  │
  │  metadata:                             │
  │    name: app-sa                        │
  │    namespace: default                  │
  │                                        │
  │  (K8s 自动管理)                        │
  │  ├── Token (JWT) ──────────┐           │
  │  ├── CA Certificate ───────┼──► Secret │
  │  └── Namespace info ───────┘           │
  │                                        │
  └────────────────────────────────────────┘
                   │
                   │  Pod 引用此 SA
                   ▼
  ┌────────────────────────────────────────┐
  │  Pod 容器内:                            │
  │  /var/run/secrets/                     │
  │    kubernetes.io/serviceaccount/       │
  │      ├── token     (JWT)               │
  │      ├── ca.crt    (CA)                │
  │      └── namespace (ns)                │
  └────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                # 核心 API 版本
kind: ServiceAccount          # 资源类型
metadata:                     # 元数据
  name: app-sa                # SA 名称
  namespace: default          # 命名空间（可省略，默认 default）
""",
        common_errors=[
            "把 ServiceAccount 和 User 搞混（SA 是给进程用的，User 是给人用的）",
            "以为创建 SA 就有权限了（还需要 RoleBinding 赋予权限）",
            "在生产环境使用 default SA（应创建专用 SA 实现最小权限）",
        ],
        tips=[
            "用 kubectl get sa 查看所有 ServiceAccount",
            "用 kubectl describe sa <name> 查看 SA 详情和关联的 Secret",
            "每个命名空间都有一个 default SA，但不建议在生产中使用",
        ],
    ),
)


# ==================== Q18.2 Pod 使用 ServiceAccount ====================

def _check_182_pod_with_sa(user_yaml: str) -> CheckResult:
    """Q18.2 创建一个使用指定 ServiceAccount 的 Pod"""
    try:
        state = ClusterState()
        # 预置 ServiceAccount
        state = preset_state(state, """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["你需要 apply 一个 kind: Pod 的 YAML"],
        )

    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    sa_name = spec.get("serviceAccountName")
    if not sa_name:
        return CheckResult(
            ok=False,
            error="Pod 未指定 spec.serviceAccountName",
            hints=["添加 spec.serviceAccountName: app-sa"],
        )

    if sa_name != "app-sa":
        return CheckResult(
            ok=False,
            error=f"serviceAccountName 应为 'app-sa'，实际为 '{sa_name}'",
            hints=["使用预置的 app-sa ServiceAccount"],
        )

    # 检查容器
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])
    c = containers[0]
    if not isinstance(c, dict) or not c.get("image"):
        return CheckResult(ok=False, error="容器缺少 image", hints=[])

    return CheckResult(
        ok=True, state=state,
        hints=["Pod 现在以 app-sa 身份运行，拥有该 SA 的所有权限 🔑"],
    )


LEVEL_Q18_2 = Level(
    id="Q18.2",
    chapter="ch18",
    title="Pod 使用 ServiceAccount",
    description="""
# Pod 使用 ServiceAccount 🔑

创建 Pod 时可以指定 `serviceAccountName`，让 Pod 以该 ServiceAccount 的身份访问 API Server。

## 任务

集群中已有 ServiceAccount `app-sa`。创建一个 Pod 使用它：
- `kind: Pod`
- `spec.serviceAccountName: app-sa`
- 容器使用 `busybox:1.36`，执行 `sleep 3600`

## 提示

在 Pod spec 中指定 serviceAccountName：
```yaml
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  # serviceAccountName: app-sa
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
""",
    check_fn=_check_182_pod_with_sa,
    lesson=Lesson(
        concept="""\
## Pod 绑定 ServiceAccount

每个 Pod 都关联一个 ServiceAccount。通过 `spec.serviceAccountName` 指定。

### Pod 如何使用 SA

```
Pod 创建
  │
  ├── spec.serviceAccountName: app-sa
  │
  ▼
K8s 自动注入
  │
  ├── 挂载 SA Token 到容器
  │   /var/run/secrets/kubernetes.io/serviceaccount/
  │     ├── token      (JWT 令牌)
  │     ├── ca.crt     (CA 证书)
  │     └── namespace  (命名空间)
  │
  └── 容器内可用此 token 访问 API Server
      curl -k -H "Authorization: Bearer $(cat token)" \\
        https://kubernetes/api/v1/namespaces/default/pods
```

### automountServiceAccountToken

如果不希望自动挂载 token（安全加固），可以设置：

```yaml
# 方式 1: 在 ServiceAccount 上禁用
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
automountServiceAccountToken: false

# 方式 2: 在 Pod 上禁用
spec:
  automountServiceAccountToken: false
  containers:
  - ...
```

### 为什么需要专用 SA？

| 场景 | 用 default SA | 用专用 SA |
|------|--------------|----------|
| 安全 | 所有 Pod 共享权限 | 每个 Pod 最小权限 |
| 审计 | 无法区分来源 | 可追踪到具体应用 |
| 权限 | 过大或过小 | 精确控制 |
| 最佳实践 | ❌ 不推荐 | ✅ 推荐 |

### 实际验证

```bash
# 进入 Pod 容器
kubectl exec -it app-pod -- sh

# 查看 token
cat /var/run/secrets/kubernetes.io/serviceaccount/token

# 用 token 访问 API Server
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -k -H "Authorization: Bearer $TOKEN" \\
  https://kubernetes/api/v1/namespaces/default/pods
```
""",
        key_fields=[
            {"name": "spec.serviceAccountName", "description": "Pod 使用的 ServiceAccount 名称", "required": True, "example": "app-sa"},
            {"name": "spec.automountServiceAccountToken", "description": "是否自动挂载 SA token", "required": False, "example": "true"},
            {"name": "spec.containers[].image", "description": "容器镜像", "required": True, "example": "busybox:1.36"},
        ],
        diagram="""\
  ┌──────────── Pod (app-pod) ────────────────┐
  │  spec:                                    │
  │    serviceAccountName: app-sa  ◄── 绑定   │
  │    containers:                            │
  │    - name: app                            │
  │      image: busybox:1.36                  │
  │      volumeMounts:                        │
  │      - mountPath: /var/run/secrets/...    │
  │        name: sa-token           ◄── 自动  │
  │    volumes:                      注入     │
  │    - name: sa-token                       │
  │      projected:                           │
  │        sources:                           │
  │        - serviceAccountToken:             │
  │            path: token          ◄── JWT   │
  └───────────────┬───────────────────────────┘
                  │
                  ▼
  ┌───────────────────────────────────────────┐
  │  容器内访问 API Server:                    │
  │                                           │
  │  Authorization: Bearer <JWT token>        │
  │  ────────────────────────────────►        │
  │  API Server 验证 token -> 确认身份         │
  │  检查 RBAC -> 决定是否允许操作             │
  └───────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                       # 核心 API
kind: Pod                           # 资源类型
metadata:                           # 元数据
  name: app-pod                     # Pod 名称
spec:                               # Pod 规格
  serviceAccountName: app-sa        # 指定 ServiceAccount
  containers:                       # 容器列表
  - name: app                       # 容器名
    image: busybox:1.36             # 镜像
    command:                        # 启动命令
    - sleep
    - "3600"
""",
        common_errors=[
            "忘记在 Pod spec 中设置 serviceAccountName（默认使用 default SA）",
            "SA 名称拼写错误（如 app-sa 写成 app_sa）",
            "试图使用不存在的 ServiceAccount（会创建失败）",
            "在生产环境不设 automountServiceAccountToken: false 导致 token 泄漏风险",
        ],
        tips=[
            "用 kubectl describe pod <name> 查看 Pod 挂载的 SA token volume",
            "用 kubectl auth can-i --list --as=system:serviceaccount:default:app-sa 查看 SA 权限",
            "如果 Pod 不需要访问 API Server，设 automountServiceAccountToken: false 更安全",
        ],
    ),
)


# ==================== Q18.3 SecurityContext ====================

def _check_183_security_context(user_yaml: str) -> CheckResult:
    """Q18.3 创建带安全上下文的 Pod"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["你需要 apply 一个 kind: Pod 的 YAML"],
        )

    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    # 检查容器
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])
    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查 securityContext（容器级或 Pod 级）
    pod_sc = spec.get("securityContext", {})
    container_sc = c.get("securityContext", {})

    if not isinstance(pod_sc, dict):
        pod_sc = {}
    if not isinstance(container_sc, dict):
        container_sc = {}

    # 合并检查 runAsNonRoot
    run_as_non_root = container_sc.get("runAsNonRoot", pod_sc.get("runAsNonRoot"))
    if run_as_non_root is not True:
        return CheckResult(
            ok=False,
            error="缺少 runAsNonRoot: true",
            hints=[
                "在 securityContext 中设置 runAsNonRoot: true 💡",
                "可放在 Pod 级或容器级 securityContext",
            ],
        )

    # 检查 readOnlyRootFilesystem
    read_only = container_sc.get("readOnlyRootFilesystem")
    if read_only is not True:
        return CheckResult(
            ok=False,
            error="缺少 readOnlyRootFilesystem: true",
            hints=[
                "在容器 securityContext 中设置 readOnlyRootFilesystem: true",
                "这使容器的根文件系统变为只读 🔒",
            ],
        )

    # 检查 runAsUser（非 root 用户）
    run_as_user = container_sc.get("runAsUser", pod_sc.get("runAsUser"))
    if run_as_user is None or str(run_as_user) == "0":
        return CheckResult(
            ok=False,
            error="runAsUser 应设为非 0 值（非 root 用户）",
            hints=["设置 runAsUser: 1000 或其他非 0 的 UID"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["安全上下文配置良好！runAsNonRoot + readOnlyRootFilesystem 是安全最佳实践 🔒"],
    )


LEVEL_Q18_3 = Level(
    id="Q18.3",
    chapter="ch18",
    title="SecurityContext - 容器安全",
    description="""
# SecurityContext - 容器安全上下文 🔒

**SecurityContext** 定义 Pod 或容器的安全设置，包括运行用户、权限、文件系统等。

## 任务

创建一个安全加固的 Pod：
- `spec.containers[0].securityContext.runAsNonRoot: true`
- `spec.containers[0].securityContext.readOnlyRootFilesystem: true`
- `spec.containers[0].securityContext.runAsUser: 1000`
- 容器使用 `nginx:1.25-alpine`

## 提示

securityContext 可在 Pod 级或容器级设置：
```yaml
spec:
  securityContext:        # Pod 级（所有容器继承）
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:      # 容器级（覆盖 Pod 级）
      readOnlyRootFilesystem: true
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    # securityContext:
    #   runAsNonRoot: true
    #   readOnlyRootFilesystem: true
    #   runAsUser: 1000
""",
    check_fn=_check_183_security_context,
    lesson=Lesson(
        concept="""\
## SecurityContext

**SecurityContext** 让你控制 Pod/容器的安全行为，是容器安全加固的核心工具。

### Pod 级 vs 容器级 SecurityContext

```
Pod spec:
  securityContext:          ← Pod 级（所有容器继承）
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
  containers:
  - name: web
    securityContext:        ← 容器级（覆盖 Pod 级）
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
```

### 关键安全字段

| 字段 | 说明 | 安全建议 |
|------|------|---------|
| runAsNonRoot | 禁止以 root 运行 | ✅ true |
| runAsUser | 指定运行 UID | ✅ 非 0 |
| runAsGroup | 指定运行 GID | ✅ 非 0 |
| readOnlyRootFilesystem | 根文件系统只读 | ✅ true |
| allowPrivilegeEscalation | 禁止提权 | ✅ false |
| privileged | 特权模式 | ❌ false |
| capabilities.drop | 丢弃 Linux 能力 | ✅ [ALL] |
| capabilities.add | 添加 Linux 能力 | 最小化 |
| fsGroup | 文件系统组 | 按需 |

### runAsNonRoot 的作用

```yaml
# ❌ 危险: 默认可能以 root 运行
spec:
  containers:
  - name: app
    image: myapp:v1

# ✅ 安全: 强制非 root
spec:
  containers:
  - name: app
    image: myapp:v1
    securityContext:
      runAsNonRoot: true    # K8s 检查镜像 USER，root 则拒绝启动
      runAsUser: 1000       # 显式指定非 root UID
```

### readOnlyRootFilesystem

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

- 容器根文件系统 `/` 变为只读
- 需要写入的目录必须用 volumeMounts 挂载
- 防止攻击者写入恶意文件

```yaml
# 需要写入 /tmp 时挂载 emptyDir
containers:
- name: app
  image: myapp:v1
  securityContext:
    readOnlyRootFilesystem: true
  volumeMounts:
  - mountPath: /tmp
    name: tmp
volumes:
- name: tmp
  emptyDir: {}
```
""",
        key_fields=[
            {"name": "securityContext.runAsNonRoot", "description": "禁止以 root 用户运行", "required": True, "example": "true"},
            {"name": "securityContext.runAsUser", "description": "指定运行用户 UID", "required": True, "example": "1000"},
            {"name": "securityContext.readOnlyRootFilesystem", "description": "根文件系统只读", "required": True, "example": "true"},
            {"name": "securityContext.allowPrivilegeEscalation", "description": "禁止提权", "required": False, "example": "false"},
        ],
        diagram="""\
  ┌──────── Pod SecurityContext ────────────────┐
  │                                              │
  │  Pod 级 securityContext:                     │
  │  ┌────────────────────────────┐              │
  │  │ runAsNonRoot: true         │ ← 禁止 root │
  │  │ runAsUser: 1000            │ ← 非 root   │
  │  │ fsGroup: 2000              │ ← 文件组    │
  │  └────────────────────────────┘              │
  │         │ 继承                                │
  │         ▼                                    │
  │  容器级 securityContext:                     │
  │  ┌────────────────────────────┐              │
  │  │ readOnlyRootFilesystem:true│ ← 只读根fs  │
  │  │ allowPrivilegeEscalation:  │              │
  │  │   false                    │ ← 禁止提权  │
  │  │ capabilities:              │              │
  │  │   drop: [ALL]              │ ← 丢弃能力  │
  │  └────────────────────────────┘              │
  │                                              │
  │  效果:                                       │
  │  ✅ 容器以 UID 1000 运行                     │
  │  ✅ 无法写入根文件系统                       │
  │  ✅ 无法提权                                 │
  │  ✅ 无 Linux 能力                            │
  └──────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                           # 核心 API
kind: Pod                               # 资源类型
metadata:                               # 元数据
  name: secure-pod                      # Pod 名称
spec:                                   # Pod 规格
  securityContext:                      # Pod 级安全上下文
    runAsNonRoot: true                  # 禁止 root 运行
    runAsUser: 1000                     # 运行用户 UID
    runAsGroup: 3000                    # 运行组 GID
    fsGroup: 2000                       # 文件系统组
  containers:                           # 容器列表
  - name: web                           # 容器名
    image: nginx:1.25-alpine            # 镜像
    securityContext:                    # 容器级安全上下文
      readOnlyRootFilesystem: true      # 根文件系统只读
      allowPrivilegeEscalation: false   # 禁止提权
      capabilities:                     # Linux 能力
        drop:                           # 丢弃
        - ALL                           # 所有能力
    volumeMounts:                       # 需要写入的目录
    - mountPath: /tmp                   # 临时目录
      name: tmp
    - mountPath: /var/cache/nginx       # Nginx 缓存
      name: cache
  volumes:                              # 卷定义
  - name: tmp                           # 临时卷
    emptyDir: {}
  - name: cache
    emptyDir: {}
""",
        common_errors=[
            "runAsNonRoot: true 但镜像默认 USER 是 root（Pod 启动会失败）",
            "readOnlyRootFilesystem: true 但没挂载 /tmp 导致程序写入失败",
            "runAsUser 设为 0（0 就是 root，等于没设）",
            "securityContext 写在了 spec 而不是 spec.containers[]（Pod 级和容器级位置不同）",
        ],
        tips=[
            "用 kubectl exec <pod> -- id 查看容器运行的用户",
            "readOnlyRootFilesystem 需要配合 volumeMounts 挂载需要写入的目录",
            "capabilities drop: [ALL] 是最安全的做法，需要时再逐个 add",
        ],
    ),
)


# ==================== Q18.4 Pod Security Standards ====================

def _check_184_pss_restricted(user_yaml: str) -> CheckResult:
    """Q18.4 创建符合 restricted PSS 的 Pod"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["你需要 apply 一个 kind: Pod 的 YAML"],
        )

    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])
    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    pod_sc = spec.get("securityContext", {})
    container_sc = c.get("securityContext", {})
    if not isinstance(pod_sc, dict):
        pod_sc = {}
    if not isinstance(container_sc, dict):
        container_sc = {}

    errors = []

    # Restricted PSS 要求:
    # 1. runAsNonRoot: true
    if container_sc.get("runAsNonRoot", pod_sc.get("runAsNonRoot")) is not True:
        errors.append("runAsNonRoot 必须为 true")

    # 2. runAsUser 非 0
    run_as_user = container_sc.get("runAsUser", pod_sc.get("runAsUser"))
    if run_as_user is None or str(run_as_user) == "0":
        errors.append("runAsUser 必须为非 0 值")

    # 3. allowPrivilegeEscalation: false
    if container_sc.get("allowPrivilegeEscalation") is not False:
        errors.append("allowPrivilegeEscalation 必须为 false")

    # 4. capabilities.drop 包含 ALL
    caps = container_sc.get("capabilities", {})
    if not isinstance(caps, dict):
        caps = {}
    drop = caps.get("drop", [])
    if not isinstance(drop, list) or "ALL" not in drop:
        errors.append("capabilities.drop 必须包含 ALL")

    # 5. seccompProfile 设置
    seccomp = pod_sc.get("seccompProfile") or container_sc.get("seccompProfile")
    if not isinstance(seccomp, dict) or seccomp.get("type") != "RuntimeDefault":
        errors.append("seccompProfile.type 必须为 RuntimeDefault")

    # 6. privileged 不能为 true
    if container_sc.get("privileged") is True:
        errors.append("privileged 不能为 true（PSS restricted 禁止特权容器）")

    # 7. hostNetwork / hostPID / hostIPC 不能为 true
    if spec.get("hostNetwork") is True:
        errors.append("hostNetwork 不能为 true（PSS restricted 禁止共享主机网络）")
    if spec.get("hostPID") is True:
        errors.append("hostPID 不能为 true（PSS restricted 禁止共享主机 PID）")
    if spec.get("hostIPC") is True:
        errors.append("hostIPC 不能为 true（PSS restricted 禁止共享主机 IPC）")

    if errors:
        return CheckResult(
            ok=False,
            error="未满足 Pod Security Standards restricted 级别:\n" + "\n".join(f"  - {e}" for e in errors),
            hints=[
                "Restricted PSS 是最严格的安全标准 💪",
                "需要: runAsNonRoot, runAsUser!=0, allowPrivilegeEscalation=false, capabilities.drop=[ALL], seccompProfile=RuntimeDefault",
            ],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["符合 Restricted PSS 标准！这是生产环境推荐的安全级别 🏆"],
    )


LEVEL_Q18_4 = Level(
    id="Q18.4",
    chapter="ch18",
    title="Pod Security Standards",
    description="""
# Pod Security Standards (PSS) 🏆

K8s 1.25+ 用 **Pod Security Standards** 替代了旧的 PodSecurityPolicy。PSS 定义了三个安全级别。

## 任务

创建一个符合 **restricted** 级别的 Pod：
- `runAsNonRoot: true`
- `runAsUser: 1000`（非 0）
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`
- `seccompProfile.type: RuntimeDefault`
- 容器使用 `nginx:1.25-alpine`

## 提示

Restricted 级别需要在 Pod 和容器 securityContext 中设置多项：
```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  # securityContext:
  #   seccompProfile:
  #     type: RuntimeDefault
  containers:
  - name: web
    image: nginx:1.25-alpine
    # securityContext:
    #   runAsNonRoot: true
    #   runAsUser: 1000
    #   allowPrivilegeEscalation: false
    #   capabilities:
    #     drop: [ALL]
    volumeMounts:
    - mountPath: /tmp
      name: tmp
  volumes:
  - name: tmp
    emptyDir: {}
""",
    check_fn=_check_184_pss_restricted,
    lesson=Lesson(
        concept="""\
## Pod Security Standards (PSS)

**PSS** 是 Kubernetes 官方的 Pod 安全标准，定义了三个递进的安全级别。

### 三个安全级别

| 级别 | 说明 | 适用场景 |
|------|------|---------|
| **privileged** | 无限制，最宽松 | 系统组件、特殊需求 |
| **baseline** | 基本安全，禁止明显危险操作 | 一般应用 |
| **restricted** | 最严格，最佳安全实践 | 生产环境推荐 |

### 各级别要求对比

```
                privileged    baseline      restricted
                ──────────    ────────      ──────────
特权容器          ✅ 允许       ❌ 禁止       ❌ 禁止
hostPath          ✅ 允许       ❌ 禁止       ❌ 禁止
hostNetwork       ✅ 允许       ❌ 禁止       ❌ 禁止
hostPID/hostIPC   ✅ 允许       ❌ 禁止       ❌ 禁止
root 用户         ✅ 允许       ✅ 允许       ❌ 禁止
allowPrivilege    ✅ 允许       ✅ 允许       ❌ 禁止
  Escalation
capabilities      ✅ 任意       保留默认       ❌ 必须drop ALL
seccompProfile    ✅ 可选       ✅ 可选       ✅ 必须 RuntimeDefault
runAsNonRoot      ✅ 可选       ✅ 可选       ✅ 必须 true
```

### 如何启用 PSS

在命名空间上设置标签：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    # enforce: 违反则拒绝创建
    pod-security.kubernetes.io/enforce: restricted
    # audit: 违反则记录审计日志
    pod-security.kubernetes.io/audit: restricted
    # warn: 违反则返回警告
    pod-security.kubernetes.io/warn: restricted
```

### Restricted 级别的完整要求

1. **runAsNonRoot: true** - 禁止 root 运行
2. **runAsUser != 0** - 非 root UID
3. **allowPrivilegeEscalation: false** - 禁止提权
4. **capabilities.drop: [ALL]** - 丢弃所有 Linux 能力
5. **seccompProfile.type: RuntimeDefault** - 使用默认 seccomp 配置
6. 禁止 hostPath/hostNetwork/hostPID/hostIPC
7. 禁止 privileged 容器
```

### 三种模式

| 模式 | 行为 |
|------|------|
| enforce | 违反 → 拒绝创建/更新 |
| audit | 违反 → 记录审计事件 |
| warn | 违反 → 返回警告信息 |
""",
        key_fields=[
            {"name": "securityContext.runAsNonRoot", "description": "禁止 root 运行", "required": True, "example": "true"},
            {"name": "securityContext.runAsUser", "description": "非 root UID", "required": True, "example": "1000"},
            {"name": "securityContext.allowPrivilegeEscalation", "description": "禁止提权", "required": True, "example": "false"},
            {"name": "securityContext.capabilities.drop", "description": "丢弃所有能力", "required": True, "example": "[ALL]"},
            {"name": "securityContext.seccompProfile.type", "description": "seccomp 配置", "required": True, "example": "RuntimeDefault"},
        ],
        diagram="""\
  ┌───────── Pod Security Standards ──────────────┐
  │                                                │
  │  ┌──────────────┐  最宽松                      │
  │  │ privileged   │  无限制，特权容器             │
  │  │              │  适用: 系统组件               │
  │  └──────┬───────┘                              │
  │         │                                      │
  │  ┌──────▼───────┐  基本安全                    │
  │  │ baseline     │  禁止特权/hostPath            │
  │  │              │  适用: 一般应用               │
  │  └──────┬───────┘                              │
  │         │                                      │
  │  ┌──────▼───────┐  最严格                      │
  │  │ restricted   │  ✅ runAsNonRoot             │
  │  │              │  ✅ runAsUser != 0           │
  │  │              │  ✅ drop ALL capabilities    │
  │  │              │  ✅ seccompProfile           │
  │  │              │  ✅ no privilege escalation  │
  │  │              │  适用: 生产环境 ⭐           │
  │  └──────────────┘                              │
  │                                                │
  │  命名空间标签启用:                              │
  │  pod-security.kubernetes.io/enforce: restricted│
  └────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                           # 核心 API
kind: Pod                               # 资源类型
metadata:                               # 元数据
  name: restricted-pod                  # Pod 名称
spec:                                   # Pod 规格
  securityContext:                      # Pod 级安全上下文
    seccompProfile:                     # seccomp 配置
      type: RuntimeDefault              # 使用运行时默认
  containers:                           # 容器列表
  - name: web                           # 容器名
    image: nginx:1.25-alpine            # 镜像
    securityContext:                    # 容器级安全上下文
      runAsNonRoot: true                # 禁止 root
      runAsUser: 1000                   # 非 root UID
      allowPrivilegeEscalation: false   # 禁止提权
      capabilities:                     # Linux 能力
        drop:                           # 丢弃
        - ALL                           # 所有能力
    volumeMounts:                       # 需要写入的目录
    - mountPath: /tmp                   # 临时目录
      name: tmp
    - mountPath: /var/cache/nginx       # Nginx 缓存
      name: cache
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
""",
        common_errors=[
            "忘记 seccompProfile.type: RuntimeDefault（restricted 强制要求）",
            "capabilities.drop 写成了 drop: ALL（应该是列表 [ALL]）",
            "allowPrivilegeEscalation 忘记设为 false（默认 true 不符合 restricted）",
            "在命名空间设置了 enforce: restricted 但 Pod 不符合标准（会被拒绝创建）",
        ],
        tips=[
            "用 kubectl label namespace <ns> pod-security.kubernetes.io/enforce=restricted 启用 PSS",
            "用 kubectl get --raw /api/v1/namespaces/<ns> 查看命名空间的 PSS 标签",
            "audit 模式可以先观察违规情况，不阻断现有工作负载",
        ],
    ),
)


# ==================== Q18.5 集群实战 - 最小权限应用部署 ====================

def _check_185_least_privilege(user_yaml: str) -> CheckResult:
    """Q18.5 集群实战 - 最小权限应用部署"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 ServiceAccount
    if not state.serviceaccounts:
        return CheckResult(
            ok=False,
            error="缺少 ServiceAccount",
            hints=["最小权限部署需要专用 ServiceAccount"],
        )

    # 检查 Pod
    if not state.pods:
        return CheckResult(
            ok=False,
            error="缺少 Pod",
            hints=["创建一个使用 ServiceAccount 且带安全上下文的 Pod"],
        )

    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    # 检查 Pod 使用了 ServiceAccount
    sa_name = spec.get("serviceAccountName", "")
    if not sa_name:
        return CheckResult(
            ok=False,
            error="Pod 未指定 serviceAccountName",
            hints=["Pod 应使用专用 ServiceAccount 而非 default"],
        )

    if sa_name not in state.serviceaccounts:
        return CheckResult(
            ok=False,
            error=f"Pod 引用的 ServiceAccount '{sa_name}' 不存在",
            hints=["确保先创建 ServiceAccount 再被 Pod 引用"],
        )

    # 检查安全上下文
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])
    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    pod_sc = spec.get("securityContext", {})
    container_sc = c.get("securityContext", {})
    if not isinstance(pod_sc, dict):
        pod_sc = {}
    if not isinstance(container_sc, dict):
        container_sc = {}

    # 检查 runAsNonRoot
    run_as_non_root = container_sc.get("runAsNonRoot", pod_sc.get("runAsNonRoot"))
    if run_as_non_root is not True:
        return CheckResult(
            ok=False,
            error="缺少 runAsNonRoot: true（最小权限要求非 root 运行）",
            hints=["在 securityContext 中设置 runAsNonRoot: true"],
        )

    # 检查 readOnlyRootFilesystem
    read_only = container_sc.get("readOnlyRootFilesystem")
    if read_only is not True:
        return CheckResult(
            ok=False,
            error="缺少 readOnlyRootFilesystem: true（最小权限要求只读根文件系统）",
            hints=["设置 readOnlyRootFilesystem: true"],
        )

    # 检查 runAsUser 非 0
    run_as_user = container_sc.get("runAsUser", pod_sc.get("runAsUser"))
    if run_as_user is None or run_as_user == 0:
        return CheckResult(
            ok=False,
            error="runAsUser 应为非 0 值（最小权限要求非 root UID）",
            hints=["设置 runAsUser: 1000"],
        )

    # 检查 capabilities.drop ALL
    caps = container_sc.get("capabilities", {})
    if not isinstance(caps, dict):
        caps = {}
    drop = caps.get("drop", [])
    if not isinstance(drop, list) or "ALL" not in drop:
        return CheckResult(
            ok=False,
            error="capabilities.drop 应包含 ALL（最小权限要求丢弃所有能力）",
            hints=["添加 capabilities: {drop: [ALL]}"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "最小权限应用部署完成！在真实集群上验证：",
            "  kubectl apply -f secure-app.yaml",
            "  kubectl get pods                # 查看 Pod 运行状态",
            "  kubectl exec <pod> -- id        # 验证非 root 用户",
            "  kubectl auth can-i --list --as=system:serviceaccount:default:<sa-name>",
        ],
    )


LEVEL_Q18_5 = Level(
    id="Q18.5",
    chapter="ch18",
    title="集群实战: 最小权限应用部署",
    description="""
# 集群实战: 最小权限应用部署 🏗️

将所学安全知识整合，部署一个遵循**最小权限原则**的应用。

## 任务

使用多文档 YAML 创建：
1. **ServiceAccount** - 专用身份（非 default）
2. **Pod** - 使用上述 SA，且满足：
   - `serviceAccountName` 引用创建的 SA
   - `runAsNonRoot: true`
   - `runAsUser: 1000`（非 0）
   - `readOnlyRootFilesystem: true`
   - `capabilities.drop: [ALL]`

## 验证步骤

```bash
# 部署
kubectl apply -f secure-app.yaml

# 验证 SA
kubectl get sa
kubectl describe sa <sa-name>

# 验证 Pod 安全上下文
kubectl get pod <pod-name> -o jsonpath='{.spec.securityContext}'
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].securityContext}'

# 验证非 root 运行
kubectl exec <pod-name> -- id
# 应输出: uid=1000 gid=0 ...

# 验证只读文件系统
kubectl exec <pod-name> -- touch /test
# 应报错: Read-only file system

# 查看 SA 权限
kubectl auth can-i --list \
  --as=system:serviceaccount:default:<sa-name>
```
""",
    starter_yaml="""\
# --- ServiceAccount ---
apiVersion: v1
kind: ServiceAccount
metadata:
  # name: secure-app-sa
  pass: true
# ---
# apiVersion: v1
# kind: Pod
# metadata:
#   name: secure-app
# spec:
#   serviceAccountName: secure-app-sa
#   securityContext:
#     runAsNonRoot: true
#     runAsUser: 1000
#   containers:
#   - name: web
#     image: nginx:1.25-alpine
#     securityContext:
#       readOnlyRootFilesystem: true
#       capabilities:
#         drop: [ALL]
#     volumeMounts:
#     - mountPath: /tmp
#       name: tmp
#   volumes:
#   - name: tmp
#     emptyDir: {}
""",
    check_fn=_check_185_least_privilege,
    lesson=Lesson(
        concept="""\
## 最小权限原则

**最小权限原则（Principle of Least Privilege）** 是安全的核心：只赋予完成任务所需的最少权限。

### 在 K8s 中的最小权限实践

```
┌─────────── 最小权限部署清单 ───────────────────┐
│                                                 │
│  1. 专用 ServiceAccount                         │
│     ✅ 不使用 default SA                        │
│     ✅ 每个应用一个 SA                          │
│                                                 │
│  2. RBAC 最小权限                               │
│     ✅ 只授予需要的操作权限                     │
│     ✅ 使用 Role 而非 ClusterRole（如可能）     │
│                                                 │
│  3. 非 root 运行                                │
│     ✅ runAsNonRoot: true                      │
│     ✅ runAsUser: 1000 (非 0)                  │
│                                                 │
│  4. 只读文件系统                                │
│     ✅ readOnlyRootFilesystem: true            │
│     ✅ 需要写入的目录用 emptyDir 挂载           │
│                                                 │
│  5. 丢弃能力                                    │
│     ✅ capabilities.drop: [ALL]                │
│                                                 │
│  6. 禁止提权                                    │
│     ✅ allowPrivilegeEscalation: false         │
│                                                 │
│  7. Seccomp                                     │
│     ✅ seccompProfile: RuntimeDefault           │
│                                                 │
│  8. NetworkPolicy                               │
│     ✅ 限制 Pod 间网络访问                      │
│                                                 │
│  9. Resource Limits                             │
│     ✅ 设置 CPU/Memory limits                   │
│                                                 │
│  10. 不自动挂载 token（如不需要）                │
│      ✅ automountServiceAccountToken: false    │
└─────────────────────────────────────────────────┘
```

### 安全层次模型

```
应用安全
├── 身份层 (Who)
│   └── ServiceAccount → RBAC 权限控制
├── 进程层 (How)
│   ├── runAsNonRoot → 非 root 运行
│   ├── capabilities → 限制内核能力
│   └── seccomp → 限制系统调用
├── 文件层 (What)
│   ├── readOnlyRootFilesystem → 只读根 fs
│   └── fsGroup → 文件权限控制
├── 网络层 (Where)
│   ├── NetworkPolicy → 流量控制
│   └── Service Mesh → mTLS 加密
└── 资源层 (How much)
    └── ResourceQuota/LimitRange → 资源限制
```

### 完整的安全加固 Pod

生产环境推荐的 Pod 安全配置：

```yaml
spec:
  serviceAccountName: app-sa        # 专用 SA
  automountServiceAccountToken: false  # 不需要 API 访问则禁用
  securityContext:
    runAsNonRoot: true              # 非 root
    runAsUser: 1000                 # 指定 UID
    runAsGroup: 3000                # 指定 GID
    fsGroup: 2000                   # 文件组
    seccompProfile:
      type: RuntimeDefault          # seccomp
  containers:
  - name: app
    image: app:v1
    securityContext:
      readOnlyRootFilesystem: true  # 只读 fs
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]                # 丢弃能力
    resources:
      limits:
        cpu: 500m
        memory: 512Mi
      requests:
        cpu: 100m
        memory: 128Mi
```
""",
        key_fields=[
            {"name": "ServiceAccount", "description": "专用身份标识", "required": True, "example": "secure-app-sa"},
            {"name": "spec.serviceAccountName", "description": "Pod 绑定 SA", "required": True, "example": "secure-app-sa"},
            {"name": "securityContext.runAsNonRoot", "description": "非 root 运行", "required": True, "example": "true"},
            {"name": "securityContext.runAsUser", "description": "非 root UID", "required": True, "example": "1000"},
            {"name": "securityContext.readOnlyRootFilesystem", "description": "只读根文件系统", "required": True, "example": "true"},
            {"name": "securityContext.capabilities.drop", "description": "丢弃所有能力", "required": True, "example": "[ALL]"},
        ],
        diagram="""\
  ┌─────────── 最小权限部署架构 ────────────────────────┐
  │                                                     │
  │  ┌─────────────────────────────────────────────┐    │
  │  │            多文档 YAML 部署                   │    │
  │  │  ---                                         │    │
  │  │  ServiceAccount: secure-app-sa               │    │
  │  │  ---                                         │    │
  │  │  Pod: secure-app                             │    │
  │  └──────────────────┬──────────────────────────┘    │
  │                     │                               │
  │     ┌───────────────┼───────────────┐               │
  │     ▼               ▼               ▼               │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐      │
  │  │   SA     │  │   Pod    │  │ Security     │      │
  │  │          │  │          │  │ Context      │      │
  │  │ 专用身份  │  │ 引用 SA  │  │              │      │
  │  │ 非default│  │          │  │ runAsNonRoot │      │
  │  └──────────┘  └──────────┘  │ runAsUser    │      │
  │                              │ readOnly FS  │      │
  │                              │ drop ALL cap │      │
  │                              └──────────────┘      │
  │                                                     │
  │  安全效果:                                          │
  │  ✅ 身份隔离 (专用 SA)                              │
  │  ✅ 非 root 运行                                    │
  │  ✅ 文件系统只读                                    │
  │  ✅ 无 Linux 能力                                   │
  │  ✅ 无法提权                                        │
  │  ✅ 攻击面最小化                                    │
  └─────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- ServiceAccount ---
apiVersion: v1                           # 核心 API
kind: ServiceAccount                     # 资源类型
metadata:                                # 元数据
  name: secure-app-sa                    # SA 名称
---
# --- Pod ---
apiVersion: v1                           # 核心 API
kind: Pod                               # 资源类型
metadata:                               # 元数据
  name: secure-app                      # Pod 名称
spec:                                   # Pod 规格
  serviceAccountName: secure-app-sa     # 绑定专用 SA
  securityContext:                      # Pod 级安全上下文
    runAsNonRoot: true                  # 禁止 root
    runAsUser: 1000                     # 非 root UID
    runAsGroup: 3000                    # 非 root GID
    fsGroup: 2000                       # 文件系统组
  containers:                           # 容器列表
  - name: web                           # 容器名
    image: nginx:1.25-alpine            # 镜像
    securityContext:                    # 容器级安全上下文
      readOnlyRootFilesystem: true      # 只读根文件系统
      allowPrivilegeEscalation: false   # 禁止提权
      capabilities:                     # Linux 能力
        drop:                           # 丢弃
        - ALL                           # 所有能力
    volumeMounts:                       # 需要写入的目录
    - mountPath: /tmp                   # 临时目录
      name: tmp
    - mountPath: /var/cache/nginx       # 缓存目录
      name: cache
  volumes:                              # 卷定义
  - name: tmp                           # 临时卷
    emptyDir: {}
  - name: cache
    emptyDir: {}
""",
        common_errors=[
            "使用了 default SA 而非专用 SA（无法实现身份隔离）",
            "安全上下文只设了 Pod 级，忘了容器级的 readOnlyRootFilesystem",
            "多文档 YAML 忘记用 --- 分隔 ServiceAccount 和 Pod",
            "Pod 引用的 SA 名称与创建的 SA 名称不匹配",
        ],
        tips=[
            "用 kubectl exec <pod> -- id 验证容器运行用户是否为非 root",
            "用 kubectl exec <pod> -- touch /test 验证根文件系统是否只读",
            "生产环境应配合 NetworkPolicy + ResourceQuota 实现全面安全",
            "automountServiceAccountToken: false 可以在不需 API 访问时进一步减少攻击面",
        ],
    ),
)


# ==================== 章节关卡列表 ====================

CHAPTER_18_LEVELS: list[Level] = [
    LEVEL_Q18_1, LEVEL_Q18_2, LEVEL_Q18_3, LEVEL_Q18_4, LEVEL_Q18_5,
]
