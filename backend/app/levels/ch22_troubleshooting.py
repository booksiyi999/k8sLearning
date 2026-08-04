"""Chapter 22: 故障排查 - Pod/Service/Node/控制平面诊断（5 关）

Q22.1 Pod 状态诊断 - fix CrashLoopBackOff scenario
Q22.2 Service 连通性排查 - validate Service+Endpoints fix
Q22.3 Node NotReady - validate node troubleshooting steps
Q22.4 控制平面故障 - validate control plane component checks
Q22.5 集群实战 - complete troubleshooting workflow
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q22.1 Pod 状态诊断 ====================

def _check_221_pod_crashloop(user_yaml: str) -> CheckResult:
    """Q22.1 修复 CrashLoopBackOff - 用户提交修复后的 Pod YAML

    场景: 一个 Pod 因为命令错误导致 CrashLoopBackOff。
    用户需要提交修正后的 YAML，确保 Pod 能正常运行。
    """
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["你需要 apply 一个 kind: Pod 的 YAML"],
        )

    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查 image 不为空
    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["CrashLoopBackOff 常见原因之一是镜像名错误或不存在"],
        )

    # 检查 command 或 args 存在（修复后的 Pod 应该有正确的启动命令）
    has_command = bool(c.get("command"))
    has_args = bool(c.get("args"))
    if not has_command and not has_args:
        return CheckResult(
            ok=False,
            error="容器缺少 command 或 args",
            hints=[
                "原始 Pod 的命令有误导致 CrashLoopBackOff",
                "添加正确的 command 或 args 让容器能正常启动",
            ],
        )

    # 检查不能使用会导致崩溃的命令（如 sleep 值为负数、不存在的二进制等）
    command = c.get("command", [])
    if isinstance(command, list) and command:
        cmd_str = " ".join(str(x) for x in command)
        # 检查不是明显错误的命令
        if "exit 1" in cmd_str or "false" in cmd_str.lower():
            return CheckResult(
                ok=False,
                error=f"command '{cmd_str}' 仍然会导致容器立即退出",
                hints=["使用能持续运行的命令，如 'sleep 3600' 或正确的应用启动命令"],
            )

    # 检查资源限制（修复后的 Pod 应该有合理的 resources）
    resources = c.get("resources", {})
    if isinstance(resources, dict) and resources:
        # 有资源限制是加分项，但不强制
        pass

    return CheckResult(
        ok=True, state=state,
        hints=["Pod 修复成功！正确的 command/image 是解决 CrashLoopBackOff 的关键 🔍"],
    )


LEVEL_Q22_1 = Level(
    id="Q22.1",
    chapter="ch22",
    title="Pod 状态诊断",
    description="""
# Pod 状态诊断 - CrashLoopBackOff 🔍

一个 Pod 陷入了 `CrashLoopBackOff` 状态。容器不断崩溃重启，需要你找出问题并修复。

## 场景

