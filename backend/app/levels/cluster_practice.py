"""Cluster Practice: 集群实战关卡（6 关）

Q1.5 部署 Nginx Pod 并访问
Q2.5 Deployment 扩缩容实战
Q3.5 Service 间通信实战
Q4.5 ConfigMap 注入配置实战
Q5.5 PVC 持久化存储实战
Q6.5 nodeSelector 调度实战

这些关卡面向有真实 K8s 集群的学员，让他们部署真实资源并验证行为。
check_fn 使用模拟器校验 YAML 格式正确性，学员在真实集群上执行 kubectl 验证。
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q1.5 部署 Nginx Pod 并访问 ====================

def _check_15_deploy_nginx_pod(user_yaml: str) -> CheckResult:
    """Q1.5 部署 Nginx Pod 并访问"""
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

    # 取第一个 Pod
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

    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image 字段",
            hints=["spec.containers[0].image 必须指定镜像"],
        )

    # 检查镜像是否为 nginx
    if "nginx" not in image.lower():
        return CheckResult(
            ok=False,
            error=f"镜像应为 nginx 系列，实际为 '{image}'",
            hints=["使用 nginx:1.25 或 nginx:latest 等 nginx 镜像"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get pods",
            "  kubectl exec <pod-name> -- curl localhost",
        ],
    )


LEVEL_Q1_5 = Level(
    id="Q1.5",
    chapter="ch01",
    title="集群实战: 部署 Nginx 并访问",
    description="""
# 集群实战: 部署 Nginx Pod 并访问 🏗️

前面你学会了在模拟器里创建 Pod，现在来真实集群上动手！

## 任务

1. 编写一个 Nginx Pod 的 YAML
2. 用 `kubectl apply -f` 部署到你的集群
3. 用 `kubectl exec` 进入 Pod，curl 访问 Nginx 首页

## 要求

- `kind: Pod`
- 容器镜像使用 `nginx` 系列（如 `nginx:1.25`）
- 容器需要暴露 80 端口（`containerPort: 80`）

## 验证步骤

```bash
# 1. 部署
kubectl apply -f your-pod.yaml

# 2. 查看 Pod 状态（等待 Running）
kubectl get pods -w

# 3. 在集群内访问 Nginx 首页
kubectl exec <pod-name> -- curl -s localhost

# 4. 查看日志
kubectl logs <pod-name>
```

## 提示

- Pod 从 Pending -> Running 需要拉取镜像，首次可能较慢
- 如果 Pod 卡在 Pending，用 `kubectl describe pod <name>` 查看事件
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-web
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      # 补充 ports.containerPort: 80
""",
    check_fn=_check_15_deploy_nginx_pod,
    lesson=Lesson(
        concept="""\
## Pod 部署到真实集群后的完整流程

当你在真实集群上 `kubectl apply` 一个 Pod YAML 时，K8s 内部会发生以下步骤：

### 1. API Server 接收与校验

`kubectl` 将 YAML 发送给 API Server，API Server 进行：
- **认证**：验证你的身份（kubeconfig 中的证书/token）
- **授权**：检查你是否有权限创建 Pod（RBAC）
- **准入控制**：Admission Controller 可能修改或拒绝请求（如注入默认 ServiceAccount）

### 2. 调度器分配节点（Scheduling）

Pod 进入 `Pending` 状态，调度器（kube-scheduler）根据以下因素选择节点：
- **资源请求**：CPU/Memory 是否满足
- **nodeSelector / nodeAffinity**：标签约束
- **Taints & Tolerations**：污点排除
- **数据卷亲和性**：已挂载 PV 的节点优先

### 3. Kubelet 拉取镜像并启动容器

节点上的 kubelet 接收到调度决策后：
1. 调用容器运行时（containerd/CRI-O）拉取镜像
2. 创建 Pod 的网络命名空间和存储卷
3. 启动容器

### 4. Pod 状态流转

```
Pending → ContainerCreating → Running
```

- **Pending**：等待调度或拉取镜像
- **ContainerCreating**：正在创建容器
- **Running**：容器已启动，应用正在运行

### 5. 在集群内访问 Pod

Pod 获得集群内 IP（如 10.244.x.x），同集群的 Pod 可以直接访问。
也可以通过 `kubectl exec` 进入 Pod 内部访问：
```bash
kubectl exec <pod-name> -- curl localhost:80
```
""",
        key_fields=[
            {"name": "apiVersion", "description": "K8s API 版本，Pod 用 v1", "required": True, "example": "v1"},
            {"name": "kind", "description": "资源类型，这里是 Pod", "required": True, "example": "Pod"},
            {"name": "metadata.name", "description": "Pod 名称", "required": True, "example": "nginx-web"},
            {"name": "spec.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
            {"name": "spec.containers[].ports[].containerPort", "description": "容器暴露端口", "required": False, "example": "80"},
        ],
        diagram="""\
  kubectl apply ──→ API Server
                        │
                   ┌────┴────┐
                   │  调度器   │  选择节点
                   └────┬────┘
                        │
                   ┌────┴────┐
                   │ Kubelet  │  拉取镜像 + 启动容器
                   └────┬────┘
                        │
                   ┌────┴────┐
                   │  Pod     │  Running (10.244.x.x:80)
                   │ nginx    │
                   └─────────┘
                        │
              kubectl exec ──→ curl localhost:80
                        │
                     Nginx 首页 HTML
""",
        example_yaml="""\
apiVersion: v1            # K8s API 版本
kind: Pod                 # 资源类型: Pod
metadata:                 # 元数据
  name: nginx-web         # Pod 名称
  labels:                 # 标签（便于后续 Service 选择）
    app: nginx
spec:                     # 规格定义
  containers:             # 容器列表
  - name: nginx           # 容器名
    image: nginx:1.25     # Nginx 镜像
    ports:                # 暴露端口
    - containerPort: 80   # Nginx 默认端口
