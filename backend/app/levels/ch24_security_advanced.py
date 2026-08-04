"""Chapter 24: 安全策略进阶 - Admission/OPA/Audit（5 关）

Q24.1 ValidatingAdmissionWebhook - 准入验证
Q24.2 MutatingAdmissionWebhook - 变准入变更
Q24.3 OPA Gatekeeper Constraint - 策略即代码
Q24.4 Audit Policy - 审计日志配置
Q24.5 集群实战 - 多层安全防护
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


# ==================== Q24.1 ValidatingAdmissionWebhook ====================

def _check_241_validating_webhook(user_yaml: str) -> CheckResult:
    """Q24.1 创建一个 ValidatingAdmissionWebhook"""
    # AdmissionWebhook 目前模拟器不支持直接 apply，
    # 直接解析 YAML 验证结构
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: ValidatingAdmissionWebhook 的 YAML"],
        )

    # 查找 ValidatingAdmissionWebhook
    webhook_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "ValidatingAdmissionWebhook":
            webhook_doc = doc
            break

    if not webhook_doc:
        return CheckResult(
            ok=False,
            error="没有找到 ValidatingAdmissionWebhook",
            hints=["你需要创建一个 kind: ValidatingAdmissionWebhook 的 YAML 🛡️"],
        )

    # 检查 apiVersion
    api_version = webhook_doc.get("apiVersion", "")
    if "admissionregistration.k8s.io" not in api_version:
        return CheckResult(
            ok=False,
            error=f"apiVersion 应为 admissionregistration.k8s.io/v1，实际为 '{api_version}'",
            hints=["ValidatingAdmissionWebhook 的 apiVersion 是 admissionregistration.k8s.io/v1"],
        )

    # 检查 metadata.name
    metadata = webhook_doc.get("metadata", {})
    if not isinstance(metadata, dict) or not metadata.get("name"):
        return CheckResult(
            ok=False,
            error="缺少 metadata.name",
            hints=["ValidatingAdmissionWebhook 需要一个名称"],
        )

    spec = webhook_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="ValidatingAdmissionWebhook 缺少 spec", hints=[])

    # 检查 webhooks 列表
    webhooks = spec.get("webhooks")
    if not isinstance(webhooks, list) or not webhooks:
        return CheckResult(
            ok=False,
            error="spec.webhooks 为空或缺失",
            hints=["spec.webhooks 是 webhook 配置列表，至少需要一个"],
        )

    wh = webhooks[0]
    if not isinstance(wh, dict):
        return CheckResult(ok=False, error="webhooks[0] 格式错误", hints=[])

    # 检查 webhook name（必须符合 DNS 子域名格式）
    wh_name = wh.get("name")
    if not wh_name:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 name",
            hints=["每个 webhook 需要 name 字段（DNS 子域名格式，如 validate.example.com）"],
        )

    # 检查 clientConfig
    client_config = wh.get("clientConfig", {})
    if not isinstance(client_config, dict) or not client_config:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 clientConfig",
            hints=["clientConfig 定义了 API server 如何连接 webhook 服务"],
        )

    # clientConfig 需要有 service 或 url
    has_service = isinstance(client_config.get("service"), dict)
    has_url = bool(client_config.get("url"))
    if not has_service and not has_url:
        return CheckResult(
            ok=False,
            error="clientConfig 需要指定 service 或 url",
            hints=["clientConfig.service 定义集群内服务，或 clientConfig.url 定义外部 URL"],
        )

    # 检查 rules
    rules = wh.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 rules",
            hints=["rules 定义哪些资源操作会触发 webhook"],
        )

    rule = rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    # 检查 operations
    operations = rule.get("operations")
    if not isinstance(operations, list) or not operations:
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 operations",
            hints=["operations 定义触发操作类型: CREATE, UPDATE, DELETE 等"],
        )

    # 检查 sideEffects（v1 必填）
    side_effects = wh.get("sideEffects")
    if side_effects is None:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 sideEffects（v1 必填）",
            hints=["sideEffects 可选值: None, NoneOnDryRun, Some, Unknown"],
        )

    # 检查 admissionReviewVersions（v1 必填）
    admission_review_versions = wh.get("admissionReviewVersions")
    if not admission_review_versions:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 admissionReviewVersions（v1 必填）",
            hints=["admissionReviewVersions 如 ['v1']"],
        )

    state = ClusterState()
    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！ValidatingAdmissionWebhook 会在资源创建/更新时进行验证 🛡️"],
    )


LEVEL_Q24_1 = Level(
    id="Q24.1",
    chapter="ch24",
    title="ValidatingAdmissionWebhook",
    description="""
# ValidatingAdmissionWebhook 🛡️

**ValidatingAdmissionWebhook** 在资源被持久化到 etcd 之前进行**验证**，如果不通过则拒绝请求。

## 任务

创建一个 ValidatingAdmissionWebhook：
- `kind: ValidatingAdmissionWebhook`
- `apiVersion: admissionregistration.k8s.io/v1`
- `spec.webhooks` 包含至少一个 webhook 配置
- webhook 需要 `name`、`clientConfig`、`rules`、`sideEffects`、`admissionReviewVersions`

## 提示

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionWebhook
metadata:
  name: validate-pod.example.com
spec:
  webhooks:
  - name: validate-pod.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: default
        path: /validate
    rules:
    - operations: ["CREATE", "UPDATE"]
      apiGroups: [""]
      apiVersions: ["v1"]
      resources: ["pods"]
    sideEffects: None
    admissionReviewVersions: ["v1"]
```
""",
    starter_yaml="""\
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionWebhook
metadata:
  name: validate-pod.example.com
spec:
  webhooks:
  # - name: validate-pod.example.com
  #   clientConfig:
  #     service: ...
  #   rules: ...
  #   sideEffects: None
  #   admissionReviewVersions: ["v1"]
""",
    check_fn=_check_241_validating_webhook,
    lesson=Lesson(
        concept="""\
## 什么是 Admission Webhook？

**Admission Webhook** 是 Kubernetes 准入控制（Admission Control）的扩展机制，允许你在资源被持久化到 etcd **之前**拦截和验证/修改请求。

### 准入控制流程

```
API Request → 认证 → 授权 → ┌─ Mutating Webhook (变更) ─┐ → 持久化
                             │  Object Schema 验证      │   到 etcd
                             └─ Validating Webhook ─────┘
                                (验证)
```

### 两种 Admission Webhook

| 类型 | 作用 | 时机 | 能否修改对象 |
|------|------|------|------------|
| MutatingAdmissionWebhook | 修改/注入字段 | 准入早期 | ✅ 可以修改 |
| ValidatingAdmissionWebhook | 验证字段合法性 | 准入晚期 | ❌ 只能拒绝 |

### ValidatingAdmissionWebhook 工作流程

```
1. kubectl apply → API Server 收到请求
2. 认证 + 授权通过
3. Mutating Webhook 执行（如果有）
4. Schema 验证
5. Validating Webhook 调用你的服务
6. 你的服务返回 allow=true 或 allow=false
7. 如果允许 → 写入 etcd
   如果拒绝 → 返回错误给用户
