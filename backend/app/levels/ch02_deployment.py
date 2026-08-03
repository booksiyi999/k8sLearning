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
from app.validator import Level, CheckResult, Lesson
from app.simulator import (
    apply_manifest,
    preset_state,
    ClusterState,
    K8sError,
)
import yaml


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
    lesson=Lesson(
        concept="""\
## 什么是 Deployment？

**Deployment** 是 Kubernetes 中最常用的工作负载控制器，负责管理无状态应用的生命周期。它通过 **ReplicaSet** 间接管理 Pod，提供副本管理、滚动更新和版本回滚三大核心能力。

### 声明式模型

Deployment 基于**期望状态（Desired State）**模型工作：你声明"要 3 个运行 nginx:1.25 的 Pod"，Deployment 控制器持续监控集群，发现实际状态与期望不符时自动 reconcile（调和）--Pod 挂了自动拉起，副本数变了自动增减。

### Deployment → ReplicaSet → Pod 三层结构

- **Deployment** 管理版本和更新策略
- **ReplicaSet** 管理某版本的 Pod 副本数（每次更新 template 产生新 RS）
- **Pod** 是实际运行的容器组

### spec.template 是核心

`spec.template` 是 Pod 模板，Deployment 基于 it 创建 Pod。**任何对 template 的修改都会触发新版本**（新 ReplicaSet + 滚动更新）。修改非 template 字段（如 replicas）不会产生新版本。

### selector 必须匹配 template.labels

Deployment 的 `spec.selector.matchLabels` 必须与 `spec.template.metadata.labels` 一致，否则 K8s 拒绝创建。这确保 Deployment 能正确识别它管理的 Pod。
""",
        key_fields=[
            {"name": "apiVersion", "description": "K8s API 版本，Deployment 用 apps/v1", "required": True, "example": "apps/v1"},
            {"name": "spec.replicas", "description": "期望副本数，Deployment 控制器维持此数量的 Pod", "required": True, "example": "3"},
            {"name": "spec.selector.matchLabels", "description": "标签选择器，必须与 template.labels 一致", "required": True, "example": "{app: nginx}"},
            {"name": "spec.template", "description": "Pod 模板，定义 Pod 的 metadata 和 spec", "required": True, "example": "Pod YAML template"},
            {"name": "spec.template.spec.containers[].image", "description": "容器镜像地址，修改它触发滚动更新", "required": True, "example": "nginx:1.25"},
        ],
        diagram="""\
┌──────── Deployment (nginx-deploy) ────────────┐
│  spec:                                         │
│    replicas: 3                                 │
│    selector:                                   │
│      matchLabels:                              │
│        app: nginx  ◄──── 必须与 template 一致   │
│    template:                                   │
│      metadata:                                 │
│        labels:                                 │
│          app: nginx  ◄──── Pod 模板标签         │
│      spec:                                     │
│        containers:                             │
│        - name: nginx                           │
│          image: nginx:1.25                     │
└────────────────────┬───────────────────────────┘
                     │ 管理
                     ▼
┌──────── ReplicaSet (nginx-deploy-xxx) ────────┐
│  replicas: 3                                   │
└──────┬──────────┬──────────┬──────────────────┘
       │          │          │ 实例化
       ▼          ▼          ▼
   ┌─Pod─┐   ┌─Pod─┐   ┌─Pod─┐
   │nginx│   │nginx│   │nginx│
   │:1.25│   │:1.25│   │:1.25│
   └─────┘   └─────┘   └─────┘
""",
        example_yaml="""\
apiVersion: apps/v1              # Deployment 用 apps/v1
kind: Deployment                 # 资源类型: Deployment
metadata:                        # 元数据
  name: nginx-deploy             # Deployment 名称
spec:                            # 规格定义
  replicas: 3                    # 期望副本数
  selector:                      # 标签选择器
    matchLabels:                 # 必须与 template.labels 一致
      app: nginx
  template:                      # Pod 模板
    metadata:                    # Pod 元数据
      labels:                    # Pod 标签
        app: nginx
    spec:                        # Pod 规格
      containers:                # 容器列表
      - name: nginx              # 容器名
        image: nginx:1.25        # 容器镜像
""",
        common_errors=[
            "忘记写 apiVersion: apps/v1（写成 v1 会被拒绝）",
            "selector.matchLabels 与 template.labels 不一致（K8s 拒绝创建）",
            "忘记写 selector（Deployment 必须声明如何选 Pod）",
            "image 写在了 spec.containers 下而非 spec.template.spec.containers 下",
            "replicas 写成了字符串 '3' 而非整数 3",
        ],
        tips=[
            "Deployment 管的是期望状态，不是直接管 Pod--理解这点是学好 K8s 的关键",
            "用 kubectl get deploy 查看副本状态，kubectl describe deploy 排查问题",
            "selector 和 template.labels 必须完全匹配，这是新手最常踩的坑",
        ],
    ),
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
    lesson=Lesson(
        concept="""\
## 水平扩展（Horizontal Scaling）

**水平扩展**是通过增加 Pod 副本数来提升应用处理能力的方式。在 K8s 中，只需修改 `spec.replicas` 字段，Deployment 控制器会自动增减 Pod 数量。

### replicas 字段的工作机制

当你把 `replicas` 从 3 改为 5：
1. Deployment 控制器检测到期望副本数（5）> 当前副本数（3）
2. 通过 ReplicaSet 创建 2 个新 Pod
3. 新 Pod 被调度到有足够资源的 Node 上启动

缩容时反过来：控制器选择多余的 Pod（优先终止最新创建的）进行清理。

### 声明式 vs 命令式

- **声明式**：修改 YAML 中的 replicas，`kubectl apply -f` → K8s 自动调和
- **命令式**：`kubectl scale deployment api-deploy --replicas=5` → 直接修改

两种方式效果相同，但声明式更符合 GitOps 理念。

### 弹性伸缩（HPA）

生产环境中，可配合 **HPA（HorizontalPodAutoscaler）** 实现 CPU/内存阈值触发的自动扩缩容，无需人工干预。HPA 根据指标自动调整 Deployment 的 replicas 字段。
""",
        key_fields=[
            {"name": "spec.replicas", "description": "期望副本数，控制器自动维持此数量的 Pod", "required": True, "example": "5"},
            {"name": "spec.selector", "description": "标签选择器，选择属于此 Deployment 的 Pod", "required": True, "example": "{matchLabels: {app: api}}"},
            {"name": "spec.template", "description": "Pod 模板，扩容时基于此模板创建新 Pod", "required": True, "example": "Pod YAML template"},
        ],
        diagram="""\
    扩容前 (replicas: 3)              扩容后 (replicas: 5)

  ┌──────────────┐                 ┌──────────────────────┐
  │ Deployment    │                 │ Deployment            │
  │ replicas: 3   │ ──改 replicas─► │ replicas: 5           │
  └──────┬───────┘                 └──────────┬────────────┘
         │                                    │
         ▼                                    ▼
  ┌─RS──────────┐                 ┌─RS──────────────────────┐
  │ pods: 3     │                 │ pods: 5 (+2 新 Pod)     │
  └─┬───┬───┬───┘                 └─┬───┬───┬───┬───┬───────┘
    │   │   │                       │   │   │   │   │
    ▼   ▼   ▼                       ▼   ▼   ▼   ▼   ▼
  Pod1 Pod2 Pod3                 Pod1 Pod2 Pod3 Pod4 Pod5
  (已有)                         (已有)         (新建↑)(新建↑)
""",
        example_yaml="""\
apiVersion: apps/v1              # K8s API 版本
kind: Deployment                 # 资源类型: Deployment
metadata:                        # 元数据
  name: api-deploy               # Deployment 名称
spec:                            # 规格定义
  replicas: 5                    # 期望 5 个副本（水平扩展）
  selector:                      # 标签选择器
    matchLabels:
      app: api
  template:                      # Pod 模板
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api                # 容器名
        image: python:3.11-slim  # Python 镜像
""",
        common_errors=[
            "把 replicas 写在 spec.template.spec 下（应在 spec 下）",
            "replicas 设为 0（等于暂停应用，非特殊场景不要这样做）",
            "手动删除 Pod 来'缩容'（Deployment 会立即重建，正确做法是改 replicas）",
            "扩容后发现 Pod 一直 Pending（Node 资源不足）",
        ],
        tips=[
            "修改 replicas 是 K8s 中最快的扩缩容方式，无需重建 Deployment",
            "用 kubectl scale deploy <name> --replicas=N 快速扩缩容",
            "生产环境建议配合 HPA 实现自动弹性伸缩",
        ],
    ),
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
    lesson=Lesson(
        concept="""\
## 滚动更新（Rolling Update）

**滚动更新**是 Deployment 的默认更新策略，通过逐步替换旧 Pod 实现零停机升级。当你修改 `spec.template`（如改 image 版本），Deployment 自动触发滚动更新。

### 滚动更新过程

先启动新 Pod，确认就绪后，再终止旧 Pod，直到全部替换完成：

```
旧 ReplicaSet (v1, nginx:1.24)     新 ReplicaSet (v2, nginx:1.25)
  Pod1 ✓ ──────────→ 终止            Pod4 ✓ 启动
  Pod2 ✓ ──────────→ 终止            Pod5 ✓ 启动
  Pod3 ✓ ──────────→ 终止            Pod6 ✓ 启动
```

### maxSurge 和 maxUnavailable

- **maxSurge**：滚动过程中允许超出 replicas 的最大 Pod 数（默认 25%）。如 replicas=3，maxSurge=1，则最多同时有 4 个 Pod。
- **maxUnavailable**：滚动过程中允许不可用的最大 Pod 数（默认 25%）。如 replicas=3，maxUnavailable=1，则最少保持 2 个 Pod 可用。

### 新版本产生新 ReplicaSet

每次 template 变更创建新 ReplicaSet，旧 ReplicaSet 副本数降为 0 但不删除--这就是回滚的基础。Revision 号单调递增。
""",
        key_fields=[
            {"name": "spec.template.spec.containers[].image", "description": "修改镜像版本触发滚动更新", "required": True, "example": "nginx:1.25"},
            {"name": "spec.strategy.type", "description": "更新策略，默认 RollingUpdate", "required": False, "example": "RollingUpdate"},
            {"name": "spec.strategy.rollingUpdate.maxSurge", "description": "超出 replicas 的最大 Pod 数（数量或百分比）", "required": False, "example": "1"},
            {"name": "spec.strategy.rollingUpdate.maxUnavailable", "description": "允许不可用的最大 Pod 数（数量或百分比）", "required": False, "example": "1"},
        ],
        diagram="""\
  滚动更新过程 (replicas=3, maxSurge=1, maxUnavailable=1)

  时间 →    T0          T1          T2          T3          T4

  旧 RS  ┌─Pod1──┐  ┌─Pod1──┐  ┌────────┐  ┌────────┐  ┌────────┐
  (1.24) │ Pod2  │  │ Pod2  │  │ Pod2  │  ┌────────┐  ┌────────┐
         │ Pod3  │  │ Pod3  │  │ Pod3  │  │ Pod3  │  ┌────────┐
         └───────┘  └───────┘  └───────┘  └───────┘  └───────┘
  新 RS            ┌─Pod4──┐  ┌─Pod4──┐  ┌─Pod4──┐  ┌─Pod4──┐
  (1.25)           │       │  │ Pod5  │  │ Pod5  │  │ Pod5  │
                    └───────┘  └───────┘  └───────┘  │ Pod6  │
                                                    └───────┘

  副本数:  3          4          4          3          3
  旧 Pod:  3          3          2          1          0
  新 Pod:  0          1          2          2          3
""",
        example_yaml="""\
apiVersion: apps/v1              # K8s API 版本
kind: Deployment
metadata:
  name: web-deploy               # Deployment 名称
spec:
  replicas: 3                    # 3 个副本
  strategy:                      # 更新策略
    type: RollingUpdate          # 滚动更新（默认）
    rollingUpdate:
      maxSurge: 1                # 最多超出 1 个 Pod
      maxUnavailable: 1          # 最多 1 个不可用
  selector:
    matchLabels:
      app: web
  template:                      # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.25        # ← 改成新版本触发滚动更新
""",
        common_errors=[
            "改了 replicas 而非 image（修改 replicas 不会产生新 revision）",
            "改了 metadata.name（应保持和旧版本一致，只改 template 内字段）",
            "改了太多字段（应只改 image，其余保持不变）",
            "忘记保持 selector 和 template.labels 不变",
        ],
        tips=[
            "滚动更新是声明式的--你只声明目标 image，K8s 自动完成替换过程",
            "用 kubectl rollout status deployment/web-deploy 查看滚动进度",
            "用 kubectl rollout pause 可以暂停滚动更新，resume 恢复",
        ],
    ),
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

    # 教学目标守卫 (F2 修复): 到这里说明最终状态全对 (image==1.24 /
    # pods==1.24 / revisions>=3), 但旧实现漏检了玩家是否真用了 rollback
    # annotation。玩家直接提交 image: nginx:1.24 (无 annotation) 也会
    # 产生 rev3 并走到这里 → 静默 false-pass, 教学目标被架空。
    # 修复: 作为最后一道闸门, 验证 user_yaml 含 rollback annotation。
    # 放在状态校验之后, 让更具体的错误消息 (还在坏版本/错误版本/Pod 未回滚)
    # 优先返回; 仅当状态全对但没走回滚机制时才报此错。
    # apply_manifest 已成功 (走到这里说明 YAML 合法), 但仍需 isinstance
    # 守卫 metadata/annotations —— 它们可能是非 dict 类型 (字符串/列表/
    # None), 直接 .get 会抛 AttributeError → /api/check HTTP 500。
    try:
        user_doc = yaml.safe_load(user_yaml)
    except yaml.YAMLError:
        # apply_manifest 已成功解析过同一 YAML, 理论不会走到这里;
        # 防御性兜底, 避免异常冒泡到 API。
        user_doc = None
    user_has_rollback = False
    if isinstance(user_doc, dict):
        user_meta = user_doc.get("metadata")
        if isinstance(user_meta, dict):
            user_ann = user_meta.get("annotations")
            if isinstance(user_ann, dict):
                user_has_rollback = user_ann.get(_ROLLBACK_ANNOTATION) == "true"
    if not user_has_rollback:
        return CheckResult(
            ok=False,
            error=(
                "最终状态正确, 但未通过回滚 annotation 触发回滚。"
                "Q2.4 的教学目标是学会用 annotation 触发回滚, "
                f"请在 metadata.annotations 下添加 {_ROLLBACK_ANNOTATION}: \"true\""
            ),
            hints=[f'在 metadata.annotations 下加 {_ROLLBACK_ANNOTATION}: "true"'],
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
    lesson=Lesson(
        concept="""\
## 版本回滚（Rollout Undo）

**回滚**是 Deployment 的版本控制能力。每次修改 `spec.template` 都会产生一个 **revision**，Deployment 保留历史 revision 用于回退。

### Revision 机制

```
revision 1: nginx:1.24   (初始版本)
revision 2: nginx:9.99.99 (失败升级)
revision 3: nginx:1.24    (回滚 = 复制 rev1 的 template)
```

回滚不是"删除 revision 2"，而是创建**新 revision 3**，其 template 内容等于 revision 1。因此 revision 号单调递增，但 template 指向旧版本。

### 触发回滚

在真实 K8s 中：
- `kubectl rollout undo deployment/web-deploy` → 回到上一版本
- `kubectl rollout undo deployment/web-deploy --to-revision=1` → 回到指定版本

在 k8s-quest 中，通过 annotation `k8s-quest/rollback: "true"` 触发回滚。

### 为什么保留旧 ReplicaSet？

Deployment 不会删除旧 ReplicaSet，只把副本数设为 0。回滚时直接把目标 ReplicaSet 的副本数恢复，无需重新拉取镜像--比重建快得多。默认保留 10 个历史 revision（`revisionHistoryLimit: 10`）。
""",
        key_fields=[
            {"name": "metadata.annotations", "description": "通过 annotation 触发回滚操作", "required": True, "example": "{k8s-quest/rollback: true}"},
            {"name": "spec.template", "description": "Pod 模板，回滚时复制旧 revision 的 template", "required": True, "example": "Pod YAML template"},
            {"name": "revisionHistoryLimit", "description": "保留的历史 revision 数量（默认 10）", "required": False, "example": "10"},
            {"name": "spec.replicas", "description": "副本数，回滚后保持不变", "required": True, "example": "3"},
        ],
        diagram="""\
  Revision 历史 (revision 号单调递增)

  ┌─rev 1──────────┐  ┌─rev 2───────────┐  ┌─rev 3──────────┐
  │ image: 1.24    │  │ image: 9.99.99  │  │ image: 1.24    │
  │ RS: rs-aaa     │  │ RS: rs-bbb      │  │ RS: rs-aaa     │
  │ replicas: 0    │  │ replicas: 0     │  │ replicas: 3    │
  └────────────────┘  └────────────────┘  └────────────────┘
         ▲                                      │
         │         回滚 = 复制 rev1 template     │
         └──────────────────────────────────────┘

  回滚后: rev3 的 template == rev1 的 template
         rev3 是新 revision（不是回到 rev1）
         rs-aaa 副本数恢复为 3（无需重新拉镜像）
""",
        example_yaml="""\
apiVersion: apps/v1              # K8s API 版本
kind: Deployment
metadata:                        # 元数据
  name: web-deploy               # Deployment 名称
  annotations:                   # 注解区
    k8s-quest/rollback: "true"   # ← 触发回滚到上一版本
spec:                            # 规格定义
  replicas: 3                    # 副本数保持不变
  selector:                      # 标签选择器
    matchLabels:
      app: web
  template:                      # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.24        # 回滚后的镜像版本
""",
        common_errors=[
            "直接改 image 回旧版本而不触发回滚机制（教学目标是学会用 annotation）",
            "annotation 写在 spec 下而非 metadata.annotations 下",
            "annotation 的值写成了 true（布尔值）而非 \"true\"（字符串）",
            "回滚后 replicas 与原来不一致",
        ],
        tips=[
            "revision 号单调递增--回滚产生新 revision，不是回到旧号",
            "用 kubectl rollout history deployment/<name> 查看 revision 历史",
            "用 kubectl rollout undo --to-revision=N 回滚到指定版本",
            "旧 ReplicaSet 不删除只是副本数归零，回滚时直接恢复，速度极快",
        ],
    ),
)


# ==================== Chapter 2 关卡汇总 ====================

CHAPTER_2_LEVELS = [LEVEL_Q2_1, LEVEL_Q2_2, LEVEL_Q2_3, LEVEL_Q2_4]