""",
        common_errors=[
            "Pod 卡在 Pending：通常是资源不足或调度约束无法满足，用 kubectl describe pod 排查",
            "Pod 卡在 ImagePullBackOff：镜像名拼写错误或仓库不可达",
            "Pod CrashLoopBackOff：容器启动后立即退出，检查应用日志",
            "忘记暴露 containerPort（不影响运行但影响后续 Service 关联）",
        ],
        tips=[
            "用 kubectl get pods -w 实时观察 Pod 状态变化",
            "用 kubectl describe pod <name> 查看调度事件和错误原因",
            "用 kubectl logs <name> 查看容器日志",
            "首次拉取镜像较慢，后续会使用本地缓存",
        ],
    ),
)


# ==================== Q2.5 Deployment 扩缩容实战 ====================

def _check_25_deployment_scaling(user_yaml: str) -> CheckResult:
    """Q2.5 Deployment 扩缩容实战"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.deployments:
        return CheckResult(
            ok=False,
            error="没有创建任何 Deployment",
            hints=["你需要 apply 一个 kind: Deployment 的 YAML"],
        )

    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    spec = dep.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    # 检查 replicas
    replicas = spec.get("replicas", 1)
    if replicas != 3:
        return CheckResult(
            ok=False,
            error=f"replicas 应为 3（初始 3 副本），实际为 {replicas}",
            hints=["spec.replicas 设为 3"],
        )

    # 检查 selector
    selector = spec.get("selector", {})
    if not isinstance(selector, dict) or not selector.get("matchLabels"):
        return CheckResult(
            ok=False,
            error="Deployment 缺少 spec.selector.matchLabels",
            hints=["selector.matchLabels 用于匹配 Pod 模板标签"],
        )

    # 检查 template
    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(
            ok=False,
            error="Deployment 缺少 spec.template",
            hints=["template 定义 Pod 模板"],
        )

    # 检查 selector 与 template labels 匹配
    tmpl_labels = template.get("metadata", {}).get("labels", {})
    sel_labels = selector.get("matchLabels", {})
    if not isinstance(tmpl_labels, dict) or not isinstance(sel_labels, dict):
        return CheckResult(ok=False, error="selector 或 template labels 格式错误", hints=[])

    for k, v in sel_labels.items():
        if tmpl_labels.get(k) != v:
            return CheckResult(
                ok=False,
                error=f"selector.matchLabels.{k}={v} 与 template.labels 不匹配",
                hints=["selector 的标签必须和 template 的标签一致"],
            )

    # 检查 template 有 containers
    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="template 缺少 spec", hints=[])
    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="template.spec 缺少 containers", hints=[])

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get deployment",
            "  # 扩容到 5 副本:",
            "  kubectl scale deployment <name> --replicas=5",
            "  kubectl get pods -w  # 观察 Pod 扩容过程",
        ],
    )


LEVEL_Q2_5 = Level(
    id="Q2.5",
    chapter="ch02",
    title="集群实战: Deployment 扩缩容",
    description="""
# 集群实战: Deployment 扩缩容 📈

学会创建 Deployment 后，来真实集群上体验扩缩容！

## 任务

1. 编写一个 3 副本的 Deployment YAML
2. 部署到集群，观察 3 个 Pod 被创建
3. 用 `kubectl scale` 扩容到 5 副本
4. 观察新增 Pod 的创建过程

## 要求

- `kind: Deployment`
- `replicas: 3`（初始 3 副本）
- `selector.matchLabels` 与 `template.metadata.labels` 匹配
- 容器使用 nginx 镜像

## 验证步骤

```bash
# 1. 部署 3 副本
kubectl apply -f deploy.yaml
kubectl get deployment

# 2. 观察 Pod
kubectl get pods -l app=<your-app>

# 3. 扩容到 5 副本
kubectl scale deployment <name> --replicas=5

# 4. 观察扩容过程
kubectl get pods -w -l app=<your-app>

# 5. 缩容回 3
kubectl scale deployment <name> --replicas=3
```

## 提示

- Deployment 的 selector 必须和 template labels 匹配
- 扩容时新 Pod 会经历 Pending → ContainerCreating → Running
- `kubectl get deployment` 的 READY 列显示 `当前/期望` 副本数
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        # 补充容器定义 (name + image)
""",
    check_fn=_check_25_deployment_scaling,
    lesson=Lesson(
        concept="""\
## Deployment 控制器如何管理 Pod 副本

Deployment 是 K8s 中最常用的工作负载控制器，它通过 **Reconcile Loop（协调循环）** 维持期望的 Pod 副本数。

### 控制器工作流程

```
用户设定 replicas=3
         │
         ▼
┌─────────────────┐
│  Deployment      │
│  Controller      │ ← 持续监控
└────────┬────────┘
         │
    ┌────┴────┐
    │ 当前状态  │  实际运行 Pod 数
    └────┬────┘
         │
    ┌────┴────────────────┐
    │ 期望=3, 当前=N       │
    │ N<3 → 创建 (3-N) Pod │
    │ N>3 → 删除 (N-3) Pod │
    └─────────────────────┘
```

### 扩容过程

当你执行 `kubectl scale deployment web --replicas=5`：

1. API Server 更新 Deployment 的 `spec.replicas` 字段
2. Deployment Controller 检测到期望副本数从 3 变为 5
3. Controller 通过 ReplicaSet 创建 2 个新 Pod
4. 调度器将新 Pod 调度到合适的节点
5. Kubelet 拉取镜像并启动容器

### 关键概念

- **期望状态 vs 实际状态**：Deployment 持续将实际状态向期望状态收敛
- **ReplicaSet**：Deployment 实际通过 ReplicaSet 管理 Pod，每次更新模板会创建新 ReplicaSet
- **自愈能力**：如果某个 Pod 崩溃或节点故障，Deployment 会自动创建新 Pod 补充

### kubectl scale 的本质

`kubectl scale` 只是修改了 `spec.replicas` 字段，真正的扩容/缩容由控制器异步完成。
""",
        key_fields=[
            {"name": "spec.replicas", "description": "期望副本数", "required": True, "example": "3"},
            {"name": "spec.selector.matchLabels", "description": "标签选择器，匹配 Pod 模板标签", "required": True, "example": "{app: web}"},
            {"name": "spec.template", "description": "Pod 模板，定义 Pod 的规格", "required": True, "example": "..."},
            {"name": "spec.template.metadata.labels", "description": "Pod 模板标签，必须与 selector 匹配", "required": True, "example": "{app: web}"},
        ],
        diagram="""\
  replicas: 3                    replicas: 5 (kubectl scale)
       │                                │
       ▼                                ▼
┌──────────────┐               ┌──────────────┐
│ Deployment    │               │ Deployment    │
│ Controller    │ ───────────→ │ Controller    │
│ (期望=3)      │   修改 spec   │ (期望=5)      │
└──────┬───────┘               └──────┬───────┘
       │                               │
   ┌───┼───┐                       ┌───┼───┬───┐
   ▼   ▼   ▼                       ▼   ▼   ▼   ▼   ▼
 Pod1 Pod2 Pod3                  Pod1 Pod2 Pod3 Pod4 Pod5
 (已运行)                        (已运行)        (新建中)
""",
        example_yaml="""\
apiVersion: apps/v1          # Deployment API 版本
kind: Deployment             # 资源类型
metadata:                    # 元数据
  name: web-deploy           # Deployment 名称
spec:                        # 规格定义
  replicas: 3                # 期望 3 个副本
  selector:                  # 标签选择器
    matchLabels:             # 必须与 template labels 匹配
      app: web
  template:                  # Pod 模板
    metadata:                # Pod 元数据
      labels:                # Pod 标签
        app: web
    spec:                    # Pod 规格
      containers:            # 容器列表
      - name: nginx          # 容器名
        image: nginx:1.25    # 镜像
        ports:               # 端口
        - containerPort: 80
""",
        common_errors=[
            "selector.matchLabels 与 template.labels 不匹配：K8s 会拒绝创建 Deployment",
            "忘记写 replicas（默认为 1，不是 0）",
            "扩容后 Pod 一直 Pending：节点资源不足，检查 kubectl describe node",
            "误以为 kubectl scale 是同步操作：实际上是异步的，Pod 创建需要时间",
        ],
        tips=[
            "用 kubectl get deployment -w 实时观察副本数变化",
            "用 kubectl get pods -l app=web -w 观察具体 Pod 的创建/删除",
            "kubectl scale 也可以缩容：--replicas=1 甚至 --replicas=0",
            "kubectl autoscale 可以根据 CPU 使用率自动扩缩容（HPA）",
        ],
    ),
)