原始 Pod YAML（有问题的）：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    command: ["exit 1"]  # ← 这就是问题！容器启动后立即退出
```

## 任务

提交修正后的 Pod YAML：
- 修正 `command` 让容器能正常运行
- 确保 `image` 正确
- 添加合理的 `command` 或 `args`

## 提示

修复后的 YAML：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    command: ["nginx", "-g", "daemon off;"]
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    # command: ["exit 1"]  ← 修复这个错误的命令
    command: []
""",
    check_fn=_check_221_pod_crashloop,
    lesson=Lesson(
        concept="""\
## CrashLoopBackOff 诊断

`CrashLoopBackOff` 是 Kubernetes 中最常见的 Pod 故障状态之一，表示容器反复崩溃并被重启。

### 常见原因

| 原因 | 症状 | 排查方法 |
|------|------|----------|
| 命令/参数错误 | 容器启动后立即退出 | `kubectl logs <pod>` |
| 镜像不存在 | ImagePullBackOff → CrashLoopBackOff | `kubectl describe pod <pod>` |
| 应用配置错误 | 应用启动失败 | `kubectl logs <pod>` |
| 资源不足 | OOMKilled | `kubectl describe pod <pod>` |
| 存活探针失败 | 探针检测失败导致重启 | `kubectl describe pod <pod>` |
| 权限不足 | 应用无法读取文件/端口 | `kubectl logs <pod>` |

### 排查步骤

```
1. kubectl get pods                    → 查看 Pod 状态
2. kubectl describe pod <pod>          → 查看事件和状态
3. kubectl logs <pod>                  → 查看容器日志
4. kubectl logs <pod> --previous       → 查看上次崩溃的日志
5. kubectl get events --sort-by=.metadata.creationTimestamp
```

### 关键日志查看

- `kubectl logs` — 当前容器的日志
- `kubectl logs --previous` — **上次崩溃前**的日志（非常关键！）
- `kubectl describe pod` — Events 部分显示拉取、启动、探针等事件
""",
        key_fields=[
            {"name": "command", "description": "容器启动命令，错误命令导致 CrashLoopBackOff", "required": True, "example": "[\"nginx\", \"-g\", \"daemon off;\"]"},
            {"name": "image", "description": "容器镜像，错误镜像导致启动失败", "required": True, "example": "nginx:1.25"},
            {"name": "resources", "description": "资源限制，不足会导致 OOMKilled", "required": False, "example": "limits: memory: 128Mi"},
            {"name": "livenessProbe", "description": "存活探针，配置错误会导致反复重启", "required": False, "example": "httpGet: path: /healthz"},
        ],
        diagram="""\
  CrashLoopBackOff 排查流程

  ┌──────────────┐
  │ kubectl get  │     CrashLoopBackOff
  │ pods         │ ──────────────────────┐
  └──────┬───────┘                       │
         ▼                               │
  ┌──────────────┐                       │
  │ kubectl      │     Events:           │
  │ describe pod │     - Pulling image   │
  │              │     - Created         │
  └──────┬───────┘     - Started         │
         ▼             - Back-off        │
  ┌──────────────┐                       │
  │ kubectl logs │     Error: exit code 1│
  │ <pod>        │ <─────────────────────┘
  └──────┬───────┘
         │ 如果当前日志为空
         ▼
  ┌──────────────────────┐
  │ kubectl logs         │
  │ <pod> --previous     │  ← 查看崩溃前日志！
  │                      │    "command not found"
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │  修复 command/image  │
  │  kubectl apply -f    │
  └──────────────────────┘
""",
        example_yaml="""\
# 修复 CrashLoopBackOff

# 问题 YAML（崩溃）:
# command: ["exit 1"]

# 修复 YAML（正常运行）:
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    command: ["nginx", "-g", "daemon off;"]
    resources:
      limits:
        memory: "128Mi"
        cpu: "250m"
      requests:
        memory: "64Mi"
        cpu: "125m"
""",
        common_errors=[
            "只看当前日志不看 --previous，看不到崩溃前的错误信息",
            "command 使用 shell 内置命令（如 sleep）但未指定 shell 入口",
            "livenessProbe 检测路径错误，导致健康检查失败触发重启",
            "resources.limits 设置过低，容器 OOMKilled 后重启循环",
        ],
        tips=[
            "kubectl logs --previous 是排查 CrashLoopBackOff 的利器",
            "用 kubectl describe pod 查看 Events 中的详细错误",
            "OOMKilled 会在 describe 的 Last State 中显示 exit code 137",
            "排查时先确认镜像是否存在，再看命令是否正确",
        ],
    ),
)


# ==================== Q22.2 Service 连通性排查 ====================

def _check_222_service_endpoints(user_yaml: str) -> CheckResult:
    """Q22.2 修复 Service 连通性 - Service selector 不匹配 Pod labels

    场景: Service 的 selector 与 Pod 的 labels 不匹配，导致没有 Endpoints。
    用户需要提交修正后的 YAML（Service + Pod），确保 selector 匹配。
    """
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查是否有 Service
    if not state.services:
        return CheckResult(
            ok=False,
            error="没有创建任何 Service",
            hints=["需要创建 kind: Service 的 YAML"],
        )

    # 检查是否有 Pod
    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["需要同时创建 Pod，让 Service 有 Endpoints"],
        )

    svc_name = next(iter(state.services))
    svc = state.services[svc_name]
    svc_spec = svc.get("spec", {})
    if not isinstance(svc_spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    selector = svc_spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(
            ok=False,
            error="Service 缺少 spec.selector",
            hints=["Service 需要 selector 来匹配后端 Pod"],
        )

    # 检查是否有 Pod 的 labels 匹配 Service 的 selector
    matched_pods = []
    for pod_name, pod in state.pods.items():
        pod_labels = pod.get("metadata", {}).get("labels", {})
        if not isinstance(pod_labels, dict):
            continue
        if all(pod_labels.get(k) == v for k, v in selector.items()):
            matched_pods.append(pod_name)

    if not matched_pods:
        return CheckResult(
            ok=False,
            error=f"Service '{svc_name}' 的 selector {selector} 没有匹配到任何 Pod",
            hints=[
                "检查 Service selector 与 Pod labels 是否一致",
                f"Service selector: {selector}",
                "确保 Pod 的 metadata.labels 包含 selector 中的所有 key-value",
            ],
        )

    # 检查 Service 有 ports 配置
    ports = svc_spec.get("ports", [])
    if not isinstance(ports, list) or not ports:
        return CheckResult(
            ok=False,
            error="Service 缺少 spec.ports 配置",
            hints=["Service 需要配置 ports 指定端口映射"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[f"Service '{svc_name}' 已匹配到 {len(matched_pods)} 个 Pod，连通性正常 🔗"],
    )


LEVEL_Q22_2 = Level(
    id="Q22.2",
    chapter="ch22",
    title="Service 连通性排查",
    description="""
# Service 连通性排查 🔗

一个 Service 无法访问后端 Pod，排查发现没有 Endpoints。需要修复 Service 和 Pod 的配置。

## 场景

问题配置：
```yaml
# Service selector 是 app: web
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web          # ← selector
  ports:
  - port: 80
    targetPort: 8080
---
# 但 Pod 的 labels 是 app: website  ← 不匹配！
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: website      # ← 与 selector 不一致
spec:
  containers:
  - name: nginx
    image: nginx:1.25
