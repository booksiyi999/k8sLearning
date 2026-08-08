"""Chapter 22: 故障排查 - Pod/Service/Node/控制平面诊断（5 关）

Q22.1 Pod 状态诊断 - fix CrashLoopBackOff scenario
Q22.2 Service 连通性排查 - validate Service+Endpoints fix
Q22.3 CrashLoopBackOff - fix args causing exit code 1
Q22.4 Pending Pod - fix resource requests causing scheduling failure
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


# ==================== Q22.3 CrashLoopBackOff 故障排查 ====================

def _check_223_crashloop_fix(user_yaml: str) -> CheckResult:
    """Q22.3 CrashLoopBackOff 故障排查 - 提交修复后的 Pod YAML

    场景: 一个 Pod 因为 args 配置错误（exit 1）导致 CrashLoopBackOff。
    用户需要按排查流程（describe -> logs -> events -> fix）理解问题，
    然后提交修正后的 Pod YAML，确保容器能正常启动。
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

    # 检查 image
    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["CrashLoopBackOff 可能是镜像问题，确保 image 正确"],
        )

    # 收集 command 和 args 的完整文本
    command = c.get("command", [])
    args = c.get("args", [])

    all_parts = []
    if isinstance(command, list):
        all_parts.extend(str(x) for x in command)
    elif isinstance(command, str):
        all_parts.append(command)
    if isinstance(args, list):
        all_parts.extend(str(x) for x in args)
    elif isinstance(args, str):
        all_parts.append(args)

    cmd_str = " ".join(all_parts).lower()

    # 拒绝明显会导致崩溃的命令/参数
    # 原始问题: args: ["echo starting && exit 1"] 导致容器退出码 1
    crash_patterns = ["exit 1", "exit 1", "--crash", "--invalid-flag", "&& exit", "exit 1"]
    for pattern in crash_patterns:
        if pattern in cmd_str:
            return CheckResult(
                ok=False,
                error=f"command/args 中仍包含会导致崩溃的内容: '{pattern}'",
                hints=[
                    "原始 Pod 的 args 为 ['echo starting && exit 1']，容器启动后立即退出",
                    "排查流程: kubectl describe pod -> kubectl logs -> 查看 Events -> 修复 YAML",
                    "修正 args 让容器持续运行，如 ['nginx', '-g', 'daemon off;']",
                ],
            )

    # 检查 command 中没有 'false' 或 'exit' 等立即退出的命令
    if isinstance(command, list) and command:
        first_cmd = str(command[0]).lower()
        if first_cmd in ("false", "exit", "true"):
            return CheckResult(
                ok=False,
                error=f"command '{first_cmd}' 会导致容器立即退出",
                hints=["使用能持续运行的命令，如 'nginx' 或 'sleep'"],
            )

    # 修复后的 Pod 应该有正确的 command 或 args，或者使用能默认启动的镜像
    has_command = bool(command) if isinstance(command, list) else bool(command)
    has_args = bool(args) if isinstance(args, list) else bool(args)

    if not has_command and not has_args:
        # 允许没有 command/args 但使用已知能默认启动的镜像
        known_good_images = ["nginx", "redis", "busybox", "python", "node", "alpine", "httpd", "memcached"]
        if not any(img in image.lower() for img in known_good_images):
            return CheckResult(
                ok=False,
                error="容器缺少 command 或 args，且镜像可能无法默认启动",
                hints=[
                    "添加正确的 command 或 args 让容器持续运行",
                    "或使用能默认启动的镜像（如 nginx:1.25）",
                ],
            )

    return CheckResult(
        ok=True, state=state,
        hints=["CrashLoopBackOff 修复成功！describe -> logs -> events -> fix 是标准排查流程 🔍"],
    )


