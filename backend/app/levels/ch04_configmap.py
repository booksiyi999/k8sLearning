"""Chapter 4: ConfigMap & Secret（4 关）

Q4.1 创建 ConfigMap
Q4.2 在 Pod 中使用 ConfigMap（环境变量）
Q4.3 在 Pod 中使用 ConfigMap（Volume 挂载）
Q4.4 创建 Secret 并在 Pod 中使用
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import (
    apply_manifest,
    preset_state,
    ClusterState,
    K8sError,
)


# ==================== Q4.1 创建 ConfigMap ====================

def _check_01_create_configmap(user_yaml: str) -> CheckResult:
    """Q4.1 创建 ConfigMap"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 ConfigMap 是否创建
    if not hasattr(state, 'configmaps') or not state.configmaps:
        return CheckResult(ok=False, error="没有创建任何 ConfigMap", hints=["你需要 apply 一个 kind: ConfigMap 的 YAML"])

    if "app-config" not in state.configmaps:
        names = list(state.configmaps.keys())
        return CheckResult(
            ok=False,
            error=f"没找到名为 'app-config' 的 ConfigMap，当前：{names}",
            hints=["ConfigMap 名字由 metadata.name 决定"],
        )

    cm = state.configmaps["app-config"]
    data = cm.get("data")
    if not isinstance(data, dict) or not data:
        return CheckResult(ok=False, error="ConfigMap 缺少 data 字段", hints=["data 是键值对形式存储配置的地方"])

    if "APP_MODE" not in data:
        return CheckResult(ok=False, error="ConfigMap 的 data 中缺少 'APP_MODE' 键", hints=["需要包含 APP_MODE: production"])

    if data["APP_MODE"] != "production":
        return CheckResult(ok=False, error=f"APP_MODE 应为 'production'，实际为 '{data['APP_MODE']}'", hints=[])

    if "LOG_LEVEL" not in data:
        return CheckResult(ok=False, error="ConfigMap 的 data 中缺少 'LOG_LEVEL' 键", hints=["需要包含 LOG_LEVEL: info"])

    return CheckResult(ok=True, state=state, hints=["ConfigMap 创建成功！ConfigMap 用于存储非敏感的配置数据"])


# ==================== Q4.2 ConfigMap 环境变量 ====================

