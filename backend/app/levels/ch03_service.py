"""Chapter 3: Service & 网络服务发现（4 关）

Q3.1 创建 ClusterIP Service
Q3.2 NodePort 对外暴露
Q3.3 Service 发现 DNS
Q3.4 Headless Service

simulator 依赖:
- apply_manifest(state, yaml)          解析+校验+应用
- preset_state(state, yaml)            预置基线状态
- resolve_service_endpoints(state, name)  selector 匹配 Pod
- resolve_dns(state, name)             模拟 DNS 解析
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import (
    apply_manifest,
    preset_state,
    resolve_service_endpoints,
    resolve_dns,
    ClusterState,
    K8sError,
)


# ==================== Q3.1 创建 ClusterIP Service ====================

def _check_01_clusterip_service(user_yaml: str) -> CheckResult:
    """Q3.1 创建 ClusterIP Service"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.services:
        return CheckResult(ok=False, error="没有创建任何 Service", hints=["你需要 apply 一个 kind: Service 的 YAML"])

    if "nginx-svc" not in state.services:
        names = list(state.services.keys())
        return CheckResult(
            ok=False,
            error=f"没找到名为 'nginx-svc' 的 Service，当前 Service 名字：{names}",
            hints=["Service 的名字由 metadata.name 决定"],
        )

    svc = state.services["nginx-svc"]
    spec = svc.get("spec", {})

    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    # 检查 selector
    selector = spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(ok=False, error="Service 缺少 spec.selector", hints=["selector 用于选择后端 Pod，如 app: nginx"])

    if selector.get("app") != "nginx":
        return CheckResult(ok=False, error=f"selector.app 应为 'nginx'，实际为 '{selector.get('app')}'", hints=[])

    # 检查 ports
    ports = spec.get("ports")
    if not isinstance(ports, list) or not ports:
        return CheckResult(ok=False, error="Service 缺少 spec.ports", hints=["至少定义一个端口映射"])

    p = ports[0]
    if not isinstance(p, dict):
        return CheckResult(ok=False, error="spec.ports[0] 格式错误", hints=[])

    if p.get("port") != 80:
        return CheckResult(ok=False, error=f"port 应为 80，实际为 {p.get('port')}", hints=["port 是 Service 对外暴露的端口"])

    if p.get("targetPort") != 8080:
        return CheckResult(ok=False, error=f"targetPort 应为 8080，实际为 {p.get('targetPort')}", hints=["targetPort 是后端 Pod 的端口"])

    # 检查 type（默认 ClusterIP，不写也行）
    svc_type = spec.get("type", "ClusterIP")
    if svc_type != "ClusterIP":
        return CheckResult(ok=False, error=f"type 应为 ClusterIP（或不写），实际为 {svc_type}", hints=[])

    return CheckResult(ok=True, state=state, hints=["ClusterIP Service 创建成功！这是集群内部访问 Service 的默认方式"])


# ==================== Q3.2 NodePort 对外暴露 ====================

