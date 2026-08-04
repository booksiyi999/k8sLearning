"""Chapter 21: 集群维护 - etcd 备份恢复/集群升级/节点维护（5 关）

Q21.1 etcd 备份 - validate etcdctl snapshot save command
Q21.2 etcd 恢复 - validate etcdctl snapshot restore
Q21.3 集群升级 - validate kubeadm upgrade plan/apply steps
Q21.4 节点维护 - validate kubectl drain/uncordon workflow
Q21.5 集群实战 - full node maintenance scenario
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q21.1 etcd 备份 ====================

def _check_211_etcd_backup(user_input: str) -> CheckResult:
    """Q21.1 验证 etcdctl snapshot save 备份命令"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 etcdctl 备份命令",
            hints=["使用 etcdctl snapshot save 命令进行备份"],
        )

    # 统一小写处理
    lower = text.lower()

    # 检查包含 etcdctl
    if "etcdctl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 etcdctl",
            hints=["etcd 备份使用 etcdctl 工具"],
        )

    # 检查 snapshot save
    if "snapshot" not in lower or "save" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 snapshot save 子命令",
            hints=["正确格式: etcdctl snapshot save <backup.db>"],
        )

    # 检查 endpoints
    if "--endpoints" not in lower and "endpoints" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 --endpoints 参数",
            hints=["需要指定 etcd 端点，如 --endpoints=https://127.0.0.1:2379"],
        )

    # 检查 cacert / cert / key（TLS 证书）
    has_cacert = "--cacert" in lower
    has_cert = "--cert" in lower
    has_key = "--key" in lower
    if not (has_cacert and has_cert and has_key):
        missing = []
        if not has_cacert:
            missing.append("--cacert")
        if not has_cert:
            missing.append("--cert")
        if not has_key:
            missing.append("--key")
        return CheckResult(
            ok=False,
            error=f"命令中缺少 TLS 证书参数: {', '.join(missing)}",
            hints=["etcd 默认启用 TLS，需要 --cacert, --cert, --key 参数"],
        )

    # 检查输出文件（.db 后缀）
    if ".db" not in lower:
        return CheckResult(
            ok=False,
            error="备份文件缺少 .db 后缀",
            hints=["etcd 快照文件通常以 .db 结尾"],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["etcd 备份成功！定期备份 etcd 是集群灾难恢复的基础 🛡️"],
    )