```

## 任务

提交修复后的 YAML（Service + Pod），确保：
- Service 的 `selector` 与 Pod 的 `labels` 匹配
- Service 有正确的 `ports` 配置
- Pod 有正确的 `labels`

## 提示

修复后的配置（统一 label）：
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web          # ← 与 selector 匹配
spec:
  containers:
  - name: nginx
    image: nginx:1.25
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: website  # ← 修复：改为 app: web
spec:
  containers:
  - name: nginx
    image: nginx:1.25
""",
    check_fn=_check_222_service_endpoints,
    lesson=Lesson(
        concept="""\
## Service 连通性排查

当 Service 无法访问后端 Pod 时，最常见的原因是 **selector 与 Pod labels 不匹配**，导致没有 Endpoints。

### 排查步骤

```
1. kubectl get svc               → 确认 Service 存在
2. kubectl get endpoints <svc>   → 检查是否有 Endpoints
3. kubectl describe svc <svc>    → 查看 selector
4. kubectl get pods --show-labels → 查看 Pod 的 labels
5. 对比 selector 和 labels       → 找出不匹配的 key
```

### 常见 Service 连通性问题

| 问题 | 症状 | 解决方法 |
|------|------|----------|
| selector 不匹配 | Endpoints 为空 | 统一 selector 和 labels |
| targetPort 错误 | 连接被拒绝 | 修正 targetPort 匹配容器端口 |
| Pod 未就绪 | Endpoints 为空 | 检查 readinessProbe |
| 命名空间不同 | Endpoints 为空 | Service 和 Pod 必须在同一 namespace |
| 端口冲突 | 连接异常 | 检查 port/targetPort/nodePort 配置 |

### Endpoints 检查

```bash
# 查看 Endpoints
kubectl get endpoints <svc-name>

# 如果 Endpoints 为空，说明 selector 没匹配到 Pod
# 检查 selector
kubectl get svc <svc-name> -o jsonpath='{.spec.selector}'

# 检查 Pod labels
kubectl get pods --show-labels
```
""",
        key_fields=[
            {"name": "selector", "description": "Service 选择后端 Pod 的标签选择器", "required": True, "example": "app: web"},
            {"name": "labels", "description": "Pod 的标签，必须与 Service selector 匹配", "required": True, "example": "app: web"},
            {"name": "ports", "description": "Service 端口映射配置", "required": True, "example": "port: 80, targetPort: 8080"},
            {"name": "targetPort", "description": "容器实际监听端口", "required": True, "example": "8080"},
        ],
        diagram="""\
  Service 连通性排查

  ┌─────────────────────────────────────────────────┐
  │  Service (web-svc)                               │
  │  selector: app: web                              │
  │  port: 80 → targetPort: 8080                    │
  └───────────────────────┬─────────────────────────┘
                          │
                    selector 匹配
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
     ┌───────────────┐       ┌───────────────┐
     │  Pod labels:  │       │  Pod labels:  │
     │  app: web ✅  │       │  app: web ✅  │
     │  port: 8080   │       │  port: 8080   │
     └───────────────┘       └───────────────┘

  问题场景: selector 不匹配

  ┌─────────────────────────────────────────────────┐
  │  Service (web-svc)                               │
  │  selector: app: web                              │
  └───────────────────────┬─────────────────────────┘
                          │
                    selector 不匹配
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
     ┌───────────────┐       ┌───────────────┐
     │  Pod labels:  │       │  Pod labels:  │
     │  app: website │       │  app: website │
     │  ❌ 不匹配     │       │  ❌ 不匹配     │
     └───────────────┘       └───────────────┘
     Endpoints: <none>       Endpoints: <none>
""",
        example_yaml="""\
# 修复后的 Service + Pod（selector 与 labels 匹配）
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 8080
""",
        common_errors=[
            "selector 和 labels 的 key-value 不完全一致（拼写错误、大小写）",
            "targetPort 与容器实际监听端口不一致",
            "Service 和 Pod 在不同的 namespace",
            "Pod 有 readinessProbe 但探针失败，导致不在 Endpoints 中",
        ],
        tips=[
            "kubectl get endpoints 是排查 Service 连通性的第一步",
            "用 kubectl get pods --show-labels 对比 Pod labels 和 Service selector",
            "readinessProbe 失败的 Pod 不会出现在 Endpoints 中",
            "Headless Service (clusterIP: None) 的 DNS 直接解析到 Pod IP",
        ],
    ),
)


# ==================== Q22.3 Node NotReady ====================

def _check_223_node_notready(user_input: str) -> CheckResult:
    """Q22.3 Node NotReady 故障排查 - 验证排查命令"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入故障排查命令",
            hints=["使用 kubectl 命令排查 Node NotReady 问题"],
        )

    lower = text.lower()

    # 检查 kubectl
    if "kubectl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["使用 kubectl 命令排查节点问题"],
        )

    # 检查包含 get nodes 或 describe node
    has_get_nodes = "get nodes" in lower or "get node" in lower
    has_describe_node = "describe node" in lower

    if not has_get_nodes and not has_describe_node:
        return CheckResult(
            ok=False,
            error="缺少节点排查命令",
            hints=["使用 kubectl get nodes 查看节点状态，或 kubectl describe node <name> 查看详情"],
        )

    # 检查是否包含具体的排查动作（describe 或 events 或 logs）
    has_events = "events" in lower
    has_describe = "describe" in lower
    has_logs = "logs" in lower
    has_journalctl = "journalctl" in lower

    if not (has_events or has_describe or has_logs or has_journalctl):
        return CheckResult(
            ok=False,
            error="排查命令不够深入",
            hints=[
                "进一步排查: kubectl describe node <name> 查看事件",
                "或 kubectl get events 查看集群事件",
                "或 journalctl -u kubelet 查看 kubelet 日志",
            ],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["节点排查思路正确！describe/events/journalctl 是排查 Node NotReady 的利器 ⚡"],
    )


LEVEL_Q22_3 = Level(
    id="Q22.3",
    chapter="ch22",
    title="Node NotReady 排查",
    description="""
# Node NotReady 排查 ⚡

集群中一个节点状态变为 `NotReady`，需要排查原因。

## 场景

```
$ kubectl get nodes
NAME       STATUS     ROLES           AGE   VERSION
master     Ready      control-plane   30d   v1.28.0
worker-1   NotReady   <none>          30d   v1.28.0
```

## 任务

编写排查 Node NotReady 的命令，至少包含：
- 使用 `kubectl get nodes` 或 `kubectl describe node` 查看节点状态
- 使用 `kubectl describe`、`kubectl get events` 或 `journalctl` 进一步排查

## 提示

排查流程：
```bash
# 1. 查看节点状态
kubectl get nodes