def _check_02_nodeport_service(user_yaml: str) -> CheckResult:
    """Q3.2 NodePort 对外暴露"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.services:
        return CheckResult(ok=False, error="没有创建任何 Service", hints=["你需要 apply 一个 kind: Service 的 YAML"])

    if "web-svc" not in state.services:
        names = list(state.services.keys())
        return CheckResult(
            ok=False,
            error=f"没找到名为 'web-svc' 的 Service，当前：{names}",
            hints=["Service 名字必须是 web-svc"],
        )

    svc = state.services["web-svc"]
    spec = svc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    # 检查 type: NodePort
    svc_type = spec.get("type", "ClusterIP")
    if svc_type != "NodePort":
        return CheckResult(ok=False, error=f"type 应为 NodePort，实际为 {svc_type}", hints=["NodePort 让集群外部可以通过节点端口访问"])

    # 检查 ports
    ports = spec.get("ports")
    if not isinstance(ports, list) or not ports:
        return CheckResult(ok=False, error="Service 缺少 spec.ports", hints=[])

    p = ports[0]
    if not isinstance(p, dict):
        return CheckResult(ok=False, error="spec.ports[0] 格式错误", hints=[])

    if p.get("port") != 80:
        return CheckResult(ok=False, error=f"port 应为 80，实际为 {p.get('port')}", hints=[])

    if p.get("targetPort") != 8080:
        return CheckResult(ok=False, error=f"targetPort 应为 8080，实际为 {p.get('targetPort')}", hints=[])

    # nodePort 可选，如果写了检查范围
    node_port = p.get("nodePort")
    if node_port is not None:
        if not isinstance(node_port, int):
            return CheckResult(ok=False, error=f"nodePort 必须是整数，实际为 {type(node_port).__name__}", hints=[])
        if node_port < 30000 or node_port > 32767:
            return CheckResult(ok=False, error=f"nodePort 范围应为 30000-32767，实际为 {node_port}", hints=["NodePort 默认范围是 30000-32767"])

    # 检查 selector
    selector = spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(ok=False, error="Service 缺少 spec.selector", hints=["selector 用于选择后端 Pod"])

    return CheckResult(ok=True, state=state, hints=["NodePort Service 创建成功！外部可通过 <节点IP>:<nodePort> 访问"])


# ==================== Q3.3 Service 发现 DNS ====================

def _check_03_dns_discovery(user_yaml: str) -> CheckResult:
    """Q3.3 Service 发现 DNS"""
    try:
        state = ClusterState()
        # 预置一个后端 Service
        state = preset_state(state, """
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
spec:
  selector:
    app: backend
  ports:
    - port: 3000
      targetPort: 3000
""")
        # 应用用户 YAML（应该是创建一个前端 Pod，通过 DNS 名访问 backend-svc）
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查用户是否创建了前端 Pod
    if not state.pods:
        return CheckResult(ok=False, error="没有创建任何 Pod", hints=["创建一个 Pod，通过环境变量或命令访问 backend-svc"])

    # 找到用户创建的 Pod（排除预置的）
    user_pod = None
    for name, pod in state.pods.items():
        user_pod = pod
        break

    if not user_pod:
        return CheckResult(ok=False, error="未找到用户创建的 Pod", hints=[])

    # 检查 Pod 是否引用了 backend-svc（通过 env 或 command）
    spec = user_pod.get("spec", {})
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查环境变量中是否引用了 backend-svc
    env = c.get("env", [])
    found_dns_ref = False
    if isinstance(env, list):
        for e in env:
            if isinstance(e, dict):
                val = str(e.get("value", ""))
                if "backend-svc" in val:
                    found_dns_ref = True
                    break

    # 也检查 command/args
    if not found_dns_ref:
        cmd = c.get("command", [])
        args = c.get("args", [])
        for items in [cmd, args]:
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str) and "backend-svc" in item:
                        found_dns_ref = True
                        break

    if not found_dns_ref:
        return CheckResult(
            ok=False,
            error="Pod 的环境变量或命令中没有引用 'backend-svc'（DNS 名称）",
            hints=["K8s 中 Pod 可以通过 <service-name> 直接访问 Service", "试试在 env 或 command 中使用 backend-svc:3000"],
        )

    # 验证 DNS 解析确实工作
    dns_result = resolve_dns(state, "backend-svc")
    if dns_result is None:
        return CheckResult(ok=False, error="DNS 解析 backend-svc 失败", hints=[])

    return CheckResult(ok=True, state=state, hints=[f"DNS 解析成功！backend-svc -> {dns_result}"])


# ==================== Q3.4 Headless Service ====================

def _check_04_headless_service(user_yaml: str) -> CheckResult:
    """Q3.4 Headless Service"""
    try:
        state = ClusterState()
        # 预置 3 个带标签的 Pod
        state = preset_state(state, """
apiVersion: v1
kind: Pod
metadata:
  name: db-0
  labels:
    app: db
spec:
  containers:
    - name: db
      image: postgres:15
