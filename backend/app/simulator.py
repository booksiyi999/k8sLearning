from dataclasses import dataclass, field
from typing import Any
import copy
import yaml


class K8sError(Exception):
    """模拟器抛出的所有错误。"""


@dataclass
class ClusterState:
    """虚拟集群状态：存放所有 K8s 资源。

    revisions: deployment_name -> [revision records]
    每个 revision record: {revision, image, replicas, doc}
    仅在 Deployment apply 时记录, Pod/Service 操作不影响。
    """
    pods: dict[str, dict] = field(default_factory=dict)
    deployments: dict[str, dict] = field(default_factory=dict)
    services: dict[str, dict] = field(default_factory=dict)
    configmaps: dict[str, dict] = field(default_factory=dict)
    secrets: dict[str, dict] = field(default_factory=dict)
    persistentvolumes: dict[str, dict] = field(default_factory=dict)
    persistentvolumeclaims: dict[str, dict] = field(default_factory=dict)
    nodes: dict[str, dict] = field(default_factory=dict)
    revisions: dict[str, list[dict]] = field(default_factory=dict)
    # v0.5: Ch7-Ch12 新增资源类型
    jobs: dict[str, dict] = field(default_factory=dict)
    cronjobs: dict[str, dict] = field(default_factory=dict)
    statefulsets: dict[str, dict] = field(default_factory=dict)
    roles: dict[str, dict] = field(default_factory=dict)
    rolebindings: dict[str, dict] = field(default_factory=dict)
    clusterroles: dict[str, dict] = field(default_factory=dict)
    clusterrolebindings: dict[str, dict] = field(default_factory=dict)
    horizontalpodautoscalers: dict[str, dict] = field(default_factory=dict)
    ingresses: dict[str, dict] = field(default_factory=dict)
    networkpolicies: dict[str, dict] = field(default_factory=dict)
    # v0.6: Ch13-Ch28 新增资源类型
    daemonsets: dict[str, dict] = field(default_factory=dict)
    namespaces: dict[str, dict] = field(default_factory=dict)
    resourcequotas: dict[str, dict] = field(default_factory=dict)
    limitranges: dict[str, dict] = field(default_factory=dict)
    poddisruptionbudgets: dict[str, dict] = field(default_factory=dict)
    priorityclasses: dict[str, dict] = field(default_factory=dict)
    customresourcedefinitions: dict[str, dict] = field(default_factory=dict)
    serviceaccounts: dict[str, dict] = field(default_factory=dict)
    # v0.7: Ch17-Ch18 自定义资源实例
    customresources: dict[str, dict] = field(default_factory=dict)
    # v0.8: Ch19-Ch20 新增资源类型
    storageclasses: dict[str, dict] = field(default_factory=dict)
    volumesnapshots: dict[str, dict] = field(default_factory=dict)
    volumesnapshotcontents: dict[str, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _has_circular_ref(obj, _seen=None):
    """检测 yaml.safe_load 产物是否含循环引用。

    yaml.safe_load 对自引用 anchor (&a / *a) **不报错**, 直接构造出
    循环引用的 Python dict (如 labels.tier → labels 自身)。该结构若落入
    result.state 并被 FastAPI 序列化, json.dumps 抛 ValueError
    "Circular reference detected" —— 该异常发生在 endpoint try/except
    **之外的中间件层**, 止血兜不住, 直接 HTTP 500。

    本函数在 parse 后立刻检测, 从根源阻断循环结构进入集群状态。
    使用 backtracking (seen.add / discard) 只标记当前遍历路径上的 id,
    避免对 YAML alias 造成的合法共享引用 (diamond, 非环) 误报。
    """
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return True
    if isinstance(obj, dict):
        _seen.add(obj_id)
        for v in obj.values():
            if _has_circular_ref(v, _seen):
                return True
        _seen.discard(obj_id)
    elif isinstance(obj, list):
        _seen.add(obj_id)
        for item in obj:
            if _has_circular_ref(item, _seen):
                return True
        _seen.discard(obj_id)
    return False


def _extract_image(doc: dict) -> str:
    """从 Deployment doc 中提取第一个容器的 image。

    供 revision history 记录使用。已通过 _validate_deployment 的 doc
    保证 template 是非空 dict, 但 _validate_deployment 不校验
    template.spec / containers, 因此此处仍需逐层 isinstance 守卫——
    否则 truthy 非 dict（如 template.spec: "broken" 字符串）会绕过
    falsy-only .get() 链, 在 .get("containers") 处抛 AttributeError
    → apply_manifest 崩溃 → /api/check HTTP 500。
    """
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        return ""
    template = spec.get("template")
    if not isinstance(template, dict):
        return ""
    tmpl_spec = template.get("spec")
    if not isinstance(tmpl_spec, dict):
        return ""
    containers = tmpl_spec.get("containers", [])
    if (
        isinstance(containers, list)
        and containers
        and isinstance(containers[0], dict)
    ):
        return containers[0].get("image", "")
    return ""


def _instantiate_pods(state: ClusterState, name: str, doc: dict) -> None:
    """为 Deployment 实例化 N 个虚拟 Pod, 替换该 Deployment 的旧 Pod。

    先删除该 Deployment 之前的 Pod (按 pod-template-hash label 匹配),
    再根据 replicas 创建新 Pod。这样 image 变更 / replica 变更 /
    rollback 都能正确反映到 Pod 列表中。
    """
    # 清理旧 Pod (该 deployment 创建的)
    old_pod_names = [
        pn for pn, p in state.pods.items()
        if isinstance(p.get("metadata", {}).get("labels", {}), dict)
        and p.get("metadata", {}).get("labels", {}).get("pod-template-hash") == name
    ]
    for pn in old_pod_names:
        del state.pods[pn]

    spec = doc["spec"]
    replicas = spec.get("replicas", 1)
    template = spec["template"]

    # 确保 template.metadata.labels 存在并打上 pod-template-hash
    template.setdefault("metadata", {}).setdefault("labels", {})[
        "pod-template-hash"
    ] = name

    for i in range(replicas):
        pod_name = f"{name}-{i:08x}"
        pod_doc = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "labels": dict(template["metadata"]["labels"]),
            },
            "spec": template.get("spec", {"containers": []}),
        }
        state.pods[pod_name] = pod_doc