# ==================== Q3.5 Service 间通信实战 ====================

def _check_35_service_communication(user_yaml: str) -> CheckResult:
    """Q3.5 Service 间通信实战"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 Service 是否创建
    if not state.services:
        return CheckResult(
            ok=False,
            error="没有创建任何 Service",
            hints=["YAML 中需要包含 kind: Service 的文档"],
        )

    # 检查 Deployment 是否创建
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="没有创建任何 Deployment",
            hints=["YAML 中需要包含 kind: Deployment 的文档", "用 --- 分隔多文档 YAML"],
        )

    # 取 Service 和 Deployment
    svc_name = next(iter(state.services))
    svc = state.services[svc_name]
    svc_spec = svc.get("spec", {})
    if not isinstance(svc_spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    # 检查 Service selector
    selector = svc_spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(
            ok=False,
            error="Service 缺少 spec.selector",
            hints=["selector 用于将流量路由到匹配标签的 Pod"],
        )

    # 检查 Service ports
    ports = svc_spec.get("ports")
    if not isinstance(ports, list) or not ports:
        return CheckResult(
            ok=False,
            error="Service 缺少 spec.ports",
            hints=["至少定义一个端口映射，如 port: 80, targetPort: 80"],
        )

    p = ports[0]
    if not isinstance(p, dict) or "port" not in p:
        return CheckResult(ok=False, error="Service ports[0] 缺少 port 字段", hints=[])

    # 检查 Deployment template labels 与 Service selector 匹配
    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {})
    if not isinstance(dep_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = dep_spec.get("template", {})
    tmpl_labels = template.get("metadata", {}).get("labels", {})
    if not isinstance(tmpl_labels, dict):
        return CheckResult(ok=False, error="Deployment template labels 格式错误", hints=[])

    for k, v in selector.items():
        if tmpl_labels.get(k) != v:
            return CheckResult(
                ok=False,
                error=f"Service selector ({k}={v}) 与 Deployment template labels 不匹配",
                hints=["Service 的 selector 必须匹配 Deployment Pod 的标签"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get svc,deploy",
            "  # 在集群内通过 Service 名称访问:",
            "  kubectl exec <any-pod> -- curl <svc-name>:<port>",
        ],
    )


LEVEL_Q3_5 = Level(
    id="Q3.5",
    chapter="ch03",
    title="集群实战: Service 间通信",
    description="""
# 集群实战: Service 间通信 🔗

部署 Deployment 后，其他 Pod 如何稳定地访问它？答案就是 Service！

## 任务

1. 编写一个多文档 YAML：包含 Deployment + ClusterIP Service
2. 部署到集群
3. 创建一个临时 Pod，通过 Service 名称访问 Deployment 的 Pod

## 要求

- `kind: Deployment`：运行 nginx，至少 2 副本
- `kind: Service`：ClusterIP 类型，selector 匹配 Deployment 的 Pod
- Service 的 `port` 和 `targetPort` 正确映射

## 验证步骤

```bash
# 1. 部署
kubectl apply -f web.yaml
kubectl get deploy,svc

# 2. 创建临时 Pod 测试访问
kubectl run debug --rm -it --image=busybox -- curl <svc-name>:<port>

# 3. 查看 Service 端点
kubectl get endpoints <svc-name>

# 4. 多次访问验证负载均衡
kubectl run debug --rm -it --image=busybox -- sh -c 'for i in 1 2 3 4 5; do curl -s <svc-name>:<port>; done'
```

## 提示

- Service 名称就是集群内的 DNS 名称：`<svc-name>.<namespace>.svc.cluster.local`
- selector 的 key-value 必须与 Deployment 的 template labels 完全匹配
- ClusterIP 是集群内部 IP，外部无法直接访问
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: ClusterIP
  # 补充 selector 和 ports
""",
    check_fn=_check_35_service_communication,
    lesson=Lesson(
        concept="""\
## Service 如何通过 selector 路由到 Pod

Service 是 K8s 中实现服务发现和负载均衡的核心组件。

### Service 工作原理

```
客户端 Pod → Service (ClusterIP: 10.96.x.x)
                    │
              ┌─────┴─────┐
              │  Endpoints  │  ← 由 selector 动态维护
              │  Controller │
              └─────┬─────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
       Pod1       Pod2       Pod3
    (10.244.1.x)(10.244.2.x)(10.244.3.x)
```

