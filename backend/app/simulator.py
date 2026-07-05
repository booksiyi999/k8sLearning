from dataclasses import dataclass, field
from typing import Any
import yaml


class K8sError(Exception):
    """模拟器抛出的所有错误。"""


@dataclass
class ClusterState:
    """虚拟集群状态：存放所有 K8s 资源。"""
    pods: dict[str, dict] = field(default_factory=dict)
    deployments: dict[str, dict] = field(default_factory=dict)
    services: dict[str, dict] = field(default_factory=dict)


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


def apply_manifest(state: ClusterState, yaml_text: str) -> ClusterState:
    """把 YAML 应用到虚拟集群，返回新状态（in-place 修改）。

    支持的资源：Pod、Deployment、Service。
    """
    try:
        doc = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise K8sError(f"YAML 解析失败：{e}") from e

    if not isinstance(doc, dict):
        raise K8sError("YAML 顶层必须是映射（dict）")

    # 循环引用检测: yaml.safe_load 对自引用 anchor (&a / *a) 不报错,
    # 直接构造出循环引用的 Python dict。该结构若存入 state 并被 FastAPI
    # 序列化, json.dumps 抛 ValueError (中间件层, try/except 之外) → HTTP 500。
    # 在此从根源阻断, 转为 K8sError → check_fn 的 except 捕获 → 200 ok=False。
    if _has_circular_ref(doc):
        raise K8sError("YAML 含循环引用（自引用 anchor），拒绝应用")

    kind = doc.get("kind")
    if kind == "Pod":
        _apply_pod(state, doc)
    elif kind == "Deployment":
        _apply_deployment(state, doc)
    elif kind == "Service":
        _apply_service(state, doc)
    else:
        raise K8sError(f"不支持的资源类型：{kind}（MVP 仅支持 Pod / Deployment / Service）")

    return state


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
    template = spec.get("template")
    # 类型守卫：template 必须是非空 dict。仅用 `if not template` falsy-only 判断
    # 会被 truthy 非 dict（str "foo" / int 5）绕过，随后 template.setdefault(...)
    # 抛 AttributeError → /api/check HTTP 500。
    if not isinstance(template, dict) or not template:
        raise K8sError(
            "Deployment 缺少 spec.template（必须是非空映射）"
        )


def _apply_deployment(state: ClusterState, doc: dict) -> None:
    _validate_deployment(doc)
    name = doc["metadata"]["name"]
    spec = doc["spec"]
    replicas = spec.get("replicas", 1)
    template = spec["template"]

    state.deployments[name] = doc
    # 实例化 N 个虚拟 Pod
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


def _apply_service(state: ClusterState, doc: dict) -> None:
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise K8sError(
            "Service 缺少 metadata.name（metadata 必须是非空映射）"
        )
    name = metadata["name"]
    state.services[name] = doc