---
apiVersion: v1
kind: Pod
metadata:
  name: db-1
  labels:
    app: db
spec:
  containers:
    - name: db
      image: postgres:15
---
apiVersion: v1
kind: Pod
metadata:
  name: db-2
  labels:
    app: db
spec:
  containers:
    - name: db
      image: postgres:15
""")
        # 应用用户 YAML（应该是创建 Headless Service）
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.services:
        return CheckResult(ok=False, error="没有创建任何 Service", hints=["创建一个 Headless Service"])

    if "db-svc" not in state.services:
        names = list(state.services.keys())
        return CheckResult(ok=False, error=f"没找到 'db-svc'，当前：{names}", hints=["Service 名字必须是 db-svc"])

    svc = state.services["db-svc"]
    spec = svc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    # 检查 clusterIP: None
    cluster_ip = spec.get("clusterIP")
    if cluster_ip != "None":
        return CheckResult(
            ok=False,
            error=f"clusterIP 应为 'None'（Headless Service），实际为 {cluster_ip}",
            hints=["Headless Service 通过设置 clusterIP: None 实现", "它不会分配 ClusterIP，而是直接返回后端 Pod IP"],
        )

    # 检查 selector
    selector = spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(ok=False, error="Service 缺少 spec.selector", hints=["Headless Service 也需要 selector 来选择后端 Pod"])

    if selector.get("app") != "db":
        return CheckResult(ok=False, error=f"selector.app 应为 'db'，实际为 '{selector.get('app')}'", hints=[])

    # 检查 ports
    ports = spec.get("ports")
    if not isinstance(ports, list) or not ports:
        return CheckResult(ok=False, error="Service 缺少 spec.ports", hints=[])

    # 验证 DNS 解析返回的是 Pod 列表而非单个 IP
    dns_result = resolve_dns(state, "db-svc")
    if dns_result is None:
        return CheckResult(ok=False, error="DNS 解析 db-svc 失败", hints=[])

    if dns_result.get("type") != "Headless":
        return CheckResult(ok=False, error=f"DNS 解析结果类型应为 Headless，实际为 {dns_result.get('type')}", hints=[])

    endpoints = dns_result.get("endpoints", [])
    if len(endpoints) != 3:
        return CheckResult(
            ok=False,
            error=f"Headless Service 应匹配 3 个 Pod，实际匹配 {len(endpoints)} 个：{endpoints}",
            hints=["检查 selector 是否正确匹配了 db-0, db-1, db-2"],
        )

    # 验证 endpoints 确实是后端 Pod
    expected = ["db-0", "db-1", "db-2"]
    if sorted(endpoints) != sorted(expected):
        return CheckResult(
            ok=False,
            error=f"匹配的 Pod 不正确，期望 {expected}，实际 {endpoints}",
            hints=[],
        )

    return CheckResult(ok=True, state=state, hints=[f"Headless Service 创建成功！DNS 解析返回 {len(endpoints)} 个 Pod 端点，用于 StatefulSet 直连"])


# ==================== 关卡注册 ====================

CHAPTER_3_LEVELS: list[Level] = [
    Level(
        id="Q3.1",
        chapter="ch03",
        title="创建 ClusterIP Service",
        description="创建一个名为 nginx-svc 的 ClusterIP Service，将端口 80 转发到后端 Pod 的 8080 端口，selector 选择 app: nginx 的 Pod",
        starter_yaml="""apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  # 在这里填写 selector、ports 和 type
""",
        check_fn=_check_01_clusterip_service,
        lesson=Lesson(
            concept="""\
## ClusterIP Service

**ClusterIP** 是 K8s Service 的默认类型，为 Pod 组提供一个稳定的虚拟 IP 和 DNS 名称，实现集群内部的负载均衡和服务发现。

### 为什么需要 Service？

Pod 是短暂的--IP 随时会变（重启、扩缩容、Node 故障）。如果前端 Pod 直接连后端 Pod IP，后端一重启就断连。Service 提供一个**固定入口**（ClusterIP + DNS 名），后端 Pod 怎么变，前端不用改。