### selector 匹配机制

1. Service 的 `spec.selector` 定义了标签筛选条件
2. Endpoints Controller 持续扫描所有 Pod，将匹配 selector 的 Pod IP 加入 Endpoints
3. kube-proxy 在每个节点上配置 iptables/IPVS 规则，将 ClusterIP 流量转发到 Endpoints
4. 当 Pod 创建/销毁时，Endpoints 自动更新

### DNS 解析

CoreDNS 为每个 Service 创建 DNS 记录：
- `web-svc.default.svc.cluster.local` → ClusterIP
- 同 namespace 内可直接用 `web-svc` 访问

### 负载均衡

Service 默认使用 round-robin（轮询）策略将请求分发到后端 Pod。
kube-proxy 的 iptables 模式使用随机概率分配，IPVS 模式支持更多算法。

### ClusterIP 的局限

ClusterIP 只在集群内部可达。如果需要外部访问，使用 NodePort 或 LoadBalancer 类型。
""",
        key_fields=[
            {"name": "spec.type", "description": "Service 类型，ClusterIP 为默认", "required": False, "example": "ClusterIP"},
            {"name": "spec.selector", "description": "标签选择器，匹配后端 Pod", "required": True, "example": "{app: web}"},
            {"name": "spec.ports[].port", "description": "Service 暴露的端口", "required": True, "example": "80"},
            {"name": "spec.ports[].targetPort", "description": "后端 Pod 的端口", "required": True, "example": "80"},
        ],
        diagram="""\
  Pod (client)                     Pod (client)
       │                                │
       ▼                                ▼
  ┌─────────────────────────────────────────┐
  │        Service: web-svc                  │
  │        ClusterIP: 10.96.0.10:80          │
  │        DNS: web-svc.default.svc...       │
  └──────────────────┬──────────────────────┘
                     │
              selector: app=web
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │  Pod 1   │ │  Pod 2   │ │  Pod 3   │
    │ nginx    │ │ nginx    │ │ nginx    │
    │ :80      │ │ :80      │ │ :80      │
    └─────────┘ └─────────┘ └─────────┘
     Endpoints 自动维护，Pod 增减时自动更新
""",
        example_yaml="""\
apiVersion: apps/v1               # Deployment API
kind: Deployment                  # 资源类型: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 2                     # 2 个副本
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web                  # ← Service selector 匹配此标签
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80       # ← targetPort 指向此端口
---
apiVersion: v1                    # Service API
kind: Service                     # 资源类型: Service
metadata:
  name: web-svc                   # Service 名称 = DNS 名称
spec:
  type: ClusterIP                 # 集群内部访问
  selector:                       # 匹配 Pod 标签
    app: web                      # ← 必须与 Deployment template labels 一致
  ports:
  - port: 80                      # Service 端口
    targetPort: 80                # Pod 端口
""",
        common_errors=[
            "Service selector 与 Deployment template labels 不匹配：Endpoints 为空，流量无处转发",
            "targetPort 与 containerPort 不一致：连接被拒绝",
            "用 ClusterIP 在集群外访问：ClusterIP 只在集群内可达",
            "忘记用 --- 分隔多文档 YAML：Deployment 和 Service 需要在同一个 apply 中",
        ],
        tips=[
            "用 kubectl get endpoints <svc-name> 确认 Service 有后端 Pod",
            "用 kubectl exec 进入 Pod 后 curl <svc-name>:<port> 测试连通性",
            "Endpoints 为空时，检查 selector 拼写和 Pod 标签",
            "Service 名称即 DNS 名，同 namespace 内直接用名称访问",
        ],
    ),
)


# ==================== Q4.5 ConfigMap 注入配置实战 ====================

def _check_45_configmap_injection(user_yaml: str) -> CheckResult:
    """Q4.5 ConfigMap 注入配置实战"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 ConfigMap 是否创建
    if not state.configmaps:
        return CheckResult(
            ok=False,
            error="没有创建任何 ConfigMap",
            hints=["YAML 中需要包含 kind: ConfigMap 的文档"],
        )

    # 检查 ConfigMap 有 data
    cm_name = next(iter(state.configmaps))
    cm = state.configmaps[cm_name]
    cm_data = cm.get("data")
    if not isinstance(cm_data, dict) or not cm_data:
        return CheckResult(
            ok=False,
            error="ConfigMap 缺少 data 字段或 data 为空",
            hints=["data 是键值对形式存储配置的地方"],
        )

    # 检查 Pod 是否创建
    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["YAML 中需要包含 kind: Pod 的文档，引用 ConfigMap"],
        )

    # 检查 Pod 是否引用了 ConfigMap
    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    pod_spec = pod.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    # 检查是否通过 envFrom 或 env.configMapKeyRef 引用 ConfigMap
    found_env_ref = False
    for c in containers:
        if not isinstance(c, dict):
            continue
        # 检查 envFrom
        env_from = c.get("envFrom", [])
        if isinstance(env_from, list):
            for ef in env_from:
                if isinstance(ef, dict):
                    ref = ef.get("configMapRef", {})
                    if isinstance(ref, dict) and ref.get("name"):
                        found_env_ref = True
                        break
        # 检查 env[].configMapKeyRef
        env_list = c.get("env", [])
        if isinstance(env_list, list):
            for e in env_list:
                if isinstance(e, dict):
                    val_from = e.get("valueFrom", {})
                    if isinstance(val_from, dict):
                        cm_ref = val_from.get("configMapKeyRef", {})
                        if isinstance(cm_ref, dict) and cm_ref.get("name"):
                            found_env_ref = True
                            break
        if found_env_ref:
            break

    if not found_env_ref:
        return CheckResult(
            ok=False,
            error="Pod 没有引用 ConfigMap（缺少 envFrom 或 env[].configMapKeyRef）",
            hints=[
                "方式1: envFrom + configMapRef 注入所有 key 为环境变量",
                "方式2: env[].valueFrom.configMapKeyRef 注入单个 key",
            ],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  # 验证环境变量已注入:",
            f"  kubectl exec <pod-name> -- env | grep <config-key>",
            "  # 查看完整环境变量:",
            "  kubectl exec <pod-name> -- env",
        ],
    )