```

### 常见使用场景

- **镜像来源验证**：只允许受信任的镜像仓库
- **标签强制**：要求所有 Pod 必须有特定标签
- **资源限制检查**：要求所有容器设置 resources.limits
- **命名规范**：验证资源名称符合规范
- **安全策略**：禁止 privileged 容器

### v1 必填字段

从 admissionregistration.k8s.io/v1 开始，以下字段为**必填**：
- `sideEffects`：声明 webhook 的副作用（None/NoneOnDryRun/Some/Unknown）
- `admissionReviewVersions`：支持的 AdmissionReview 版本
""",
        key_fields=[
            {"name": "spec.webhooks[].name", "description": "Webhook 名称（DNS 子域名格式）", "required": True, "example": "validate-pod.example.com"},
            {"name": "spec.webhooks[].clientConfig", "description": "API Server 如何连接 webhook 服务", "required": True, "example": "{service: {name: webhook-svc, namespace: default, path: /validate}}"},
            {"name": "spec.webhooks[].rules", "description": "哪些资源操作触发 webhook", "required": True, "example": "[{operations: [CREATE], apiGroups: [''], resources: [pods]}]"},
            {"name": "spec.webhooks[].sideEffects", "description": "Webhook 副作用声明（v1 必填）", "required": True, "example": "None"},
            {"name": "spec.webhooks[].admissionReviewVersions", "description": "支持的 AdmissionReview 版本（v1 必填）", "required": True, "example": "['v1']"},
        ],
        diagram="""\
┌──────── ValidatingAdmissionWebhook ────────────────┐
│  spec:                                             │
│    webhooks:                                       │
│    - name: validate-pod.example.com                │
│      clientConfig:                                 │
│        service:                                    │
│          name: webhook-service                     │
│          namespace: default                        │
│          path: /validate                           │
│      rules:                                        │
│      - operations: [CREATE, UPDATE]                │
│        apiGroups: [""]                             │
│        resources: [pods]                           │
│      sideEffects: None                             │
│      admissionReviewVersions: ["v1"]               │
└────────────────────┬───────────────────────────────┘
                     │
    kubectl apply pod │
          ┌──────────▼──────────┐
          │    API Server       │
          │  (Admission Chain)  │
          └──────────┬──────────┘
                     │ HTTP POST /validate
                     ▼
          ┌──────────────────────┐
          │  Webhook Service     │
          │  验证逻辑            │
          │  → allow: true/false │
          └──────────────────────┘
""",
        example_yaml="""\
apiVersion: admissionregistration.k8s.io/v1  # API 版本
kind: ValidatingAdmissionWebhook             # 资源类型
metadata:                                    # 元数据
  name: validate-pod.example.com             # 名称
spec:                                        # 规格定义
  webhooks:                                  # Webhook 列表
  - name: validate-pod.example.com           # Webhook 名（DNS 子域名）
    clientConfig:                            # 客户端配置
      service:                               # 集群内服务
        name: webhook-service                # Service 名
        namespace: default                   # 命名空间
        path: /validate                      # Webhook 路径
    rules:                                   # 触发规则
    - operations: [CREATE, UPDATE]           # 操作类型
      apiGroups: [""]                        # 核心 API 组
      apiVersions: ["v1"]                    # API 版本
      resources: [pods]                      # 资源类型
    sideEffects: None                        # 无副作用（v1 必填）
    admissionReviewVersions: ["v1"]          # 支持版本（v1 必填）
    failurePolicy: Fail                      # 失败策略: Fail/Ignore
    timeoutSeconds: 5                        # 超时时间
""",
        common_errors=[
            "忘记设置 sideEffects（v1 必填字段）",
            "忘记设置 admissionReviewVersions（v1 必填字段）",
            "webhook name 不符合 DNS 子域名格式（如包含下划线）",
            "clientConfig 中 service 和 url 都不设，API Server 无法调用 webhook",
            "rules 中的 apiGroups 写错（核心资源是空字符串 ''）",
        ],
        tips=[
            "用 kubectl get validatingwebhookconfigurations 查看配置",
            "开发 webhook 服务时可先用 --dry-run 测试",
            "failurePolicy: Ignore 可以在 webhook 不可用时放行请求（不安全但便于调试）",
            "生产环境建议设置合理的 timeoutSeconds（默认 10s）",
        ],
    ),
)


# ==================== Q24.2 MutatingAdmissionWebhook ====================

def _check_242_mutating_webhook(user_yaml: str) -> CheckResult:
    """Q24.2 创建一个 MutatingAdmissionWebhook"""
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 kind: MutatingAdmissionWebhook 的 YAML"],
        )

    webhook_doc = None
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "MutatingAdmissionWebhook":
            webhook_doc = doc
            break

    if not webhook_doc:
        return CheckResult(
            ok=False,
            error="没有找到 MutatingAdmissionWebhook",
            hints=["你需要创建一个 kind: MutatingAdmissionWebhook 的 YAML 🔄"],
        )

    # 检查 apiVersion
    api_version = webhook_doc.get("apiVersion", "")
    if "admissionregistration.k8s.io" not in api_version:
        return CheckResult(
            ok=False,
            error=f"apiVersion 应为 admissionregistration.k8s.io/v1，实际为 '{api_version}'",
            hints=["MutatingAdmissionWebhook 的 apiVersion 是 admissionregistration.k8s.io/v1"],
        )

    spec = webhook_doc.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="MutatingAdmissionWebhook 缺少 spec", hints=[])

    webhooks = spec.get("webhooks")
    if not isinstance(webhooks, list) or not webhooks:
        return CheckResult(
            ok=False,
            error="spec.webhooks 为空或缺失",
            hints=["spec.webhooks 是 webhook 配置列表，至少需要一个"],
        )

    wh = webhooks[0]
    if not isinstance(wh, dict):
        return CheckResult(ok=False, error="webhooks[0] 格式错误", hints=[])

    # 检查 name
    if not wh.get("name"):
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 name",
            hints=["每个 webhook 需要 name 字段"],
        )

    # 检查 clientConfig
    client_config = wh.get("clientConfig", {})
    if not isinstance(client_config, dict) or not client_config:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 clientConfig",
            hints=["clientConfig 定义了 API server 如何连接 webhook 服务"],
        )

    has_service = isinstance(client_config.get("service"), dict)
    has_url = bool(client_config.get("url"))
    if not has_service and not has_url:
        return CheckResult(
            ok=False,
            error="clientConfig 需要指定 service 或 url",
            hints=["clientConfig.service 定义集群内服务，或 clientConfig.url 定义外部 URL"],
        )

    # 检查 rules
    rules = wh.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 rules",
            hints=["rules 定义哪些资源操作会触发 webhook"],
        )

    # 检查 sideEffects（v1 必填）
    if wh.get("sideEffects") is None:
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 sideEffects（v1 必填）",
            hints=["sideEffects 可选值: None, NoneOnDryRun, Some, Unknown"],
        )

    # 检查 admissionReviewVersions（v1 必填）
    if not wh.get("admissionReviewVersions"):
        return CheckResult(
            ok=False,
            error="webhooks[0] 缺少 admissionReviewVersions（v1 必填）",
            hints=["admissionReviewVersions 如 ['v1']"],
        )

    # MutatingWebhook 特有：建议检查 reinvocationPolicy
    reinvocation = wh.get("reinvocationPolicy")
    hints = ["干得漂亮！MutatingAdmissionWebhook 可以在资源保存前注入或修改字段 🔄"]
    if reinvocation is None:
        hints.append("💡 建议设置 reinvocationPolicy: IfNeeded 或 Never（默认 Never）")

    state = ClusterState()
    return CheckResult(ok=True, state=state, hints=hints)


LEVEL_Q24_2 = Level(
    id="Q24.2",
    chapter="ch24",
    title="MutatingAdmissionWebhook",
    description="""
# MutatingAdmissionWebhook 🔄

**MutatingAdmissionWebhook** 在资源被验证之前**修改/注入**字段，常用于自动注入 Sidecar、标签、注解等。

## 任务

创建一个 MutatingAdmissionWebhook：
- `kind: MutatingAdmissionWebhook`
- `apiVersion: admissionregistration.k8s.io/v1`
- `spec.webhooks` 包含至少一个 webhook 配置
- webhook 需要 `name`、`clientConfig`、`rules`、`sideEffects`、`admissionReviewVersions`

## 提示

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionWebhook
metadata:
  name: inject-sidecar.example.com
spec:
  webhooks:
  - name: inject-sidecar.example.com
    clientConfig:
      service:
        name: sidecar-injector
        namespace: default
        path: /mutate
    rules:
    - operations: ["CREATE"]
      apiGroups: [""]
      apiVersions: ["v1"]
      resources: ["pods"]
    sideEffects: None
    admissionReviewVersions: ["v1"]
    reinvocationPolicy: IfNeeded
```
""",
    starter_yaml="""\
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionWebhook
metadata:
  name: inject-sidecar.example.com