### selector + label 匹配机制

Service 通过 `spec.selector` 选择后端 Pod--只要 Pod 的 labels 匹配 selector，就自动被纳入 Service 的 endpoints。这实现了**松耦合**：Service 和 Pod 互不感知，通过 labels 间接关联。

### 负载均衡

kube-proxy 在每个 Node 上维护 iptables/ipvs 规则，将发往 ClusterIP 的流量**随机轮询**转发到后端 Pod。默认是轮询策略，无需额外配置。

### 端口映射

- `port`：Service 暴露的端口（集群内访问用）
- `targetPort`：后端 Pod 的容器端口
- 两者可以不同，Service 做端口转发
""",
            key_fields=[
                {"name": "spec.type", "description": "Service 类型，ClusterIP 是默认值", "required": False, "example": "ClusterIP"},
                {"name": "spec.selector", "description": "标签选择器，匹配后端 Pod 的 labels", "required": True, "example": "{app: nginx}"},
                {"name": "spec.ports[].port", "description": "Service 暴露的端口", "required": True, "example": "80"},
                {"name": "spec.ports[].targetPort", "description": "后端 Pod 的容器端口", "required": True, "example": "8080"},
                {"name": "spec.ports[].protocol", "description": "协议，默认 TCP", "required": False, "example": "TCP"},
            ],
            diagram="""\
  集群内部访问流程

  Client Pod                    Service (nginx-svc)              Backend Pods
  ┌──────────┐                 ┌─────────────────────┐          ┌─────────┐
  │ curl     │ ──ClusterIP──►  │  ClusterIP: 10.96.x │ ──LB──►  │ Pod1    │
  │ nginx-svc│                 │  Port: 80           │ ──LB──►  │ :8080   │
  │ :80      │                 │  selector:          │ ──LB──►  │ Pod2    │
  └──────────┘                 │    app: nginx       │          │ :8080   │
                               └─────────────────────┘          │ Pod3    │
                                  ▲                              │ :8080   │
                                  │ selector 匹配 labels         └─────────┘
                                  └─── app=nginx ◄─── labels: {app: nginx}
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Service                   # 资源类型: Service
metadata:                       # 元数据
  name: nginx-svc               # Service 名称（也是 DNS 名）
spec:                           # 规格定义
  type: ClusterIP               # 默认类型（可省略）
  selector:                     # 标签选择器
    app: nginx                  # 匹配 app=nginx 的 Pod
  ports:                        # 端口映射
  - port: 80                    # Service 端口
    targetPort: 8080            # 后端 Pod 端口
    protocol: TCP               # 协议（默认 TCP）
""",
            common_errors=[
                "selector 写成了 matchLabels（Service 用直接键值对，不是 matchLabels）",
                "port 和 targetPort 写反了（port 是 Service 的，targetPort 是 Pod 的）",
                "selector 与 Pod 的 labels 不匹配（Service 会没有 endpoints）",
                "忘记写 spec.ports（Service 至少需要一个端口）",
            ],
            tips=[
                "ClusterIP 只能集群内访问，对外暴露用 NodePort 或 LoadBalancer",
                "用 kubectl get svc 查看 Service 的 ClusterIP",
                "用 kubectl get endpoints <svc-name> 查看后端 Pod 列表",
            ],
        ),
    ),
    Level(
        id="Q3.2",
        chapter="ch03",
        title="NodePort 对外暴露",
        description="创建一个名为 web-svc 的 NodePort Service，端口 80 转发到 8080，让集群外部可以访问",
        starter_yaml="""apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  # 设置 type: NodePort
  # 配置 ports 和 selector
""",
        check_fn=_check_02_nodeport_service,
        lesson=Lesson(
            concept="""\
## NodePort Service

**NodePort** 在 ClusterIP 基础上，在每个 Node 上开放一个固定端口（30000-32767），让集群外部可以通过 `<NodeIP>:<NodePort>` 访问服务。