LEVEL_Q4_5 = Level(
    id="Q4.5",
    chapter="ch04",
    title="集群实战: ConfigMap 注入配置",
    description="""
# 集群实战: ConfigMap 注入配置 ⚙️

将配置与镜像解耦是 K8s 的最佳实践。ConfigMap 让你无需重新构建镜像就能修改应用配置。

## 任务

1. 编写一个多文档 YAML：ConfigMap + Pod
2. Pod 通过环境变量读取 ConfigMap 中的配置
3. 部署后验证环境变量已正确注入

## 要求

- `kind: ConfigMap`：包含至少 2 个键值对配置
- `kind: Pod`：通过 `envFrom` 或 `env` 引用 ConfigMap
- 容器使用 nginx 或 busybox 镜像

## 验证步骤

```bash
# 1. 部署
kubectl apply -f config.yaml

# 2. 查看环境变量
kubectl exec <pod-name> -- env

# 3. 验证特定配置项
kubectl exec <pod-name> -- env | grep APP_MODE

# 4. 修改 ConfigMap（注意：envFrom 注入的变量不会热更新）
kubectl edit configmap <name>
# 已运行的 Pod 不会自动更新环境变量，需要重启 Pod
kubectl delete pod <pod-name>  # 触发重建
```

## 提示

- `envFrom` 一次性注入 ConfigMap 所有 key 为环境变量
- `env[].valueFrom.configMapKeyRef` 精确注入单个 key
- 环境变量注入方式不会热更新，需要重启 Pod 才能生效
- Volume 挂载方式支持热更新（后续学习）
""",
    starter_yaml="""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      # 补充 envFrom 引用 app-config
""",
    check_fn=_check_45_configmap_injection,
    lesson=Lesson(
        concept="""\
## 配置分离的最佳实践

在传统部署中，配置通常打包在镜像里，修改配置需要重新构建镜像。K8s 的 ConfigMap 实现了配置与镜像的解耦。

### ConfigMap 注入方式对比

| 方式 | 特点 | 热更新 | 适用场景 |
|------|------|--------|----------|
| envFrom | 批量注入所有 key 为环境变量 | ❌ | 大量简单配置 |
| env[].configMapKeyRef | 精确注入单个 key | ❌ | 少量特定配置 |
| Volume 挂载 | 作为文件挂载到容器 | ✅ | 配置文件（如 nginx.conf） |

### envFrom 工作原理

```
ConfigMap (app-config)          Pod (app-pod)
┌──────────────────┐           ┌──────────────────┐
│ data:            │           │ spec.containers:  │
│   APP_MODE: prod │  envFrom  │ - envFrom:        │
│   LOG_LEVEL: info│ ────────→ │   - configMapRef: │
│   DB_HOST: ...   │           │     name: app-config│
└──────────────────┘           │                   │
                               │ 环境变量:          │
                               │   APP_MODE=prod   │
                               │   LOG_LEVEL=info  │
                               │   DB_HOST=...     │
                               └──────────────────┘
```

### 为什么环境变量不热更新？

K8s 的环境变量在容器启动时由 kubelet 注入，之后不可变。
修改 ConfigMap 后，已运行 Pod 的环境变量不会更新。
需要删除 Pod 让 Deployment 重建（或 rollout restart）。

### 配置分离的好处

1. **同一镜像，不同环境**：dev/staging/prod 使用不同 ConfigMap
2. **快速迭代**：修改配置无需重新构建镜像
3. **安全性**：敏感配置用 Secret 而非 ConfigMap
4. **版本管理**：ConfigMap 可以纳入 Git 管理
""",
        key_fields=[
            {"name": "data", "description": "ConfigMap 的配置数据，键值对形式", "required": True, "example": "{APP_MODE: production}"},
            {"name": "spec.containers[].envFrom", "description": "批量注入 ConfigMap 所有 key 为环境变量", "required": False, "example": "[{configMapRef: {name: app-config}}]"},
            {"name": "spec.containers[].env[].valueFrom.configMapKeyRef", "description": "精确注入单个 key", "required": False, "example": "{name: app-config, key: APP_MODE}"},
        ],
        diagram="""\
  ConfigMap (app-config)               Pod (app-pod)
  ┌─────────────────────┐             ┌──────────────────────┐
  │ data:                │             │ Container: app         │
  │   APP_MODE: prod     │  envFrom    │ ┌──────────────────┐  │
  │   LOG_LEVEL: info    │ ─────────→  │ │ ENV:              │  │
  │   DB_HOST: db.svc    │             │ │   APP_MODE=prod   │  │
  └─────────────────────┘             │ │   LOG_LEVEL=info  │  │
                                       │ │   DB_HOST=db.svc  │  │
  修改 ConfigMap →                     │ └──────────────────┘  │
  需重启 Pod 才生效                     └──────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                  # ConfigMap API
kind: ConfigMap                 # 资源类型: ConfigMap
metadata:
  name: app-config              # ConfigMap 名称
data:                           # 配置数据（键值对）
  APP_MODE: production          # 应用模式
  LOG_LEVEL: info               # 日志级别
  DB_HOST: db.default.svc       # 数据库地址
---
apiVersion: v1                  # Pod API
kind: Pod                       # 资源类型: Pod
metadata:
  name: app-pod                 # Pod 名称
spec:
  containers:
  - name: app                   # 容器名
    image: nginx:1.25           # 镜像
    envFrom:                    # 批量注入环境变量
    - configMapRef:             # 引用 ConfigMap
        name: app-config        # ConfigMap 名称
""",
        common_errors=[
            "ConfigMap 和 Pod 在不同 namespace：引用会失败",
            "ConfigMap 的 key 名包含非法字符（环境变量名只能用大写字母、数字、下划线）",
            "期望修改 ConfigMap 后环境变量自动更新：环境变量不热更新",
            "把敏感信息放在 ConfigMap 而非 Secret：ConfigMap 数据是明文的",
        ],
        tips=[
            "用 kubectl get configmap <name> -o yaml 查看 ConfigMap 完整内容",
            "用 kubectl exec <pod> -- env 验证环境变量是否注入成功",
            "修改 ConfigMap 后用 kubectl rollout restart deployment/<name> 触发 Pod 重建",
            "复杂配置文件推荐用 Volume 挂载方式，支持热更新",
        ],
    ),
)


# ==================== Q5.5 PVC 持久化存储实战 ====================