spec:
  webhooks:
  # - name: inject-sidecar.example.com
  #   clientConfig:
  #     service: ...
  #   rules: ...
  #   sideEffects: None
  #   admissionReviewVersions: ["v1"]
  #   reinvocationPolicy: IfNeeded
""",
    check_fn=_check_242_mutating_webhook,
    lesson=Lesson(
        concept="""\
## MutatingAdmissionWebhook 变更准入

**MutatingAdmissionWebhook** 在准入控制的**早期阶段**执行，可以**修改**请求中的对象。

### Mutating vs Validating

```
API Request
    │
    ▼
┌──────────────────────┐
│  Mutating Webhooks   │ ← 可以修改对象（注入字段、Sidecar 等）
│  (按配置顺序执行)     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Object Schema 验证  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Validating Webhooks │ ← 只能验证，不能修改
│  (全部并行执行)      │
└──────────┬───────────┘
           ▼
       写入 etcd
```

### 常见使用场景

| 场景 | 说明 |
|------|------|
| **Sidecar 注入** | Istio/Linkerd 自动注入代理容器 |
| **镜像修改** | 自动添加镜像签名/修改 tag |
| **标签注入** | 自动添加 team/project 标签 |
| **注解注入** | 添加默认注解 |
| **SA 注入** | 自动绑定默认 ServiceAccount |
| **Volume 注入** | 自动挂载证书/配置卷 |

### reinvocationPolicy

Mutating Webhook 独有字段，控制是否在后续 webhook 修改对象后**重新调用**：

- `Never`（默认）：只调用一次
- `IfNeeded`：如果后续 webhook 修改了对象，重新调用此 webhook

### Webhook 配置中的关键概念

```
AdmissionReview (请求) → Webhook 服务 → AdmissionReview (响应)
     │                                      │
     │  包含:                               │  包含:
     │  - kind/apiVersion                   │  - response.allowed
     │  - operation (CREATE/UPDATE)         │  - response.patch (JSON Patch)
     │  - object (原始对象)                 │  - response.patchType
     │  - userInfo                         │  - response.warnings
```

### JSON Patch

Mutating Webhook 通过 **JSON Patch** 返回修改：
```json
[
  {"op": "add", "path": "/spec/containers/-", "value": {"name": "sidecar", ...}},
  {"op": "add", "path": "/metadata/labels/injected", "value": "true"}
]
```
""",
        key_fields=[
            {"name": "spec.webhooks[].name", "description": "Webhook 名称（DNS 子域名格式）", "required": True, "example": "inject-sidecar.example.com"},
            {"name": "spec.webhooks[].clientConfig", "description": "API Server 连接 webhook 的配置", "required": True, "example": "{service: {name: injector, namespace: default, path: /mutate}}"},
            {"name": "spec.webhooks[].rules", "description": "触发规则", "required": True, "example": "[{operations: [CREATE], resources: [pods]}]"},
            {"name": "spec.webhooks[].sideEffects", "description": "副作用声明（v1 必填）", "required": True, "example": "None"},
            {"name": "spec.webhooks[].admissionReviewVersions", "description": "支持的 AdmissionReview 版本", "required": True, "example": "['v1']"},
            {"name": "spec.webhooks[].reinvocationPolicy", "description": "重新调用策略（Mutating 独有）", "required": False, "example": "IfNeeded"},
        ],
        diagram="""\
┌──────── MutatingAdmissionWebhook ───────────────────┐
│  spec:                                              │
│    webhooks:                                        │
│    - name: inject-sidecar.example.com               │
│      clientConfig:                                  │
│        service:                                     │
│          name: sidecar-injector                     │
│          namespace: default                         │
│          path: /mutate                              │
│      rules:                                         │
│      - operations: [CREATE]                         │
│        apiGroups: [""]                              │
│        resources: [pods]                            │
│      sideEffects: None                              │
│      admissionReviewVersions: ["v1"]                │
│      reinvocationPolicy: IfNeeded                   │
└────────────────────┬────────────────────────────────┘
                     │
  kubectl apply pod  │
      ┌──────────────▼──────────────┐
      │       API Server            │
      │   ┌───────────────────┐     │
      │   │ Mutating Webhook  │─────┼──> /mutate
      │   │ (修改对象)         │<────┼──  JSON Patch
      │   └────────┬──────────┘     │
      │            ▼                │
      │   ┌───────────────────┐     │
      │   │ Validating Webhook│     │
      │   └────────┬──────────┘     │
      │            ▼                │
      │         etcd                │
      └─────────────────────────────┘
                     │
            Pod 被注入了 Sidecar 容器