LEVEL_Q21_1 = Level(
    id="Q21.1",
    chapter="ch21",
    title="etcd 备份",
    description="""
# etcd 备份 🛡️

**etcd** 是 Kubernetes 的核心数据存储，保存了集群所有的状态数据。定期备份 etcd 是灾难恢复的关键。

## 任务

编写一条 `etcdctl snapshot save` 命令，完成以下目标：
- 使用 `etcdctl` 工具
- 执行 `snapshot save` 子命令
- 指定 etcd 端点 `--endpoints=https://127.0.0.1:2379`
- 提供 TLS 证书：`--cacert`, `--cert`, `--key`
- 备份文件保存为 `snapshot.db`

## 提示

etcd 备份命令格式：
```bash
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```
""",
    starter_yaml="""\
# 输入 etcdctl snapshot save 备份命令
# 包含 --endpoints, --cacert, --cert, --key 参数
# 备份文件保存为 snapshot.db
""",
    check_fn=_check_211_etcd_backup,
    lesson=Lesson(
        concept="""\
## etcd 备份

**etcd** 是一个分布式键值存储，Kubernetes 使用它来存储所有集群状态数据。如果 etcd 数据丢失，整个集群的状态将不可恢复。

### 为什么需要备份 etcd

- **灾难恢复**：etcd 损坏时从备份恢复
- **集群迁移**：将集群状态迁移到新环境
- **误操作回滚**：误删除资源后恢复
- **合规要求**：满足数据保护合规标准

### etcdctl snapshot save 命令

```bash
ETCDCTL_API=3 etcdctl snapshot save <备份文件> \
  --endpoints=<etcd地址> \
  --cacert=<CA证书> \
  --cert=<客户端证书> \
  --key=<客户端私钥>
```

### 关键参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `ETCDCTL_API=3` | 指定使用 etcd v3 API | 必须设置 |
| `snapshot save` | 创建快照子命令 | |
| `--endpoints` | etcd 服务器地址 | `https://127.0.0.1:2379` |
| `--cacert` | CA 证书路径 | `/etc/kubernetes/pki/etcd/ca.crt` |
| `--cert` | 客户端证书路径 | `/etc/kubernetes/pki/etcd/server.crt` |
| `--key` | 客户端私钥路径 | `/etc/kubernetes/pki/etcd/server.key` |
""",
        key_fields=[
            {"name": "snapshot save", "description": "etcdctl 快照保存子命令", "required": True, "example": "snapshot save snapshot.db"},
            {"name": "--endpoints", "description": "etcd 服务器端点地址", "required": True, "example": "https://127.0.0.1:2379"},
            {"name": "--cacert", "description": "CA 根证书路径", "required": True, "example": "/etc/kubernetes/pki/etcd/ca.crt"},
            {"name": "--cert", "description": "客户端证书路径", "required": True, "example": "/etc/kubernetes/pki/etcd/server.crt"},
            {"name": "--key", "description": "客户端私钥路径", "required": True, "example": "/etc/kubernetes/pki/etcd/server.key"},
        ],
        diagram="""\
  etcd 备份流程

  ┌──────────────┐     etcdctl snapshot save     ┌──────────────┐
  │  etcd 集群   │ ────────────────────────────► │  snapshot.db │
  │ (3 节点 HA)  │                               │  (备份文件)   │
  └──────────────┘                               └──────────────┘
       │                                               │
       │ TLS 加密通信                                   │ 定期备份
       ▼                                               ▼
  ┌──────────────┐                               ┌──────────────┐
  │   PKI 证书   │                               │  异地存储     │
  │ ca.crt/cert  │                               │  (S3/NFS)    │
  │ server.key   │                               └──────────────┘
  └──────────────┘
""",
        example_yaml="""\
# etcd 备份命令
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 验证备份
ETCDCTL_API=3 etcdctl snapshot status snapshot.db
""",
        common_errors=[
            "忘记设置 ETCDCTL_API=3，默认使用 v2 API 不支持 snapshot",
            "TLS 证书路径错误，导致连接 etcd 失败",
            "未指定 --endpoints，默认连接 localhost 可能不是 etcd 地址",
            "备份文件没有写入权限，导致保存失败",
        ],
        tips=[
            "建议每天至少备份一次 etcd，并保留多个历史版本",
            "将备份文件存储到异地（如 S3），防止单点故障",
            "用 etcdctl snapshot status 验证备份文件完整性",
            "在生产环境定期演练恢复流程，确保备份可用",
        ],
    ),
)


# ==================== Q21.2 etcd 恢复 ====================

def _check_212_etcd_restore(user_input: str) -> CheckResult:
    """Q21.2 验证 etcdctl snapshot restore 恢复命令"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 etcdctl 恢复命令",
            hints=["使用 etcdctl snapshot restore 命令进行恢复"],
        )

    lower = text.lower()

    # 检查 etcdctl
    if "etcdctl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 etcdctl",
            hints=["etcd 恢复使用 etcdctl 工具"],
        )

    # 检查 snapshot restore
    if "snapshot" not in lower or "restore" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 snapshot restore 子命令",
            hints=["正确格式: etcdctl snapshot restore <backup.db>"],
        )

    # 检查 --data-dir
    if "--data-dir" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 --data-dir 参数",
            hints=["恢复时需要指定新的数据目录: --data-dir=/var/lib/etcd-restored"],
        )

    # 检查备份文件 (.db)
    if ".db" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少备份文件（.db 后缀）",
            hints=["需要指定之前备份的快照文件"],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["etcd 恢复成功！恢复后需要重启 etcd 并指向新数据目录 🔄"],
    )


LEVEL_Q21_2 = Level(
    id="Q21.2",
    chapter="ch21",
    title="etcd 恢复",
    description="""
