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


# ==================== Chapter 2 关卡汇总 ====================

CHAPTER_2_LEVELS = [LEVEL_Q2_1]