""",
        example_yaml="""\
apiVersion: admissionregistration.k8s.io/v1  # API 版本
kind: MutatingAdmissionWebhook              # 资源类型
metadata:                                   # 元数据
  name: inject-sidecar.example.com          # 名称
spec:                                       # 规格定义
  webhooks:                                 # Webhook 列表
  - name: inject-sidecar.example.com        # Webhook 名
    clientConfig:                           # 客户端配置
      service:                              # 集群内服务
        name: sidecar-injector              # Service 名
        namespace: default                  # 命名空间
        path: /mutate                       # Webhook 路径
    rules:                                  # 触发规则
    - operations: [CREATE]                  # 仅创建时触发
      apiGroups: [""]                       # 核心 API 组
      apiVersions: ["v1"]                   # API 版本
      resources: [pods]                     # 资源类型
    sideEffects: None                       # 无副作用
    admissionReviewVersions: ["v1"]         # 支持版本
    reinvocationPolicy: IfNeeded            # 按需重新调用
    failurePolicy: Fail                     # 失败策略
    timeoutSeconds: 5                       # 超时
""",
        common_errors=[
            "忘记设置 sideEffects 或 admissionReviewVersions（v1 必填）",
            "Mutating 和 Validating webhook 搞混（Mutating 在前，Validating 在后）",
            "reinvocationPolicy 设置不当导致无限循环（Mutating webhook 互相触发）",
            "clientConfig 中未配置 caBundle 导致 API Server 无法验证 webhook 服务 TLS 证书",
            "rules 中遗漏了需要注入的资源类型",
        ],
        tips=[
            "用 kubectl get mutatingwebhookconfigurations 查看配置",
            "Istio 的 sidecar 注入就是通过 MutatingAdmissionWebhook 实现的",
            "开发时可以用 --dry-run=server 测试 webhook 是否被正确调用",
            "多个 Mutating Webhook 按 name 字母序执行，注意执行顺序",
        ],
    ),
)


# ==================== Q24.3 OPA Gatekeeper Constraint ====================

def _check_243_opa_constraint(user_yaml: str) -> CheckResult:
    """Q24.3 创建一个 OPA Gatekeeper Constraint"""
    # Gatekeeper Constraint 是 CRD，需要先注册
    crd_yaml = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: constraints.templates.gatekeeper.sh
spec:
  group: templates.gatekeeper.sh
  names:
    kind: ConstraintTemplate
    plural: constrainttemplates
    singular: constrainttemplate
  scope: Cluster
  versions:
  - name: v1
    served: true
    storage: true
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: k8srequiredlabels.constraints.gatekeeper.sh
spec:
  group: constraints.gatekeeper.sh
  names:
    kind: K8sRequiredLabels
    plural: k8srequiredlabels
    singular: k8srequiredlabels
  scope: Cluster
  versions:
  - name: v1
    served: true
    storage: true
"""
    try:
        state = ClusterState()
        state = preset_state(state, crd_yaml)
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 查找 Constraint（Gatekeeper Constraint 是 CR）
    constraint_docs = [
        doc for doc in state.customresources.values()
        if doc.get("apiVersion", "").startswith("constraints.gatekeeper.sh")
    ]
    if not constraint_docs:
        return CheckResult(
            ok=False,
            error="没有创建任何 Gatekeeper Constraint",
            hints=["你需要 apply 一个 apiVersion 为 constraints.gatekeeper.sh/v1beta1 的 YAML 📋"],
        )

    constraint = constraint_docs[0]
    spec = constraint.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Constraint 缺少 spec", hints=[])

    # 检查 match（匹配范围）
    match = spec.get("match", {})
    if not isinstance(match, dict) or not match:
        return CheckResult(
            ok=False,
            error="Constraint 缺少 spec.match",
            hints=["spec.match 定义约束的匹配范围（kinds/namespaces/labelSelector）"],
        )

    # match 中至少应有 kinds
    kinds = match.get("kinds")
    if not isinstance(kinds, list) or not kinds:
        return CheckResult(
            ok=False,
            error="spec.match 缺少 kinds",
            hints=["match.kinds 定义约束作用的资源类型，如 [{apiGroups: [''], kinds: ['Namespace']}]"],
        )

    # 检查 parameters（约束参数）
    parameters = spec.get("parameters", {})
    if not isinstance(parameters, dict) or not parameters:
        return CheckResult(
            ok=False,
            error="Constraint 缺少 spec.parameters",
            hints=["spec.parameters 定义约束的具体参数，如要求哪些标签"],
        )

    # 对于 K8sRequiredLabels，检查 labels 参数
    kind = constraint.get("kind", "")
    if "RequiredLabels" in kind:
        labels_param = parameters.get("labels")
        if not isinstance(labels_param, list) or not labels_param:
            return CheckResult(
                ok=False,
                error="K8sRequiredLabels 的 parameters 缺少 labels 列表",
                hints=["parameters.labels 定义必须的标签列表，如 ['team', 'env']"],
            )

    # 检查 enforcementAction（可选）
    enforcement = spec.get("enforcementAction", "deny")
    if enforcement not in ("deny", "dryrun", "warn"):
        return CheckResult(
            ok=False,
            error=f"enforcementAction 应为 deny/dryrun/warn，实际为 '{enforcement}'",
            hints=["enforcementAction: deny（拒绝）、dryrun（仅记录不拒绝）、warn（告警）"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！OPA Gatekeeper 会根据此 Constraint 验证资源是否符合策略 📋"],
    )


LEVEL_Q24_3 = Level(
    id="Q24.3",
    chapter="ch24",
    title="OPA Gatekeeper Constraint",
    description="""
# OPA Gatekeeper Constraint 📋

**OPA Gatekeeper** 是 Kubernetes 的策略引擎，用 **Constraint** 资源声明策略规则。

## 任务

创建一个 K8sRequiredLabels Constraint，要求所有 Namespace 必须有 `team` 和 `env` 标签：
- `apiVersion: constraints.gatekeeper.sh/v1beta1`
- `kind: K8sRequiredLabels`
- `spec.match.kinds` 匹配 Namespace
- `spec.parameters.labels` 包含 `team` 和 `env`

## 提示

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-ns-labels
spec:
  match:
    kinds:
    - apiGroups: [""]
      kinds: ["Namespace"]
  parameters:
    labels: ["team", "env"]
  enforcementAction: deny
```
""",
    starter_yaml="""\
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-ns-labels
spec:
  # match: ...
  # parameters: ...
  # enforcementAction: deny
""",
    check_fn=_check_243_opa_constraint,
    lesson=Lesson(
        concept="""\
## OPA Gatekeeper：策略即代码

**OPA (Open Policy Agent)** 是一个通用策略引擎，**Gatekeeper** 是 OPA 在 Kubernetes 上的实现，将策略管理变为**声明式**的 K8s 资源。

### 架构

```
┌──────────────────────────────────────────────────┐
│              Kubernetes API Server               │
│                    │                             │
│         ValidatingAdmissionWebhook               │
│                    │                             │
└────────────────────┼─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│              Gatekeeper Controller               │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Constraint  │  │ ConstraintTemplate       │  │
│  │ (策略实例)   │  │ (Rego 规则 + CRD 定义)   │  │
│  └─────────────┘  └──────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ OPA Engine (Rego 评估)                    │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### 两个核心资源

| 资源 | 作用 | 包含 |
|------|------|------|
| **ConstraintTemplate** | 定义策略规则和 CRD Schema | Rego 代码 + OpenAPI Schema |
| **Constraint** | 策略实例，配置具体参数 | match + parameters |

### ConstraintTemplate 示例

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          properties:
            labels:
              type: array
              items: { type: string }
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8srequiredlabels
      violation[{"msg": msg}] {
        provided := {label | input.review.object.metadata.labels[label]}
        required := {label | label := input.parameters.labels[_]}
        missing := required - provided
        count(missing) > 0
        msg := sprintf("missing required labels: %v", [missing])
      }
```

### Rego 语言

OPA 使用 **Rego** 声明式查询语言：
```rego
# 违规条件：缺失必需标签
violation[{"msg": msg}] {
    provided := {label | input.review.object.metadata.labels[label]}
    required := {label | label := input.parameters.labels[_]}
    missing := required - provided
    count(missing) > 0
    msg := sprintf("missing required labels: %v", [missing])
}
```

### enforcementAction

| 值 | 行为 |
|----|------|
| `deny` | 拒绝不合规请求（默认） |
| `dryrun` | 仅记录，不拒绝（测试用） |
| `warn` | 返回警告但允许请求 |

### match 字段

```yaml
match:
  kinds:              # 资源类型
  - apiGroups: [""]
    kinds: ["Pod"]
  namespaces:         # 命名空间
  - "production"
  - "staging"
  labelSelector:      # 标签选择器
    matchLabels:
      env: production
  excludedNamespaces: # 排除的命名空间
  - kube-system
```
""",
        key_fields=[
            {"name": "spec.match.kinds", "description": "约束作用的资源类型", "required": True, "example": "[{apiGroups: [''], kinds: ['Namespace']}]"},
            {"name": "spec.parameters", "description": "约束参数，由 ConstraintTemplate 定义", "required": True, "example": "{labels: [team, env]}"},
            {"name": "spec.enforcementAction", "description": "执行动作: deny/dryrun/warn", "required": False, "example": "deny"},
            {"name": "spec.match.namespaces", "description": "约束作用的命名空间列表", "required": False, "example": "[production]"},
            {"name": "spec.match.excludedNamespaces", "description": "排除的命名空间", "required": False, "example": "[kube-system]"},
        ],
        diagram="""\
┌──────── ConstraintTemplate ──────────────┐
│  spec:                                   │
│    crd:                                  │
│      spec:                               │
│        names:                            │
│          kind: K8sRequiredLabels         │
│    targets:                              │
│    - rego: |                             │
│        violation[...] { ... }            │
└──────────────────┬───────────────────────┘
                   │ 创建 CRD Kind
                   ▼
┌──────── Constraint (实例) ───────────────┐
│  apiVersion: constraints.gatekeeper.sh   │
│  kind: K8sRequiredLabels                 │
│  spec:                                   │
│    match:                                │
│      kinds: [{kinds: [Namespace]}]       │
│    parameters:                           │
│      labels: [team, env]                 │
│    enforcementAction: deny               │
└──────────────────┬───────────────────────┘
                   │
    kubectl create namespace (无 team 标签)
                   │
                   ▼
          ┌──────────────────┐
          │  Gatekeeper      │
          │  Rego 评估       │
          │  → violation!    │
          │  → deny request  │
          └──────────────────┘
""",
        example_yaml="""\
apiVersion: constraints.gatekeeper.sh/v1beta1  # Gatekeeper API
kind: K8sRequiredLabels                        # Constraint 类型（由 Template 定义）
metadata:                                      # 元数据
  name: require-ns-labels                      # 名称
spec:                                          # 规格定义
  match:                                       # 匹配范围
    kinds:                                     # 资源类型
    - apiGroups: [""]                          # 核心 API 组
      kinds: ["Namespace"]                     # Namespace 资源
  parameters:                                  # 约束参数
    labels:                                    # 必需标签列表
    - team                                     # 团队标签
    - env                                      # 环境标签
  enforcementAction: deny                      # 拒绝不合规请求
""",
        common_errors=[
            "忘记创建 ConstraintTemplate 就直接创建 Constraint（Template 必须先存在）",
            "match.kinds 写错 apiGroups（核心资源用空字符串 ''，不是 'core'）",
            "parameters 的结构与 ConstraintTemplate 中定义的 Schema 不匹配",
            "enforcementAction 拼写错误（如写成 dry-run 而非 dryrun）",
            "Rego 规则语法错误导致 Constraint 无法正常评估",
        ],
        tips=[
            "先用 enforcementAction: dryrun 测试策略，确认无误后改为 deny",
            "用 kubectl get constraints 查看所有约束",
            "Gatekeeper 审计结果存储在 Constraint 的 status 字段中",
            "可以在 Rego 中使用 input.review.object 访问被验证的资源",
        ],
    ),
)


# ==================== Q24.4 Audit Policy ====================

def _check_244_audit_policy(user_yaml: str) -> CheckResult:
    """Q24.4 创建一个 Audit Policy 配置"""
    # Audit Policy 不是 K8s 资源（不能 apply），是 API Server 配置文件
    # 直接解析 YAML 验证结构
    try:
        docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败: {e}", hints=[])

    if not docs:
        return CheckResult(
            ok=False,
            error="YAML 为空或格式错误",
            hints=["你需要编写一个 Audit Policy 配置文件"],
        )

    policy = docs[0]
    if not isinstance(policy, dict):
        return CheckResult(ok=False, error="YAML 格式错误", hints=[])

    # Audit Policy 的根字段是 rules
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Audit Policy 缺少 rules 字段或为空",
            hints=["rules 是审计规则列表，至少需要一条规则"],
        )

    # 检查规则结构
    valid_levels = {"None", "Metadata", "Request", "RequestResponse"}
    valid_verbs = {"get", "list", "watch", "create", "update", "patch", "delete", "deletecollection"}

    has_requestresponse = False
    has_none = False

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return CheckResult(ok=False, error=f"rules[{i}] 格式错误", hints=[])

        # 检查 level（必填）
        level = rule.get("level")
        if not level:
            return CheckResult(
                ok=False,
                error=f"rules[{i}] 缺少 level 字段",
                hints=["level 是必填字段: None, Metadata, Request, RequestResponse"],
            )

        if level not in valid_levels:
            return CheckResult(
                ok=False,
                error=f"rules[{i}] level '{level}' 无效，应为: {', '.join(sorted(valid_levels))}",
                hints=[f"有效值: None, Metadata, Request, RequestResponse"],
            )

        if level == "RequestResponse":
            has_requestresponse = True
        if level == "None":
            has_none = True

        # 检查 resources（可选）
        resources = rule.get("resources")
        if resources is not None:
            if not isinstance(resources, list):
                return CheckResult(
                    ok=False,
                    error=f"rules[{i}] resources 应为列表",
                    hints=["resources 格式: [{apiGroups: [''], resources: ['pods', 'services']}]"],
                )

    # 建议：至少有一条 RequestResponse 级别规则（记录完整请求和响应）
    hints = []
    if not has_requestresponse:
        hints.append("💡 建议至少有一条 level: RequestResponse 规则来记录完整的请求/响应内容")
    if not has_none:
        hints.append("💡 建议用 level: None 过滤掉高频低价值事件（如 get/list/watch）")

    if not hints:
        hints.append("干得漂亮！Audit Policy 配置合理，能有效记录 API 访问行为 🔍")

    state = ClusterState()
    return CheckResult(ok=True, state=state, hints=hints)


