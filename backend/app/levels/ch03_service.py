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
from app.validator import Level, CheckResult
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
    ),
]