# etcd 恢复 🔄

当 etcd 数据损坏或集群需要回滚时，可以使用之前的快照备份恢复 etcd。

## 任务

编写一条 `etcdctl snapshot restore` 命令：
- 使用 `etcdctl` 工具
- 执行 `snapshot restore` 子命令
- 指定备份文件 `snapshot.db`
- 指定恢复后的数据目录 `--data-dir=/var/lib/etcd-restored`

## 提示

etcd 恢复命令格式：
```bash
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restored
```
""",
    starter_yaml="""\
# 输入 etcdctl snapshot restore 恢复命令
# 指定备份文件和 --data-dir 参数
""",
    check_fn=_check_212_etcd_restore,
    lesson=Lesson(
        concept="""\
## etcd 恢复

`etcdctl snapshot restore` 从快照文件恢复 etcd 数据到指定目录。恢复过程是**离线操作**——需要先停止 etcd 服务。

### 恢复流程

```
1. 停止 etcd 服务（所有控制平面节点）
2. 备份当前 etcd 数据目录（以防万一）
3. 执行 snapshot restore 到新目录
4. 修改 etcd 配置指向新数据目录
5. 重启 etcd 服务
6. 验证集群状态
```

### 恢复命令

```bash
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \\
  --data-dir=/var/lib/etcd-restored
```

### 多节点集群恢复

在 HA 集群中，每个 etcd 节点都需要独立恢复：
- 每个节点使用相同的快照文件
- 每个节点指定不同的 `--name` 和 `--initial-advertise-peer-urls`
- 使用 `--initial-cluster` 指定所有成员

### 注意事项

- **必须先停止 etcd**：恢复时 etcd 不能在运行
- **数据目录必须是空或不存在**：恢复会创建新目录
- **恢复后需要更新 etcd 配置**：将 `--data-dir` 指向新目录
""",
        key_fields=[
            {"name": "snapshot restore", "description": "etcdctl 快照恢复子命令", "required": True, "example": "snapshot restore snapshot.db"},
            {"name": "--data-dir", "description": "恢复后的数据目录路径", "required": True, "example": "/var/lib/etcd-restored"},
            {"name": "--name", "description": "etcd 成员名称（多节点恢复时）", "required": False, "example": "etcd-node-1"},
            {"name": "--initial-cluster", "description": "初始集群成员列表（多节点恢复时）", "required": False, "example": "etcd-node-1=https://10.0.0.1:2380"},
        ],
        diagram="""\
  etcd 恢复流程

  ┌──────────────┐    snapshot restore     ┌────────────────────┐
  │  snapshot.db │ ──────────────────────► │ /var/lib/etcd-     │
  │  (备份文件)  │   --data-dir=...        │ restored (新目录)   │
  └──────────────┘                         └─────────┬──────────┘
                                                       │
                                            修改配置 & 重启
                                                       ▼
                                             ┌──────────────────┐
                                             │   etcd 服务      │
                                             │  (使用新数据)     │
                                             └──────────────────┘
""",
        example_yaml="""\
# 1. 停止 etcd
systemctl stop etcd

# 2. 恢复快照
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \\
  --data-dir=/var/lib/etcd-restored

# 3. 修改 etcd 配置指向新目录
# 编辑 /etc/kubernetes/manifests/etcd.yaml 中 --data-dir

# 4. 重启 etcd
systemctl start etcd