LEVEL_Q24_4 = Level(
    id="Q24.4",
    chapter="ch24",
    title="Audit Policy 审计日志",
    description="""
# Audit Policy 审计日志 🔍

**Audit Policy** 定义 Kubernetes API Server 如何记录 API 访问日志，是安全审计的基础。

## 任务

创建一个 Audit Policy 配置：
- 根字段 `rules` 包含至少 2 条规则
- 使用不同的 `level`（如 `RequestResponse` 和 `None`）
- 至少有一条规则记录 `RequestResponse` 级别

## 提示

Audit Policy 不是 K8s 资源，而是 API Server 的配置文件：

```yaml
# audit-policy.yaml
rules:
# 记录 Secret 的完整请求和响应
- level: RequestResponse
  resources:
  - apiGroups: [""]
    resources: ["secrets"]

# 不记录 get/list/watch（高频低价值）
- level: None
  verbs: ["get", "list", "watch"]

# 其他请求记录元数据
- level: Metadata
```
""",
    starter_yaml="""\
# Audit Policy 配置文件（非 K8s 资源）
rules:
# - level: RequestResponse
#   resources: ...
# - level: None
#   verbs: ...
# - level: Metadata
""",
    check_fn=_check_244_audit_policy,
    lesson=Lesson(
        concept="""\
## Kubernetes Audit Policy

**Audit Policy** 定义 API Server 如何记录对 Kubernetes API 的访问，是安全合规的核心工具。

### 审计级别（Level）

| 级别 | 记录内容 | 存储开销 | 适用场景 |
|------|---------|---------|---------|
| `None` | 不记录 | 无 | 过滤高频低价值事件 |
| `Metadata` | 请求元数据（who/what/when） | 低 | 常规审计 |
| `Request` | 元数据 + 请求体 | 中 | 记录变更操作 |
| `RequestResponse` | 元数据 + 请求体 + 响应体 | 高 | 敏感资源完整审计 |

### 审计日志流程

```
kubectl apply → API Server → 审计日志记录
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              后端存储      日志文件     Webhook
              (ELK/Loki)   (/var/log)  (HTTP POST)
```

### 审计记录内容

```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "RequestResponse",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/default/secrets/db-password",
  "verb": "create",
  "user": {
    "username": "alice@example.com",
    "groups": ["system:authenticated"]
  },
  "sourceIPs": ["10.0.0.1"],
  "objectRef": {
    "resource": "secrets",
    "namespace": "default",
    "name": "db-password"
  },
  "requestObject": { ... },
  "responseStatus": { "code": 201 },
  "requestReceivedTimestamp": "2024-01-01T00:00:00Z",
  "stageTimestamp": "2024-01-01T00:00:01Z"
}
```

### 策略设计原则

1. **先排除再包含**：用 `level: None` 过滤低价值事件
2. **敏感资源全覆盖**：Secret、RBAC 等用 `RequestResponse`
3. **变更操作记录**：create/update/delete 用 `Request` 或 `RequestResponse`
4. **只读操作降级**：get/list/watch 用 `Metadata` 或 `None`

### 配置方式

Audit Policy 通过 API Server 启动参数配置：
```bash
kube-apiserver \\
  --audit-policy-file=/etc/kubernetes/audit-policy.yaml \\
  --audit-log-path=/var/log/kubernetes/audit.log \\
  --audit-log-maxage=30 \\
  --audit-log-maxbackup=10 \\
  --audit-log-maxsize=100
```

### 规则匹配顺序

规则按**从上到下**顺序匹配，**第一个匹配的规则生效**（类似 iptables）：
```yaml
rules:
# 1. 先排除高频事件
- level: None
  verbs: ["watch", "list"]

# 2. 敏感资源全记录
- level: RequestResponse
  resources:
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]

# 3. 认证相关
- level: Request
  resources:
  - apiGroups: ["rbac.authorization.k8s.io"]

# 4. 兜底：记录元数据
- level: Metadata
```
""",
        key_fields=[
            {"name": "rules[].level", "description": "审计级别: None/Metadata/Request/RequestResponse", "required": True, "example": "RequestResponse"},
            {"name": "rules[].resources", "description": "匹配的资源类型", "required": False, "example": "[{apiGroups: [''], resources: ['secrets']}]"},
            {"name": "rules[].verbs", "description": "匹配的操作类型", "required": False, "example": "[create, update, delete]"},
            {"name": "rules[].userGroups", "description": "匹配的用户组", "required": False, "example": "[system:authenticated]"},
            {"name": "rules[].namespaces", "description": "匹配的命名空间", "required": False, "example": "[kube-system]"},
        ],
        diagram="""\
┌─────────────── Audit Policy ────────────────────┐
│  rules:                                         │
│  - level: None                                  │
│    verbs: [get, list, watch]  # 过滤只读操作     │
│                                                 │
│  - level: RequestResponse                       │
│    resources:                                   │
│    - apiGroups: [""]                            │
│      resources: [secrets]     # Secret 全记录   │
│                                                 │
│  - level: Request                               │
│    verbs: [create, update, delete] # 变更记录   │
│                                                 │
│  - level: Metadata             # 兜底           │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
            ┌──────────────────┐
            │  API Server      │
            │  审计日志记录     │
            └────────┬─────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     日志文件    Webhook    后端存储
     /var/log   HTTP POST  ELK/Loki
""",
        example_yaml="""\
# Audit Policy 配置文件（不是 K8s 资源，是 API Server 配置）
rules:
# 1. 不记录只读操作（减少日志量）
- level: None
  verbs: ["get", "list", "watch"]

# 2. Secret 完整记录（请求 + 响应）
- level: RequestResponse
  resources:
  - apiGroups: [""]
    resources: ["secrets"]

# 3. RBAC 变更记录请求体
- level: Request
  resources:
  - apiGroups: ["rbac.authorization.k8s.io"]
  verbs: ["create", "update", "patch", "delete"]

# 4. 认证事件记录元数据
- level: Metadata
  userGroups: ["system:authenticated"]

# 5. 兜底：其他请求记录元数据
- level: Metadata
""",
        common_errors=[
            "规则顺序不对：把兜底规则放在最前面，导致后续规则永远不生效",
            "对所有请求都用 RequestResponse 级别，导致日志量爆炸",
            "忘记过滤 get/list/watch 等高频操作",
            "level 拼写错误（如写成 request-response 而非 RequestResponse）",
            "Audit Policy 不是 K8s 资源，不能用 kubectl apply 部署",
        ],
        tips=[
            "Audit Policy 通过 --audit-policy-file 参数传递给 API Server",
            "建议将审计日志发送到 ELK/Loki 等系统进行集中分析",
            "用 --audit-log-maxsize 和 --audit-log-maxbackup 控制日志轮转",
            "生产环境通常对 Secret/RBAC 用 RequestResponse，对其他用 Metadata",
        ],
    ),
)


