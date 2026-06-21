"""Chapter 1: Pod 基础（4 关）"""
from app.validator import Level, CheckResult
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
)


# ==================== Chapter 1 关卡汇总 ====================

CHAPTER_1_LEVELS = [LEVEL_Q1_1, LEVEL_Q1_2, LEVEL_Q1_3]
