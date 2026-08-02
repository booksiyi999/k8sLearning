"""Chapter 4: ConfigMap & Secret（4 关）

Q4.1 创建 ConfigMap
Q4.2 在 Pod 中使用 ConfigMap（环境变量）
Q4.3 在 Pod 中使用 ConfigMap（Volume 挂载）
Q4.4 创建 Secret 并在 Pod 中使用
"""
from app.validator import Level, CheckResult
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
    ),
]