### NodePort 的工作原理

```
外部请求 → NodeIP:NodePort → kube-proxy(iptables) → Service → Pod
```

kube-proxy 在每个 Node 上监听 NodePort，将流量转发到 Service 的 ClusterIP，再由 ClusterIP 负载均衡到后端 Pod。**任何 Node 的 IP 都可以访问**，即使该 Node 上没有运行后端 Pod。

### 端口三层映射

- `nodePort`：Node 上开放的端口（30000-32767），外部访问入口
- `port`：Service 的 ClusterIP 端口，集群内部访问用
- `targetPort`：后端 Pod 的容器端口

### 适用场景

NodePort 适合快速测试和简单对外暴露。生产环境通常配合 **LoadBalancer** 或 **Ingress** 使用，NodePort 作为底层机制被 LoadBalancer 类型自动调用。

### 注意事项

- NodePort 范围由 `--service-node-port-range` 控制（默认 30000-32767）
- 如果不指定 nodePort，K8s 自动分配一个可用端口
- 每个 Node 上都会监听该端口，即使没有后端 Pod
""",
            key_fields=[
                {"name": "spec.type", "description": "必须设为 NodePort", "required": True, "example": "NodePort"},
                {"name": "spec.ports[].port", "description": "Service ClusterIP 端口", "required": True, "example": "80"},
                {"name": "spec.ports[].targetPort", "description": "后端 Pod 容器端口", "required": True, "example": "8080"},
                {"name": "spec.ports[].nodePort", "description": "Node 上开放的端口（30000-32767），可选自动分配", "required": False, "example": "30080"},
            ],
            diagram="""\
  外部访问流程 (NodePort)

  外部客户端                Node (任意节点)              Service              Backend Pods
  ┌──────────┐            ┌──────────────────┐       ┌──────────────┐     ┌─────────┐
  │ curl     │            │  NodeIP:30080    │       │ ClusterIP:80 │ ──► │ Pod1    │
  │ NodeIP   │ ─────────► │  (kube-proxy     │ ────► │              │ ──► │ Pod2    │
  │ :30080   │            │   iptables 规则) │       │ selector:    │ ──► │ Pod3    │
  └──────────┘            └──────────────────┘       │   app: web   │     └─────────┘
                                                      └──────────────┘
  端口映射: nodePort(30080) → port(80) → targetPort(8080)
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Service                   # 资源类型: Service
metadata:                       # 元数据
  name: web-svc                 # Service 名称
spec:                           # 规格定义
  type: NodePort                # ← 关键: 设为 NodePort
  selector:                     # 标签选择器
    app: web                    # 匹配 app=web 的 Pod
  ports:                        # 端口映射
  - port: 80                    # Service ClusterIP 端口
    targetPort: 8080            # 后端 Pod 端口
    nodePort: 30080             # Node 端口 (30000-32767，可选)
""",
            common_errors=[
                "忘记设 type: NodePort（默认是 ClusterIP，外部访问不了）",
                "nodePort 超出范围（必须是 30000-32767）",
                "nodePort 写成了字符串（应为整数）",
                "以为只能访问运行 Pod 的 Node（实际任何 Node 都可以）",
            ],
            tips=[
                "NodePort 适合测试，生产环境推荐用 LoadBalancer 或 Ingress",
                "用 kubectl get svc 查看 NodePort 分配情况",
                "不指定 nodePort 时 K8s 自动分配，避免端口冲突",
            ],
        ),
    ),
    Level(
        id="Q3.3",
        chapter="ch03",
        title="Service 发现 DNS",
        description="集群中已有一个 backend-svc Service。创建一个前端 Pod，通过环境变量引用 backend-svc 的 DNS 名称来访问后端服务",
        starter_yaml="""apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
spec:
  containers:
    - name: frontend
      image: nginx:latest
      # 添加 env，引用 backend-svc 的 DNS 名称
""",
        check_fn=_check_03_dns_discovery,
        lesson=Lesson(
            concept="""\
