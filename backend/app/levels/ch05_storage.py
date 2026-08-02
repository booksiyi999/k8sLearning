"""Chapter 5: Storage 存储（4 关）

Q5.1 创建 PersistentVolume (PV)
Q5.2 创建 PersistentVolumeClaim (PVC)
Q5.3 在 Pod 中使用 PVC
Q5.4 emptyDir 临时存储
"""
from app.validator import Level, CheckResult
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


def _check_01_create_pv(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.persistentvolumes:
        return CheckResult(ok=False, error="没有创建任何 PersistentVolume", hints=["创建 kind: PersistentVolume"])

    if "data-pv" not in state.persistentvolumes:
        return CheckResult(ok=False, error=f"没找到 'data-pv'，当前：{list(state.persistentvolumes.keys())}", hints=[])

    pv = state.persistentvolumes["data-pv"]
    spec = pv.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PV 缺少 spec", hints=[])

    capacity = spec.get("capacity")
    if not isinstance(capacity, dict):
        return CheckResult(ok=False, error="capacity 应为映射（dict）", hints=[])
    if capacity.get("storage") != "5Gi":
        return CheckResult(ok=False, error=f"capacity.storage 应为 5Gi，实际 {capacity.get('storage')}", hints=[])

    if spec.get("accessModes") != ["ReadWriteOnce"]:
        return CheckResult(ok=False, error=f"accessModes 应为 [ReadWriteOnce]，实际 {spec.get('accessModes')}", hints=[])

    host_path = spec.get("hostPath")
    if not isinstance(host_path, dict):
        return CheckResult(ok=False, error="hostPath 应为映射（dict）", hints=[])
    if host_path.get("path") != "/mnt/data":
        return CheckResult(ok=False, error=f"hostPath.path 应为 /mnt/data，实际 {host_path.get('path')}", hints=[])

    return CheckResult(ok=True, state=state, hints=["PV 创建成功！PV 是集群级存储资源"])


def _check_02_create_pvc(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.persistentvolumeclaims:
        return CheckResult(ok=False, error="没有创建任何 PVC", hints=["创建 kind: PersistentVolumeClaim"])

    if "data-pvc" not in state.persistentvolumeclaims:
        return CheckResult(ok=False, error=f"没找到 'data-pvc'，当前：{list(state.persistentvolumeclaims.keys())}", hints=[])

    pvc = state.persistentvolumeclaims["data-pvc"]
    spec = pvc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PVC 缺少 spec", hints=[])

    if spec.get("accessModes") != ["ReadWriteOnce"]:
        return CheckResult(ok=False, error=f"accessModes 应为 [ReadWriteOnce]，实际 {spec.get('accessModes')}", hints=[])

    resources = spec.get("resources")
    if not isinstance(resources, dict):
        return CheckResult(ok=False, error="resources 应为映射（dict）", hints=[])
    requests = resources.get("requests")
    if not isinstance(requests, dict):
        return CheckResult(ok=False, error="resources.requests 应为映射（dict）", hints=[])
    if requests.get("storage") != "5Gi":
        return CheckResult(ok=False, error=f"resources.requests.storage 应为 5Gi", hints=[])

    return CheckResult(ok=True, state=state, hints=["PVC 创建成功！PVC 是对 PV 的存储申请"])


def _check_03_pod_with_pvc(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = preset_state(state, """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建一个 Pod，通过 volumes 引用 PVC"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    volumes = spec.get("volumes", [])
    found_pvc = False
    if isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict):
                pvc_ref = v.get("persistentVolumeClaim", {})
                if isinstance(pvc_ref, dict) and pvc_ref.get("claimName") == "data-pvc":
                    found_pvc = True
                    break

    if not found_pvc:
        return CheckResult(ok=False, error="Pod volumes 没有引用 PVC 'data-pvc'", hints=["在 volumes 中添加 persistentVolumeClaim.claimName: data-pvc"])

    containers = spec.get("containers", [])
    if isinstance(containers, list) and containers and isinstance(containers[0], dict):
        mounts = containers[0].get("volumeMounts", [])
        if not isinstance(mounts, list) or not mounts:
            return CheckResult(ok=False, error="容器缺少 volumeMounts", hints=["在 volumeMounts 中挂载 PVC volume"])

    return CheckResult(ok=True, state=state, hints=["Pod 使用 PVC 成功！数据持久化到 PV"])


def _check_04_emptydir(user_yaml: str) -> CheckResult:
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(ok=False, error="没有创建 Pod", hints=["创建一个多容器 Pod，使用 emptyDir 共享数据"])

    pod = None
    for p in state.pods.values():
        pod = p
        break

    spec = pod.get("spec", {})
    volumes = spec.get("volumes", [])
    found_emptydir = False
    if isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict):
                ed = v.get("emptyDir", {})
                if isinstance(ed, dict):
                    found_emptydir = True
                    break

    if not found_emptydir:
        return CheckResult(ok=False, error="Pod volumes 中没有 emptyDir", hints=["在 volumes 中添加 emptyDir: {}"])

    containers = spec.get("containers", [])
    if not isinstance(containers, list) or len(containers) < 2:
        return CheckResult(ok=False, error="需要至少 2 个容器来演示 emptyDir 共享", hints=["创建一个含 writer 和 reader 两个容器的 Pod"])

    return CheckResult(ok=True, state=state, hints=["emptyDir 创建成功！同一 Pod 内容器共享临时存储"])


CHAPTER_5_LEVELS: list[Level] = [
    Level(id="Q5.1", chapter="ch05", title="创建 PersistentVolume",
          description="创建一个名为 data-pv 的 PV，5Gi 容量，ReadWriteOnce，hostPath /mnt/data",
          starter_yaml="apiVersion: v1\nkind: PersistentVolume\nmetadata:\n  name: data-pv\nspec:\n  # capacity, accessModes, hostPath",
          check_fn=_check_01_create_pv),
    Level(id="Q5.2", chapter="ch05", title="创建 PersistentVolumeClaim",
          description="集群已有 data-pv。创建一个名为 data-pvc 的 PVC，申请 5Gi，ReadWriteOnce",
          starter_yaml="apiVersion: v1\nkind: PersistentVolumeClaim\nmetadata:\n  name: data-pvc\nspec:\n  # accessModes, resources",
          check_fn=_check_02_create_pvc),
    Level(id="Q5.3", chapter="ch05", title="Pod 使用 PVC",
          description="集群已有 data-pv 和 data-pvc。创建 Pod，通过 volume 挂载 PVC",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: app-pod\nspec:\n  containers:\n    - name: app\n      image: nginx\n      # volumeMounts\n  # volumes with PVC",
          check_fn=_check_03_pod_with_pvc),
    Level(id="Q5.4", chapter="ch05", title="emptyDir 临时存储",
          description="创建一个含 2 个容器的 Pod，使用 emptyDir 在容器间共享临时数据",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: shared-pod\nspec:\n  containers:\n    - name: writer\n      image: busybox\n    - name: reader\n      image: busybox\n  # volumes with emptyDir",
          check_fn=_check_04_emptydir),
]