LEVEL_Q22_3 = Level(
    id="Q22.3",
    chapter="ch22",
    title="CrashLoopBackOff 故障排查",
    description="""
# CrashLoopBackOff 故障排查 🔍

一个 Pod 陷入了 `CrashLoopBackOff` 状态。容器不断崩溃重启，需要你按照排查流程定位问题并修复。

## 场景

故障 Pod 的 YAML（有问题）：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["/bin/sh", "-c"]
    args: ["echo starting && exit 1"]  # ← 问题！容器启动后立即退出（exit code 1）
```

模拟排查输出：
```
$ kubectl get pods
NAME      READY   STATUS             RESTARTS   AGE
app-pod   0/1     CrashLoopBackOff   5          2m

$ kubectl describe pod app-pod
...
Containers:
  app:
    State:       Waiting
    Reason:      CrashLoopBackOff
    Last State:  Terminated
      Reason:    Completed
      Exit Code: 1    # ← 退出码 1，应用主动退出
Events:
  Warning  BackOff    5s (x6)  kubelet  Back-off restarting failed container

$ kubectl logs app-pod
starting    # ← 只输出了 "starting" 就退出了
```

## 排查流程

```
1. kubectl get pods              -> 确认 CrashLoopBackOff 状态
2. kubectl describe pod app-pod  -> 查看 Exit Code 和 Events
3. kubectl logs app-pod          -> 查看容器日志（输出 "starting" 后退出）
4. 定位问题: args 中的 "exit 1" 导致容器立即退出
5. 修复 YAML: 修正 args 让容器持续运行
```

## 任务

提交修正后的 Pod YAML：
- 修正 `command` 和 `args`，让容器能正常持续运行
- 确保 `image` 正确
- 不能包含 `exit 1` 或其他会导致立即退出的命令

## 提示

修复后的 YAML（使用 nginx 默认启动命令）：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["nginx", "-g", "daemon off;"]
```

或者直接移除 command/args，让 nginx 使用默认启动命令：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["/bin/sh", "-c"]
    args: ["echo starting && exit 1"]  # ← 修复这个 args
""",
    check_fn=_check_223_crashloop_fix,
    lesson=Lesson(
        concept="""\
## CrashLoopBackOff 排查流程

`CrashLoopBackOff` 表示容器反复崩溃并被 kubelet 重启。排查需要遵循 **describe -> logs -> events -> fix** 的标准流程。

### 排查步骤详解

```
Step 1: kubectl get pods
  -> 确认 Pod 处于 CrashLoopBackOff 状态
  -> 查看 RESTARTS 次数（频繁重启说明问题持续存在）

Step 2: kubectl describe pod <pod-name>
  -> 查看 Containers 部分:
     - State: Waiting, Reason: CrashLoopBackOff
     - Last State: Terminated
       - Exit Code: 0 = 正常退出（但不应退出）
       - Exit Code: 1 = 应用错误
       - Exit Code: 137 = OOMKilled（内存不足）
       - Exit Code: 126/127 = 命令不存在
  -> 查看 Events 部分: BackOff 重启事件

Step 3: kubectl logs <pod-name>
  -> 查看当前容器日志
  -> 如果日志为空，使用 kubectl logs <pod-name> --previous
     查看上次崩溃前的日志（非常关键！）

Step 4: 根据日志定位问题并修复
  -> 命令/参数错误 -> 修正 command/args
  -> 镜像不存在 -> 修正 image
  -> 配置错误 -> 修正 ConfigMap/Secret 引用
  -> OOMKilled -> 增加 resources.limits.memory
```

### Exit Code 对照表

| Exit Code | 含义 | 常见原因 |
|-----------|------|----------|
| 0 | 正常退出 | 容器任务完成后退出（非长期运行服务） |
| 1 | 应用错误 | 应用启动失败、配置错误 |
| 125 | Docker 错误 | 容器运行时问题 |
| 126 | 命令不可执行 | 权限不足 |
| 127 | 命令未找到 | command/args 指定了不存在的二进制 |
| 137 | OOMKilled | 内存不足被 kill（SIGKILL） |
| 139 | 段错误 | 应用 crash（SIGSEGV） |
| 143 | 正常终止 | 收到 SIGTERM 后正常退出 |
""",
        key_fields=[
            {"name": "command", "description": "容器启动命令，错误命令导致 CrashLoopBackOff", "required": True, "example": "[\"nginx\", \"-g\", \"daemon off;\"]"},
            {"name": "args", "description": "容器启动参数，错误参数导致应用退出", "required": False, "example": "[\"--config\", \"/etc/app/config.yaml\"]"},
            {"name": "image", "description": "容器镜像，错误镜像导致启动失败", "required": True, "example": "nginx:1.25"},
            {"name": "Exit Code", "description": "describe 中显示的退出码，帮助定位问题", "required": False, "example": "1（应用错误）, 137（OOMKilled）"},
        ],
        diagram="""\
  CrashLoopBackOff 排查流程

  ┌──────────────┐
  │ kubectl get  │     CrashLoopBackOff
  │ pods         │ ──────────────────────┐
  └──────┬───────┘                       │
         ▼                               │
  ┌──────────────┐                       │
  │ kubectl      │     Last State:       │
  │ describe pod │     Exit Code: 1      │
  │              │     Events: BackOff   │
  └──────┬───────┘                       │
         ▼                               │
  ┌──────────────┐                       │
  │ kubectl logs │     "starting"        │
  │ <pod>        │ <─────────────────────┘
  └──────┬───────┘
         │ 如果当前日志为空
         ▼
  ┌──────────────────────┐
  │ kubectl logs         │
  │ <pod> --previous     │  ← 查看崩溃前日志
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │  修复 command/args   │
  │  kubectl apply -f    │
  └──────────────────────┘
""",
        example_yaml="""\
# 修复 CrashLoopBackOff

# 问题 YAML（崩溃）:
# command: ["/bin/sh", "-c"]
# args: ["echo starting && exit 1"]

# 修复方案 1: 使用 nginx 启动命令
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["nginx", "-g", "daemon off;"]

# 修复方案 2: 移除 command/args，使用镜像默认入口
# apiVersion: v1
# kind: Pod
# metadata:
#   name: app-pod
# spec:
#   containers:
#   - name: app
#     image: nginx:1.25
""",
        common_errors=[
            "只看当前日志不看 --previous，看不到崩溃前的错误信息",
            "command 使用 shell 内置命令（如 echo）但未指定 /bin/sh -c",
            "args 中包含 exit 1 或 false 等立即退出的命令",
            "livenessProbe 检测路径错误，导致健康检查失败触发重启",
        ],
        tips=[
            "kubectl logs --previous 是排查 CrashLoopBackOff 的利器",
            "用 kubectl describe pod 查看 Last State 中的 Exit Code",
            "Exit Code 137 = OOMKilled，需要增加内存限制",
            "Exit Code 127 = 命令未找到，检查 command/args 拼写",
        ],
    ),
)