def _record_revision(state: ClusterState, name: str, doc: dict) -> None:
    """为 Deployment 记录一个新的 revision。

    每次 apply (含 rollback) 都调用此函数。revision 号自动递增。
    doc 使用深拷贝, 防止后续原地修改污染历史记录。
    """
    rev_list = state.revisions.setdefault(name, [])
    new_rev_num = len(rev_list) + 1
    rev_list.append({
        "revision": new_rev_num,
        "image": _extract_image(doc),
        "replicas": doc.get("spec", {}).get("replicas", 1),
        "doc": copy.deepcopy(doc),
    })


# ---------------------------------------------------------------------------
# 公开 API: apply_manifest / preset_state / rollback_deployment
# ---------------------------------------------------------------------------

def apply_manifest(state: ClusterState, yaml_text: str) -> ClusterState:
    """把 YAML 应用到虚拟集群，返回新状态（in-place 修改）。

    支持的资源：Pod、Deployment、Service。
    支持多文档 YAML（用 --- 分隔）。

    Deployment 特殊行为:
    - 每次 apply 记录一个 revision (版本历史)
    - 若 YAML 含 annotation ``k8s-quest/rollback: "true"``,
      触发回滚到上一 revision 而非正常 apply
    """
    try:
        docs = list(yaml.safe_load_all(yaml_text))
    except yaml.YAMLError as e:
        raise K8sError(f"YAML 解析失败：{e}") from e
    except RecursionError:
        raise K8sError("YAML 嵌套层级过深（最多支持约 300 层）") from None

    for doc in docs:
        if doc is None:
            continue  # 跳过空文档（--- 后面没有内容）

        if not isinstance(doc, dict):
            raise K8sError("YAML 顶层必须是映射（dict）")

        if _has_circular_ref(doc):
            raise K8sError("YAML 含循环引用（自引用 anchor），拒绝应用")

        kind = doc.get("kind")
        if kind == "Pod":
            _apply_pod(state, doc)
        elif kind == "Deployment":
            _apply_deployment(state, doc)
        elif kind == "Service":
            _apply_service(state, doc)
        elif kind == "ConfigMap":
            _apply_configmap(state, doc)
        elif kind == "Secret":
            _apply_secret(state, doc)
        elif kind == "PersistentVolume":
            _apply_pv(state, doc)
        elif kind == "PersistentVolumeClaim":
            _apply_pvc(state, doc)
        elif kind == "Node":
            _apply_node(state, doc)
        elif kind == "Job":
            _apply_job(state, doc)
        elif kind == "CronJob":
            _apply_cronjob(state, doc)
        elif kind == "StatefulSet":
            _apply_statefulset(state, doc)
        elif kind == "Role":
            _apply_role(state, doc)
        elif kind == "RoleBinding":
            _apply_rolebinding(state, doc)
        elif kind == "ClusterRole":
            _apply_clusterrole(state, doc)
        elif kind == "ClusterRoleBinding":
            _apply_clusterrolebinding(state, doc)
        elif kind == "HorizontalPodAutoscaler":
            _apply_hpa(state, doc)
        elif kind == "Ingress":
            _apply_ingress(state, doc)
        elif kind == "NetworkPolicy":
            _apply_networkpolicy(state, doc)
        elif kind == "DaemonSet":
            _apply_daemonset(state, doc)
        elif kind == "Namespace":
            _apply_namespace(state, doc)
        elif kind == "ResourceQuota":
            _apply_resourcequota(state, doc)
        elif kind == "LimitRange":
            _apply_limitrange(state, doc)
        elif kind == "PodDisruptionBudget":
            _apply_pdb(state, doc)
        elif kind == "PriorityClass":
            _apply_priorityclass(state, doc)
        elif kind == "CustomResourceDefinition":
            _apply_crd(state, doc)
        elif kind == "ServiceAccount":
            _apply_serviceaccount(state, doc)
        elif kind == "StorageClass":
            _apply_storageclass(state, doc)
        elif kind == "VolumeSnapshot":
            _apply_volumesnapshot(state, doc)
        elif kind == "VolumeSnapshotContent":
            _apply_volumesnapshotcontent(state, doc)
        else:
            # 尝试作为自定义资源（CRD 实例）处理
            _apply_customresource(state, doc)

    return state


def preset_state(state: ClusterState, yaml_text: str) -> ClusterState:
    """预置集群状态：等价于 apply_manifest 但语义上表示'已存在的基线'。

    供 check_fn 在应用玩家 YAML 前设置关卡前置状态 (如 Q2.3 需要预置
    web-deploy v1)。preset 的 Deployment 同样会记录 revision history。
    """
    return apply_manifest(state, yaml_text)


def rollback_deployment(
    state: ClusterState, name: str, to_revision: int | None = None
) -> None:
    """回滚 Deployment 到指定 revision。

    Args:
        state: 集群状态
        name: Deployment 名称
        to_revision: 回滚到的 revision 编号。None 表示回滚到上一版。

    Raises:
        K8sError: Deployment 不存在、没有 revision history、
                  指定 revision 不存在、或只有 1 个 revision 无法回滚。
    """
    if name not in state.revisions or not state.revisions[name]:
        raise K8sError(
            f"Deployment '{name}' 没有 rollout history，无法回滚"
        )

    rev_list = state.revisions[name]

    if to_revision is None:
        # 回滚到上一版
        if len(rev_list) < 2:
            raise K8sError(
                f"Deployment '{name}' 只有 1 个版本，没有可回滚的上一版本"
            )
        target = rev_list[-2]
    else:
        # 回滚到指定 revision
        target = next(
            (r for r in rev_list if r["revision"] == to_revision), None
        )
        if target is None:
            raise K8sError(
                f"Deployment '{name}' 没有版本 {to_revision}"
            )

    # 深拷贝目标 revision 的 doc, 避免修改历史记录
    restored_doc = copy.deepcopy(target["doc"])

    # 记录 rollback 为新 revision (与真实 K8s 行为一致)
    _record_revision(state, name, restored_doc)

    # 更新 deployment 状态 + 重新实例化 Pod
    state.deployments[name] = restored_doc
    _instantiate_pods(state, name, restored_doc)