## DNS 服务发现

K8s 集群内置 **CoreDNS**，为每个 Service 自动创建 DNS 记录。Pod 内部可以直接用 Service 名称作为域名访问，无需知道 ClusterIP。

### DNS 命名规则

```
<service-name>.<namespace>.svc.cluster.local
```

- 同 namespace 下，直接用 `<service-name>` 即可
- 跨 namespace，用 `<service-name>.<namespace>`
- 完整 FQDN：`<service-name>.<namespace>.svc.cluster.local`

例如 `backend-svc` 在 default namespace 中，Pod 内 `curl backend-svc:3000` 就能访问。

### CoreDNS 工作原理

1. Pod 的 `/etc/resolv.conf` 指向 CoreDNS 的 ClusterIP
2. Pod 发起 DNS 查询 → CoreDNS 解析
3. 普通 Service：返回 ClusterIP
4. Headless Service：返回所有 Pod IP

### 为什么用 DNS 而非 IP？

- ClusterIP 在 Service 重建后可能变化
- DNS 名称基于 metadata.name，稳定不变
- 支持跨 namespace 发现，天然解耦

### 实践方式

在 Pod 的 env 或 command 中用 Service 名称作为主机名，CoreDNS 会自动解析。
""",
            key_fields=[
                {"name": "metadata.name", "description": "Service 名称，自动成为 DNS 名称", "required": True, "example": "backend-svc"},
                {"name": "spec.selector", "description": "标签选择器，匹配后端 Pod", "required": True, "example": "{app: backend}"},
                {"name": "spec.ports[].port", "description": "Service 端口，DNS 访问时用此端口", "required": True, "example": "3000"},
            ],
            diagram="""\
  DNS 解析流程

  Frontend Pod                CoreDNS                    Service
  ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
  │ env:         │           │              │           │ backend-svc  │
  │  BACKEND_URL=│ ─query──► │  解析        │ ─return──►│ ClusterIP    │
  │  backend-svc │           │  backend-svc │           │ 10.96.x.x    │
  │  :3000       │           │  → 10.96.x.x │           └──────┬───────┘
  └──────────────┘           └──────────────┘                  │
                                                                │ LB
                    Pod 用 DNS 名访问 ──────────────────────────►│
                                                                ▼
                                                          ┌──────────┐
                                                          │ Backend   │
                                                          │ Pods      │
                                                          └──────────┘
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: frontend-pod            # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: frontend              # 容器名
    image: nginx:latest         # 镜像
    env:                        # 环境变量
    - name: BACKEND_URL         # 变量名
      value: "backend-svc:3000" # ← 用 Service DNS 名访问后端
""",
            common_errors=[
                "用了 ClusterIP 而非 Service 名称（IP 会变，DNS 名稳定）",
                "Service 名称拼错（DNS 名严格匹配 metadata.name）",
                "跨 namespace 访问时只写 Service 名（需加 namespace 后缀）",
                "在 Pod 外部用 Service DNS 名（CoreDNS 只在集群内生效）",
            ],
            tips=[
                "DNS 发现是 K8s 服务解耦的核心机制--用名称而非 IP",
                "用 kubectl exec <pod> -- nslookup <service-name> 测试 DNS 解析",
                "同 namespace 用短名，跨 namespace 用 <name>.<namespace>",
            ],
        ),
    ),
    Level(
        id="Q3.4",
        chapter="ch03",
        title="Headless Service",
        description="集群中已有 3 个 db Pod（db-0, db-1, db-2）。创建一个 Headless Service db-svc，clusterIP 设为 None，selector 选择 app: db",
        starter_yaml="""apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  # 设置 clusterIP: None
  # 配置 selector 和 ports
""",
        check_fn=_check_04_headless_service,
        lesson=Lesson(
            concept="""\
## Headless Service

**Headless Service** 通过设置 `clusterIP: None` 实现，不分配虚拟 IP，DNS 查询直接返回后端 Pod 的 IP 列表。适用于需要**直连 Pod**的场景。