# ==================== Q24.5 集群实战 - 多层安全防护 ====================

def _check_245_security_stack(user_yaml: str) -> CheckResult:
    """Q24.5 部署完整的多层安全防护：ValidatingWebhook + OPA Constraint + Audit"""
    # 预置 Gatekeeper CRD
    crd_yaml = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: k8srequiredlabels.constraints.gatekeeper.sh
spec:
  group: constraints.gatekeeper.sh
  names:
    kind: K8sRequiredLabels
    plural: k8srequiredlabels
    singular: k8srequiredlabels
  scope: Cluster
  versions:
  - name: v1beta1
    served: true
    storage: true
"""

    try:
        state = ClusterState()
        state = preset_state(state, crd_yaml)
        # 同时尝试 apply 支持的资源
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        # 如果 apply 失败（可能是因为 AdmissionWebhook 不支持），尝试直接解析
        try:
            docs = _parse_yaml_docs(user_yaml)
        except yaml.YAMLError:
            return CheckResult(ok=False, error=str(e), hints=[])

        # 重新初始化 state，只 apply 支持的资源
        state = ClusterState()
        state = preset_state(state, crd_yaml)
        for doc in docs:
            kind = doc.get("kind", "") if isinstance(doc, dict) else ""
            if kind in ("ValidatingAdmissionWebhook", "MutatingAdmissionWebhook"):
                continue  # 跳过不支持的资源
            try:
                import yaml as _yaml
                state = apply_manifest(state, _yaml.dump(doc))
            except K8sError:
                pass  # 忽略单个资源失败

    # 同时解析所有文档以检查 AdmissionWebhook
    try:
        all_docs = _parse_yaml_docs(user_yaml)
    except yaml.YAMLError:
        all_docs = []

    hints = []
    missing = []

    # 检查 1: ValidatingAdmissionWebhook
    has_validating = any(
        isinstance(d, dict) and d.get("kind") == "ValidatingAdmissionWebhook"
        for d in all_docs
    )
    if not has_validating:
        missing.append("ValidatingAdmissionWebhook（准入验证）")

    # 检查 2: OPA Gatekeeper Constraint
    constraint_docs = [
        doc for doc in state.customresources.values()
        if isinstance(doc, dict) and doc.get("apiVersion", "").startswith("constraints.gatekeeper.sh")
    ]
    if not constraint_docs:
        # 也检查原始 YAML
        has_constraint = any(
            isinstance(d, dict) and d.get("apiVersion", "").startswith("constraints.gatekeeper.sh")
            for d in all_docs
        )
        if not has_constraint:
            missing.append("OPA Gatekeeper Constraint（策略即代码）")

    # 检查 3: Audit Policy 或 NetworkPolicy（安全加固）
    has_audit = any(
        isinstance(d, dict) and "rules" in d and "level" in str(d.get("rules", [{}])[0] if isinstance(d.get("rules"), list) and d.get("rules") else {})
        for d in all_docs
    )
    has_networkpolicy = bool(state.networkpolicies)
    if not has_audit and not has_networkpolicy:
        missing.append("Audit Policy 或 NetworkPolicy（审计/网络隔离）")

    if missing:
        return CheckResult(
            ok=False,
            error=f"安全防护栈不完整，缺少：{', '.join(missing)}",
            hints=[
                "多层安全防护需要：1️⃣ ValidatingAdmissionWebhook（准入验证）2️⃣ OPA Constraint（策略即代码）3️⃣ Audit Policy 或 NetworkPolicy",
                "使用多文档 YAML（--- 分隔）在一个文件中定义所有资源",
            ],
        )

    hints.append("🎉 多层安全防护栈部署成功！")
    hints.append("🛡️ ValidatingAdmissionWebhook → 准入验证")
    hints.append("📋 OPA Constraint → 策略即代码")
    hints.append("🔍 Audit/NetworkPolicy → 审计与网络隔离")

    return CheckResult(ok=True, state=state, hints=hints)


LEVEL_Q24_5 = Level(
    id="Q24.5",
    chapter="ch24",
    title="集群实战: 多层安全防护",
    description="""