# 2. 查看节点详情和事件
kubectl describe node worker-1

# 3. 查看集群事件
kubectl get events --field-selector involvedObject.kind=Node

# 4. 查看 kubelet 日志
journalctl -u kubelet -f
```
""",
    starter_yaml="""\
# 输入 Node NotReady 排查命令
# 1. kubectl get nodes
# 2. kubectl describe node <name>  或  kubectl get events
""",
    check_fn=_check_223_node_notready,
    lesson=Lesson(
        concept="""\
## Node NotReady 排查

节点状态变为 `NotReady` 表示 kubelet 无法正常与 API Server 通信，或节点本身出现了问题。

### NotReady 的常见原因

| 原因 | 症状 | 排查方法 |
|------|------|----------|
| kubelet 停止 | 节点 NotReady | `systemctl status kubelet` |
| kubelet 无法访问 API Server | 节点 NotReady | `journalctl -u kubelet` |
| 节点资源耗尽 | 节点 NotReady | `kubectl describe node` |
| 网络分区 | 节点 NotReady | `ping <api-server>` |
| 容器运行时故障 | 节点 NotReady | `systemctl status containerd` |
| 磁盘压力 | 节点 DiskPressure | `df -h` |
| 内存压力 | 节点 MemoryPressure | `free -m` |
| PID 耗尽 | 节点 PIDPressure | `ps aux | wc -l` |

### 排查流程

```
1. kubectl get nodes               → 确认哪些节点 NotReady
2. kubectl describe node <name>    → 查看条件和事件
3. ssh 到节点                       → 检查系统级问题
4. systemctl status kubelet        → kubelet 是否运行
5. journalctl -u kubelet           → kubelet 日志
6. systemctl status containerd     → 容器运行时状态
7. df -h / free -m                 → 磁盘/内存资源
8. ping <api-server-ip>            → 网络连通性
```

### 节点条件（Conditions）

`kubectl describe node` 中的 Conditions 部分：

| 条件 | 含义 |
|------|------|
| Ready | 节点是否健康（True=正常, False=NotReady, Unknown=失联） |
| DiskPressure | 磁盘空间不足 |
| MemoryPressure | 内存不足 |
| PIDPressure | 进程数不足 |
| NetworkUnavailable | 网络配置不正确 |
""",
        key_fields=[
            {"name": "kubectl get nodes", "description": "查看所有节点状态", "required": True, "example": "kubectl get nodes"},
            {"name": "kubectl describe node", "description": "查看节点详情、条件和事件", "required": True, "example": "kubectl describe node worker-1"},
            {"name": "journalctl -u kubelet", "description": "查看 kubelet 服务日志", "required": False, "example": "journalctl -u kubelet -f"},
            {"name": "systemctl status kubelet", "description": "检查 kubelet 服务状态", "required": False, "example": "systemctl status kubelet"},
        ],
        diagram="""\
  Node NotReady 排查流程

  ┌──────────────┐
  │ kubectl get  │     worker-1: NotReady
  │ nodes        │ ──────────────────────┐
  └──────┬───────┘                       │
         ▼                               │
  ┌──────────────────┐                   │
  │ kubectl describe │  Conditions:      │
  │ node worker-1    │  Ready: False     │
  │                  │  DiskPressure:True│
  └──────┬───────────┘  (找到原因!)      │
         │                               │
         ▼                               │
  ┌──────────────────┐                   │
  │ SSH 到节点       │                   │
  │                  │                   │
  │ systemctl status │  kubelet: running │
  │   kubelet        │                   │
  │                  │                   │
  │ journalctl -u    │  "disk pressure   │
  │   kubelet        │   detected"       │
  └──────┬───────────┘                   │
         │                               │
         ▼                               │
  ┌──────────────────┐                   │
  │ 修复问题         │                   │
  │ - 清理磁盘空间   │                   │
  │ - 重启 kubelet   │                   │
  │ - 检查容器运行时 │                   │
  └──────────────────┘                   │
                                         │
  验证: kubectl get nodes ────────────────┘
         worker-1: Ready ✅
""",
        example_yaml="""\
# Node NotReady 排查命令

# 1. 查看节点状态
kubectl get nodes

# 2. 查看节点详情
kubectl describe node worker-1

# 3. 查看节点相关事件
kubectl get events --field-selector involvedObject.kind=Node

# 4. SSH 到节点检查 kubelet
ssh worker-1
systemctl status kubelet
journalctl -u kubelet --since "1 hour ago"

# 5. 检查容器运行时
systemctl status containerd

# 6. 检查资源
df -h
free -m
""",
        common_errors=[
            "只看 kubectl get nodes 不深入 describe，找不到具体原因",
            "忘记检查 kubelet 服务状态和日志",
            "忽略 DiskPressure/MemoryPressure 等条件",
            "不检查容器运行时（containerd/docker）状态",
        ],
        tips=[
            "kubectl describe node 的 Conditions 和 Events 部分是排查关键",
            "journalctl -u kubelet --since '10 min ago' 查看最近的 kubelet 日志",
            "节点 NotReady 后，Pod 会在 node-monitor-grace-period 后被驱逐",
            "检查节点上的磁盘空间，磁盘满会导致 kubelet 无法正常工作",
        ],
    ),
)


# ==================== Q22.4 控制平面故障 ====================

def _check_224_control_plane(user_input: str) -> CheckResult:
    """Q22.4 控制平面故障排查 - 验证排查命令"""
    text = user_input.strip()

    if not text:
        return CheckResult(
            ok=False,
            error="请输入控制平面排查命令",
            hints=["使用 kubectl 检查控制平面组件状态"],
        )

    lower = text.lower()

    # 检查 kubectl
    if "kubectl" not in lower:
        return CheckResult(
            ok=False,
            error="命令中缺少 kubectl",
            hints=["使用 kubectl 命令检查控制平面"],
        )

    # 检查包含组件检查命令
    has_get_pods = "get pods" in lower
    has_get_componentstatuses = "componentstatuses" in lower or "cs" in lower.split()
    has_get_pods_kube_system = "kube-system" in lower
    has_logs = "logs" in lower

    # 至少要有一种控制平面检查方式
    if not (has_get_pods or has_get_componentstatuses or has_logs):
        return CheckResult(
            ok=False,
            error="缺少控制平面组件检查命令",
            hints=[
                "kubectl get pods -n kube-system 检查控制平面 Pod",
                "kubectl get componentstatuses 检查组件健康状态",
            ],
        )

    # 检查是否包含对具体组件的检查
    has_api_server = "kube-apiserver" in lower or "apiserver" in lower
    has_etcd = "etcd" in lower
    has_scheduler = "scheduler" in lower
    has_controller = "controller" in lower
    has_kube_system = "kube-system" in lower

    if not (has_api_server or has_etcd or has_scheduler or has_controller or has_kube_system):
        return CheckResult(
            ok=False,
            error="需要检查具体的控制平面组件",
            hints=[
                "检查 kube-system 命名空间的 Pod",
                "或检查 kube-apiserver, etcd, kube-scheduler, kube-controller-manager",
            ],
        )

    return CheckResult(
        ok=True, state=ClusterState(),
        hints=["控制平面排查思路正确！确保所有组件 Pod Running 🎛️"],
    )


LEVEL_Q22_4 = Level(
    id="Q22.4",
    chapter="ch22",
    title="控制平面故障排查",
    description="""
# 控制平面故障排查 🎛️

API Server 响应缓慢，怀疑控制平面组件出问题。需要排查控制平面各组件状态。

## 场景

```
$ kubectl get pods -n kube-system
NAME                                   READY   STATUS             RESTARTS
kube-apiserver-master                  1/1     Running            0
etcd-master                            0/1     CrashLoopBackOff   5    # ← 问题！
kube-controller-manager-master         1/1     Running            0
kube-scheduler-master                  1/1     Running            0
```

## 任务

编写控制平面故障排查命令，包含：
- 使用 `kubectl get pods -n kube-system` 检查控制平面 Pod
- 或使用 `kubectl get componentstatuses` 检查组件健康
- 检查具体组件（kube-apiserver/etcd/scheduler/controller-manager）

## 提示

排查流程：
```bash
# 1. 检查控制平面 Pod
kubectl get pods -n kube-system

