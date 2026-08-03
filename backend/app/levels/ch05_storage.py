"""Chapter 5: Storage 存储（4 关）

Q5.1 创建 PersistentVolume (PV)
Q5.2 创建 PersistentVolumeClaim (PVC)
Q5.3 在 Pod 中使用 PVC
Q5.4 emptyDir 临时存储
"""
from app.validator import Level, CheckResult, Lesson
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
          check_fn=_check_01_create_pv,
          lesson=Lesson(
              concept="""\
## PersistentVolume (PV)

**PersistentVolume（PV）** 是 K8s 集群级别的存储资源，由管理员预先创建或通过 StorageClass 动态分配。它独立于 Pod 生命周期，Pod 删除后 PV 中的数据仍然存在。

### PV vs Pod Volume

普通 Volume（如 emptyDir）的生命周期与 Pod 绑定--Pod 删了数据就没了。PV 解耦了存储和计算：
- Pod 挂了 → 数据还在
- PV 可以被不同 Pod 反复挂载
- 支持网络存储（NFS、iSCSI、Ceph）和本地存储（hostPath）

### 核心属性

- **capacity**：存储容量（如 5Gi）
- **accessModes**：访问模式
  - `ReadWriteOnce`（RWO）：单节点读写
  - `ReadOnlyMany`（ROX）：多节点只读
  - `ReadWriteMany`（RWX）：多节点读写
- **hostPath**：挂载 Node 上的本地路径（仅测试用，生产环境不推荐）

### PV 生命周期

```
Available → Bound → Released → Available/Retained
```

1. **Available**：PV 已创建，等待 PVC 绑定
2. **Bound**：PVC 绑定了 PV
3. **Released**：PVC 删除，PV 保留数据但不可用
4. **Retained/Recycled**：根据 reclaimPolicy 决定保留或回收

### 静态 vs 动态供给

- **静态供给**：管理员手动创建 PV（本关学习的方式）
- **动态供给**：PVC 创建时自动通过 StorageClass 创建 PV（生产环境推荐）
""",
              key_fields=[
                  {"name": "spec.capacity.storage", "description": "PV 容量，如 5Gi", "required": True, "example": "5Gi"},
                  {"name": "spec.accessModes", "description": "访问模式列表，RWO/ROX/RWX", "required": True, "example": "[ReadWriteOnce]"},
                  {"name": "spec.hostPath.path", "description": "Node 上的本地路径（仅测试用）", "required": False, "example": "/mnt/data"},
                  {"name": "spec.persistentVolumeReclaimPolicy", "description": "回收策略: Retain/Recycle/Delete", "required": False, "example": "Retain"},
              ],
              diagram="""\
┌──────── PersistentVolume (data-pv) ─────────┐
│                                              │
│  spec:                                       │
│    capacity:                                 │
│      storage: 5Gi          ◄── 存储容量      │
│    accessModes:                              │
│    - ReadWriteOnce         ◄── 单节点读写    │
│    hostPath:                                 │
│      path: /mnt/data       ◄── Node 本地路径 │
│    persistentVolumeReclaimPolicy: Retain     │
│                                              │
│  状态: Available → Bound (被 PVC 绑定)       │
│  生命周期: 独立于 Pod，Pod 删除数据不丢失    │
└──────────────────────────────────────────────┘
       │
       │ 绑定
       ▼
  PersistentVolumeClaim (PVC)
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: PersistentVolume          # 资源类型: PV
metadata:                       # 元数据
  name: data-pv                 # PV 名称
spec:                           # 规格定义
  capacity:                     # 容量
    storage: 5Gi                # 5 GiB
  accessModes:                  # 访问模式
  - ReadWriteOnce               # 单节点读写（RWO）
  hostPath:                     # 本地路径（仅测试）
    path: /mnt/data             # Node 上的路径
  # persistentVolumeReclaimPolicy: Retain  # 回收策略
""",
              common_errors=[
                  "accessModes 写成单数（应为列表 [ReadWriteOnce]）",
                  "capacity.storage 大小与 PVC 不匹配（PVC 找不到匹配的 PV）",
                  "生产环境用 hostPath（应使用 NFS/Ceph/云盘等网络存储）",
                  "忘记写 accessModes（PV 必须声明访问模式）",
              ],
              tips=[
                  "PV 是集群级资源，不属于任何 namespace",
                  "生产环境推荐用 StorageClass 动态供给，而非手动创建 PV",
                  "用 kubectl get pv 查看 PV 状态（Available/Bound）",
              ],
          ),
    ),
    Level(id="Q5.2", chapter="ch05", title="创建 PersistentVolumeClaim",
          description="集群已有 data-pv。创建一个名为 data-pvc 的 PVC，申请 5Gi，ReadWriteOnce",
          starter_yaml="apiVersion: v1\nkind: PersistentVolumeClaim\nmetadata:\n  name: data-pvc\nspec:\n  # accessModes, resources",
          check_fn=_check_02_create_pvc,
          lesson=Lesson(
              concept="""\
## PersistentVolumeClaim (PVC)

**PersistentVolumeClaim（PVC）** 是用户对存储的申请--声明需要多大、什么访问模式的存储。K8s 控制器自动匹配满足条件的 PV 并绑定。

### PV 和 PVC 的关系

```
用户创建 PVC (需要 5Gi, RWO)
       ↓
K8s 控制器搜索匹配的 PV
       ↓
找到 data-pv (5Gi, RWO, Available)
       ↓
绑定: PVC ↔ PV (1:1 关系)
```

PVC 是 namespace 级资源，PV 是集群级资源。一个 PV 只能绑定一个 PVC，绑定后状态变为 Bound。

### 绑定规则

K8s 按以下条件匹配 PV：
1. **accessModes**：PV 的访问模式必须包含 PVC 请求的模式
2. **storage**：PV 的容量 >= PVC 请求的容量
3. **storageClassName**：如果指定了 StorageClass，PV 必须属于该类
4. **selector**：PVC 可以用 label selector 筛选 PV

如果找不到匹配的 PV，PVC 保持 Pending 状态。

### 为什么需要 PVC？

直接用 PV 的问题：用户需要知道具体存储细节（NFS 地址、磁盘路径）。PVC 抽象了存储细节：
- 用户只需声明"我要 5Gi 存储"
- 管理员负责创建 PV 或配置 StorageClass
- 实现存储的"申请-供给"解耦

### 动态供给

如果集群配置了 StorageClass，PVC 创建时找不到匹配 PV，K8s 会自动通过 StorageClass 创建 PV 并绑定--这就是动态供给，生产环境推荐方式。
""",
              key_fields=[
                  {"name": "spec.accessModes", "description": "请求的访问模式，必须与 PV 匹配", "required": True, "example": "[ReadWriteOnce]"},
                  {"name": "spec.resources.requests.storage", "description": "请求的存储容量", "required": True, "example": "5Gi"},
                  {"name": "spec.storageClassName", "description": "指定 StorageClass（省略则用默认）", "required": False, "example": "standard"},
                  {"name": "spec.selector", "description": "用 label selector 筛选 PV", "required": False, "example": "{matchLabels: {type: fast}}"},
              ],
              diagram="""\
  PVC 与 PV 的绑定过程

  ┌──── PVC (data-pvc) ──────────┐
  │  spec:                       │
  │    accessModes:              │
  │    - ReadWriteOnce           │
  │    resources:                │
  │      requests:               │
  │        storage: 5Gi          │
  │  状态: Pending               │
  └──────────┬───────────────────┘
             │ K8s 控制器搜索匹配的 PV
             ▼
  ┌──── PV (data-pv) ────────────┐
  │  capacity:                   │
  │    storage: 5Gi    ✓ 匹配    │
  │  accessModes:                │
  │  - ReadWriteOnce   ✓ 匹配    │
  │  状态: Available → Bound     │
  └──────────────────────────────┘

  绑定后: PVC.status.phase = Bound
         PV.status.phase = Bound
         PVC.spec.volumeName = data-pv
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: PersistentVolumeClaim     # 资源类型: PVC
metadata:                       # 元数据
  name: data-pvc                # PVC 名称
spec:                           # 规格定义
  accessModes:                  # 访问模式（与 PV 匹配）
  - ReadWriteOnce               # 单节点读写
  resources:                    # 资源请求
    requests:                   # 请求量
      storage: 5Gi              # 请求 5Gi 存储
  # storageClassName: standard  # 指定 StorageClass（可选）
""",
              common_errors=[
                  "resources.requests.storage 写成了 capacity（PVC 用 resources.requests，PV 用 capacity）",
                  "accessModes 与 PV 不匹配（PVC 的模式必须是 PV 支持的子集）",
                  "请求的 storage 大于 PV 容量（找不到匹配的 PV，PVC 一直 Pending）",
                  "PVC 是 namespace 级资源但 PV 是集群级（跨 namespace 无法共享 PVC）",
              ],
              tips=[
                  "PVC 是用户视角的存储申请，PV 是管理员视角的存储供给",
                  "用 kubectl get pvc 查看绑定状态（Pending=未绑定，Bound=已绑定）",
                  "生产环境推荐用 StorageClass 动态供给，无需手动创建 PV",
              ],
          ),
    ),
    Level(id="Q5.3", chapter="ch05", title="Pod 使用 PVC",
          description="集群已有 data-pv 和 data-pvc。创建 Pod，通过 volume 挂载 PVC",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: app-pod\nspec:\n  containers:\n    - name: app\n      image: nginx\n      # volumeMounts\n  # volumes with PVC",
          check_fn=_check_03_pod_with_pvc,
          lesson=Lesson(
              concept="""\
## Pod 使用 PVC

Pod 通过 `volumes[].persistentVolumeClaim` 引用 PVC，再通过 `volumeMounts` 挂载到容器内。数据持久化到 PV 支撑的存储上，Pod 删除后数据不丢失。

### 挂载流程

```
Pod → volumes (引用 PVC) → PVC → PV → 实际存储 (hostPath/NFS/云盘)
```

1. Pod 的 `spec.volumes` 定义一个 volume，类型为 `persistentVolumeClaim`
2. `claimName` 指向已存在的 PVC
3. 容器的 `volumeMounts` 将该 volume 挂载到容器内路径
4. 容器写入的数据通过 PVC → PV 持久化到实际存储

### 为什么不能直接挂载 PV？

Pod 直接引用 PV 会导致：
- 用户需要知道 PV 的具体细节
- namespace 隔离被打破（PV 是集群级）
- 无法实现存储的动态供给

通过 PVC 间接引用，实现了存储的抽象和解耦。

### accessModes 对 Pod 的影响

- `ReadWriteOnce`：Pod 只能调度到 PV 所在的 Node（对于 hostPath PV）
- `ReadWriteMany`：多个 Pod 可以同时读写（需要共享存储如 NFS）
- 如果多个 Pod 用同一个 RWO PVC，会被调度到同一 Node

### 数据生命周期

- Pod 删除 → PVC 保留 → PV 保留 → 数据保留
- PVC 删除 → PV Released（数据保留但不可用）
- PV 的 reclaimPolicy 决定 PVC 删除后 PV 的命运
""",
              key_fields=[
                  {"name": "spec.volumes[].persistentVolumeClaim.claimName", "description": "引用的 PVC 名称", "required": True, "example": "data-pvc"},
                  {"name": "spec.containers[].volumeMounts[].name", "description": "volume 名称，与 volumes 中的 name 一致", "required": True, "example": "data-volume"},
                  {"name": "spec.containers[].volumeMounts[].mountPath", "description": "容器内挂载路径", "required": True, "example": "/app/data"},
              ],
              diagram="""\
  Pod 使用 PVC 的完整数据流

  ┌──────── Pod (app-pod) ──────────────────────┐
  │  spec:                                      │
  │    volumes:                                 │
  │    - name: data-volume                      │
  │      persistentVolumeClaim:                 │
  │        claimName: data-pvc  ◄── 引用 PVC    │
  │    containers:                              │
  │    - name: app                              │
  │      volumeMounts:                          │
  │      - name: data-volume    ◄── 引用 volume │
  │        mountPath: /app/data                 │
  └──────────┬──────────────────────────────────┘
             │
             ▼
  ┌──── PVC (data-pvc) ──────┐    ┌──── PV (data-pv) ──────┐
  │  状态: Bound             │ →  │  capacity: 5Gi         │
  │  volumeName: data-pv     │    │  hostPath: /mnt/data   │
  └──────────────────────────┘    └───────────┬────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Node 磁盘       │
                                    │ /mnt/data       │
                                    │ (持久化存储)    │
                                    └─────────────────┘
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: app-pod                 # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx                # 镜像
    volumeMounts:               # 卷挂载
    - name: data-volume         # 引用 volume 名
      mountPath: /app/data      # 容器内挂载路径
  volumes:                      # 卷定义
  - name: data-volume           # volume 名
    persistentVolumeClaim:      # 引用 PVC
      claimName: data-pvc       # PVC 名称
""",
              common_errors=[
                  "volumeMounts 的 name 与 volumes 的 name 不一致",
                  "claimName 写错（必须与已存在的 PVC 名称一致）",
                  "忘记写 volumeMounts（定义了 volume 但没挂载到容器）",
                  "PVC 还没 Bound 就挂载（Pod 会卡在 ContainerCreating）",
              ],
              tips=[
                  "Pod 删除后 PVC 和 PV 保留，数据不丢失--这是持久化存储的核心价值",
                  "ReadWriteOnce 的 PVC 只能被一个 Node 上的 Pod 使用",
                  "用 kubectl describe pvc <name> 查看 PVC 绑定状态",
              ],
          ),
    ),
    Level(id="Q5.4", chapter="ch05", title="emptyDir 临时存储",
          description="创建一个含 2 个容器的 Pod，使用 emptyDir 在容器间共享临时数据",
          starter_yaml="apiVersion: v1\nkind: Pod\nmetadata:\n  name: shared-pod\nspec:\n  containers:\n    - name: writer\n      image: busybox\n    - name: reader\n      image: busybox\n  # volumes with emptyDir",
          check_fn=_check_04_emptydir,
          lesson=Lesson(
              concept="""\
## emptyDir 临时存储

**emptyDir** 是一种临时 Volume，在 Pod 被调度到 Node 时创建，Pod 删除时随之销毁。主要用于同一 Pod 内多容器间的**临时数据共享**。

### emptyDir 的生命周期

```
Pod 调度到 Node → 创建 emptyDir（空目录）→ 容器启动
                                          ↓
                              容器间通过 emptyDir 共享数据
                                          ↓
Pod 删除 → emptyDir 数据永久丢失
```

emptyDir 的生命周期**完全绑定 Pod**，不是绑定某个容器。Pod 内任一容器重启（crash 重启），emptyDir 数据**保留**。只有 Pod 被删除时数据才丢失。

### 典型使用场景

1. **Sidecar 模式**：主容器写日志，sidecar 容器通过 emptyDir 读取
2. **缓存空间**：临时计算结果的存储
3. **Init Container 传递数据**：init 容器下载数据，主容器使用
4. **多容器共享工作区**：如 writer 容器写入 → reader 容器读取

### emptyDir vs PVC

| 特性 | emptyDir | PVC |
|------|----------|-----|
| 持久性 | Pod 删除即消失 | Pod 删除后保留 |
| 共享范围 | Pod 内容器间 | 跨 Pod |
| 存储位置 | Node 本地磁盘 | 网络/本地存储 |
| 适用场景 | 临时共享 | 持久化数据 |

### medium 选项

默认 emptyDir 存储在 Node 的磁盘上。设置 `medium: Memory` 可以使用内存（tmpfs/RAM disk）：
- 速度极快（内存读写）
- 占用 Pod 内存配额
- 适合需要高速 IO 的临时数据
- 容器重启后数据丢失（因为 Pod 还在，但内存清空了... 实际上容器重启时 tmpfs 数据会丢失）

### sizeLimit

可以设置 `sizeLimit` 限制 emptyDir 的最大容量，超过时 Pod 会被驱逐。
""",
              key_fields=[
                  {"name": "spec.volumes[].emptyDir", "description": "声明 emptyDir 卷（空对象即可）", "required": True, "example": "{}"},
                  {"name": "spec.volumes[].emptyDir.medium", "description": "存储介质，默认为空(磁盘)，Memory 为内存", "required": False, "example": "Memory"},
                  {"name": "spec.containers[].volumeMounts[].name", "description": "引用 volume 名称", "required": True, "example": "shared-data"},
                  {"name": "spec.containers[].volumeMounts[].mountPath", "description": "容器内挂载路径", "required": True, "example": "/shared"},
              ],
              diagram="""\
  emptyDir 在多容器 Pod 中的共享

  ┌──────── Pod (shared-pod) ───────────────────┐
  │                                              │
  │  volumes:                                    │
  │  - name: shared-data                         │
  │    emptyDir: {}         ◄── 临时空目录       │
  │                                              │
  │  ┌────────────────┐  ┌────────────────┐     │
  │  │ Container:     │  │ Container:     │     │
  │  │   writer       │  │   reader       │     │
  │  │ Image: busybox │  │ Image: busybox │     │
  │  │                │  │                │     │
  │  │ volumeMounts:  │  │ volumeMounts:  │     │
  │  │ - name:        │  │ - name:        │     │
  │  │   shared-data  │  │   shared-data  │     │
  │  │   mountPath:   │  │   mountPath:   │     │
  │  │   /output      │  │   /input       │     │
  │  └───────┬────────┘  └───────▲────────┘     │
  │          │                    │               │
  │          │    共享同一个       │               │
  │          └──→ emptyDir ←──────┘               │
  │              (Node 本地磁盘)                  │
  │                                              │
  └──────────────────────────────────────────────┘
    Pod 删除 → emptyDir 数据永久丢失
    容器重启 → emptyDir 数据保留
""",
              example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: shared-pod              # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: writer                # 写入容器
    image: busybox              # 轻量镜像
    volumeMounts:               # 卷挂载
    - name: shared-data         # 引用 volume
      mountPath: /output        # 写入路径
  - name: reader                # 读取容器
    image: busybox              # 轻量镜像
    volumeMounts:               # 卷挂载
    - name: shared-data         # 同一个 volume
      mountPath: /input         # 读取路径
  volumes:                      # 卷定义
  - name: shared-data           # volume 名
    emptyDir: {}                # 临时空目录
""",
              common_errors=[
                  "用 emptyDir 存储需要持久化的数据（Pod 删除数据就没了）",
                  "volumeMounts 的 name 与 volumes 的 name 不一致",
                  "两个容器挂载到不同的 mountPath 但期望共享（必须挂载同一个 volume）",
                  "期望 emptyDir 在容器重启后丢失数据（实际容器重启数据保留，Pod 删除才丢）",
              ],
              tips=[
                  "emptyDir 适合 Sidecar/Init Container 场景的临时数据共享",
                  "需要高速 IO 时设 medium: Memory 用内存存储（但消耗内存配额）",
                  "Pod 内容器重启不会丢 emptyDir 数据，只有 Pod 删除才丢",
              ],
          ),
    ),
]
