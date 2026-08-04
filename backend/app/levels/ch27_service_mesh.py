"""Chapter 27: Service Mesh 概念 - Istio CRD（5 关）

Q27.1 Istio 架构概念 - 控制面/数据面
Q27.2 VirtualService - 虚拟服务路由
Q27.3 DestinationRule - 目标规则
Q27.4 Gateway - 网关配置
Q27.5 集群实战 - 完整 Service Mesh 配置
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


# ==================== 预置 Istio CRD（供 Q27.2-Q27.5 使用）====================

_ISTIO_CRD_YAML = """\
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: virtualservices.networking.istio.io
spec:
  group: networking.istio.io
  names:
    kind: VirtualService
    plural: virtualservices
    singular: virtualservice
    shortNames:
    - vs
  versions:
  - name: v1
    served: true
    storage: true
  scope: Namespaced
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: destinationrules.networking.istio.io
spec:
  group: networking.istio.io
  names:
    kind: DestinationRule
    plural: destinationrules
    singular: destinationrule
    shortNames:
    - dr
  versions:
  - name: v1
    served: true
    storage: true
  scope: Namespaced
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: gateways.networking.istio.io
spec:
  group: networking.istio.io
  names:
    kind: Gateway
    plural: gateways
    singular: gateway
  versions:
  - name: v1
    served: true
    storage: true
  scope: Namespaced
"""


# ==================== Q27.1 Istio 架构概念 ====================

def _check_271_istio_arch(user_yaml: str) -> CheckResult:
    """Q27.1 创建 Istio 控制面 Deployment"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: Deployment 的 YAML"],
        )

    deploy_doc = None
    ns_doc = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind", "")
        if kind == "Deployment" and deploy_doc is None:
            deploy_doc = doc
        elif kind == "Namespace" and ns_doc is None:
            ns_doc = doc

    if not deploy_doc:
        return CheckResult(
            ok=False,
            error="没有找到 Deployment",
            hints=["你需要创建一个 kind: Deployment 的 YAML 🌐"],
        )

    metadata = deploy_doc.get("metadata", {})
    if not isinstance(metadata, dict):
        return CheckResult(ok=False, error="Deployment 缺少 metadata", hints=[])

    # 检查是否在 istio-system namespace
    ns = metadata.get("namespace", "")
    name = metadata.get("name", "").lower()

    # 检查是否是 Istio 控制面组件
    istio_keywords = ["istiod", "istio", "pilot", "citadel", "galley"]
    is_istio = any(kw in name for kw in istio_keywords)

    if not is_istio and "istio" not in ns.lower():
        return CheckResult(
            ok=False,
            error="Deployment 名称或命名空间应与 Istio 相关（如 istiod, namespace: istio-system）",
            hints=["Istio 控制面组件通常部署在 istio-system 命名空间"],
        )

    spec = deploy_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    pod_spec = template.get("spec", {})
    if not isinstance(pod_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    containers = pod_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(
            ok=False,
            error="Deployment 缺少 containers",
            hints=["添加 containers 列表"],
        )

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    if not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["指定 Istio 控制面镜像，如 istio/pilot:1.21.0"],
        )

    # 检查是否在 istio-system namespace 或创建了这个 namespace
    if "istio" not in ns.lower() and not ns_doc:
        return CheckResult(
            ok=False,
            error="Istio 控制面应部署在 istio-system 命名空间",
            hints=["设置 metadata.namespace: istio-system 或创建 istio-system Namespace"],
        )

    return CheckResult(
        ok=True, state=None,
        hints=["Istio 控制面 (istiod) 管理所有数据面 Envoy 代理的配置 🌐"],
    )


