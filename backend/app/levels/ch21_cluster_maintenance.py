"""Chapter 21: 集群维护 - etcd 备份恢复/证书续期/集群升级/综合实战（5 关）

Q21.1 etcd 备份 - validate etcdctl snapshot save command
Q21.2 etcd 恢复 - validate etcdctl snapshot restore
Q21.3 证书续期 - validate kubeadm certs renew
Q21.4 kubeadm upgrade - validate kubeadm upgrade plan/apply
Q21.5 集群实战 - comprehensive backup + restore + upgrade scenario
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
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
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
## etcd 备份原理

**etcd** 是一个分布式键值存储（基于 Raft 共识算法），Kubernetes 使用它来存储**所有**集群状态数据——包括 Pod、Service、ConfigMap、Secret、Deployment 等全部资源对象。如果 etcd 数据丢失，整个集群的状态将不可恢复。

### 为什么需要备份 etcd

- **灾难恢复**：etcd 损坏或数据被误删时，可从快照恢复
- **集群迁移**：将集群状态迁移到新环境
- **误操作回滚**：误删除资源（如 `kubectl delete namespace`）后恢复
- **合规要求**：满足数据保护合规标准（如等保、GDPR）

### etcdctl snapshot save 工作原理

`etcdctl snapshot save` 命令通过 etcd 的 v3 API 向 etcd 服务器发送快照请求。etcd 服务器内部会：

1. **暂停写操作**：短暂暂停写入，确保数据一致性
2. **读取数据**：从 etcd 的后端存储（bbolt 数据库）读取所有键值对
3. **写入快照文件**：将数据序列化写入指定的 `.db` 文件
4. **恢复写操作**：恢复正常的读写服务

整个过程对集群的影响极小（通常毫秒级暂停），但保证了快照的数据一致性。

### 关键参数详解

| 参数 | 说明 | 为什么需要 |
|------|------|------------|
| `ETCDCTL_API=3` | 指定使用 etcd v3 API | etcd v2 不支持 snapshot，必须显式指定 v3 |
| `snapshot save` | 创建快照子命令 | etcdctl 的核心备份操作 |
| `--endpoints` | etcd 服务器地址 | 生产环境 etcd 通常监听 2379 端口，需要指定 |
| `--cacert` | CA 根证书路径 | etcd 默认启用 mTLS，需要 CA 证书验证服务器身份 |
| `--cert` | 客户端证书路径 | etcd 要求双向 TLS 认证，客户端也需要提供证书 |
| `--key` | 客户端私钥路径 | 配合 `--cert` 使用的私钥文件 |

### TLS 证书路径（kubeadm 部署的集群）

```
/etc/kubernetes/pki/etcd/
├── ca.crt          ← --cacert
├── server.crt      ← --cert（或 healthcheck-client.crt）
├── server.key      ← --key
├── peer.crt        ← 节点间通信证书
├── peer.key
└── apiserver-etcd-client.crt  ← kube-apiserver 访问 etcd 的证书
```

### 验证备份

```bash
# 查看快照状态（验证备份完整性）
ETCDCTL_API=3 etcdctl snapshot status snapshot.db -w table

# 输出示例：
# +----------+----------+------------+------------+
# |   HASH   | REVISION | TOTAL KEYS | TOTAL SIZE |
# +----------+----------+------------+------------+
# | 0x2e8bf6 |     1234 |        567 |     2.1 MB |
# +----------+----------+------------+------------+
```
""",
        key_fields=[
            {"name": "ETCDCTL_API=3", "description": "必须设置为 v3 API，v2 不支持 snapshot", "required": True, "example": "ETCDCTL_API=3"},
            {"name": "snapshot save", "description": "etcdctl 快照保存子命令", "required": True, "example": "snapshot save snapshot.db"},
            {"name": "--endpoints", "description": "etcd 服务器端点地址，生产环境可能不是 localhost", "required": True, "example": "https://127.0.0.1:2379"},
            {"name": "--cacert", "description": "CA 根证书路径，用于验证 etcd 服务器身份", "required": True, "example": "/etc/kubernetes/pki/etcd/ca.crt"},
            {"name": "--cert", "description": "客户端证书路径，etcd 要求 mTLS 双向认证", "required": True, "example": "/etc/kubernetes/pki/etcd/server.crt"},
            {"name": "--key", "description": "客户端私钥路径，配合 --cert 使用", "required": True, "example": "/etc/kubernetes/pki/etcd/server.key"},
        ],
        diagram="""\
  etcd 快照备份原理

  ┌─────────────────────────────────────────────────────────────┐
  │  etcdctl snapshot save snapshot.db                         │
  │                                                             │
  │  1. 通过 TLS 连接到 etcd                                    │
  │     ┌─────────┐    mTLS (cacert/cert/key)    ┌───────────┐ │
  │     │etcdctl  │ ◄──────────────────────────► │  etcd     │ │
  │     │ client  │    https://127.0.0.1:2379    │  server   │ │
  │     └─────────┘                               └─────┬─────┘ │
  │                                                     │       │
  │  2. etcd 内部执行:                                   │       │
  │     ┌─────────────────────────────────────────────────┤      │
  │     │ a. 短暂暂停写操作（保证一致性）                  │      │
  │     │ b. 读取 bbolt 后端存储的全部 KV 数据             │      │
  │     │ c. 序列化写入快照文件                            │      │
  │     │ d. 恢复写操作                                    │      │
  │     └─────────────────────────────────────────────────┘      │
  │                     │                                       │
  │  3. 生成快照文件     ▼                                       │
  │     ┌──────────────────────────────┐                        │
  │     │  snapshot.db                  │                        │
  │     │  ├─ HASH: 0x2e8bf6            │                        │
  │     │  ├─ REVISION: 1234            │                        │
  │     │  ├─ TOTAL KEYS: 567           │                        │
  │     │  └─ SIZE: 2.1 MB              │                        │
  │     └──────────────┬───────────────┘                        │
  │                    │                                        │
  │  4. 异地存储        ▼                                        │
  │     ┌──────────────────────────────┐                        │
  │     │  S3 / NFS / 备份服务器         │                        │
  │     │  （防止单点故障）              │                        │
  │     └──────────────────────────────┘                        │
  └─────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# etcd 备份完整命令
# 在控制平面节点上执行（etcd 通常运行在此）

# 方法一：设置环境变量
export ETCDCTL_API=3

etcdctl snapshot save snapshot.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 方法二：内联环境变量
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 验证备份文件完整性
ETCDCTL_API=3 etcdctl snapshot status snapshot.db -w table
""",
        common_errors=[
            "忘记设置 ETCDCTL_API=3，默认使用 v2 API 不支持 snapshot save",
            "TLS 证书路径错误（如写成 /etc/etcd/ssl/ 而非 /etc/kubernetes/pki/etcd/），导致连接 etcd 失败",
            "使用 healthcheck-client.crt 而非 server.crt 作为 --cert，部分 etcd 版本会拒绝",
            "未指定 --endpoints，默认连接 localhost:2379 但生产环境 etcd 可能监听其他地址",
            "备份文件没有写入权限（如 /etc/kubernetes/pki/etcd/ 目录），导致保存失败",
            "未验证备份文件就认为备份成功，可能文件已损坏",
        ],
        tips=[
            "建议每天至少备份一次 etcd，并保留多个历史版本（如保留 7 天）",
            "将备份文件存储到异地（如 S3、NFS），防止单点故障",
            "用 `etcdctl snapshot status snapshot.db -w table` 验证备份文件完整性和大小",
            "在生产环境定期演练恢复流程，确保备份可用（很多团队备份成功但从未验证恢复）",
            "使用 CronJob 或外部脚本自动化备份，避免手动操作遗漏",
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
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \\
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
> **风险警告**: 本节涉及 etcd 数据操作等破坏性操作。
> - **切勿在生产集群上练习**，请使用专用学习集群
> - `mv /var/lib/etcd` 会停止 etcd 服务，导致集群不可用
> - `kubeadm upgrade` 不可回滚，操作前必须完整备份
> - 建议先在模拟器模式完成本章学习，再在隔离环境中实操

## etcd 恢复原理

`etcdctl snapshot restore` 从快照文件恢复 etcd 数据到指定目录。与备份不同，恢复是一个**离线操作**——必须先停止 etcd 服务。

### 为什么恢复必须离线

etcd 使用 bbolt 数据库作为后端存储。如果 etcd 正在运行并持有 bbolt 文件的写锁，`snapshot restore` 会因为文件锁定而失败。此外，恢复的数据会覆盖 etcd 的内存状态，如果 etcd 仍在运行会导致数据不一致。

### 完整恢复流程（6 步）

```
步骤 1: 停止 etcd 服务（所有控制平面节点）
         ↓
步骤 2: 备份当前 etcd 数据目录（保险措施）
         ↓
步骤 3: 执行 snapshot restore 到新目录
         ↓
步骤 4: 修改 etcd 配置指向新数据目录
         ↓
步骤 5: 重启 etcd 服务
         ↓
步骤 6: 验证集群状态
```

### 各步骤详解

**步骤 1：停止 etcd**

kubeadm 部署的集群中，etcd 以 Static Pod 形式运行：
```bash
# 方法一：移动 etcd static pod manifest（推荐）
mv /etc/kubernetes/manifests/etcd.yaml /tmp/etcd.yaml.bak

# 方法二：如果是 systemd 管理的 etcd
systemctl stop etcd
```

**步骤 2：备份当前数据目录**
```bash
# 备份现有数据（以防恢复失败可以回退）
mv /var/lib/etcd /var/lib/etcd.bak.$(date +%Y%m%d)
```

**步骤 3：执行恢复**
```bash
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \\
  --data-dir=/var/lib/etcd
```

恢复过程会：
- 读取快照文件中的所有 KV 数据
- 创建新的 bbolt 数据库文件
- 将数据写入 `/var/lib/etcd/member/snap/db`

**步骤 4：修改配置（仅 Static Pod 方式需要）**

如果步骤 1 移动了 manifest，需要恢复：
```bash
mv /tmp/etcd.yaml.bak /etc/kubernetes/manifests/etcd.yaml
```

确保 etcd manifest 中的 `--data-dir` 指向恢复的数据目录。

**步骤 5：重启 etcd**
```bash
# Static Pod 方式：kubelet 会自动检测 manifest 并重启 etcd
# systemd 方式：
systemctl start etcd

# 等待 etcd 就绪
sleep 5
```

**步骤 6：验证集群状态**
```bash
# 检查 etcd 端点健康
ETCDCTL_API=3 etcdctl endpoint health \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 检查 Kubernetes 集群状态
kubectl get nodes
kubectl get pods -A
```

### 多节点 HA 集群恢复

在 HA 集群（3+ etcd 节点）中，恢复流程更复杂：

- 每个节点都需要使用**相同的快照文件**独立恢复
- 恢复时需要指定 `--name`、`--initial-advertise-peer-urls`、`--initial-cluster`
- 使用 `--initial-cluster-token` 避免加入旧集群

```bash
# 在每个节点上执行（以 node-1 为例）
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \\
  --data-dir=/var/lib/etcd \\
  --name=etcd-node-1 \\
  --initial-advertise-peer-urls=https://10.0.0.1:2380 \\
  --initial-cluster=etcd-node-1=https://10.0.0.1:2380,etcd-node-2=https://10.0.0.2:2380,etcd-node-3=https://10.0.0.3:2380 \\
  --initial-cluster-token=new-cluster-token
```

### 恢复注意事项

- **必须先停止 etcd**：运行中的 etcd 持有文件锁
- **数据目录必须为空或不存在**：restore 会创建新目录
- **恢复后 etcd 会丢失快照之后的所有变更**：这是预期行为
- **kube-apiserver 会自动重连**：etcd 重启后 apiserver 自动恢复连接
""",
        key_fields=[
            {"name": "snapshot restore", "description": "etcdctl 快照恢复子命令，从 .db 文件恢复数据", "required": True, "example": "snapshot restore snapshot.db"},
            {"name": "--data-dir", "description": "恢复后的数据目录路径，必须为空或不存在", "required": True, "example": "/var/lib/etcd-restored"},
            {"name": "--name", "description": "etcd 成员名称（多节点恢复时必须指定）", "required": False, "example": "etcd-node-1"},
            {"name": "--initial-cluster", "description": "初始集群成员列表（多节点恢复时必须指定）", "required": False, "example": "etcd-node-1=https://10.0.0.1:2380,etcd-node-2=https://10.0.0.2:2380"},
            {"name": "--initial-cluster-token", "description": "集群令牌，避免加入旧集群（多节点恢复时）", "required": False, "example": "new-cluster-token"},
        ],
        diagram="""\
  etcd 恢复完整流程

  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 1: 停止 etcd 服务                                      │
  │                                                              │
  │  Static Pod 方式:               systemd 方式:                │
  │  mv /etc/kubernetes/            systemctl stop etcd          │
  │     manifests/etcd.yaml                                      │
  │  /tmp/etcd.yaml.bak                                         │
  │                                                              │
  │  → etcd 停止运行，释放文件锁                                  │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 2: 备份当前数据目录（保险措施）                          │
  │                                                              │
  │  mv /var/lib/etcd /var/lib/etcd.bak.20240101                │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 3: 执行 snapshot restore                               │
  │                                                              │
  │  ETCDCTL_API=3 etcdctl snapshot restore snapshot.db         │
  │    --data-dir=/var/lib/etcd                                  │
  │                                                              │
  │  ┌──────────┐    读取快照     ┌────────────────────────┐    │
  │  │snapshot  │ ──────────────► │ /var/lib/etcd/         │    │
  │  │.db       │   反序列化      │   member/snap/db       │    │
  │  │(备份)    │   写入 bbolt    │   (新的 bbolt 数据库)   │    │
  │  └──────────┘                 └────────────────────────┘    │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 4: 恢复 etcd 配置                                      │
  │                                                              │
  │  mv /tmp/etcd.yaml.bak /etc/kubernetes/manifests/etcd.yaml  │
  │  → 确认 --data-dir 指向恢复目录                              │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 5: 重启 etcd                                           │
  │                                                              │
  │  Static Pod: kubelet 自动检测 manifest 并启动 etcd           │
  │  systemd:    systemctl start etcd                            │
  │  → 等待 5 秒让 etcd 完成初始化                                │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 6: 验证集群状态                                        │
  │                                                              │
  │  etcdctl endpoint health  → etcd 是否健康                    │
  │  kubectl get nodes        → 节点是否 Ready                   │
  │  kubectl get pods -A      → 所有 Pod 是否正常                │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === 完整 etcd 恢复流程 ===

# 步骤 1: 停止 etcd（Static Pod 方式）
mv /etc/kubernetes/manifests/etcd.yaml /tmp/etcd.yaml.bak

# 步骤 2: 备份当前数据目录
mv /var/lib/etcd /var/lib/etcd.bak.$(date +%Y%m%d)

# 步骤 3: 从快照恢复
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \\
  --data-dir=/var/lib/etcd

# 步骤 4: 恢复 etcd manifest
mv /tmp/etcd.yaml.bak /etc/kubernetes/manifests/etcd.yaml

# 步骤 5: 等待 etcd 重启
sleep 5

# 步骤 6: 验证
ETCDCTL_API=3 etcdctl endpoint health \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

kubectl get nodes
kubectl get pods -A
""",
        common_errors=[
            "恢复时未先停止 etcd 服务，bbolt 文件被锁定导致恢复失败",
            "--data-dir 指向非空目录（如现有的 /var/lib/etcd 未清理），恢复失败",
            "恢复后忘记恢复 etcd manifest，导致 etcd 无法重启",
            "在 HA 集群中只在单个节点恢复，未在所有 etcd 成员上执行相同快照恢复",
            "多节点恢复时忘记指定 --initial-cluster-token，导致节点尝试加入旧集群",
            "恢复后未验证 etcd 健康状态就操作集群，可能导致数据不一致",
        ],
        tips=[
            "恢复前务必备份当前数据目录作为保险（mv 而非 rm）",
            "多节点集群恢复时使用 --initial-cluster-token 创建全新集群标识",
            "恢复后用 `etcdctl endpoint health` 验证 etcd 健康，再操作 Kubernetes",
            "定期进行恢复演练（建议每季度），验证备份的可用性",
            "恢复操作应在维护窗口进行，避免影响在线服务",
        ],
    ),
)


# ==================== Q21.3 证书续期 ====================

def _check_213_cert_renewal(user_input: str) -> CheckResult:
    """Q21.3 验证 kubeadm certs renew 证书续期命令"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入证书续期命令",
            hints=["使用 kubeadm certs renew 命令续期证书"],
        )

    lower = text.lower()

    # 检查 kubeadm
    if "kubeadm" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubeadm",
            hints=["证书续期使用 kubeadm certs renew 命令"],
        )

    # 检查 certs 子命令
    if "certs" not in lower and "cert" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 certs 子命令",
            hints=["使用 kubeadm certs renew 续期证书"],
        )

    # 检查 renew
    if "renew" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 renew 子命令",
            hints=["正确格式: kubeadm certs renew <cert-name> 或 kubeadm certs renew all"],
        )

    # 检查续期目标：all 或具体证书名
    has_all = "all" in lower
    has_specific_cert = any(
        cert in lower
        for cert in [
            "apiserver",
            "apiserver-kubelet-client",
            "front-proxy-client",
            "etcd-server",
            "etcd-peer",
            "apiserver-etcd-client",
            "front-proxy-ca",
            "etcd-ca",
            "ca",
        ]
    )

    if not has_all and not has_specific_cert:
        return CheckResult(
            ok=False,
            error="命令中缺少续期目标（all 或具体证书名）",
            hints=["使用 `kubeadm certs renew all` 续期所有证书，或指定具体证书如 `kubeadm certs renew apiserver`"],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["证书续期命令正确！续期后需要重启控制平面组件 📜"],
    )


