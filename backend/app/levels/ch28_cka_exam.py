"""Chapter 28: CKA 模拟考试（5 关）

Q28.1 Pod 部署与调试 - 综合 Pod 操作
Q28.2 网络与安全策略 - Service+NetworkPolicy+Ingress
Q28.3 存储与配置 - PVC+ConfigMap+Secret
Q28.4 集群故障排查 - 综合诊断
Q28.5 RBAC 与安全 - 权限与安全上下文
"""
import yaml
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


def _parse_yaml_docs(user_yaml: str) -> list[dict]:
    """安全解析多文档 YAML，返回非 None 文档列表。"""
    docs = []
    for doc in yaml.safe_load_all(user_yaml):
        if doc is not None:
            docs.append(doc)
    return docs


# ==================== Q28.1 Pod 部署与调试 ====================

def _check_281_pod_deploy(user_yaml: str) -> CheckResult:
    """Q28.1 综合 Pod 操作：Deployment + Service + 资源限制"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写多文档 YAML"],
        )

    deploy_doc = None
    svc_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Deployment" and deploy_doc is None:
            deploy_doc = doc
        elif kind == "Service" and svc_doc is None:
            svc_doc = doc

    if not deploy_doc:
        return CheckResult(
            ok=False,
            error="缺少 Deployment",
            hints=["创建一个 Deployment 部署应用"],
        )

    spec = deploy_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    # 检查 replicas >= 2
    replicas = spec.get("replicas", 1)
    if not isinstance(replicas, int) or replicas < 2:
        return CheckResult(
            ok=False,
            error=f"CKA 要求 replicas >= 2，实际为 {replicas}",
            hints=["设置 replicas: 2 或更多"],
        )

    template = spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    pod_spec = template.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查资源限制
    resources = c.get("resources")
    if not isinstance(resources, dict):
        return CheckResult(
            ok=False,
            error="容器缺少 resources（CKA 要求设置资源限制）",
            hints=["添加 resources.requests 和 resources.limits"],
        )

    has_requests = isinstance(resources.get("requests"), dict)
    has_limits = isinstance(resources.get("limits"), dict)
    if not has_requests or not has_limits:
        return CheckResult(
            ok=False,
            error="resources 需要同时包含 requests 和 limits",
            hints=["添加 requests: {cpu: 100m, memory: 128Mi} 和 limits: {cpu: 200m, memory: 256Mi}"],
        )

    # 检查 readinessProbe
    has_readiness = isinstance(c.get("readinessProbe"), dict)
    if not has_readiness:
        return CheckResult(
            ok=False,
            error="容器缺少 readinessProbe（CKA 要求配置就绪探针）",
            hints=["添加 readinessProbe 配置 HTTP/TCP 检查"],
        )

    # 检查 Service
    if not svc_doc:
        return CheckResult(
            ok=False,
            error="缺少 Service（CKA 要求暴露服务）",
            hints=["添加一个 Service 暴露 Deployment"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["综合 Pod 部署完成！Deployment + Service + 资源限制 + 就绪探针 🎯"],
    )


LEVEL_Q28_1 = Level(
    id="Q28.1",
    chapter="ch28",
    title="Pod 部署与调试 - 综合 Pod 操作",
    description="""
# CKA 模拟 - Pod 部署与调试 🎯

**综合考核**：创建一个生产级 Deployment 并暴露 Service。

## 任务

创建多文档 YAML 包含：
1. **Deployment**（名称 `nginx-app`）
   - replicas: 3
   - 容器 `nginx`，镜像 `nginx:1.25`
   - resources: requests {cpu: 100m, memory: 128Mi}, limits {cpu: 200m, memory: 256Mi}
   - readinessProbe: HTTP GET / on port 80
2. **Service**（名称 `nginx-svc`）
   - type: NodePort
   - port: 80, targetPort: 80
   - selector 匹配 app: nginx-app

## 提示

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx-app
  template:
    metadata:
      labels:
        app: nginx-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  type: NodePort
  selector:
    app: nginx-app
  ports:
  - port: 80
    targetPort: 80