def _check_02_configmap_env(user_yaml: str) -> CheckResult:
    """Q4.2 在 Pod 中使用 ConfigMap（环境变量）"""
    try:
        state = ClusterState()
        # 预置 ConfigMap
        state = preset_state(state, """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建任何 Pod", hints=["创建一个 Pod，通过 envFrom 或 env引用 ConfigMap"])

    # 找到用户创建的 Pod
    pod = None
    for name, p in state.pods.items():
        pod = p
        break

    if not pod:
        return CheckResult(ok=False, error="未找到 Pod", hints=[])

    spec = pod.get("spec", {})
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查是否通过 envFrom 或 env.configMapKeyRef 引用 ConfigMap
    env = c.get("env", [])
    env_from = c.get("envFrom", [])

    found_env_ref = False

    # 方式1: env[].configMapKeyRef
    if isinstance(env, list):
        for e in env:
            if isinstance(e, dict):
                ref = e.get("valueFrom", {})
                if isinstance(ref, dict):
                    cm_ref = ref.get("configMapKeyRef", {})
                    if isinstance(cm_ref, dict) and cm_ref.get("name") == "app-config":
                        found_env_ref = True
                        break

    # 方式2: envFrom[].configMapRef
    if not found_env_ref and isinstance(env_from, list):
        for ef in env_from:
            if isinstance(ef, dict):
                cm_ref = ef.get("configMapRef", {})
                if isinstance(cm_ref, dict) and cm_ref.get("name") == "app-config":
                    found_env_ref = True
                    break

    if not found_env_ref:
        return CheckResult(
            ok=False,
            error="Pod 的容器没有引用 ConfigMap 'app-config'",
            hints=["方式1: env[].valueFrom.configMapKeyRef 引用单个 key", "方式2: envFrom[].configMapRef 引用整个 ConfigMap"],
        )

    return CheckResult(ok=True, state=state, hints=["ConfigMap 环境变量注入成功！"])


# ==================== Q4.3 ConfigMap Volume 挂载 ====================

def _check_03_configmap_volume(user_yaml: str) -> CheckResult:
    """Q4.3 在 Pod 中使用 ConfigMap（Volume 挂载）"""
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建任何 Pod", hints=["创建一个 Pod，通过 volumes 挂载 ConfigMap"])

    pod = None
    for name, p in state.pods.items():
        pod = p
        break

    if not pod:
        return CheckResult(ok=False, error="未找到 Pod", hints=[])

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    # 检查 volumes 中是否有 ConfigMap
    volumes = spec.get("volumes", [])
    found_cm_volume = False
    if isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict):
                cm_source = v.get("configMap", {})
                if isinstance(cm_source, dict) and cm_source.get("name") == "app-config":
                    found_cm_volume = True
                    break

    if not found_cm_volume:
        return CheckResult(
            ok=False,
            error="Pod 的 volumes 中没有引用 ConfigMap 'app-config'",
            hints=["在 spec.volumes 中添加 configMap: { name: app-config }"],
        )

    # 检查 containers 中是否有 volumeMounts
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    volume_mounts = c.get("volumeMounts", [])
    if not isinstance(volume_mounts, list) or not volume_mounts:
        return CheckResult(ok=False, error="容器缺少 volumeMounts", hints=["在 containers[].volumeMounts 中挂载 ConfigMap Volume"])

    found_mount = False
    for vm in volume_mounts:
        if isinstance(vm, dict) and vm.get("name"):
            found_mount = True
            break

    if not found_mount:
        return CheckResult(ok=False, error="volumeMounts 中没有有效的挂载项", hints=[])

    return CheckResult(ok=True, state=state, hints=["ConfigMap Volume 挂载成功！每个 key 变成一个文件"])


# ==================== Q4.4 创建 Secret 并使用 ====================

def _check_04_secret(user_yaml: str) -> CheckResult:
    """Q4.4 创建 Secret 并在 Pod 中使用"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 Secret 是否创建
    if not hasattr(state, 'secrets') or not state.secrets:
        return CheckResult(ok=False, error="没有创建任何 Secret", hints=["你需要 apply 一个 kind: Secret 的 YAML"])

    if "db-secret" not in state.secrets:
        names = list(state.secrets.keys())
        return CheckResult(
            ok=False,
            error=f"没找到名为 'db-secret' 的 Secret，当前：{names}",
            hints=["Secret 名字必须是 db-secret"],
        )

    secret = state.secrets["db-secret"]

    # 检查 type
    sec_type = secret.get("type", "Opaque")
    if sec_type != "Opaque":
        return CheckResult(ok=False, error=f"type 应为 Opaque（默认），实际为 {sec_type}", hints=[])

    # 检查 data
    data = secret.get("data")
    if not isinstance(data, dict) or not data:
        return CheckResult(ok=False, error="Secret 缺少 data 字段", hints=["Secret 的 data 是 base64 编码的键值对"])

    if "password" not in data:
        return CheckResult(ok=False, error="Secret 的 data 中缺少 'password' 键", hints=["需要包含 password 字段（base64编码）"])

    # 检查是否有 Pod 引用了这个 Secret
    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod 来使用 Secret", hints=["创建一个 Pod，通过 env 或 volume 引用 db-secret"])

    pod = None
    for name, p in state.pods.items():
        pod = p
        break

    if not pod:
        return CheckResult(ok=False, error="未找到 Pod", hints=[])

    spec = pod.get("spec", {})
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查是否引用了 Secret
    env = c.get("env", [])
    env_from = c.get("envFrom", [])
    volumes = spec.get("volumes", [])
    found_secret_ref = False

    # env[].valueFrom.secretKeyRef
    if isinstance(env, list):
        for e in env:
            if isinstance(e, dict):
                ref = e.get("valueFrom", {})
                if isinstance(ref, dict):
                    sec_ref = ref.get("secretKeyRef", {})
                    if isinstance(sec_ref, dict) and sec_ref.get("name") == "db-secret":
                        found_secret_ref = True
                        break

    # envFrom[].secretRef
    if not found_secret_ref and isinstance(env_from, list):
        for ef in env_from:
            if isinstance(ef, dict):
                sec_ref = ef.get("secretRef", {})
                if isinstance(sec_ref, dict) and sec_ref.get("name") == "db-secret":
                    found_secret_ref = True
                    break

    # volumes[].secret
    if not found_secret_ref and isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict):
                sec_source = v.get("secret", {})
                if isinstance(sec_source, dict) and sec_source.get("secretName") == "db-secret":
                    found_secret_ref = True
                    break

    if not found_secret_ref:
        return CheckResult(
            ok=False,
            error="Pod 没有引用 Secret 'db-secret'",
            hints=["通过 env.valueFrom.secretKeyRef 或 envFrom.secretRef 或 volumes.secret 引用"],
        )

    return CheckResult(ok=True, state=state, hints=["Secret 创建并使用成功！Secret 用于存储敏感数据（密码/密钥/证书）"])