# 2. 检查组件状态
kubectl get componentstatuses

# 3. 查看出问题组件的日志
kubectl logs etcd-master -n kube-system
```
""",
    starter_yaml="""\
# 输入控制平面排查命令
# 1. kubectl get pods -n kube-system
# 2. kubectl get componentstatuses
# 3. kubectl logs <component> -n kube-system
""",
    check_fn=_check_224_control_plane,
    lesson=Lesson(
        concept="""\
## 控制平面故障排查

Kubernetes 控制平面包含四个核心组件，任何一个出问题都会影响集群功能。

### 控制平面组件

| 组件 | 作用 | 故障影响 |
|------|------|----------|
| **kube-apiserver** | API 入口，所有操作通过它 | 集群不可操作 |
| **etcd** | 集群状态存储 | 数据丢失风险，API Server 无法工作 |
| **kube-scheduler** | Pod 调度 | 新 Pod 无法被调度 |
| **kube-controller-manager** | 控制器循环 | Deployment/ReplicaSet 等无法协调 |

### 排查步骤

```
1. kubectl get pods -n kube-system
   → 检查控制平面 Pod 状态

2. kubectl get componentstatuses
   → 检查 etcd/scheduler/controller-manager 健康状态

3. kubectl logs <component> -n kube-system
   → 查看出问题组件的日志