# 集群实战: 多层安全防护 🎉

将前面学到的安全组件组合起来，构建多层安全防护体系！

## 任务

在一个 YAML 文件中定义以下安全资源（用 `---` 分隔）：

1. **ValidatingAdmissionWebhook** - 准入验证 webhook
2. **K8sRequiredLabels Constraint** - OPA Gatekeeper 约束（要求 Pod 有 `app` 标签）
3. **NetworkPolicy** 或 **Audit Policy** - 网络隔离或审计日志

## 验证步骤

```bash
# 1. 部署安全防护栈
kubectl apply -f security-stack.yaml

# 2. 检查各组件
kubectl get validatingwebhookconfigurations
kubectl get constraints
kubectl get networkpolicy

# 3. 测试安全策略
kubectl run test-pod --image=nginx  # 应被 OPA 拦截（缺少标签）
kubectl apply -f compliant-pod.yaml # 应通过所有检查
```

## 提示

- ValidatingAdmissionWebhook: `apiVersion: admissionregistration.k8s.io/v1`
- OPA Constraint: `apiVersion: constraints.gatekeeper.sh/v1beta1`
- NetworkPolicy: `apiVersion: networking.k8s.io/v1`
""",
    starter_yaml="""\
# 1. ValidatingAdmissionWebhook - 准入验证
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionWebhook
metadata:
  name: validate-deploy.example.com
spec:
  webhooks:
  # - name: validate-deploy.example.com
  #   clientConfig: ...
  #   rules: ...
  #   sideEffects: None
  #   admissionReviewVersions: ["v1"]