# 5. 验证
ETCDCTL_API=3 etcdctl endpoint health \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key
""",
        common_errors=[
            "恢复时未先停止 etcd 服务，导致数据冲突",
            "--data-dir 指向非空目录，恢复失败",
            "恢复后忘记修改 etcd 配置文件指向新目录",
            "在 HA 集群中只在单个节点恢复，未在所有成员上执行",
        ],
        tips=[
            "恢复前务必备份当前数据目录作为保险",
            "多节点集群恢复时使用 --initial-cluster-token 避免加入旧集群",
            "恢复后用 etcdctl endpoint health 验证集群健康",
            "定期进行恢复演练，验证备份的可用性",
        ],
    ),
)


# ==================== Q21.3 集群升级 ====================

def _check_213_cluster_upgrade(user_input: str) -> CheckResult:
    """Q21.3 验证 kubeadm upgrade plan/apply 步骤"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入集群升级命令",
            hints=["集群升级使用 kubeadm upgrade 命令"],
        )

    lower = text.lower()

    # 检查 kubeadm
    if "kubeadm" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubeadm",
            hints=["集群升级使用 kubeadm upgrade 命令"],
        )

    # 检查 upgrade 子命令
    if "upgrade" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 upgrade 子命令",
            hints=["使用 kubeadm upgrade plan/apply 进行升级"],
        )

    # 检查 plan 或 apply
    has_plan = "plan" in lower
    has_apply = "apply" in lower
    if not has_plan and not has_apply:
        return CheckResult(
            ok=False,
            error="命令中缺少 plan 或 apply 子命令",
            hints=["先用 kubeadm upgrade plan 检查，再用 kubeadm upgrade apply 升级"],
        )

    # 如果是 apply，检查版本号
    if has_apply:
        import re
        version_match = re.search(r'v?\d+\.\d+\.\d+', text)
        if not version_match:
            return CheckResult(
                ok=False,
                error="kubeadm upgrade apply 需要指定目标版本号",
                hints=["如: kubeadm upgrade apply v1.28.0"],
            )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["集群升级流程正确！升级前务必备份 etcd ⬆️"],
    )


