"""Chapter 11: Ingress（入口路由）（5 关）

Q11.1 创建 Ingress（单路由）
Q11.2 Ingress 多域名
Q11.3 Ingress 路径路由
Q11.4 Ingress TLS
Q11.5 集群实战 - 部署 Nginx Ingress
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q11.1 创建 Ingress（单路由） ====================

def _check_111_create_ingress(user_yaml: str) -> CheckResult:
    """Q11.1 创建 Ingress 将 example.com 路由到 web-svc:80"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.ingresses:
        return CheckResult(
            ok=False,
            error="没有创建任何 Ingress",
            hints=["你需要 apply 一个 kind: Ingress 的 YAML"],
        )

    ing_name = next(iter(state.ingresses))
    ing = state.ingresses[ing_name]
    spec = ing.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Ingress 缺少 spec", hints=[])

    # 验证 rules 非空
    rules = spec.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Ingress 缺少 spec.rules（必须是非空列表）",
            hints=["在 spec.rules 下定义路由规则"],
        )

    # 检查 rule 有 host
    rule = rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    host = rule.get("host", "")
    if not host:
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 host 字段",
            hints=["设置 host，如 example.com"],
        )

    # 检查有 backend 配置
    http = rule.get("http", {})
    if not isinstance(http, dict):
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 http 配置",
            hints=["添加 http.paths 配置路由"],
        )

    paths = http.get("paths", [])
    if not isinstance(paths, list) or not paths:
        return CheckResult(
            ok=False,
            error="rules[0].http.paths 为空",
            hints=["添加 paths 配置，指向 Service"],
        )

    # 检查 backend 指向 web-svc:80
    backend = paths[0].get("backend", {})
    if not isinstance(backend, dict):
        return CheckResult(ok=False, error="paths[0].backend 格式错误", hints=[])

    service_name = backend.get("service", {}).get("name", "")
    if not service_name:
        # 兼容旧版格式
        service_name = backend.get("serviceName", "")

    if service_name != "web-svc":
        return CheckResult(
            ok=False,
            error=f"backend 应指向 web-svc，实际为 '{service_name}'",
            hints=["设置 backend.service.name: web-svc"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Ingress 创建成功！example.com 的流量将路由到 web-svc 🌐"],
    )


LEVEL_Q11_1 = Level(
    id="Q11.1",
    chapter="ch11",
    title="创建 Ingress（单路由）",
    description="""
# 创建 Ingress（单路由）🌐

**Ingress** 是 Kubernetes 的七层（HTTP/HTTPS）负载均衡器，根据域名和路径将外部流量路由到集群内的 Service。

## 任务

创建一个 Ingress，将 `example.com` 的流量路由到 `web-svc:80`：
- `kind: Ingress`
- `apiVersion: networking.k8s.io/v1`
- `spec.rules[0].host` 为 `example.com`
- backend 指向 `web-svc`，端口 `80`

## 提示

```yaml
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  # rules: 定义路由规则
""",
    check_fn=_check_111_create_ingress,
    lesson=Lesson(
        concept="""\
## 什么是 Ingress？

**Ingress** 是 Kubernetes 的七层（HTTP/HTTPS）路由控制器。它根据域名（host）和 URL 路径（path）将外部流量路由到集群内的 Service。

### Ingress vs Service (NodePort/LoadBalancer)

| 特性 | Ingress | NodePort | LoadBalancer |
|------|---------|----------|-------------|
| 层级 | 七层 (HTTP/HTTPS) | 四层 (TCP) | 四层 (TCP) |
| 路由 | 域名 + 路径 | 端口 | 端口 |
| TLS | 支持 | 手动配置 | 手动配置 |
| 费用 | 一个 LB 多个域名 | 免费但端口有限 | 每个 LB 收费 |
| 适用 | Web 应用 | 简单暴露 | 需要外部 LB |

### Ingress 架构

```
外部用户 ──> Ingress Controller (如 Nginx) ──> Service ──> Pod
                │
                ├── example.com → web-svc:80
                ├── api.example.com → api-svc:8080
                └── example.com/static → static-svc:80
```

### Ingress Controller

Ingress 资源本身只是路由规则，需要 **Ingress Controller** 来实际执行路由。常见的 Ingress Controller：

1. **NGINX Ingress Controller** - 最流行，基于 Nginx
2. **Traefik** - 现代化，支持自动服务发现
3. **HAProxy Ingress** - 高性能
4. **AWS ALB Ingress** - 使用 AWS ALB

### 规则匹配

Ingress 按以下优先级匹配：
1. 精确路径匹配（`Exact`）
2. 最长前缀匹配（`Prefix`）
3. 默认后端（无 host 匹配时）
""",
        key_fields=[
            {"name": "spec.rules", "description": "路由规则列表", "required": True, "example": "[{host: example.com, http: {paths: [...]}}]"},
            {"name": "spec.rules[].host", "description": "匹配的域名", "required": True, "example": "example.com"},
            {"name": "spec.rules[].http.paths[].path", "description": "URL 路径", "required": True, "example": "/"},
            {"name": "spec.rules[].http.paths[].backend.service.name", "description": "后端 Service 名称", "required": True, "example": "web-svc"},
            {"name": "spec.rules[].http.paths[].pathType", "description": "路径匹配类型: Prefix/Exact", "required": True, "example": "Prefix"},
        ],
        diagram="""\
  Ingress 路由模型

  外部用户 (HTTP 请求)
       │
       │ Host: example.com
       │ Path: /
       ▼
  ┌──────────────────────────────┐
  │  Ingress (web-ingress)        │
  │  rules:                       │
  │  - host: example.com          │
  │    http:                      │
  │      paths:                   │
  │      - path: /                │
  │        backend:               │
  │          service:             │
  │            name: web-svc      │
  │            port: 80           │
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────┐
  │  Service (web-svc)    │
  │  port: 80             │
  └──────────┬───────────┘
             │
     ┌───────┼───────┐
     ▼       ▼       ▼
   ┌────┐ ┌────┐ ┌────┐
   │Pod │ │Pod │ │Pod │
   │web │ │web │ │web │
   └────┘ └────┘ └────┘
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型: Ingress
metadata:                                   # 元数据
  name: web-ingress                         # Ingress 名称
  annotations:                              # 注解（可选）
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:                                       # 规格定义
  rules:                                    # 路由规则
  - host: example.com                       # 匹配域名
    http:                                   # HTTP 路由
      paths:                                # 路径列表
      - path: /                             # 匹配路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端配置
          service:                          # 指向 Service
            name: web-svc                   # Service 名称
            port:                           # 端口
              number: 80                    # 端口号
""",
        common_errors=[
            "apiVersion 写成 extensions/v1beta1（已废弃，应用 networking.k8s.io/v1）",
            "忘记写 pathType（networking.k8s.io/v1 必填）",
            "backend 格式用旧版（serviceName/servicePort 而非 service.name/service.port）",
            "没有安装 Ingress Controller，Ingress 规则不生效",
        ],
        tips=[
            "Ingress 需要安装 Ingress Controller 才能工作",
            "用 kubectl get ingress 查看路由规则和分配的地址",
            "用 kubectl describe ingress <name> 查看详细路由信息",
        ],
    ),
)


# ==================== Q11.2 Ingress 多域名 ====================

def _check_112_multi_host(user_yaml: str) -> CheckResult:
    """Q11.2 创建 Ingress 支持多个 host"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.ingresses:
        return CheckResult(
            ok=False,
            error="没有创建任何 Ingress",
            hints=["你需要 apply 一个 kind: Ingress 的 YAML"],
        )

    ing_name = next(iter(state.ingresses))
    ing = state.ingresses[ing_name]
    spec = ing.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Ingress 缺少 spec", hints=[])

    # 验证 rules 至少有 2 个
    rules = spec.get("rules")
    if not isinstance(rules, list):
        return CheckResult(
            ok=False,
            error="Ingress 缺少 spec.rules（必须是列表）",
            hints=["在 spec.rules 下定义多个路由规则"],
        )

    if len(rules) < 2:
        return CheckResult(
            ok=False,
            error=f"多域名 Ingress 应至少有 2 个 rule，实际 {len(rules)} 个",
            hints=["在 rules 下添加多个 host 规则"],
        )

    # 验证每个 rule 有 host
    hosts = []
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return CheckResult(ok=False, error=f"rules[{i}] 格式错误", hints=[])
        host = rule.get("host", "")
        if not host:
            return CheckResult(
                ok=False,
                error=f"rules[{i}] 缺少 host",
                hints=["每个 rule 都需要设置 host"],
            )
        hosts.append(host)

    # 验证 host 不重复
    if len(set(hosts)) != len(hosts):
        return CheckResult(
            ok=False,
            error=f"rules 中的 host 有重复: {hosts}",
            hints=["每个 rule 的 host 应该不同"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["多域名 Ingress 创建成功！不同域名路由到不同 Service 🌐"],
    )


LEVEL_Q11_2 = Level(
    id="Q11.2",
    chapter="ch11",
    title="Ingress 多域名",
    description="""
# Ingress 多域名 🌐

一个 Ingress 可以配置多个 host 规则，将不同域名的流量路由到不同的后端 Service。

## 任务

创建一个 Ingress，支持至少 2 个域名：
- `example.com` -> `web-svc:80`
- `api.example.com` -> `api-svc:8080`

## 提示

```yaml
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
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
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-host-ingress
spec:
  # rules: 添加至少 2 个 host 规则
""",
    check_fn=_check_112_multi_host,
    lesson=Lesson(
        concept="""\
## Ingress 多域名路由

Ingress 的强大之处在于一个资源可以管理多个域名的路由规则。这比每个域名创建一个 LoadBalancer Service 成本低得多。

### 多域名路由架构

```
                    ┌──────────────────────┐
   example.com ────►│                      │──► web-svc:80
                    │  Ingress Controller  │
  api.example.com ─►│  (如 Nginx)          │──► api-svc:8080
                    │                      │
  app.example.com ─►│                      │──► app-svc:3000
                    └──────────────────────┘
```

### 基于 host 的虚拟主机

Ingress 实现了"基于名称的虚拟主机"（Name-based Virtual Hosting）：
- 多个域名共用同一个 IP 地址
- Ingress Controller 通过 HTTP `Host` 头区分请求
- 无需为每个域名分配独立 IP

### 默认后端

当请求的 host 不匹配任何规则时，Ingress 使用默认后端（default backend）：
```yaml
spec:
  defaultBackend:
    service:
      name: default-svc
      port:
        number: 80
```

### Wildcard host

Ingress 支持通配符 host：
```yaml
rules:
- host: "*.example.com"   # 匹配所有 *.example.com 子域名
```

注意：通配符只匹配一级子域名，`foo.bar.example.com` 不会被 `*.example.com` 匹配。
""",
        key_fields=[
            {"name": "spec.rules", "description": "路由规则列表，可包含多个 host", "required": True, "example": "[{host: example.com, ...}, {host: api.example.com, ...}]"},
            {"name": "spec.rules[].host", "description": "匹配的域名", "required": True, "example": "example.com"},
            {"name": "spec.defaultBackend", "description": "默认后端（无匹配时使用）", "required": False, "example": "{service: {name: default-svc}}"},
            {"name": "spec.rules[].http.paths[].backend", "description": "后端 Service 配置", "required": True, "example": "{service: {name: web-svc, port: {number: 80}}}"},
        ],
        diagram="""\
  Ingress 多域名路由

  用户请求 (Host 头区分)
       │
       ├── Host: example.com ─────────────┐
       ├── Host: api.example.com ─────────┤
       └── Host: app.example.com ─────────┤
                                         │
                                         ▼
                    ┌──────────────────────────────┐
                    │  Ingress (multi-host)         │
                    │  rules:                       │
                    │  - host: example.com          │
                    │    → web-svc:80               │
                    │  - host: api.example.com      │
                    │    → api-svc:8080             │
                    │  - host: app.example.com      │
                    │    → app-svc:3000             │
                    └──────┬───────┬───────┬────────┘
                           │       │       │
                           ▼       ▼       ▼
                        ┌────┐  ┌────┐  ┌────┐
                        │web │  │api │  │app │
                        │svc │  │svc │  │svc │
                        └────┘  └────┘  └────┘

  所有域名共用一个 IP (基于 Host 头的虚拟主机)
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型
metadata:                                   # 元数据
  name: multi-host-ingress                  # 名称
spec:                                       # 规格
  rules:                                    # 路由规则（多个）
  - host: example.com                       # 域名 1
    http:                                   # HTTP 路由
      paths:
      - path: /                             # 匹配所有路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: web-svc                   # Web 服务
            port:
              number: 80
  - host: api.example.com                   # 域名 2
    http:                                   # HTTP 路由
      paths:
      - path: /                             # 匹配所有路径
        pathType: Prefix
        backend:                            # 后端
          service:
            name: api-svc                   # API 服务
            port:
              number: 8080
""",
        common_errors=[
            "多个 rule 使用了相同的 host（会冲突）",
            "忘记为每个 rule 都设置 backend",
            "DNS 未配置域名解析到 Ingress Controller IP",
            "通配符 host 匹配范围理解错误（*.example.com 不匹配 a.b.example.com）",
        ],
        tips=[
            "一个 Ingress 可以管理无限多个域名路由",
            "用 kubectl get ingress 查看所有路由规则",
            "在本地测试可通过 curl -H 'Host: api.example.com' <ingress-ip>",
        ],
    ),
)


# ==================== Q11.3 Ingress 路径路由 ====================

def _check_113_path_routing(user_yaml: str) -> CheckResult:
    """Q11.3 创建 Ingress 按路径路由"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.ingresses:
        return CheckResult(
            ok=False,
            error="没有创建任何 Ingress",
            hints=["你需要 apply 一个 kind: Ingress 的 YAML"],
        )

    ing_name = next(iter(state.ingresses))
    ing = state.ingresses[ing_name]
    spec = ing.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Ingress 缺少 spec", hints=[])

    rules = spec.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Ingress 缺少 spec.rules",
            hints=["在 spec.rules 下定义路由规则"],
        )

    rule = rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    http = rule.get("http", {})
    if not isinstance(http, dict):
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 http 配置",
            hints=["添加 http.paths 定义路径路由"],
        )

    paths = http.get("paths", [])
    if not isinstance(paths, list) or len(paths) < 2:
        return CheckResult(
            ok=False,
            error=f"路径路由应至少有 2 个 path，实际 {len(paths) if isinstance(paths, list) else 0} 个",
            hints=["添加 /api 和 /web 两个路径，分别指向不同 Service"],
        )

    # 收集所有 path 和 backend
    path_backends = {}
    for i, p in enumerate(paths):
        if not isinstance(p, dict):
            return CheckResult(ok=False, error=f"paths[{i}] 格式错误", hints=[])
        path = p.get("path", "")
        backend = p.get("backend", {})
        svc_name = ""
        if isinstance(backend, dict):
            svc_name = backend.get("service", {}).get("name", "") or backend.get("serviceName", "")
        path_backends[path] = svc_name

    # 检查有 /api 和 /web 路径
    has_api = any("/api" in p for p in path_backends.keys())
    has_web = any("/web" in p for p in path_backends.keys())

    if not has_api or not has_web:
        missing = []
        if not has_api:
            missing.append("/api")
        if not has_web:
            missing.append("/web")
        return CheckResult(
            ok=False,
            error=f"缺少路径: {missing}，当前路径: {list(path_backends.keys())}",
            hints=["添加 /api -> api-svc 和 /web -> web-svc 的路径路由"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["路径路由配置成功！/api 和 /web 分别路由到不同 Service 🔀"],
    )


LEVEL_Q11_3 = Level(
    id="Q11.3",
    chapter="ch11",
    title="Ingress 路径路由",
    description="""
# Ingress 路径路由 🔀

除了按域名路由，Ingress 还可以按 URL 路径将请求路由到不同的后端 Service。

## 任务

创建一个 Ingress，在同一域名下按路径路由：
- `/api` -> `api-svc:8080`
- `/web` -> `web-svc:80`

## 提示

```yaml
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
```
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing-ingress
spec:
  rules:
  - host: example.com
    http:
      # paths: 添加 /api 和 /web 两个路径
""",
    check_fn=_check_113_path_routing,
    lesson=Lesson(
        concept="""\
## Ingress 路径路由

Ingress 不仅支持按域名路由，还支持在同一个域名下按 URL 路径路由到不同的后端 Service。这是微服务架构中常用的路由模式。

### pathType 匹配类型

| 类型 | 说明 | 示例 |
|------|------|------|
| Prefix | 前缀匹配 | `/api` 匹配 `/api`, `/api/v1`, `/api/users` |
| Exact | 精确匹配 | `/api` 只匹配 `/api`，不匹配 `/api/v1` |
| ImplementationSpecific | 由 Ingress Controller 决定 | 取决于实现 |

### 路径匹配规则

Prefix 匹配遵循以下规则：
- `/api` 匹配 `/api`, `/api/`, `/api/v1`, `/api/v1/users`
- `/api` **不**匹配 `/apis`, `/apiv1`
- `/` 匹配所有路径（兜底）
- 最长前缀优先匹配

### 微服务路由模式

```
example.com/
├── /api/*     → api-svc      (API 服务)
├── /web/*     → web-svc      (Web 前端)
├── /static/*  → static-svc   (静态资源)
└── /admin/*   → admin-svc    (管理后台)
```

### rewrite-target 注解

有时后端服务不期望路径前缀（如 `/api`），可以用 rewrite-target 去掉前缀：

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
  - http:
      paths:
      - path: /api(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: api-svc
```

这样 `/api/v1/users` 会被转发为 `/v1/users`。
""",
        key_fields=[
            {"name": "spec.rules[].http.paths", "description": "路径列表，每个路径可指向不同后端", "required": True, "example": "[{path: /api, ...}, {path: /web, ...}]"},
            {"name": "spec.rules[].http.paths[].path", "description": "URL 路径", "required": True, "example": "/api"},
            {"name": "spec.rules[].http.paths[].pathType", "description": "匹配类型: Prefix/Exact", "required": True, "example": "Prefix"},
            {"name": "spec.rules[].http.paths[].backend.service.name", "description": "后端 Service 名称", "required": True, "example": "api-svc"},
        ],
        diagram="""\
  Ingress 路径路由

  用户请求: http://example.com/api/users
                    │
                    │ Host: example.com
                    │ Path: /api/users
                    ▼
  ┌──────────────────────────────────────┐
  │  Ingress Controller                   │
  │                                       │
  │  Path 匹配 (最长前缀优先):            │
  │  ├── /api/*   → api-svc:8080   ✅匹配 │
  │  ├── /web/*   → web-svc:80           │
  │  └── /*       → default-svc          │
  └──────────────────┬───────────────────┘
                     │
                     ▼
  ┌──────────────────────┐
  │  Service (api-svc)    │
  │  port: 8080           │
  └──────────┬───────────┘
             │
     ┌───────┼───────┐
     ▼       ▼       ▼
   ┌────┐ ┌────┐ ┌────┐
   │api │ │api │ │api │
   │pod │ │pod │ │pod │
   └────┘ └────┘ └────┘

  路径路由示例:
  example.com/api  → api-svc
  example.com/web  → web-svc
  example.com/     → default
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型
metadata:                                   # 元数据
  name: path-routing-ingress                # 名称
  annotations:                              # 注解
    nginx.ingress.kubernetes.io/rewrite-target: /  # 重写目标
spec:                                       # 规格
  rules:                                    # 路由规则
  - host: example.com                       # 域名
    http:                                   # HTTP 路由
      paths:                                # 路径列表
      - path: /api                          # API 路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: api-svc                   # API 服务
            port:
              number: 8080
      - path: /web                          # Web 路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: web-svc                   # Web 服务
            port:
              number: 80
""",
        common_errors=[
            "忘记写 pathType（networking.k8s.io/v1 必填）",
            "路径顺序错误（应该最长前缀在前，避免 / 被先匹配）",
            "后端服务不期望路径前缀，但未配置 rewrite-target",
            "把 /api 和 /web 写在了不同的 rule 中（应在同一 rule 的 http.paths 下）",
        ],
        tips=[
            "路径匹配遵循最长前缀优先原则",
            "用 nginx.ingress.kubernetes.io/rewrite-target 去除路径前缀",
            "用 curl -H 'Host: example.com' http://<ingress-ip>/api 测试路由",
        ],
    ),
)


# ==================== Q11.4 Ingress TLS ====================

def _check_114_tls(user_yaml: str) -> CheckResult:
    """Q11.4 创建带 TLS 的 Ingress"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.ingresses:
        return CheckResult(
            ok=False,
            error="没有创建任何 Ingress",
            hints=["你需要 apply 一个 kind: Ingress 的 YAML"],
        )

    ing_name = next(iter(state.ingresses))
    ing = state.ingresses[ing_name]
    spec = ing.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Ingress 缺少 spec", hints=[])

    # 验证 TLS 存在
    tls = spec.get("tls")
    if not isinstance(tls, list) or not tls:
        return CheckResult(
            ok=False,
            error="Ingress 缺少 spec.tls（必须是非空列表）",
            hints=["添加 spec.tls 配置 TLS 证书"],
        )

    # 验证 tls 条目有 hosts 或 secretName
    tls_entry = tls[0]
    if not isinstance(tls_entry, dict):
        return CheckResult(ok=False, error="tls[0] 格式错误", hints=[])

    has_hosts = "hosts" in tls_entry
    has_secret = "secretName" in tls_entry

    if not has_secret:
        return CheckResult(
            ok=False,
            error="tls[0] 缺少 secretName（TLS 证书引用的 Secret）",
            hints=["设置 tls[0].secretName 指向包含 TLS 证书的 Secret"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["TLS Ingress 创建成功！支持 HTTPS 加密访问 🔒"],
    )


LEVEL_Q11_4 = Level(
    id="Q11.4",
    chapter="ch11",
    title="Ingress TLS",
    description="""
# Ingress TLS 🔒

Ingress 支持 TLS/HTTPS 加密，通过引用包含 TLS 证书的 Secret 来实现 HTTPS 访问。

## 任务

创建一个带 TLS 的 Ingress：
- `spec.tls` 配置 TLS 证书
- `tls[0].secretName` 引用一个包含证书的 Secret
- `tls[0].hosts` 列出使用该证书的域名

## 提示

```yaml
spec:
  tls:
  - hosts:
    - example.com
    secretName: tls-secret
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
```

> 注意：tls-secret 应是一个 `kubernetes.io/tls` 类型的 Secret，包含 `tls.crt` 和 `tls.key`。
""",
    starter_yaml="""\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  # tls: 配置 TLS 证书
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-svc
            port:
              number: 80
""",
    check_fn=_check_114_tls,
    lesson=Lesson(
        concept="""\
## Ingress TLS 加密

Ingress 支持终止 TLS（TLS Termination），即 Ingress Controller 负责 HTTPS 解密，后端 Service 收到的是明文 HTTP。

### TLS 终止模式

```
客户端 ──HTTPS──> Ingress Controller ──HTTP──> Service ──> Pod
         加密              解密               明文
```

### TLS Secret 格式

Ingress 引用的 Secret 必须是 `kubernetes.io/tls` 类型，包含两个键：
- `tls.crt` - 证书（PEM 格式）
- `tls.key` - 私钥（PEM 格式）

创建 TLS Secret：
```bash
kubectl create secret tls tls-secret \
  --cert=certificate.crt \
  --key=private.key
```

### 多域名 TLS

一个 Ingress 可以配置多个 TLS 条目，每个对应不同域名的证书：

```yaml
tls:
- hosts: [example.com]
  secretName: example-tls
- hosts: [api.example.com]
  secretName: api-tls
```

### HTTP 自动重定向

配置 TLS 后，通常希望 HTTP 自动重定向到 HTTPS：

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
```

### TLS Passthrough

如果需要端到端加密（不在 Ingress 终止 TLS），可以使用 TLS Passthrough：
- 流量直接透传到后端 Pod
- Ingress 不解密，仅根据 SNI 路由
- 需要 Ingress Controller 支持（如 nginx 的 ssl-passthrough）
""",
        key_fields=[
            {"name": "spec.tls", "description": "TLS 配置列表", "required": True, "example": "[{hosts: [example.com], secretName: tls-secret}]"},
            {"name": "spec.tls[].hosts", "description": "使用该证书的域名列表", "required": True, "example": "[example.com]"},
            {"name": "spec.tls[].secretName", "description": "包含 TLS 证书的 Secret 名称", "required": True, "example": "tls-secret"},
            {"name": "metadata.annotations", "description": "TLS 相关注解（如 ssl-redirect）", "required": False, "example": "{nginx.ingress.kubernetes.io/ssl-redirect: true}"},
        ],
        diagram="""\
  Ingress TLS 终止模型

  客户端
    │
    │ HTTPS (加密)
    │ Host: example.com
    ▼
  ┌──────────────────────────────────────┐
  │  Ingress Controller                   │
  │                                       │
  │  TLS 配置:                            │
  │  spec.tls:                            │
  │  - hosts: [example.com]               │
  │    secretName: tls-secret             │
  │                                       │
  │  ┌─────────────────────────────────┐  │
  │  │ TLS 终止 (解密 HTTPS)           │  │
  │  │ 证书来自 Secret: tls-secret     │  │
  │  └─────────────────────────────────┘  │
  └──────────────────┬───────────────────┘
                     │
                     │ HTTP (明文)
                     ▼
  ┌──────────────────────┐
  │  Service (web-svc)    │
  │  port: 80             │
  └──────────────────────┘

  流程: HTTPS → Ingress 解密 → HTTP → Service → Pod
""",
        example_yaml="""\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型
metadata:                                   # 元数据
  name: tls-ingress                         # 名称
  annotations:                              # 注解
    nginx.ingress.kubernetes.io/ssl-redirect: "true"  # HTTP 重定向到 HTTPS
spec:                                       # 规格
  tls:                                      # ← TLS 配置
  - hosts:                                  # 使用该证书的域名
    - example.com                           # 域名
    secretName: tls-secret                  # TLS 证书 Secret
  rules:                                    # 路由规则
  - host: example.com                       # 域名
    http:                                   # HTTP 路由
      paths:
      - path: /                             # 路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: web-svc                   # Service 名称
            port:
              number: 80
""",
        common_errors=[
            "Secret 类型不是 kubernetes.io/tls（需要 tls.crt 和 tls.key）",
            "tls.hosts 中的域名与 rules 中的 host 不匹配",
            "证书已过期或域名不匹配（浏览器报错）",
            "忘记创建 TLS Secret（只写了 Ingress 但没有对应的 Secret）",
        ],
        tips=[
            "用 kubectl create secret tls 命令快速创建 TLS Secret",
            "配置 ssl-redirect 注解让 HTTP 自动重定向到 HTTPS",
            "生产环境建议使用 cert-manager 自动管理证书",
        ],
    ),
)


# ==================== Q11.5 集群实战 - 部署 Nginx Ingress ====================

def _check_115_deploy_nginx_ingress(user_yaml: str) -> CheckResult:
    """Q11.5 集群实战 - 部署 Nginx Ingress"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查有 Ingress
    if not state.ingresses:
        return CheckResult(
            ok=False,
            error="没有创建任何 Ingress",
            hints=["你需要 apply 一个 kind: Ingress 的 YAML"],
        )

    ing_name = next(iter(state.ingresses))
    ing = state.ingresses[ing_name]
    spec = ing.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Ingress 缺少 spec", hints=[])

    # 检查 rules 存在
    rules = spec.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Ingress 缺少 spec.rules",
            hints=["在 spec.rules 下定义路由规则"],
        )

    # 检查至少有一个 rule 有 host 和 backend
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        host = rule.get("host", "")
        http = rule.get("http", {})
        if not isinstance(http, dict):
            continue
        paths = http.get("paths", [])
        if not isinstance(paths, list) or not paths:
            continue

        # 找到第一个有效的 backend
        backend = paths[0].get("backend", {})
        if isinstance(backend, dict):
            svc = backend.get("service", {})
            if isinstance(svc, dict) and svc.get("name"):
                return CheckResult(
                    ok=True, state=state,
                    hints=[
                        "YAML 校验通过！在真实集群上执行：",
                        "  kubectl apply -f <your-yaml>",
                        "  kubectl get ingress",
                        "  kubectl describe ingress <name>",
                        "  # 获取 Ingress IP 后用 curl 测试:",
                        f"  curl -H 'Host: {host}' http://<ingress-ip>",
                    ],
                )

    return CheckResult(
        ok=False,
        error="Ingress 的 rules 中缺少有效的 backend 配置",
        hints=["确保每个 rule 的 http.paths[].backend.service.name 已设置"],
    )


LEVEL_Q11_5 = Level(
    id="Q11.5",
    chapter="ch11",
    title="集群实战: 部署 Nginx Ingress",
    description="""
# 集群实战: 部署 Nginx Ingress 🏗️

来真实集群上部署完整的 Ingress 方案，体验从 Service 到 Ingress 的完整流量路由！

## 任务

1. 创建一个 Deployment + Service
2. 创建 Ingress 将域名路由到 Service
3. 通过 Ingress IP 访问应用

## 要求

用多文档 YAML 创建：
- `kind: Deployment` + `kind: Service`（如 nginx:1.25）
- `kind: Ingress`，host 路由到 Service

## 验证步骤

```bash
# 1. 安装 NGINX Ingress Controller（如果尚未安装）
# 参考官方文档: https://kubernetes.github.io/ingress-nginx/

# 2. 部署应用
kubectl apply -f ingress-app.yaml

# 3. 获取 Ingress 地址
kubectl get ingress
# NAME            CLASS   HOSTS            ADDRESS        PORTS
# web-ingress     nginx   example.com      192.168.1.10   80

# 4. 通过 Ingress 访问
curl -H "Host: example.com" http://<ingress-address>

# 5. 查看路由详情
kubectl describe ingress web-ingress
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
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
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  # rules: 定义路由规则
""",
    check_fn=_check_115_deploy_nginx_ingress,
    lesson=Lesson(
        concept="""\
## Nginx Ingress 完整部署

在真实集群中部署 Ingress 方案涉及多个组件：Ingress Controller、Deployment、Service 和 Ingress 资源。

### 完整架构

```
外部流量 (HTTP/HTTPS)
    │
    ▼
┌─────────────────────────────┐
│  NGINX Ingress Controller    │
│  (DaemonSet 或 Deployment)   │
│  监听 Ingress 资源变化        │
│  动态更新 Nginx 配置         │
└──────────────┬──────────────┘
               │
               │ 按 host/path 路由
               ▼
┌─────────────────────────────┐
│  Ingress (web-ingress)       │
│  rules:                      │
│  - host: example.com         │
│    → web-svc:80              │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Service (web-svc)           │
│  selector: app=web           │
└──────────────┬──────────────┘
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     ┌────┐ ┌────┐ ┌────┐
     │web │ │web │ │web │
     │Pod │ │Pod │ │Pod │
     └────┘ └────┘ └────┘
```

### NGINX Ingress Controller 工作原理

1. **监听 Ingress 资源** - Controller 通过 Watch 机制监听集群中 Ingress 的变化
2. **生成 Nginx 配置** - 根据 Ingress 规则动态生成 nginx.conf
3. **重载 Nginx** - 通过 nginx -s reload 应用新配置
4. **处理流量** - Nginx 接收外部请求并按规则路由

### IngressClass

从 K8s 1.18+ 开始，Ingress 需要指定 `ingressClassName`：
```yaml
spec:
  ingressClassName: nginx
```

这告诉 K8s 该 Ingress 由哪个 Ingress Controller 处理。

### 生产环境最佳实践

1. **安装 cert-manager** - 自动管理 TLS 证书（Let's Encrypt）
2. **配置默认后端** - 处理未匹配的路由
3. **限流和认证** - 通过 Ingress 注解实现
4. **监控和告警** - 监控 Ingress 的 QPS、延迟、错误率
5. **会话亲和性** - 通过注解实现 sticky session
""",
        key_fields=[
            {"name": "spec.ingressClassName", "description": "Ingress Controller 类名", "required": False, "example": "nginx"},
            {"name": "spec.rules", "description": "路由规则", "required": True, "example": "[{host: example.com, http: {paths: [...]}}]"},
            {"name": "spec.rules[].http.paths[].backend.service.name", "description": "后端 Service", "required": True, "example": "web-svc"},
            {"name": "metadata.annotations", "description": "Ingress Controller 特定注解", "required": False, "example": "{nginx.ingress.kubernetes.io/rewrite-target: /}"},
        ],
        diagram="""\
  Nginx Ingress 完整部署架构

  ┌──────────────────────────────────────────────┐
  │  外部用户                                     │
  │  curl -H 'Host: example.com' http://<IP>     │
  └──────────────────┬───────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────────┐
  │  NGINX Ingress Controller                     │
  │  ┌────────────────────────────────────────┐  │
  │  │ Nginx (监听 80/443)                    │  │
  │  │ 动态配置来自 Ingress 资源              │  │
  │  └────────────────────────────────────────┘  │
  └──────────────────┬───────────────────────────┘
                     │ 路由: example.com → web-svc
                     ▼
  ┌──────────────────────────────┐
  │  Ingress (web-ingress)        │
  │  ingressClassName: nginx      │
  │  rules:                       │
  │  - host: example.com          │
  │    http.paths:                │
  │    - backend: web-svc:80      │
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────┐
  │  Service (web-svc)    │
  │  selector: app=web    │
  │  port: 80             │
  └──────────┬───────────┘
             │
     ┌───────┼───────┐
     ▼       ▼       ▼
   ┌────┐  ┌────┐  ┌────┐
   │web-│  │web-│  │web-│
   │pod1│  │pod2│  │pod3│
   └────┘  └────┘  └────┘
""",
        example_yaml="""\
# Deployment                                # Web 应用
apiVersion: apps/v1                        # API 版本
kind: Deployment                           # 资源类型
metadata:                                  # 元数据
  name: web                                # 名称
spec:                                      # 规格
  replicas: 2                              # 2 个副本
  selector:                                # 标签选择器
    matchLabels:
      app: web
  template:                                # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:                          # 容器
      - name: nginx                        # 容器名
        image: nginx:1.25                 # 镜像
---                                        # 多文档分隔
# Service                                  # 服务暴露
apiVersion: v1                             # API 版本
kind: Service                              # 资源类型
metadata:                                  # 元数据
  name: web-svc                            # 名称
spec:                                      # 规格
  selector:                                # 选择 Pod
    app: web                               # 匹配标签
  ports:                                   # 端口
  - port: 80                               # Service 端口
---                                        # 多文档分隔
# Ingress                                  # 入口路由
apiVersion: networking.k8s.io/v1           # Ingress API 版本
kind: Ingress                              # 资源类型
metadata:                                  # 元数据
  name: web-ingress                        # 名称
spec:                                      # 规格
  ingressClassName: nginx                  # Ingress Controller 类
  rules:                                   # 路由规则
  - host: example.com                      # 域名
    http:                                  # HTTP 路由
      paths:                               # 路径列表
      - path: /                            # 匹配所有路径
        pathType: Prefix                   # 前缀匹配
        backend:                           # 后端
          service:                         # 指向 Service
            name: web-svc                  # Service 名称
            port:
              number: 80                   # 端口
""",
        common_errors=[
            "未安装 Ingress Controller，Ingress 规则不生效",
            "Ingress 的 backend.service.name 与 Service 名称不匹配",
            "DNS 未配置域名解析到 Ingress Controller 的 IP",
            "忘记设置 ingressClassName（K8s 1.18+ 需要）",
        ],
        tips=[
            "用 kubectl get ingress -o wide 查看路由和地址",
            "本地测试用 curl -H 'Host: example.com' http://<ingress-ip>",
            "生产环境推荐安装 cert-manager 自动管理 TLS 证书",
        ],
    ),
)


CHAPTER_11_LEVELS: list[Level] = [
    LEVEL_Q11_1, LEVEL_Q11_2, LEVEL_Q11_3, LEVEL_Q11_4, LEVEL_Q11_5,
]
