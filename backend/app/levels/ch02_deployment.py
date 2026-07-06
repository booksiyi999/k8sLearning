"""Chapter 2: Deployment（4 关）

Q2.1 创建第一个 Deployment
Q2.2 扩缩容（改 replicas）
Q2.3 滚动更新（改 image）
Q2.4 回滚（annotation 触发）

类型安全说明:
所有 check_fn 对用户 YAML 解析后的嵌套结构都用 isinstance 守卫,
防止 truthy 非 dict/list（如字符串/数字）绕过 falsy-only guard 后
在 .get / [0] 处抛 AttributeError/TypeError → /api/check HTTP 500。
参考 ch01_pod.py _check_04_resource_limits 的守卫风格。

simulator 依赖（T2 已实现, 见 backend/app/simulator.py）:
- apply_manifest(state, yaml)         解析+校验+应用
- preset_state(state, yaml)            预置基线状态（语义包装 apply_manifest）
- rollback_deployment(state, name, to_revision=None)  回滚
- ClusterState.revisions: dict[name, list[dict]]      revision 历史
  每个 record: {"revision": int, "image": str, "replicas": int, "doc": dict}
- 回滚触发: Deployment YAML metadata.annotations["k8s-quest/rollback"] == "true"
  注意: 是 k8s-quest/rollback, 不是调研报告里写的 kubectl.quest/rollback
  （以实际 simulator.py 代码为准, T2 metadata 已注明此差异）
"""
from app.validator import Level, CheckResult
from app.simulator import (
    apply_manifest,
    preset_state,
    ClusterState,
    K8sError,
)


# ---------------------------------------------------------------------------
# 类型安全 helper：从 deployment doc 中安全提取 replicas / image
# ---------------------------------------------------------------------------

def _safe_get_replicas(dep: dict) -> tuple[int | None, str | None]:
    """安全提取 Deployment spec.replicas。

    Returns:
        (replicas, None) 成功; (None, error_msg) 结构异常。
    simulator 的 _validate_deployment 已保证 replicas 是 int, 但 check_fn
    做防御性守卫以防 simulator 未来变更或 state 被外部篡改。
    """
    if not isinstance(dep, dict):
        return None, "Deployment 文档结构异常"
    spec = dep.get("spec")
    if not isinstance(spec, dict):
        return None, "Deployment spec 缺失或类型错误（必须是映射）"
    replicas = spec.get("replicas", 1)
    # bool 是 int 子类, 必须排除（True/False 不应作为副本数）
    if isinstance(replicas, bool) or not isinstance(replicas, int):
        return None, f"spec.replicas 必须是整数，实际为 {type(replicas).__name__}"
    return replicas, None


def _safe_get_image(dep: dict) -> tuple[str | None, str | None]:
    """安全提取 Deployment template 第一个 container 的 image。

    Returns:
        (image, None) 成功; (None, error_msg) 结构异常。
    守卫 template.spec / containers 每一层, 防 truthy 非 dict/list 绕过
    falsy-only guard 导致 AttributeError → HTTP 500。
    """
    if not isinstance(dep, dict):
        return None, "Deployment 文档结构异常"
    spec = dep.get("spec")
    if not isinstance(spec, dict):
        return None, "Deployment spec 缺失或类型错误（必须是映射）"
    template = spec.get("template")
    # template 必须是非空 dict。仅 `if not template` falsy-only 判断会被
    # truthy 非 dict（str/int）绕过, 随后 .get 抛 AttributeError → 500。
    if not isinstance(template, dict) or not template:
        return None, "Deployment 缺少 spec.template（必须是非空映射）"
    tmpl_spec = template.get("spec")
    if not isinstance(tmpl_spec, dict):
        return None, "spec.template.spec 缺失或类型错误（必须是映射）"
    containers = tmpl_spec.get("containers")
    # containers 必须是非空 list。falsy-only guard 会被 truthy 非 list 绕过。
    if not isinstance(containers, list) or not containers:
        return None, "template 缺少 containers（必须是非空列表）"
    c0 = containers[0]
    if not isinstance(c0, dict):
        return None, f"containers[0] 必须是映射，实际为 {type(c0).__name__}"
    return c0.get("image", ""), None