LEVEL_Q21_3 = Level(
    id="Q21.3",
    chapter="ch21",
    title="集群升级",
    description="""
# 集群升级 ⬆️

Kubernetes 集群升级是维护中的重要操作。使用 `kubeadm` 可以安全地升级控制平面和工作节点。

## 任务

编写集群升级命令，完成以下目标之一：
- 使用 `kubeadm upgrade plan` 检查可升级版本
- 或使用 `kubeadm upgrade apply v1.28.0` 执行升级

## 提示

升级流程：
```bash
# 1. 检查可升级版本
kubeadm upgrade plan

# 2. 升级控制平面
kubeadm upgrade apply v1.28.0

# 3. 升级 kubelet/kubectl
apt-get install kubelet=1.28.0-00 kubectl=1.28.0-00
```
""",
    starter_yaml="""\
# 输入 kubeadm upgrade 命令
# kubeadm upgrade plan 或 kubeadm upgrade apply <version>
""",
    check_fn=_check_213_cluster_upgrade,
    lesson=Lesson(
        concept="""\
## Kubernetes 集群升级

使用 `kubeadm` 升级 Kubernetes 集群是一个多步骤过程，需要按正确顺序操作。

### 升级顺序

```
1. 升级 kubeadm 工具
2. kubeadm upgrade plan（检查可升级版本）
3. kubeadm upgrade apply v<x.y.z>（升级控制平面）
4. 升级控制平面节点的 kubelet 和 kubectl
5. 升级工作节点（逐个进行）
   a. 驱逐节点 (kubectl drain)
   b. 升级 kubeadm
   c. kubeadm upgrade node
   d. 升级 kubelet
   e. 恢复节点 (kubectl uncordon)
6. 验证集群状态
```

### 版本兼容性

- 次版本号最多差 1（如 1.27 → 1.28 可以，1.27 → 1.29 不行）
- kubelet 不能高于 API Server 版本
- kubelet 可以比 API Server 低最多 3 个次版本

### 关键命令

| 命令 | 说明 |
|------|------|
| `kubeadm upgrade plan` | 检查当前版本和可升级版本 |
| `kubeadm upgrade apply v1.28.0` | 升级控制平面到指定版本 |
| `kubeadm upgrade node` | 升级工作节点 |
| `kubectl drain <node>` | 驱逐节点上的 Pod |
| `kubectl uncordon <node>` | 恢复节点调度 |
""",
        key_fields=[
            {"name": "kubeadm upgrade plan", "description": "检查可升级的版本列表", "required": True, "example": "kubeadm upgrade plan"},
            {"name": "kubeadm upgrade apply", "description": "执行控制平面升级", "required": True, "example": "kubeadm upgrade apply v1.28.0"},
            {"name": "kubeadm upgrade node", "description": "升级工作节点", "required": False, "example": "kubeadm upgrade node"},
            {"name": "version", "description": "目标版本号", "required": True, "example": "v1.28.0"},
        ],
        diagram="""\
  Kubernetes 集群升级流程

  ┌──────────────────────────────────────────────────┐
  │  1. 升级前准备                                    │
  │     • 备份 etcd    • 检查集群健康    • 查看版本   │
  └──────────────────────┬───────────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  2. 升级 kubeadm                                  │
  │     apt-get install kubeadm=1.28.0-00            │
  └──────────────────────┬───────────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  3. 升级控制平面                                  │
  │     kubeadm upgrade plan                         │
  │     kubeadm upgrade apply v1.28.0                │
  └──────────────────────┬───────────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  4. 升级 kubelet & kubectl                       │
  │     apt-get install kubelet=1.28.0-00            │
  │     systemctl restart kubelet                    │
  └──────────────────────┬───────────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  5. 逐个升级工作节点                              │
  │     kubectl drain → kubeadm upgrade node         │
  │     → 升级 kubelet → kubectl uncordon             │
  └──────────────────────┬───────────────────────────┘
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  6. 验证                                          │
  │     kubectl get nodes  →  所有节点 Ready          │
  └──────────────────────────────────────────────────┘
""",
        example_yaml="""\
# 1. 升级 kubeadm
apt-get install -y kubeadm=1.28.0-00

# 2. 检查升级计划
kubeadm upgrade plan

# 3. 升级控制平面
kubeadm upgrade apply v1.28.0

# 4. 升级 kubelet 和 kubectl
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
systemctl restart kubelet

# 5. 验证
kubectl get nodes
""",
        common_errors=[
            "跳过 plan 步骤直接 apply，版本不兼容导致升级失败",
            "升级跨度太大（跨多个次版本），需要逐版本升级",
            "未先升级 kubeadm 就执行 upgrade apply",
            "升级工作节点时未先 drain，导致服务中断",
        ],
        tips=[
            "升级前务必备份 etcd，以防升级失败需要回滚",
            "一次只升级一个次版本（1.27→1.28→1.29）",
            "升级工作节点时要逐个进行，确保最小化影响",
            "升级后用 kubectl get nodes 确认所有节点版本一致",
        ],
    ),
)


# ==================== Q21.4 节点维护 ====================

def _check_214_node_maintenance(user_input: str) -> CheckResult:
    """Q21.4 验证 kubectl drain/uncordon 节点维护流程"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入节点维护命令",
            hints=["节点维护使用 kubectl drain 和 uncordon 命令"],
        )

    lower = text.lower()

    # 检查 kubectl
    if "kubectl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["节点维护使用 kubectl drain/uncordon 命令"],
        )

    # 检查 drain
    has_drain = "drain" in lower
    has_uncordon = "uncordon" in lower

    if not has_drain:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl drain",
            hints=["维护前需要先驱逐节点: kubectl drain <node>"],
        )

    # 检查 drain 的关键参数
    has_ignore_daemonsets = "--ignore-daemonsets" in lower
    has_delete_emptydir = "--delete-emptydir-data" in lower or "--delete-local-data" in lower

    if not has_ignore_daemonsets:
        return CheckResult(
            ok=False,
            error="drain 命令缺少 --ignore-daemonsets 参数",
            hints=["DaemonSet Pod 不会被驱逐，需要 --ignore-daemonsets 参数"],
        )

    if not has_delete_emptydir:
        return CheckResult(
            ok=False,
            error="drain 命令缺少 --delete-emptydir-data 参数",
            hints=["使用 --delete-emptydir-data 允许删除 emptyDir 数据的 Pod"],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["节点维护流程正确！drain + 维护 + uncordon 是标准流程 🔧"],
    )


LEVEL_Q21_4 = Level(
    id="Q21.4",
    chapter="ch21",
    title="节点维护",
    description="""