# ---------------------------------------------------------------------------
# 内部 apply 函数
# ---------------------------------------------------------------------------

def _validate_pod(doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError(
            "Pod 缺少 metadata.name（metadata 必须是非空映射）"
        )
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("Pod 缺少 spec（必须是映射）")
    containers = spec.get("containers")
    # 类型守卫：containers 必须是非空 list。仅用 `not spec.get("containers")`
    # falsy-only 判断会被 truthy 非 list（int 5 / dict {} / str "foo"）绕过，
    # 随后 enumerate(spec["containers"]) 抛 TypeError → /api/check HTTP 500。
    if not isinstance(containers, list) or not containers:
        raise K8sError(
            "Pod 缺少 spec.containers（必须是非空列表）"
        )
    for i, c in enumerate(containers):
        if not isinstance(c, dict):
            # 类型守卫：containers 元素必须是 dict。若只做 "name" in c 子串判断，
            # 字符串如 "name-image" 会被误判为合法容器，绕过校验后在下层
            # 调用 c.get(...) 时抛 AttributeError → /api/check HTTP 500。
            raise K8sError(f"Pod spec.containers[{i}] 必须是映射（dict），实际为 {type(c).__name__}")
        if "name" not in c:
            raise K8sError(f"Pod spec.containers[{i}] 缺少 name")
        if "image" not in c:
            raise K8sError(f"Pod spec.containers[{i}] 缺少 image")


def _apply_pod(state: ClusterState, doc: dict) -> None:
    _validate_pod(doc)
    name = doc["metadata"]["name"]
    state.pods[name] = doc


def _validate_deployment(doc: dict) -> None:
    """Deployment 前置校验：metadata / spec / replicas / template 全部类型守卫。

    防止 truthy 非 dict（str/int）绕过 falsy-only guard 后在 .get / setdefault /
    int() 处崩溃 → /api/check HTTP 500。与 _validate_pod 同类加固。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError(
            "Deployment 缺少 metadata.name（metadata 必须是非空映射）"
        )
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("Deployment 缺少 spec（必须是映射）")
    replicas = spec.get("replicas", 1)
    # 类型守卫：replicas 必须是 int。int("foo") 会抛 ValueError → HTTP 500。
    if isinstance(replicas, bool) or not isinstance(replicas, int):
        raise K8sError(
            "Deployment spec.replicas 必须是整数"
        )
    # F1: replicas 范围校验。_instantiate_pods 盲目 for i in range(replicas),
    # replicas=1000000 → 创建 100 万 Pod dict → worker 挂死 (>30s)。
    # 教学场景 100 足够; 真实 K8s 上限 ~1000。
    if replicas < 0 or replicas > 100:
        raise K8sError(
            f"Deployment spec.replicas 超出合理范围 (0-100), 实际 {replicas}"
        )
    template = spec.get("template")
    # 类型守卫：template 必须是非空 dict。仅用 `if not template` falsy-only 判断
    # 会被 truthy 非 dict（str "foo" / int 5）绕过，随后 template.setdefault(...)
    # 抛 AttributeError → /api/check HTTP 500。
    if not isinstance(template, dict) or not template:
        raise K8sError(
            "Deployment 缺少 spec.template（必须是非空映射）"
        )
    # W2: containers 元素校验 (与 _validate_pod 一致)。
    # _validate_deployment 此前不校验 template.spec.containers, containers 塞
    # 字符串元素 → 放行, check_fn 只查 containers[0] 不崩, 但 2nd 容器是脏数据。
    tmpl_spec = template.get("spec")
    if not isinstance(tmpl_spec, dict):
        raise K8sError(
            "Deployment 缺少 spec.template.spec（必须是映射）"
        )
    containers = tmpl_spec.get("containers")
    if not isinstance(containers, list) or not containers:
        raise K8sError(
            "Deployment 缺少 spec.template.spec.containers（必须是非空列表）"
        )
    for i, c in enumerate(containers):
        if not isinstance(c, dict):
            raise K8sError(
                f"Deployment template.spec.containers[{i}] 必须是映射（dict），实际为 {type(c).__name__}"
            )


def _apply_deployment(state: ClusterState, doc: dict) -> None:
    _validate_deployment(doc)
    name = doc["metadata"]["name"]

    # 检测 rollback annotation: k8s-quest/rollback: "true"
    # 玩家提交带此 annotation 的 YAML → 触发回滚到上一 revision
    annotations = doc.get("metadata", {}).get("annotations", {})
    if (
        isinstance(annotations, dict)
        and annotations.get("k8s-quest/rollback") == "true"
    ):
        rollback_deployment(state, name)
        return

    # 记录 revision history (每次 apply 都记录, 含首次)
    _record_revision(state, name, doc)

    # 存储 deployment + 实例化 Pod
    state.deployments[name] = doc
    _instantiate_pods(state, name, doc)


def _validate_service(doc: dict) -> None:
    """Service 前置校验：metadata / spec / type / ports / selector 类型守卫。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError(
            "Service 缺少 metadata.name（metadata 必须是非空映射）"
        )
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("Service 缺少 spec（必须是映射）")

    # type 校验（可选，默认 ClusterIP）
    svc_type = spec.get("type", "ClusterIP")
    if not isinstance(svc_type, str):
        raise K8sError("Service spec.type 必须是字符串")
    valid_types = {"ClusterIP", "NodePort", "LoadBalancer", "ExternalName"}
    if svc_type not in valid_types:
        raise K8sError(
            f"Service spec.type 不支持 '{svc_type}'，可选值：{', '.join(sorted(valid_types))}"
        )

    # ports 校验（必须是非空 list）
    ports = spec.get("ports")
    if not isinstance(ports, list) or not ports:
        raise K8sError(
            "Service 缺少 spec.ports（必须是非空列表）"
        )
    for i, p in enumerate(ports):
        if not isinstance(p, dict):
            raise K8sError(
                f"Service spec.ports[{i}] 必须是映射（dict），实际为 {type(p).__name__}"
            )
        if "port" not in p:
            raise K8sError(f"Service spec.ports[{i}] 缺少 port")
        if not isinstance(p["port"], int):
            raise K8sError(f"Service spec.ports[{i}].port 必须是整数")

    # clusterIP 校验（Headless 时必须为 None 字符串）
    cluster_ip = spec.get("clusterIP")
    if cluster_ip is not None:
        if not isinstance(cluster_ip, str):
            raise K8sError("Service spec.clusterIP 必须是字符串")

    # selector 校验（可选，但 Headless+selector 是常见用法）
    selector = spec.get("selector")
    if selector is not None and not isinstance(selector, dict):
        raise K8sError("Service spec.selector 必须是映射（dict）")


def _apply_service(state: ClusterState, doc: dict) -> None:
    _validate_service(doc)
    name = doc["metadata"]["name"]
    state.services[name] = doc


def resolve_service_endpoints(state: ClusterState, svc_name: str) -> list[str]:
    """返回 Service 匹配到的 Pod 名称列表（按 selector 匹配 labels）。

    Headless Service (clusterIP: None) 返回所有匹配 Pod 的名称。
    ClusterIP Service 返回 [svc_name]（代表通过 ClusterIP 访问）。
    """
    if svc_name not in state.services:
        return []

    svc = state.services[svc_name]
    spec = svc.get("spec", {})
    if not isinstance(spec, dict):
        return []

    selector = spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return []

    matched = []
    for pod_name, pod in state.pods.items():
        pod_labels = pod.get("metadata", {}).get("labels", {})
        if not isinstance(pod_labels, dict):
            continue
        # 所有 selector key=value 都匹配
        if all(pod_labels.get(k) == v for k, v in selector.items()):
            matched.append(pod_name)

    return sorted(matched)


def resolve_dns(state: ClusterState, svc_name: str, namespace: str = "default") -> dict | None:
    """模拟 CoreDNS 解析 Service。

    ClusterIP Service: 返回 {"type": "ClusterIP", "ip": "<cluster-ip>"}
    Headless Service: 返回 {"type": "Headless", "endpoints": ["pod-name1", ...]}
    NodePort Service: 返回 {"type": "NodePort", "ip": "<cluster-ip>", "nodePort": <port>}
    不存在: 返回 None
    """
    if svc_name not in state.services:
        return None

    svc = state.services[svc_name]
    spec = svc.get("spec", {})
    if not isinstance(spec, dict):
        return None

    svc_type = spec.get("type", "ClusterIP")
    cluster_ip = spec.get("clusterIP", "10.96.0.1")  # 模拟默认 ClusterIP

    # Headless Service
    if cluster_ip == "None":
        endpoints = resolve_service_endpoints(state, svc_name)
        return {"type": "Headless", "endpoints": endpoints}

    # NodePort
    if svc_type == "NodePort":
        ports = spec.get("ports", [])
        node_port = None
        if isinstance(ports, list) and ports and isinstance(ports[0], dict):
            node_port = ports[0].get("nodePort")
        return {"type": "NodePort", "ip": cluster_ip, "nodePort": node_port}

    # ClusterIP
    return {"type": "ClusterIP", "ip": cluster_ip}


def _apply_configmap(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("ConfigMap 缺少 metadata.name")
    name = metadata["name"]
    state.configmaps[name] = doc


def _apply_secret(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("Secret 缺少 metadata.name")
    name = metadata["name"]
    state.secrets[name] = doc


def _apply_pv(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("PersistentVolume 缺少 metadata.name")
    name = metadata["name"]
    state.persistentvolumes[name] = doc


def _apply_pvc(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("PersistentVolumeClaim 缺少 metadata.name")
    name = metadata["name"]
    state.persistentvolumeclaims[name] = doc


def _apply_node(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("Node 缺少 metadata.name")
    name = metadata["name"]
    state.nodes[name] = doc


# ---------------------------------------------------------------------------
# v0.5: Ch7-Ch12 新增资源类型
# ---------------------------------------------------------------------------

def _apply_job(state: ClusterState, doc: dict) -> None:
    """Job: 验证并存储，同时创建对应的 Pod（模拟任务执行）。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("Job 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("Job 缺少 spec")
    template = spec.get("template")
    if not isinstance(template, dict) or not template:
        raise K8sError("Job 缺少 spec.template")
    tmpl_spec = template.get("spec")
    if not isinstance(tmpl_spec, dict):
        raise K8sError("Job 缺少 spec.template.spec")
    containers = tmpl_spec.get("containers")
    if not isinstance(containers, list) or not containers:
        raise K8sError("Job 缺少 spec.template.spec.containers")

    name = metadata["name"]
    state.jobs[name] = doc

    # 模拟: 为 Job 创建一个 Pod
    pod_name = f"{name}-pod"
    pod_doc = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod_name, "labels": {"job-name": name}},
        "spec": tmpl_spec,
    }
    state.pods[pod_name] = pod_doc


def _apply_cronjob(state: ClusterState, doc: dict) -> None:
    """CronJob: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("CronJob 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("CronJob 缺少 spec")
    schedule = spec.get("schedule")
    if not isinstance(schedule, str) or not schedule:
        raise K8sError("CronJob 缺少 spec.schedule")
    job_template = spec.get("jobTemplate")
    if not isinstance(job_template, dict) or not job_template:
        raise K8sError("CronJob 缺少 spec.jobTemplate")

    name = metadata["name"]
    state.cronjobs[name] = doc


def _apply_statefulset(state: ClusterState, doc: dict) -> None:
    """StatefulSet: 验证并存储，同时创建有序 Pod（statefulset-0, statefulset-1, ...）。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("StatefulSet 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("StatefulSet 缺少 spec")
    replicas = spec.get("replicas", 1)
    if isinstance(replicas, bool) or not isinstance(replicas, int):
        raise K8sError("StatefulSet spec.replicas 必须是整数")
    if replicas < 0 or replicas > 100:
        raise K8sError(f"StatefulSet spec.replicas 超出合理范围 (0-100), 实际 {replicas}")
    template = spec.get("template")
    if not isinstance(template, dict) or not template:
        raise K8sError("StatefulSet 缺少 spec.template")
    # StatefulSet 需要 serviceName
    service_name = spec.get("serviceName")
    if not isinstance(service_name, str) or not service_name:
        raise K8sError("StatefulSet 缺少 spec.serviceName（Headless Service 名称）")

    name = metadata["name"]
    state.statefulsets[name] = doc

    # 清理旧 Pod（该 StatefulSet 创建的）
    old_pods = [pn for pn, p in state.pods.items()
                if isinstance(p.get("metadata", {}).get("labels", {}), dict)
                and p.get("metadata", {}).get("labels", {}).get("controller") == name]
    for pn in old_pods:
        del state.pods[pn]

    # 模拟: 创建有序 Pod (sts-name-0, sts-name-1, ...)
    tmpl_spec = template.get("spec", {"containers": []})
    for i in range(replicas):
        pod_name = f"{name}-{i}"
        pod_labels = dict(template.get("metadata", {}).get("labels", {}))
        pod_labels["controller"] = name
        pod_doc = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": pod_name, "labels": pod_labels},
            "spec": tmpl_spec,
        }
        state.pods[pod_name] = pod_doc


def _apply_role(state: ClusterState, doc: dict) -> None:
    """Role: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("Role 缺少 metadata.name")
    rules = doc.get("spec", {}).get("rules") or doc.get("rules")
    if not isinstance(rules, list):
        raise K8sError("Role 缺少 rules（必须是列表）")
    name = metadata["name"]
    state.roles[name] = doc


def _apply_rolebinding(state: ClusterState, doc: dict) -> None:
    """RoleBinding: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("RoleBinding 缺少 metadata.name")
    role_ref = doc.get("roleRef")
    if not isinstance(role_ref, dict):
        raise K8sError("RoleBinding 缺少 roleRef")
    name = metadata["name"]
    state.rolebindings[name] = doc


def _apply_clusterrole(state: ClusterState, doc: dict) -> None:
    """ClusterRole: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("ClusterRole 缺少 metadata.name")
    rules = doc.get("rules")
    if not isinstance(rules, list):
        raise K8sError("ClusterRole 缺少 rules（必须是列表）")
    name = metadata["name"]
    state.clusterroles[name] = doc


def _apply_clusterrolebinding(state: ClusterState, doc: dict) -> None:
    """ClusterRoleBinding: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("ClusterRoleBinding 缺少 metadata.name")
    role_ref = doc.get("roleRef")
    if not isinstance(role_ref, dict):
        raise K8sError("ClusterRoleBinding 缺少 roleRef")
    name = metadata["name"]
    state.clusterrolebindings[name] = doc


def _apply_hpa(state: ClusterState, doc: dict) -> None:
    """HorizontalPodAutoscaler: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("HorizontalPodAutoscaler 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("HorizontalPodAutoscaler 缺少 spec")
    target = spec.get("scaleTargetRef")
    if not isinstance(target, dict):
        raise K8sError("HorizontalPodAutoscaler 缺少 spec.scaleTargetRef")
    max_replicas = spec.get("maxReplicas")
    if not isinstance(max_replicas, int) or max_replicas < 1:
        raise K8sError("HorizontalPodAutoscaler spec.maxReplicas 必须是正整数")
    name = metadata["name"]
    state.horizontalpodautoscalers[name] = doc


def _apply_ingress(state: ClusterState, doc: dict) -> None:
    """Ingress: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("Ingress 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("Ingress 缺少 spec")
    rules = spec.get("rules")
    if not isinstance(rules, list):
        raise K8sError("Ingress 缺少 spec.rules（必须是列表）")
    name = metadata["name"]
    state.ingresses[name] = doc


def _apply_networkpolicy(state: ClusterState, doc: dict) -> None:
    """NetworkPolicy: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("NetworkPolicy 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("NetworkPolicy 缺少 spec")
    name = metadata["name"]
    state.networkpolicies[name] = doc


# ---------------------------------------------------------------------------
# v0.6: Ch13-Ch28 新增资源类型
# ---------------------------------------------------------------------------

def _apply_daemonset(state: ClusterState, doc: dict) -> None:
    """DaemonSet: 验证并存储，为每个匹配的 Node 创建一个 Pod。

    如果 Pod 模板中包含 nodeSelector，则只在标签匹配的 Node 上创建 Pod。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("DaemonSet 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise K8sError("DaemonSet 缺少 spec")
    template = spec.get("template")
    if not isinstance(template, dict) or not template:
        raise K8sError("DaemonSet 缺少 spec.template")
    tmpl_spec = template.get("spec")
    if not isinstance(tmpl_spec, dict):
        raise K8sError("DaemonSet 缺少 spec.template.spec")
    containers = tmpl_spec.get("containers")
    if not isinstance(containers, list) or not containers:
        raise K8sError("DaemonSet 缺少 spec.template.spec.containers")

    name = metadata["name"]
    state.daemonsets[name] = doc

    # 清理旧 Pod（该 DaemonSet 创建的）
    old_pods = [pn for pn, p in state.pods.items()
                if isinstance(p.get("metadata", {}).get("labels", {}), dict)
                and p.get("metadata", {}).get("labels", {}).get("daemonset") == name]
    for pn in old_pods:
        del state.pods[pn]

    # 获取 nodeSelector（如果有），用于过滤目标节点
    node_selector = tmpl_spec.get("nodeSelector", {})
    if not isinstance(node_selector, dict):
        node_selector = {}

    # 为每个匹配的 Node 创建一个 Pod
    tmpl_spec_ref = template.get("spec", {"containers": []})
    for node_name, node_doc in state.nodes.items():
        # 检查 Node 是否匹配 nodeSelector
        node_labels = node_doc.get("metadata", {}).get("labels", {})
        if not isinstance(node_labels, dict):
            node_labels = {}
        if not all(node_labels.get(k) == v for k, v in node_selector.items()):
            continue
        pod_name = f"{name}-{node_name}"
        pod_labels = dict(template.get("metadata", {}).get("labels", {}))
        pod_labels["daemonset"] = name
        pod_doc = {
            "apiVersion": "v1", "kind": "Pod",
            "metadata": {"name": pod_name, "labels": pod_labels},
            "spec": tmpl_spec_ref,
        }
        state.pods[pod_name] = pod_doc


def _apply_namespace(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("Namespace 缺少 metadata.name")
    state.namespaces[metadata["name"]] = doc


def _apply_resourcequota(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("ResourceQuota 缺少 metadata.name")
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        raise K8sError("ResourceQuota 缺少 spec")
    hard = spec.get("hard")
    if not isinstance(hard, dict) or not hard:
        raise K8sError("ResourceQuota 缺少 spec.hard")
    state.resourcequotas[metadata["name"]] = doc


def _apply_limitrange(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("LimitRange 缺少 metadata.name")
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        raise K8sError("LimitRange 缺少 spec")
    limits = spec.get("limits")
    if not isinstance(limits, list) or not limits:
        raise K8sError("LimitRange 缺少 spec.limits")
    state.limitranges[metadata["name"]] = doc


def _apply_pdb(state: ClusterState, doc: dict) -> None:
    """PodDisruptionBudget: 验证并存储。"""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("PodDisruptionBudget 缺少 metadata.name")
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        raise K8sError("PodDisruptionBudget 缺少 spec")
    if "minAvailable" not in spec and "maxUnavailable" not in spec:
        raise K8sError("PodDisruptionBudget 需要 spec.minAvailable 或 spec.maxUnavailable")
    if "minAvailable" in spec and "maxUnavailable" in spec:
        raise K8sError("PDB 不能同时设置 minAvailable 和 maxUnavailable")
    state.poddisruptionbudgets[metadata["name"]] = doc


def _apply_priorityclass(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("PriorityClass 缺少 metadata.name")
    value = doc.get("value")
    if isinstance(value, bool) or not isinstance(value, int):
        raise K8sError("PriorityClass 缺少 value（必须是整数）")
    state.priorityclasses[metadata["name"]] = doc


def _apply_crd(state: ClusterState, doc: dict) -> None:
    """CustomResourceDefinition: 验证并存储。

    校验 metadata.name / spec.group / spec.names / spec.versions。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("CustomResourceDefinition 缺少 metadata.name")
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        raise K8sError("CustomResourceDefinition 缺少 spec")
    names = spec.get("names")
    if not isinstance(names, dict):
        raise K8sError("CustomResourceDefinition 缺少 spec.names")
    group = spec.get("group")
    if not isinstance(group, str) or not group:
        raise K8sError("CustomResourceDefinition 缺少 spec.group")
    versions = spec.get("versions")
    if not isinstance(versions, list) or not versions:
        raise K8sError("CustomResourceDefinition 缺少 spec.versions（必须是非空列表）")
    for i, v in enumerate(versions):
        if not isinstance(v, dict):
            raise K8sError(f"spec.versions[{i}] 必须是映射（dict）")
        if "name" not in v:
            raise K8sError(f"spec.versions[{i}] 缺少 name")
    state.customresourcedefinitions[metadata["name"]] = doc


def _apply_serviceaccount(state: ClusterState, doc: dict) -> None:
    """ServiceAccount: 验证并存储。

    校验 metadata.name；metadata.namespace 可选（默认 default）。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("ServiceAccount 缺少 metadata.name")
    namespace = metadata.get("namespace", "default")
    if not isinstance(namespace, str):
        raise K8sError("ServiceAccount metadata.namespace 必须是字符串")
    state.serviceaccounts[metadata["name"]] = doc


def _apply_customresource(state: ClusterState, doc: dict) -> None:
    """自定义资源实例（CR）：根据已注册的 CRD 验证并存储。

    当 apply_manifest 遇到未知 kind 时调用此函数。遍历所有已注册 CRD，
    按 spec.names.kind + spec.group 匹配 apiVersion（group/version）。
    匹配成功则存储到 state.customresources；失败则抛出 K8sError。
    """
    kind = doc.get("kind")
    api_version = doc.get("apiVersion", "")

    # 解析 apiVersion: "<group>/<version>" 或 "<version>"（核心资源无 group）
    if "/" in api_version:
        group = api_version.split("/")[0]
    else:
        group = ""

    # 遍历已注册 CRD 查找匹配
    for crd_name, crd in state.customresourcedefinitions.items():
        crd_spec = crd.get("spec", {})
        if not isinstance(crd_spec, dict):
            continue
        crd_names = crd_spec.get("names", {})
        if not isinstance(crd_names, dict):
            continue
        crd_kind = crd_names.get("kind")
        crd_group = crd_spec.get("group", "")
        if crd_kind == kind and crd_group == group:
            # 匹配到 CRD，验证 CR metadata
            metadata = doc.get("metadata")
            if not isinstance(metadata, dict) or "name" not in metadata:
                raise K8sError(f"{kind} 缺少 metadata.name")
            namespace = metadata.get("namespace", "default")
            cr_key = f"{namespace}/{metadata['name']}"
            state.customresources[cr_key] = doc
            return

    raise K8sError(
        f"不支持的资源类型：{kind}（apiVersion: {api_version}）。"
        f"如需创建自定义资源，请先注册对应的 CRD。"
    )


# ---------------------------------------------------------------------------
# v0.8: Ch19-Ch20 新增资源类型
# ---------------------------------------------------------------------------

def _apply_storageclass(state: ClusterState, doc: dict) -> None:
    """StorageClass: 验证并存储。

    注意: StorageClass 的 provisioner / reclaimPolicy / volumeBindingMode /
    parameters / allowVolumeExpansion 都是顶层字段，不在 spec 下。
    模拟器统一将其归入 spec dict 以方便 check_fn 访问。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("StorageClass 缺少 metadata.name")
    provisioner = doc.get("provisioner")
    if not isinstance(provisioner, str) or not provisioner:
        raise K8sError("StorageClass 缺少 provisioner")
    # 归一化：将顶层字段放入 spec，方便 check_fn 统一访问
    spec = {
        "provisioner": provisioner,
        "reclaimPolicy": doc.get("reclaimPolicy", "Delete"),
        "volumeBindingMode": doc.get("volumeBindingMode", "Immediate"),
        "parameters": doc.get("parameters", {}),
        "allowVolumeExpansion": doc.get("allowVolumeExpansion"),
    }
    doc_norm = dict(doc)
    doc_norm["spec"] = spec
    state.storageclasses[metadata["name"]] = doc_norm


def _apply_volumesnapshot(state: ClusterState, doc: dict) -> None:
    """VolumeSnapshot: 验证并存储。

    校验 metadata.name / spec.source（引用 PVC 或 VolumeSnapshotContent）。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("VolumeSnapshot 缺少 metadata.name")
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        raise K8sError("VolumeSnapshot 缺少 spec")
    source = spec.get("source")
    if not isinstance(source, dict) or not source:
        raise K8sError("VolumeSnapshot 缺少 spec.source")
    state.volumesnapshots[metadata["name"]] = doc


def _apply_volumesnapshotcontent(state: ClusterState, doc: dict) -> None:
    """VolumeSnapshotContent: 验证并存储。

    校验 metadata.name / spec.volumeSnapshotRef / spec.source。
    """
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError("VolumeSnapshotContent 缺少 metadata.name")
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        raise K8sError("VolumeSnapshotContent 缺少 spec")
    state.volumesnapshotcontents[metadata["name"]] = doc


# ---------------------------------------------------------------------------
# RBAC 权限检查 & NetworkPolicy 流量模拟（P1 修复：消除假阳性）
# ---------------------------------------------------------------------------

def _get_role_rules(role_doc: dict) -> list:
    """从 Role/ClusterRole doc 中提取 rules 列表。

    Role 的 rules 可能在顶层或 spec 下（_apply_role 两种都接受），
    ClusterRole 的 rules 在顶层。
    """
    rules = role_doc.get("rules")
    if not isinstance(rules, list):
        rules = role_doc.get("spec", {}).get("rules", [])
    if not isinstance(rules, list):
        return []
    return rules


def _match_labels(pod_labels: dict, selector: dict) -> bool:
    """检查 pod 的 labels 是否匹配 selector（matchLabels 语义）。

    selector 为空 dict {} 表示匹配所有 Pod（K8s 中 podSelector: {} 的含义）。
    """
    if not selector:
        return True
    match_labels = selector.get("matchLabels", {})
    if not isinstance(match_labels, dict):
        return True  # 无 matchLabels，视为匹配所有
    for k, v in match_labels.items():
        if pod_labels.get(k) != v:
            return False
    return True


def simulate_rbac_check(
    state: ClusterState, sa_name: str, verb: str, resource: str
) -> bool:
    """模拟 kubectl auth can-i 逻辑。

    遍历所有 RoleBinding / ClusterRoleBinding，找到绑定到指定 SA 的绑定，
    然后检查对应 Role / ClusterRole 的 rules 是否授予请求的 verb + resource。

    Args:
        state: 集群状态
        sa_name: ServiceAccount 名称
        verb: 请求的操作（get, list, create, delete, ...）
        resource: 请求的资源类型（pods, services, ...）

    Returns:
        True 如果 SA 被授予了该权限，False 否则
    """
    # 收集所有绑定到该 SA 的 Role/ClusterRole doc
    roles_to_check: list[dict] = []

    # --- RoleBinding（命名空间级绑定） ---
    for rb in state.rolebindings.values():
        subjects = rb.get("subjects")
        if not isinstance(subjects, list):
            continue
        sa_bound = any(
            isinstance(s, dict)
            and s.get("kind") == "ServiceAccount"
            and s.get("name") == sa_name
            for s in subjects
        )
        if not sa_bound:
            continue
        role_ref = rb.get("roleRef")
        if not isinstance(role_ref, dict):
            continue
        ref_kind = role_ref.get("kind", "")
        ref_name = role_ref.get("name", "")
        if ref_kind == "Role" and ref_name in state.roles:
            roles_to_check.append(state.roles[ref_name])
        elif ref_kind == "ClusterRole" and ref_name in state.clusterroles:
            roles_to_check.append(state.clusterroles[ref_name])

    # --- ClusterRoleBinding（集群级绑定） ---
    for crb in state.clusterrolebindings.values():
        subjects = crb.get("subjects")
        if not isinstance(subjects, list):
            continue
        sa_bound = any(
            isinstance(s, dict)
            and s.get("kind") == "ServiceAccount"
            and s.get("name") == sa_name
            for s in subjects
        )
        if not sa_bound:
            continue
        role_ref = crb.get("roleRef")
        if not isinstance(role_ref, dict):
            continue
        ref_kind = role_ref.get("kind", "")
        ref_name = role_ref.get("name", "")
        # ClusterRoleBinding 只能引用 ClusterRole
        if ref_kind == "ClusterRole" and ref_name in state.clusterroles:
            roles_to_check.append(state.clusterroles[ref_name])

    # --- 检查每个 Role/ClusterRole 的 rules ---
    for role_doc in roles_to_check:
        for rule in _get_role_rules(role_doc):
            if not isinstance(rule, dict):
                continue
            verbs = rule.get("verbs", [])
            resources = rule.get("resources", [])
            if not isinstance(verbs, list) or not isinstance(resources, list):
                continue
            # verb 匹配：精确匹配或通配符 '*'
            verb_ok = verb in verbs or "*" in verbs
            # resource 匹配：精确匹配或通配符 '*'
            resource_ok = resource in resources or "*" in resources
            if verb_ok and resource_ok:
                return True

    return False


def _from_matches_pod(
    src_labels: dict, src_namespace: str, from_element: dict
) -> bool:
    """检查 NetworkPolicy ingress.from 的单个元素是否匹配源 Pod。

    from 元素可包含:
    - podSelector: 按 Pod 标签选择（同命名空间）
    - namespaceSelector: 按命名空间标签选择
    - 两者同时存在时为 AND 逻辑
    - 空元素 {} 表示匹配所有来源
    """
    if not from_element:
        return True  # 空 from 元素 -> 匹配所有

    # podSelector 匹配
    pod_sel = from_element.get("podSelector")
    pod_match = True
    if isinstance(pod_sel, dict) and pod_sel:
        pod_match = _match_labels(src_labels, pod_sel)

    # namespaceSelector 匹配
    ns_sel = from_element.get("namespaceSelector")
    ns_match = True
    if isinstance(ns_sel, dict) and ns_sel:
        ns_labels = ns_sel.get("matchLabels", {})
        if isinstance(ns_labels, dict) and ns_labels:
            # K8s 1.21+ 自动添加 kubernetes.io/metadata.name 标签
            expected_ns = ns_labels.get("kubernetes.io/metadata.name")
            if expected_ns is not None:
                ns_match = (src_namespace == expected_ns)

    return pod_match and ns_match


def simulate_traffic(
    state: ClusterState, src_pod: str, dst_pod: str, port: int
) -> dict:
    """模拟 NetworkPolicy 流量检查。

    模拟 K8s NetworkPolicy 的 ingress 流量判定逻辑:
    a. 如果没有任何 NetworkPolicy 选择 dst_pod -> 默认允许（K8s 默认行为）
    b. 如果有 NetworkPolicy 选择 dst_pod（ingress 策略）:
       - 检查是否有策略的 from 字段允许 src_pod
       - 检查是否有策略的 ports 字段允许请求的 port
       - 多个策略叠加：任一策略允许即放行
    c. 返回是否允许和匹配的策略名列表

    Args:
        state: 集群状态
        src_pod: 源 Pod 名称
        dst_pod: 目标 Pod 名称
        port: 请求的端口号

    Returns:
        {"allowed": bool, "matched_policies": [str]}
    """
    # 获取 dst_pod / src_pod 的 labels 和 namespace
    dst_pod_doc = state.pods.get(dst_pod)
    if not isinstance(dst_pod_doc, dict):
        return {"allowed": False, "matched_policies": []}
    dst_meta = dst_pod_doc.get("metadata", {})
    if not isinstance(dst_meta, dict):
        dst_meta = {}
    dst_labels = dst_meta.get("labels", {})
    if not isinstance(dst_labels, dict):
        dst_labels = {}

    src_pod_doc = state.pods.get(src_pod)
    if not isinstance(src_pod_doc, dict):
        return {"allowed": False, "matched_policies": []}
    src_meta = src_pod_doc.get("metadata", {})
    if not isinstance(src_meta, dict):
        src_meta = {}
    src_labels = src_meta.get("labels", {})
    if not isinstance(src_labels, dict):
        src_labels = {}
    src_namespace = src_meta.get("namespace", "default")

    # 找到所有选择 dst_pod 且管控 Ingress 的 NetworkPolicy
    matched_policies: list[str] = []
    for np_name, np in state.networkpolicies.items():
        spec = np.get("spec")
        if not isinstance(spec, dict):
            continue
        policy_types = spec.get("policyTypes", [])
        if not isinstance(policy_types, list) or "Ingress" not in policy_types:
            continue
        pod_selector = spec.get("podSelector", {})
        if not isinstance(pod_selector, dict):
            pod_selector = {}
        # 检查 dst_pod 是否被此 policy 选择
        if not _match_labels(dst_labels, pod_selector):
            continue
        matched_policies.append(np_name)

    # a. 没有 NetworkPolicy 选择 dst_pod -> 默认允许
    if not matched_policies:
        return {"allowed": True, "matched_policies": []}

    # b. 有策略选择 dst_pod，检查是否有策略允许此流量
    for np_name in matched_policies:
        np = state.networkpolicies[np_name]
        spec = np.get("spec", {})
        ingress_rules = spec.get("ingress")
        # 如果没有 ingress 规则，此策略拒绝所有入站
        if not isinstance(ingress_rules, list) or not ingress_rules:
            continue
        for rule in ingress_rules:
            if not isinstance(rule, dict):
                continue

            # --- 检查 from 是否匹配 src_pod ---
            from_list = rule.get("from")
            source_ok = False
            # from 缺失或空列表 -> 允许所有来源（K8s 语义）
            if not isinstance(from_list, list) or not from_list:
                source_ok = True
            else:
                for src_elem in from_list:
                    if not isinstance(src_elem, dict):
                        continue
                    if _from_matches_pod(src_labels, src_namespace, src_elem):
                        source_ok = True
                        break
            if not source_ok:
                continue

            # --- 检查 ports 是否匹配请求的端口 ---
            ports_list = rule.get("ports")
            port_ok = False
            # ports 缺失或空列表 -> 允许所有端口（K8s 语义）
            if not isinstance(ports_list, list) or not ports_list:
                port_ok = True
            else:
                for p in ports_list:
                    if not isinstance(p, dict):
                        continue
                    if p.get("port") == port:
                        port_ok = True
                        break

            # from 和 ports 都匹配 -> 此策略允许流量
            if source_ok and port_ok:
                return {"allowed": True, "matched_policies": matched_policies}

    # c. 有策略选择 dst_pod 但没有策略允许此流量 -> 拒绝
    return {"allowed": False, "matched_policies": matched_policies}