# ==================== Q22.4 Pending Pod 故障排查 ====================

def _check_224_pending_fix(user_yaml: str) -> CheckResult:
    """Q22.4 Pending Pod 故障排查 - 提交修复后的 Pod YAML

    场景: 一个 Pod 因为 resources.requests 过大（100 CPU / 512Gi 内存），
    没有节点能满足调度需求，一直处于 Pending 状态。
    用户需要按排查流程（describe -> events -> 定位原因 -> fix）理解问题，
    然后提交修正后的 Pod YAML，确保资源请求合理。
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

    # 检查 image
    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["Pending Pod 排查后仍需要正确的 image"],
        )

    # ── 核心校验：resources.requests 必须合理 ──
    # 原始问题: requests.cpu = "100", requests.memory = "512Gi"
    # 没有节点能满足，导致 Pending（FailedScheduling）
    resources = c.get("resources", {})
    if not isinstance(resources, dict):
        resources = {}

    requests = resources.get("requests", {})
    if not isinstance(requests, dict):
        requests = {}

    # 解析 CPU 请求值（支持 "100" / "100m" / 100 等格式）
    cpu_request = requests.get("cpu")
    cpu_millicores = _parse_cpu(cpu_request)

    # 解析 Memory 请求值（支持 "512Gi" / "512Mi" / 536870912 等格式）
    mem_request = requests.get("memory")
    mem_mib = _parse_memory(mem_request)

    # 合理的资源请求上限（单节点典型容量）
    # CPU: 64 核 = 64000m（远超大多数节点）
    # Memory: 256Gi = 262144 Mi
    MAX_CPU_M = 64000       # 64 cores
    MAX_MEM_MIB = 262144    # 256 Gi

    if cpu_millicores is not None and cpu_millicores > MAX_CPU_M:
        return CheckResult(
            ok=False,
            error=f"CPU 请求 {cpu_millicores}m 仍然过大（上限 {MAX_CPU_M}m = 64 核）",
            hints=[
                "原始 Pod 请求 100 CPU，没有节点能满足",
                "kubectl describe pod 显示 Events: FailedScheduling, Insufficient cpu",
                "将 requests.cpu 减小到合理值，如 '500m' 或 '1'",
            ],
        )

    if mem_mib is not None and mem_mib > MAX_MEM_MIB:
        return CheckResult(
            ok=False,
            error=f"内存请求 {mem_mib}Mi 仍然过大（上限 {MAX_MEM_MIB}Mi = 256Gi）",
            hints=[
                "原始 Pod 请求 512Gi 内存，没有节点能满足",
                "kubectl describe pod 显示 Events: FailedScheduling, Insufficient memory",
                "将 requests.memory 减小到合理值，如 '512Mi' 或 '1Gi'",
            ],
        )

    # 检查是否提供了合理的资源请求（修复后应该有 resources.requests）
    # 原始 YAML 有不合理的 requests，修复后应该有合理的 requests 或移除 requests
    has_requests = bool(requests)
    if has_requests:
        # 有 requests 是好的，只要值合理（已在上面校验）
        pass
    else:
        # 没有 requests 也可以接受（让调度器自由分配）
        # 但提示用户添加 resources 更好
        pass

    # 额外检查：如果有 nodeSelector，也是合理的修复方式
    # （场景中也可以通过添加 nodeSelector 指定有足够资源的节点）
    node_selector = spec.get("nodeSelector")
    if isinstance(node_selector, dict) and node_selector:
        # 有 nodeSelector 是有效的修复策略
        pass

    return CheckResult(
        ok=True, state=state,
        hints=["Pending Pod 修复成功！describe -> events -> 定位资源不足 -> 修复 requests ⚡"],
    )


def _parse_cpu(cpu_val) -> int | None:
    """将 CPU 请求值解析为 millicores（整数毫核）。

    支持: "100" -> 100000, "500m" -> 500, "1" -> 1000, 100 (int) -> 100000
    返回 None 表示无法解析或未指定。
    """
    if cpu_val is None:
        return None
    if isinstance(cpu_val, (int, float)):
        return int(cpu_val * 1000)
    if isinstance(cpu_val, str):
        cpu_val = cpu_val.strip()
        if cpu_val.endswith("m"):
            try:
                return int(cpu_val[:-1])
            except ValueError:
                return None
        else:
            try:
                return int(float(cpu_val) * 1000)
            except ValueError:
                return None
    return None


def _parse_memory(mem_val) -> int | None:
    """将 Memory 请求值解析为 MiB（整数兆字节）。

    支持: "512Gi" -> 524288, "512Mi" -> 512, "1Gi" -> 1024, 536870912 (int bytes) -> 512
    返回 None 表示无法解析或未指定。
    """
    if mem_val is None:
        return None
    if isinstance(mem_val, (int, float)):
        # 原始字节数
        return int(mem_val / (1024 * 1024))
    if isinstance(mem_val, str):
        mem_val = mem_val.strip()
        # 后缀映射: Ki, Mi, Gi, Ti, Pi, Ei, K, M, G, T, P, E
        suffixes = {
            "Ki": 1 / 1024,
            "Mi": 1,
            "Gi": 1024,
            "Ti": 1024 * 1024,
            "Pi": 1024 * 1024 * 1024,
            "Ei": 1024 * 1024 * 1024 * 1024,
            "K": 0.9765625,   # 1000 bytes -> 0.953 MiB
            "M": 0.953674,     # 1000000 bytes -> 0.953 MiB
            "G": 953.674,
            "T": 976562.5,
            "P": 976562500,
            "E": 976562500000,
        }
        for suffix, multiplier in suffixes.items():
            if mem_val.endswith(suffix):
                try:
                    return int(float(mem_val[:-len(suffix)]) * multiplier)
                except ValueError:
                    return None
        # 无后缀，按字节处理
        try:
            return int(float(mem_val) / (1024 * 1024))
        except ValueError:
            return None
    return None


LEVEL_Q22_4 = Level(
    id="Q22.4",
    chapter="ch22",
    title="Pending Pod 故障排查",
    description="""