# 节点维护 🔧

在维护节点时（如升级内核、更换硬件），需要安全地将 Pod 迁移到其他节点。

## 任务

编写节点维护命令，完成以下目标：
- 使用 `kubectl drain <node>` 驱逐节点上的 Pod
- 添加 `--ignore-daemonsets` 参数（保留 DaemonSet Pod）
- 添加 `--delete-emptydir-data` 参数（允许删除 emptyDir 数据）

## 提示

节点维护流程：
```bash
# 1. 驱逐节点
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# 2. 执行维护操作...

# 3. 恢复节点
kubectl uncordon worker-1
```
""",
    starter_yaml="""\
# 输入 kubectl drain 命令
# 包含 --ignore-daemonsets 和 --delete-emptydir-data 参数
""",
    check_fn=_check_214_node_maintenance,
    lesson=Lesson(
        concept="""\
## 节点维护：drain 与 uncordon

在 Kubernetes 中对节点进行维护时，需要先安全地驱逐节点上的工作负载，维护完成后再恢复调度。

### drain 的工作流程

`kubectl drain` 会：
1. 将节点标记为 **unschedulable**（SchedulingDisabled）
2. **驱逐（evict）** 节点上所有非 DaemonSet、非 mirror Pod 的 Pod
3. Pod 会根据 Deployment/ReplicaSet 在其他节点上重新创建

### 关键参数

| 参数 | 说明 |
|------|------|
| `--ignore-daemonsets` | 忽略 DaemonSet Pod（它们通常需要留在节点上） |
| `--delete-emptydir-data` | 允许删除使用 emptyDir 的 Pod |
| `--force` | 强制驱逐（即使 Pod 未被控制器管理） |
| `--grace-period=-1` | 使用 Pod 指定的优雅终止时间 |
| `--timeout` | 等待驱逐的超时时间 |

### uncordon 恢复调度

维护完成后使用 `kubectl uncordon <node>` 恢复节点调度。注意：
- uncordon 只是恢复调度，**不会** 将 Pod 迁回
- 新创建的 Pod 可能会被调度到该节点
- 已迁移到其他节点的 Pod 不会自动迁回

### drain vs cordon

| 操作 | 效果 |
|------|------|
| `kubectl cordon <node>` | 标记为不可调度，**不驱逐** Pod |
| `kubectl drain <node>` | 标记为不可调度 **+** 驱逐 Pod |
| `kubectl uncordon <node>` | 恢复可调度 |
""",
        key_fields=[
            {"name": "kubectl drain", "description": "驱逐节点上的 Pod 并标记为不可调度", "required": True, "example": "kubectl drain worker-1"},
            {"name": "--ignore-daemonsets", "description": "忽略 DaemonSet Pod，不驱逐它们", "required": True, "example": "--ignore-daemonsets"},
            {"name": "--delete-emptydir-data", "description": "允许删除使用 emptyDir 卷的 Pod", "required": True, "example": "--delete-emptydir-data"},
            {"name": "kubectl uncordon", "description": "恢复节点调度", "required": False, "example": "kubectl uncordon worker-1"},
        ],
        diagram="""\
  节点维护流程

  ┌──────────────────────────────────────────────────┐
  │  正常状态                                         │
  │  worker-1: Ready, schedulable                    │
  │  ┌──────┐ ┌──────┐ ┌──────┐                     │
  │  │ Pod A│ │ Pod B│ │ Pod C│                     │
  │  └──────┘ └──────┘ └──────┘                     │
  └──────────────────────┬───────────────────────────┘
                         │ kubectl drain worker-1
                         │ --ignore-daemonsets
                         │ --delete-emptydir-data
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  drain 后                                         │
  │  worker-1: Ready,SchedulingDisabled             │
  │  (Pod 被驱逐，在其他节点重建)                      │
  │                                                  │
  │  worker-2: ┌──────┐ ┌──────┐ ┌──────┐           │
  │            │ Pod A│ │ Pod B│ │ Pod C│           │
  │            └──────┘ └──────┘ └──────┘           │
  └──────────────────────┬───────────────────────────┘
                         │ 维护操作...
                         │ kubectl uncordon worker-1
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  恢复调度                                         │
  │  worker-1: Ready, schedulable                    │
  │  (新 Pod 可能调度到此节点)                         │
  └──────────────────────────────────────────────────┘