def _check_55_pvc_persistent_storage(user_yaml: str) -> CheckResult:
    """Q5.5 PVC 持久化存储实战"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 PVC 是否创建
    if not state.persistentvolumeclaims:
        return CheckResult(
            ok=False,
            error="没有创建任何 PVC",
            hints=["YAML 中需要包含 kind: PersistentVolumeClaim 的文档"],
        )

    # 检查 PVC 有 storage 请求
    pvc_name = next(iter(state.persistentvolumeclaims))
    pvc = state.persistentvolumeclaims[pvc_name]
    pvc_spec = pvc.get("spec", {})
    if not isinstance(pvc_spec, dict):
        return CheckResult(ok=False, error="PVC 缺少 spec", hints=[])

    resources = pvc_spec.get("resources", {})
    if not isinstance(resources, dict):
        return CheckResult(ok=False, error="PVC 缺少 spec.resources", hints=[])

    requests = resources.get("requests", {})
    if not isinstance(requests, dict) or "storage" not in requests:
        return CheckResult(
            ok=False,
            error="PVC 缺少 spec.resources.requests.storage",
            hints=["指定存储大小，如 storage: 1Gi"],
        )

    # 检查 Pod 是否创建
    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["YAML 中需要包含 kind: Pod 的文档，挂载 PVC"],
        )

    # 检查 Pod 是否挂载了 PVC
    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    pod_spec = pod.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    # 检查 volumes 中的 persistentVolumeClaim
    volumes = pod_spec.get("volumes", [])
    if not isinstance(volumes, list) or not volumes:
        return CheckResult(
            ok=False,
            error="Pod 缺少 spec.volumes（需要定义 PVC 卷）",
            hints=["在 volumes 中用 persistentVolumeClaim 引用 PVC"],
        )

    found_pvc_mount = False
    for vol in volumes:
        if not isinstance(vol, dict):
            continue
        pvc_ref = vol.get("persistentVolumeClaim", {})
        if isinstance(pvc_ref, dict) and pvc_ref.get("claimName"):
            found_pvc_mount = True
            break

    if not found_pvc_mount:
        return CheckResult(
            ok=False,
            error="Pod 的 volumes 中没有 persistentVolumeClaim 引用",
            hints=["volumes 中添加 persistentVolumeClaim.claimName 引用 PVC"],
        )

    # 检查 volumeMounts
    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    found_mount = False
    for c in containers:
        if not isinstance(c, dict):
            continue
        mounts = c.get("volumeMounts", [])
        if isinstance(mounts, list) and mounts:
            found_mount = True
            break

    if not found_mount:
        return CheckResult(
            ok=False,
            error="容器缺少 volumeMounts（需要挂载 PVC 卷）",
            hints=["在 containers[].volumeMounts 中挂载 PVC 卷"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get pvc",
            "  # 写入数据:",
            f"  kubectl exec <pod-name> -- sh -c 'echo hello > <mount-path>/test.txt'",
            "  # 验证持久化:",
            "  kubectl delete pod <pod-name> && kubectl apply -f <your-yaml>",
            f"  kubectl exec <pod-name> -- cat <mount-path>/test.txt",
        ],
    )


LEVEL_Q5_5 = Level(
    id="Q5.5",
    chapter="ch05",
    title="集群实战: PVC 持久化存储",
    description="""
# 集群实战: PVC 持久化存储 💾

Pod 是短暂的，数据会随 Pod 消失。PVC 让你的数据比 Pod 活得更久！

## 任务

1. 编写一个多文档 YAML：PVC + Pod
2. Pod 挂载 PVC，写入测试数据
3. 删除 Pod 后重新创建，验证数据仍然存在

## 要求

- `kind: PersistentVolumeClaim`：申请存储（如 1Gi）
- `kind: Pod`：挂载 PVC 到某个路径
- 容器使用 nginx 或 busybox 镜像

## 验证步骤

```bash
# 1. 部署
kubectl apply -f storage.yaml
kubectl get pvc  # 等待 Bound 状态

# 2. 写入数据
kubectl exec <pod-name> -- sh -c 'echo "persistent data" > /data/test.txt'
kubectl exec <pod-name> -- cat /data/test.txt

# 3. 删除 Pod
kubectl delete pod <pod-name>

# 4. 重新创建 Pod
kubectl apply -f storage.yaml

# 5. 验证数据持久化
kubectl exec <pod-name> -- cat /data/test.txt
# 应输出: persistent data
```

## 提示

- PVC 需要先于 Pod 创建（或有 StorageClass 自动供应 PV）
- PVC 状态为 Bound 表示已绑定 PV，可以挂载使用
- accessModes: ReadWriteOnce 表示同一节点可读写
- 删除 PVC 会释放存储（取决于回收策略）
""",
    starter_yaml="""\
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      # 补充 volumeMounts 和 volumes
""",
    check_fn=_check_55_pvc_persistent_storage,
    lesson=Lesson(
        concept="""\
## PV/PVC 生命周期和存储持久化

K8s 的存储体系将集群存储资源（PV）与应用存储需求（PVC）解耦。

### PV/PVC 生命周期

```
1. 管理员创建 PV（或 StorageClass 自动供应）
   PersistentVolume (data-pv, 5Gi, ReadWriteOnce)

2. 用户创建 PVC（申请存储）
   PersistentVolumeClaim (data-pvc, 1Gi)

3. 控制器匹配 PVC 与 PV（容量 >= 请求, 访问模式兼容）
   PVC.status.phase = Bound

4. Pod 挂载 PVC
   Pod.spec.volumes[].persistentVolumeClaim.claimName = data-pvc

5. Pod 读写数据 → 数据存储在 PV 对应的后端存储

6. Pod 删除 → PV 和数据保留
   Pod 重建 → 重新挂载同一 PVC → 数据仍在
```

### 存储持久化原理

```
Pod (app-pod)                    后端存储
┌────────────────┐              ┌────────────────┐
│ Container: app  │              │  /mnt/data/     │
│  /data ←────────┼── PVC ──────│  test.txt       │
│  (volumeMount)  │  (Bound)    │  "hello"        │
└────────────────┘              └────────────────┘
       ↑                              ↑
  Pod 删除后重建              数据依然在这里
  重新挂载 PVC               不受 Pod 生命周期影响
```