# ==================== 关卡注册 ====================

CHAPTER_4_LEVELS: list[Level] = [
    Level(
        id="Q4.1",
        chapter="ch04",
        title="创建 ConfigMap",
        description="创建一个名为 app-config 的 ConfigMap，包含 APP_MODE=production 和 LOG_LEVEL=info 两个键值对",
        starter_yaml="""apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  # 添加 APP_MODE 和 LOG_LEVEL
""",
        check_fn=_check_01_create_configmap,
        lesson=Lesson(
            concept="""\
## ConfigMap

**ConfigMap** 是 K8s 中用于存储非敏感配置数据的资源。它将配置与镜像解耦，让同一镜像在不同环境（dev/staging/prod）中使用不同配置。

### 为什么需要 ConfigMap？

传统做法是把配置打包进镜像（如 application.properties），但这样每次改配置都要重新构建镜像。ConfigMap 将配置独立出来：
- 修改配置不需要重建镜像
- 不同环境共用同一镜像，只换 ConfigMap
- 配置集中管理，便于审计

### data 字段

ConfigMap 的核心是 `data` 字段，以键值对形式存储配置：
- **键**：配置项名称（如 APP_MODE）
- **值**：字符串形式的配置值

每个 key-value 对可以映射为：
- 环境变量（env / envFrom）
- 配置文件（Volume 挂载）
- 命令行参数

### ConfigMap vs Secret

| 特性 | ConfigMap | Secret |
|------|-----------|--------|
| 用途 | 非敏感配置 | 敏感数据（密码/密钥） |
| 编码 | 明文 | Base64 |
| 大小限制 | 1MB | 1MB |
| 类型 | 无 | Opaque/tls/etc. |

### 注意事项

- ConfigMap 不加密，**不要存密码**--用 Secret
- 总大小限制 1MB，大配置考虑挂载文件或其他方案
- ConfigMap 更新后，环境变量不会自动刷新（Volume 挂载会延迟刷新）
""",
            key_fields=[
                {"name": "apiVersion", "description": "K8s API 版本，ConfigMap 用 v1", "required": True, "example": "v1"},
                {"name": "kind", "description": "资源类型，ConfigMap", "required": True, "example": "ConfigMap"},
                {"name": "metadata.name", "description": "ConfigMap 名称", "required": True, "example": "app-config"},
                {"name": "data", "description": "键值对配置数据，值为字符串", "required": True, "example": "{APP_MODE: production, LOG_LEVEL: info}"},
            ],
            diagram="""\
┌──────── ConfigMap (app-config) ───────────┐
│                                            │
│  data:                                     │
│    APP_MODE: production  ─────► 环境变量    │
│    LOG_LEVEL: info       ─────► 环境变量    │
│    config.yaml: |        ─────► 配置文件    │
│      server:                               │
│        port: 8080                          │
│                                            │
└────────────────────────────────────────────┘
        │ 被以下方式引用
        ├──► Pod env / envFrom (环境变量注入)
        ├──► Pod volumes (配置文件挂载)
        └──► Pod command args (命令行参数)
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: ConfigMap                 # 资源类型: ConfigMap
metadata:                       # 元数据
  name: app-config              # ConfigMap 名称
data:                           # 配置数据（键值对）
  APP_MODE: production          # 应用运行模式
  LOG_LEVEL: info               # 日志级别
  # 也可以存储多行配置文件:
  # config.yaml: |
  #   server:
  #     port: 8080
""",
            common_errors=[
                "data 值未用引号包裹特殊字符（如值含冒号需要引号）",
                "把敏感数据（密码）放在 ConfigMap 里（应该用 Secret）",
                "忘记写 data 字段（ConfigMap 必须有 data）",
                "data 值写成整数（YAML 会解析为 int，但 ConfigMap 要求字符串）",
            ],
            tips=[
                "ConfigMap 实现配置与镜像解耦，是云原生最佳实践",
                "用 kubectl get cm 查看 ConfigMap，kubectl describe cm 查看内容",
                "ConfigMap 更新后 env 不会刷新，Volume 挂载会延迟更新（约 1 分钟）",
            ],
        ),
    ),
    Level(
        id="Q4.2",
        chapter="ch04",
        title="ConfigMap 环境变量注入",
        description="集群中已有 app-config ConfigMap。创建一个 Pod，通过环境变量引用 ConfigMap 中的值",
        starter_yaml="""apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      # 通过 env 或 envFrom 引用 app-config
""",
        check_fn=_check_02_configmap_env,
        lesson=Lesson(
            concept="""\
## ConfigMap 环境变量注入

ConfigMap 可以通过两种方式注入为 Pod 的环境变量：**env（逐个引用）** 和 **envFrom（批量引用）**。

### 方式一：env + configMapKeyRef

逐个引用 ConfigMap 的 key 作为环境变量：

```yaml
env:
- name: APP_MODE                          # 环境变量名
  valueFrom:
    configMapKeyRef:
      name: app-config                    # ConfigMap 名称
      key: APP_MODE                       # data 中的 key
```

优点：可以重命名环境变量，只引用需要的 key。缺点：每个变量都要单独声明。

### 方式二：envFrom + configMapRef

批量引用整个 ConfigMap，所有 key-value 自动变成环境变量：

```yaml
envFrom:
- configMapRef:
    name: app-config                      # 所有 key 自动注入
```

优点：一行代码注入所有配置。缺点：变量名必须与 ConfigMap 的 key 完全一致。

### 选择建议

- 配置项少（<5 个）→ 用 env 精确控制
- 配置项多且变量名一致 → 用 envFrom 批量注入
- 需要重命名或只引用部分 → 用 env

### optional 字段

设置 `optional: true` 后，ConfigMap 不存在时 Pod 也能启动（变量为空）。默认 false，ConfigMap 不存在则 Pod 启动失败。
""",
            key_fields=[
                {"name": "spec.containers[].env[].valueFrom.configMapKeyRef", "description": "引用 ConfigMap 的单个 key 作为环境变量", "required": False, "example": "{name: app-config, key: APP_MODE}"},
                {"name": "spec.containers[].envFrom[].configMapRef", "description": "批量引用整个 ConfigMap 的所有 key", "required": False, "example": "{name: app-config}"},
                {"name": "configMapKeyRef.optional", "description": "ConfigMap 不存在时是否允许 Pod 启动", "required": False, "example": "true"},
            ],
            diagram="""\
  ConfigMap 注入环境变量的两种方式

  ┌──── ConfigMap (app-config) ────┐
  │  data:                         │
  │    APP_MODE: production        │
  │    LOG_LEVEL: info             │
  └──────┬─────────────┬───────────┘
         │             │
    方式1: env        方式2: envFrom
         │             │
         ▼             ▼
  ┌─── Pod Container ───────────┐  ┌─── Pod Container ───────────┐
  │  env:                       │  │  envFrom:                   │
  │  - name: APP_MODE           │  │  - configMapRef:            │
  │    valueFrom:               │  │      name: app-config       │
  │      configMapKeyRef:       │  │                             │
  │        name: app-config     │  │  # APP_MODE=production      │
  │        key: APP_MODE        │  │  # LOG_LEVEL=info           │
  │  # APP_MODE=production      │  │  # (全部自动注入)            │
  └─────────────────────────────┘  └─────────────────────────────┘
  精确引用，可重命名                   批量注入，变量名=key名
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: app-pod                 # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx:latest         # 镜像
    envFrom:                    # 批量注入 ConfigMap
    - configMapRef:
        name: app-config        # 引用 app-config 的所有 key
    # 或者逐个引用:
    # env:
    # - name: APP_MODE
    #   valueFrom:
    #     configMapKeyRef:
    #       name: app-config
    #       key: APP_MODE
""",
            common_errors=[
                "configMapKeyRef 的 name 写错（必须与 ConfigMap 的 metadata.name 一致）",
                "key 写错（必须与 ConfigMap data 中的 key 完全一致）",
                "把 configMapRef 写成了 configMapKeyRef（envFrom 用 configMapRef，env 用 configMapKeyRef）",
                "ConfigMap 不存在导致 Pod 一直处于 CreateContainerConfigError",
            ],
            tips=[
                "envFrom 适合配置项多的场景，env 适合精确控制",
                "用 kubectl exec <pod> -- env 查看注入的环境变量",
                "ConfigMap 更新后已运行的 Pod 不会自动刷新环境变量",
            ],
        ),
    ),
    Level(
        id="Q4.3",
        chapter="ch04",
        title="ConfigMap Volume 挂载",
        description="集群中已有 app-config ConfigMap。创建一个 Pod，通过 Volume 挂载 ConfigMap 到容器中",
        starter_yaml="""apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      # 添加 volumeMounts
  # 添加 volumes，引用 app-config
""",
        check_fn=_check_03_configmap_volume,
        lesson=Lesson(
            concept="""\
## ConfigMap Volume 挂载

将 ConfigMap 作为 **Volume** 挂载到 Pod 中，每个 data key 变成一个文件，文件内容就是 key 的 value。这适合注入**配置文件**（如 nginx.conf、application.yaml）。

### 工作原理

```
ConfigMap data:
  nginx.conf: "server { listen 80; }"   →  /etc/nginx/nginx.conf
  app.yaml: "port: 8080"                →  /etc/config/app.yaml
```

K8s 自动将每个 key 转为文件名，value 转为文件内容，挂载到指定目录。

### vs 环境变量注入

| 特性 | 环境变量 | Volume 挂载 |
|------|----------|-------------|
| 格式 | 键值对 | 文件 |
| 更新 | 不刷新 | 延迟刷新（约1分钟） |
| 适合 | 简单配置 | 配置文件 |
| 大小 | 受环境变量限制 | 可存大配置 |

### items 精确控制

默认挂载所有 key。用 `items` 可以只挂载部分 key，并自定义文件路径和权限：

```yaml
volumes:
- name: config-vol
  configMap:
    name: app-config
    items:
    - key: nginx.conf
      path: nginx.conf
      mode: 0644
```

### subPath 避免覆盖目录

Volume 挂载会覆盖目标目录的已有内容。用 `subPath` 可以只挂载单个文件，不覆盖目录：
```yaml
volumeMounts:
- name: config-vol
  mountPath: /etc/nginx/nginx.conf
  subPath: nginx.conf
```
""",
            key_fields=[
                {"name": "spec.volumes[].configMap.name", "description": "引用的 ConfigMap 名称", "required": True, "example": "app-config"},
                {"name": "spec.volumes[].configMap.items", "description": "精确控制挂载哪些 key 及文件路径", "required": False, "example": "[{key: nginx.conf, path: nginx.conf}]"},
                {"name": "spec.containers[].volumeMounts[].name", "description": "引用 volume 名称，必须与 volumes 中一致", "required": True, "example": "config-vol"},
                {"name": "spec.containers[].volumeMounts[].mountPath", "description": "容器内挂载路径", "required": True, "example": "/etc/config"},
            ],
            diagram="""\
  ConfigMap Volume 挂载流程

  ┌──── ConfigMap (app-config) ────┐
  │  data:                         │
  │    APP_MODE: production        │
  │    LOG_LEVEL: info             │
  └──────────┬─────────────────────┘
             │ 引用
             ▼
  ┌──── Pod spec ──────────────────────────────────┐
  │  volumes:                                      │
  │  - name: config-vol                            │
  │    configMap:                                  │
  │      name: app-config                          │
  │                                                │
  │  containers:                                   │
  │  - name: app                                   │
  │    volumeMounts:                               │
  │    - name: config-vol          ◄── 必须与 volume name 一致
  │      mountPath: /etc/config                    │
  └────────────────────────────────────────────────┘
             │
             ▼ 挂载后容器内文件系统:
  /etc/config/
    ├── APP_MODE      (内容: production)
    └── LOG_LEVEL     (内容: info)
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: config-pod              # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx:latest         # 镜像
    volumeMounts:               # 卷挂载
    - name: config-vol          # 挂载的 volume 名
      mountPath: /etc/config    # 容器内挂载路径
  volumes:                      # 卷定义
  - name: config-vol            # volume 名（与 mount 一致）
    configMap:                  # 引用 ConfigMap
      name: app-config          # ConfigMap 名称
""",
            common_errors=[
                "volumeMounts 的 name 与 volumes 的 name 不一致（必须完全相同）",
                "忘记写 volumeMounts（只定义了 volume 但没挂载到容器）",
                "mountPath 覆盖了容器原有目录（用 subPath 避免覆盖）",
                "configMap.name 写错（必须与 ConfigMap 的 metadata.name 一致）",
            ],
            tips=[
                "Volume 挂载适合配置文件场景，环境变量适合简单键值对",
                "ConfigMap 更新后 Volume 会延迟刷新（约1分钟），环境变量不刷新",
                "用 kubectl exec <pod> -- ls /etc/config 查看挂载的文件",
            ],
        ),
    ),
    Level(
        id="Q4.4",
        chapter="ch04",
        title="创建 Secret 并使用",
        description="创建一个 Opaque 类型的 Secret db-secret，包含 password 字段（base64编码），然后创建一个 Pod 引用这个 Secret",
        starter_yaml="""apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  # password 的 base64 编码值
---
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
    - name: client
      image: postgres:15
      # 引用 db-secret
""",
        check_fn=_check_04_secret,
        lesson=Lesson(
            concept="""\
## Secret

**Secret** 用于存储敏感数据（密码、密钥、证书、Token）。与 ConfigMap 类似，但 data 中的值使用 **Base64 编码**，且在 etcd 中可以加密存储。

### Secret vs ConfigMap

| 特性 | ConfigMap | Secret |
|------|-----------|--------|
| 敏感度 | 非敏感 | 敏感 |
| 编码 | 明文 | Base64 |
| etcd 存储 | 明文 | 可配置加密 |
| 使用方式 | env/volume | env/volume（相同） |
| 类型 | 无 | Opaque/tls/dockerconfigjson等 |

### Base64 编码

Secret 的 data 值必须 Base64 编码：
```bash
echo -n 'mypassword' | base64    # → bXlwYXNzd29yZA==
```

也可以用 `stringData` 字段写明文，K8s 自动编码：
```yaml
stringData:
  password: mypassword           # 明文，K8s 自动转 Base64
```

### Secret 类型

- **Opaque**：通用类型（默认），存储任意键值对
- **kubernetes.io/tls**：TLS 证书
- **kubernetes.io/dockerconfigjson**：镜像仓库认证
- **kubernetes.io/service-account-token**：SA Token

### 使用方式

与 ConfigMap 完全相同：
- `env[].valueFrom.secretKeyRef`：引用单个 key
- `envFrom[].secretRef`：批量引用
- `volumes[].secret.secretName`：作为 Volume 挂载

### 安全注意

- Base64 不是加密，只是编码--任何人都能解码
- 生产环境应启用 etcd 加密存储 Secret
- 用 RBAC 限制 Secret 访问权限
- 避免在日志中输出 Secret 值
""",
            key_fields=[
                {"name": "type", "description": "Secret 类型，Opaque 是通用类型", "required": False, "example": "Opaque"},
                {"name": "data", "description": "Base64 编码的键值对", "required": True, "example": "{password: bXlwYXNzd29yZA==}"},
                {"name": "stringData", "description": "明文键值对，K8s 自动编码为 Base64", "required": False, "example": "{password: mypassword}"},
                {"name": "spec.containers[].env[].valueFrom.secretKeyRef", "description": "引用 Secret 的单个 key 作为环境变量", "required": False, "example": "{name: db-secret, key: password}"},
            ],
            diagram="""\
  Secret 创建与使用流程

  ┌──── Secret (db-secret) ──────────┐
  │  type: Opaque                    │
  │  data:                           │
  │    password: bXlwYXNzd29yZA==    │  ← Base64('mypassword')
  │    username: YWRtaW4=            │  ← Base64('admin')
  └──────┬──────────┬────────────────┘
         │          │
    方式1: env   方式2: volume
         │          │
         ▼          ▼
  ┌── Pod Container ────────┐  ┌── Pod Container ────────┐
  │  env:                   │  │  volumes:               │
  │  - name: DB_PASSWORD    │  │  - name: secret-vol     │
  │    valueFrom:           │  │    secret:              │
  │      secretKeyRef:      │  │      secretName:        │
  │        name: db-secret  │  │        db-secret        │
  │        key: password    │  │  # /etc/secret/password │
  │  # DB_PASSWORD=         │  │  #   内容: mypassword   │
  │  #   mypassword (解码)  │  └─────────────────────────┘
  └─────────────────────────┘
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Secret                    # 资源类型: Secret
metadata:                       # 元数据
  name: db-secret               # Secret 名称
type: Opaque                    # 通用类型（默认）
data:                           # Base64 编码数据
  password: bXlwYXNzd29yZA==    # echo -n 'mypassword' | base64
---                             # 多文档分隔符
apiVersion: v1                  # Pod 定义
kind: Pod
metadata:
  name: db-client               # Pod 名称
spec:
  containers:
  - name: client                # 容器名
    image: postgres:15          # 镜像
    env:                        # 环境变量
    - name: DB_PASSWORD         # 变量名
      valueFrom:
        secretKeyRef:           # 引用 Secret
          name: db-secret       # Secret 名称
          key: password         # data 中的 key
""",
            common_errors=[
                "data 值未 Base64 编码（必须编码，否则 K8s 拒绝）",
                "Base64 编码时用了 echo 而非 echo -n（会多一个换行符）",
                "把 Secret 和 ConfigMap 混用（密码必须用 Secret）",
                "secretKeyRef 的 name/key 与 Secret 不匹配",
            ],
            tips=[
                "Base64 不是加密--生产环境应启用 etcd 加密存储",
                "用 kubectl create secret generic <name> --from-literal=key=value 快速创建",
                "stringData 字段可以写明文，K8s 自动编码，方便调试",
                "Secret 挂载为 Volume 时自动解码为明文文件",
            ],
        ),
    ),
]