```
""",
    starter_yaml="""\
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx-app
  template:
    metadata:
      labels:
        app: nginx-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        # 添加 resources 和 readinessProbe
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  # 添加 type, selector, ports
""",
    check_fn=_check_281_pod_deploy,
    lesson=Lesson(
        concept="""\
## CKA Pod 部署与调试

CKA（Certified Kubernetes Administrator）考试中，Pod 部署是最核心的技能。本关模拟考试中常见的综合部署场景。

### CKA 考试要点

1. **快速编写 YAML**：考试时间有限，需要熟练手写 YAML
2. **资源管理**：必须设置 requests/limits
3. **健康检查**：配置 livenessProbe/readinessProbe
4. **服务暴露**：通过 Service 暴露应用
5. **调试能力**：使用 kubectl describe/logs/exec 排查问题

### 常用 kubectl 调试命令

```bash
kubectl get pods -o wide           # 查看 Pod 详情（含节点）
kubectl describe pod <pod>         # 查看 Pod 事件和状态
kubectl logs <pod> -c <container>  # 查看容器日志
kubectl exec -it <pod> -- /bin/sh  # 进入容器调试
kubectl get events --sort-by=.metadata.creationTimestamp  # 查看事件
```

### CKA 备考建议

- 练习不用 YAML 文件直接用 kubectl 创建资源
- 熟记 kubectl 速查表
- 理解 Pod 生命周期和状态
- 掌握滚动更新和回滚
""",
        key_fields=[
            {"name": "spec.replicas", "description": "多副本高可用", "required": True, "example": "3"},
            {"name": "resources.requests/limits", "description": "资源请求和限制", "required": True, "example": "{cpu: 100m, memory: 128Mi}"},
            {"name": "readinessProbe", "description": "就绪探针，控制流量进入", "required": True, "example": "{httpGet: {path: /, port: 80}}"},
            {"name": "Service.type", "description": "服务类型", "required": True, "example": "NodePort"},
        ],
        diagram="""\
  CKA 综合部署架构

  ┌─── Deployment (nginx-app, replicas: 3) ───┐
  │  containers:                              │
  │  - nginx:1.25                             │
  │    resources: requests + limits           │
  │    readinessProbe: HTTP GET / :80         │
  └──────────────────┬────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Pod-0   │ │ Pod-1   │ │ Pod-2   │
   │ Ready   │ │ Ready   │ │ Ready   │
   └────┬────┘ └────┬────┘ └────┬────┘
        └───────────┼───────────┘
                    │ selector: app=nginx-app
                    ▼
            ┌───────────────┐
            │ Service       │
            │ nginx-svc     │
            │ NodePort:80   │
            └───────────────┘
""",
        example_yaml="""\
---                                          # 文档分隔
apiVersion: apps/v1                          # Deployment API
kind: Deployment                             # 资源类型
metadata:                                    # 元数据
  name: nginx-app                            # Deployment 名称
spec:                                        # 规格
  replicas: 3                                # 3 副本
  selector:                                  # 标签选择器
    matchLabels:
      app: nginx-app
  template:                                  # Pod 模板
    metadata:
      labels:
        app: nginx-app
    spec:                                    # Pod 规格
      containers:                            # 容器列表
      - name: nginx                          # 容器名
        image: nginx:1.25                    # 镜像
        resources:                           # 资源限制
          requests:                          # 请求
            cpu: 100m
            memory: 128Mi
          limits:                            # 上限
            cpu: 200m
            memory: 256Mi
        readinessProbe:                      # 就绪探针
          httpGet:                           # HTTP 检查
            path: /                          # 检查路径
            port: 80                         # 检查端口
---                                          # 文档分隔
apiVersion: v1                               # Service API
kind: Service                                # 资源类型
metadata:                                    # 元数据
  name: nginx-svc                            # Service 名称
spec:                                        # 规格
  type: NodePort                             # 节点端口
  selector:                                  # 标签选择器
    app: nginx-app
  ports:                                     # 端口映射
  - port: 80                                 # Service 端口
    targetPort: 80                           # Pod 端口
""",
        common_errors=[
            "忘记设置 resources（CKA 考试中资源管理是必考项）",
            "readinessProbe 路径或端口写错导致 Pod 不 Ready",
            "Service selector 不匹配 Pod labels",
            "replicas 设为 1（考试要求多副本高可用）",
        ],
        tips=[
            "CKA 考试时间紧张，优先用 kubectl create deployment 快速生成再修改",
            "用 kubectl get pods -w 实时观察 Pod 状态变化",
            "Pod 一直 NotReady 时先检查 readinessProbe 配置",
        ],
    ),
)


# ==================== Q28.2 网络与安全策略 ====================

def _check_282_network_security(user_yaml: str) -> CheckResult:
    """Q28.2 Service + NetworkPolicy + Ingress 综合配置"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写多文档 YAML"],
        )

    svc_doc = None
    np_doc = None
    ingress_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Service" and svc_doc is None:
            svc_doc = doc
        elif kind == "NetworkPolicy" and np_doc is None:
            np_doc = doc
        elif kind == "Ingress" and ingress_doc is None:
            ingress_doc = doc

    if not svc_doc:
        return CheckResult(
            ok=False,
            error="缺少 Service",
            hints=["创建一个 Service 暴露后端 Pod"],
        )

    if not np_doc:
        return CheckResult(
            ok=False,
            error="缺少 NetworkPolicy（CKA 要求网络隔离）",
            hints=["创建一个 NetworkPolicy 限制 Pod 入站流量"],
        )

    # 检查 NetworkPolicy 结构
    np_spec = np_doc.get("spec", {})
    if not isinstance(np_spec, dict):
        return CheckResult(ok=False, error="NetworkPolicy 缺少 spec", hints=[])

    if "policyTypes" not in np_spec:
        return CheckResult(
            ok=False,
            error="NetworkPolicy 缺少 policyTypes",
            hints=["添加 policyTypes: [Ingress] 或 [Ingress, Egress]"],
        )

    if not ingress_doc:
        return CheckResult(
            ok=False,
            error="缺少 Ingress（CKA 要求配置七层路由）",
            hints=["创建一个 Ingress 配置域名路由"],
        )

    # 检查 Ingress 结构
    ing_spec = ingress_doc.get("spec", {})
    if not isinstance(ing_spec, dict):
        return CheckResult(ok=False, error="Ingress 缺少 spec", hints=[])

    rules = ing_spec.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Ingress 缺少 spec.rules",
            hints=["添加 rules 配置域名和路径路由"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["网络与安全综合配置完成！Service + NetworkPolicy + Ingress 🔒"],
    )


LEVEL_Q28_2 = Level(
    id="Q28.2",
    chapter="ch28",
    title="网络与安全策略 - Service+NetworkPolicy+Ingress",
    description="""
# CKA 模拟 - 网络与安全策略 🔒

**综合考核**：配置 Service、NetworkPolicy 和 Ingress 实现网络路由与安全隔离。

## 任务

创建多文档 YAML 包含：
1. **Service**（名称 `api-svc`）
   - selector: {app: api}
   - port: 8080, targetPort: 8080
2. **NetworkPolicy**（名称 `api-network-policy`）
   - podSelector: {app: api}
   - policyTypes: [Ingress]
   - ingress: 只允许 app=frontend 的 Pod 访问 8080 端口
3. **Ingress**（名称 `api-ingress`）
   - 规则: host `api.example.com`, 路径 `/` 路由到 `api-svc:8080`

## 提示

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  selector:
    app: api
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
```
""",
    starter_yaml="""\
---
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  # 添加 selector 和 ports
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  # 添加 podSelector, policyTypes, ingress
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
spec:
  # 添加 rules
""",
    check_fn=_check_282_network_security,
    lesson=Lesson(
        concept="""\
## CKA 网络与安全策略

CKA 考试中，网络配置是高频考点。需要综合运用 Service、NetworkPolicy 和 Ingress。

### 三者关系

```
外部用户 → Ingress (域名路由) → Service (负载均衡) → Pod
                                    ↑
                          NetworkPolicy (流量控制)
                          只允许特定 Pod 访问
```

### NetworkPolicy 要点

1. **默认拒绝**：创建 NetworkPolicy 后，未匹配的流量默认被拒绝
2. **podSelector**：选择受保护的 Pod
3. **ingress/egress**：入站/出站规则
4. **policyTypes**：指定策略类型（Ingress/Egress）

### Ingress 要点

1. **host**：域名匹配
2. **paths**：路径路由
3. **pathType**：Prefix（前缀匹配）/ Exact（精确匹配）
4. **backend**：后端 Service