### 访问模式（AccessModes）

| 模式 | 缩写 | 说明 |
|------|------|------|
| ReadWriteOnce | RWO | 单节点读写（最常用） |
| ReadOnlyMany | ROX | 多节点只读 |
| ReadWriteMany | RWX | 多节点读写（需要 NFS 等共享存储） |

### StorageClass 自动供应

如果没有预先创建 PV，StorageClass 可以根据 PVC 请求自动创建 PV：
- 云平台：动态创建云盘（AWS EBS, GCP PD, Azure Disk）
- 本地：使用 hostPath 或 local volume
- 共享：使用 NFS, Ceph, GlusterFS 等

### 回收策略（Reclaim Policy）

- **Retain**：删除 PVC 后 PV 保留，数据不丢（需手动清理）
- **Delete**：删除 PVC 后自动删除 PV 和后端存储
- **Recycle**（已废弃）：清空数据后 PV 可重新绑定
""",
        key_fields=[
            {"name": "spec.accessModes", "description": "访问模式，ReadWriteOnce 最常用", "required": True, "example": "[ReadWriteOnce]"},
            {"name": "spec.resources.requests.storage", "description": "申请的存储容量", "required": True, "example": "1Gi"},
            {"name": "spec.volumes[].persistentVolumeClaim.claimName", "description": "引用 PVC 名称", "required": True, "example": "data-pvc"},
            {"name": "spec.containers[].volumeMounts", "description": "容器内挂载路径", "required": True, "example": "[{name: data, mountPath: /data}]"},
        ],
        diagram="""\
  PVC (data-pvc)                        PV (data-pv)
  ┌──────────────────┐                  ┌──────────────────┐
  │ spec:            │    Bound         │ spec:            │
  │   accessModes:   │ ←──────────────→ │   capacity: 5Gi  │
  │     [RWO]        │                  │   accessModes:   │
  │   resources:     │                  │     [RWO]        │
  │     storage: 1Gi │                  │   hostPath:      │
  └──────────────────┘                  │     /mnt/data    │
                                        └────────┬─────────┘
                                                 │
  Pod (app-pod)                                 │
  ┌──────────────────────┐                      │
  │ Container: app        │                      │
  │  volumeMounts:        │                      │
  │    /data ←──┐         │                      │
  └─────────────┼─────────┘                      │
                │                                │
  volumes:      │                                │
    - name: data│                                │
      pvc:      │                                │
        claimName: data-pvc ────→ PVC ────→ PV ──┘
""",
        example_yaml="""\
apiVersion: v1                     # PVC API
kind: PersistentVolumeClaim        # 资源类型: PVC
metadata:
  name: data-pvc                   # PVC 名称
spec:
  accessModes:                     # 访问模式
  - ReadWriteOnce                  # 单节点读写
  resources:                       # 资源请求
    requests:                      # 申请量
      storage: 1Gi                 # 1 GiB
---
apiVersion: v1                     # Pod API
kind: Pod                          # 资源类型: Pod
metadata:
  name: app-pod                    # Pod 名称
spec:
  containers:
  - name: app                      # 容器名
    image: nginx:1.25              # 镜像
    volumeMounts:                  # 卷挂载
    - name: data                   # 卷名（与 volumes 对应）
      mountPath: /data             # 挂载到容器的 /data
  volumes:                         # 卷定义
  - name: data                     # 卷名
    persistentVolumeClaim:         # 引用 PVC
      claimName: data-pvc          # PVC 名称
""",
        common_errors=[
            "PVC 一直 Pending：没有可用 PV 或 StorageClass，检查 kubectl get pv,sc",
            "volumeMounts.name 与 volumes.name 不匹配：挂载会失败",
            "accessModes 不兼容：PVC 请求 RWX 但 PV 只有 RWO",
            "删除 PVC 后数据丢失：回收策略为 Delete 时会自动清理后端存储",
        ],
        tips=[
            "用 kubectl get pvc 查看 PVC 绑定状态（Pending → Bound）",
            "用 kubectl describe pvc <name> 排查绑定失败原因",
            "测试持久化：写数据 → 删 Pod → 重建 Pod → 读数据",
            "生产环境推荐使用 StorageClass 动态供应，避免手动创建 PV",
        ],
    ),
)


# ==================== Q6.5 nodeSelector 调度实战 ====================

def _check_65_node_selector_scheduling(user_yaml: str) -> CheckResult:
    """Q6.5 nodeSelector 调度实战"""
    try:
        state = ClusterState()
        # 预置两个带标签的节点
        state = preset_state(state, """
apiVersion: v1
kind: Node
metadata:
  name: node-ssd
  labels:
    disktype: ssd
    cpu: x86
---
apiVersion: v1
kind: Node
metadata:
  name: node-hdd
  labels:
    disktype: hdd
    cpu: x86
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.pods:
        return CheckResult(
            ok=False,
            error="没有创建任何 Pod",
            hints=["创建一个带 nodeSelector 的 Pod"],
        )

    # 取用户创建的 Pod
    pod_name = next(iter(state.pods))
    pod = state.pods[pod_name]
    spec = pod.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    # 检查 nodeSelector
    node_selector = spec.get("nodeSelector")
    if not isinstance(node_selector, dict) or not node_selector:
        return CheckResult(
            ok=False,
            error="Pod 缺少 spec.nodeSelector",
            hints=["添加 nodeSelector: { disktype: ssd } 来调度到 SSD 节点"],
        )

    # 检查 nodeSelector 是否有效（至少有一个 key-value）
    has_valid_selector = False
    for k, v in node_selector.items():
        if k and v:
            has_valid_selector = True
            break

    if not has_valid_selector:
        return CheckResult(
            ok=False,
            error="nodeSelector 为空或无效",
            hints=["nodeSelector 需要至少一个有效的 key-value 对"],
        )

    # 检查 containers
    containers = spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  # 先给节点打标签:",
            "  kubectl label node <node-name> disktype=ssd",
            "  # 部署 Pod:",
            "  kubectl apply -f <your-yaml>",
            "  # 验证 Pod 调度到正确节点:",
            "  kubectl get pod <pod-name> -o wide",
            "  kubectl describe pod <pod-name> | grep Node:",
        ],
    )