---
# 2. OPA Constraint - 策略即代码
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-pod-labels
spec:
  # match: ...
  # parameters: ...

---
# 3. NetworkPolicy - 网络隔离
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  # podSelector: {}
  # policyTypes: [Ingress]
""",
    check_fn=_check_245_security_stack,
    lesson=Lesson(
        concept="""\
## 多层安全防护体系

Kubernetes 安全应采用**纵深防御（Defense in Depth）**策略，在不同层面部署安全控制。

### 安全层次

```
┌──────────────────────────────────────────────────┐
│  Layer 1: 认证 (Authentication)                  │
│  → Who are you? (证书/Token/OIDC)                │
├──────────────────────────────────────────────────┤
│  Layer 2: 授权 (Authorization)                   │
│  → What can you do? (RBAC)                       │
├──────────────────────────────────────────────────┤
│  Layer 3: 准入控制 (Admission Control)            │
│  → Is the request valid? (Webhook/OPA)           │
├──────────────────────────────────────────────────┤
│  Layer 4: 网络安全 (Network Security)             │
│  → Can resources communicate? (NetworkPolicy)    │
├──────────────────────────────────────────────────┤
│  Layer 5: Pod 安全 (Pod Security)                 │
│  → Is the Pod safe? (PSS/SecurityContext)        │
├──────────────────────────────────────────────────┤
│  Layer 6: 审计 (Audit)                            │
│  → What happened? (Audit Policy/Log)             │
└──────────────────────────────────────────────────┘
```

### 各层职责

| 层次 | 组件 | 作用 |
|------|------|------|
| 准入验证 | ValidatingAdmissionWebhook | 资源创建前验证 |
| 策略即代码 | OPA Gatekeeper | 声明式策略管理 |
| 网络隔离 | NetworkPolicy | Pod 间流量控制 |
| 审计追踪 | Audit Policy | API 访问记录 |

### 安全防护流程

```
用户请求 → 认证 → 授权 → ┌─ Mutating Webhook ──┐
                         │  Validating Webhook  │ → NetworkPolicy
                         │  OPA Constraint      │   (运行时网络隔离)
                         └──────────────────────┘
                                   │
                             写入 etcd
                                   │
                         ┌─ Audit Log 记录 ─────┐
                         │  (事后追溯)           │
                         └──────────────────────┘
```

### 生产环境安全建议

1. **最小权限原则**：RBAC 只授予必要的权限
2. **镜像安全**：只允许受信任的镜像仓库
3. **Pod 安全标准**：enforce restricted 模式
4. **网络隔离**：默认拒绝，按需开放
5. **审计日志**：记录所有敏感操作
6. **定期审计**：检查策略有效性
7. **密钥管理**：使用外部 Secret 管理（Vault等）

### 安全策略演进

```
PodSecurityPolicy (PSP)  →  Pod Security Admission (PSA)
                          →  OPA Gatekeeper
                          →  Kyverno
                          →  Custom Webhooks
```
""",
        key_fields=[
            {"name": "ValidatingAdmissionWebhook.spec.webhooks", "description": "准入验证 webhook 配置", "required": True, "example": "[{name: validate, clientConfig: {...}, rules: [...]}]"},
            {"name": "Constraint.spec.match", "description": "OPA 策略匹配范围", "required": True, "example": "{kinds: [{apiGroups: [''], kinds: [Pod]}]}"},
            {"name": "Constraint.spec.parameters", "description": "OPA 策略参数", "required": True, "example": "{labels: [app]}"},
            {"name": "NetworkPolicy.spec.podSelector", "description": "网络策略作用的 Pod", "required": False, "example": "{}（所有 Pod）"},
            {"name": "NetworkPolicy.spec.policyTypes", "description": "策略方向: Ingress/Egress", "required": False, "example": "[Ingress, Egress]"},
        ],
        diagram="""\
┌──────────── 多层安全防护栈 ────────────────────────────┐
│                                                       │
│  ┌── ValidatingAdmissionWebhook ──┐                   │
│  │  验证 Deployment 配置           │                   │
│  │  sideEffects: None              │                   │
│  └────────────┬───────────────────┘                   │
│               │ +                                     │
│  ┌── OPA Constraint ──────────────┐                   │
│  │  K8sRequiredLabels             │                   │
│  │  match: pods                   │                   │
│  │  parameters: labels=[app]      │                   │
│  └────────────┬───────────────────┘                   │
│               │ +                                     │
│  ┌── NetworkPolicy ───────────────┐                   │
│  │  default-deny                  │                   │
│  │  podSelector: {}               │                   │
│  │  policyTypes: [Ingress]        │                   │
│  └────────────┬───────────────────┘                   │
│               │                                       │
│               ▼                                       │
│  ┌── 审计日志 ─────────────────────┐                  │
│  │  Audit Policy                  │                   │
│  │  记录所有安全相关事件           │                   │
│  └────────────────────────────────┘                   │
│                                                       │
│  深度防御：准入 → 策略 → 网络 → 审计                  │
└───────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# 1. ValidatingAdmissionWebhook - 准入验证
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionWebhook
metadata:
  name: validate-deploy.example.com
spec:
  webhooks:
  - name: validate-deploy.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: default
        path: /validate
    rules:
    - operations: [CREATE, UPDATE]
      apiGroups: ["apps"]
      apiVersions: ["v1"]
      resources: ["deployments"]
    sideEffects: None
    admissionReviewVersions: ["v1"]
---
# 2. OPA Constraint - 策略即代码
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-pod-labels
spec:
  match:
    kinds:
    - apiGroups: [""]
      kinds: ["Pod"]
  parameters:
    labels: ["app"]
  enforcementAction: deny
---
# 3. NetworkPolicy - 网络隔离
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
""",
        common_errors=[
            "多文档 YAML 中忘记用 --- 分隔不同资源",
            "ValidatingAdmissionWebhook 缺少 v1 必填字段（sideEffects, admissionReviewVersions）",
            "OPA Constraint 的 match.kinds 配置不正确",
            "NetworkPolicy 的 policyTypes 缺失或写错",
            "各安全组件之间没有协调，可能产生冲突或重复检查",
        ],
        tips=[
            "先部署安全组件，再用测试 Pod 验证策略是否生效",
            "OPA Constraint 建议先用 dryrun 模式测试，确认无误后改为 deny",
            "NetworkPolicy 需要支持 CNI 插件（如 Calico/Cilium）才能生效",
            "定期审查审计日志，发现潜在安全问题",
            "安全策略应该版本控制，通过 GitOps 管理变更",
        ],
    ),
)


CHAPTER_24_LEVELS: list[Level] = [
    LEVEL_Q24_1, LEVEL_Q24_2, LEVEL_Q24_3, LEVEL_Q24_4, LEVEL_Q24_5,
]