LEVEL_Q27_1 = Level(
    id="Q27.1",
    chapter="ch27",
    title="Istio 架构概念 - 控制面/数据面",
    description="""
# Istio 架构概念 - 控制面/数据面 🌐

**Istio** 是 Kubernetes 上最流行的 Service Mesh 实现。它由**控制面**（istiod）和**数据面**（Envoy sidecar）组成。

## 任务

创建 Istio 控制面 Deployment：
- `kind: Deployment`，名称 `istiod`
- `metadata.namespace: istio-system`
- 容器镜像 `istio/pilot:1.21.0`
- 同时创建 `istio-system` Namespace

## 提示

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: istio-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: istiod
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: istiod
  template:
    metadata:
      labels:
        app: istiod
    spec:
      containers:
      - name: istiod
        image: istio/pilot:1.21.0
```
""",
    starter_yaml="""\
---
apiVersion: v1
kind: Namespace
metadata:
  name: istio-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: istiod
  # 添加 namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: istiod
  template:
    metadata:
      labels:
        app: istiod
    spec:
      containers:
      # 添加 istiod 容器
""",
    check_fn=_check_271_istio_arch,
    lesson=Lesson(
        concept="""\
## Istio Service Mesh 架构

**Istio** 是一个开源 Service Mesh 平台，为微服务提供流量管理、安全、可观测性能力。

### 控制面与数据面

```
┌─────────────────────────────────────┐
│           控制面 (Control Plane)      │
│           istiod                     │
│  ┌─────────────────────────────┐    │
│  │ Pilot: 流量路由配置           │    │
│  │ Citadel: mTLS 证书管理       │    │
│  │ Galley: 配置验证             │    │
│  └─────────────────────────────┘    │
└────────────────┬────────────────────┘
                 │ xDS 下发配置
    ┌────────────┼────────────┐
    ▼            ▼            ▼
  Envoy       Envoy       Envoy    ← 数据面 (Data Plane)
  (Sidecar)   (Sidecar)   (Sidecar)
     │            │            │
  ┌──┴──┐     ┌──┴──┐     ┌──┴──┐
  │Pod A│     │Pod B│     │Pod C│
  │ App │     │ App │     │ App │
  └─────┘     └─────┘     └─────┘
```

### 控制面组件 (istiod)

- **Pilot**：将路由规则（VirtualService/DestinationRule）转换为 Envoy 配置
- **Citadel**：管理 mTLS 证书的签发和轮转
- **Galley**：验证 Istio 配置的合法性

### 数据面 (Envoy Sidecar)

- 以 Sidecar 方式注入到每个 Pod
- 拦截所有进出 Pod 的网络流量
- 执行路由、负载均衡、mTLS、熔断、重试等策略

### Sidecar 注入方式

1. **自动注入**：给 Namespace 打标签 `istio-injection=enabled`
2. **手动注入**：`istioctl kube-inject -f deployment.yaml`
""",
        key_fields=[
            {"name": "metadata.namespace", "description": "Istio 控制面部署在 istio-system 命名空间", "required": True, "example": "istio-system"},
            {"name": "spec.containers[].image", "description": "istiod 镜像", "required": True, "example": "istio/pilot:1.21.0"},
        ],
        diagram="""\
  Istio Service Mesh 架构

  ┌────────────────────────────────────────────────────┐
  │                 控制面 (istiod)                     │
  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
  │  │  Pilot  │  │ Citadel │  │ Galley  │            │
  │  │ 路由配置 │  │ mTLS证书│  │ 配置验证 │            │
  │  └────┬────┘  └────┬────┘  └─────────┘            │
  └───────┼────────────┼───────────────────────────────┘
          │ xDS 下发    │ 证书下发
          │             │
     ┌────┼─────────────┼────────────────┐
     │    ▼             ▼                │
     │  Envoy A      Envoy B      Envoy C │ ← 数据面
     │  (Sidecar)    (Sidecar)    (Sidecar)│
     │    │            │             │    │
     │  App A        App B        App C   │
     │  (Pod)        (Pod)        (Pod)   │
     └────────────────────────────────────┘

  流量路径: App A → Envoy A → (mTLS) → Envoy B → App B
""",
        example_yaml="""\
---                                    # 多文档分隔
apiVersion: v1                         # Namespace API
kind: Namespace                        # 资源类型
metadata:                              # 元数据
  name: istio-system                   # Istio 专用命名空间
---                                    # 多文档分隔
apiVersion: apps/v1                    # Deployment API
kind: Deployment                       # 资源类型
metadata:                              # 元数据
  name: istiod                         # 控制面组件名
  namespace: istio-system              # 部署在 istio-system
spec:                                  # 规格
  replicas: 1                          # 1 个副本
  selector:                            # 标签选择器
    matchLabels:
      app: istiod
  template:                            # Pod 模板
    metadata:
      labels:
        app: istiod
    spec:                              # Pod 规格
      containers:                      # 容器列表
      - name: istiod                   # 容器名
        image: istio/pilot:1.21.0      # Pilot 镜像
""",
        common_errors=[
            "把 istiod 部署在 default 命名空间（应部署在 istio-system）",
            "忘记创建 istio-system Namespace",
            "把控制面和数据面混淆（istiod 是控制面，Envoy 是数据面）",
        ],
        tips=[
            "Istio 1.5+ 将 Pilot/Citadel/Galley 合并为单一组件 istiod",
            "用 kubectl get pods -n istio-system 查看控制面状态",
            "Sidecar 自动注入: kubectl label namespace default istio-injection=enabled",
        ],
    ),
)


# ==================== Q27.2 VirtualService ====================

