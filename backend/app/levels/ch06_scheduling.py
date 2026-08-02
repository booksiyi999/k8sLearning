"""Chapter 6: Scheduling 调度（4 关）

Q6.1 nodeSelector 节点选择
Q6.2 nodeAffinity 节点亲和性
Q6.3 Taints & Tolerations 污点与容忍
Q6.4 资源限制与调度
"""
from app.validator import Level, CheckResult
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


def _check_01_node_selector(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-ssd
  labels:
    disktype: ssd
    cpu: x86
---
apiVersion: v1
kind: Node
metadata:
  name: node-hdd
  labels:
    disktype: hdd
    cpu: x86
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，使用 nodeSelector 调度到 SSD 节点"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    selector = spec.get("nodeSelector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(ok=False, error="Pod 缺少 nodeSelector", hints=["添加 nodeSelector: { disktype: ssd }"])

    if selector.get("disktype") != "ssd":
        return CheckResult(ok=False, error=f"nodeSelector.disktype 应为 'ssd'，实际 '{selector.get('disktype')}'", hints=[])

    return CheckResult(ok=True, state=state, hints=["nodeSelector 调度成功！Pod 被调度到有 disktype=ssd 标签的节点"])


def _check_02_node_affinity(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: gpu-node
  labels:
    gpu: "true"
    zone: us-east-1a
---
apiVersion: v1
kind: Node
metadata:
  name: cpu-node
  labels:
    gpu: "false"
    zone: us-east-1b
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，使用 nodeAffinity 调度到 GPU 节点"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    affinity = spec.get("affinity")
    if not isinstance(affinity, dict):
        return CheckResult(ok=False, error="Pod 缺少 affinity", hints=["添加 affinity.nodeAffinity"])

    node_affinity = affinity.get("nodeAffinity")
    if not isinstance(node_affinity, dict):
        return CheckResult(ok=False, error="缺少 affinity.nodeAffinity", hints=[])

    required = node_affinity.get("requiredDuringSchedulingIgnoredDuringExecution")
    if not isinstance(required, dict):
        return CheckResult(ok=False, error="缺少 requiredDuringSchedulingIgnoredDuringExecution", hints=[])

    terms = required.get("nodeSelectorTerms")
    if not isinstance(terms, list) or not terms:
        return CheckResult(ok=False, error="缺少 nodeSelectorTerms", hints=[])

    # 检查是否有匹配 gpu=true 的 matchExpressions
    found_gpu = False
    for term in terms:
        if not isinstance(term, dict):
            continue
        exprs = term.get("matchExpressions", [])
        if isinstance(exprs, list):
            for expr in exprs:
                if isinstance(expr, dict) and expr.get("key") == "gpu":
                    found_gpu = True
                    break

    if not found_gpu:
        return CheckResult(ok=False, error="nodeAffinity 中没有匹配 'gpu' 标签的表达式", hints=["使用 matchExpressions 匹配 gpu: true"])

    return CheckResult(ok=True, state=state, hints=["nodeAffinity 调度成功！比 nodeSelector 更灵活的调度方式"])


def _check_03_taints_tolerations(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，添加 toleration 容忍节点的污点"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    tolerations = spec.get("tolerations")
    if not isinstance(tolerations, list) or not tolerations:
        return CheckResult(ok=False, error="Pod 缺少 tolerations", hints=["添加 tolerations 来容忍节点污点"])

    found_toleration = False
    for t in tolerations:
        if isinstance(t, dict):
            key = t.get("key", "")
            operator = t.get("operator", "Equal")
            effect = t.get("effect", "")
            if key == "dedicated" or (operator == "Exists" and effect in ["NoSchedule", "NoExecute"]):
                found_toleration = True
                break

    if not found_toleration:
        return CheckResult(ok=False, error="没有找到有效的 toleration", hints=["toleration 需要匹配节点的 taint (key/effect)"])

    return CheckResult(ok=True, state=state, hints=["Toleration 配置成功！让 Pod 可以被调度到有污点的节点"])


def _check_04_resource_limits(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建 Pod，设置 resources requests 和 limits"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    resources = c.get("resources")
    if not isinstance(resources, dict):
        return CheckResult(ok=False, error="容器缺少 resources", hints=["添加 resources.requests 和 resources.limits"])

    requests = resources.get("requests")
    if not isinstance(requests, dict) or not requests:
        return CheckResult(ok=False, error="缺少 resources.requests", hints=["requests 用于调度决策"])

    if "cpu" not in requests:
        return CheckResult(ok=False, error="requests 中缺少 cpu", hints=["添加 cpu request，如 cpu: 100m"])

    if "memory" not in requests:
        return CheckResult(ok=False, error="requests 中缺少 memory", hints=["添加 memory request，如 memory: 128Mi"])

    limits = resources.get("limits")
    if not isinstance(limits, dict) or not limits:
        return CheckResult(ok=False, error="缺少 resources.limits", hints=["limits 用于限制容器最大资源使用"])

    if "cpu" not in limits:
        return CheckResult(ok=False, error="limits 中缺少 cpu", hints=["添加 cpu limit"])

    if "memory" not in limits:
        return CheckResult(ok=False, error="limits 中缺少 memory", hints=["添加 memory limit"])

    return CheckResult(ok=True, state=state, hints=["资源限制配置成功！requests 调度用，limits 限流用"])


CHAPTER_6_LEVELS: list[Level] = [
    Level(id="Q6.1", chapter="ch06", title="nodeSelector 节点选择",
          description="集群有 node-ssd(disktype=ssd) 和 node-hdd(disktype=hdd) 两个节点。创建 Pod，用 nodeSelector 调度到 SSD 节点",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n    - name: nginx\n      image: nginx\n  # nodeSelector",
          check_fn=_check_01_node_selector),
    Level(id="Q6.2", chapter="ch06", title="nodeAffinity 节点亲和性",
          description="集群有 gpu-node(gpu=true) 和 cpu-node(gpu=false)。创建 Pod，用 nodeAffinity 的 required 规则调度到 GPU 节点",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: ml-pod\nspec:\n  containers:\n    - name: app\n      image: tensorflow:latest\n  # affinity.nodeAffinity",
          check_fn=_check_02_node_affinity),
    Level(id="Q6.3", chapter="ch06", title="Taints & Tolerations",
          description="创建一个 Pod，配置 toleration 容忍节点的 dedicated 污点",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: special-pod\nspec:\n  containers:\n    - name: app\n      image: nginx\n  # tolerations",
          check_fn=_check_03_taints_tolerations),
    Level(id="Q6.4", chapter="ch06", title="资源限制与调度",
          description="创建一个 Pod，设置 CPU 和 memory 的 requests 和 limits",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: limited-pod\nspec:\n  containers:\n    - name: app\n      image: nginx\n      # resources.requests 和 resources.limits",
          check_fn=_check_04_resource_limits),
]