4. kubectl describe pod <component> -n kube-system
   → 查看 Pod 事件

5. 如果是静态 Pod:
   → 检查 /etc/kubernetes/manifests/ 下的 YAML
   → 检查 kubelet 日志: journalctl -u kubelet
```

### 静态 Pod

控制平面组件通常以**静态 Pod** 形式运行：
- YAML 放在 `/etc/kubernetes/manifests/` 目录
- 由 kubelet 直接管理，不依赖 API Server
- 修改 YAML 后 kubelet 自动重建 Pod
- Pod 名称格式: `<component>-<node-name>`

### 常见控制平面故障

| 故障 | 原因 | 解决方法 |
|------|------|----------|
| etcd CrashLoopBackOff | 磁盘满/数据损坏 | 清理磁盘/恢复快照 |
| API Server 无法启动 | 证书过期 | 更新证书 |
| Scheduler 不工作 | 配置错误 | 检查配置文件 |
| Controller Manager 重启 | 权限问题 | 检查 kubeconfig |
""",
        key_fields=[
            {"name": "kubectl get pods -n kube-system", "description": "检查控制平面 Pod 状态", "required": True, "example": "kubectl get pods -n kube-system"},
            {"name": "kubectl get componentstatuses", "description": "检查控制平面组件健康状态", "required": False, "example": "kubectl get cs"},
            {"name": "kubectl logs", "description": "查看组件日志", "required": True, "example": "kubectl logs etcd-master -n kube-system"},
            {"name": "/etc/kubernetes/manifests/", "description": "静态 Pod YAML 目录", "required": False, "example": "/etc/kubernetes/manifests/etcd.yaml"},
        ],
        diagram="""\
  控制平面排查流程

  ┌───────────────────────────────────────────────────────┐
  │  kubectl get pods -n kube-system                      │
  │                                                       │
  │  kube-apiserver-master       1/1     Running    ✅    │
  │  etcd-master                 0/1     CrashLoop ❌     │
  │  kube-controller-manager     1/1     Running    ✅    │
  │  kube-scheduler-master       1/1     Running    ✅    │
  └─────────────────────────┬─────────────────────────────┘
                            │
                            ▼
  ┌───────────────────────────────────────────────────────┐
  │  kubectl logs etcd-master -n kube-system              │
  │                                                       │
  │  "disk space exhausted"                               │
  │  "failed to write wal"                                │
  └─────────────────────────┬─────────────────────────────┘
                            │
                            ▼
  ┌───────────────────────────────────────────────────────┐
  │  修复 etcd                                             │
  │  1. 清理磁盘空间 / 压缩 etcd                           │
  │  2. 或从快照恢复                                       │
  │  3. etcd Pod 自动重启 (静态 Pod)                       │
  └─────────────────────────┬─────────────────────────────┘
                            │
                            ▼
  ┌───────────────────────────────────────────────────────┐
  │  验证                                                  │
  │  kubectl get cs   →  all healthy                      │
  │  kubectl get pods -n kube-system  →  all Running ✅   │
  └───────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# 控制平面排查命令

# 1. 检查控制平面 Pod
kubectl get pods -n kube-system

# 2. 检查组件健康状态
kubectl get componentstatuses

# 3. 查看故障组件日志
kubectl logs etcd-master -n kube-system

# 4. 查看静态 Pod 配置
cat /etc/kubernetes/manifests/etcd.yaml

# 5. 检查 kubelet
journalctl -u kubelet | grep etcd

# 6. 检查磁盘空间（etcd 常见问题）
df -h /var/lib/etcd
""",
        common_errors=[
            "忘记检查 kube-system 命名空间的 Pod 状态",
            "不查看故障组件的日志，盲目操作",
            "忽略 etcd 磁盘空间问题（最常见的控制平面故障）",
            "修改静态 Pod YAML 后忘记等待 kubelet 自动重建",
        ],
        tips=[
            "kubectl get componentstatuses 快速检查核心组件健康",
            "etcd 故障最常见原因是磁盘满，定期检查磁盘空间",
            "控制平面证书过期会导致 API Server 无法启动",
            "用 etcdctl endpoint health 检查 etcd 健康",
        ],
    ),
)


# ==================== Q22.5 集群实战 - 完整故障排查 ====================

def _check_225_full_troubleshooting(user_yaml: str) -> CheckResult:
    """Q22.5 完整故障排查 - 修复一个包含多个问题的集群

    场景: 集群中有一个 Deployment + Service + Pod 的组合，
    存在多个问题需要修复：
    1. Service selector 与 Pod labels 不匹配
    2. Pod 容器 command 错误
    用户需要提交修复后的完整 YAML。
    """
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查有 Deployment
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="没有创建 Deployment",
            hints=["提交一个 Deployment YAML"],
        )

    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {})
    if not isinstance(dep_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    # 检查 Deployment 有正确的 selector 匹配 template labels
    selector = dep_spec.get("selector", {})
    template_labels = dep_spec.get("template", {}).get("metadata", {}).get("labels", {})

    if isinstance(selector, dict) and isinstance(template_labels, dict):
        match_labels = selector.get("matchLabels", {})
        if match_labels:
            for k, v in match_labels.items():
                if template_labels.get(k) != v:
                    return CheckResult(
                        ok=False,
                        error=f"Deployment selector matchLabels ({k}: {v}) 与 template labels 不匹配",
                        hints=["确保 spec.selector.matchLabels 与 spec.template.metadata.labels 一致"],
                    )

    # 检查有 Service
    if not state.services:
        return CheckResult(
            ok=False,
            error="没有创建 Service",
            hints=["还需要创建一个 Service 来暴露 Deployment"],
        )

    svc_name = next(iter(state.services))
    svc = state.services[svc_name]
    svc_spec = svc.get("spec", {})
    if not isinstance(svc_spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    # 检查 Service selector 匹配 Deployment 的 template labels
    svc_selector = svc_spec.get("selector", {})
    if not isinstance(svc_selector, dict) or not svc_selector:
        return CheckResult(
            ok=False,
            error="Service 缺少 selector",
            hints=["Service 需要 selector 来匹配 Deployment 的 Pod"],
        )

    if isinstance(template_labels, dict):
        for k, v in svc_selector.items():
            if template_labels.get(k) != v:
                return CheckResult(
                    ok=False,
                    error=f"Service selector ({k}: {v}) 与 Pod labels 不匹配",
                    hints=[f"Service selector 应与 Deployment template labels 一致: {template_labels}"],
                )

    # 检查 Service 有 ports
    ports = svc_spec.get("ports", [])
    if not isinstance(ports, list) or not ports:
        return CheckResult(
            ok=False,
            error="Service 缺少 ports 配置",
            hints=["Service 需要配置 ports"],
        )

    # 检查容器有正确的 image
    template = dep_spec.get("template", {})
    tmpl_spec = template.get("spec", {})
    containers = tmpl_spec.get("containers", []) if isinstance(tmpl_spec, dict) else []
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Deployment template 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["确保容器有正确的 image"],
        )

    # 检查不是会导致崩溃的命令
    command = c.get("command", [])
    if isinstance(command, list) and command:
        cmd_str = " ".join(str(x) for x in command)
        if "exit 1" in cmd_str or cmd_str.strip() == "false":
            return CheckResult(
                ok=False,
                error=f"command '{cmd_str}' 会导致容器崩溃",
                hints=["使用正确的启动命令"],
            )

    # 检查有 Pod 被创建
    if not state.pods:
        return CheckResult(
            ok=False,
            error="Deployment 没有创建 Pod",
            hints=["检查 Deployment 配置是否正确"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[f"集群故障已修复！Deployment '{dep_name}' + Service '{svc_name}' 正常运行 🏆"],
    )


LEVEL_Q22_5 = Level(
    id="Q22.5",
    chapter="ch22",
    title="集群实战 - 完整故障排查",
    description="""
# 集群实战 - 完整故障排查 🏆

一个 Web 应用无法访问，经排查发现多个问题。提交修复后的完整 YAML。

## 场景

问题配置：
```yaml
# Service selector 与 Pod labels 不匹配
apiVersion: v1
kind: Service
metadata:
  name: app-svc