""",
        example_yaml="""\
# 1. 驱逐节点
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# 2. 执行维护操作（升级内核、更换磁盘等）
# ...

# 3. 恢复节点调度
kubectl uncordon worker-1

# 4. 验证节点状态
kubectl get nodes
""",
        common_errors=[
            "忘记 --ignore-daemonsets，导致 drain 被 DaemonSet Pod 阻塞",
            "忘记 --delete-emptydir-data，有 emptyDir 的 Pod 无法驱逐",
            "维护完成后忘记 uncordon，节点一直不可调度",
            "对没有足够资源承载迁移 Pod 的集群执行 drain",
        ],
        tips=[
            "drain 前用 kubectl get pods -o wide 检查节点上的工作负载",
            "使用 PDB (PodDisruptionBudget) 确保驱逐时维持最小可用副本数",
            "对生产节点逐个 drain，避免同时影响多个节点",
            "uncordon 后不会自动迁移 Pod 回来，新 Pod 才可能调度到该节点",
        ],
    ),
)


# ==================== Q21.5 集群实战 - 完整节点维护场景 ====================

def _check_215_full_maintenance(user_input: str) -> CheckResult:
    """Q21.5 完整节点维护场景 - 验证 drain + 修复 + uncordon 全流程"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入完整的节点维护流程命令",
            hints=["完整流程: drain → 维护 → uncordon"],
        )

    lower = text.lower()

    # 检查包含完整流程
    has_drain = "drain" in lower
    has_uncordon = "uncordon" in lower
    has_kubectl = "kubectl" in lower

    if not has_kubectl:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["使用 kubectl 执行 drain 和 uncordon"],
        )

    if not has_drain:
        return CheckResult(
            ok=False,
            error="缺少 drain 步骤",
            hints=["维护前先 drain 节点: kubectl drain <node> --ignore-daemonsets"],
        )

    if not has_uncordon:
        return CheckResult(
            ok=False,
            error="缺少 uncordon 步骤",
            hints=["维护后恢复节点: kubectl uncordon <node>"],
        )

    # 检查 drain 参数
    if "--ignore-daemonsets" not in lower:
        return CheckResult(
            ok=False,
            error="drain 命令缺少 --ignore-daemonsets",
            hints=["drain 需要 --ignore-daemonsets 参数"],
        )

    # 检查包含节点名称
    if "worker" not in lower and "node" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少目标节点名称",
            hints=["指定要维护的节点名，如 worker-1"],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["完整节点维护流程正确！这就是生产环境的标准操作 🏆"],
    )