def _deploy_pod_count(state: ClusterState, name: str) -> int:
    """统计某 Deployment 实例化的 Pod 数量（按 pod-template-hash 标签）。"""
    count = 0
    for p in state.pods.values():
        labels = p.get("metadata", {}).get("labels")
        if isinstance(labels, dict) and labels.get("pod-template-hash") == name:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Q2.1 创建第一个 Deployment
# ---------------------------------------------------------------------------

def _check_21_create_deployment(user_yaml: str) -> CheckResult:
    """Q2.1 创建第一个 Deployment: nginx-deploy, 3 replicas, nginx:1.25"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 找名为 nginx-deploy 的 Deployment
    if "nginx-deploy" not in state.deployments:
        names = list(state.deployments.keys())
        return CheckResult(
            ok=False,
            error=f"没找到 Deployment 'nginx-deploy'，当前: {names}",
            hints=["Deployment 的 metadata.name 决定名字"],
        )

    dep = state.deployments["nginx-deploy"]

    # 校验 replicas
    replicas, err = _safe_get_replicas(dep)
    if err is not None:
        return CheckResult(ok=False, error=err, hints=["spec.replicas 应为整数 3"])
    if replicas != 3:
        return CheckResult(
            ok=False,
            error=f"replicas 应为 3，实际 {replicas}",
            hints=["spec.replicas 控制副本数（期望状态）"],
        )

    # 校验 image
    image, err = _safe_get_image(dep)
    if err is not None:
        return CheckResult(
            ok=False, error=err,
            hints=["image 在 spec.template.spec.containers[0].image"],
        )
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"镜像应为 nginx:1.25，实际 {image}",
            hints=["检查 spec.template.spec.containers[0].image"],
        )

    # 教学分支：缺 selector（真实 K8s 强制要求 selector 匹配 template.labels）
    spec = dep.get("spec")
    if isinstance(spec, dict) and "selector" not in spec:
        return CheckResult(
            ok=False,
            error="缺少 spec.selector（Deployment 必须声明如何选 Pod）",
            hints=["selector.matchLabels 应与 template.labels 一致"],
        )

    # 校验 Pod 实例化数量（simulator 应已生成 3 个 Pod）
    pod_count = _deploy_pod_count(state, "nginx-deploy")
    if pod_count != 3:
        return CheckResult(
            ok=False,
            error=f"期望 3 个 Pod，实际 {pod_count}（simulator 应按 replicas 实例化）",
            hints=["Deployment 会自动维持 replicas 个 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！Deployment 自动维持 3 个副本——这就是期望状态 🚀"],
    )


LEVEL_Q2_1 = Level(
    id="Q2.1",
    chapter="ch02",
    title="创建第一个 Deployment",
    description="""
# 创建第一个 Deployment 🚀

**Deployment** 是 K8s 里管 Pod 的工作负载。和直接创建 Pod 不同，Deployment 帮你维持**期望状态**——你说要 3 个副本，它就始终保证有 3 个 Pod 在跑，挂了自动拉起。

## 要求

创建一个 Deployment：
- `kind: Deployment`，名字 `nginx-deploy`
- `3` 个副本（`spec.replicas: 3`）
- Pod 模板里容器镜像 `nginx:1.25`

## 提示