### CKA 常见网络考题

- 创建 NetworkPolicy 限制 Pod 间通信
- 配置 Ingress 实现域名路由
- 排查 Service 无法访问的问题
- 理解 ClusterIP / NodePort / LoadBalancer 的区别
""",
        key_fields=[
            {"name": "Service.selector", "description": "匹配后端 Pod", "required": True, "example": "{app: api}"},
            {"name": "NetworkPolicy.podSelector", "description": "受保护的 Pod", "required": True, "example": "{matchLabels: {app: api}}"},
            {"name": "NetworkPolicy.ingress", "description": "入站规则", "required": True, "example": "[{from: [{podSelector: {matchLabels: {app: frontend}}}]}]"},
            {"name": "Ingress.rules", "description": "域名和路径路由规则", "required": True, "example": "[{host: api.example.com, http: {paths: [...]}}]"},
        ],
        diagram="""\
  网络与安全综合架构

  外部用户
      │
      ▼
  ┌──────────────────────────────────┐
  │  Ingress (api-ingress)           │
  │  host: api.example.com           │
  │  path: / → api-svc:8080          │
  └──────────────┬───────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────┐
  │  Service (api-svc)               │
  │  selector: {app: api}            │
  │  port: 8080                      │
  └──────────────┬───────────────────┘
                 │
  ┌──────────────┼──────────────────┐
  │              │                   │
  │  ┌───────────┴──────────────┐   │
  │  │  NetworkPolicy            │   │
  │  │  podSelector: {app: api}  │   │
  │  │  ingress:                 │   │
  │  │    from: {app: frontend}  │   │
  │  │    port: 8080             │   │
  │  └───────────┬──────────────┘   │
  │              │                   │
  │  ┌───────────▼──────────────┐   │
  │  │  Pod (app: api)          │   │
  │  │  只接受 frontend 的请求   │   │
  │  └──────────────────────────┘   │
  └──────────────────────────────────┘
""",
        example_yaml="""\
---                                          # 文档分隔
apiVersion: v1                               # Service API
kind: Service                                # 资源类型
metadata:                                    # 元数据
  name: api-svc                              # Service 名称
spec:                                        # 规格
  selector:                                  # 标签选择器
    app: api                                 # 匹配 app=api
  ports:                                     # 端口映射
  - port: 8080                               # Service 端口
    targetPort: 8080                         # Pod 端口
---                                          # 文档分隔
apiVersion: networking.k8s.io/v1             # NetworkPolicy API
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: api-network-policy                   # NP 名称
spec:                                        # 规格
  podSelector:                               # 保护的 Pod
    matchLabels:
      app: api                               # 匹配 app=api
  policyTypes:                               # 策略类型
  - Ingress                                  # 入站控制
  ingress:                                   # 入站规则
  - from:                                    # 允许的来源
    - podSelector:                           # 来自特定 Pod
        matchLabels:
          app: frontend                      # 只允许 frontend
    ports:                                   # 允许的端口
    - protocol: TCP
      port: 8080
---                                          # 文档分隔
apiVersion: networking.k8s.io/v1             # Ingress API
kind: Ingress                                # 资源类型
metadata:                                    # 元数据
  name: api-ingress                          # Ingress 名称
spec:                                        # 规格
  rules:                                     # 路由规则
  - host: api.example.com                    # 域名
    http:                                    # HTTP 路由
      paths:                                 # 路径列表
      - path: /                              # 路径
        pathType: Prefix                     # 前缀匹配
        backend:                             # 后端服务
          service:
            name: api-svc                    # Service 名
            port:
              number: 8080                   # Service 端口