LEVEL_Q6_5 = Level(
    id="Q6.5",
    chapter="ch06",
    title="集群实战: nodeSelector 调度",
    description="""
# 集群实战: nodeSelector 调度 🎯

控制 Pod 跑在哪个节点上！通过 nodeSelector 让调度器将 Pod 调度到有特定标签的节点。

## 任务

1. 给集群中的某个节点打标签（如 `disktype=ssd`）
2. 编写带 nodeSelector 的 Pod YAML
3. 部署后验证 Pod 被调度到正确的节点

## 要求

- `kind: Pod`
- `spec.nodeSelector` 指定节点标签约束
- 容器使用 nginx 镜像

## 验证步骤

```bash
# 1. 查看节点
kubectl get nodes

# 2. 给节点打标签
kubectl label node <node-name> disktype=ssd

# 3. 验证标签
kubectl get nodes --show-labels

# 4. 部署带 nodeSelector 的 Pod
kubectl apply -f pod.yaml

# 5. 验证 Pod 调度到正确节点
kubectl get pod <pod-name> -o wide

# 6. 查看调度详情
kubectl describe pod <pod-name> | grep -A5 Events

# 7. 清理标签（可选）
kubectl label node <node-name> disktype-
```

## 提示

- nodeSelector 是最简单的节点选择方式，要求节点必须有所需的全部标签
- 如果没有节点匹配标签，Pod 会一直 Pending
- `kubectl get nodes --show-labels` 查看所有节点标签
- nodeAffinity 是 nodeSelector 的增强版，支持更复杂的条件
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
  # 补充 nodeSelector 调度到 disktype=ssd 的节点
""",
    check_fn=_check_65_node_selector_scheduling,
    lesson=Lesson(
        concept="""\
## 调度器如何根据标签选择节点

K8s 调度器（kube-scheduler）负责决定 Pod 运行在哪个节点上。nodeSelector 是最简单的调度约束方式。

### 调度流程

```
Pod 提交 (带 nodeSelector: disktype=ssd)
              │
              ▼
    ┌─────────────────┐
    │  kube-scheduler  │
    │  (调度器)         │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │   过滤阶段        │  排除不满足 nodeSelector 的节点
    │   (Predicate)    │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │   打分阶段        │  对剩余节点按优先级打分
    │   (Priority)     │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │  选择最高分节点   │  绑定 Pod 到该节点
    │  (Bind)          │
    └─────────────────┘
```

### nodeSelector 匹配规则

nodeSelector 是**硬约束**：节点必须拥有 nodeSelector 中指定的**所有**标签键值对。

```
nodeSelector:
  disktype: ssd    # 节点必须有 disktype=ssd 标签
  cpu: x86         # 且必须有 cpu=x86 标签
```

如果没有任何节点满足所有条件，Pod 会一直处于 Pending 状态。

### 节点标签管理

```bash
# 添加标签
kubectl label node <node-name> disktype=ssd

# 查看标签
kubectl get nodes --show-labels

# 删除标签（key 后面加减号）
kubectl label node <node-name> disktype-
```

### K8s 内置节点标签

K8s 自动为节点添加一些标签：
- `kubernetes.io/hostname` - 节点主机名
- `kubernetes.io/os` - 操作系统（linux）
- `kubernetes.io/arch` - CPU 架构（amd64, arm64）
- `topology.kubernetes.io/zone` - 可用区
- `node.kubernetes.io/instance-type` - 实例类型（云平台）

### nodeSelector vs nodeAffinity

| 特性 | nodeSelector | nodeAffinity |
|------|-------------|--------------|
| 复杂度 | 简单 | 复杂 |
| 条件 | 等值匹配 | 支持 In/NotIn/Exists 等操作符 |
| 软约束 | ❌ | ✅ (preferred) |
| 命名空间 | 节点级 | 节点级 |

nodeSelector 适合简单场景，nodeAffinity 适合需要更精细控制的场景。
""",
        key_fields=[
            {"name": "spec.nodeSelector", "description": "节点标签选择器，硬约束", "required": True, "example": "{disktype: ssd}"},
            {"name": "spec.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
        ],
        diagram="""\
  Pod (nginx-pod)                     Nodes
  ┌──────────────────┐               ┌──────────────────────┐
  │ spec:            │               │ node-ssd              │
  │   nodeSelector:  │    匹配       │   labels:             │
  │     disktype: ssd│ ────────────→ │     disktype: ssd  ✓  │
  │   containers:    │               │     cpu: x86          │
  │   - nginx        │               └──────────────────────┘
  └──────────────────┘               ┌──────────────────────┐
                                     │ node-hdd              │
                                     │   labels:             │
                                     │     disktype: hdd  ✗  │
                                     │     cpu: x86          │
                                     └──────────────────────┘

  调度器: 过滤掉不匹配的节点 → 从匹配节点中选择最优
""",
        example_yaml="""\
apiVersion: v1              # K8s API 版本
kind: Pod                   # 资源类型: Pod
metadata:
  name: nginx-pod           # Pod 名称
spec:                       # 规格定义
  containers:               # 容器列表
  - name: nginx             # 容器名
    image: nginx:1.25       # 镜像
  nodeSelector:             # 节点选择器（硬约束）
    disktype: ssd           # 只调度到有 disktype=ssd 标签的节点
""",
        common_errors=[
            "Pod 一直 Pending：没有节点拥有所需标签，检查 kubectl get nodes --show-labels",
            "标签 key 拼写错误：disktype vs disk-type vs disk_type",
            "忘记先给节点打标签：需要先 kubectl label node 再部署 Pod",
            "nodeSelector 的值必须是字符串，不能是数字或布尔值",
        ],
        tips=[
            "用 kubectl get nodes --show-labels 查看所有节点标签",
            "用 kubectl describe pod <name> 查看调度失败原因",
            "K8s 内置标签如 kubernetes.io/hostname 可以用于指定具体节点",
            "需要更灵活的调度约束时，学习 nodeAffinity 和 Taints/Tolerations",
        ],
    ),
)


# ==================== 集群实战关卡汇总 ====================

CLUSTER_PRACTICE_LEVELS: list[Level] = [
    LEVEL_Q1_5,
    LEVEL_Q2_5,
    LEVEL_Q3_5,
    LEVEL_Q4_5,
    LEVEL_Q5_5,
    LEVEL_Q6_5,
]