spec:
  selector:
    app: myapp          # ← selector
  ports:
  - port: 80
    targetPort: 80
---
# Deployment 的 template labels 不匹配 selector
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deploy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: broken     # ← 与 selector 不匹配！
    spec:
      containers:
      - name: web
        image: nginx:1.25
        command: ["exit 1"]  # ← 命令也会导致崩溃！
```

## 任务

提交修复后的 YAML（Service + Deployment），解决所有问题：
1. Service selector 与 Deployment template labels 匹配
2. 容器 command 正确（不导致崩溃）
3. Deployment selector.matchLabels 与 template labels 一致
4. Service 有正确的 ports 配置

## 提示

修复要点：
- 统一 labels: `app: myapp`
- 移除或修正 `command`
- 确保 Service selector 和 Deployment selector 一致
""",
    starter_yaml="""\
apiVersion: v1
kind: Service
metadata:
  name: app-svc
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deploy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: broken  # ← 修复为 app: myapp
    spec:
      containers:
      - name: web
        image: nginx:1.25
        command: ["exit 1"]  # ← 修复或删除此行
""",
    check_fn=_check_225_full_troubleshooting,
    lesson=Lesson(
        concept="""\
## 完整故障排查实战

在生产环境中，应用故障往往不是单一原因，需要系统性地排查和修复。

### 系统性排查框架

```
1. 确认现象
   → kubectl get pods, svc, deploy
   → 明确什么不工作