# Pending Pod 故障排查 ⚡

一个 Pod 一直处于 `Pending` 状态，无法被调度到任何节点。需要你按照排查流程定位问题并修复。

## 场景

故障 Pod 的 YAML（有问题）：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "100"        # ← 100 CPU！没有节点有这么多 CPU
        memory: "512Gi"   # ← 512Gi 内存！远超任何节点容量
```

模拟排查输出：
```
$ kubectl get pods
NAME     READY   STATUS    RESTARTS   AGE
worker   0/1     Pending   0          5m

$ kubectl describe pod worker
...
Events:
  Warning  FailedScheduling  5m  default-scheduler
    0/3 nodes are available: 3 Insufficient cpu, 3 Insufficient memory.
  # ← 没有节点的 CPU/内存能满足请求！
```

## 排查流程

```
1. kubectl get pods              -> 确认 Pending 状态
2. kubectl describe pod worker   -> 查看 Events 中的 FailedScheduling 原因
3. 定位问题: requests.cpu=100, requests.memory=512Gi 远超节点容量
4. 修复 YAML: 将 resources.requests 减小到合理值
5. kubectl apply -f fixed.yaml   -> 重新调度
```

## 任务

提交修正后的 Pod YAML：
- 将 `resources.requests` 减小到合理值（CPU ≤ 64 核，Memory ≤ 256Gi）
- 保留 `image` 和 `command`
- 确保 Pod 能被正常调度

## 提示

修复后的 YAML（合理资源请求）：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "500m"      # ← 0.5 核，合理
        memory: "512Mi"   # ← 512MB，合理
      limits:
        cpu: "1"
        memory: "1Gi"
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "100"        # ← 修复：减小到合理值
        memory: "512Gi"   # ← 修复：减小到合理值
""",
    check_fn=_check_224_pending_fix,
    lesson=Lesson(
        concept="""\
## Pending Pod 排查

Pod 处于 `Pending` 状态表示它已被提交到 Kubernetes，但尚未被调度到任何节点。最常见的原因是**调度失败**。

### 排查步骤

```
1. kubectl get pods
   -> 确认 Pod 处于 Pending 状态