""",
        common_errors=[
            "NetworkPolicy 的 podSelector 不匹配需要保护的 Pod",
            "Ingress backend 的 service name 与 Service 名称不一致",
            "NetworkPolicy ingress 中忘记指定 ports",
            "Ingress pathType 写错（K8s 1.19+ 必须指定 pathType）",
        ],
        tips=[
            "CKA 考试中 NetworkPolicy 是必考题，务必熟练",
            "用 kubectl get networkpolicy 查看 NP 规则",
            "排查网络问题时先检查 NetworkPolicy 再检查 Service selector",
        ],
    ),
)


# ==================== Q28.3 存储与配置 ====================

def _check_283_storage_config(user_yaml: str) -> CheckResult:
    """Q28.3 PVC + ConfigMap + Secret 综合配置"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写多文档 YAML"],
        )

    pvc_doc = None
    cm_doc = None
    secret_doc = None
    pod_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "PersistentVolumeClaim" and pvc_doc is None:
            pvc_doc = doc
        elif kind == "ConfigMap" and cm_doc is None:
            cm_doc = doc
        elif kind == "Secret" and secret_doc is None:
            secret_doc = doc
        elif kind == "Pod" and pod_doc is None:
            pod_doc = doc

    if not pvc_doc:
        return CheckResult(
            ok=False,
            error="缺少 PersistentVolumeClaim",
            hints=["创建一个 PVC 申请存储"],
        )

    pvc_spec = pvc_doc.get("spec", {})
    if not isinstance(pvc_spec, dict):
        return CheckResult(ok=False, error="PVC 缺少 spec", hints=[])
    if not pvc_spec.get("resources", {}).get("requests", {}).get("storage"):
        return CheckResult(
            ok=False,
            error="PVC 缺少 resources.requests.storage",
            hints=["指定存储大小，如 1Gi"],
        )

    if not cm_doc:
        return CheckResult(
            ok=False,
            error="缺少 ConfigMap",
            hints=["创建一个 ConfigMap 存储应用配置"],
        )

    cm_data = cm_doc.get("data")
    if not isinstance(cm_data, dict) or not cm_data:
        return CheckResult(
            ok=False,
            error="ConfigMap 缺少 data",
            hints=["在 data 中添加配置项"],
        )

    if not secret_doc:
        return CheckResult(
            ok=False,
            error="缺少 Secret",
            hints=["创建一个 Secret 存储敏感信息"],
        )

    secret_data = secret_doc.get("data")
    if not isinstance(secret_data, dict) or not secret_data:
        return CheckResult(
            ok=False,
            error="Secret 缺少 data",
            hints=["在 data 中添加 base64 编码的敏感数据"],
        )

    if not pod_doc:
        return CheckResult(
            ok=False,
            error="缺少 Pod（需要挂载 PVC、ConfigMap 和 Secret）",
            hints=["创建一个 Pod 使用以上资源"],
        )

    # 检查 Pod 是否使用了 PVC
    pod_spec = pod_doc.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    volumes = pod_spec.get("volumes", [])
    has_pvc = False
    has_cm = False
    has_secret = False
    if isinstance(volumes, list):
        for v in volumes:
            if not isinstance(v, dict):
                continue
            if v.get("persistentVolumeClaim"):
                has_pvc = True
            if v.get("configMap"):
                has_cm = True
            if v.get("secret"):
                has_secret = True

    if not has_pvc:
        return CheckResult(
            ok=False,
            error="Pod 未挂载 PVC",
            hints=["在 volumes 中添加 persistentVolumeClaim"],
        )
    if not has_cm:
        return CheckResult(
            ok=False,
            error="Pod 未挂载 ConfigMap",
            hints=["在 volumes 中添加 configMap"],
        )
    if not has_secret:
        return CheckResult(
            ok=False,
            error="Pod 未挂载 Secret",
            hints=["在 volumes 中添加 secret"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["存储与配置综合完成！PVC + ConfigMap + Secret + Pod 💾"],
    )


LEVEL_Q28_3 = Level(
    id="Q28.3",
    chapter="ch28",
    title="存储与配置 - PVC+ConfigMap+Secret",
    description="""
# CKA 模拟 - 存储与配置 💾

**综合考核**：创建 PVC、ConfigMap、Secret 并在 Pod 中挂载使用。

## 任务

创建多文档 YAML 包含：
1. **PVC**（名称 `data-pvc`）
   - accessModes: [ReadWriteOnce]
   - resources.requests.storage: 1Gi
2. **ConfigMap**（名称 `app-config`）
   - data: {APP_MODE: "production", LOG_LEVEL: "info"}
3. **Secret**（名称 `db-secret`）
   - data: {password: cGFzc3dvcmQxMjM=}  (base64 of "password123")
4. **Pod**（名称 `app-pod`）
   - 容器 `app`，镜像 `nginx:1.25`
   - 挂载 PVC 到 `/data`
   - 挂载 ConfigMap 到 `/etc/config`
   - 挂载 Secret 到 `/etc/secret`

## 提示

```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: "production"
  LOG_LEVEL: "info"
---
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: data
      mountPath: /data
    - name: config
      mountPath: /etc/config
    - name: secret
      mountPath: /etc/secret
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: data-pvc
  - name: config
    configMap:
      name: app-config
  - name: secret
    secret:
      secretName: db-secret
```
""",
    starter_yaml="""\
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  # 添加 accessModes 和 resources
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  # 添加配置项
---
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
data:
  # 添加 base64 编码数据
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    # 添加 volumeMounts
  # 添加 volumes (PVC + ConfigMap + Secret)
""",
    check_fn=_check_283_storage_config,
    lesson=Lesson(
        concept="""\
## CKA 存储与配置

CKA 考试中，存储和配置管理是核心考点。需要综合运用 PVC、ConfigMap 和 Secret。

### 资源关系

```
Pod
├── volumeMounts → 挂载到容器内路径
│   ├── PVC (持久化存储)
│   ├── ConfigMap (配置文件)
│   └── Secret (敏感数据)
```

### PVC 要点

1. **accessModes**：ReadWriteOnce / ReadOnlyMany / ReadWriteMany
2. **storageClassName**：指定 StorageClass（可省略用默认）
3. **resources.requests.storage**：申请容量

### ConfigMap vs Secret

| 特性 | ConfigMap | Secret |
|------|-----------|--------|
| 数据类型 | 明文 | base64 编码 |
| 用途 | 配置文件 | 密码/证书 |
| 挂载方式 | volume/env | volume/env |
| 大小限制 | 1MB | 1MB |

### 常用 kubectl 命令

```bash
kubectl get pvc                          # 查看 PVC
kubectl get configmap                    # 查看 ConfigMap
kubectl get secrets                      # 查看 Secret
kubectl describe pod <pod>               # 查看 Pod 挂载详情
echo -n 'password' | base64              # 生成 Secret 数据
echo 'cGFzc3dvcmQ=' | base64 --decode    # 解码 Secret
```
""",
        key_fields=[
            {"name": "PVC.spec.accessModes", "description": "访问模式", "required": True, "example": "[ReadWriteOnce]"},
            {"name": "PVC.spec.resources.requests.storage", "description": "存储容量", "required": True, "example": "1Gi"},
            {"name": "ConfigMap.data", "description": "配置数据（明文）", "required": True, "example": "{APP_MODE: production}"},
            {"name": "Secret.data", "description": "敏感数据（base64 编码）", "required": True, "example": "{password: cGFzc3dvcmQxMjM=}"},
            {"name": "Pod.spec.volumes", "description": "卷定义，引用 PVC/CM/Secret", "required": True, "example": "[{name: data, persistentVolumeClaim: {claimName: data-pvc}}]"},
        ],
        diagram="""\
  存储与配置综合架构

  ┌────────────────── Pod (app-pod) ──────────────────┐
  │                                                    │
  │  Container: app (nginx:1.25)                       │
  │  ┌──────────────────────────────────────────┐      │
  │  │ volumeMounts:                            │      │
  │  │  /data       ← volume: data              │      │
  │  │  /etc/config ← volume: config            │      │
  │  │  /etc/secret ← volume: secret            │      │
  │  └──────────────────────────────────────────┘      │
  │                                                    │
  │  volumes:                                          │
  │  ┌──────────┐ ┌──────────────┐ ┌──────────────┐   │
  │  │ data     │ │ config       │ │ secret       │   │
  │  │ (PVC)    │ │ (ConfigMap)  │ │ (Secret)     │   │
  │  └────┬─────┘ └──────┬───────┘ └──────┬───────┘   │
  └───────┼──────────────┼────────────────┼───────────┘
          │              │                │
          ▼              ▼                ▼
   ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
   │ PVC         │ │ ConfigMap    │ │ Secret       │
   │ data-pvc    │ │ app-config   │ │ db-secret    │
   │ 1Gi RWO     │ │ APP_MODE     │ │ password:    │
   │             │ │ LOG_LEVEL    │ │  cGFzc3...   │
   └─────────────┘ └──────────────┘ └──────────────┘
""",
        example_yaml="""\
---                                          # 文档分隔
apiVersion: v1                               # PVC API
kind: PersistentVolumeClaim                  # 资源类型
metadata:                                    # 元数据
  name: data-pvc                             # PVC 名称
spec:                                        # 规格
  accessModes:                               # 访问模式
  - ReadWriteOnce                            # 单节点读写
  resources:                                 # 资源请求
    requests:
      storage: 1Gi                           # 申请 1Gi
---                                          # 文档分隔
apiVersion: v1                               # ConfigMap API
kind: ConfigMap                              # 资源类型
metadata:                                    # 元数据
  name: app-config                           # ConfigMap 名称
data:                                        # 配置数据
  APP_MODE: "production"                     # 应用模式
  LOG_LEVEL: "info"                          # 日志级别
---                                          # 文档分隔
apiVersion: v1                               # Secret API
kind: Secret                                 # 资源类型
metadata:                                    # 元数据
  name: db-secret                            # Secret 名称
type: Opaque                                 # 通用类型
data:                                        # base64 编码数据
  password: cGFzc3dvcmQxMjM=                # password123 的 base64
---                                          # 文档分隔
apiVersion: v1                               # Pod API
kind: Pod                                    # 资源类型
metadata:                                    # 元数据
  name: app-pod                              # Pod 名称
spec:                                        # 规格
  containers:                                # 容器列表
  - name: app                                # 容器名
    image: nginx:1.25                        # 镜像
    volumeMounts:                            # 卷挂载
    - name: data                             # 挂载 PVC
      mountPath: /data
    - name: config                           # 挂载 ConfigMap
      mountPath: /etc/config
    - name: secret                           # 挂载 Secret
      mountPath: /etc/secret
  volumes:                                   # 卷定义
  - name: data                               # PVC 卷
    persistentVolumeClaim:
      claimName: data-pvc                    # 引用 PVC
  - name: config                             # ConfigMap 卷
    configMap:
      name: app-config                       # 引用 ConfigMap
  - name: secret                             # Secret 卷
    secret:
      secretName: db-secret                  # 引用 Secret
""",
        common_errors=[
            "Secret data 未做 base64 编码（如直接写 password: password123）",
            "PVC 的 claimName 与 PVC 名称不匹配",
            "ConfigMap/Secret 的 name 与 volumes 中引用的不一致",
            "volumeMounts 的 name 与 volumes 的 name 不匹配",
        ],
        tips=[
            "Secret base64 编码: echo -n 'value' | base64",
            "PVC 默认使用 default StorageClass，可用 kubectl get sc 查看",
            "ConfigMap 挂载为文件时，每个 key 变成一个文件",
        ],
    ),
)


# ==================== Q28.4 集群故障排查 ====================

def _check_284_troubleshoot(user_yaml: str) -> CheckResult:
    """Q28.4 综合诊断：修复有问题的 Pod 和 Service"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写修复后的多文档 YAML"],
        )

    deploy_doc = None
    svc_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Deployment" and deploy_doc is None:
            deploy_doc = doc
        elif kind == "Service" and svc_doc is None:
            svc_doc = doc

    if not deploy_doc:
        return CheckResult(
            ok=False,
            error="缺少修复后的 Deployment",
            hints=["提供一个修复后的 Deployment"],
        )

    # 检查 Deployment 是否有正确的 selector 和 template labels 匹配
    spec = deploy_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    selector = spec.get("selector", {}).get("matchLabels", {})
    template_labels = spec.get("template", {}).get("metadata", {}).get("labels", {})

    if not isinstance(selector, dict) or not selector:
        return CheckResult(
            ok=False,
            error="Deployment 缺少 selector.matchLabels",
            hints=["CKA 修复：添加 selector.matchLabels"],
        )

    if not isinstance(template_labels, dict) or not template_labels:
        return CheckResult(
            ok=False,
            error="Deployment 缺少 template.metadata.labels",
            hints=["CKA 修复：添加 template labels"],
        )

    # 检查 selector 和 template labels 是否匹配
    for k, v in selector.items():
        if template_labels.get(k) != v:
            return CheckResult(
                ok=False,
                error=f"selector 与 template labels 不匹配: selector[{k}]={v}, template={template_labels.get(k)}",
                hints=["CKA 修复：确保 selector.matchLabels 与 template labels 一致"],
            )

    # 检查容器配置
    pod_spec = spec.get("template", {}).get("spec", {})
    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(
            ok=False,
            error="Deployment 缺少 containers",
            hints=["CKA 修复：添加 containers"],
        )

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    if not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image（CKA 修复：添加正确的镜像）",
            hints=["指定镜像，如 nginx:1.25"],
        )

    # 检查容器端口
    has_port = False
    ports = c.get("ports", [])
    if isinstance(ports, list) and ports:
        has_port = True

    # 检查 Service
    if not svc_doc:
        return CheckResult(
            ok=False,
            error="缺少修复后的 Service",
            hints=["提供一个修复后的 Service"],
        )

    svc_spec = svc_doc.get("spec", {})
    if not isinstance(svc_spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    # 检查 Service selector 是否匹配 Deployment labels
    svc_selector = svc_spec.get("selector", {})
    if not isinstance(svc_selector, dict) or not svc_selector:
        return CheckResult(
            ok=False,
            error="Service 缺少 selector（CKA 修复：添加 selector 匹配 Pod labels）",
            hints=["Service selector 必须匹配 Deployment 的 template labels"],
        )

    for k, v in svc_selector.items():
        if template_labels.get(k) != v:
            return CheckResult(
                ok=False,
                error=f"Service selector 与 Pod labels 不匹配: svc[{k}]={v}, pod={template_labels.get(k)}",
                hints=["CKA 修复：Service selector 必须匹配 Pod labels"],
            )

    return CheckResult(
        ok=True, state=None,
        hints=["故障排查完成！selector/labels 匹配 + 正确配置 = 服务恢复 🔍"],
    )


LEVEL_Q28_4 = Level(
    id="Q28.4",
    chapter="ch28",
    title="集群故障排查 - 综合诊断",
    description="""
# CKA 模拟 - 集群故障排查 🔍

**综合考核**：诊断并修复一个有问题的 Deployment + Service 配置。

## 故障场景

一个应用部署后 Pod 一直处于 CrashLoopBackOff 且 Service 没有 Endpoints。经排查发现以下问题：
1. Deployment 的 selector 与 template labels 不匹配
2. 容器缺少 image
3. Service 的 selector 与 Pod labels 不匹配

## 任务

编写修复后的 Deployment + Service YAML：
1. **Deployment**（名称 `fixed-app`）
   - selector.matchLabels 和 template.labels 必须一致: {app: fixed-app}
   - 容器 `web`，镜像 `nginx:1.25`，端口 80
   - replicas: 2
2. **Service**（名称 `fixed-svc`）
   - selector 必须匹配 Pod labels: {app: fixed-app}
   - port: 80, targetPort: 80

## 提示

常见故障排查：
- selector 与 labels 不匹配 → Pod 无法被管理/发现
- 容器缺少 image → Pod CrashLoopBackOff
- Service selector 不匹配 → 无 Endpoints

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fixed-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fixed-app    # 必须与 template labels 一致
  template:
    metadata:
      labels:
        app: fixed-app    # 必须与 selector 一致
    spec:
      containers:
      - name: web
        image: nginx:1.25
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: fixed-svc
spec:
  selector:
    app: fixed-app    # 必须匹配 Pod labels
  ports:
  - port: 80
    targetPort: 80
```
""",
    starter_yaml="""\
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fixed-app
spec:
  replicas: 2
  # 修复: selector 必须匹配 template labels
  selector:
    matchLabels:
      app: wrong-app    # BUG: 不匹配
  template:
    metadata:
      labels:
        app: fixed-app
    spec:
      containers:
      - name: web
        # 修复: 添加 image
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: fixed-svc
spec:
  # 修复: selector 必须匹配 Pod labels
  selector:
    app: wrong-svc    # BUG: 不匹配
  ports:
  - port: 80
    targetPort: 80
""",
    check_fn=_check_284_troubleshoot,
    lesson=Lesson(
        concept="""\
## CKA 集群故障排查

CKA 考试中有大量故障排查题。掌握系统化的排查方法论至关重要。

### 排查方法论

```
1. kubectl get pods -o wide        → Pod 状态和节点
2. kubectl describe pod <pod>      → Events 和错误信息
3. kubectl logs <pod>              → 应用日志
4. kubectl logs <pod> --previous   → 上次崩溃的日志
5. kubectl get svc                 → Service 状态
6. kubectl get endpoints <svc>     → Endpoints 是否匹配
7. kubectl get events              → 集群事件
```

### 常见 Pod 故障

| 状态 | 原因 | 修复 |
|------|------|------|
| Pending | 资源不足/调度失败 | 检查 resources 和节点容量 |
| CrashLoopBackOff | 容器启动失败 | 检查 image/command/logs |
| ImagePullBackOff | 镜像拉取失败 | 检查镜像名和仓库权限 |
| ErrImagePull | 镜像不存在 | 修正镜像名 |
| OOMKilled | 内存不足 | 增加 memory limits |

### 常见 Service 故障

| 症状 | 原因 | 修复 |
|------|------|------|
| 无 Endpoints | selector 不匹配 | 修正 selector 匹配 Pod labels |
| 连接被拒绝 | targetPort 错误 | 检查 targetPort 匹配 containerPort |
| DNS 解析失败 | Service 不存在或命名错误 | 检查 Service 名称和命名空间 |

### selector + labels 匹配规则

```
Deployment:
  selector.matchLabels  ==  template.metadata.labels  (必须一致)

Service:
  spec.selector  ⊆  Pod labels  (必须匹配)
```
""",
        key_fields=[
            {"name": "Deployment.selector.matchLabels", "description": "必须与 template labels 完全一致", "required": True, "example": "{app: fixed-app}"},
            {"name": "Deployment.template.metadata.labels", "description": "Pod 标签，必须与 selector 一致", "required": True, "example": "{app: fixed-app}"},
            {"name": "containers[].image", "description": "容器镜像，缺失会导致 CrashLoopBackOff", "required": True, "example": "nginx:1.25"},
            {"name": "Service.selector", "description": "必须匹配 Pod 的 labels", "required": True, "example": "{app: fixed-app}"},
        ],
        diagram="""\
  故障排查流程

  故障现象:
  ┌─────────────────────────────────────┐
  │ Pod: CrashLoopBackOff               │
  │ Service: 无 Endpoints               │
  └─────────────────────────────────────┘
           │
           ▼ 排查
  ┌─────────────────────────────────────┐
  │ 问题 1: selector ≠ template labels  │
  │   selector: {app: wrong-app}        │
  │   labels:   {app: fixed-app}        │
  │   → Deployment 无法管理 Pod          │
  └─────────────────────────────────────┘
           │
           ▼ 排查
  ┌─────────────────────────────────────┐
  │ 问题 2: 容器缺少 image              │
  │   → CrashLoopBackOff                │
  └─────────────────────────────────────┘
           │
           ▼ 排查
  ┌─────────────────────────────────────┐
  │ 问题 3: Service selector ≠ Pod labels│
  │   svc selector: {app: wrong-svc}    │
  │   Pod labels:   {app: fixed-app}    │
  │   → 无 Endpoints                    │
  └─────────────────────────────────────┘
           │
           ▼ 修复
  ┌─────────────────────────────────────┐
  │ 修复后:                              │
  │   selector = labels = {app: fixed-app}│
  │   image: nginx:1.25                 │
  │   svc selector = {app: fixed-app}   │
  │   → Pod Running, Endpoints 正常     │
  └─────────────────────────────────────┘
""",
        example_yaml="""\
---                                          # 文档分隔
apiVersion: apps/v1                          # Deployment API
kind: Deployment                             # 资源类型
metadata:                                    # 元数据
  name: fixed-app                            # 名称
spec:                                        # 规格
  replicas: 2                                # 副本数
  selector:                                  # 标签选择器
    matchLabels:                             # 必须与 template labels 一致
      app: fixed-app                         # ✅ 已修复
  template:                                  # Pod 模板
    metadata:
      labels:                                # Pod 标签
        app: fixed-app                       # ✅ 与 selector 一致
    spec:                                    # Pod 规格
      containers:                            # 容器列表
      - name: web                            # 容器名
        image: nginx:1.25                    # ✅ 已添加 image
        ports:                               # 端口
        - containerPort: 80                  # 容器端口
---                                          # 文档分隔
apiVersion: v1                               # Service API
kind: Service                                # 资源类型
metadata:                                    # 元数据
  name: fixed-svc                            # 名称
spec:                                        # 规格
  selector:                                  # 标签选择器
    app: fixed-app                           # ✅ 匹配 Pod labels
  ports:                                     # 端口映射
  - port: 80                                 # Service 端口
    targetPort: 80                           # Pod 端口
""",
        common_errors=[
            "selector.matchLabels 与 template labels 不一致（最常见的 Deployment 错误）",
            "Service selector 不匹配 Pod labels（导致无 Endpoints）",
            "容器缺少 image 或 image 名称错误（导致 CrashLoopBackOff）",
            "targetPort 与 containerPort 不匹配（导致连接被拒绝）",
        ],
        tips=[
            "排查 Pod 故障: describe → logs → logs --previous",
            "排查 Service 故障: get endpoints → 检查 selector",
            "CKA 考试中故障排查题占 30%+，务必熟练",
        ],
    ),
)


# ==================== Q28.5 RBAC 与安全 ====================

def _check_285_rbac_security(user_yaml: str) -> CheckResult:
    """Q28.5 RBAC + ServiceAccount + 安全上下文综合配置"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写多文档 YAML"],
        )

    sa_doc = None
    role_doc = None
    rb_doc = None
    pod_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "ServiceAccount" and sa_doc is None:
            sa_doc = doc
        elif kind == "Role" and role_doc is None:
            role_doc = doc
        elif kind == "RoleBinding" and rb_doc is None:
            rb_doc = doc
        elif kind == "Pod" and pod_doc is None:
            pod_doc = doc

    if not sa_doc:
        return CheckResult(
            ok=False,
            error="缺少 ServiceAccount",
            hints=["创建一个 ServiceAccount"],
        )

    if not role_doc:
        return CheckResult(
            ok=False,
            error="缺少 Role",
            hints=["创建一个 Role 定义权限"],
        )

    # 检查 Role rules
    role_rules = role_doc.get("rules")
    if not isinstance(role_rules, list) or not role_rules:
        return CheckResult(
            ok=False,
            error="Role 缺少 rules",
            hints=["添加 rules 定义 API 权限"],
        )

    rule = role_rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    if not rule.get("apiGroups"):
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 apiGroups",
            hints=["指定 apiGroups，如 [''] 或 ['apps']"],
        )

    if not rule.get("resources"):
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 resources",
            hints=["指定 resources，如 ['pods', 'pods/log']"],
        )

    if not rule.get("verbs"):
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 verbs",
            hints=["指定 verbs，如 ['get', 'list', 'watch']"],
        )

    if not rb_doc:
        return CheckResult(
            ok=False,
            error="缺少 RoleBinding",
            hints=["创建一个 RoleBinding 绑定 SA 和 Role"],
        )

    # 检查 RoleBinding
    role_ref = rb_doc.get("roleRef")
    if not isinstance(role_ref, dict):
        return CheckResult(
            ok=False,
            error="RoleBinding 缺少 roleRef",
            hints=["添加 roleRef 引用 Role"],
        )

    subjects = rb_doc.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        return CheckResult(
            ok=False,
            error="RoleBinding 缺少 subjects",
            hints=["添加 subjects 引用 ServiceAccount"],
        )

    if not pod_doc:
        return CheckResult(
            ok=False,
            error="缺少 Pod（需要绑定 SA 并设置安全上下文）",
            hints=["创建一个 Pod 使用 SA 并配置 securityContext"],
        )

    # 检查 Pod 是否绑定了 SA
    pod_spec = pod_doc.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Pod 缺少 spec", hints=[])

    sa_name = pod_spec.get("serviceAccountName")
    if not sa_name:
        return CheckResult(
            ok=False,
            error="Pod 缺少 serviceAccountName（需要绑定 SA）",
            hints=["添加 spec.serviceAccountName 引用 ServiceAccount"],
        )

    # 检查 securityContext
    has_pod_sc = isinstance(pod_spec.get("securityContext"), dict)
    containers = pod_spec.get("containers", [])
    has_container_sc = False
    if isinstance(containers, list) and containers:
        c = containers[0]
        if isinstance(c, dict) and isinstance(c.get("securityContext"), dict):
            has_container_sc = True

    if not has_pod_sc and not has_container_sc:
        return CheckResult(
            ok=False,
            error="缺少 securityContext（CKA 要求配置安全上下文）",
            hints=["在 Pod 或容器级别添加 securityContext（如 runAsNonRoot: true）"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["RBAC 与安全综合完成！SA + Role + RoleBinding + securityContext 🏆"],
    )


LEVEL_Q28_5 = Level(
    id="Q28.5",
    chapter="ch28",
    title="RBAC 与安全 - 权限与安全上下文",
    description="""
# CKA 模拟 - RBAC 与安全 🏆

**综合考核**：配置 ServiceAccount、Role、RoleBinding 和 Pod 安全上下文。

## 任务

创建多文档 YAML 包含：
1. **ServiceAccount**（名称 `app-sa`）
2. **Role**（名称 `pod-reader`）
   - rules: apiGroups [""], resources ["pods", "pods/log"], verbs ["get", "list", "watch"]
3. **RoleBinding**（名称 `pod-reader-binding`）
   - roleRef: Role/pod-reader
   - subjects: ServiceAccount/app-sa
4. **Pod**（名称 `secure-app`）
   - serviceAccountName: app-sa
   - 容器 `app`，镜像 `nginx:1.25`
   - securityContext: runAsNonRoot: true, runAsUser: 1000

## 提示

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-reader
subjects:
- kind: ServiceAccount
  name: app-sa
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  serviceAccountName: app-sa
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: app
    image: nginx:1.25
```
""",
    starter_yaml="""\
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
# 添加 rules
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
# 添加 roleRef 和 subjects
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  # 添加 serviceAccountName
  # 添加 securityContext
  containers:
  - name: app
    image: nginx:1.25
""",
    check_fn=_check_285_rbac_security,
    lesson=Lesson(
        concept="""\
## CKA RBAC 与安全

CKA 考试中，RBAC（基于角色的访问控制）和安全上下文是必考内容。

### RBAC 四要素

```
ServiceAccount (身份) → RoleBinding (绑定) → Role (权限) → API 操作
```

1. **ServiceAccount**：Pod 的身份标识
2. **Role**：命名空间级权限规则
3. **RoleBinding**：将 Role 绑定到 SA/User/Group
4. **ClusterRole/ClusterRoleBinding**：集群级权限

### securityContext 要点

```yaml
# Pod 级别
spec:
  securityContext:
    runAsNonRoot: true      # 禁止 root 运行
    runAsUser: 1000         # 以 UID 1000 运行
    runAsGroup: 2000        # 以 GID 2000 运行
    fsGroup: 3000           # 卷文件组

# 容器级别
spec:
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false  # 禁止提权
      readOnlyRootFilesystem: true      # 只读根文件系统
      capabilities:
        drop: ["ALL"]                   # 删除所有 Linux capabilities
```

### 常用 kubectl 命令

```bash
kubectl auth can-i get pods --as=system:serviceaccount:default:app-sa  # 检查权限
kubectl get role,rolebinding                                           # 查看 RBAC
kubectl describe role <name>                                           # 查看 Role 规则
kubectl auth can-i --list --as=<user>                                  # 列出所有权限
```

### CKA 安全最佳实践

1. 为每个应用创建专用 ServiceAccount
2. 遵循最小权限原则（只授予必要的 verbs）
3. Pod 禁止 root 运行（runAsNonRoot: true）
4. 容器只读文件系统（readOnlyRootFilesystem: true）
5. 删除不必要的 capabilities
""",
        key_fields=[
            {"name": "Role.rules[].apiGroups", "description": "API 组", "required": True, "example": '[""]'},
            {"name": "Role.rules[].resources", "description": "资源类型", "required": True, "example": '["pods", "pods/log"]'},
            {"name": "Role.rules[].verbs", "description": "操作动词", "required": True, "example": '["get", "list", "watch"]'},
            {"name": "RoleBinding.roleRef", "description": "引用 Role", "required": True, "example": "{apiGroup: rbac.authorization.k8s.io, kind: Role, name: pod-reader}"},
            {"name": "RoleBinding.subjects", "description": "绑定的身份", "required": True, "example": "[{kind: ServiceAccount, name: app-sa}]"},
            {"name": "Pod.spec.serviceAccountName", "description": "绑定的 SA", "required": True, "example": "app-sa"},
            {"name": "securityContext", "description": "安全上下文", "required": True, "example": "{runAsNonRoot: true, runAsUser: 1000}"},
        ],
        diagram="""\
  RBAC + 安全上下文综合架构

  ┌────────────────────────────────────────────────────┐
  │  ServiceAccount (app-sa)                           │
  │  Pod 的身份标识                                     │
  └──────────────────────┬─────────────────────────────┘
                         │ 绑定
                         ▼
  ┌────────────────────────────────────────────────────┐
  │  RoleBinding (pod-reader-binding)                  │
  │  roleRef: Role/pod-reader                          │
  │  subjects: ServiceAccount/app-sa                   │
  └──────────────────────┬─────────────────────────────┘
                         │ 授予
                         ▼
  ┌────────────────────────────────────────────────────┐
  │  Role (pod-reader)                                 │
  │  rules:                                            │
  │  - apiGroups: [""]                                 │
  │    resources: ["pods", "pods/log"]                 │
  │    verbs: ["get", "list", "watch"]                 │
  └────────────────────────────────────────────────────┘

  ┌────────────────── Pod (secure-app) ────────────────┐
  │  serviceAccountName: app-sa                        │
  │  securityContext:                                  │
  │    runAsNonRoot: true    ◄── 禁止 root             │
  │    runAsUser: 1000       ◄── 非 root 用户          │
  │  containers:                                       │
  │  - app (nginx:1.25)                                │
  └────────────────────────────────────────────────────┘
""",
        example_yaml="""\
---                                          # 文档分隔
apiVersion: v1                               # SA API
kind: ServiceAccount                         # 资源类型
metadata:                                    # 元数据
  name: app-sa                               # SA 名称
---                                          # 文档分隔
apiVersion: rbac.authorization.k8s.io/v1     # RBAC API
kind: Role                                   # 资源类型: Role
metadata:                                    # 元数据
  name: pod-reader                           # Role 名称
rules:                                       # 权限规则
- apiGroups:                                 # API 组
  - ""                                       # 核心组
  resources:                                 # 资源类型
  - pods                                     # Pod 资源
  - pods/log                                 # Pod 日志
  verbs:                                     # 操作权限
  - get                                      # 获取
  - list                                     # 列表
  - watch                                    # 监听
---                                          # 文档分隔
apiVersion: rbac.authorization.k8s.io/v1     # RBAC API
kind: RoleBinding                            # 资源类型: RoleBinding
metadata:                                    # 元数据
  name: pod-reader-binding                   # 绑定名称
roleRef:                                     # 引用 Role
  apiGroup: rbac.authorization.k8s.io        # API 组
  kind: Role                                 # Role 类型
  name: pod-reader                           # Role 名称
subjects:                                    # 绑定主体
- kind: ServiceAccount                       # SA 类型
  name: app-sa                               # SA 名称
---                                          # 文档分隔
apiVersion: v1                               # Pod API
kind: Pod                                    # 资源类型
metadata:                                    # 元数据
  name: secure-app                           # Pod 名称
spec:                                        # 规格
  serviceAccountName: app-sa                 # 绑定 SA
  securityContext:                           # Pod 安全上下文
    runAsNonRoot: true                       # 禁止 root
    runAsUser: 1000                          # UID 1000
  containers:                                # 容器列表
  - name: app                                # 容器名
    image: nginx:1.25                        # 镜像
""",
        common_errors=[
            "Role rules 中 apiGroups 写成 ['v1']（核心 API 组是空字符串 ''）",
            "RoleBinding 的 roleRef 或 subjects 与 Role/SA 名称不匹配",
            "Pod 忘记绑定 serviceAccountName（默认使用 default SA）",
            "securityContext 写在 spec 外面（应在 spec 下或 container 内）",
        ],
        tips=[
            "用 kubectl auth can-i --as=system:serviceaccount:default:app-sa get pods 验证权限",
            "apiGroups 的核心组是空字符串 ''，不是 'v1'",
            "Pod 级 securityContext 对所有容器生效，容器级可覆盖 Pod 级",
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