2. 分层排查
   → Pod 层: CrashLoopBackOff? ImagePullBackOff?
   → Service 层: Endpoints 为空? 端口不匹配?
   → Deployment 层: selector 匹配? replicas 正确?
   → Node 层: 节点 Ready? 资源充足?

3. 定位根因
   → kubectl describe / kubectl logs
   → 对比配置，找出不一致

4. 修复验证
   → 修正 YAML
   → kubectl apply
   → 验证服务恢复正常
```

### 常见组合故障

| 故障组合 | 症状 | 排查方法 |
|----------|------|----------|
| selector 不匹配 + 命令错误 | Service 无 Endpoints + Pod 崩溃 | describe + logs |
| 资源不足 + 探针错误 | Pod OOMKilled + 不在 Endpoints | describe + events |
| 证书过期 + API Server 不可用 | kubectl 命令超时 | 检查证书有效期 |
| 网络策略 + DNS 故障 | Pod 间无法通信 | NetworkPolicy + CoreDNS |

### 生产环境排查工具

```bash
# 一键检查集群健康
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Running
kubectl get events -A --sort-by=.metadata.creationTimestamp | tail -20

# 检查 Service 连通性
kubectl get svc --all-namespaces
kubectl get endpoints --all-namespaces

# 检查 Deployment
kubectl get deploy --all-namespaces
kubectl rollout status deploy/<name>
```
""",
        key_fields=[
            {"name": "selector.matchLabels", "description": "Deployment 选择 Pod 的标签，必须与 template labels 一致", "required": True, "example": "app: myapp"},
            {"name": "template.labels", "description": "Pod 模板标签，必须与 selector 和 Service selector 一致", "required": True, "example": "app: myapp"},
            {"name": "Service.selector", "description": "Service 选择后端 Pod 的标签，必须与 Pod labels 一致", "required": True, "example": "app: myapp"},
            {"name": "command", "description": "容器启动命令，错误命令导致 CrashLoopBackOff", "required": False, "example": "[\"nginx\", \"-g\", \"daemon off;\"]"},
        ],
        diagram="""\
  完整故障排查流程

  ┌─────────────────────────────────────────────────┐
  │  现象: Web 应用无法访问                          │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Step 1: kubectl get pods                       │
  │  app-deploy-xxx   0/1   CrashLoopBackOff  ❌    │
  │  → 容器命令错误                                  │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Step 2: kubectl get endpoints app-svc          │
  │  app-svc   <none>                      ❌        │
  │  → Service selector 不匹配 Pod labels           │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Step 3: 对比配置                                │
  │  Service selector:  app: myapp                  │
  │  Pod labels:        app: broken   ← 不匹配!     │
  │  Deployment selector: app: myapp                │
  │  Container command: ["exit 1"]   ← 崩溃!        │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Step 4: 修复                                    │
  │  1. Pod labels → app: myapp                     │
  │  2. 移除/修正 command                            │
  │  3. kubectl apply -f fixed.yaml                 │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Step 5: 验证                                    │
  │  kubectl get pods   → Running ✅                │
  │  kubectl get ep     → 有 Endpoints ✅           │
  │  curl <svc-ip>      → 200 OK ✅                 │
  └─────────────────────────────────────────────────┘
""",
        example_yaml="""\
# 修复后的完整配置
apiVersion: v1
kind: Service
metadata:
  name: app-svc
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deploy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp          # ← 修复：与 selector 一致
    spec:
      containers:
      - name: web
        image: nginx:1.25
        # 移除错误的 command，使用镜像默认命令
        ports:
        - containerPort: 80
        resources:
          limits:
            memory: "128Mi"
            cpu: "250m"
          requests:
            memory: "64Mi"
            cpu: "125m"
""",
        common_errors=[
            "只修复一个问题就提交，忽略其他故障",
            "修复 selector 但忘记同步 Deployment 的 selector.matchLabels",
            "移除了 command 但 image 默认入口也有问题",
            "修复后忘记验证 Service Endpoints 是否正常",
        ],
        tips=[
            "系统性排查：Pod → Service → Deployment 逐层检查",
            "kubectl get endpoints 是验证 Service 连通性的快速方法",
            "修改 labels 后需要重建 Pod 才能生效",
            "生产环境排查时先看 events 再看 logs，效率更高",
        ],
    ),
)


# ==================== Chapter 22 Levels ====================

CHAPTER_22_LEVELS: list[Level] = [
    LEVEL_Q22_1, LEVEL_Q22_2, LEVEL_Q22_3, LEVEL_Q22_4, LEVEL_Q22_5,
]