2. kubectl describe pod <pod-name>
   -> 查看 Events 部分:
      - FailedScheduling: 没有节点满足调度条件
      - Insufficient cpu: CPU 资源不足
      - Insufficient memory: 内存资源不足
      - node(s) didn't match node selector: 亲和性不匹配
      - node(s) had taints that the pod didn't tolerate: 污点不容忍

3. 检查资源请求
   -> kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources}'
   -> 对比节点可用资源: kubectl describe node | grep -A 5 Allocated

4. 修复并重新部署
   -> 减小 resources.requests
   -> 或添加 nodeSelector 指定有足够资源的节点
   -> 或添加 tolerations 容忍节点污点
```

### Pending 的常见原因

| 原因 | Events 消息 | 解决方法 |
|------|------------|----------|
| **资源不足** | Insufficient cpu/memory | 减小 resources.requests |
| **nodeSelector 不匹配** | didn't match node selector | 修正 nodeSelector 或添加标签到节点 |
| **节点污点** | had taints that the pod didn't tolerate | 添加 tolerations 或移除污点 |
| **亲和性/反亲和性** | node(s) didn't satisfy pod affinity | 修正 affinity 规则 |
| **资源配额超限** | exceeded quota | 减少资源请求或申请增加配额 |
| **PVC 未绑定** | pod has unbound immediate PersistentVolumeClaims | 检查 PVC/PV 配置 |
| **节点 NotReady** | 0/N nodes are available | 修复 NotReady 节点 |

### 资源单位

```
CPU:
  1 = 1 核 = 1000m (millicores)
  500m = 0.5 核
  100m = 0.1 核