def _check_272_virtualservice(user_yaml: str) -> CheckResult:
    """Q27.2 创建 VirtualService 路由规则"""
    try:
        state = ClusterState()
        # 预注册 Istio CRD
        state = preset_state(state, _ISTIO_CRD_YAML)
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 查找 VirtualService
    vs_docs = [
        cr for cr in state.customresources.values()
        if isinstance(cr, dict) and cr.get("kind") == "VirtualService"
    ]

    if not vs_docs:
        return CheckResult(
            ok=False,
            error="没有找到 VirtualService",
            hints=["创建 kind: VirtualService 的 YAML，apiVersion: networking.istio.io/v1"],
        )

    vs = vs_docs[0]
    spec = vs.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="VirtualService 缺少 spec", hints=[])

    # 检查 hosts
    hosts = spec.get("hosts")
    if not isinstance(hosts, list) or not hosts:
        return CheckResult(
            ok=False,
            error="VirtualService 缺少 spec.hosts",
            hints=["添加 spec.hosts 指定目标服务，如 ['my-service']"],
        )

    # 检查 http 路由规则
    http = spec.get("http")
    if not isinstance(http, list) or not http:
        return CheckResult(
            ok=False,
            error="VirtualService 缺少 spec.http（HTTP 路由规则）",
            hints=["添加 spec.http 路由规则"],
        )

    route = http[0]
    if not isinstance(route, dict):
        return CheckResult(ok=False, error="http[0] 格式错误", hints=[])

    # 检查 route.destination
    destination = route.get("route")
    if not isinstance(destination, list) or not destination:
        return CheckResult(
            ok=False,
            error="http[0] 缺少 route（目标路由）",
            hints=["添加 route 列表指定目标服务和权重"],
        )

    dest = destination[0]
    if not isinstance(dest, dict):
        return CheckResult(ok=False, error="route[0] 格式错误", hints=[])

    dest_service = dest.get("destination", {})
    if not isinstance(dest_service, dict) or not dest_service.get("host"):
        return CheckResult(
            ok=False,
            error="route[0] 缺少 destination.host",
            hints=["指定目标服务 host，如 destination: {host: my-service}"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["VirtualService 定义了流量路由规则，如按路径/权重分发请求 🛤️"],
    )


LEVEL_Q27_2 = Level(
    id="Q27.2",
    chapter="ch27",
    title="VirtualService - 虚拟服务路由",
    description="""
# VirtualService - 虚拟服务路由 🛤️

**VirtualService** 定义了流量的路由规则，控制请求如何被分发到不同的服务版本或端点。

## 任务

创建一个 VirtualService：
- `kind: VirtualService`，`apiVersion: networking.istio.io/v1`
- 名称 `reviews-vs`
- hosts: `["reviews"]`
- http 路由规则：
  - 匹配 URI 前缀 `/api/v1`，路由到 `reviews` 服务 v1 版本
  - 其余流量路由到 `reviews` 服务 v2 版本

## 提示

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-vs
spec:
  hosts:
  - reviews
  http:
  - match:
    - uri:
        prefix: /api/v1
    route:
    - destination:
        host: reviews
        subset: v1
  - route:
    - destination:
        host: reviews
        subset: v2
```
""",
    starter_yaml="""\
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-vs
spec:
  # 添加 hosts 和 http 路由规则
""",
    check_fn=_check_272_virtualservice,
    lesson=Lesson(
        concept="""\
## VirtualService

**VirtualService** 是 Istio 的核心流量管理资源，定义了"如何路由到服务"。它将请求按 URI 路径、Header、权重等条件分发到不同的服务版本。

### VirtualService 的核心能力

1. **路径路由**：按 URI 前缀/精确匹配分发
2. **权重路由**：按百分比分流（灰度发布）
3. **Header 路由**：按请求头条件分发
4. **重写/重定向**：修改请求 URI 或重定向
5. **故障注入**：注入延迟或错误（测试用）
6. **重试/超时**：配置请求重试和超时

### 路由示例

```yaml
http:
# 按路径路由
- match:
  - uri:
      prefix: /api/v1
  route:
  - destination:
      host: reviews
      subset: v1

# 按权重路由（灰度发布: 90% v1, 10% v2）
- route:
  - destination:
      host: reviews
      subset: v1
    weight: 90
  - destination:
      host: reviews
      subset: v2
    weight: 10
```

### VirtualService vs Kubernetes Service

- **K8s Service**：基于 selector 的简单负载均衡
- **VirtualService**：基于 L7 的精细流量路由
""",
        key_fields=[
            {"name": "spec.hosts", "description": "目标服务主机名列表", "required": True, "example": "[reviews]"},
            {"name": "spec.http[]", "description": "HTTP 路由规则列表", "required": True, "example": "[{match: {uri: {prefix: /api}}, route: [...]}]"},
            {"name": "spec.http[].match", "description": "匹配条件（URI/Header 等）", "required": False, "example": "{uri: {prefix: /api/v1}}"},
            {"name": "spec.http[].route[].destination", "description": "目标服务", "required": True, "example": "{host: reviews, subset: v1}"},
            {"name": "spec.http[].route[].weight", "description": "流量权重（0-100）", "required": False, "example": "90"},
        ],
        diagram="""\
  VirtualService 流量路由

  ┌────────── VirtualService (reviews-vs) ──────────┐
  │  hosts: [reviews]                               │
  │  http:                                          │
  │  - match: uri.prefix=/api/v1                    │
  │    route: → reviews:v1                          │
  │  - route: → reviews:v2                          │
  └──────────────────┬──────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    /api/v1/*                 其他路径
         │                       │
         ▼                       ▼
   ┌───────────┐           ┌───────────┐
   │ reviews   │           │ reviews   │
   │ subset:v1 │           │ subset:v2 │
   └───────────┘           └───────────┘
""",
        example_yaml="""\
apiVersion: networking.istio.io/v1       # Istio 网络 API
kind: VirtualService                     # 资源类型
metadata:                                # 元数据
  name: reviews-vs                       # VS 名称
spec:                                    # 规格
  hosts:                                 # 目标服务
  - reviews                              # 服务名
  http:                                  # HTTP 路由规则
  - match:                               # 匹配条件
    - uri:
        prefix: /api/v1                  # 匹配 /api/v1 前缀
    route:                               # 路由目标
    - destination:                       # 目标服务
        host: reviews                    # 服务名
        subset: v1                       # 子集 v1
  - route:                               # 默认路由
    - destination:
        host: reviews                    # 服务名
        subset: v2                       # 子集 v2
""",
        common_errors=[
            "hosts 为空或不匹配实际服务名",
            "route 中忘记 destination.host",
            "subset 名称与 DestinationRule 中定义的不一致",
            "weight 总和不等于 100（Istio 要求权重总和为 100）",
        ],
        tips=[
            "用 kubectl get vs 查看所有 VirtualService",
            "VirtualService 通常与 DestinationRule 配合使用",
            "match 条件可以组合使用（URI + Header 同时匹配）",
        ],
    ),
)


# ==================== Q27.3 DestinationRule ====================

def _check_273_destinationrule(user_yaml: str) -> CheckResult:
    """Q27.3 创建 DestinationRule"""
    try:
        state = ClusterState()
        state = preset_state(state, _ISTIO_CRD_YAML)
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    dr_docs = [
        cr for cr in state.customresources.values()
        if isinstance(cr, dict) and cr.get("kind") == "DestinationRule"
    ]

    if not dr_docs:
        return CheckResult(
            ok=False,
            error="没有找到 DestinationRule",
            hints=["创建 kind: DestinationRule 的 YAML，apiVersion: networking.istio.io/v1"],
        )

    dr = dr_docs[0]
    spec = dr.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DestinationRule 缺少 spec", hints=[])

    # 检查 host
    host = spec.get("host")
    if not host:
        return CheckResult(
            ok=False,
            error="DestinationRule 缺少 spec.host",
            hints=["添加 spec.host 指定目标服务名"],
        )

    # 检查 subsets
    subsets = spec.get("subsets")
    if not isinstance(subsets, list) or not subsets:
        return CheckResult(
            ok=False,
            error="DestinationRule 缺少 spec.subsets（服务版本子集）",
            hints=["添加 subsets 定义服务版本，如 v1/v2"],
        )

    subset = subsets[0]
    if not isinstance(subset, dict):
        return CheckResult(ok=False, error="subsets[0] 格式错误", hints=[])

    if not subset.get("name"):
        return CheckResult(
            ok=False,
            error="subsets[0] 缺少 name",
            hints=["每个 subset 需要 name 字段，如 v1"],
        )

    # 检查至少有一个 subset 有 labels
    has_labels = any(
        isinstance(s, dict) and s.get("labels")
        for s in subsets
    )
    if not has_labels:
        return CheckResult(
            ok=False,
            error="subsets 中缺少 labels（用于区分不同版本）",
            hints=["为每个 subset 添加 labels 匹配 Pod 版本标签"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["DestinationRule 定义服务版本子集和流量策略（负载均衡、熔断等）🔧"],
    )


LEVEL_Q27_3 = Level(
    id="Q27.3",
    chapter="ch27",
    title="DestinationRule - 目标规则",
    description="""
# DestinationRule - 目标规则 🔧

**DestinationRule** 定义了流量到达目标服务后的策略，包括版本子集（subsets）、负载均衡、熔断等。

## 任务

创建一个 DestinationRule：
- `kind: DestinationRule`，`apiVersion: networking.istio.io/v1`
- 名称 `reviews-dr`
- host: `reviews`
- subsets:
  - name: v1, labels: {version: v1}
  - name: v2, labels: {version: v2}
- trafficPolicy: 简单轮询负载均衡

## 提示

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-dr
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
```
""",
    starter_yaml="""\
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-dr
spec:
  # 添加 host, subsets 和 trafficPolicy
""",
    check_fn=_check_273_destinationrule,
    lesson=Lesson(
        concept="""\
## DestinationRule

**DestinationRule** 定义了流量**到达目标服务后**的策略。它与 VirtualService 配合使用：VirtualService 决定"去哪"，DestinationRule 决定"怎么去"。

### DestinationRule 的核心能力

1. **版本子集**：通过 labels 将服务分为 v1/v2 等子集
2. **负载均衡**：ROUND_ROBIN / LEAST_CONN / RANDOM / PASSTHROUGH
3. **熔断**：连接池限制、异常检测
4. **mTLS**：配置双向 TLS 模式
5. **异常驱逐**：自动移除不健康的实例

### VirtualService + DestinationRule 配合

```
请求 → VirtualService (路由决策)
     → DestinationRule (版本选择 + 策略)
     → 目标 Pod
```

### 熔断配置示例

```yaml
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100    # 最大连接数
    http:
      http1MaxPendingRequests: 10  # 最大等待请求
  outlierDetection:
    consecutive5xxErrors: 5  # 连续 5 次 5xx 触发驱逐
    interval: 30s            # 检查间隔
    ejectTime: 30s           # 驱逐时长
```
""",
        key_fields=[
            {"name": "spec.host", "description": "目标服务名", "required": True, "example": "reviews"},
            {"name": "spec.subsets[].name", "description": "子集名称，VirtualService 通过此名称引用", "required": True, "example": "v1"},
            {"name": "spec.subsets[].labels", "description": "标签选择器，匹配 Pod 版本", "required": True, "example": "{version: v1}"},
            {"name": "spec.trafficPolicy", "description": "流量策略（负载均衡、熔断、mTLS）", "required": False, "example": "{loadBalancer: {simple: ROUND_ROBIN}}"},
        ],
        diagram="""\
  VirtualService + DestinationRule 配合

  ┌───── VirtualService (reviews-vs) ─────┐
  │  route:                               │
  │  - destination: {host: reviews,       │
  │      subset: v1}     ◄── 引用 subset   │
  └──────────────────┬────────────────────┘
                     │
                     ▼
  ┌───── DestinationRule (reviews-dr) ────┐
  │  host: reviews                        │
  │  subsets:                             │
  │  - name: v1, labels: {version: v1}   │ ← 定义 subset
  │  - name: v2, labels: {version: v2}   │
  │  trafficPolicy:                       │
  │    loadBalancer: ROUND_ROBIN          │
  └──────────────────┬────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    ┌───────────┐         ┌───────────┐
    │ Pod: v1   │         │ Pod: v2   │
    │ labels:   │         │ labels:   │
    │ version:v1│         │ version:v2│
    └───────────┘         └───────────┘
""",
        example_yaml="""\
apiVersion: networking.istio.io/v1        # Istio 网络 API
kind: DestinationRule                     # 资源类型
metadata:                                 # 元数据
  name: reviews-dr                        # DR 名称
spec:                                     # 规格
  host: reviews                           # 目标服务
  subsets:                                # 版本子集
  - name: v1                              # 子集名 v1
    labels:                               # 标签选择器
      version: v1                         # 匹配 version=v1
  - name: v2                              # 子集名 v2
    labels:
      version: v2                         # 匹配 version=v2
  trafficPolicy:                          # 流量策略
    loadBalancer:                         # 负载均衡
      simple: ROUND_ROBIN                 # 轮询
""",
        common_errors=[
            "subset name 与 VirtualService 中引用的不一致",
            "subset labels 不匹配 Pod 的实际标签",
            "忘记 host 字段（DestinationRule 必须指定目标服务）",
            '把 DestinationRule 和 VirtualService 搞混（DR 定义"怎么去"，VS 定义"去哪"）',
        ],
        tips=[
            "用 kubectl get dr 查看所有 DestinationRule",
            "DestinationRule 的 subset 名被 VirtualService 的 destination.subset 引用",
            "熔断和异常驱逐只在 DestinationRule 中配置，VirtualService 不支持",
        ],
    ),
)


# ==================== Q27.4 Gateway ====================

def _check_274_gateway(user_yaml: str) -> CheckResult:
    """Q27.4 创建 Istio Gateway"""
    try:
        state = ClusterState()
        state = preset_state(state, _ISTIO_CRD_YAML)
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    gw_docs = [
        cr for cr in state.customresources.values()
        if isinstance(cr, dict) and cr.get("kind") == "Gateway"
    ]

    if not gw_docs:
        return CheckResult(
            ok=False,
            error="没有找到 Gateway",
            hints=["创建 kind: Gateway 的 YAML，apiVersion: networking.istio.io/v1"],
        )

    gw = gw_docs[0]
    spec = gw.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Gateway 缺少 spec", hints=[])

    # 检查 selector
    selector = spec.get("selector")
    if not isinstance(selector, dict) or not selector:
        return CheckResult(
            ok=False,
            error="Gateway 缺少 spec.selector",
            hints=["添加 selector 选择 Istio Ingress Gateway，如 {istio: ingressgateway}"],
        )

    # 检查 servers
    servers = spec.get("servers")
    if not isinstance(servers, list) or not servers:
        return CheckResult(
            ok=False,
            error="Gateway 缺少 spec.servers（端口配置）",
            hints=["添加 servers 配置监听端口"],
        )

    server = servers[0]
    if not isinstance(server, dict):
        return CheckResult(ok=False, error="servers[0] 格式错误", hints=[])

    port = server.get("port", {})
    if not isinstance(port, dict):
        return CheckResult(ok=False, error="servers[0] 缺少 port", hints=[])

    if not port.get("number"):
        return CheckResult(
            ok=False,
            error="servers[0].port 缺少 number",
            hints=["设置端口号，如 80 或 443"],
        )

    if not port.get("protocol"):
        return CheckResult(
            ok=False,
            error="servers[0].port 缺少 protocol",
            hints=["设置协议: HTTP / HTTPS / GRPC / TCP"],
        )

    # 检查 hosts
    hosts = server.get("hosts")
    if not isinstance(hosts, list) or not hosts:
        return CheckResult(
            ok=False,
            error="servers[0] 缺少 hosts",
            hints=["设置允许的主机名，如 ['*'] 或 ['example.com']"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Gateway 是 Istio 的入口网关，控制外部流量如何进入 Mesh 🚪"],
    )


LEVEL_Q27_4 = Level(
    id="Q27.4",
    chapter="ch27",
    title="Gateway - 网关配置",
    description="""
# Gateway - 网关配置 🚪

**Gateway** 配置 Istio 的入口/出口网关，控制外部流量如何进入 Service Mesh。

## 任务

创建一个 Istio Gateway：
- `kind: Gateway`，`apiVersion: networking.istio.io/v1`
- 名称 `my-gateway`
- selector: `{istio: ingressgateway}`（选择 Istio Ingress Gateway Pod）
- servers:
  - 端口 80, 协议 HTTP, name http
  - hosts: `["*"]`

## 提示

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
```
""",
    starter_yaml="""\
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
spec:
  # 添加 selector 和 servers
""",
    check_fn=_check_274_gateway,
    lesson=Lesson(
        concept="""\
## Istio Gateway

**Gateway** 配置 Service Mesh 边缘的负载均衡器，处理外部流量进入 Mesh 的入口。它类似于 K8s Ingress，但功能更强大。

### Gateway vs K8s Ingress

| 特性 | K8s Ingress | Istio Gateway |
|------|------------|---------------|
| 协议 | HTTP/HTTPS | HTTP/HTTPS/TCP/gRPC/TLS |
| 路由 | 简单路径路由 | L7 精细路由（配合 VS） |
| TLS | 支持 | 支持 + mTLS |
| 多网关 | 有限 | 灵活（Ingress/Egress） |
| 扩展 | Ingress Controller | Envoy 代理 |

### Gateway 工作流程

```
外部请求 → LoadBalancer → Istio Ingress Gateway Pod (Envoy)
         → Gateway (配置端口/主机)
         → VirtualService (路由规则)
         → 目标服务 Pod
```

### 入口网关 vs 出口网关

- **Ingress Gateway**：外部流量进入 Mesh
- **Egress Gateway**：Mesh 内部流量访问外部服务

### HTTPS 配置示例

```yaml
servers:
- port:
    number: 443
    name: https
    protocol: HTTPS
  hosts:
  - "example.com"
  tls:
    mode: SIMPLE
    credentialName: my-tls-cert  # K8s Secret 名
```
""",
        key_fields=[
            {"name": "spec.selector", "description": "选择 Gateway 代理 Pod（通常 istio: ingressgateway）", "required": True, "example": "{istio: ingressgateway}"},
            {"name": "spec.servers[].port.number", "description": "监听端口", "required": True, "example": "80"},
            {"name": "spec.servers[].port.protocol", "description": "协议: HTTP/HTTPS/TCP/GRPC", "required": True, "example": "HTTP"},
            {"name": "spec.servers[].hosts", "description": "允许的主机名列表", "required": True, "example": "[*]"},
            {"name": "spec.servers[].tls", "description": "TLS 配置（HTTPS 时需要）", "required": False, "example": "{mode: SIMPLE, credentialName: cert}"},
        ],
        diagram="""\
  Istio Gateway 流量入口

  外部用户
      │
      ▼
  ┌─────────────────────┐
  │   LoadBalancer       │
  │   (云负载均衡器)      │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────────────────────────┐
  │  Istio Ingress Gateway Pod (Envoy)      │
  │  ┌───────────────────────────────────┐  │
  │  │  Gateway (my-gateway)             │  │
  │  │  selector: {istio: ingressgateway}│  │
  │  │  servers:                         │  │
  │  │  - port: 80, protocol: HTTP       │  │
  │  │    hosts: ["*"]                   │  │
  │  └──────────────┬────────────────────┘  │
  └─────────────────┼───────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────┐
  │  VirtualService (路由规则)               │
  │  → 路由到内部服务                         │
  └─────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: networking.istio.io/v1       # Istio 网络 API
kind: Gateway                            # 资源类型
metadata:                                # 元数据
  name: my-gateway                       # Gateway 名称
spec:                                    # 规格
  selector:                              # 选择 Gateway 代理
    istio: ingressgateway                # Istio Ingress Gateway
  servers:                               # 监听服务器列表
  - port:                                # 端口配置
      number: 80                         # 端口号
      name: http                         # 端口名
      protocol: HTTP                     # 协议
    hosts:                               # 允许的主机
    - "*"                                # 允许所有主机
""",
        common_errors=[
            "selector 不匹配 Ingress Gateway Pod 的标签",
            "protocol 写成 http 小写（应为大写 HTTP）",
            "hosts 为空（至少需要 '*' 或具体域名）",
            "Gateway 和 VirtualService 没有关联（VS 需要指定 gateways 字段）",
        ],
        tips=[
            "Gateway 通常配合 VirtualService 使用：VS 中 spec.gateways 引用 Gateway 名称",
            "用 kubectl get gw 查看所有 Gateway",
            "HTTPS 需要在 servers 中配置 tls 字段和 K8s TLS Secret",
        ],
    ),
)


# ==================== Q27.5 集群实战 - 完整 Service Mesh 配置 ====================

def _check_275_full_mesh(user_yaml: str) -> CheckResult:
    """Q27.5 完整 Service Mesh 配置"""
    try:
        state = ClusterState()
        state = preset_state(state, _ISTIO_CRD_YAML)
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 收集所有 Istio CR
    cr_kinds = {}
    for cr in state.customresources.values():
        if isinstance(cr, dict):
            kind = cr.get("kind", "")
            cr_kinds.setdefault(kind, []).append(cr)

    # 检查 Gateway
    if "Gateway" not in cr_kinds:
        return CheckResult(
            ok=False,
            error="缺少 Gateway（需要配置入口网关）",
            hints=["添加 kind: Gateway 配置外部流量入口"],
        )

    # 检查 VirtualService
    if "VirtualService" not in cr_kinds:
        return CheckResult(
            ok=False,
            error="缺少 VirtualService（需要定义路由规则）",
            hints=["添加 kind: VirtualService 配置流量路由"],
        )

    vs = cr_kinds["VirtualService"][0]
    vs_spec = vs.get("spec", {})

    # 检查 VirtualService 是否关联了 Gateway
    vs_gateways = vs_spec.get("gateways")
    if not isinstance(vs_gateways, list) or not vs_gateways:
        return CheckResult(
            ok=False,
            error="VirtualService 缺少 spec.gateways（需要关联 Gateway）",
            hints=["在 VirtualService 中添加 gateways 字段引用 Gateway 名称"],
        )

    # 检查 DestinationRule
    if "DestinationRule" not in cr_kinds:
        return CheckResult(
            ok=False,
            error="缺少 DestinationRule（需要定义服务版本和策略）",
            hints=["添加 kind: DestinationRule 定义版本子集"],
        )

    # 检查 DestinationRule 的 subsets 与 VirtualService 的 subset 是否匹配
    dr = cr_kinds["DestinationRule"][0]
    dr_spec = dr.get("spec", {})
    dr_subsets = set()
    for s in dr_spec.get("subsets", []):
        if isinstance(s, dict) and s.get("name"):
            dr_subsets.add(s["name"])

    # 提取 VirtualService 中引用的 subsets
    vs_subsets = set()
    for http_route in vs_spec.get("http", []):
        if not isinstance(http_route, dict):
            continue
        for r in http_route.get("route", []):
            if not isinstance(r, dict):
                continue
            dest = r.get("destination", {})
            if isinstance(dest, dict) and dest.get("subset"):
                vs_subsets.add(dest["subset"])

    # 检查是否所有 VS 引用的 subset 都在 DR 中定义
    missing = vs_subsets - dr_subsets
    if missing:
        return CheckResult(
            ok=False,
            error=f"VirtualService 引用的 subset {missing} 未在 DestinationRule 中定义",
            hints=[f"在 DestinationRule 的 subsets 中定义: {missing}"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["完整 Service Mesh = Gateway + VirtualService + DestinationRule 🎉"],
    )


LEVEL_Q27_5 = Level(
    id="Q27.5",
    chapter="ch27",
    title="集群实战 - 完整 Service Mesh 配置",
    description="""
# 集群实战 - 完整 Service Mesh 配置 🎉

综合运用 Gateway、VirtualService 和 DestinationRule 构建完整的 Service Mesh 流量管理。

## 任务

创建完整的 Service Mesh 配置（多文档 YAML）：
1. **Gateway**（名称 `mesh-gateway`）
   - selector: `{istio: ingressgateway}`
   - servers: 端口 80, HTTP, hosts `["*"]`
2. **VirtualService**（名称 `productpage-vs`）
   - gateways: `["mesh-gateway"]`
   - hosts: `["productpage"]`
   - http 路由：100% 流量到 `productpage` 服务的 `v1` subset
3. **DestinationRule**（名称 `productpage-dr`）
   - host: `productpage`
   - subsets: name `v1`, labels `{version: v1}`

## 提示

```yaml
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: mesh-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: productpage-vs
spec:
  gateways:
  - mesh-gateway
  hosts:
  - productpage
  http:
  - route:
    - destination:
        host: productpage
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: productpage-dr
spec:
  host: productpage
  subsets:
  - name: v1
    labels:
      version: v1
```
""",
    starter_yaml="""\
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: mesh-gateway
spec:
  # 添加 selector 和 servers
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: productpage-vs
spec:
  # 添加 gateways, hosts 和 http 路由
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: productpage-dr
spec:
  # 添加 host 和 subsets
""",
    check_fn=_check_275_full_mesh,
    lesson=Lesson(
        concept="""\
## 完整 Service Mesh 配置

一个生产级 Service Mesh 流量管理配置通常包含三大组件：

### 三件套关系

```
Gateway          → 配置入口（端口、主机、TLS）
VirtualService   → 路由规则（去哪个服务、哪个版本）
DestinationRule  → 服务策略（版本定义、负载均衡、熔断）
```

### 请求流转全过程

```
1. 外部请求到达 LoadBalancer
2. LoadBalancer 转发到 Istio Ingress Gateway Pod (Envoy)
3. Gateway 配置确定监听端口和主机
4. VirtualService 路由规则匹配请求
5. DestinationRule 选择具体版本子集
6. 流量到达目标 Pod 的 Envoy Sidecar
7. Sidecar 转发给应用容器
```

### 灰度发布示例

```yaml
# VirtualService: 90% v1, 10% v2
http:
- route:
  - destination: {host: app, subset: v1}
    weight: 90
  - destination: {host: app, subset: v2}
    weight: 10

# DestinationRule: 定义 v1/v2
subsets:
- name: v1
  labels: {version: v1}
- name: v2
  labels: {version: v2}
```

### 生产环境最佳实践

1. Gateway 统一管理入口
2. 每个 Service 一个 VirtualService
3. 版本发布通过 DestinationRule subsets 管理
4. 配置熔断和异常驱逐
5. 启用 mTLS 加密
""",
        key_fields=[
            {"name": "Gateway", "description": "入口网关配置", "required": True, "example": "selector + servers"},
            {"name": "VirtualService.gateways", "description": "关联的 Gateway 名称", "required": True, "example": "[mesh-gateway]"},
            {"name": "VirtualService.http[].route[].destination.subset", "description": "引用 DestinationRule 的 subset", "required": True, "example": "v1"},
            {"name": "DestinationRule.subsets[].name", "description": "版本子集名称", "required": True, "example": "v1"},
        ],
        diagram="""\
  完整 Service Mesh 流量管理

  外部请求
      │
      ▼
  ┌────────────────────────────────────────────┐
  │  Gateway (mesh-gateway)                    │
  │  selector: {istio: ingressgateway}         │
  │  port: 80, HTTP, hosts: ["*"]             │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────┐
  │  VirtualService (productpage-vs)           │
  │  gateways: [mesh-gateway]                 │
  │  hosts: [productpage]                      │
  │  http:                                     │
  │  - route:                                  │
  │    - destination: {host: productpage,      │
  │        subset: v1}  ◄── 引用 subset        │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────┐
  │  DestinationRule (productpage-dr)          │
  │  host: productpage                         │
  │  subsets:                                  │
  │  - name: v1  ◄── 定义 subset               │
  │    labels: {version: v1}                  │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  ┌─────────────────┐
  │  Pod (v1)       │
  │  Envoy + App    │
  └─────────────────┘
""",
        example_yaml="""\
---                                          # 文档分隔
apiVersion: networking.istio.io/v1           # Istio 网络 API
kind: Gateway                                # 资源类型: Gateway
metadata:                                    # 元数据
  name: mesh-gateway                         # Gateway 名称
spec:                                        # 规格
  selector:                                  # 选择代理 Pod
    istio: ingressgateway                    # Ingress Gateway
  servers:                                   # 监听配置
  - port:                                    # 端口
      number: 80                             # 端口号
      name: http                             # 端口名
      protocol: HTTP                         # 协议
    hosts:                                   # 允许主机
    - "*"                                    # 所有主机
---                                          # 文档分隔
apiVersion: networking.istio.io/v1           # Istio 网络 API
kind: VirtualService                         # 资源类型: VS
metadata:                                    # 元数据
  name: productpage-vs                       # VS 名称
spec:                                        # 规格
  gateways:                                  # 关联 Gateway
  - mesh-gateway                             # Gateway 名称
  hosts:                                     # 目标服务
  - productpage                              # 服务名
  http:                                      # HTTP 路由
  - route:                                   # 路由目标
    - destination:                           # 目标服务
        host: productpage                    # 服务名
        subset: v1                           # 版本子集
---                                          # 文档分隔
apiVersion: networking.istio.io/v1           # Istio 网络 API
kind: DestinationRule                        # 资源类型: DR
metadata:                                    # 元数据
  name: productpage-dr                       # DR 名称
spec:                                        # 规格
  host: productpage                          # 目标服务
  subsets:                                   # 版本子集
  - name: v1                                 # 子集名
    labels:                                  # 标签选择器
      version: v1                            # 匹配 version=v1
""",
        common_errors=[
            "VirtualService 的 gateways 字段不匹配 Gateway 名称",
            "VirtualService 引用的 subset 在 DestinationRule 中未定义",
            "Gateway selector 不匹配 Ingress Gateway Pod 标签",
            "三个资源分散在不同文档但忘记用 --- 分隔",
        ],
        tips=[
            "生产环境建议每个微服务一套 VS+DR，统一 Gateway 管理入口",
            "灰度发布只需修改 VirtualService 的 weight 即可",
            "用 istioctl analyze 检查 Istio 配置的一致性",
        ],
    ),
)


# ==================== 章节导出 ====================

CHAPTER_27_LEVELS = [
    LEVEL_Q27_1,
    LEVEL_Q27_2,
    LEVEL_Q27_3,
    LEVEL_Q27_4,
    LEVEL_Q27_5,
]