### 普通 Service vs Headless Service

| 特性 | ClusterIP Service | Headless Service |
|------|-------------------|------------------|
| clusterIP | 分配虚拟 IP | None（不分配） |
| DNS 查询 | 返回 ClusterIP | 返回所有 Pod IP |
| 负载均衡 | kube-proxy 轮询 | 客户端自行选择 |
| 适用场景 | 无状态服务 | 有状态服务 |

### 为什么需要 Headless？

普通 Service 做了负载均衡，客户端无法选择连哪个 Pod。但在有状态场景中（如数据库主从、分布式存储），客户端需要：
- 连接到**特定的 Pod**（如 Master 节点）
- 获取**所有 Pod 的 IP 列表**（如客户端做分片）
- Pod 有**稳定的网络标识**（如 StatefulSet 的 Pod DNS）

### StatefulSet + Headless Service

Headless Service 是 StatefulSet 的标配。StatefulSet 的每个 Pod 有有序名称（db-0, db-1, db-2），配合 Headless Service，每个 Pod 有独立的 DNS 记录：`db-0.db-svc.default.svc.cluster.local`，实现稳定的网络标识。

### DNS 返回

- 普通 Service：DNS 返回单个 ClusterIP
- Headless Service：DNS 返回 A 记录列表，每条对应一个 Pod IP
""",
            key_fields=[
                {"name": "spec.clusterIP", "description": "必须设为 None（字符串），表示 Headless", "required": True, "example": "None"},
                {"name": "spec.selector", "description": "标签选择器，选择后端 Pod", "required": True, "example": "{app: db}"},
                {"name": "spec.ports", "description": "端口映射（与普通 Service 相同）", "required": True, "example": "[{port: 5432, targetPort: 5432}]"},
            ],
            diagram="""\
  Headless Service vs 普通 Service

  普通 Service (clusterIP: 10.96.x.x)     Headless Service (clusterIP: None)
  ┌────────────────────────────┐           ┌────────────────────────────┐
  │  DNS: db-svc → 10.96.x.x  │           │  DNS: db-svc → [多A记录]   │
  │         │                  │           │         │                  │
  │    ClusterIP               │           │    无 ClusterIP            │
  │         │                  │           │         │                  │
  │    kube-proxy LB           │           │    客户端自行选择          │
  └────┬────┬────┬─────────────┘           └────┬────┬────┬─────────────┘
       │    │    │                              │    │    │
       ▼    ▼    ▼                              ▼    ▼    ▼
     db-0  db-1  db-2                        db-0  db-1  db-2
     :5432 :5432 :5432                       :5432 :5432 :5432

  DNS 返回单个 IP → 负载均衡               DNS 返回 Pod IP 列表 → 直连
""",
            example_yaml="""\
apiVersion: v1                  # K8s API 版本
kind: Service                   # 资源类型: Service
metadata:                       # 元数据
  name: db-svc                  # Service 名称
spec:                           # 规格定义
  clusterIP: None               # ← 关键: 设为 None (Headless)
  selector:                     # 标签选择器
    app: db                     # 匹配 app=db 的 Pod
  ports:                        # 端口映射
  - port: 5432                  # Service 端口
    targetPort: 5432            # 后端 Pod 端口
""",
            common_errors=[
                "clusterIP 写成 null 或不写（必须显式写 None 字符串）",
                "以为 Headless Service 不需要 selector（仍然需要 selector 选择 Pod）",
                "把 Headless 用在无状态服务上（无状态用普通 ClusterIP 即可）",
                "DNS 查询只返回一个 IP（Headless 应返回所有 Pod IP）",
            ],
            tips=[
                "Headless Service 主要配合 StatefulSet 使用，实现 Pod 稳定网络标识",
                "用 kubectl get svc 确认 clusterIP 显示为 None",
                "每个 Pod 有独立 DNS: <pod-name>.<svc-name>.<namespace>.svc.cluster.local",
            ],
        ),
    ),
]