Memory:
  1 Ki = 1024 bytes
  1 Mi = 1024 Ki = 1,048,576 bytes
  1 Gi = 1024 Mi = 1,073,741,824 bytes
```
""",
        key_fields=[
            {"name": "resources.requests.cpu", "description": "CPU 请求值，过大导致调度失败", "required": True, "example": "500m (0.5 核)"},
            {"name": "resources.requests.memory", "description": "内存请求值，过大导致调度失败", "required": True, "example": "512Mi"},
            {"name": "nodeSelector", "description": "节点选择器，可指定有足够资源的节点", "required": False, "example": "disktype: ssd"},
            {"name": "tolerations", "description": "污点容忍，允许调度到有污点的节点", "required": False, "example": "key: node-role.kubernetes.io/master"},
        ],
        diagram="""\
  Pending Pod 排查流程

  ┌──────────────┐
  │ kubectl get  │     Pending
  │ pods         │ ──────────────────────┐
  └──────┬───────┘                       │
         ▼                               │
  ┌──────────────────┐                   │
  │ kubectl describe │  Events:          │
  │ pod worker       │  FailedScheduling │
  │                  │  Insufficient cpu │
  └──────┬───────────┘  Insufficient mem │
         │                               │
         ▼                               │
  ┌──────────────────┐                   │
  │ 检查资源请求      │                   │
  │                  │                   │
  │ requests.cpu:    │  100 CPU ← 太大!  │
  │ requests.memory: │  512Gi  ← 太大!  │
  └──────┬───────────┘                   │
         │                               │
         ▼                               │
  ┌──────────────────┐                   │
  │ 修复 resources   │                   │
  │ cpu: 500m        │                   │
  │ memory: 512Mi    │                   │
  │ kubectl apply    │                   │
  └──────┬───────────┘                   │
         │                               │
         ▼                               │
  ┌──────────────────┐                   │
  │ 验证              │                   │
  │ kubectl get pods │                   │
  │ worker: Running  │ ──────────────────┘
  └──────────────────┘   ✅
""",
        example_yaml="""\
# 修复 Pending Pod（资源请求过大）

# 问题 YAML（Pending）:
# resources:
#   requests:
#     cpu: "100"
#     memory: "512Gi"

# 修复 YAML（合理资源请求）:
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "1"
        memory: "1Gi"
""",
        common_errors=[
            "resources.requests 设置过大，超过所有节点的可用资源",
            "忘记检查 kubectl describe pod 的 Events 部分，看不到 FailedScheduling 原因",
            "nodeSelector 指定的标签不存在于任何节点",
            "忽略了节点的 taints，Pod 无法被调度到有污点的节点",
        ],
        tips=[
            "kubectl describe pod 的 Events 部分是排查 Pending 的关键",
            "kubectl describe node | grep -A 10 Allocated 查看节点已分配资源",
            "requests 不需要等于 limits，通常 requests < limits",
            "生产环境建议设置 resources.requests 避免过度调度",
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