LEVEL_Q21_5 = Level(
    id="Q21.5",
    chapter="ch21",
    title="集群实战 - 完整节点维护",
    description="""
# 集群实战 - 完整节点维护 🏆

将前面学到的节点维护知识综合运用，完成一个完整的节点维护流程。

## 场景

生产集群中 `worker-1` 节点需要升级内核，请编写完整的维护流程命令：
1. 使用 `kubectl drain` 安全驱逐节点
2. 添加 `--ignore-daemonsets` 参数
3. 使用 `kubectl uncordon` 恢复节点

## 提示

完整维护流程：
```bash
# 驱逐节点
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# ... 执行维护操作 ...

# 恢复节点
kubectl uncordon worker-1
```
""",
    starter_yaml="""\
# 输入完整的节点维护流程命令
# 1. kubectl drain worker-1 --ignore-daemonsets ...
# 2. kubectl uncordon worker-1
""",
    check_fn=_check_215_full_maintenance,
    lesson=Lesson(
        concept="""\
## 完整节点维护实战

在生产环境中，节点维护是一个需要谨慎操作的流程。以下是标准的维护流程：

### 维护前检查

1. **检查节点状态**：`kubectl get nodes` 确认节点健康
2. **检查工作负载**：`kubectl get pods -o wide --field-selector spec.nodeName=worker-1`
3. **检查 PDB**：确保有 PodDisruptionBudget 保护关键应用
4. **检查集群容量**：确保其他节点有足够资源接收迁移的 Pod

### 维护流程

```
1. kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data
   → Pod 被驱逐，在其他节点重建

2. 等待所有 Pod 在其他节点 Running
   → kubectl get pods -o wide --field-selector spec.nodeName!=worker-1

3. 执行维护操作
   → 升级内核 / 更换硬件 / 清理磁盘等

4. kubectl uncordon worker-1
   → 恢复节点调度

5. 验证集群状态
   → kubectl get nodes（确认 worker-1 Ready）
```

### 生产环境最佳实践

- **维护窗口**：在低峰期执行维护
- **逐个节点**：一次只维护一个节点
- **监控告警**：维护期间密切关注监控
- **回滚计划**：准备维护失败的回滚方案
- **通知团队**：维护前通知相关团队
""",
        key_fields=[
            {"name": "kubectl drain", "description": "驱逐节点 Pod 并标记不可调度", "required": True, "example": "kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data"},
            {"name": "kubectl uncordon", "description": "恢复节点调度", "required": True, "example": "kubectl uncordon worker-1"},
            {"name": "维护操作", "description": "在 drain 和 uncordon 之间执行的维护", "required": False, "example": "apt-get upgrade"},
        ],
        diagram="""\
  完整节点维护流程

  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  检查集群   │ ──► │  drain 节点  │ ──► │  等待 Pod   │
  │  容量 & PDB │     │  worker-1   │     │  迁移完成   │
  └─────────────┘     └─────────────┘     └──────┬──────┘
                                                   │
                                                   ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  uncordon   │ ◄── │  验证节点   │ ◄── │  执行维护   │
  │  恢复调度   │     │  状态       │     │  操作       │
  └─────────────┘     └─────────────┘     └─────────────┘
""",
        example_yaml="""\
# 完整节点维护流程

# 1. 检查集群状态
kubectl get nodes
kubectl get pods -o wide --field-selector spec.nodeName=worker-1

# 2. 驱逐节点
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# 3. 等待 Pod 迁移
kubectl get pods -o wide --watch

# 4. 执行维护（如升级内核）
apt-get update && apt-get upgrade -y
reboot

# 5. 恢复节点调度
kubectl uncordon worker-1

# 6. 验证
kubectl get nodes
kubectl get pods -o wide
""",
        common_errors=[
            "同时 drain 多个节点，导致集群容量不足",
            "维护后忘记 uncordon，节点长期不可调度",
            "未检查 PDB，drain 时导致服务不可用",
            "维护后未验证节点和 Pod 状态就结束",
        ],
        tips=[
            "维护前用 kubectl describe node 检查节点详情",
            "对关键应用配置 PDB，确保 drain 时维持最小副本数",
            "维护后用 kubectl get nodes 确认所有节点 Ready",
            "记录维护操作日志，便于后续审计和问题追踪",
        ],
    ),
)


# ==================== Chapter 21 Levels ====================

CHAPTER_21_LEVELS: list[Level] = [
    LEVEL_Q21_1, LEVEL_Q21_2, LEVEL_Q21_3, LEVEL_Q21_4, LEVEL_Q21_5,
]
