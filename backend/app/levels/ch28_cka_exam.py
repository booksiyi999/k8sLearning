"""Chapter 28: CKA 模拟考试 - kubectl 操作挑战（5 关）

Q28.1 kubectl 操作挑战 - 创建 Pod + 暴露 Service + 扩容
Q28.2 故障排查挑战 - 排查 CrashLoopBackOff
Q28.3 网络排查挑战 - 排查 Service 连通性
Q28.4 RBAC 排查挑战 - 检查权限
Q28.5 综合挑战 - 多步骤操作（命名空间+部署+网络策略+验证）

CKA 考试核心是 kubectl 操作能力，本章全部重写为命令行挑战。
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q28.1 kubectl 操作挑战 ====================

def _check_281_kubectl_ops(user_input: str) -> CheckResult:
    """Q28.1 验证 kubectl run/expose/scale 命令序列"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 kubectl 命令序列",
            hints=["需要使用 kubectl run、kubectl expose、kubectl scale 命令"],
        )

    # 解析 kubectl 命令（跳过注释和空行）
    import shlex
    commands = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('kubectl ') or line.startswith('kubectl\t'):
            try:
                parts = shlex.split(line[8:])  # 去掉 "kubectl" 前缀
            except ValueError:
                parts = line[8:].split()
            commands.append({
                'subcommand': parts[0].lower() if parts else '',
                'args': parts[1:] if len(parts) > 1 else [],
                'raw': line,
            })

    if not commands:
        return CheckResult(
            ok=False,
            error="未找到有效的 kubectl 命令（注释和空行不算）",
            hints=["每行以 kubectl 开头，如: kubectl run nginx --image=nginx"],
        )

    # 检查 kubectl run（创建 Pod/Deployment）
    run_cmds = [c for c in commands if c['subcommand'] == 'run']
    if not run_cmds:
        return CheckResult(
            ok=False,
            error="缺少 kubectl run 命令（创建 Pod/Deployment）",
            hints=["使用 kubectl run <name> --image=<image> 创建应用"],
        )

    # 验证 run 命令有 --image 参数
    for cmd in run_cmds:
        args_str = ' '.join(cmd['args'])
        if '--image' not in args_str:
            return CheckResult(
                ok=False,
                error="kubectl run 缺少 --image 参数",
                hints=["kubectl run 需要 --image=<image> 指定镜像，如: kubectl run nginx --image=nginx"],
            )

    # 检查 kubectl expose（暴露 Service）
    expose_cmds = [c for c in commands if c['subcommand'] == 'expose']
    if not expose_cmds:
        return CheckResult(
            ok=False,
            error="缺少 kubectl expose 命令（暴露 Service）",
            hints=["使用 kubectl expose deployment <name> --port=<port> 暴露服务"],
        )

    # 检查 kubectl scale（扩容）
    scale_cmds = [c for c in commands if c['subcommand'] == 'scale']
    if not scale_cmds:
        return CheckResult(
            ok=False,
            error="缺少 kubectl scale 命令（扩容副本数）",
            hints=["使用 kubectl scale deployment <name> --replicas=<n> 扩容"],
        )

    # 验证 scale 命令有 --replicas 参数
    for cmd in scale_cmds:
        args_str = ' '.join(cmd['args'])
        if '--replicas' not in args_str:
            return CheckResult(
                ok=False,
                error="kubectl scale 缺少 --replicas 参数",
                hints=["kubectl scale 需要 --replicas=<n> 指定副本数"],
            )

    # 验证命令顺序: run 应在 expose 之前
    run_idx = next((i for i, c in enumerate(commands) if c['subcommand'] == 'run'), -1)
    expose_idx = next((i for i, c in enumerate(commands) if c['subcommand'] == 'expose'), -1)
    scale_idx = next((i for i, c in enumerate(commands) if c['subcommand'] == 'scale'), -1)

    if run_idx >= 0 and expose_idx >= 0 and run_idx > expose_idx:
        return CheckResult(
            ok=False,
            error="命令顺序错误: kubectl run 应在 kubectl expose 之前执行",
            hints=["先创建应用 (run)，再暴露服务 (expose)，最后扩容 (scale)"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["kubectl 操作序列正确！run + expose + scale 是 CKA 最基础的操作组合 🎯"],
    )


LEVEL_Q28_1 = Level(
    id="Q28.1",
    chapter="ch28",
    title="kubectl 操作挑战 - 创建+暴露+扩容",
    description="""
# CKA 挑战 - kubectl 操作 🎯

> **实操提示**: 本章为 CKA 实战挑战关。模拟器模式校验命令语法，集群模式可真实执行命令验证结果。

**核心考核**：使用 kubectl 命令完成应用部署、服务暴露和扩容。

## 场景

你需要完成以下操作序列：
1. 创建一个 nginx Deployment
2. 将其暴露为 Service
3. 扩容到 3 个副本

## 任务

写出完整的 kubectl 命令序列：
- `kubectl run` 创建 Deployment
- `kubectl expose` 暴露 Service
- `kubectl scale` 扩容副本

## 提示

```bash
# 创建 Deployment
kubectl run nginx-app --image=nginx:1.25

# 暴露 Service
kubectl expose deployment nginx-app --port=80 --target-port=80

# 扩容到 3 个副本
kubectl scale deployment nginx-app --replicas=3
```
""",
    starter_yaml="""\
# 输入 kubectl 命令序列
# 1. kubectl run <name> --image=<image>
# 2. kubectl expose deployment <name> --port=<port>
# 3. kubectl scale deployment <name> --replicas=<n>
""",
    check_fn=_check_281_kubectl_ops,
    lesson=Lesson(
        concept="""\
## CKA kubectl 操作基础

CKA 考试中，**kubectl 命令行操作**是最核心的技能。考试时间有限（2小时），熟练使用 kubectl 命令比手写 YAML 更高效。

### kubectl run - 创建资源

`kubectl run` 可以快速创建 Deployment 或 Pod：

```bash
# 创建 Deployment（默认行为，K8s 1.18+）
kubectl run nginx-app --image=nginx:1.25

# 创建 Pod（使用 --restart=Never）
kubectl run nginx-pod --image=nginx:1.25 --restart=Never

# 带命令和参数
kubectl run busybox --image=busybox --command -- sleep 3600

# 带标签
kubectl run nginx-app --image=nginx:1.25 --labels=app=web,env=prod

# 带端口
kubectl run nginx-app --image=nginx:1.25 --port=80
```

### kubectl expose - 暴露 Service

`kubectl expose` 从已有资源（Deployment/Pod/ReplicaSet）创建 Service：

```bash
# 暴露 Deployment
kubectl expose deployment nginx-app --port=80 --target-port=80

# 暴露为 NodePort
kubectl expose deployment nginx-app --port=80 --type=NodePort

# 暴露为 LoadBalancer
kubectl expose deployment nginx-app --port=80 --type=LoadBalancer

# 指定标签选择器
kubectl expose deployment nginx-app --port=80 --target-port=8080
```

### kubectl scale - 扩缩容

```bash
# 扩容到 3 个副本
kubectl scale deployment nginx-app --replicas=3

# 缩容到 1 个副本
kubectl scale deployment nginx-app --replicas=1

# 批量扩容多个 Deployment
kubectl scale deployment --all --replicas=3 -n production

# 基于 CPU 使用率自动扩容（HPA）
kubectl autoscale deployment nginx-app --min=2 --max=10 --cpu-percent=80
```

### CKA 考试技巧

1. **优先用命令而非 YAML**：`kubectl run` + `kubectl expose` 比 YAML 快得多
2. **--dry-run=client -o yaml**：生成 YAML 供修改
3. **kubectl create**：创建 Namespace、ConfigMap、Secret 等资源
4. **善用 --help**：忘记参数时 `kubectl run --help`
""",
        key_fields=[
            {"name": "kubectl run", "description": "创建 Deployment 或 Pod", "required": True, "example": "kubectl run nginx-app --image=nginx:1.25"},
            {"name": "kubectl expose", "description": "从 Deployment/Pod 创建 Service", "required": True, "example": "kubectl expose deployment nginx-app --port=80"},
            {"name": "kubectl scale", "description": "扩缩容 Deployment 副本数", "required": True, "example": "kubectl scale deployment nginx-app --replicas=3"},
            {"name": "--image", "description": "指定容器镜像", "required": True, "example": "--image=nginx:1.25"},
            {"name": "--port / --target-port", "description": "Service 端口和容器端口", "required": False, "example": "--port=80 --target-port=80"},
        ],
        diagram="""\
  kubectl 操作序列

  步骤 1: kubectl run                     步骤 2: kubectl expose
  ┌──────────────────────────┐            ┌──────────────────────────┐
  │ kubectl run nginx-app    │            │ kubectl expose deployment │
  │   --image=nginx:1.25     │            │   nginx-app              │
  │                          │            │   --port=80              │
  │ -> 创建 Deployment        │ ────────► │ -> 创建 Service           │
  │   nginx-app (replicas:1) │            │   nginx-app:80            │
  └──────────────────────────┘            └──────────┬───────────────┘
                                                     │
                                                     ▼
                                          步骤 3: kubectl scale
                                          ┌──────────────────────────┐
                                          │ kubectl scale deployment  │
                                          │   nginx-app --replicas=3 │
                                          │                          │
                                          │ -> 扩容到 3 个副本        │
                                          │   Pod-0, Pod-1, Pod-2    │
                                          └──────────────────────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────────┐
                                          │     Service (nginx-app)  │
                                          │          port: 80        │
                                          │    ┌───┬───┬───┐         │
                                          │    │P0 │P1 │P2 │         │
                                          │    └───┴───┴───┘         │
                                          └──────────────────────────┘
""",
        example_yaml="""\
# === CKA kubectl 操作序列 ===

# 步骤 1: 创建 Deployment
kubectl run nginx-app --image=nginx:1.25 --port=80

# 步骤 2: 暴露 Service
kubectl expose deployment nginx-app --port=80 --target-port=80

# 步骤 3: 扩容到 3 个副本
kubectl scale deployment nginx-app --replicas=3

# 验证
kubectl get deployments
kubectl get svc
kubectl get pods -o wide
""",
        common_errors=[
            "kubectl run 忘记指定 --image，创建失败",
            "kubectl expose 的资源类型和名称与实际不匹配（如 deployment 名写错）",
            "kubectl scale 指定的资源类型错误（如写成 scale pod 而非 scale deployment）",
            "expose 后忘记验证 Service 的 Endpoints 是否正常",
            "混淆 --port（Service 端口）和 --target-port（容器端口）",
        ],
        tips=[
            "使用 `kubectl run --dry-run=client -o yaml > deploy.yaml` 生成 YAML 再修改",
            "用 `kubectl get svc` 确认 Service 的 ClusterIP 和端口",
            "用 `kubectl get endpoints <svc>` 确认 Service 后端有 Pod",
            "CKA 考试中优先用命令操作，省下时间给复杂题目",
        ],
    ),
)


# ==================== Q28.2 故障排查挑战 ====================

def _check_282_troubleshoot(user_input: str) -> CheckResult:
    """Q28.2 验证排查 CrashLoopBackOff 的 kubectl 命令序列"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 kubectl 排查命令序列",
            hints=["排查 CrashLoopBackOff 需要 kubectl describe 和 kubectl logs"],
        )

    # 解析 kubectl 命令（跳过注释和空行）
    import shlex
    commands = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('kubectl ') or line.startswith('kubectl\t'):
            try:
                parts = shlex.split(line[8:])
            except ValueError:
                parts = line[8:].split()
            commands.append({
                'subcommand': parts[0].lower() if parts else '',
                'args': parts[1:] if len(parts) > 1 else [],
                'raw': line,
            })

    if not commands:
        return CheckResult(
            ok=False,
            error="未找到有效的 kubectl 命令（注释和空行不算）",
            hints=["每行以 kubectl 开头，如: kubectl describe pod <pod-name>"],
        )

    # 检查 describe（查看 Pod 事件和状态）
    describe_cmds = [c for c in commands if c['subcommand'] == 'describe']
    if not describe_cmds:
        return CheckResult(
            ok=False,
            error="缺少 kubectl describe 命令（查看 Pod 事件和详细状态）",
            hints=["使用 kubectl describe pod <pod-name> 查看 Events 和错误信息"],
        )

    # 验证 describe 有资源类型参数（如 pod）
    for cmd in describe_cmds:
        if not cmd['args'] or cmd['args'][0].lower() not in ('pod', 'pods', 'po'):
            return CheckResult(
                ok=False,
                error="kubectl describe 需要指定资源类型（如 pod <pod-name>）",
                hints=["kubectl describe pod <pod-name> 查看Pod详情"],
            )

    # 检查 logs（查看容器日志）
    logs_cmds = [c for c in commands if c['subcommand'] == 'logs']
    if not logs_cmds:
        return CheckResult(
            ok=False,
            error="缺少 kubectl logs 命令（查看容器日志）",
            hints=["使用 kubectl logs <pod-name> 查看应用日志，或 kubectl logs <pod> --previous 查看上次崩溃的日志"],
        )

    # 验证 logs 有 pod 名称参数
    for cmd in logs_cmds:
        if not cmd['args']:
            return CheckResult(
                ok=False,
                error="kubectl logs 需要指定 Pod 名称",
                hints=["kubectl logs <pod-name> 查看日志"],
            )

    return CheckResult(
        ok=True, state=None,
        hints=["故障排查命令序列正确！describe + logs 是排查 Pod 故障的标准流程 🔍"],
    )


LEVEL_Q28_2 = Level(
    id="Q28.2",
    chapter="ch28",
    title="故障排查挑战 - CrashLoopBackOff",
    description="""
# CKA 挑战 - 故障排查 🔍

**核心考核**：使用 kubectl 命令排查 Pod CrashLoopBackOff 故障。

## 场景

一个 Pod 一直处于 CrashLoopBackOff 状态。你需要写出排查命令序列：
1. 查看 Pod 详细信息（Events、错误信息）
2. 查看容器日志（应用输出）
3. 查看上次崩溃时的日志（关键！）

## 任务

写出排查 CrashLoopBackOff 的 kubectl 命令序列：
- `kubectl describe pod` 查看 Pod 事件
- `kubectl logs` 查看容器日志
- `kubectl logs --previous` 查看上次崩溃日志

## 提示

```bash
# 查看 Pod 详细状态和事件
kubectl describe pod <pod-name>

# 查看当前容器日志
kubectl logs <pod-name>

# 查看上次崩溃时的日志（关键！）
kubectl logs <pod-name> --previous
```
""",
    starter_yaml="""\
# 输入排查 CrashLoopBackOff 的 kubectl 命令序列
# 1. kubectl describe pod <pod-name>
# 2. kubectl logs <pod-name>
# 3. kubectl logs <pod-name> --previous
""",
    check_fn=_check_282_troubleshoot,
    lesson=Lesson(
        concept="""\
## CKA 故障排查方法论

CKA 考试中约 30% 的题目涉及故障排查。掌握系统化的排查方法论至关重要。

### CrashLoopBackOff 排查流程

```
kubectl get pods           -> 确认 Pod 状态
       |
       v
kubectl describe pod       -> 查看 Events（拉取镜像失败？启动命令错误？）
       |
       v
kubectl logs               -> 查看当前日志（应用是否启动？）
       |
       v
kubectl logs --previous    -> 查看上次崩溃日志（关键！崩溃前输出了什么？）
       |
       v
kubectl exec               -> 进入容器调试（如果容器还活着）
```

### kubectl describe - 查看 Pod 详情

`kubectl describe pod` 是排查的第一步，它会显示：

```bash
kubectl describe pod <pod-name>
```

关键信息：
- **Events 部分**：记录了 Pod 的生命周期事件
  - `Pulling image` / `Pulled` -> 镜像拉取状态
  - `Created container` / `Started container` -> 容器启动状态
  - `Back-off restarting failed container` -> CrashLoopBackOff
- **State 部分**：当前容器状态（Waiting/Running/Terminated）
- **Last State 部分**：上次终止原因（Exit Code、Reason）
  - Exit Code 0 -> 正常退出
  - Exit Code 1 -> 应用错误
  - Exit Code 137 -> OOMKilled（内存不足被杀）
  - Exit Code 139 -> Segmentation Fault

### kubectl logs - 查看容器日志

```bash
# 查看当前日志
kubectl logs <pod-name>

# 查看指定容器日志（多容器 Pod）
kubectl logs <pod-name> -c <container-name>

# 查看上次崩溃时的日志（CrashLoopBackOff 必用！）
kubectl logs <pod-name> --previous

# 实时跟踪日志
kubectl logs <pod-name> -f

# 查看最近 20 行
kubectl logs <pod-name> --tail=20

# 查看最近 1 小时的日志
kubectl logs <pod-name> --since=1h
```

### 常见 Pod 故障状态及排查

| 状态 | 可能原因 | 排查命令 |
|------|----------|----------|
| Pending | 资源不足/调度失败/PVC 未绑定 | `kubectl describe pod` -> Events |
| CrashLoopBackOff | 容器启动失败/命令错误/应用异常 | `kubectl logs --previous` |
| ImagePullBackOff | 镜像名错误/仓库不可达/无权限 | `kubectl describe pod` -> Events |
| ErrImagePull | 镜像不存在 | 检查镜像名和 Tag |
| OOMKilled | 内存 limit 太小 | `kubectl describe pod` -> Last State Exit Code 137 |
| Running 但 NotReady | 健康检查失败 | `kubectl describe pod` -> Events |

### kubectl exec - 进入容器调试

```bash
# 进入容器 shell
kubectl exec -it <pod-name> -- /bin/sh

# 指定容器（多容器 Pod）
kubectl exec -it <pod-name> -c <container> -- /bin/sh

# 执行单条命令
kubectl exec <pod-name> -- env
kubectl exec <pod-name> -- ls /app
kubectl exec <pod-name> -- cat /etc/config/app.conf
```
""",
        key_fields=[
            {"name": "kubectl describe pod", "description": "查看 Pod 详细信息、Events、Last State", "required": True, "example": "kubectl describe pod my-app-xxx-yyy"},
            {"name": "kubectl logs", "description": "查看容器日志输出", "required": True, "example": "kubectl logs my-app-xxx-yyy"},
            {"name": "kubectl logs --previous", "description": "查看上次崩溃时的日志（CrashLoopBackOff 排查关键）", "required": False, "example": "kubectl logs my-app-xxx-yyy --previous"},
            {"name": "kubectl exec", "description": "进入容器调试", "required": False, "example": "kubectl exec -it my-app -- /bin/sh"},
            {"name": "Exit Code", "description": "describe 中的退出码提示崩溃原因", "required": False, "example": "137=OOMKilled, 1=应用错误"},
        ],
        diagram="""\
  CrashLoopBackOff 排查流程

  ┌──────────────────────────────────────────────────────────────┐
  │  故障现象: Pod CrashLoopBackOff                              │
  │                                                              │
  │  $ kubectl get pods                                         │
  │  NAME       READY   STATUS             RESTARTS   AGE       │
  │  my-app-0   0/1     CrashLoopBackOff   5          3m        │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 1: kubectl describe pod                                │
  │                                                              │
  │  $ kubectl describe pod my-app-0                            │
  │                                                              │
  │  关键信息:                                                   │
  │  ┌────────────────────────────────────────────┐              │
  │  │ State:          Waiting                    │              │
  │  │   Reason:       CrashLoopBackOff           │              │
  │  │ Last State:     Terminated                 │              │
  │  │   Reason:       Error                      │              │
  │  │   Exit Code:    1                          │              │
  │  │   Started:      Mon, 10 Jan ...            │              │
  │  │   Finished:     Mon, 10 Jan ...            │              │
  │  └────────────────────────────────────────────┘              │
  │  Events:                                                     │
  │  ┌────────────────────────────────────────────┐              │
  │  │ Back-off restarting failed container       │              │
  │  │ Error: failed to start container           │              │
  │  └────────────────────────────────────────────┘              │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 2: kubectl logs                                        │
  │                                                              │
  │  $ kubectl logs my-app-0                                    │
  │  -> 查看当前容器日志（可能为空，因为容器刚启动就崩溃了）     │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 3: kubectl logs --previous  <- 关键！                  │
  │                                                              │
  │  $ kubectl logs my-app-0 --previous                         │
  │  -> 查看上次崩溃前的日志（通常包含错误信息）                 │
  │  例如:                                                       │
  │    "FATAL: Cannot connect to database at localhost:3306"    │
  │    "Error: config file /etc/app/config.yaml not found"      │
  │    "panic: runtime error: invalid memory address"           │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  根据日志修复问题                                            │
  │  -> 修正数据库连接配置                                       │
  │  -> 挂载 ConfigMap                                           │
  │  -> 修正启动命令                                             │
  │  -> 增加 memory limit                                        │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === CrashLoopBackOff 排查命令序列 ===

# 步骤 1: 确认 Pod 状态
kubectl get pods

# 步骤 2: 查看 Pod 详细信息和事件
kubectl describe pod my-app-0
# 重点关注:
#   - State / Last State / Exit Code
#   - Events 中的错误信息

# 步骤 3: 查看当前容器日志
kubectl logs my-app-0

# 步骤 4: 查看上次崩溃时的日志（关键！）
kubectl logs my-app-0 --previous

# 步骤 5: 如果容器还在运行，进入调试
kubectl exec -it my-app-0 -- /bin/sh

# 步骤 6: 查看集群事件
kubectl get events --sort-by=.metadata.creationTimestamp
""",
        common_errors=[
            "只看 kubectl logs 不看 kubectl logs --previous，错过崩溃前的关键日志",
            "不看 kubectl describe 的 Events 部分，遗漏调度或镜像拉取错误",
            "忽略 Last State 的 Exit Code，不知道崩溃原因（如 137=OOMKilled）",
            "忘记 -c 指定容器名（多容器 Pod 中 logs 默认看第一个容器）",
            "describe 后不看 Events 只看 spec 配置",
        ],
        tips=[
            "`kubectl logs --previous` 是排查 CrashLoopBackOff 的利器，必用！",
            "Exit Code 137 = OOMKilled，需要增加 memory limit",
            "Exit Code 1 = 应用错误，需要看日志确认具体原因",
            "用 `kubectl get events --sort-by=.metadata.creationTimestamp` 查看集群事件",
            "多容器 Pod 要用 `-c <container>` 指定容器名",
        ],
    ),
)


# ==================== Q28.3 网络排查挑战 ====================

def _check_283_network_debug(user_input: str) -> CheckResult:
    """Q28.3 验证排查 Service 连通性的 kubectl 命令序列"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 kubectl 网络排查命令序列",
            hints=["排查 Service 连通性需要 kubectl get endpoints 和 kubectl exec curl"],
        )

    lower = text.lower()

    # 检查包含 kubectl
    if "kubectl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["使用 kubectl get endpoints 和 kubectl exec 排查网络"],
        )

    # 检查 get endpoints（查看 Service 后端）
    has_endpoints = "endpoints" in lower or "get ep" in lower
    if not has_endpoints:
        return CheckResult(
            ok=False,
            error="缺少 kubectl get endpoints 命令（查看 Service 后端 Pod）",
            hints=["使用 kubectl get endpoints <svc-name> 检查 Service 是否有后端 Pod"],
        )

    # 检查 exec（进入容器测试连通性）
    has_exec = "exec" in lower
    if not has_exec:
        return CheckResult(
            ok=False,
            error="缺少 kubectl exec 命令（进入容器测试连通性）",
            hints=["使用 kubectl exec -it <pod> -- curl <service-ip> 测试网络连通性"],
        )

    # 检查 curl 或 wget（实际测试连通性）
    has_curl = "curl" in lower or "wget" in lower
    if not has_curl:
        return CheckResult(
            ok=False,
            error="缺少 curl 或 wget 命令（实际测试网络连通性）",
            hints=["在容器内用 curl <service-name>:<port> 测试 Service 连通性"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["网络排查命令序列正确！get endpoints + exec curl 是排查 Service 连通性的标准方法 🌐"],
    )


LEVEL_Q28_3 = Level(
    id="Q28.3",
    chapter="ch28",
    title="网络排查挑战 - Service 连通性",
    description="""
# CKA 挑战 - 网络排查 🌐

**核心考核**：使用 kubectl 命令排查 Service 连通性问题。

## 场景

一个 Service 创建后无法访问后端 Pod。你需要写出排查命令序列：
1. 查看 Service 的 Endpoints 是否正常
2. 进入容器用 curl 测试 Service 连通性
3. 检查 DNS 解析是否正常

## 任务

写出排查 Service 连通性的 kubectl 命令序列：
- `kubectl get endpoints` 检查 Service 后端
- `kubectl exec` 进入容器
- `curl` 测试连通性

## 提示

```bash
# 查看 Service 的 Endpoints
kubectl get endpoints <svc-name>

# 进入容器测试连通性
kubectl exec -it <pod-name> -- curl http://<svc-name>:<port>

# 测试 DNS 解析
kubectl exec -it <pod-name> -- nslookup <svc-name>
```
""",
    starter_yaml="""\
# 输入排查 Service 连通性的 kubectl 命令序列
# 1. kubectl get endpoints <svc-name>
# 2. kubectl exec -it <pod> -- curl <svc-name>:<port>
""",
    check_fn=_check_283_network_debug,
    lesson=Lesson(
        concept="""\
## CKA 网络排查方法论

Service 无法访问是 CKA 考试中的高频题型。掌握系统化的排查方法至关重要。

### Service 连通性排查流程

```
kubectl get svc             -> 确认 Service 存在，查看 ClusterIP
       |
       v
kubectl get endpoints       -> 检查 Endpoints 是否有后端 Pod
       |
       v
  +-- Endpoints 为空        -> selector 不匹配 / Pod 未 Ready
  +-- Endpoints 有 Pod       -> 继续排查
       |
       v
kubectl exec -- curl        -> 在容器内测试 Service 连通性
       |
       v
kubectl exec -- nslookup    -> 测试 DNS 解析
       |
       v
kubectl get networkpolicy   -> 检查 NetworkPolicy 是否阻断
```

### kubectl get endpoints - 检查 Service 后端

Service 通过 selector 选择后端 Pod，匹配的 Pod IP 会出现在 Endpoints 中：

```bash
# 查看 Service 的 Endpoints
kubectl get endpoints <svc-name>

# 输出示例（正常）:
# NAME         ENDPOINTS                           AGE
# nginx-svc    10.244.1.5:80,10.244.2.3:80        5m

# 输出示例（异常 - 无 Endpoints）:
# NAME         ENDPOINTS                           AGE
# nginx-svc    <none>                              5m
```

**Endpoints 为空的常见原因：**
1. Service selector 与 Pod labels 不匹配
2. Pod 未通过 readinessProbe（NotReady 状态不加入 Endpoints）
3. targetPort 与 containerPort 不匹配

### kubectl exec + curl - 测试连通性

```bash
# 进入容器测试 Service 连通性
kubectl exec -it <pod-name> -- curl http://<svc-name>:<port>

# 使用 ClusterIP 测试
kubectl exec -it <pod-name> -- curl http://10.96.0.100:80

# 测试 DNS 解析
kubectl exec -it <pod-name> -- nslookup <svc-name>
kubectl exec -it <pod-name> -- nslookup <svc-name>.<namespace>.svc.cluster.local

# 测试跨命名空间访问
kubectl exec -it <pod-name> -- curl http://<svc-name>.<namespace>:<port>

# 使用 busybox 调试 Pod（如果没有可用的容器）
kubectl run debug --image=busybox --rm -it --restart=Never -- sh
# 然后在容器内:
#   wget -qO- http://<svc-name>:<port>
#   nslookup <svc-name>
```

### NetworkPolicy 排查

如果 Endpoints 正常但 curl 失败，可能是 NetworkPolicy 阻断了流量：

```bash
# 查看命名空间中的 NetworkPolicy
kubectl get networkpolicy

# 查看 NetworkPolicy 详情
kubectl describe networkpolicy <np-name>

# 临时删除 NetworkPolicy 测试
kubectl delete networkpolicy <np-name>
```

### 常见网络故障

| 症状 | 可能原因 | 排查方法 |
|------|----------|----------|
| Endpoints 为空 | selector 不匹配 | 对比 svc selector 和 pod labels |
| curl 连接被拒 | targetPort 错误 | 检查 targetPort = containerPort |
| DNS 解析失败 | CoreDNS 异常 | `kubectl get pods -n kube-system -l k8s-app=kube-dns` |
| 超时 | NetworkPolicy 阻断 | `kubectl get networkpolicy` |
| 偶尔不通 | Pod 不健康 | 检查 readinessProbe |
""",
        key_fields=[
            {"name": "kubectl get endpoints", "description": "查看 Service 后端 Pod IP 列表，为空说明 selector 不匹配", "required": True, "example": "kubectl get endpoints nginx-svc"},
            {"name": "kubectl exec", "description": "进入容器执行命令测试连通性", "required": True, "example": "kubectl exec -it my-pod -- curl http://nginx-svc:80"},
            {"name": "curl / wget", "description": "在容器内测试 HTTP 连通性", "required": True, "example": "curl http://nginx-svc:80"},
            {"name": "nslookup", "description": "测试 DNS 解析是否正常", "required": False, "example": "nslookup nginx-svc"},
            {"name": "kubectl get networkpolicy", "description": "检查是否有 NetworkPolicy 阻断流量", "required": False, "example": "kubectl get networkpolicy"},
        ],
        diagram="""\
  Service 连通性排查流程

  ┌──────────────────────────────────────────────────────────────┐
  │  故障现象: Service 无法访问                                   │
  │                                                              │
  │  $ kubectl get svc                                          │
  │  NAME        TYPE        CLUSTER-IP      PORT(S)            │
  │  nginx-svc   ClusterIP   10.96.0.100     80/TCP             │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 1: kubectl get endpoints                               │
  │                                                              │
  │  $ kubectl get endpoints nginx-svc                          │
  │                                                              │
  │  情况 A: 有 Endpoints（正常）                                │
  │  ┌──────────────────────────────────────────┐               │
  │  │ 10.244.1.5:80, 10.244.2.3:80            │               │
  │  └──────────────────────────────────────────┘               │
  │  -> 继续 step 2                                             │
  │                                                              │
  │  情况 B: 无 Endpoints（异常！）                              │
  │  ┌──────────────────────────────────────────┐               │
  │  │ <none>                                   │               │
  │  └──────────────────────────────────────────┘               │
  │  -> 检查 selector 是否匹配 Pod labels                        │
  │  -> 检查 Pod 是否 Ready                                      │
  │  -> 检查 targetPort 是否正确                                 │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 2: kubectl exec -- curl                                │
  │                                                              │
  │  $ kubectl exec -it my-pod -- curl http://nginx-svc:80      │
  │                                                              │
  │  -> 测试 Service 名称 + 端口                                 │
  │  -> 也可以用 ClusterIP: kubectl exec -it my-pod --           │
  │    curl http://10.96.0.100:80                               │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 3: DNS 解析测试                                        │
  │                                                              │
  │  $ kubectl exec -it my-pod -- nslookup nginx-svc            │
  │  -> 确认 DNS 能解析 Service 名称                             │
  │  -> 如果失败: 检查 CoreDNS 是否正常运行                      │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 4: 检查 NetworkPolicy                                  │
  │                                                              │
  │  $ kubectl get networkpolicy                                │
  │  -> 如果有 NP，检查是否阻断了流量                            │
  │  -> 临时删除 NP 测试: kubectl delete networkpolicy <name>   │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === Service 连通性排查命令序列 ===

# 步骤 1: 查看 Service 信息
kubectl get svc nginx-svc

# 步骤 2: 检查 Endpoints（关键！）
kubectl get endpoints nginx-svc
# 如果为空 -> 检查 selector 和 Pod labels

# 步骤 3: 进入容器测试连通性
kubectl exec -it my-pod -- curl http://nginx-svc:80

# 步骤 4: 测试 DNS 解析
kubectl exec -it my-pod -- nslookup nginx-svc

# 步骤 5: 检查 NetworkPolicy
kubectl get networkpolicy

# 步骤 6: 如果没有可用容器，启动调试 Pod
kubectl run debug --image=busybox --rm -it --restart=Never -- sh
# 在容器内:
#   wget -qO- http://nginx-svc:80
#   nslookup nginx-svc
""",
        common_errors=[
            "不看 Endpoints 直接 curl，不知道 Service 后端是否正常",
            "selector 与 Pod labels 不匹配导致 Endpoints 为空（最常见原因）",
            "Pod 处于 NotReady 状态（readinessProbe 未通过），不加入 Endpoints",
            "targetPort 与 containerPort 不匹配，curl 连接被拒绝",
            "忘记检查 NetworkPolicy，流量被策略阻断",
            "DNS 解析使用短名称但跨命名空间访问时未指定全限定名",
        ],
        tips=[
            "`kubectl get endpoints <svc>` 是排查 Service 的第一步",
            "Endpoints 为空则检查 selector；Endpoints 有值但 curl 失败则检查 NetworkPolicy",
            "用 `kubectl run debug --image=busybox --rm -it -- sh` 快速启动调试容器",
            "跨命名空间访问要用全限定名: <svc>.<ns>.svc.cluster.local",
            "CoreDNS 异常会导致所有 Service DNS 解析失败",
        ],
    ),
)


# ==================== Q28.4 RBAC 排查挑战 ====================

def _check_284_rbac_debug(user_input: str) -> CheckResult:
    """Q28.4 验证检查权限的 kubectl auth can-i 命令"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 kubectl RBAC 排查命令",
            hints=["使用 kubectl auth can-i 命令检查权限"],
        )

    lower = text.lower()

    # 检查包含 kubectl
    if "kubectl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["使用 kubectl auth can-i 命令检查权限"],
        )

    # 检查 auth 子命令
    if "auth" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 auth 子命令",
            hints=["使用 kubectl auth can-i 检查权限"],
        )

    # 检查 can-i
    if "can-i" not in lower and "can" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 can-i 子命令",
            hints=["正确格式: kubectl auth can-i <verb> <resource>"],
        )

    # 检查 --as 参数（模拟用户身份）
    has_as = "--as" in lower

    return CheckResult(
        ok=True, state=None,
        hints=["RBAC 权限检查命令正确！auth can-i 是排查权限问题的核心工具 🔐" + ("（还包含 --as 模拟身份）" if has_as else "")],
    )


LEVEL_Q28_4 = Level(
    id="Q28.4",
    chapter="ch28",
    title="RBAC 排查挑战 - 权限检查",
    description="""
# CKA 挑战 - RBAC 权限排查 🔐

**核心考核**：使用 kubectl auth can-i 命令检查和排查 RBAC 权限问题。

## 场景

一个 ServiceAccount 无法获取 Pod 列表。你需要写出排查命令：
1. 检查当前用户是否有特定权限
2. 模拟 ServiceAccount 身份检查权限
3. 列出所有权限

## 任务

写出检查 RBAC 权限的 kubectl 命令：
- `kubectl auth can-i` 检查权限
- `--as` 模拟特定用户/ServiceAccount

## 提示

```bash
# 检查当前用户权限
kubectl auth can-i get pods

# 模拟 ServiceAccount 检查权限
kubectl auth can-i get pods --as=system:serviceaccount:default:app-sa

# 列出所有权限
kubectl auth can-i --list
```
""",
    starter_yaml="""\
# 输入 kubectl auth can-i 命令
# kubectl auth can-i <verb> <resource>
# kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<ns>:<sa>
""",
    check_fn=_check_284_rbac_debug,
    lesson=Lesson(
        concept="""\
## CKA RBAC 权限排查

RBAC（基于角色的访问控制）是 Kubernetes 安全的核心。CKA 考试中经常需要排查权限问题。

### kubectl auth can-i - 权限检查利器

`kubectl auth can-i` 是排查 RBAC 问题最直接的工具：

```bash
# 检查当前用户是否有 get pods 权限
kubectl auth can-i get pods
# 输出: yes / no

# 检查特定权限
kubectl auth can-i create deployments
kubectl auth can-i delete pods
kubectl auth can-i list secrets
kubectl auth can-i update services

# 模拟特定用户身份检查权限
kubectl auth can-i get pods --as=system:serviceaccount:default:app-sa

# 模拟用户检查权限
kubectl auth can-i get pods --as=jane

# 模拟用户 + 命名空间
kubectl auth can-i get pods --as=system:serviceaccount:default:app-sa -n production

# 列出当前用户的所有权限
kubectl auth can-i --list

# 列出特定 SA 的所有权限
kubectl auth can-i --list --as=system:serviceaccount:default:app-sa
```

### RBAC 排查流程

```
kubectl auth can-i <verb> <resource> --as=<user>
       |
       v
  +-- yes -> 权限正常，问题在其他地方
  +-- no  -> 需要排查 RBAC 配置
       |
       v
kubectl get role,rolebinding -n <ns>
       |
       v
kubectl get clusterrole,clusterrolebinding
       |
       v
kubectl describe role <name> -n <ns>
kubectl describe rolebinding <name> -n <ns>
       |
       v
  +-- Role rules 正确 -> 检查 RoleBinding 的 subjects
  +-- Role rules 错误 -> 修正 rules
  +-- RoleBinding 未绑定 SA -> 修正 subjects
```

### RBAC 四要素

```
ServiceAccount (身份) -> RoleBinding (绑定) -> Role (权限) -> API 操作
```

1. **ServiceAccount**：Pod 的身份标识
2. **Role**：命名空间级权限规则（ClusterRole 是集群级）
3. **RoleBinding**：将 Role 绑定到 SA/User/Group
4. **ClusterRole/ClusterRoleBinding**：集群级权限

### 常用 RBAC 排查命令

```bash
# 查看 Role 和 RoleBinding
kubectl get role,rolebinding -n <namespace>

# 查看 ClusterRole 和 ClusterRoleBinding
kubectl get clusterrole,clusterrolebinding

# 查看 Role 详情（检查 rules）
kubectl describe role <name> -n <namespace>

# 查看 RoleBinding 详情（检查 roleRef 和 subjects）
kubectl describe rolebinding <name> -n <namespace>

# 检查特定 SA 的权限
kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>

# 检查 SA 是否可以执行特定操作
kubectl auth can-i get pods --as=system:serviceaccount:default:app-sa
kubectl auth can-i create pods --as=system:serviceaccount:default:app-sa
kubectl auth can-i delete pods --as=system:serviceaccount:default:app-sa
```

### --as 参数格式

| 身份类型 | --as 格式 | 示例 |
|----------|-----------|------|
| 普通用户 | `--as=<username>` | `--as=jane` |
| ServiceAccount | `--as=system:serviceaccount:<ns>:<sa>` | `--as=system:serviceaccount:default:app-sa` |
| 组 | `--as-group=<group>` | `--as-group=dev-team` |
""",
        key_fields=[
            {"name": "kubectl auth can-i", "description": "检查是否有特定权限，输出 yes/no", "required": True, "example": "kubectl auth can-i get pods"},
            {"name": "--as", "description": "模拟特定用户/SA 身份检查权限", "required": False, "example": "--as=system:serviceaccount:default:app-sa"},
            {"name": "--list", "description": "列出用户的所有权限", "required": False, "example": "kubectl auth can-i --list"},
            {"name": "kubectl get role/rolebinding", "description": "查看 RBAC 资源", "required": False, "example": "kubectl get role,rolebinding -n default"},
            {"name": "-n <namespace>", "description": "指定命名空间检查权限", "required": False, "example": "kubectl auth can-i get pods -n production"},
        ],
        diagram="""\
  RBAC 权限排查流程

  ┌──────────────────────────────────────────────────────────────┐
  │  故障现象: ServiceAccount 无法操作资源                       │
  │                                                              │
  │  $ kubectl auth can-i get pods                               │
  │    --as=system:serviceaccount:default:app-sa                │
  │  -> no                                                       │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 1: 列出所有权限                                        │
  │                                                              │
  │  $ kubectl auth can-i --list                                 │
  │    --as=system:serviceaccount:default:app-sa                │
  │                                                              │
  │  -> 查看 SA 当前拥有的所有权限                               │
  │  -> 确认缺少哪些权限                                        │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 2: 查看 RBAC 资源                                      │
  │                                                              │
  │  $ kubectl get role,rolebinding -n default                   │
  │  $ kubectl get clusterrole,clusterrolebinding                │
  │                                                              │
  │  -> 查看是否有匹配的 Role/RoleBinding                        │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 3: 检查 RoleBinding                                    │
  │                                                              │
  │  $ kubectl describe rolebinding <name> -n default            │
  │                                                              │
  │  ┌──────────────────────────────────────────┐               │
  │  │ roleRef:                                 │               │
  │  │   kind: Role                             │               │
  │  │   name: pod-reader                       │               │
  │  │ subjects:                                │               │
  │  │ - kind: ServiceAccount                   │               │
  │  │   name: app-sa       <- 是否匹配？        │               │
  │  └──────────────────────────────────────────┘               │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 4: 检查 Role rules                                     │
  │                                                              │
  │  $ kubectl describe role pod-reader -n default               │
  │                                                              │
  │  ┌──────────────────────────────────────────┐               │
  │  │ rules:                                  │               │
  │  │ - apiGroups: [""]                        │               │
  │  │   resources: ["pods"]  <- 是否包含？      │               │
  │  │   verbs: ["get", "list"] <- 是否包含？    │               │
  │  └──────────────────────────────────────────┘               │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  修复: 创建/修改 Role 和 RoleBinding                         │
  │  -> 确保 Role rules 包含所需 verbs                           │
  │  -> 确保 RoleBinding subjects 包含正确的 SA                  │
  │  -> 验证: kubectl auth can-i get pods --as=...              │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === RBAC 权限排查命令序列 ===

# 步骤 1: 检查当前用户权限
kubectl auth can-i get pods

# 步骤 2: 模拟 ServiceAccount 检查权限
kubectl auth can-i get pods --as=system:serviceaccount:default:app-sa

# 步骤 3: 列出 SA 的所有权限
kubectl auth can-i --list --as=system:serviceaccount:default:app-sa

# 步骤 4: 查看 Role 和 RoleBinding
kubectl get role,rolebinding -n default

# 步骤 5: 查看 RoleBinding 详情
kubectl describe rolebinding pod-reader-binding -n default

# 步骤 6: 查看 Role 详情
kubectl describe role pod-reader -n default

# 步骤 7: 查看 ClusterRole
kubectl get clusterrole | grep pod
kubectl describe clusterrole <name>
""",
        common_errors=[
            "忘记 --as 参数，检查的是当前用户权限而非目标 SA",
            "--as 格式错误，正确格式是 system:serviceaccount:<ns>:<sa>",
            "Role rules 中 apiGroups 核心组写成 ['v1']（应该是空字符串 ''）",
            "RoleBinding 的 subjects 中 SA 名称或命名空间不匹配",
            "RoleBinding 绑定了 Role 但 Role 的 rules 缺少所需 verb",
            "命名空间级别权限用了 ClusterRole 但没创建 ClusterRoleBinding",
        ],
        tips=[
            "`kubectl auth can-i --list --as=<user>` 一次列出所有权限，非常高效",
            "--as 格式: system:serviceaccount:<namespace>:<sa-name>",
            "apiGroups 的核心组是空字符串 ''，不是 'v1'",
            "权限不足时先查 RoleBinding subjects，再查 Role rules",
            "用 `kubectl auth can-i <verb> <resource> -n <ns>` 检查命名空间级权限",
        ],
    ),
)


# ==================== Q28.5 综合挑战 ====================

def _check_285_comprehensive(user_input: str) -> CheckResult:
    """Q28.5 综合挑战 - 多步骤 kubectl 操作（命名空间+部署+网络策略+验证）"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入 kubectl 命令序列",
            hints=["综合挑战需要多个 kubectl 命令完成多步骤操作"],
        )

    lower = text.lower()

    # 检查包含 kubectl
    if "kubectl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["使用多个 kubectl 命令完成综合操作"],
        )

    # 统计 kubectl 命令数量
    kubectl_count = lower.count("kubectl")

    # 检查包含创建命名空间
    has_namespace = "namespace" in lower or "ns " in lower
    if not has_namespace:
        return CheckResult(
            ok=False,
            error="缺少创建/使用命名空间的操作",
            hints=["使用 kubectl create namespace <name> 创建命名空间"],
        )

    # 检查包含部署操作
    has_deploy = "run" in lower or "apply" in lower or "create deployment" in lower
    if not has_deploy:
        return CheckResult(
            ok=False,
            error="缺少部署应用的操作",
            hints=["使用 kubectl run 或 kubectl apply 部署应用"],
        )

    # 检查包含验证操作
    has_verify = "get" in lower
    if not has_verify:
        return CheckResult(
            ok=False,
            error="缺少验证操作（kubectl get）",
            hints=["使用 kubectl get pods/svc 验证部署结果"],
        )

    # 至少需要 3 个 kubectl 命令
    if kubectl_count < 3:
        return CheckResult(
            ok=False,
            error=f"命令数量不足（仅 {kubectl_count} 个 kubectl 命令），综合挑战需要至少 3 个步骤",
            hints=["综合挑战需要: 创建命名空间 + 部署应用 + 验证结果，至少 3 个 kubectl 命令"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=[f"综合操作完成！共 {kubectl_count} 个 kubectl 命令，多步骤操作是 CKA 考试的核心能力 🏆"],
    )


LEVEL_Q28_5 = Level(
    id="Q28.5",
    chapter="ch28",
    title="综合挑战 - 多步骤操作",
    description="""
# CKA 综合挑战 🏆

**终极考核**：使用 kubectl 命令完成多步骤综合操作。

## 场景

你需要在一个新命名空间中完成以下操作：
1. 创建命名空间 `production`
2. 在该命名空间中部署 nginx 应用
3. 暴露 Service
4. 验证所有资源是否正常

## 任务

写出完整的 kubectl 命令序列，包含至少 3 个 kubectl 命令：
- `kubectl create namespace` 创建命名空间
- `kubectl run` 或 `kubectl apply` 部署应用
- `kubectl expose` 暴露 Service
- `kubectl get` 验证结果

## 提示

```bash
# 1. 创建命名空间
kubectl create namespace production

# 2. 在命名空间中部署应用
kubectl run nginx-app --image=nginx:1.25 -n production

# 3. 暴露 Service
kubectl expose deployment nginx-app --port=80 -n production

# 4. 验证
kubectl get pods -n production
kubectl get svc -n production
```
""",
    starter_yaml="""\
# 输入完整的 kubectl 命令序列
# 1. kubectl create namespace <name>
# 2. kubectl run <name> --image=<image> -n <ns>
# 3. kubectl expose deployment <name> --port=<port> -n <ns>
# 4. kubectl get pods -n <ns>
""",
    check_fn=_check_285_comprehensive,
    lesson=Lesson(
        concept="""\
## CKA 综合操作能力

CKA 考试的最后一类题目是综合操作——需要多个 kubectl 命令组合完成复杂任务。这类题目考验对 Kubernetes 资源体系的整体理解和命令熟练度。

### 常见综合操作场景

#### 场景 1：命名空间隔离部署

```bash
# 创建命名空间
kubectl create namespace production

# 在命名空间中部署应用
kubectl run nginx-app --image=nginx:1.25 -n production

# 暴露 Service
kubectl expose deployment nginx-app --port=80 -n production

# 验证
kubectl get pods,svc -n production
```

#### 场景 2：ConfigMap + Secret + Pod

```bash
# 创建 ConfigMap
kubectl create configmap app-config --from-literal=KEY=value -n production

# 创建 Secret
kubectl create secret generic db-secret --from-literal=password=mysecret -n production

# 部署 Pod 使用配置
kubectl run app --image=nginx:1.25 --dry-run=client -o yaml > pod.yaml
# 编辑 pod.yaml 添加 envFrom / volumeMounts
kubectl apply -f pod.yaml

# 验证
kubectl get pods -n production
kubectl exec -it app -n production -- env
```

#### 场景 3：网络策略隔离

```bash
# 创建命名空间
kubectl create namespace secure-app

# 部署后端应用
kubectl run backend --image=nginx:1.25 -n secure-app
kubectl expose deployment backend --port=80 -n secure-app

# 部署前端应用
kubectl run frontend --image=nginx:1.25 -n secure-app
kubectl expose deployment frontend --port=80 -n secure-app

# 创建 NetworkPolicy 限制后端只接受前端流量
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: secure-app
spec:
  podSelector:
    matchLabels:
      run: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          run: frontend
    ports:
    - protocol: TCP
      port: 80
EOF

# 验证
kubectl get networkpolicy -n secure-app
kubectl get pods,svc -n secure-app
```

#### 场景 4：扩容 + 滚动更新 + 回滚

```bash
# 部署应用
kubectl run web --image=nginx:1.25

# 扩容
kubectl scale deployment web --replicas=5

# 更新镜像
kubectl set image deployment/web nginx=nginx:1.26

# 查看滚动更新状态
kubectl rollout status deployment/web

# 如果出问题，回滚
kubectl rollout undo deployment/web

# 查看历史
kubectl rollout history deployment/web
```

### CKA 考试时间管理

```
2 小时考试时间分配建议:
- 简单部署题（run/expose/scale）: 5-10 分钟/题
- 故障排查题（describe/logs）: 10-15 分钟/题
- 网络策略题（NetworkPolicy）: 10-15 分钟/题
- RBAC 题（auth/role/rolebinding）: 10-15 分钟/题
- 综合题（多步骤）: 15-20 分钟/题
- 检查和验证: 最后 15 分钟
```

### CKA 考试速查命令

```bash
# 创建资源
kubectl create namespace <name>
kubectl create configmap <name> --from-literal=<k>=<v>
kubectl create secret generic <name> --from-literal=<k>=<v>
kubectl run <name> --image=<image>
kubectl expose deployment <name> --port=<port>

# 管理资源
kubectl scale deployment <name> --replicas=<n>
kubectl set image deployment/<name> <container>=<image>
kubectl rollout undo deployment/<name>

# 查看资源
kubectl get pods,svc,deploy -n <ns>
kubectl get pods -o wide
kubectl describe pod <name>

# 排查
kubectl logs <pod> --previous
kubectl exec -it <pod> -- /bin/sh
kubectl auth can-i <verb> <resource> --as=<user>

# 生成 YAML
kubectl run <name> --image=<image> --dry-run=client -o yaml
kubectl create configmap <name> --from-literal=k=v --dry-run=client -o yaml
```
""",
        key_fields=[
            {"name": "kubectl create namespace", "description": "创建命名空间实现资源隔离", "required": True, "example": "kubectl create namespace production"},
            {"name": "kubectl run / apply", "description": "部署应用到命名空间", "required": True, "example": "kubectl run nginx --image=nginx:1.25 -n production"},
            {"name": "kubectl expose", "description": "暴露 Service", "required": False, "example": "kubectl expose deployment nginx --port=80 -n production"},
            {"name": "kubectl get", "description": "验证资源状态", "required": True, "example": "kubectl get pods,svc -n production"},
            {"name": "-n / --namespace", "description": "指定命名空间，综合操作中必须注意", "required": True, "example": "-n production"},
        ],
        diagram="""\
  CKA 综合操作流程

  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 1: 创建命名空间                                        │
  │                                                              │
  │  $ kubectl create namespace production                      │
  │                                                              │
  │  ┌──────────────────────────────────┐                       │
  │  │  namespace: production            │                       │
  │  │  (资源隔离)                       │                       │
  │  └──────────────────────────────────┘                       │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 2: 部署应用                                            │
  │                                                              │
  │  $ kubectl run nginx-app --image=nginx:1.25 -n production   │
  │                                                              │
  │  ┌──────────────────────────────────┐                       │
  │  │  namespace: production            │                       │
  │  │  ┌──────────────────────┐         │                       │
  │  │  │ Deployment: nginx-app │         │                       │
  │  │  │  replicas: 1          │         │                       │
  │  │  │  ┌──────────────────┐ │         │                       │
  │  │  │  │ Pod: nginx-app-0 │ │         │                       │
  │  │  │  │  image: nginx    │ │         │                       │
  │  │  │  └──────────────────┘ │         │                       │
  │  │  └──────────────────────┘         │                       │
  │  └──────────────────────────────────┘                       │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 3: 暴露 Service                                        │
  │                                                              │
  │  $ kubectl expose deployment nginx-app --port=80            │
  │    -n production                                             │
  │                                                              │
  │  ┌──────────────────────────────────┐                       │
  │  │  namespace: production            │                       │
  │  │  ┌──────────────────────┐         │                       │
  │  │  │ Service: nginx-app   │         │                       │
  │  │  │  ClusterIP: 10.96... │         │                       │
  │  │  │  port: 80            │         │                       │
  │  │  └──────────┬───────────┘         │                       │
  │  │             │ selector             │                       │
  │  │             v                      │                       │
  │  │  ┌──────────────────────┐         │                       │
  │  │  │ Pod: nginx-app-0     │         │                       │
  │  │  └──────────────────────┘         │                       │
  │  └──────────────────────────────────┘                       │
  └──────────────────────────┬───────────────────────────────────┘
                             │
                             v
  ┌──────────────────────────────────────────────────────────────┐
  │  步骤 4: 验证                                                │
  │                                                              │
  │  $ kubectl get pods,svc -n production                       │
  │  NAME                        READY   STATUS    AGE           │
  │  pod/nginx-app-xxx           1/1     Running   1m           │
  │  service/nginx-app           ClusterIP  10.96.x.x  80/TCP   │
  │                                                              │
  │  $ kubectl get endpoints nginx-app -n production            │
  │  NAME         ENDPOINTS           AGE                       │
  │  nginx-app    10.244.1.5:80      1m                        │
  └──────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# === CKA 综合操作完整命令序列 ===

# 步骤 1: 创建命名空间
kubectl create namespace production

# 步骤 2: 在命名空间中部署应用
kubectl run nginx-app --image=nginx:1.25 -n production

# 步骤 3: 暴露 Service
kubectl expose deployment nginx-app --port=80 --target-port=80 -n production

# 步骤 4: 扩容
kubectl scale deployment nginx-app --replicas=3 -n production

# 步骤 5: 验证所有资源
kubectl get pods,svc,deploy -n production

# 步骤 6: 检查 Endpoints
kubectl get endpoints nginx-app -n production

# 步骤 7: 测试连通性
kubectl exec -it $(kubectl get pods -n production -l run=nginx-app -o jsonpath='{.items[0].metadata.name}') -n production -- curl -s http://nginx-app:80
""",
        common_errors=[
            "忘记在每个 kubectl 命令后加 -n <namespace>，资源创建到 default 命名空间",
            "命名空间名称写错（如 Production vs production，K8s 命名空间区分大小写）",
            "expose 时忘记指定 -n，Service 创建在错误的命名空间",
            "验证时忘记 -n，看不到新创建的资源",
            "综合操作中没有验证步骤，不确定操作是否成功",
            "时间管理不当，在简单题上花太多时间",
        ],
        tips=[
            "综合操作中每个 kubectl 命令都要带 -n <namespace>，这是最常见的错误",
            "用 `kubectl get all -n <ns>` 一次查看命名空间中所有资源",
            "CKA 考试时间紧张，优先用命令而非 YAML，省下时间给复杂题",
            "每完成一步就验证，不要等所有步骤做完再检查",
            "用 `kubectl get pods -w` 实时观察 Pod 状态变化",
            "最后留 15 分钟检查所有题目，确保没有遗漏",
        ],
    ),
)


# ==================== 章节导出 ====================

CHAPTER_28_LEVELS = [
    LEVEL_Q28_1,
    LEVEL_Q28_2,
    LEVEL_Q28_3,
    LEVEL_Q28_4,
    LEVEL_Q28_5,
]