LEVEL_Q21_3 = Level(
    id="Q21.3",
    chapter="ch21",
    title="证书续期",
    description="""
# 证书续期 📜

Kubernetes 集群使用大量 TLS 证书来保障组件间通信安全。kubeadm 部署的集群证书默认有效期为 **1 年**，到期前需要续期。

## 任务

编写 `kubeadm certs renew` 命令，完成以下目标：
- 使用 `kubeadm certs renew` 续期证书
- 续期所有证书（使用 `all`）或指定具体证书

## 提示

证书续期命令：
```bash
# 查看证书到期时间
kubeadm certs check-expiration

# 续期所有证书
kubeadm certs renew all

# 或续期单个证书
kubeadm certs renew apiserver
```
""",
    starter_yaml="""\
# 输入 kubeadm certs renew 命令
# kubeadm certs renew all  或  kubeadm certs renew <cert-name>
""",
    check_fn=_check_213_cert_renewal,
    lesson=Lesson(
        concept="""\
> **风险警告**: 本节涉及 etcd 数据操作等破坏性操作。
> - **切勿在生产集群上练习**，请使用专用学习集群
> - `mv /var/lib/etcd` 会停止 etcd 服务，导致集群不可用
> - `kubeadm upgrade` 不可回滚，操作前必须完整备份
> - 建议先在模拟器模式完成本章学习，再在隔离环境中实操

## Kubernetes 证书续期

kubeadm 部署的集群使用大量 TLS 证书来保障各组件间的双向认证（mTLS）。这些证书默认有效期为 **1 年**，到期后集群将无法正常工作。

### 集群中的证书体系

```
/etc/kubernetes/pki/
├── ca.crt / ca.key                 ← Kubernetes 根 CA（10年有效期）
├── apiserver.crt / .key            ← kube-apiserver 服务端证书
├── apiserver-kubelet-client.crt    ← apiserver 访问 kubelet 的客户端证书
├── front-proxy-ca.crt / .key       ← 前端代理 CA（10年有效期）
├── front-proxy-client.crt / .key   ← 前端代理客户端证书
└── etcd/
    ├── ca.crt / ca.key             ← etcd 专用 CA（10年有效期）
    ├── server.crt / .key           ← etcd 服务端证书
    ├── peer.crt / .key             ← etcd 节点间通信证书
    └── apiserver-etcd-client.crt   ← apiserver 访问 etcd 的客户端证书
```

### 哪些证书需要续期（1 年有效期）

| 证书 | 用途 | 到期影响 |
|------|------|----------|
| apiserver | kube-apiserver 服务端 | API 不可用 |
| apiserver-kubelet-client | apiserver → kubelet | 无法管理节点 |
| front-proxy-client | 聚合 API 代理 | 聚合 API 失败 |
| etcd/server | etcd 服务端 | etcd 不可用 |
| etcd/peer | etcd 节点间通信 | HA 集群分裂 |
| apiserver-etcd-client | apiserver → etcd | apiserver 无法读写数据 |

### 哪些证书不需要续期（10 年有效期）

- **ca.crt / ca.key**：Kubernetes 根 CA
- **front-proxy-ca.crt / .key**：前端代理 CA
- **etcd/ca.crt / ca.key**：etcd CA

这些 CA 证书有效期 10 年，通常不需要续期。但如果 CA 过期，需要重新生成所有证书。

### 续期流程

```
步骤 1: 检查证书到期时间
         ↓
步骤 2: 备份现有证书（重要！）
         ↓
步骤 3: 执行 kubeadm certs renew
         ↓
步骤 4: 重启控制平面组件
         ↓
步骤 5: 更新 kubeconfig 文件
         ↓
步骤 6: 验证证书
```

### 关键命令

**检查证书到期时间：**
```bash
kubeadm certs check-expiration

# 输出示例：
# CERTIFICATE                EXPIRES                  RESIDUAL TIME
# apiserver                  Jan 10, 2025 12:00 UTC   30d        ← 即将到期
# apiserver-kubelet-client   Jan 10, 2025 12:00 UTC   30d
# front-proxy-client         Jan 10, 2025 12:00 UTC   30d
# ...
```

**续期所有证书：**
```bash
# 续期所有 1 年有效期的证书（不影响 CA）
kubeadm certs renew all
```

**续期单个证书：**
```bash
kubeadm certs renew apiserver
kubeadm certs renew apiserver-kubelet-client
kubeadm certs renew etcd-server
```

**续期后重启控制平面组件：**
```bash
# Static Pod 方式：移动 manifest 再移回，触发重启
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/
mv /etc/kubernetes/manifests/kube-controller-manager.yaml /tmp/
mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/
sleep 2
mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/
mv /tmp/kube-controller-manager.yaml /etc/kubernetes/manifests/
mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/

# 重启 kubelet
systemctl restart kubelet
```

**更新 kubeconfig：**
```bash
# 重新生成 admin kubeconfig（使用新证书）
kubeadm init phase kubeconfig admin
cp /etc/kubernetes/admin.conf ~/.kube/config
```

**验证证书：**
```bash
# 查看新证书到期时间
kubeadm certs check-expiration

# 手动检查单个证书
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -dates
```
""",
        key_fields=[
            {"name": "kubeadm certs check-expiration", "description": "检查所有证书的到期时间", "required": False, "example": "kubeadm certs check-expiration"},
            {"name": "kubeadm certs renew all", "description": "续期所有 1 年有效期的证书（不影响 CA）", "required": True, "example": "kubeadm certs renew all"},
            {"name": "kubeadm certs renew <cert>", "description": "续期指定证书", "required": False, "example": "kubeadm certs renew apiserver"},
            {"name": "重启控制平面", "description": "续期后需要重启 kube-apiserver/controller-manager/scheduler", "required": True, "example": "mv manifest -> sleep -> mv back"},
            {"name": "更新 kubeconfig", "description": "续期后 admin.conf 中的证书也需要更新", "required": True, "example": "kubeadm init phase kubeconfig admin"},
        ],
        diagram="""\
  Kubernetes 证书续期流程

  ┌──────────────────────────────────────────────────────────────┐
  │  证书体系（kubeadm 部署）                                    │
  │                                                              │
  │  /etc/kubernetes/pki/                                        │
  │  ├── ca.crt (10年) ← 不需要续期                               │
  │  │   ├── apiserver.crt (1年) ← 需要续期                      │
  │  │   └── apiserver-kubelet-client.crt (1年) ← 需要续期       │
  │  ├── front-proxy-ca.crt (10年) ← 不需要续期                   │
  │  │   └── front-proxy-client.crt (1年) ← 需要续期             │
  │  └── etcd/                                                   │
  │      ├── ca.crt (10年) ← 不需要续期                           │
  │      ├── server.crt (1年) ← 需要续期                         │
  │      ├── peer.crt (1年) ← 需要续期                           │
  │      └── apiserver-etcd-client.crt (1年) ← 需要续期          │
  └──────────────────────────────────────────────────────────────┘

  ┌─────────────┐    kubeadm certs          ┌──────────────┐
  │ check-      │ ────────────────────────► │ 查看到期时间  │
  │ expiration  │                            │ 剩余天数      │
  └─────────────┘                            └──────┬───────┘
                                                     │ < 30天
                                                     ▼
  ┌──────────────────────────────────────────────────────────┐
  │  续期流程                                                │
  │                                                          │
  │  1. 备份现有证书                                          │
  │     cp -r /etc/kubernetes/pki /etc/kubernetes/pki.bak   │
  │                                                          │
  │  2. kubeadm certs renew all                              │
  │     → 用 CA 重新签发所有 1 年证书                         │
  │     → CA 证书不变                                        │
  │                                                          │
  │  3. 重启控制平面组件                                      │
  │     → apiserver / controller-manager / scheduler         │
  │     → 重启 kubelet                                       │
  │                                                          │
  │  4. 更新 kubeconfig                                       │
  │     → kubeadm init phase kubeconfig admin                │
  │     → cp admin.conf ~/.kube/config                       │
  │                                                          │
  │  5. 验证                                                  │
  │     → kubeadm certs check-expiration                     │
  │     → openssl x509 -in apiserver.crt -dates              │
  └──────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === Kubernetes 证书续期完整流程 ===

# 步骤 1: 检查证书到期时间
kubeadm certs check-expiration

# 步骤 2: 备份现有证书
cp -r /etc/kubernetes/pki /etc/kubernetes/pki.bak.$(date +%Y%m%d)

# 步骤 3: 续期所有证书
kubeadm certs renew all

# 步骤 4: 重启控制平面 Static Pod
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/
mv /etc/kubernetes/manifests/kube-controller-manager.yaml /tmp/
mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/
sleep 2
mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/
mv /tmp/kube-controller-manager.yaml /etc/kubernetes/manifests/
mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/

# 步骤 5: 重启 kubelet
systemctl restart kubelet

# 步骤 6: 更新 kubeconfig
kubeadm init phase kubeconfig admin
cp /etc/kubernetes/admin.conf ~/.kube/config

# 步骤 7: 验证
kubeadm certs check-expiration
kubectl get nodes
""",
        common_errors=[
            "忘记续期后重启控制平面组件，apiserver 仍使用旧证书",
            "续期后未更新 ~/.kube/config，kubectl 连接失败",
            "在 HA 集群中只在单个控制平面节点续期，其他节点证书过期",
            "误用 kubeadm certs renew ca（CA 证书不能通过 renew 续期）",
            "续期前未备份现有证书，出错后无法回退",
            "续期 etcd 证书后忘记重启 etcd，导致 etcd 通信失败",
        ],
        tips=[
            "建议在证书到期前 30 天执行续期，避免紧急操作",
            "使用 `kubeadm certs check-expiration` 定期监控证书状态",
            "HA 集群需要在每个控制平面节点上分别执行续期",
            "续期后务必更新所有 kubeconfig 文件（admin/controller-manager/scheduler）",
            "可以配置外部证书管理工具（如 cert-manager）实现自动续期",
        ],
    ),
)