Deployment 的关键字段：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:              # 选哪些 Pod 归你管，必须匹配 template.labels
    matchLabels:
      app: nginx
  template:              # Pod 的模板
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
```

> 💡 `selector` 告诉 Deployment 用标签选 Pod，它必须和 `template.labels` 一致，否则 K8s 会拒绝创建。
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
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
    check_fn=_check_21_create_deployment,
)


# ---------------------------------------------------------------------------
# Q2.2 扩缩容
# ---------------------------------------------------------------------------

def _check_22_scale(user_yaml: str) -> CheckResult:
    """Q2.2 扩缩容: api-deploy, 5 replicas, python:3.11-slim"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "api-deploy" not in state.deployments:
        names = list(state.deployments.keys())
        return CheckResult(
            ok=False,
            error=f"没找到 Deployment 'api-deploy'，当前: {names}",
            hints=["Deployment 的 metadata.name 应为 api-deploy"],
        )

    dep = state.deployments["api-deploy"]

    # 校验 replicas
    replicas, err = _safe_get_replicas(dep)
    if err is not None:
        return CheckResult(ok=False, error=err, hints=["spec.replicas 应为整数 5"])
    if replicas != 5:
        return CheckResult(
            ok=False,
            error=f"replicas 应为 5，实际 {replicas}（水平扩展 = 改 replicas）",
            hints=["spec.replicas: 5"],
        )

    # 校验 image
    image, err = _safe_get_image(dep)
    if err is not None:
        return CheckResult(
            ok=False, error=err,
            hints=["image 在 spec.template.spec.containers[0].image"],
        )
    if image != "python:3.11-slim":
        return CheckResult(
            ok=False,
            error=f"镜像应为 python:3.11-slim，实际 {image}",
            hints=["检查 spec.template.spec.containers[0].image"],
        )

    # 校验 Pod 数量同步到 5
    pod_count = _deploy_pod_count(state, "api-deploy")
    if pod_count != 5:
        return CheckResult(
            ok=False,
            error=f"期望 5 个 Pod，实际 {pod_count}（simulator 应按 replicas 扩容）",
            hints=["改 replicas 后 Deployment 会自动增减 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["扩容完成！改 replicas 就是水平扩展 📈"],
    )


LEVEL_Q2_2 = Level(
    id="Q2.2",
    chapter="ch02",
    title="扩缩容",
    description="""
# 扩缩容 📈

业务流量上来了？**水平扩展**只需改一个字段：`spec.replicas`。Deployment 会自动增减 Pod 数量，这就是云原生的弹性。

## 要求

创建一个 API 服务的 Deployment：
- `kind: Deployment`，名字 `api-deploy`
- `5` 个副本
- 镜像 `python:3.11-slim`

## 提示

把 Q2.1 的思路搬过来，改名字、副本数、镜像：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deploy
spec:
  replicas: 5
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: python:3.11-slim
```

> 💡 `replicas` 是**期望状态**——你声明要几个，Deployment 控制器就拼命维持几个。改这个数字 = 扩容/缩容，无需重建 Deployment。
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deploy
spec:
  replicas: 5
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: python:3.11-slim
""",
    check_fn=_check_22_scale,
)


# ---------------------------------------------------------------------------
# Q2.3 滚动更新
# ---------------------------------------------------------------------------

# 预置状态：web-deploy v1, 3 副本 nginx:1.24（玩家需升级到 nginx:1.25）
_WEB_DEPLOY_V1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  labels:
    app: web
spec:
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
          image: nginx:1.24
"""


def _safe_get_pod_image(pod: dict) -> tuple[str | None, str | None]:
    """安全提取 Pod 第一个 container 的 image。

    Pod spec 来自 Deployment template, 结构与 deployment 不同（无
    template 层, containers 直接在 spec 下）。逐层 isinstance 守卫。
    """
    if not isinstance(pod, dict):
        return None, "Pod 文档结构异常"
    spec = pod.get("spec")
    if not isinstance(spec, dict):
        return None, "Pod spec 缺失或类型错误"
    containers = spec.get("containers")
    if not isinstance(containers, list) or not containers:
        return None, "Pod 缺少 containers（必须是非空列表）"
    c0 = containers[0]
    if not isinstance(c0, dict):
        return None, f"Pod containers[0] 必须是映射，实际为 {type(c0).__name__}"
    return c0.get("image", ""), None


