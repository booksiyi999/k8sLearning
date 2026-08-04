"""Chapter 20: 存储进阶 - StorageClass/CSI/VolumeSnapshot（5 关）

Q20.1 创建 StorageClass - 动态 Provisioning
Q20.2 CSI 驱动概念 - driver/volumeBindingMode
Q20.3 VolumeSnapshot - 卷快照创建
Q20.4 VolumeSnapshotContent - 快照内容管理
Q20.5 集群实战 - 动态存储全流程 (SC+PVC+Pod+Snapshot)
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q20.1 创建 StorageClass ====================

def _check_201_create_sc(user_yaml: str) -> CheckResult:
    """Q20.1 创建一个 StorageClass（动态 Provisioning）"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.storageclasses:
        return CheckResult(
            ok=False,
            error="没有创建任何 StorageClass",
            hints=["你需要 apply 一个 kind: StorageClass 的 YAML"],
        )

    sc_name = next(iter(state.storageclasses))
    sc = state.storageclasses[sc_name]
    spec = sc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="StorageClass 缺少 spec", hints=[])

    # 检查 provisioner
    provisioner = spec.get("provisioner")
    if not provisioner:
        return CheckResult(
            ok=False,
            error="StorageClass 缺少 spec.provisioner",
            hints=["provisioner 指定动态卷分配器，如 kubernetes.io/no-provisioner 或 CSI 驱动名"],
        )

    # 检查 reclaimPolicy（可选，默认 Delete）
    reclaim_policy = spec.get("reclaimPolicy", "Delete")
    if reclaim_policy not in ("Delete", "Retain"):
        return CheckResult(
            ok=False,
            error=f"reclaimPolicy 应为 'Delete' 或 'Retain'，实际为 '{reclaim_policy}'",
            hints=["reclaimPolicy: Delete（默认）或 Retain"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["StorageClass 创建成功！动态 Provisioning 会按需创建 PV 🏗️"],
    )


LEVEL_Q20_1 = Level(
    id="Q20.1",
    chapter="ch20",
    title="创建 StorageClass",
    description="""
# 创建 StorageClass 🏗️

**StorageClass** 为管理员提供了一种描述"存储类别"的方式。通过 StorageClass，K8s 可以实现**动态卷供应（Dynamic Provisioning）**——当 PVC 创建时自动分配 PV，无需预先创建。

## 任务

创建一个 StorageClass：
- `kind: StorageClass`
- `spec.provisioner` 指定一个 CSI 驱动或内置驱动
- `spec.reclaimPolicy: Retain`（PV 释放后保留数据）

## 提示

StorageClass 让存储按需创建：
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: pd.csi.storage.gke.io
reclaimPolicy: Retain
parameters:
  type: pd-ssd
```

注意：StorageClass 没有传统意义上的 spec 字段——provisioner、parameters 等字段是**顶层**字段。
""",
    starter_yaml="""\
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
# provisioner: pd.csi.storage.gke.io
# reclaimPolicy: Retain
# parameters:
#   type: pd-ssd
""",
    check_fn=_check_201_create_sc,
    lesson=Lesson(
        concept="""\
## StorageClass 与动态 Provisioning

**StorageClass** 是 K8s 中描述"存储类别"的资源，它实现了**动态卷供应**：当用户创建 PVC 时，K8s 根据 PVC 引用的 StorageClass 自动创建对应的 PV，无需管理员手动预先创建。

### 静态 vs 动态 Provisioning

| 特性 | 静态 Provisioning | 动态 Provisioning |
|------|-------------------|-------------------|
| PV 创建方式 | 管理员手动创建 | 根据 PVC 自动创建 |
| 工作流程 | 先创建 PV → 再创建 PVC 绑定 | 创建 PVC → 自动创建 PV |
| StorageClass | 不需要 | 必须指定 |
| 适用场景 | 已有存储设备 | 云存储、按需分配 |

### StorageClass 核心字段

注意：StorageClass 的 `provisioner`、`reclaimPolicy` 等字段是**顶层字段**，不在 `spec` 下（尽管模拟器中统一存储在 spec 下）。

| 字段 | 说明 | 示例 |
|------|------|------|
| `provisioner` | 卷分配器名称 | `kubernetes.io/no-provisioner` |
| `reclaimPolicy` | PV 回收策略 | `Delete` / `Retain` |
| `volumeBindingMode` | 卷绑定模式 | `Immediate` / `WaitForFirstConsumer` |
| `parameters` | 分配器参数 | `type: pd-ssd` |
| `allowVolumeExpansion` | 是否允许卷扩容 | `true` |

### 动态 Provisioning 工作流程

```
1. 管理员创建 StorageClass (指定 provisioner)
2. 用户创建 PVC (指定 storageClassName)
3. K8s 根据 StorageClass 自动创建 PV
4. PV 与 PVC 自动绑定
5. Pod 通过 PVC 使用存储
```

### 常见 provisioner

| provisioner | 说明 |
|-------------|------|
| `kubernetes.io/no-provisioner` | 不支持动态供应（需静态 PV） |
| `kubernetes.io/aws-ebs` | AWS EBS |
| `kubernetes.io/gce-pd` | GCE Persistent Disk |
| `kubernetes.io/azure-disk` | Azure Disk |
| `pd.csi.storage.gke.io` | GCE PD CSI 驱动 |
| `ebs.csi.aws.com` | AWS EBS CSI 驱动 |
| `disk.csi.azure.com` | Azure Disk CSI 驱动 |
| `rbd.csi.ceph.com` | Ceph RBD CSI 驱动 |
""",
        key_fields=[
            {"name": "provisioner", "description": "卷分配器名称，决定使用哪个存储后端", "required": True, "example": "pd.csi.storage.gke.io"},
            {"name": "reclaimPolicy", "description": "PV 回收策略: Delete 或 Retain", "required": False, "example": "Retain"},
            {"name": "volumeBindingMode", "description": "卷绑定模式: Immediate 或 WaitForFirstConsumer", "required": False, "example": "WaitForFirstConsumer"},
            {"name": "parameters", "description": "传递给 provisioner 的参数", "required": False, "example": "type: pd-ssd"},
            {"name": "allowVolumeExpansion", "description": "是否允许在线扩容 PV", "required": False, "example": "true"},
        ],
        diagram="""\
  StorageClass 动态 Provisioning 流程

  ┌───────────────────────────────────────────────────┐
  │              StorageClass (fast-storage)          │
  │  provisioner: pd.csi.storage.gke.io               │
  │  reclaimPolicy: Retain                            │
  │  parameters:                                      │
  │    type: pd-ssd                                   │
  └───────────────────────┬───────────────────────────┘
                          │
                          │ PVC 引用 storageClassName
                          ▼
  ┌───────────────────────────────────────────────────┐
  │              PersistentVolumeClaim                │
  │  spec:                                           │
  │    storageClassName: fast-storage                 │
  │    accessModes: [ReadWriteOnce]                   │
  │    resources:                                     │
  │      requests:                                    │
  │        storage: 10Gi                              │
  └───────────────────────┬───────────────────────────┘
                          │
                          │ CSI 驱动自动创建 PV
                          ▼
  ┌───────────────────────────────────────────────────┐
  │              PersistentVolume (自动创建)           │
  │  capacity: 10Gi                                   │
  │  accessModes: [ReadWriteOnce]                     │
  │  storageClassName: fast-storage                   │
  │  status: Bound                                    │
  └───────────────────────┬───────────────────────────┘
                          │
                          │ Pod 挂载 PVC
                          ▼
                    ┌──────────┐
                    │   Pod     │
                    │  volume:  │
                    │   pvc     │
                    └──────────┘
""",
        example_yaml="""\
apiVersion: storage.k8s.io/v1   # StorageClass API 版本
kind: StorageClass              # 资源类型
metadata:
  name: fast-storage            # StorageClass 名称
provisioner: pd.csi.storage.gke.io  # CSI 驱动
reclaimPolicy: Retain           # PV 释放后保留数据
volumeBindingMode: WaitForFirstConsumer  # 延迟绑定
allowVolumeExpansion: true      # 允许在线扩容
parameters:                     # 驱动参数
  type: pd-ssd                  # SSD 磁盘
  replication-type: regional-pd # 区域级持久磁盘
""",
        common_errors=[
            "provisioner 写错，导致动态供应失败（找不到对应的 CSI 驱动）",
            "reclaimPolicy 写成小写 delete（K8s 要求首字母大写: Delete/Retain）",
            "StorageClass 名字与 PVC 中 storageClassName 不匹配",
            "在不支持动态供应的环境中使用 StorageClass（需确保集群有 CSI 驱动）",
        ],
        tips=[
            "用 kubectl get storageclass 查看集群中的 StorageClass",
            "用 kubectl get sc <name> -o yaml 查看详细配置",
            "默认 StorageClass 带有 annotation: storageclass.kubernetes.io/is-default-class: true",
        ],
    ),
)


# ==================== Q20.2 CSI 驱动概念 ====================

def _check_202_csi_driver(user_yaml: str) -> CheckResult:
    """Q20.2 CSI 驱动概念 - 验证 volumeBindingMode 和 CSI 相关配置"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.storageclasses:
        return CheckResult(
            ok=False,
            error="没有创建任何 StorageClass",
            hints=["创建 kind: StorageClass 的 YAML"],
        )

    sc_name = next(iter(state.storageclasses))
    sc = state.storageclasses[sc_name]
    spec = sc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="StorageClass 缺少 spec", hints=[])

    # 检查 provisioner 是 CSI 驱动（包含 .csi. 或 csi.storage）
    provisioner = spec.get("provisioner", "")
    if not provisioner:
        return CheckResult(
            ok=False,
            error="StorageClass 缺少 provisioner",
            hints=["指定 CSI 驱动名称作为 provisioner"],
        )

    is_csi = "csi" in provisioner.lower()
    if not is_csi:
        return CheckResult(
            ok=False,
            error=f"provisioner '{provisioner}' 不是 CSI 驱动",
            hints=["CSI 驱动名称通常包含 'csi'，如 ebs.csi.aws.com"],
        )

    # 检查 volumeBindingMode
    binding_mode = spec.get("volumeBindingMode")
    if not binding_mode:
        return CheckResult(
            ok=False,
            error="StorageClass 缺少 volumeBindingMode",
            hints=["添加 volumeBindingMode: WaitForFirstConsumer"],
        )

    if binding_mode not in ("Immediate", "WaitForFirstConsumer"):
        return CheckResult(
            ok=False,
            error=f"volumeBindingMode 应为 'Immediate' 或 'WaitForFirstConsumer'，实际为 '{binding_mode}'",
            hints=["WaitForFirstConsumer 延迟绑定，直到 Pod 调度后才创建 PV"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["CSI 驱动配置正确！WaitForFirstConsumer 确保存储和 Pod 在同一拓扑域 🔧"],
    )


LEVEL_Q20_2 = Level(
    id="Q20.2",
    chapter="ch20",
    title="CSI 驱动概念",
    description="""
# CSI 驱动概念 🔧

**CSI（Container Storage Interface）** 是 K8s 存储的标准接口。通过 CSI，存储厂商可以编写独立的驱动插件，无需修改 K8s 核心代码。

## 任务

创建一个使用 **CSI 驱动** 的 StorageClass：
- `provisioner` 使用 CSI 驱动名称（如 `ebs.csi.aws.com`）
- `volumeBindingMode: WaitForFirstConsumer`（延迟卷绑定）
- 添加 `parameters` 配置磁盘类型

## 提示

WaitForFirstConsumer 模式下，PV 不会在 PVC 创建时立即绑定，而是等到 Pod 被调度后才创建：
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  fsType: ext4
```
""",
    starter_yaml="""\
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
# provisioner: ebs.csi.aws.com
# volumeBindingMode: WaitForFirstConsumer
# parameters:
#   type: gp3
#   fsType: ext4
""",
    check_fn=_check_202_csi_driver,
    lesson=Lesson(
        concept="""\
## CSI（Container Storage Interface）

**CSI** 是一个标准化的容器存储接口，使 K8s 可以与各种存储系统交互。CSI 将存储逻辑从 K8s 核心代码中解耦，存储厂商只需实现 CSI 接口即可。

### CSI 架构

```
┌─────────────────────────────────────────────────┐
│                  Kubernetes                      │
│  ┌───────────────────────────────────────────┐  │
│  │            CSI External Components         │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────┐│  │
│  │  │ Provisioner│ │ Attacher   │ │Resizer ││  │
│  │  │ Controller │ │ Controller │ │        ││  │
│  │  └─────┬──────┘ └─────┬──────┘ └───┬────┘│  │
│  └────────┼──────────────┼────────────┼─────┘  │
│           │              │            │         │
│  ┌────────┴──────────────┴────────────┴─────┐  │
│  │           CSI Driver (Sidecar)            │  │
│  │  ┌─────────────┐  ┌─────────────────┐    │  │
│  │  │ CSI Plugin  │  │ Node Plugin      │    │  │
│  │  │ (Controller)│  │ (kubelet sidecar)│    │  │
│  │  └──────┬──────┘  └────────┬────────┘    │  │
│  └─────────┼──────────────────┼─────────────┘  │
└────────────┼──────────────────┼─────────────────┘
             │                  │
             ▼                  ▼
        ┌─────────────────────────────┐
        │    存储后端 (EBS/Ceph/NFS)   │
        └─────────────────────────────┘
```

### volumeBindingMode

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| **Immediate** | PVC 创建时立即创建并绑定 PV | 单区域集群 |
| **WaitForFirstConsumer** | 等 Pod 调度后才创建 PV | 多区域/可用区集群 |

**WaitForFirstConsumer** 的优势：
- 确保存储与 Pod 在同一可用区
- 避免跨区域存储访问的性能问题
- 配合 topology constraints 工作

### CSI 驱动能力

CSI 驱动可以支持以下能力（通过 ControllerGetCapabilities / NodeGetCapabilities）：

| 能力 | 说明 |
|------|------|
| 创建/删除卷 | 基本的动态供应 |
| 挂载/卸载卷 | 将存储附加到节点 |
| 卷快照 | 创建卷快照 |
| 卷扩容 | 在线扩展卷容量 |
| 卷克隆 | 从已有卷克隆新卷 |
| 原始块设备 | 支持块设备模式 |
""",
        key_fields=[
            {"name": "provisioner", "description": "CSI 驱动名称", "required": True, "example": "ebs.csi.aws.com"},
            {"name": "volumeBindingMode", "description": "卷绑定模式: Immediate 或 WaitForFirstConsumer", "required": True, "example": "WaitForFirstConsumer"},
            {"name": "parameters.type", "description": "磁盘类型参数", "required": False, "example": "gp3"},
            {"name": "parameters.fsType", "description": "文件系统类型", "required": False, "example": "ext4"},
            {"name": "allowVolumeExpansion", "description": "允许在线扩容", "required": False, "example": "true"},
        ],
        diagram="""\
  CSI 驱动与 StorageClass 工作流程

  ┌─────── StorageClass (ebs-sc) ──────────────────┐
  │  provisioner: ebs.csi.aws.com                  │
  │  volumeBindingMode: WaitForFirstConsumer       │
  │  parameters:                                   │
  │    type: gp3                                   │
  │    fsType: ext4                                │
  └───────────────────┬───────────────────────────┘
                      │
                      │ PVC 引用 (不立即绑定)
                      ▼
  ┌───────────────────────────────────────────────┐
  │  PVC (data-pvc)  -- 状态: Pending (未绑定)    │
  └───────────────────┬───────────────────────────┘
                      │
                      │ Pod 创建 → 调度器选择节点 (zone=us-east-1a)
                      ▼
  ┌───────────────────────────────────────────────┐
  │  CSI Provisioner Controller                   │
  │  调用 CSI CreateVolume (zone=us-east-1a)      │
  │  → 在同 zone 创建 EBS 卷                       │
  │  → 返回 volume ID                             │
  └───────────────────┬───────────────────────────┘
                      │
                      ▼
  ┌───────────────────────────────────────────────┐
  │  PV (自动创建) -- 状态: Bound (绑定到 PVC)    │
  │  CSI Node Plugin                              │
  │  → 将 EBS 卷挂载到节点                        │
  │  → Pod 容器通过 volumeMounts 访问             │
  └───────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: storage.k8s.io/v1   # StorageClass API 版本
kind: StorageClass
metadata:
  name: ebs-sc                  # StorageClass 名称
provisioner: ebs.csi.aws.com    # AWS EBS CSI 驱动
volumeBindingMode: WaitForFirstConsumer  # 延迟绑定
allowVolumeExpansion: true      # 允许在线扩容
reclaimPolicy: Delete           # PVC 删除时自动删除 PV
parameters:                     # CSI 驱动参数
  type: gp3                     # EBS 卷类型
  fsType: ext4                  # 文件系统类型
  encrypted: "true"             # 启用加密
mountOptions:                   # 挂载选项
  - noatime                     # 不更新访问时间
""",
        common_errors=[
            "volumeBindingMode 写成小写 immediate（K8s 要求首字母大写）",
            "WaitForFirstConsumer 模式下没有 topology 信息导致 Pod 无法调度",
            "CSI 驱动未安装就创建 StorageClass（集群中没有对应的 CSI driver）",
            "parameters 中的参数不被 CSI 驱动支持（查阅驱动文档）",
        ],
        tips=[
            "用 kubectl get csidriver 查看集群中安装的 CSI 驱动",
            "WaitForFirstConsumer 适合多可用区集群，避免跨区存储延迟",
            "allowVolumeExpansion: true 允许通过修改 PVC 的 requests.storage 在线扩容",
        ],
    ),
)


# ==================== Q20.3 VolumeSnapshot ====================

def _check_203_create_snapshot(user_yaml: str) -> CheckResult:
    """Q20.3 创建 VolumeSnapshot - 对 PVC 创建快照"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.volumesnapshots:
        return CheckResult(
            ok=False,
            error="没有创建任何 VolumeSnapshot",
            hints=["创建 kind: VolumeSnapshot 的 YAML"],
        )

    vs_name = next(iter(state.volumesnapshots))
    vs = state.volumesnapshots[vs_name]
    spec = vs.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="VolumeSnapshot 缺少 spec", hints=[])

    # 检查 source
    source = spec.get("source")
    if not isinstance(source, dict) or not source:
        return CheckResult(
            ok=False,
            error="VolumeSnapshot 缺少 spec.source",
            hints=["spec.source 应引用 PVC 或 VolumeSnapshotContent"],
        )

    # 检查 source.persistentVolumeClaimName
    pvc_ref = source.get("persistentVolumeClaimName")
    if not pvc_ref:
        return CheckResult(
            ok=False,
            error="VolumeSnapshot source 缺少 persistentVolumeClaimName",
            hints=["spec.source.persistentVolumeClaimName 引用要快照的 PVC"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["VolumeSnapshot 创建成功！CSI 驱动会自动对 PVC 的卷创建快照 📸"],
    )


LEVEL_Q20_3 = Level(
    id="Q20.3",
    chapter="ch20",
    title="VolumeSnapshot 卷快照",
    description="""
# VolumeSnapshot 卷快照 📸

**VolumeSnapshot** 允许你对 PV 中的数据创建时间点副本（快照），用于备份、恢复和克隆。

## 任务

创建一个 **VolumeSnapshot**：
- `kind: VolumeSnapshot`
- `spec.source.persistentVolumeClaimName` 引用一个 PVC

## 提示

VolumeSnapshot 通过引用 PVC 来创建快照：
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-snapshot
spec:
  source:
    persistentVolumeClaimName: data-pvc
```
""",
    starter_yaml="""\
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-snapshot
spec:
  # source:
  #   persistentVolumeClaimName: data-pvc
""",
    check_fn=_check_203_create_snapshot,
    lesson=Lesson(
        concept="""\
## VolumeSnapshot 卷快照

**VolumeSnapshot** 是 K8s 中对持久卷创建**时间点快照**的资源。快照可以用于数据备份、恢复到之前的状态，或创建新的卷（从快照恢复）。

### 快照相关资源

| 资源 | 作用域 | 说明 |
|------|--------|------|
| **VolumeSnapshot** | 命名空间级 | 用户创建的快照请求 |
| **VolumeSnapshotContent** | 集群级 | 快照的实际后端资源（类似 PV） |
| **VolumeSnapshotClass** | 集群级 | 快照的配置模板（类似 StorageClass） |

### 快照的工作流程

```
1. 用户创建 VolumeSnapshot（引用 PVC）
2. CSI 驱动对 PVC 对应的存储卷创建快照
3. K8s 自动创建 VolumeSnapshotContent（集群级资源）
4. VolumeSnapshot 变为 ReadyToUse: true
5. 用户可从快照恢复新的 PVC
```

### 快照与 PVC 的关系

```
PVC (data-pvc)  ←─── 源卷
    │
    │ 创建 VolumeSnapshot
    ▼
VolumeSnapshot (data-snapshot)
    │
    │ CSI 驱动创建后端快照
    ▼
VolumeSnapshotContent (snapcontent-xxx)  ←─── 集群级资源
    │
    │ 从快照恢复
    ▼
PVC (restored-pvc)  ←─── 新卷（数据与快照时一致）
```

### VolumeSnapshot 字段

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-snapshot
  namespace: default
spec:
  source:
    # 方式一: 从 PVC 创建快照（动态）
    persistentVolumeClaimName: data-pvc
    # 方式二: 引用已有的 VolumeSnapshotContent（静态）
    # volumeSnapshotContentName: snapcontent-xxx
  # volumeSnapshotClassName: my-snapshot-class  # 可选
```

### 从快照恢复 PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-pvc
spec:
  storageClassName: fast-storage
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
  dataSource:
    name: data-snapshot           # 引用快照
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```
""",
        key_fields=[
            {"name": "spec.source.persistentVolumeClaimName", "description": "要快照的 PVC 名称", "required": True, "example": "data-pvc"},
            {"name": "spec.source.volumeSnapshotContentName", "description": "引用已有快照内容（静态）", "required": False, "example": "snapcontent-xxx"},
            {"name": "spec.volumeSnapshotClassName", "description": "快照类名称", "required": False, "example": "my-snapshot-class"},
            {"name": "status.readyToUse", "description": "快照是否就绪（只读）", "required": False, "example": "true"},
        ],
        diagram="""\
  VolumeSnapshot 创建与恢复流程

  ┌─────────────────────────────────────────────────────┐
  │                   原始数据卷                        │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐     │
  │  │   PVC    │───▶│   PV     │───▶│ 存储后端  │     │
  │  │ data-pvc │    │ pv-001   │    │ (EBS)    │     │
  │  └──────────┘    └──────────┘    └─────┬────┘     │
  └────────────────────────────────────────┼──────────┘
                                           │
                        创建 VolumeSnapshot │
                                           ▼
  ┌─────────────────────────────────────────────────────┐
  │                   快照创建                           │
  │  ┌────────────────────┐                             │
  │  │  VolumeSnapshot    │  metadata: data-snapshot    │
  │  │                    │  spec.source.pvcName: data-pvc│
  │  └────────┬───────────┘                             │
  │           │                                         │
  │           │ CSI 驱动创建后端快照                     │
  │           ▼                                         │
  │  ┌────────────────────────────┐                     │
  │  │ VolumeSnapshotContent      │  集群级资源          │
  │  │ snapcontent-xxx            │  status: ReadyToUse │
  │  └────────────────────────────┘                     │
  └─────────────────────────────────────────────────────┘
                                           │
                        从快照恢复         │
                                           ▼
  ┌─────────────────────────────────────────────────────┐
  │                   恢复新卷                           │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐     │
  │  │   PVC    │───▶│   PV     │───▶│ 存储后端  │     │
  │  │ restored │    │ pv-002   │    │ (EBS)    │     │
  │  │   -pvc   │    │ (新创建) │    │ (从快照) │     │
  │  └──────────┘    └──────────┘    └──────────┘     │
  │  dataSource: VolumeSnapshot: data-snapshot          │
  └─────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: snapshot.storage.k8s.io/v1  # 快照 API 版本
kind: VolumeSnapshot                    # 资源类型
metadata:
  name: data-snapshot                   # 快照名称
  namespace: default                    # 命名空间
spec:
  source:
    persistentVolumeClaimName: data-pvc # 要快照的 PVC 名称
  volumeSnapshotClassName: csi-snapclass # 快照类（可选）
""",
        common_errors=[
            "引用的 PVC 不存在或未绑定 PV（快照需要 PVC 处于 Bound 状态）",
            "CSI 驱动不支持快照功能（需确认驱动支持 VolumeSnapshot）",
            "忘记创建 VolumeSnapshotClass（某些 CSI 驱动需要）",
            "apiVersion 写错：快照使用 snapshot.storage.k8s.io/v1",
        ],
        tips=[
            "用 kubectl get volumesnapshot 查看快照状态",
            "用 kubectl describe volumesnapshot <name> 查看快照详情和事件",
            "快照恢复时新 PVC 的 storage 不能小于快照源卷的大小",
        ],
    ),
)


# ==================== Q20.4 VolumeSnapshotContent ====================

def _check_204_snapshot_content(user_yaml: str) -> CheckResult:
    """Q20.4 VolumeSnapshotContent - 快照内容管理"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.volumesnapshotcontents:
        return CheckResult(
            ok=False,
            error="没有创建任何 VolumeSnapshotContent",
            hints=["创建 kind: VolumeSnapshotContent 的 YAML"],
        )

    vsc_name = next(iter(state.volumesnapshotcontents))
    vsc = state.volumesnapshotcontents[vsc_name]
    spec = vsc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="VolumeSnapshotContent 缺少 spec", hints=[])

    # 检查 volumeSnapshotRef
    snap_ref = spec.get("volumeSnapshotRef")
    if not isinstance(snap_ref, dict) or not snap_ref:
        return CheckResult(
            ok=False,
            error="VolumeSnapshotContent 缺少 spec.volumeSnapshotRef",
            hints=["volumeSnapshotRef 引用对应的 VolumeSnapshot"],
        )
    if not snap_ref.get("name"):
        return CheckResult(
            ok=False,
            error="volumeSnapshotRef 缺少 name",
            hints=["volumeSnapshotRef.name 引用 VolumeSnapshot 名称"],
        )

    # 检查 source（快照后端句柄）
    source = spec.get("source")
    if not isinstance(source, dict) or not source:
        return CheckResult(
            ok=False,
            error="VolumeSnapshotContent 缺少 spec.source",
            hints=["source 包含快照的后端句柄，如 snapshotHandle"],
        )

    # 静态快照需要 source.snapshotHandle
    # 动态快照由 CSI 驱动填充 source，但静态创建时需要指定
    if not source.get("snapshotHandle"):
        return CheckResult(
            ok=False,
            error="source 缺少 snapshotHandle（静态快照必须指定后端快照 ID）",
            hints=["source.snapshotHandle: snap-xxx（存储后端的快照 ID）"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["VolumeSnapshotContent 创建成功！它是集群级资源，管理后端快照的句柄 🗃️"],
    )


LEVEL_Q20_4 = Level(
    id="Q20.4",
    chapter="ch20",
    title="VolumeSnapshotContent",
    description="""
# VolumeSnapshotContent 快照内容管理 🗃️

**VolumeSnapshotContent** 是集群级资源，代表存储后端的实际快照。它类似于 PV 与 PVC 的关系——VolumeSnapshotContent 是 VolumeSnapshot 的后端资源。

## 任务

创建一个**静态** VolumeSnapshotContent：
- `kind: VolumeSnapshotContent`
- `spec.volumeSnapshotRef` 引用一个 VolumeSnapshot
- `spec.source.snapshotHandle` 指定后端快照 ID
- `spec.driver` 指定 CSI 驱动

## 提示

VolumeSnapshotContent 是集群级资源（类似 PV），VolumeSnapshot 是命名空间级资源（类似 PVC）：
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotContent
metadata:
  name: snapcontent-001
spec:
  driver: ebs.csi.aws.com
  volumeSnapshotRef:
    name: data-snapshot
    namespace: default
  source:
    snapshotHandle: snap-0abcdef1234567890
```
""",
    starter_yaml="""\
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotContent
metadata:
  name: snapcontent-001
spec:
  # driver: ebs.csi.aws.com
  # volumeSnapshotRef:
  #   name: data-snapshot
  #   namespace: default
  # source:
  #   snapshotHandle: snap-0abcdef1234567890
""",
    check_fn=_check_204_snapshot_content,
    lesson=Lesson(
        concept="""\
## VolumeSnapshotContent 快照内容

**VolumeSnapshotContent** 是**集群级**资源，代表存储后端的实际快照。它与 VolumeSnapshot 的关系类似 PV 与 PVC：

| 资源 | 作用域 | 作用 |
|------|--------|------|
| VolumeSnapshotContent | 集群级 | 后端快照实例（类似 PV） |
| VolumeSnapshot | 命名空间级 | 用户快照请求（类似 PVC） |
| VolumeSnapshotClass | 集群级 | 快照配置模板（类似 StorageClass） |

### 静态 vs 动态快照

| 类型 | 工作流程 | VolumeSnapshotContent |
|------|----------|----------------------|
| **动态快照** | 用户创建 VolumeSnapshot → CSI 自动创建 VolumeSnapshotContent | 自动生成 |
| **静态快照** | 管理员手动创建 VolumeSnapshotContent → 用户创建 VolumeSnapshot 引用 | 手动创建 |

### 动态快照流程

```
1. 用户创建 VolumeSnapshot (引用 PVC)
2. CSI 驱动创建后端快照
3. K8s 自动创建 VolumeSnapshotContent
4. VolumeSnapshotContent 中填充 source.snapshotHandle
5. VolumeSnapshot.status.readyToUse = true
```

### 静态快照流程

```
1. 管理员在存储后端手动创建快照
2. 管理员创建 VolumeSnapshotContent (指定 snapshotHandle)
3. 用户创建 VolumeSnapshot (引用 VolumeSnapshotContent)
4. VolumeSnapshot 绑定到 VolumeSnapshotContent
```

### VolumeSnapshotContent 关键字段

```yaml
spec:
  driver: ebs.csi.aws.com          # CSI 驱动名称
  volumeSnapshotRef:               # 引用 VolumeSnapshot
    name: data-snapshot
    namespace: default
  source:
    # 静态: 指定已有快照
    snapshotHandle: snap-0abcdef...
    # 动态: CSI 驱动填充（创建时留空）
    # volumeHandle: vol-xxx  (动态时源卷的 handle)
  deletionPolicy: Retain           # 删除策略: Delete / Retain
```

### VolumeSnapshotClass

VolumeSnapshotClass 类似 StorageClass，用于配置快照的创建参数：

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapclass
driver: ebs.csi.aws.com            # CSI 驱动
deletionPolicy: Delete             # 快照删除策略
parameters:                        # 驱动特定参数
  encrypted: "true"
```
""",
        key_fields=[
            {"name": "spec.driver", "description": "CSI 驱动名称", "required": True, "example": "ebs.csi.aws.com"},
            {"name": "spec.volumeSnapshotRef", "description": "引用对应的 VolumeSnapshot", "required": True, "example": "{name: data-snapshot, namespace: default}"},
            {"name": "spec.source.snapshotHandle", "description": "后端快照 ID（静态快照必须指定）", "required": True, "example": "snap-0abcdef..."},
            {"name": "spec.deletionPolicy", "description": "删除策略: Delete 或 Retain", "required": False, "example": "Retain"},
            {"name": "spec.source.volumeHandle", "description": "源卷 ID（动态快照创建时使用）", "required": False, "example": "vol-xxx"},
        ],
        diagram="""\
  VolumeSnapshotContent 与 VolumeSnapshot 的关系

  ┌─────────────── 集群级 (Cluster-scoped) ────────────────┐
  │                                                        │
  │  ┌──────────────────────────────────────┐             │
  │  │  VolumeSnapshotContent               │             │
  │  │  metadata.name: snapcontent-001      │             │
  │  │  spec:                               │             │
  │  │    driver: ebs.csi.aws.com           │             │
  │  │    volumeSnapshotRef:                │             │
  │  │      name: data-snapshot             │──┐          │
  │  │      namespace: default              │  │ 引用      │
  │  │    source:                           │  │          │
  │  │      snapshotHandle: snap-0abc...    │  │          │
  │  │    deletionPolicy: Retain            │  │          │
  │  └──────────────────────────────────────┘  │          │
  │                                             │          │
  └─────────────────────────────────────────────┼──────────┘
                                                │
  ┌─────────────── 命名空间级 (Namespace) ──────┼──────────┐
  │                                             │          │
  │  ┌──────────────────────────────────────┐  │          │
  │  │  VolumeSnapshot                      │◄─┘          │
  │  │  metadata.name: data-snapshot        │             │
  │  │  metadata.namespace: default         │             │
  │  │  spec:                               │             │
  │  │    source:                           │             │
  │  │      volumeSnapshotContentName:      │             │
  │  │        snapcontent-001               │──┐          │
  │  │  status:                             │  │ 绑定      │
  │  │    readyToUse: true                  │  │          │
  │  │    boundVolumeSnapshotContentName:   │  │          │
  │  │      snapcontent-001                 │  │          │
  │  └──────────────────────────────────────┘  │          │
  │                                             │          │
  └─────────────────────────────────────────────┼──────────┘
                                                │
  ┌─────────────────────────────────────────────┼──────────┐
  │  存储后端 (EBS)                              │          │
  │  ┌──────────────────────────────────────┐  │          │
  │  │  快照 snap-0abcdef...                 │◄─┘          │
  │  │  (通过 snapshotHandle 关联)           │             │
  │  └──────────────────────────────────────┘             │
  └────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: snapshot.storage.k8s.io/v1  # 快照内容 API 版本
kind: VolumeSnapshotContent             # 资源类型（集群级）
metadata:
  name: snapcontent-001                 # 快照内容名称
spec:
  driver: ebs.csi.aws.com               # CSI 驱动名称
  deletionPolicy: Retain                # 删除策略: 保留快照
  volumeSnapshotRef:                    # 引用 VolumeSnapshot
    name: data-snapshot                 # VolumeSnapshot 名称
    namespace: default                  # 命名空间
  source:
    snapshotHandle: snap-0abcdef1234567890  # 后端快照 ID
""",
        common_errors=[
            "混淆 VolumeSnapshotContent（集群级）和 VolumeSnapshot（命名空间级）",
            "静态快照忘记指定 snapshotHandle（后端快照 ID）",
            "volumeSnapshotRef 中的 name/namespace 与实际 VolumeSnapshot 不匹配",
            "deletionPolicy 写成小写 retain（应为 Retain 或 Delete）",
        ],
        tips=[
            "用 kubectl get volumesnapshotcontent 查看集群级快照内容",
            "动态快照的 VolumeSnapshotContent 由 CSI 驱动自动创建，无需手动管理",
            "静态快照适合从其他集群或外部存储系统导入已有快照",
        ],
    ),
)


# ==================== Q20.5 集群实战 - 动态存储全流程 ====================

def _check_205_full_workflow(user_yaml: str) -> CheckResult:
    """Q20.5 集群实战 - 动态存储全流程 (SC + PVC + Pod + Snapshot)"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 StorageClass
    if not state.storageclasses:
        return CheckResult(
            ok=False,
            error="缺少 StorageClass",
            hints=["创建 kind: StorageClass 定义存储类别"],
        )

    # 检查 PVC
    if not state.persistentvolumeclaims:
        return CheckResult(
            ok=False,
            error="缺少 PersistentVolumeClaim",
            hints=["创建 PVC 并引用 StorageClass"],
        )

    # 检查 Pod
    if not state.pods:
        return CheckResult(
            ok=False,
            error="缺少 Pod",
            hints=["创建 Pod 并通过 volumes 引用 PVC"],
        )

    # 检查 VolumeSnapshot
    if not state.volumesnapshots:
        return CheckResult(
            ok=False,
            error="缺少 VolumeSnapshot",
            hints=["创建 VolumeSnapshot 对 PVC 进行快照"],
        )

    # 验证 PVC 引用了 StorageClass
    pvc_name = next(iter(state.persistentvolumeclaims))
    pvc = state.persistentvolumeclaims[pvc_name]
    pvc_spec = pvc.get("spec", {})
    if not isinstance(pvc_spec, dict):
        return CheckResult(ok=False, error="PVC 缺少 spec", hints=[])

    sc_name_in_pvc = pvc_spec.get("storageClassName", "")
    sc_names = list(state.storageclasses.keys())
    if sc_name_in_pvc and sc_name_in_pvc not in sc_names:
        return CheckResult(
            ok=False,
            error=f"PVC 引用的 storageClassName '{sc_name_in_pvc}' 不存在于 StorageClass 列表中",
            hints=[f"可用的 StorageClass: {sc_names}"],
        )

    # 验证 Pod 引用了 PVC
    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    pod_spec = pod.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    volumes = pod_spec.get("volumes", [])
    found_pvc_ref = False
    if isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict):
                pvc_ref = v.get("persistentVolumeClaim", {})
                if isinstance(pvc_ref, dict) and pvc_ref.get("claimName"):
                    found_pvc_ref = True
                    break

    if not found_pvc_ref:
        return CheckResult(
            ok=False,
            error="Pod 没有通过 volumes 引用 PVC",
            hints=["在 Pod spec.volumes 中添加 persistentVolumeClaim"],
        )

    # 验证 VolumeSnapshot 引用了 PVC
    vs_name = next(iter(state.volumesnapshots))
    vs = state.volumesnapshots[vs_name]
    vs_spec = vs.get("spec", {})
    if not isinstance(vs_spec, dict):
        return CheckResult(ok=False, error="VolumeSnapshot 缺少 spec", hints=[])

    vs_source = vs_spec.get("source", {})
    if not isinstance(vs_source, dict):
        vs_source = {}
    vs_pvc_ref = vs_source.get("persistentVolumeClaimName", "")

    if not vs_pvc_ref:
        return CheckResult(
            ok=False,
            error="VolumeSnapshot 没有引用 PVC",
            hints=["spec.source.persistentVolumeClaimName 应引用 PVC"],
        )

    if vs_pvc_ref != pvc_name:
        return CheckResult(
            ok=False,
            error=f"VolumeSnapshot 引用的 PVC '{vs_pvc_ref}' 与创建的 PVC '{pvc_name}' 不一致",
            hints=["VolumeSnapshot 应引用同一 YAML 中创建的 PVC"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "动态存储全流程校验通过！在真实集群上验证：",
            "  kubectl get storageclass              # 查看存储类",
            "  kubectl get pvc                       # 查看 PVC 绑定状态",
            "  kubectl get pods                      # 查看 Pod 状态",
            "  kubectl get volumesnapshot            # 查看快照状态",
            "  kubectl describe volumesnapshot <name> # 快照详情",
        ],
    )


LEVEL_Q20_5 = Level(
    id="Q20.5",
    chapter="ch20",
    title="集群实战: 动态存储全流程",
    description="""
# 集群实战: 动态存储全流程 🏗️

将所学存储知识整合，部署一个完整的动态存储工作流！

## 任务

使用多文档 YAML 创建：
1. **StorageClass** — 定义存储类别（CSI 驱动）
2. **PersistentVolumeClaim** — 引用 StorageClass 申请存储
3. **Pod** — 通过 volumes 引用 PVC 使用存储
4. **VolumeSnapshot** — 对 PVC 创建快照

确保各资源之间的引用关系正确：
- PVC 的 `storageClassName` 引用 StorageClass
- Pod 的 `volumes[].persistentVolumeClaim.claimName` 引用 PVC
- VolumeSnapshot 的 `source.persistentVolumeClaimName` 引用 PVC

## 验证步骤

```bash
# 部署
kubectl apply -f storage-workflow.yaml

# 验证 StorageClass
kubectl get sc

# 验证 PVC（等待 Bound）
kubectl get pvc

# 验证 Pod
kubectl get pods

# 验证快照
kubectl get volumesnapshot
kubectl describe volumesnapshot data-snapshot

# 在 Pod 中写入数据
kubectl exec storage-pod -- sh -c "echo 'hello' > /data/test.txt"

# 从快照恢复新 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-pvc
spec:
  storageClassName: ebs-sc
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
  dataSource:
    name: data-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
EOF
```
""",
    starter_yaml="""\
# --- StorageClass ---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
# provisioner: ebs.csi.aws.com
# volumeBindingMode: WaitForFirstConsumer
---
# --- PVC ---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  # storageClassName: ebs-sc
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
# --- Pod ---
apiVersion: v1
kind: Pod
metadata:
  name: storage-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    # volumeMounts:
    # - name: data
    #   mountPath: /data
  # volumes:
  # - name: data
  #   persistentVolumeClaim:
  #     claimName: data-pvc
---
# --- VolumeSnapshot ---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-snapshot
spec:
  # source:
  #   persistentVolumeClaimName: data-pvc
""",
    check_fn=_check_205_full_workflow,
    lesson=Lesson(
        concept="""\
## 动态存储全流程

在生产环境中，一个完整的存储方案通常包含以下组件协同工作：

### 全流程架构

```
┌──────────────────────────────────────────────────────┐
│                     存储全流程                         │
│                                                      │
│  StorageClass  ───▶  PVC  ───▶  PV(自动)  ───▶  Pod  │
│  (存储模板)          (存储申请)    (后端卷)      (消费者)│
│                                                      │
│  VolumeSnapshot  ───▶  VolumeSnapshotContent         │
│  (快照请求)             (后端快照)                     │
│                                                      │
│  VolumeSnapshot  ───▶  新 PVC  ───▶  新 PV  ───▶ Pod │
│  (恢复数据)         (快照恢复)     (新卷)        (消费者)│
└──────────────────────────────────────────────────────┘
```

### 各资源的角色

| 资源 | 角色 | 作用域 | 比喻 |
|------|------|--------|------|
| StorageClass | 模板 | 集群级 | 存储"菜单" |
| PVC | 申请 | 命名空间 | 点"菜单"上的存储 |
| PV | 实体 | 集群级 | 实际的存储设备 |
| Pod | 消费者 | 命名空间 | 使用存储的应用 |
| VolumeSnapshot | 快照请求 | 命名空间 | 对数据拍照 |
| VolumeSnapshotContent | 快照实体 | 集群级 | 后端快照数据 |
| VolumeSnapshotClass | 快照模板 | 集群级 | 快照"菜单" |

### 生产环境最佳实践

1. **数据备份**：定期创建 VolumeSnapshot
2. **恢复测试**：定期从快照恢复验证数据完整性
3. **存储分层**：使用不同 StorageClass 区分 SSD/HDD
4. **配额管理**：通过 ResourceQuota 限制命名空间的存储使用量
5. **CSI 驱动选择**：根据业务需求选择支持快照/扩容/克隆的驱动
6. **监控告警**：监控 PVC 容量使用率，及时扩容

### 卷生命周期管理

```
创建 PVC
  │
  ├─ 动态: CSI 驱动自动创建 PV → 绑定
  ├─ 静态: 匹配已有 PV → 绑定
  │
  ▼
Pod 使用 PVC
  │
  ├─ 创建快照 (VolumeSnapshot)
  ├─ 扩容 (修改 PVC requests.storage)
  ├─ 克隆 (新 PVC dataSource 引用旧 PVC)
  │
  ▼
删除 PVC
  │
  ├─ reclaimPolicy: Delete → PV 和后端卷自动删除
  └─ reclaimPolicy: Retain → PV 保留，后端卷保留
```
""",
        key_fields=[
            {"name": "StorageClass.provisioner", "description": "CSI 驱动名称", "required": True, "example": "ebs.csi.aws.com"},
            {"name": "PVC.storageClassName", "description": "引用 StorageClass", "required": True, "example": "ebs-sc"},
            {"name": "PVC.resources.requests.storage", "description": "申请的存储容量", "required": True, "example": "5Gi"},
            {"name": "Pod.volumes[].persistentVolumeClaim.claimName", "description": "引用 PVC", "required": True, "example": "data-pvc"},
            {"name": "VolumeSnapshot.source.persistentVolumeClaimName", "description": "快照源 PVC", "required": True, "example": "data-pvc"},
        ],
        diagram="""\
  动态存储全流程架构

  ┌─────────────────────────────────────────────────────────┐
  │                     多文档 YAML                         │
  │                                                         │
  │  1. StorageClass (ebs-sc)                               │
  │     provisioner: ebs.csi.aws.com                        │
  │     volumeBindingMode: WaitForFirstConsumer             │
  │                    │                                    │
  │                    │ 引用                                │
  │                    ▼                                    │
  │  2. PVC (data-pvc)                                      │
  │     storageClassName: ebs-sc                            │
  │     accessModes: [ReadWriteOnce]                        │
  │     resources.requests.storage: 5Gi                     │
  │          │                    │                         │
  │          │ 引用                │ 快照                     │
  │          ▼                    ▼                         │
  │  3. Pod (storage-pod)   4. VolumeSnapshot (data-snap)   │
  │     volumes:               source:                      │
  │     - pvc: data-pvc          pvcName: data-pvc          │
  │     volumeMounts:                                        │
  │     - mountPath: /data                                   │
  └─────────────────────────────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                    集群状态                              │
  │                                                         │
  │  StorageClass  ──▶  PVC  ──▶  PV(自动创建)  ──▶  Pod    │
  │  (ebs-sc)          (Bound)   (Bound)          (Running) │
  │                                                         │
  │  VolumeSnapshot ──▶ VolumeSnapshotContent ──▶ 后端快照   │
  │  (data-snapshot)   (snapcontent-xxx)       (snap-xxx)   │
  └─────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- StorageClass ---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc                        # 存储类名称
provisioner: ebs.csi.aws.com          # CSI 驱动
volumeBindingMode: WaitForFirstConsumer  # 延迟绑定
reclaimPolicy: Retain                 # 回收策略: 保留
parameters:
  type: gp3                           # EBS 卷类型
  fsType: ext4                        # 文件系统
---
# --- PVC ---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc                      # PVC 名称
spec:
  storageClassName: ebs-sc            # 引用 StorageClass
  accessModes: [ReadWriteOnce]        # 访问模式
  resources:
    requests:
      storage: 5Gi                    # 申请 5Gi
---
# --- Pod ---
apiVersion: v1
kind: Pod
metadata:
  name: storage-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    volumeMounts:
    - name: data
      mountPath: /data                # 挂载路径
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: data-pvc             # 引用 PVC
---
# --- VolumeSnapshot ---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-snapshot                 # 快照名称
spec:
  source:
    persistentVolumeClaimName: data-pvc  # 快照源 PVC
""",
        common_errors=[
            "PVC 的 storageClassName 与 StorageClass 名称不匹配",
            "Pod 的 volumeMounts 与 volumes 名称不对应",
            "VolumeSnapshot 引用的 PVC 名称与实际创建的 PVC 不一致",
            "多文档 YAML 中资源顺序错误（虽然 K8s 会处理依赖，但引用必须存在）",
        ],
        tips=[
            "用 kubectl get sc,pvc,pod,volumesnapshot 一次性查看所有存储资源",
            "PVC 状态为 Pending 可能是 WaitForFirstConsumer 模式下 Pod 未调度",
            "快照恢复时新 PVC 的容量不能小于源卷",
            "定期创建快照并验证恢复，确保数据安全",
        ],
    ),
)


CHAPTER_20_LEVELS: list[Level] = [
    LEVEL_Q20_1, LEVEL_Q20_2, LEVEL_Q20_3, LEVEL_Q20_4, LEVEL_Q20_5,
]