# ==================== Q21.4 kubeadm upgrade ====================

def _check_214_kubeadm_upgrade(user_input: str) -> CheckResult:
    """Q21.4 验证 kubeadm upgrade plan/apply 升级命令"""
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

    # 检查 plan 或 apply 或 node
    has_plan = "plan" in lower
    has_apply = "apply" in lower
    has_node = "node" in lower
    if not has_plan and not has_apply and not has_node:
        return CheckResult(
            ok=False,
            error="命令中缺少 plan、apply 或 node 子命令",
            hints=["先用 kubeadm upgrade plan 检查，再用 kubeadm upgrade apply 升级控制平面，最后 kubeadm upgrade node 升级工作节点"],
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


LEVEL_Q21_4 = Level(
    id="Q21.4",
    chapter="ch21",
    title="kubeadm upgrade",
    description="""
# kubeadm upgrade 集群升级 ⬆️

Kubernetes 集群升级是维护中的重要操作。使用 `kubeadm` 可以安全地升级控制平面和工作节点。

## 任务

编写集群升级命令，完成以下目标之一：
- 使用 `kubeadm upgrade plan` 检查可升级版本
- 或使用 `kubeadm upgrade apply v1.28.0` 执行升级
- 或使用 `kubeadm upgrade node` 升级工作节点

## 提示

升级流程：
```bash
# 1. 检查可升级版本
kubeadm upgrade plan

# 2. 升级控制平面
kubeadm upgrade apply v1.28.0

# 3. 升级工作节点
kubeadm upgrade node
```
""",
    starter_yaml="""\
# 输入 kubeadm upgrade 命令
# kubeadm upgrade plan 或 kubeadm upgrade apply <version> 或 kubeadm upgrade node
""",
    check_fn=_check_214_kubeadm_upgrade,
    lesson=Lesson(
        concept="""\
> **风险警告**: 本节涉及 etcd 数据操作等破坏性操作。
> - **切勿在生产集群上练习**，请使用专用学习集群
> - `mv /var/lib/etcd` 会停止 etcd 服务，导致集群不可用
> - `kubeadm upgrade` 不可回滚，操作前必须完整备份
> - 建议先在模拟器模式完成本章学习，再在隔离环境中实操

## Kubernetes 集群升级流程

使用 `kubeadm` 升级 Kubernetes 集群是一个多步骤过程，需要按正确顺序操作。升级前**必须备份 etcd**。

### 升级顺序总览

```
升级前准备（备份 etcd、检查健康）
         ↓
升级第一个控制平面节点
  ├── 升级 kubeadm 工具
  ├── kubeadm upgrade plan（检查可升级版本）
  ├── kubeadm upgrade apply v<x.y.z>（升级控制平面）
  ├── 升级 kubelet + kubectl
  └── 重启 kubelet
         ↓
升级其余控制平面节点（逐个）
  ├── 升级 kubeadm
  ├── kubeadm upgrade apply v<x.y.z>
  ├── 升级 kubelet + kubectl
  └── 重启 kubelet
         ↓
升级工作节点（逐个）
  ├── kubectl drain <node>（驱逐节点）
  ├── 升级 kubeadm
  ├── kubeadm upgrade node（升级节点配置）
  ├── 升级 kubelet + kubectl
  ├── 重启 kubelet
  └── kubectl uncordon <node>（恢复调度）
         ↓
验证集群状态
```

### 各阶段详解

#### 阶段 1：升级前准备

```bash
# 备份 etcd（最重要！）
ETCDCTL_API=3 etcdctl snapshot save pre-upgrade-backup.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 检查集群健康
kubectl get nodes
kubectl get pods -A

# 检查当前版本
kubeadm version
kubectl version
```

#### 阶段 2：升级控制平面

```bash
# 步骤 1: 升级 kubeadm 工具
apt-get update
apt-get install -y kubeadm=1.28.0-00

# 步骤 2: 检查可升级版本
kubeadm upgrade plan
# 输出会显示当前版本和可升级到的版本列表

# 步骤 3: 执行升级
kubeadm upgrade apply v1.28.0
# 此步骤会：
# - 升级 etcd（如果是 Static Pod 方式）
# - 升级 kube-apiserver、controller-manager、scheduler 的配置和镜像
# - 升级 kube-proxy 配置和镜像
# - 更新 CoreDNS 配置

# 步骤 4: 升级 kubelet 和 kubectl
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
systemctl restart kubelet
```

#### 阶段 3：升级其余控制平面节点

在 HA 集群中，其余控制平面节点也需要升级：

```bash
# 在每个控制平面节点上执行
apt-get install -y kubeadm=1.28.0-00
kubeadm upgrade apply v1.28.0    # 注意：也是 apply，不是 node
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
systemctl restart kubelet
```

#### 阶段 4：升级工作节点（逐个进行）

```bash
# 步骤 1: 驱逐节点
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# 步骤 2: 升级 kubeadm
apt-get install -y kubeadm=1.28.0-00

# 步骤 3: 升级节点配置
kubeadm upgrade node
# 注意：工作节点用 node，不是 apply
# 此步骤会更新 kubelet 配置和 kube-proxy 配置

# 步骤 4: 升级 kubelet
apt-get install -y kubelet=1.28.0-00
systemctl restart kubelet

# 步骤 5: 恢复调度
kubectl uncordon worker-1
```

#### 阶段 5：验证

```bash
# 检查所有节点版本
kubectl get nodes
# 所有节点应显示 v1.28.0

# 检查组件状态
kubectl get componentstatuses

# 检查所有 Pod
kubectl get pods -A
```

### 版本兼容性规则

| 规则 | 说明 |
|------|------|
| 次版本号差 ≤ 1 | 1.27 → 1.28 可以，1.27 → 1.29 不行（需先升到 1.28） |
| kubelet ≤ API Server | kubelet 不能高于 API Server 版本 |
| kubelet ≥ API Server - 3 | kubelet 可以比 API Server 低最多 3 个次版本 |
| kubectl ± 1 | kubectl 可以比 API Server 高或低 1 个次版本 |

### apply vs node 的区别

| 命令 | 用于 | 做了什么 |
|------|------|----------|
| `kubeadm upgrade apply` | 控制平面节点 | 升级 etcd + apiserver + controller-manager + scheduler + kube-proxy + CoreDNS |
| `kubeadm upgrade node` | 工作节点 | 只升级 kubelet 配置 + kube-proxy 配置 |
""",
        key_fields=[
            {"name": "kubeadm upgrade plan", "description": "检查当前版本和可升级到的版本列表", "required": True, "example": "kubeadm upgrade plan"},
            {"name": "kubeadm upgrade apply", "description": "升级控制平面到指定版本（含 etcd/apiserver/controller-manager/scheduler）", "required": True, "example": "kubeadm upgrade apply v1.28.0"},
            {"name": "kubeadm upgrade node", "description": "升级工作节点配置（kubelet/kube-proxy），不需要版本号", "required": False, "example": "kubeadm upgrade node"},
            {"name": "version", "description": "apply 需要指定的目标版本号，格式 v<x.y.z>", "required": True, "example": "v1.28.0"},
            {"name": "kubectl drain/uncordon", "description": "工作节点升级前 drain，升级后 uncordon", "required": False, "example": "kubectl drain worker-1 --ignore-daemonsets"},
        ],
        diagram="""\
  Kubernetes 集群升级完整流程

  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 0: 升级前准备                                          │
  │                                                              │
  │  ┌──────────────────┐  ┌──────────────────┐                 │
  │  │ 备份 etcd         │  │ 检查集群健康      │                 │
  │  │ snapshot save     │  │ kubectl get nodes│                 │
  │  └──────────────────┘  └────────┬─────────┘                 │
  └─────────────────────────────────┼────────────────────────────┘
                                    ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 1: 升级第一个控制平面节点                                │
  │                                                              │
  │  apt install kubeadm=1.28.0-00                              │
  │         ↓                                                    │
  │  kubeadm upgrade plan  ──► 显示可升级版本                     │
  │         ↓                                                    │
  │  kubeadm upgrade apply v1.28.0                              │
  │    → 升级 etcd Static Pod                                    │
  │    → 升级 apiserver/controller-manager/scheduler             │
  │    → 升级 kube-proxy + CoreDNS                               │
  │         ↓                                                    │
  │  apt install kubelet=1.28.0-00 kubectl=1.28.0-00            │
  │  systemctl restart kubelet                                   │
  └─────────────────────────────────┬────────────────────────────┘
                                    ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 2: 升级其余控制平面节点（HA 集群，逐个）                 │
  │                                                              │
  │  在 cp-2, cp-3 上重复阶段 1 的步骤                            │
  │  （也是 kubeadm upgrade apply v1.28.0）                      │
  └─────────────────────────────────┬────────────────────────────┘
                                    ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 3: 升级工作节点（逐个进行）                              │
  │                                                              │
  │  ┌──────────────────────────────────────────────────┐        │
  │  │ worker-1:                                        │        │
  │  │  kubectl drain worker-1 --ignore-daemonsets      │        │
  │  │  apt install kubeadm=1.28.0-00                   │        │
  │  │  kubeadm upgrade node  ← 注意是 node 不是 apply  │        │
  │  │  apt install kubelet=1.28.0-00                   │        │
  │  │  systemctl restart kubelet                       │        │
  │  │  kubectl uncordon worker-1                       │        │
  │  └──────────────────────────────────────────────────┘        │
  │                                                              │
  │  等待 worker-1 Ready 后，再升级 worker-2 ...                 │
  └─────────────────────────────────┬────────────────────────────┘
                                    ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 4: 验证                                                 │
  │                                                              │
  │  kubectl get nodes     → 所有节点 v1.28.0, Ready             │
  │  kubectl get pods -A   → 所有 Pod Running                    │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === Kubernetes 集群升级完整流程 ===

# 阶段 0: 升级前准备
# 备份 etcd（最重要！）
ETCDCTL_API=3 etcdctl snapshot save pre-upgrade-backup.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 阶段 1: 升级控制平面
apt-get update
apt-get install -y kubeadm=1.28.0-00

kubeadm upgrade plan
kubeadm upgrade apply v1.28.0

apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
systemctl restart kubelet

# 阶段 2: 升级工作节点（逐个）
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

apt-get install -y kubeadm=1.28.0-00
kubeadm upgrade node
apt-get install -y kubelet=1.28.0-00
systemctl restart kubelet

kubectl uncordon worker-1

# 阶段 3: 验证
kubectl get nodes
kubectl get pods -A
""",
        common_errors=[
            "跳过 plan 步骤直接 apply，版本不兼容导致升级失败",
            "升级跨度太大（跨多个次版本），需要逐版本升级（1.27→1.28→1.29）",
            "未先升级 kubeadm 就执行 upgrade apply，kubeadm 版本太旧不支持新版本",
            "升级工作节点时未先 drain，导致服务中断",
            "工作节点误用 `kubeadm upgrade apply` 而非 `kubeadm upgrade node`",
            "同时升级多个工作节点，导致集群容量不足",
            "升级前未备份 etcd，升级失败后无法回滚",
        ],
        tips=[
            "升级前务必备份 etcd，这是升级失败时唯一的回滚手段",
            "一次只升级一个次版本（1.27→1.28→1.29），不要跨版本升级",
            "升级工作节点时要逐个进行，确保最小化影响",
            "升级后用 `kubectl get nodes` 确认所有节点版本一致",
            "注意 CNI 插件版本兼容性（如 Calico/Flannel 需要支持新 K8s 版本）",
            "生产环境升级前先在测试环境验证完整流程",
        ],
    ),
)


# ==================== Q21.5 集群实战 - 综合维护场景 ====================

def _check_215_comprehensive(user_input: str) -> CheckResult:
    """Q21.5 综合维护场景 - 备份 + 恢复 + 升级全流程"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入完整的集群维护流程命令",
            hints=["综合场景包含: etcd 备份 + 证书检查 + kubeadm upgrade"],
        )

    lower = text.lower()

    # 检查包含 etcd 备份步骤
    has_etcd_backup = "etcdctl" in lower and ("snapshot" in lower and "save" in lower)
    if not has_etcd_backup:
        return CheckResult(
            ok=False,
            error="缺少 etcd 备份步骤",
            hints=["综合场景第一步: ETCDCTL_API=3 etcdctl snapshot save <file> --endpoints ... --cacert ... --cert ... --key ..."],
        )

    # 检查包含 kubeadm upgrade 步骤
    has_upgrade = "kubeadm" in lower and "upgrade" in lower
    if not has_upgrade:
        return CheckResult(
            ok=False,
            error="缺少 kubeadm upgrade 步骤",
            hints=["综合场景需要包含 kubeadm upgrade plan/apply 升级步骤"],
        )

    # 检查升级包含 plan 或 apply
    has_plan_or_apply = "plan" in lower or "apply" in lower
    if not has_plan_or_apply:
        return CheckResult(
            ok=False,
            error="kubeadm upgrade 缺少 plan 或 apply 子命令",
            hints=["先用 kubeadm upgrade plan 检查，再用 kubeadm upgrade apply v1.28.0 升级"],
        )

    # 检查包含证书检查或节点维护步骤（加分项）
    has_cert_check = "certs" in lower and "check" in lower
    has_drain = "drain" in lower
    has_uncordon = "uncordon" in lower

    bonus = []
    if has_cert_check:
        bonus.append("证书检查")
    if has_drain and has_uncordon:
        bonus.append("节点 drain/uncordon")

    hint = "综合维护流程正确！备份 + 升级是生产环境的标准操作 🏆"
    if bonus:
        hint = f"综合维护流程正确！还包含: {', '.join(bonus)} 🏆"

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=[hint],
    )


LEVEL_Q21_5 = Level(
    id="Q21.5",
    chapter="ch21",
    title="集群实战 - 综合维护",
    description="""
# 集群实战 - 综合维护场景 🏆

将前面学到的 etcd 备份、证书续期、集群升级知识综合运用，完成一个完整的生产环境维护流程。

## 场景

生产集群需要从 v1.27.x 升级到 v1.28.0。请编写完整的维护流程命令，包含：
1. **备份 etcd**（升级前最重要的操作）
2. **检查证书到期时间**（升级前确认证书不会过期）
3. **kubeadm upgrade plan**（检查可升级版本）
4. **kubeadm upgrade apply**（执行升级）
5. （可选）工作节点 drain + upgrade node + uncordon

## 提示

综合维护流程：
```bash
# 1. 备份 etcd
ETCDCTL_API=3 etcdctl snapshot save pre-upgrade.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 2. 检查证书
kubeadm certs check-expiration

# 3. 升级 kubeadm
apt-get install -y kubeadm=1.28.0-00

# 4. 检查升级计划
kubeadm upgrade plan

# 5. 执行升级
kubeadm upgrade apply v1.28.0
```
""",
    starter_yaml="""\
# 输入完整的集群综合维护流程命令
# 1. ETCDCTL_API=3 etcdctl snapshot save ... --endpoints ... --cacert ... --cert ... --key ...
# 2. kubeadm upgrade plan / kubeadm upgrade apply v1.28.0
""",
    check_fn=_check_215_comprehensive,
    lesson=Lesson(
        concept="""\
> **风险警告**: 本节涉及 etcd 数据操作等破坏性操作。
> - **切勿在生产集群上练习**，请使用专用学习集群
> - `mv /var/lib/etcd` 会停止 etcd 服务，导致集群不可用
> - `kubeadm upgrade` 不可回滚，操作前必须完整备份
> - 建议先在模拟器模式完成本章学习，再在隔离环境中实操

## 综合集群维护实战

在生产环境中，集群维护是一个需要系统化思考的流程。本关将 etcd 备份、证书管理、集群升级三个核心技能综合运用。

### 生产环境维护最佳实践

#### 维护前检查清单

```
□ 1. 备份 etcd（最重要！升级失败的唯一回滚手段）
□ 2. 检查证书到期时间（kubeadm certs check-expiration）
□ 3. 检查集群健康（kubectl get nodes, kubectl get pods -A）
□ 4. 检查集群容量（确保有足够资源应对节点 drain）
□ 5. 通知相关团队（维护窗口、预期影响）
□ 6. 准备回滚方案（etcd 恢复流程、旧版本包）
```

#### 综合维护流程

```
阶段 1: 升级前准备
  ├── 备份 etcd
  ├── 检查证书到期时间
  ├── 检查集群健康状态
  └── 检查集群容量

阶段 2: 升级控制平面
  ├── 升级 kubeadm 工具
  ├── kubeadm upgrade plan（确认可升级版本）
  ├── kubeadm upgrade apply v1.28.0
  ├── 升级 kubelet + kubectl
  └── 验证控制平面

阶段 3: 升级工作节点（逐个）
  ├── kubectl drain <node> --ignore-daemonsets
  ├── 升级 kubeadm
  ├── kubeadm upgrade node
  ├── 升级 kubelet
  ├── kubectl uncordon <node>
  └── 验证节点 Ready

阶段 4: 验证 & 清理
  ├── kubectl get nodes（所有节点版本一致）
  ├── kubectl get pods -A（所有 Pod 正常）
  └── 清理旧版本包和临时文件
```

#### 升级失败回滚方案

如果升级失败，需要回滚：

```bash
# 步骤 1: 停止控制平面组件
mv /etc/kubernetes/manifests/*.yaml /tmp/

# 步骤 2: 降级 kubeadm/kubelet/kubectl
apt-get install kubeadm=1.27.0-00 kubelet=1.27.0-00 kubectl=1.27.0-00

# 步骤 3: 从 etcd 备份恢复
ETCDCTL_API=3 etcdctl snapshot restore pre-upgrade.db \\
  --data-dir=/var/lib/etcd

# 步骤 4: 恢复控制平面
mv /tmp/*.yaml /etc/kubernetes/manifests/
systemctl restart kubelet

# 步骤 5: 验证
kubectl get nodes
kubectl get pods -A
```

### 各操作之间的关系

```
etcd 备份 ──────► 升级失败的回滚保障
                   │
证书检查 ──────► 确保升级期间证书不会过期
                   │
kubeadm upgrade ──► 核心升级操作
  ├── plan ──► 确认版本兼容性
  ├── apply ─► 升级控制平面
  └── node ──► 升级工作节点
                   │
kubectl drain ────► 工作节点升级前的安全措施
kubectl uncordon ─► 工作节点升级后恢复调度
```
""",
        key_fields=[
            {"name": "etcd snapshot save", "description": "升级前备份 etcd，是回滚的唯一保障", "required": True, "example": "etcdctl snapshot save pre-upgrade.db --endpoints=..."},
            {"name": "kubeadm certs check-expiration", "description": "检查证书到期时间，确保升级期间不会过期", "required": False, "example": "kubeadm certs check-expiration"},
            {"name": "kubeadm upgrade plan", "description": "检查可升级版本和兼容性", "required": True, "example": "kubeadm upgrade plan"},
            {"name": "kubeadm upgrade apply", "description": "执行控制平面升级", "required": True, "example": "kubeadm upgrade apply v1.28.0"},
            {"name": "kubectl drain/uncordon", "description": "工作节点升级前驱逐、升级后恢复", "required": False, "example": "kubectl drain worker-1 --ignore-daemonsets"},
        ],
        diagram="""\
  综合集群维护流程

  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 1: 升级前准备                                          │
  │                                                              │
  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
  │  │ etcd 备份        │  │ 证书检查         │  │ 集群健康检查  │ │
  │  │ snapshot save   │  │ check-expiration│  │ get nodes    │ │
  │  │ (回滚保障)       │  │ (避免过期)       │  │ get pods -A  │ │
  │  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘ │
  └───────────┼────────────────────┼──────────────────┼─────────┘
              └────────────────────┼──────────────────┘
                                   ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 2: 升级控制平面                                        │
  │                                                              │
  │  apt install kubeadm=1.28.0-00                              │
  │         ↓                                                    │
  │  kubeadm upgrade plan ──► 确认可升级到 v1.28.0               │
  │         ↓                                                    │
  │  kubeadm upgrade apply v1.28.0                              │
  │    → 升级 apiserver/controller-manager/scheduler/etcd       │
  │         ↓                                                    │
  │  apt install kubelet=1.28.0-00 kubectl=1.28.0-00            │
  │  systemctl restart kubelet                                   │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 3: 升级工作节点（逐个）                                 │
  │                                                              │
  │  kubectl drain worker-1 --ignore-daemonsets                 │
  │  apt install kubeadm=1.28.0-00                              │
  │  kubeadm upgrade node                                        │
  │  apt install kubelet=1.28.0-00                               │
  │  systemctl restart kubelet                                   │
  │  kubectl uncordon worker-1                                   │
  │  → 等待 worker-1 Ready 后再升级 worker-2                     │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  阶段 4: 验证                                                │
  │                                                              │
  │  kubectl get nodes  → 全部 v1.28.0, Ready                   │
  │  kubectl get pods -A → 全部 Running                          │
  │                                                              │
  │  如果失败:                                                    │
  │  → 从 etcd 备份恢复 (snapshot restore)                      │
  │  → 降级 kubeadm/kubelet 到旧版本                             │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === 综合集群维护完整流程 ===

# --- 阶段 1: 升级前准备 ---

# 1.1 备份 etcd（最重要！）
ETCDCTL_API=3 etcdctl snapshot save pre-upgrade.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# 1.2 检查证书到期时间
kubeadm certs check-expiration

# 1.3 检查集群健康
kubectl get nodes
kubectl get pods -A

# --- 阶段 2: 升级控制平面 ---

# 2.1 升级 kubeadm
apt-get update
apt-get install -y kubeadm=1.28.0-00

# 2.2 检查升级计划
kubeadm upgrade plan

# 2.3 执行升级
kubeadm upgrade apply v1.28.0

# 2.4 升级 kubelet 和 kubectl
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
systemctl restart kubelet

# --- 阶段 3: 升级工作节点（逐个） ---

kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data
apt-get install -y kubeadm=1.28.0-00
kubeadm upgrade node
apt-get install -y kubelet=1.28.0-00
systemctl restart kubelet
kubectl uncordon worker-1

# --- 阶段 4: 验证 ---
kubectl get nodes
kubectl get pods -A
""",
        common_errors=[
            "升级前未备份 etcd，升级失败后无法回滚",
            "未检查证书到期时间，升级后证书刚好过期导致集群不可用",
            "同时升级多个工作节点，导致集群容量不足服务中断",
            "升级后未验证集群状态就结束维护",
            "升级失败后未从 etcd 备份恢复，而是尝试继续升级",
            "未通知相关团队就执行升级，影响在线服务",
        ],
        tips=[
            "etcd 备份是升级的'保险'，务必在升级前执行",
            "使用 `kubeadm certs check-expiration` 确保证书不会在升级期间过期",
            "工作节点升级要逐个进行，每个节点升级后验证再升级下一个",
            "准备回滚方案：etcd 恢复 + 降级软件包，并在测试环境演练",
            "维护窗口选择低峰期，提前通知所有相关团队",
            "升级后持续监控集群 24-48 小时，及时发现潜在问题",
        ],
    ),
)


# ==================== Chapter 21 Levels ====================

CHAPTER_21_LEVELS: list[Level] = [
    LEVEL_Q21_1, LEVEL_Q21_2, LEVEL_Q21_3, LEVEL_Q21_4, LEVEL_Q21_5,
]