def _check_23_rolling_update(user_yaml: str) -> CheckResult:
    """Q2.3 滚动更新: 已有 web-deploy v1(nginx:1.24) → 玩家升级到 nginx:1.25"""
    state = ClusterState()
    try:
        state = preset_state(state, _WEB_DEPLOY_V1)       # 预置 v1
        state = apply_manifest(state, user_yaml)          # 玩家升级
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "web-deploy" not in state.deployments:
        return CheckResult(
            ok=False,
            error="应更新已有的 web-deploy，而非新建别的 Deployment",
            hints=["metadata.name 必须是 web-deploy"],
        )

    dep = state.deployments["web-deploy"]
    image, err = _safe_get_image(dep)
    if err is not None:
        return CheckResult(ok=False, error=err, hints=["检查 spec.template.spec.containers[0].image"])

    # 错误分支：image 没改（还是旧版本）
    if image == "nginx:1.24":
        return CheckResult(
            ok=False,
            error="image 还是 nginx:1.24，需升级到 nginx:1.25",
            hints=["改 spec.template.spec.containers[0].image 为 nginx:1.25"],
        )

    # 错误分支：改成了错误的版本
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"image 应为 nginx:1.25，实际 {image}",
            hints=["只改 image，其余字段保持和 v1 一致"],
        )

    # 校验所有 Pod 都升级到新版本（滚动完成的标志）
    web_pods = [
        p for p in state.pods.values()
        if isinstance(p.get("metadata", {}).get("labels"), dict)
        and p["metadata"]["labels"].get("pod-template-hash") == "web-deploy"
    ]
    if not web_pods:
        return CheckResult(ok=False, error="没有 web-deploy 的 Pod（simulator 未实例化）", hints=[])
    not_upgraded = []
    for p in web_pods:
        pod_img, perr = _safe_get_pod_image(p)
        if perr is not None or pod_img != "nginx:1.25":
            not_upgraded.append(p)
    if not_upgraded:
        return CheckResult(
            ok=False,
            error=f"还有 {len(not_upgraded)}/{len(web_pods)} 个 Pod 未升级到 nginx:1.25",
            hints=["滚动更新应替换所有 Pod 的镜像"],
        )

    # 教学点：升级应产生新 revision（改 image = 改 template = 新 revision）
    revs = state.revisions.get("web-deploy", [])
    if len(revs) < 2:
        return CheckResult(
            ok=False,
            error=f"升级应产生新 revision，但历史只有 {len(revs)} 条（template 未变化？）",
            hints=["改 image 会触发新 revision"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["滚动更新完成！声明式升级——你只声明目标，K8s 自动滚动 🔄"],
    )


LEVEL_Q2_3 = Level(
    id="Q2.3",
    chapter="ch02",
    title="滚动更新",
    description="""
# 滚动更新 🔄

线上服务要升级版本，不能停机。**声明式升级**：你只把 `image` 改成新版本，Deployment 会自动滚动替换 Pod——先起新的，再杀旧的，零停机。

## 场景

集群里**已经有一个** `web-deploy`（3 副本，镜像 `nginx:1.24`）。你的任务：把它升级到 `nginx:1.25`。

## 要求

提交一个 `web-deploy` 的 Deployment YAML，把镜像从 `nginx:1.24` 改成 `nginx:1.25`，其余字段保持不变。

## 提示

只需改 `image` 一行：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
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
          image: nginx:1.25   # ← 把 1.24 改成 1.25
```

> 💡 改 `spec.template`（哪怕只改 image）会触发新 **revision**。Deployment 控制器创建新 ReplicaSet、渐进替换 Pod。这就是"声明式"——你说目标，K8s 想办法达到。
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
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
          image: nginx:1.24   # ← 升级到 nginx:1.25
""",
    check_fn=_check_23_rolling_update,
)


# ---------------------------------------------------------------------------
# Q2.4 回滚
# ---------------------------------------------------------------------------

# 失败升级用的"坏 image"（不存在的版本）
_WEB_DEPLOY_BAD = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  labels:
    app: web
spec:
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
          image: nginx:9.99.99   # 故意写错的版本（模拟失败升级）
"""

# 回滚触发的 annotation（以 simulator.py 实际代码为准）
# 注意: 是 k8s-quest/rollback, 不是调研报告里的 kubectl.quest/rollback
_ROLLBACK_ANNOTATION = "k8s-quest/rollback"


def _check_24_rollback(user_yaml: str) -> CheckResult:
    """Q2.4 回滚: 模拟失败升级 → 玩家 rollback 回上一版(nginx:1.24)"""
    state = ClusterState()
    try:
        state = preset_state(state, _WEB_DEPLOY_V1)           # revision 1: nginx:1.24
        state = apply_manifest(state, _WEB_DEPLOY_BAD)        # revision 2: 失败升级 nginx:9.99.99
        state = apply_manifest(state, user_yaml)              # 玩家触发回滚
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "web-deploy" not in state.deployments:
        return CheckResult(
            ok=False,
            error="web-deploy 不存在（回滚目标丢失）",
            hints=[],
        )

    dep = state.deployments["web-deploy"]
    image, err = _safe_get_image(dep)
    if err is not None:
        return CheckResult(ok=False, error=err, hints=["检查 spec.template.spec.containers[0].image"])

    # 错误分支1: 还停在坏版本（没触发回滚）
    if image == "nginx:9.99.99":
        return CheckResult(
            ok=False,
            error="还在坏版本 nginx:9.99.99，回滚未生效",
            hints=[
                f'给 Deployment 加 annotation: {_ROLLBACK_ANNOTATION}: "true" 来触发回滚',
                "annotation 写在 metadata.annotations 下",
            ],
        )

    # 错误分支2: 回滚到了错误的版本
    if image != "nginx:1.24":
        return CheckResult(
            ok=False,
            error=f"回滚后 image 应为 nginx:1.24，实际 {image}",
            hints=["rollback 默认回到上一个 revision（nginx:1.24）"],
        )

    # 校验所有 Pod 也回到旧版本
    web_pods = [
        p for p in state.pods.values()
        if isinstance(p.get("metadata", {}).get("labels"), dict)
        and p["metadata"]["labels"].get("pod-template-hash") == "web-deploy"
    ]
    bad_pods = []
    for p in web_pods:
        pod_img, perr = _safe_get_pod_image(p)
        if perr is not None or pod_img != "nginx:1.24":
            bad_pods.append(p)
    if bad_pods:
        return CheckResult(
            ok=False,
            error=f"还有 {len(bad_pods)}/{len(web_pods)} 个 Pod 未回到 nginx:1.24",
            hints=["回滚应重建所有 Pod 的镜像"],
        )

    # 教学点：rollback 应产生新 revision 号（K8s 真实行为）
    # 预期: rev1(1.24) → rev2(9.99.99) → rev3(1.24, 回滚产生)
    revs = state.revisions.get("web-deploy", [])
    if len(revs) < 3:
        return CheckResult(
            ok=False,
            error=f"回滚应产生新 revision，实际历史 {len(revs)} 条（预期 ≥3）",
            hints=["rollback 本身是一次 template 变更，会产生新 revision"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["回滚成功！Deployment 自带撤销，revision 历史是你的后悔药 🔙"],
    )


LEVEL_Q2_4 = Level(
    id="Q2.4",
    chapter="ch02",
    title="回滚",
    description="""
# 回滚 🔙

升级翻车了？别慌。Deployment 自带**版本历史**，一键回滚到上一版。

## 场景

你刚把 `web-deploy` 升级到一个**不存在的镜像版本**（`nginx:9.99.99`），Pod 全部起不来。现在需要**回滚**到上一个版本（`nginx:1.24`）。

## 要求

提交一个 `web-deploy` 的 Deployment YAML，加上回滚 annotation：
```yaml
metadata:
  annotations:
    k8s-quest/rollback: "true"
```

simulator 检测到这个 annotation，就会把 Deployment 回滚到上一个 revision。

## 提示

完整 YAML（只需加 annotation 触发回滚）：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    k8s-quest/rollback: "true"   # ← 关键：触发回滚
spec:
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
          image: nginx:1.24
```

> 💡 真实 K8s 用 `kubectl rollout undo deployment/web-deploy` 回滚。本质是把上一个 revision 的 template 复制回来——这本身又是一次 template 变更，会产生**新的 revision 号**（不是回到旧号）。所以 revision 号单调递增，但 template 指向旧的。
>
> 在 k8s-quest 里，我们用 annotation `k8s-quest/rollback: "true"` 来触发同样的行为。
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    k8s-quest/rollback: "true"   # ← 加这个 annotation 触发回滚
spec:
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
          image: nginx:1.24
""",
    check_fn=_check_24_rollback,
)


# ==================== Chapter 2 关卡汇总 ====================

CHAPTER_2_LEVELS = [LEVEL_Q2_1, LEVEL_Q2_2, LEVEL_Q2_3, LEVEL_Q2_4]
