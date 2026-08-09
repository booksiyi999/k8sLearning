"""Chapter 17: CRD & Operator 概念（10 关）

Q17.1 创建 CRD - metadata.name 格式校验 + spec.names.kind 必填
Q17.2 CRD Schema 验证 - OpenAPI v3 properties 必填
Q17.3 Operator RBAC - Role + RoleBinding 校验
Q17.4 Status 子资源 - CRD subresources.status + Deployment WATCH
Q17.5 Operator Deployment 完整校验
Q17.6 Reconcile 循环骨架 - 关键模式识别
Q17.7 OwnerReference 与级联删除
Q17.8 Finalizer 概念
Q17.9 Conditions 状态管理
Q17.10 Operator 最佳实践总结
"""
import yaml
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# 预置 CRD YAML（供 Q17.7-Q17.9 等关卡使用）
_PRESET_CRD_YAML = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
    singular: blog
    shortNames:
    - bl
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
              author:
                type: string
              content:
                type: string
          status:
            type: object
            properties:
              conditions:
                type: array
                items:
                  type: object
                  properties:
                    type:
                      type: string
                    status:
                      type: string
                    lastTransitionTime:
                      type: string
"""


# ==================== Q17.1 创建 CRD（增强：metadata.name 格式校验） ====================

def _check_171_create_crd(user_yaml: str) -> CheckResult:
    """Q17.1 创建一个 Blog CRD，校验 metadata.name 格式 = <plural>.<group>"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.customresourcedefinitions:
        return CheckResult(
            ok=False,
            error="没有创建任何 CustomResourceDefinition",
            hints=["你需要 apply 一个 kind: CustomResourceDefinition 的 YAML"],
        )

    crd_name = next(iter(state.customresourcedefinitions))
    crd = state.customresourcedefinitions[crd_name]
    spec = crd.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="CRD 缺少 spec", hints=[])

    # 检查 group
    group = spec.get("group")
    if not group or not isinstance(group, str):
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.group",
            hints=["spec.group 定义自定义资源的 API 组，如 'blog.example.com'"],
        )

    # 检查 names
    names = spec.get("names", {})
    if not isinstance(names, dict) or not names:
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.names",
            hints=["spec.names 定义资源的命名，包括 kind/plural/singular"],
        )

    if not names.get("kind"):
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.names.kind",
            hints=["spec.names.kind 是资源的类型名，如 'Blog'"],
        )

    if not names.get("plural"):
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.names.plural",
            hints=["spec.names.plural 是资源的复数名，如 'blogs'"],
        )

    # 检查 versions
    versions = spec.get("versions")
    if not isinstance(versions, list) or not versions:
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.versions",
            hints=["spec.versions 定义 API 版本列表，至少需要一个版本"],
        )

    v0 = versions[0]
    if not isinstance(v0, dict) or not v0.get("name"):
        return CheckResult(
            ok=False,
            error="spec.versions[0] 缺少 name",
            hints=["版本需要 name 字段，如 'v1'"],
        )

    # 检查 scope
    scope = spec.get("scope")
    if scope not in ("Namespaced", "Cluster"):
        return CheckResult(
            ok=False,
            error=f"spec.scope 应为 'Namespaced' 或 'Cluster'，实际为 '{scope}'",
            hints=["scope 决定资源是命名空间级还是集群级"],
        )

    # 增强：校验 metadata.name 格式 = <plural>.<group>
    plural = names.get("plural", "")
    expected_name = f"{plural}.{group}"
    if crd_name != expected_name:
        return CheckResult(
            ok=False,
            error=(
                f"metadata.name 格式错误：应为 '{expected_name}'"
                f"（<plural>.<group>），实际为 '{crd_name}'"
            ),
            hints=[
                "CRD 的 metadata.name 必须遵循 <plural>.<group> 格式",
                f"plural='{plural}', group='{group}' -> name='{expected_name}'",
            ],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["CRD 创建成功！metadata.name 格式校验通过 🎉"],
    )


LEVEL_Q17_1 = Level(
    id="Q17.1",
    chapter="ch17",
    title="创建 CRD - 自定义资源定义",
    description="""
# 创建 CRD - 自定义资源定义 🏗️

**CustomResourceDefinition (CRD)** 让你扩展 Kubernetes API，创建自己的资源类型。就像给 K8s 安装了一个"插件"，让它认识全新的资源。

## 任务

创建一个 `Blog` 资源的 CRD：
- `kind: CustomResourceDefinition`
- `apiVersion: apiextensions.k8s.io/v1`
- `spec.group: blog.example.com`
- `spec.names.kind: Blog`，`plural: blogs`
- `spec.versions` 包含 `v1` 版本
- `spec.scope: Namespaced`
- **`metadata.name` 必须为 `<plural>.<group>` 格式**，即 `blogs.blog.example.com`

## 提示

CRD 的 name 遵循 `<plural>.<group>` 格式，如 `blogs.blog.example.com`
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
```
""",
    starter_yaml="""\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  # group: blog.example.com
  # names:
  #   kind: Blog
  #   plural: blogs
  # scope: Namespaced
  # versions:
  # - name: v1
  #   served: true
  #   storage: true
""",
    check_fn=_check_171_create_crd,
    lesson=Lesson(
        concept="""\
## 什么是 CustomResourceDefinition？

**CRD（自定义资源定义）** 是 Kubernetes 的扩展机制。它允许你在不修改 K8s 源码的情况下，创建全新的资源类型。

### CRD 的核心组成

```
┌──────── CRD (blogs.blog.example.com) ────────┐
│  spec:                                       │
│    group: blog.example.com    # API 组       │
│    names:                     # 资源命名      │
│      kind: Blog               # 类型名       │
│      plural: blogs            # 复数         │
│      singular: blog           # 单数         │
│      shortNames: [bl]         # 简称         │
│    scope: Namespaced          # 作用域       │
│    versions:                  # API 版本     │
│    - name: v1                                │
│      served: true             # 是否提供服务  │
│      storage: true            # 是否存储版本  │
└──────────────────────────────────────────────┘
```

### metadata.name 格式校验

CRD 的 `metadata.name` **必须**遵循 `<plural>.<group>` 格式，这是 K8s API Server 的硬性要求：

| 字段 | 值 | 来源 |
|------|------|------|
| plural | blogs | spec.names.plural |
| group | blog.example.com | spec.group |
| **metadata.name** | **blogs.blog.example.com** | plural + "." + group |

如果 name 格式不正确，API Server 会直接拒绝创建 CRD。

### scope 选项

| scope | 说明 | 示例 |
|-------|------|------|
| Namespaced | 资源属于某个命名空间 | Pod, Deployment |
| Cluster | 集群级资源，不属命名空间 | Node, PV |

### CRD 注册后会发生什么？

1. K8s API Server 注册新的 REST 路径：`/apis/blog.example.com/v1/blogs`
2. `kubectl get blogs` 可以列出资源
3. `kubectl apply -f blog.yaml` 可以创建实例
4. 可以用 kubectl 对 CR 进行增删改查
""",
        key_fields=[
            {"name": "metadata.name", "description": "CRD 名称，格式: <plural>.<group>（强制校验）", "required": True, "example": "blogs.blog.example.com"},
            {"name": "spec.group", "description": "API 组名，自定义资源的命名空间", "required": True, "example": "blog.example.com"},
            {"name": "spec.names.kind", "description": "资源类型名（PascalCase）", "required": True, "example": "Blog"},
            {"name": "spec.names.plural", "description": "资源复数名（小写）", "required": True, "example": "blogs"},
            {"name": "spec.versions", "description": "API 版本列表", "required": True, "example": "[{name: v1, served: true, storage: true}]"},
            {"name": "spec.scope", "description": "资源作用域: Namespaced 或 Cluster", "required": True, "example": "Namespaced"},
        ],
        diagram="""\
  ┌─────────────── CRD ────────────────────┐
  │  kind: CustomResourceDefinition         │
  │  metadata:                              │
  │    name: blogs.blog.example.com  ◄── 格式校验
  │           ▲      ▲                      │
  │           │      └── spec.group         │
  │           └── spec.names.plural         │
  │  spec:                                  │
  │    group: blog.example.com              │
  │    names:                               │
  │      kind: Blog   ──────────────────┐   │
  │      plural: blogs                   │   │
  │      shortNames: [bl]                │   │
  │    scope: Namespaced                 │   │
  │    versions:                         │   │
  │    - name: v1                        │   │
  │      served: true                    │   │
  │      storage: true                   │   │
  └──────────────────────────────────────┼───┘
                                         │
              K8s API Server 注册新资源    │
                                         │
  ┌──────────────────────────────────────▼───┐
  │  /apis/blog.example.com/v1/blogs          │
  │                                           │
  │  kubectl get blogs      ← 列出 CR         │
  │  kubectl get blog <name> ← 查看单个 CR    │
  │  kubectl get bl         ← 简称也行        │
  └───────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: apiextensions.k8s.io/v1     # CRD API 版本
kind: CustomResourceDefinition          # 资源类型
metadata:                               # 元数据
  name: blogs.blog.example.com          # 必须是 <plural>.<group> 格式
spec:                                   # 规格定义
  group: blog.example.com               # API 组
  names:                                # 资源命名
    kind: Blog                          # 类型名（PascalCase）
    plural: blogs                       # 复数名
    singular: blog                      # 单数名
    shortNames:                         # kubectl 简称
    - bl
  scope: Namespaced                     # 命名空间级
  versions:                             # API 版本列表
  - name: v1                            # 版本名
    served: true                        # 是否提供服务
    storage: true                       # 是否为存储版本
""",
        common_errors=[
            "metadata.name 不是 <plural>.<group> 格式（如写成了 'blog' 而非 'blogs.blog.example.com'）",
            "metadata.name 的 plural 部分与 spec.names.plural 不一致",
            "spec.names.kind 没有用 PascalCase（如写成了 'blog' 而非 'Blog'）",
            "忘记 spec.versions 或 versions 为空",
            "scope 写成了小写 'namespaced'（必须首字母大写 'Namespaced'）",
        ],
        tips=[
            "用 kubectl get crd 查看集群中所有已注册的 CRD",
            "用 kubectl explain blog.spec 查看 CRD 定义的字段结构",
            "CRD 名称格式固定为 <plural>.<group>，这是 K8s 的硬性要求",
        ],
    ),
)


# ==================== Q17.2 CRD Schema 验证 ====================

def _check_172_crd_schema(user_yaml: str) -> CheckResult:
    """Q17.2 创建带 OpenAPI v3 Schema 验证的 CRD"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.customresourcedefinitions:
        return CheckResult(
            ok=False,
            error="没有创建任何 CustomResourceDefinition",
            hints=["你需要 apply 一个 kind: CustomResourceDefinition 的 YAML"],
        )

    crd_name = next(iter(state.customresourcedefinitions))
    crd = state.customresourcedefinitions[crd_name]
    spec = crd.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="CRD 缺少 spec", hints=[])

    versions = spec.get("versions", [])
    if not isinstance(versions, list) or not versions:
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.versions",
            hints=["至少需要一个版本定义"],
        )

    v0 = versions[0]
    if not isinstance(v0, dict):
        return CheckResult(ok=False, error="spec.versions[0] 格式错误", hints=[])

    # 检查 schema
    schema = v0.get("schema")
    if not isinstance(schema, dict):
        return CheckResult(
            ok=False,
            error="spec.versions[0] 缺少 schema",
            hints=["添加 schema.openAPIV3Schema 来定义验证规则"],
        )

    open_api_schema = schema.get("openAPIV3Schema")
    if not isinstance(open_api_schema, dict):
        return CheckResult(
            ok=False,
            error="schema 缺少 openAPIV3Schema",
            hints=["使用 schema.openAPIV3Schema 定义 OpenAPI v3 验证"],
        )

    # 检查 type
    if open_api_schema.get("type") != "object":
        return CheckResult(
            ok=False,
            error="openAPIV3Schema.type 应为 'object'",
            hints=["根 schema 的 type 必须是 object"],
        )

    # 检查 properties（必须有）
    properties = open_api_schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return CheckResult(
            ok=False,
            error="openAPIV3Schema 缺少 properties（必须定义字段结构）",
            hints=["在 properties 中定义 spec 等字段的验证规则"],
        )

    # 检查 spec 字段定义
    spec_prop = properties.get("spec")
    if not isinstance(spec_prop, dict):
        return CheckResult(
            ok=False,
            error="properties 缺少 spec 字段定义",
            hints=["在 properties.spec 中定义 spec 的验证规则"],
        )

    # 检查 spec 的子属性
    spec_props = spec_prop.get("properties")
    if not isinstance(spec_props, dict) or not spec_props:
        return CheckResult(
            ok=False,
            error="spec 的 properties 为空",
            hints=["在 spec.properties 中定义具体字段，如 title、author"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Schema 验证让 CRD 更安全！错误的数据会在提交时被拒绝 🛡️"],
    )


LEVEL_Q17_2 = Level(
    id="Q17.2",
    chapter="ch17",
    title="CRD Schema 验证",
    description="""
# CRD Schema 验证 🛡️

默认情况下，CR 接受任何 spec 内容。通过 **OpenAPI v3 Schema**，你可以定义字段类型、必填项和验证规则，让 K8s 在 API 层面拒绝无效数据。

## 任务

创建一个带 Schema 验证的 CRD：
- `spec.versions[0].schema.openAPIV3Schema` 定义验证规则
- 根 `type: object`
- `properties.spec` 包含 `title`（string, required）和 `author`（string）字段验证

## 提示

OpenAPI v3 Schema 类似 JSON Schema：
```yaml
versions:
- name: v1
  served: true
  storage: true
  schema:
    openAPIV3Schema:
      type: object
      properties:
        spec:
          type: object
          properties:
            title:
              type: string
          required: [title]
```
""",
    starter_yaml="""\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    # schema:
    #   openAPIV3Schema:
    #     type: object
    #     properties:
    #       spec:
    #         type: object
    #         properties:
    #           title:
    #             type: string
    #         required: [title]
""",
    check_fn=_check_172_crd_schema,
    lesson=Lesson(
        concept="""\
## OpenAPI v3 Schema 验证

从 K8s 1.16 开始，CRD **必须**提供 `schema.openAPIV3Schema`。它定义了 CR 的字段结构和验证规则。

### Schema 结构

```
openAPIV3Schema:
  type: object              # 根必须是 object
  properties:               # 定义字段
    spec:                   # spec 字段
      type: object
      properties:           # spec 的子字段
        title:
          type: string      # 类型
          minLength: 1      # 最小长度
          maxLength: 200    # 最大长度
        author:
          type: string
        status:
          type: string
          enum:             # 枚举值
          - draft
          - published
      required:             # 必填字段
      - title
```

### 常用验证规则

| 规则 | 适用类型 | 说明 |
|------|---------|------|
| type | 所有 | 数据类型: string/integer/boolean/object/array |
| required | object | 必填字段列表 |
| enum | string/integer | 枚举值 |
| minimum/maximum | integer | 数值范围 |
| minLength/maxLength | string | 字符串长度 |
| pattern | string | 正则匹配 |
| items | array | 数组元素 schema |
| properties | object | 子字段定义 |

### 验证示例

```yaml
# 这个 CR 会通过验证 ✅
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: valid-blog
spec:
  title: "Hello"      # 符合 type: string, required
  author: "dev"       # 符合 type: string

# 这个 CR 会被拒绝 ❌
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: invalid-blog
spec:
  author: "dev"       # 缺少 required: title
```

### 为什么需要 Schema？

1. **API 层面拦截**：无效数据在提交时就被拒绝，不会进入 etcd
2. **自动文档**：kubectl explain 自动从 schema 生成文档
3. **类型安全**：防止拼写错误、类型错误
4. **Operator 友好**：控制器可以信任 CR 数据的格式
""",
        key_fields=[
            {"name": "versions[].schema.openAPIV3Schema", "description": "OpenAPI v3 验证 schema", "required": True, "example": "{type: object, properties: {...}}"},
            {"name": "openAPIV3Schema.type", "description": "根类型，必须为 object", "required": True, "example": "object"},
            {"name": "openAPIV3Schema.properties", "description": "字段定义（必须非空）", "required": True, "example": "{spec: {type: object, properties: {...}}}"},
            {"name": "properties.spec.required", "description": "spec 必填字段列表", "required": False, "example": "[title]"},
        ],
        diagram="""\
  ┌─────── CRD Schema 验证 ─────────────────────┐
  │                                              │
  │  versions:                                   │
  │  - name: v1                                  │
  │    schema:                                   │
  │      openAPIV3Schema:                        │
  │        type: object                          │
  │        properties:  ◄── 必须非空             │
  │          spec:                               │
  │            type: object                      │
  │            properties:                       │
  │              title:  type: string ← 必填     │
  │              author: type: string            │
  │              status: type: string            │
  │                enum: [draft, published]      │
  │            required: [title]                 │
  └──────────────────┬───────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────────┐
  │            API Server 验证                   │
  │                                              │
  │  CR 提交时，API Server 用 schema 校验:       │
  │  ✅ title 存在且为 string  -> 通过           │
  │  ❌ 缺少 title             -> 拒绝 (400)     │
  │  ❌ status 值不在 enum 中   -> 拒绝 (400)    │
  └──────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:                          # Schema 验证
      openAPIV3Schema:               # OpenAPI v3
        type: object                 # 根类型
        properties:                  # 字段定义
          spec:                      # spec 字段
            type: object
            properties:              # spec 子字段
              title:                 # 标题
                type: string
                minLength: 1         # 最少 1 字符
              author:                # 作者
                type: string
              status:                # 状态
                type: string
                enum:                # 枚举
                - draft
                - published
            required:                # 必填字段
            - title
""",
        common_errors=[
            "忘记写 schema.openAPIV3Schema（K8s 1.16+ 强制要求）",
            "根 schema 的 type 不是 object",
            "openAPIV3Schema 缺少 properties 字段",
            "required 写在错误的层级（应该在 spec 下，不是根 schema 下）",
            "enum 值与 type 不匹配（如 type: string 但 enum 写了数字）",
        ],
        tips=[
            "用 kubectl explain blog.spec 查看 CRD schema 生成的文档",
            "Schema 验证在 API Server 层执行，不需要 Operator 参与",
            "x-kubernetes-preserve-unknown-fields: true 可以允许未定义的字段",
        ],
    ),
)


# ==================== Q17.3 Operator RBAC - Role + RoleBinding ====================

def _check_173_operator_rbac(user_yaml: str) -> CheckResult:
    """Q17.3 创建 Operator 所需的 Role 和 RoleBinding"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 Role 存在
    if not state.roles:
        return CheckResult(
            ok=False,
            error="缺少 Role（Operator 需要角色来操作集群资源）",
            hints=[
                "创建一个 Role，赋予 Operator 操作 Blog/Deployment/Service 的权限",
                "使用多文档 YAML（--- 分隔）同时创建 Role 和 RoleBinding",
            ],
        )

    # 检查 RoleBinding 存在
    if not state.rolebindings:
        return CheckResult(
            ok=False,
            error="缺少 RoleBinding（需要将 Role 绑定到 ServiceAccount）",
            hints=[
                "创建一个 RoleBinding，将 Role 绑定到 Operator 的 ServiceAccount",
                "RoleBinding 的 subjects 应指向 ServiceAccount",
            ],
        )

    # 检查 Role.rules 非空
    role = next(iter(state.roles.values()))
    rules = role.get("rules") or role.get("spec", {}).get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="Role.rules 为空（必须定义至少一条权限规则）",
            hints=[
                "在 rules 中定义 apiGroups、resources、verbs",
                "例如: apiGroups: ['blog.example.com'], resources: ['blogs'], verbs: ['get','list','watch','create','update','delete']",
            ],
        )

    # 检查每条 rule 有 apiGroups 和 verbs
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return CheckResult(
                ok=False,
                error=f"Role.rules[{i}] 格式错误（必须是映射）",
                hints=["每条 rule 应包含 apiGroups、resources、verbs"],
            )
        if not rule.get("apiGroups"):
            return CheckResult(
                ok=False,
                error=f"Role.rules[{i}] 缺少 apiGroups",
                hints=["apiGroups 指定可操作的 API 组，如 ['blog.example.com']"],
            )
        if not rule.get("verbs"):
            return CheckResult(
                ok=False,
                error=f"Role.rules[{i}] 缺少 verbs",
                hints=["verbs 指定允许的操作，如 ['get','list','watch','create','update','delete']"],
            )

    # 检查 RoleBinding.subjects 指向 ServiceAccount
    rb = next(iter(state.rolebindings.values()))
    subjects = rb.get("subjects", [])
    if not isinstance(subjects, list) or not subjects:
        return CheckResult(
            ok=False,
            error="RoleBinding 缺少 subjects（必须指定绑定的 ServiceAccount）",
            hints=[
                "subjects 中 kind 应为 ServiceAccount",
                "例如: subjects: [{kind: ServiceAccount, name: blog-operator-sa, namespace: default}]",
            ],
        )

    has_sa_subject = False
    for s in subjects:
        if isinstance(s, dict) and s.get("kind") == "ServiceAccount":
            if s.get("name"):
                has_sa_subject = True
                break

    if not has_sa_subject:
        return CheckResult(
            ok=False,
            error="RoleBinding.subjects 未指向 ServiceAccount",
            hints=[
                "Operator 通过 ServiceAccount 获取身份",
                "subjects 中需要 kind: ServiceAccount 且 name 非空",
            ],
        )

    # 检查 RoleBinding.roleRef 指向已创建的 Role
    role_ref = rb.get("roleRef", {})
    if isinstance(role_ref, dict):
        ref_name = role_ref.get("name", "")
        if ref_name and ref_name not in state.roles:
            return CheckResult(
                ok=False,
                error=f"RoleBinding.roleRef 指向的 Role '{ref_name}' 不存在",
                hints=["确保 RoleBinding 的 roleRef.name 与 Role 的 metadata.name 一致"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=["RBAC 配置正确！Operator 现在有了操作集群资源的权限 🔐"],
    )


LEVEL_Q17_3 = Level(
    id="Q17.3",
    chapter="ch17",
    title="Operator RBAC - Role + RoleBinding",
    description="""
# Operator RBAC - Role + RoleBinding 🔐

Operator 需要权限来操作集群资源（CRD 实例、Deployment、Service 等）。通过 **Role + RoleBinding**，你可以遵循最小权限原则，只授予 Operator 需要的权限。

## 任务

使用多文档 YAML 创建：
1. **Role** - 定义 Operator 可以执行的操作
   - `rules` 非空，包含 `apiGroups`、`resources`、`verbs`
   - 允许操作 `blog.example.com` 组的 `blogs` 资源
   - 允许操作 `apps` 组的 `deployments` 资源
2. **RoleBinding** - 将 Role 绑定到 ServiceAccount
   - `subjects` 指向 `kind: ServiceAccount`
   - `roleRef` 指向上面创建的 Role

## 提示

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: blog-operator-role
rules:
- apiGroups: ["blog.example.com"]
  resources: ["blogs"]
  verbs: ["get", "list", "watch", "create", "update", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
subjects:
- kind: ServiceAccount
  name: blog-operator-sa
roleRef:
  kind: Role
  name: blog-operator-role
  apiGroup: rbac.authorization.k8s.io
```
""",
    starter_yaml="""\
# --- Role ---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: blog-operator-role
# rules:
# - apiGroups: ["blog.example.com"]
#   resources: ["blogs"]
#   verbs: ["get", "list", "watch", "create", "update", "delete"]
---
# --- RoleBinding ---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
# subjects:
# - kind: ServiceAccount
#   name: blog-operator-sa
# roleRef:
#   kind: Role
#   name: blog-operator-role
#   apiGroup: rbac.authorization.k8s.io
""",
    check_fn=_check_173_operator_rbac,
    lesson=Lesson(
        concept="""\
## Operator RBAC 权限管理

Operator 以 Deployment 形式运行，通过 **ServiceAccount** 获取身份，通过 **Role + RoleBinding** 获取权限。没有正确的 RBAC 配置，Operator 将无法操作集群资源。

### RBAC 四件套

```
┌─────────────── Operator RBAC 架构 ───────────────┐
│                                                   │
│  ServiceAccount          Role                     │
│  ┌──────────────┐       ┌──────────────────────┐ │
│  │ blog-op-sa   │       │ rules:               │ │
│  │ (身份)       │       │ - apiGroups: [blog..]│ │
│  └──────┬───────┘       │   resources: [blogs] │ │
│         │               │   verbs: [get,list..] │ │
│         │               └──────────┬───────────┘ │
│         │                          │             │
│         │      RoleBinding         │             │
│         │      ┌───────────────┐   │             │
│         └─────►│ subjects: [SA]│───┘             │
│                │ roleRef: Role │                 │
│                └───────────────┘                 │
│                                                   │
│  Deployment                                      │
│  ┌──────────────────────────────────────────────┐│
│  │ spec.template.spec.serviceAccountName: sa    ││
│  └──────────────────────────────────────────────┘│
└───────────────────────────────────────────────────┘
```

### Role.rules 结构

每条 rule 包含三个核心字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| apiGroups | API 组列表 | ["blog.example.com", "apps"] |
| resources | 资源类型列表 | ["blogs", "deployments", "services"] |
| verbs | 允许的操作 | ["get", "list", "watch", "create", "update", "delete"] |

常用 verbs：`get`, `list`, `watch`, `create`, `update`, `patch`, `delete`

### RoleBinding.subjects

subjects 指定将 Role 绑定给谁：

```yaml
subjects:
- kind: ServiceAccount          # 必须指向 SA
  name: blog-operator-sa        # SA 名称
  namespace: default            # 命名空间
```

### 最小权限原则

- 只授予 Operator **实际需要**的权限
- 不要使用 ClusterRole 除非确实需要集群级权限
- verbs 中 `watch` 是 Operator 必需的（用于监听资源变化）
- 生产环境应避免使用 `*` 通配符
""",
        key_fields=[
            {"name": "Role.rules", "description": "权限规则列表（必须非空）", "required": True, "example": "[{apiGroups: [blog.example.com], resources: [blogs], verbs: [get,list,watch,create,update,delete]}]"},
            {"name": "Role.rules[].apiGroups", "description": "可操作的 API 组", "required": True, "example": "[blog.example.com]"},
            {"name": "Role.rules[].verbs", "description": "允许的操作", "required": True, "example": "[get,list,watch,create,update,delete]"},
            {"name": "RoleBinding.subjects", "description": "绑定目标（必须指向 ServiceAccount）", "required": True, "example": "[{kind: ServiceAccount, name: blog-operator-sa}]"},
            {"name": "RoleBinding.roleRef", "description": "引用的 Role", "required": True, "example": "{kind: Role, name: blog-operator-role}"},
        ],
        diagram="""\
  ┌─────────── Operator RBAC 数据流 ───────────────┐
  │                                                 │
  │  1. ServiceAccount (blog-operator-sa)           │
  │     └─► Deployment.spec.template.spec           │
  │         .serviceAccountName = "blog-operator-sa"│
  │                                                 │
  │  2. Role (blog-operator-role)                   │
  │     └─► rules:                                  │
  │         - apiGroups: [blog.example.com]         │
  │           resources: [blogs]                    │
  │           verbs: [get, list, watch, ...]        │
  │         - apiGroups: [apps]                     │
  │           resources: [deployments]              │
  │           verbs: [get, list, watch, create,...] │
  │                                                 │
  │  3. RoleBinding (blog-operator-binding)         │
  │     └─► subjects: [{kind: SA, name: ...}]  ──┐  │
  │     └─► roleRef: {kind: Role, name: ...}  ───┤  │
  │                                              │  │
  │     ServiceAccount ◄────────────────────────┘  │
  │           +                                    │
  │     Role ──────────────────────────────────────┘
  │           = Operator 有了操作 Blog/Deployment 的权限
  └─────────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- Role ---
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API
kind: Role                                 # 命名空间级角色
metadata:
  name: blog-operator-role                 # 角色名
rules:                                     # 权限规则（必须非空）
- apiGroups: ["blog.example.com"]          # API 组
  resources: ["blogs"]                     # 资源类型
  verbs: ["get", "list", "watch",          # 允许的操作
          "create", "update", "delete"]
- apiGroups: ["apps"]                      # 操作 Deployment
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "delete"]
- apiGroups: [""]
  resources: ["services"]
  verbs: ["get", "list", "watch", "create", "update", "delete"]
---
# --- RoleBinding ---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
subjects:                                  # 绑定目标
- kind: ServiceAccount                     # 必须指向 SA
  name: blog-operator-sa
  namespace: default
roleRef:                                   # 引用的 Role
  kind: Role
  name: blog-operator-role
  apiGroup: rbac.authorization.k8s.io
""",
        common_errors=[
            "Role.rules 为空或缺失（Operator 无法操作任何资源）",
            "RoleBinding.subjects 的 kind 不是 ServiceAccount",
            "RoleBinding.roleRef.name 与 Role 的 metadata.name 不匹配",
            "忘记在 verbs 中包含 watch（Operator 需要监听资源变化）",
            "apiGroups 写错（core 资源如 Service 的 apiGroup 是空字符串 ''）",
        ],
        tips=[
            "用 kubectl auth can-i --list --as=system:serviceaccount:default:blog-operator-sa 检查权限",
            "生产环境建议使用 ClusterRole + ClusterRoleBinding 管理集群级 CRD 资源",
            "verbs 中的 watch 是 Operator 工作的基础——它通过 watch 监听 CR 变化",
        ],
    ),
)


# ==================== Q17.4 Status 子资源 + Deployment WATCH ====================

def _check_174_status_subresource(user_yaml: str) -> CheckResult:
    """Q17.4 CRD 启用 Status 子资源 + Operator Deployment 含 WATCH 环境变量"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 CRD 存在
    if not state.customresourcedefinitions:
        return CheckResult(
            ok=False,
            error="缺少 CustomResourceDefinition",
            hints=["需要创建一个 CRD 并启用 status 子资源"],
        )

    # 检查 CRD 有 versions[].subresources.status
    crd_name = next(iter(state.customresourcedefinitions))
    crd = state.customresourcedefinitions[crd_name]
    crd_spec = crd.get("spec", {})
    if not isinstance(crd_spec, dict):
        return CheckResult(ok=False, error="CRD 缺少 spec", hints=[])

    versions = crd_spec.get("versions", [])
    if not isinstance(versions, list) or not versions:
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.versions",
            hints=["CRD 需要定义至少一个 API 版本"],
        )

    v0 = versions[0]
    if not isinstance(v0, dict):
        return CheckResult(ok=False, error="spec.versions[0] 格式错误", hints=[])

    # subresources 在 versions[0] 下（K8s API 规范）
    subresources = v0.get("subresources")
    if not isinstance(subresources, dict):
        return CheckResult(
            ok=False,
            error="versions[0] 缺少 subresources（需要启用 status 子资源）",
            hints=["添加 versions[].subresources.status: {} 来启用 status 子资源"],
        )

    status_sub = subresources.get("status")
    if status_sub is None:
        return CheckResult(
            ok=False,
            error="subresources 缺少 status 字段",
            hints=["添加 subresources.status: {} 来启用 status 子资源"],
        )

    # 检查 Deployment 存在
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="缺少 Deployment（Operator 控制器）",
            hints=["创建一个 Deployment 运行 Operator 控制器"],
        )

    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {})
    if not isinstance(dep_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = dep_spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Deployment 缺少 containers", hints=[])

    # 检查至少一个容器有 WATCH_NAMESPACE 环境变量
    has_watch_env = False
    for c in containers:
        if not isinstance(c, dict):
            continue
        env = c.get("env", [])
        if isinstance(env, list):
            for e in env:
                if isinstance(e, dict):
                    name = e.get("name", "")
                    if isinstance(name, str) and name == "WATCH_NAMESPACE":
                        has_watch_env = True
                        break
        if has_watch_env:
            break

    if not has_watch_env:
        return CheckResult(
            ok=False,
            error="Operator 容器缺少 WATCH_NAMESPACE 环境变量",
            hints=[
                "Operator 通过 WATCH_NAMESPACE 环境变量配置监听范围",
                "添加 env: [{name: WATCH_NAMESPACE, value: \"\"}]",
            ],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Status 子资源已启用！Operator 可以安全地更新 CR 状态了 📊"],
    )


LEVEL_Q17_4 = Level(
    id="Q17.4",
    chapter="ch17",
    title="Status 子资源与 Operator Deployment",
    description="""
# Status 子资源与 Operator Deployment 📊

**Status 子资源** 是 CRD 的重要特性：它将 spec（用户期望）和 status（实际状态）分离，防止 Operator 意外覆盖用户配置。

## 任务

使用多文档 YAML 创建：

1. **CRD** - 启用 status 子资源
   - `spec.subresources.status: {}` 启用 /status 端点
   - 包含基本的 schema 定义

2. **Deployment** - Operator 控制器
   - 容器包含 `WATCH_NAMESPACE` 环境变量
   - image: `operator-sdk/example-operator:v1`

## 提示

```yaml
# --- CRD ---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
          status:
            type: object
            properties:
              phase:
                type: string
    subresources:
      status: {}
---
# --- Deployment ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE
          value: ""
```
""",
    starter_yaml="""\
# --- CRD ---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
  # subresources:
  #   status: {}
---
# --- Deployment ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        # env:
        # - name: WATCH_NAMESPACE
        #   value: ""
""",
    check_fn=_check_174_status_subresource,
    lesson=Lesson(
        concept="""\
## Status 子资源

默认情况下，CR 的 spec 和 status 通过同一个 API 端点读写。这意味着 Operator 更新 status 时可能会意外覆盖 spec。**Status 子资源** 解决了这个问题。

### 启用 Status 子资源

在 CRD 的 `spec.subresources` 中启用：

```yaml
spec:
  subresources:
    status: {}    # 启用 /status 子资源
```

启用后：
- `PUT /apis/blog.example.com/v1/namespaces/default/blogs/my-blog/status` 只能更新 status
- `PUT /apis/blog.example.com/v1/namespaces/default/blogs/my-blog` 只能更新 spec/metadata
- **spec 和 status 完全隔离**

### 为什么需要 Status 子资源？

```
没有 status 子资源：                      有 status 子资源：
┌────────────────────┐                   ┌────────────────────┐
│ PUT /blogs/my-blog │                   │ PUT /blogs/my-blog │
│  body: {           │                   │  body: {           │
│    spec: {...},    │                   │    spec: {...}     │ ← 只能改 spec
│    status: {...}   │ ← 全部覆盖        │  }                 │
│  }                 │                   │                    │
└────────────────────┘                   │ PUT /blogs/my-blog │
                                         │      /status       │
  问题：Operator 更新 status             │  body: {           │
  时可能意外覆盖 spec！                   │    status: {...}   │ ← 只能改 status
                                         │  }                 │
                                         └────────────────────┘
                                           spec 和 status 隔离 ✅
```

### Operator 更新 Status 的流程

```python
# Operator 代码中更新 status
cr = get_blog(name)
cr["status"]["phase"] = "Ready"
cr["status"]["conditions"] = [...]

# 通过 status 子资源更新（不会影响 spec）
api.put_status(cr)
```

### WATCH_NAMESPACE 环境变量

Operator 控制器通过 `WATCH_NAMESPACE` 环境变量决定监听范围：

| 值 | 行为 |
|------|------|
| "" (空) | 监听所有命名空间 |
| "default" | 只监听 default 命名空间 |
| "ns1,ns2" | 监听多个命名空间 |

这是 Operator SDK 和 kubebuilder 的标准约定。
""",
        key_fields=[
            {"name": "spec.subresources.status", "description": "启用 status 子资源（值为空对象 {}）", "required": True, "example": "{}"},
            {"name": "Deployment.containers[].env", "description": "环境变量，必须包含 WATCH_NAMESPACE", "required": True, "example": "[{name: WATCH_NAMESPACE, value: \"\"}]"},
            {"name": "schema.openAPIV3Schema.properties.status", "description": "status 字段的 schema 定义", "required": False, "example": "{type: object, properties: {phase: {type: string}}}"},
        ],
        diagram="""\
  ┌─────────────── Status 子资源工作流 ──────────────────┐
  │                                                       │
  │  CRD spec:                                            │
  │    subresources:                                      │
  │      status: {}  ◄── 启用 /status 端点               │
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │              Blog CR (my-blog)                  │ │
  │  │  ┌─────────────┐    ┌──────────────────────┐   │ │
  │  │  │   spec      │    │      status          │   │ │
  │  │  │  title: Hi  │    │  phase: Ready        │   │ │
  │  │  │  author: dev│    │  conditions: [...]   │   │ │
  │  │  └──────┬──────┘    └─────────┬────────────┘   │ │
  │  └─────────┼─────────────────────┼────────────────┘ │
  │            │                     │                  │
  │     PUT /blogs/my-blog    PUT /blogs/my-blog/status │
  │     (用户更新 spec)        (Operator 更新 status)    │
  │            │                     │                  │
  │     ✅ 不影响 status       ✅ 不影响 spec            │
  └─────────────────────────────────────────────────────┘

  ┌─────────────── Operator Deployment ──────────────────┐
  │  containers:                                         │
  │  - name: operator                                    │
  │    image: operator-sdk/example-operator:v1           │
  │    env:                                              │
  │    - name: WATCH_NAMESPACE  ◄── 监听范围配置         │
  │      value: ""                (空 = 所有命名空间)    │
  └──────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- CRD ---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
          status:                           # status schema
            type: object
            properties:
              phase:
                type: string
              conditions:
                type: array
                items:
                  type: object
    subresources:                           # 子资源
      status: {}                            # 启用 status 子资源
---
# --- Deployment ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE             # 监听范围
          value: ""                         # 空 = 所有命名空间
""",
        common_errors=[
            "忘记添加 spec.subresources.status（status 子资源未启用）",
            "spec.subresources.status 写成了 true 而非 {}（应为空对象）",
            "WATCH_NAMESPACE 环境变量缺失或值不正确",
            "schema 中没有定义 status 字段（建议定义以便类型校验）",
            "多文档 YAML 忘记用 --- 分隔 CRD 和 Deployment",
        ],
        tips=[
            "启用 status 子资源后，kubectl get blog -o yaml 会分别显示 spec 和 status",
            "Status 子资源还支持 spec.subresources.scale 用于自定义扩缩容",
            "WATCH_NAMESPACE 环境变量是 Operator SDK 的标准约定",
        ],
    ),
)


# ==================== Q17.5 Operator Deployment 完整校验 ====================

def _check_175_deploy_operator(user_yaml: str) -> CheckResult:
    """Q17.5 集群实战 - 部署完整的 Operator 栈（CRD + SA + Deployment）"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 CRD
    if not state.customresourcedefinitions:
        return CheckResult(
            ok=False,
            error="缺少 CustomResourceDefinition",
            hints=["一个完整的 Operator 部署需要 CRD + SA + Deployment"],
        )

    # 检查 ServiceAccount
    if not state.serviceaccounts:
        return CheckResult(
            ok=False,
            error="缺少 ServiceAccount",
            hints=["Operator 需要专用 ServiceAccount 来操作集群资源"],
        )

    # 检查 Deployment
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="缺少 Deployment（控制器）",
            hints=["Operator 控制器以 Deployment 形式运行"],
        )

    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {})
    if not isinstance(dep_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    # 检查 replicas == 1
    replicas = dep_spec.get("replicas", 1)
    if not isinstance(replicas, int) or isinstance(replicas, bool):
        return CheckResult(
            ok=False,
            error="Deployment spec.replicas 必须是整数",
            hints=["Operator 通常只需 1 个副本"],
        )
    if replicas != 1:
        return CheckResult(
            ok=False,
            error=f"Deployment replicas 应为 1，实际为 {replicas}",
            hints=["Operator 控制器通常只需 1 个副本（除非需要高可用 leader election）"],
        )

    # 检查 Deployment 使用了 ServiceAccount
    template = dep_spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

    sa_name = tmpl_spec.get("serviceAccountName", "")
    if not sa_name or not isinstance(sa_name, str):
        return CheckResult(
            ok=False,
            error="Deployment 未指定 serviceAccountName",
            hints=["在 Pod 模板中设置 spec.serviceAccountName 引用 ServiceAccount"],
        )

    if sa_name not in state.serviceaccounts:
        return CheckResult(
            ok=False,
            error=f"Deployment 引用的 ServiceAccount '{sa_name}' 不存在",
            hints=["确保 ServiceAccount 名称与 Deployment 中引用的一致"],
        )

    # 检查容器有 image 和 WATCH_NAMESPACE 环境变量
    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Deployment 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    if not c.get("image"):
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["Operator 控制器需要指定 image"],
        )

    # 检查 WATCH_NAMESPACE 环境变量
    env = c.get("env", [])
    has_watch_env = False
    if isinstance(env, list):
        for e in env:
            if isinstance(e, dict):
                name = e.get("name", "")
                if isinstance(name, str) and name == "WATCH_NAMESPACE":
                    has_watch_env = True
                    break

    if not has_watch_env:
        return CheckResult(
            ok=False,
            error="Operator 容器缺少 WATCH_NAMESPACE 环境变量",
            hints=[
                "Operator 控制器通过环境变量配置监听范围 💡",
                "添加 env: [{name: WATCH_NAMESPACE, value: \"\"}]",
            ],
        )

    # 检查 CRD 有 versions
    crd_name = next(iter(state.customresourcedefinitions))
    crd = state.customresourcedefinitions[crd_name]
    crd_spec = crd.get("spec", {})
    versions = crd_spec.get("versions", [])
    if not isinstance(versions, list) or not versions:
        return CheckResult(
            ok=False,
            error="CRD 缺少 spec.versions",
            hints=["CRD 需要定义至少一个 API 版本"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "完整的 Operator 栈已就绪！",
            "  CRD + SA + Deployment 全部校验通过 ✅",
            "在真实集群上执行：",
            "  kubectl apply -f operator-stack.yaml",
            "  kubectl get crd          # 查看注册的 CRD",
            "  kubectl get pods         # 查看 Operator 运行状态",
            "  kubectl logs <operator-pod>  # 查看 Reconcile 日志",
        ],
    )


LEVEL_Q17_5 = Level(
    id="Q17.5",
    chapter="ch17",
    title="集群实战: 部署完整 Operator 栈",
    description="""
# 集群实战: 部署完整 Operator 栈 🚀

部署一个完整的 Operator 栈：CRD + ServiceAccount + Deployment，所有组件协同工作。

## 任务

使用多文档 YAML（`---` 分隔）创建：
1. **CustomResourceDefinition** - 定义 Blog 资源类型
2. **ServiceAccount** - Operator 使用的身份
3. **Deployment** - Operator 控制器

## 要求

- CRD: group=`blog.example.com`, kind=`Blog`, versions 含 `v1`
- ServiceAccount: name=`blog-operator-sa`
- Deployment:
  - `replicas: 1`
  - `serviceAccountName: blog-operator-sa`（引用上面的 SA）
  - image=`operator-sdk/example-operator:v1`
  - env 包含 `WATCH_NAMESPACE`

## 验证步骤

```bash
# 部署
kubectl apply -f operator-stack.yaml

# 检查 CRD
kubectl get crd blogs.blog.example.com

# 检查 Operator 运行状态
kubectl get pods -l app=blog-operator

# 查看日志
kubectl logs -l app=blog-operator -f

# 创建 Blog 实例测试
kubectl apply -f - <<EOF
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: test-blog
spec:
  title: "Test"
EOF

# 查看 Operator 是否响应
kubectl get blog test-blog -o yaml
```
""",
    starter_yaml="""\
# --- CRD ---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  # 补全 group, names, versions, scope
# ---
# apiVersion: v1
# kind: ServiceAccount
# metadata:
#   name: blog-operator-sa
# ---
# apiVersion: apps/v1
# kind: Deployment
# metadata:
#   name: blog-operator
# spec:
#   replicas: 1
#   selector:
#     matchLabels:
#       app: blog-operator
#   template:
#     metadata:
#       labels:
#         app: blog-operator
#     spec:
#       # serviceAccountName: blog-operator-sa
#       containers:
#       - name: operator
#         # image: operator-sdk/example-operator:v1
#         env:
#         - name: WATCH_NAMESPACE
#           value: ""
""",
    check_fn=_check_175_deploy_operator,
    lesson=Lesson(
        concept="""\
## 部署完整的 Operator

一个生产级的 Operator 部署通常包含多个资源，它们协同工作形成完整的自动化系统。

### Operator 栈的组成

```
┌─────────────────── Operator 部署栈 ───────────────────┐
│                                                        │
│  1. CRD          定义自定义资源类型 (Blog)              │
│     └─► 注册到 API Server                              │
│                                                        │
│  2. ServiceAccount  Operator 的身份标识                 │
│     └─► 用于 RBAC 权限控制                             │
│                                                        │
│  3. Role/RoleBinding  赋予 Operator 操作权限           │
│     └─► 允许 CRUD Blog/Deployment/Service 等           │
│                                                        │
│  4. Deployment    运行控制器代码                        │
│     └─► 使用 SA 身份，监听 CR 变化                     │
│     └─► replicas: 1（通常只需 1 个副本）               │
│                                                        │
│  5. (可选) CR     创建实例触发 Operator 工作           │
│     └─► Operator 检测到后自动创建子资源                 │
└────────────────────────────────────────────────────────┘
```

### ServiceAccount 的作用

Operator 需要操作集群资源（创建 Pod、Service 等），这需要权限。
ServiceAccount 是 Operator 的"身份证"，配合 RBAC 使用：

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: blog-operator-sa

# Deployment 引用 SA
spec:
  template:
    spec:
      serviceAccountName: blog-operator-sa  # 绑定身份
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
```

### replicas: 1 的原因

Operator 控制器通常设为 `replicas: 1`：
- 多个副本会同时监听同一资源，导致重复操作
- 如需高可用，使用 **Leader Election**（选主机制），而非简单增加副本
- Operator SDK / kubebuilder 默认支持 leader election

### 多文档 YAML

用 `---` 分隔多个资源，一次部署：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: blog-operator-sa
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
# ...
```

### 生产环境最佳实践

1. **最小权限**：只授予 Operator 需要的权限
2. **健康检查**：添加 livenessProbe/readinessProbe
3. **资源限制**：设置 resources.limits 防止资源泄漏
4. **优雅升级**：配置 strategy 滚动更新策略
5. **监控**：暴露 metrics 端点供 Prometheus 采集
6. **Leader Election**：高可用场景下启用选主机制
""",
        key_fields=[
            {"name": "CustomResourceDefinition", "description": "定义自定义资源类型", "required": True, "example": "blogs.blog.example.com"},
            {"name": "ServiceAccount", "description": "Operator 的身份标识", "required": True, "example": "blog-operator-sa"},
            {"name": "Deployment.spec.replicas", "description": "副本数，通常为 1", "required": True, "example": "1"},
            {"name": "Deployment.spec.template.spec.serviceAccountName", "description": "Pod 使用的 SA（必须与 SA 名称一致）", "required": True, "example": "blog-operator-sa"},
            {"name": "Deployment.spec.template.spec.containers[].image", "description": "控制器镜像", "required": True, "example": "operator-sdk/example-operator:v1"},
            {"name": "Deployment.spec.template.spec.containers[].env", "description": "环境变量，必须含 WATCH_NAMESPACE", "required": True, "example": "[{name: WATCH_NAMESPACE, value: \"\"}]"},
        ],
        diagram="""\
  ┌─────────── Operator 部署流程 ──────────────────────┐
  │                                                     │
  │  kubectl apply -f operator-stack.yaml               │
  │         │                                           │
  │         ▼                                           │
  │  ┌─────────────────────────────────────────────┐    │
  │  │              多文档 YAML                     │    │
  │  │  ---                                         │    │
  │  │  CRD: blogs.blog.example.com                 │    │
  │  │  ---                                         │    │
  │  │  SA: blog-operator-sa                        │    │
  │  │  ---                                         │    │
  │  │  Deployment: blog-operator                   │    │
  │  │    replicas: 1                               │    │
  │  │    serviceAccountName: blog-operator-sa      │    │
  │  │    env: WATCH_NAMESPACE=""                   │    │
  │  └──────────────────┬──────────────────────────┘    │
  │                     │                               │
  │     ┌───────────────┼───────────────┐               │
  │     ▼               ▼               ▼               │
  │  ┌──────┐     ┌──────────┐    ┌──────────┐         │
  │  │ CRD  │     │   SA     │    │   Pod    │         │
  │  │注册   │     │ (身份)   │    │(控制器)  │         │
  │  └──────┘     └──────────┘    └────┬─────┘         │
  │                                    │               │
  │                          Watch ◄───┘               │
  │                            │                        │
  │                    用户创建 Blog CR                 │
  │                            │                        │
  │                    Reconcile Loop                   │
  │                    创建子资源                        │
  └─────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- CRD ---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
            required: [title]
---
# --- ServiceAccount ---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: blog-operator-sa
---
# --- Deployment ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1                          # 通常 1 个副本
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      serviceAccountName: blog-operator-sa   # 绑定 SA
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE        # 监听范围
          value: ""                    # 空 = 所有命名空间
""",
        common_errors=[
            "多文档 YAML 忘记用 --- 分隔",
            "Deployment 的 serviceAccountName 与 ServiceAccount 名称不匹配",
            "CRD 的 versions 缺少 schema（K8s 1.16+ 强制要求）",
            "忘记在 Deployment 的 Pod 模板中设置 serviceAccountName",
            "replicas 设为 0 或大于 1（Operator 通常只需 1 个副本）",
        ],
        tips=[
            "用 kubectl get crd,sa,deploy 一次性查看所有部署的资源",
            "生产环境还应添加 Role + RoleBinding 赋予 SA 权限",
            "用 kubectl describe deploy blog-operator 检查 SA 是否正确挂载",
        ],
    ),
)


# ==================== Q17.6 Reconcile 循环骨架 ====================

def _check_176_reconcile_loop(user_yaml: str) -> CheckResult:
    """Q17.6 Reconcile 循环骨架 - 验证 CR 的 status 字段符合 Reconcile 循环写入的模式"""
    try:
        docs = list(yaml.safe_load_all(user_yaml))
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])
    except RecursionError:
        return CheckResult(ok=False, error="YAML 嵌套层级过深", hints=[])

    for doc in docs:
        if doc is None or not isinstance(doc, dict):
            continue

        status = doc.get("status")
        if not isinstance(status, dict):
            continue

        # 验证: status.conditions 是列表，每项有 type/status/lastTransitionTime
        conditions = status.get("conditions")
        if not isinstance(conditions, list):
            return CheckResult(
                ok=False,
                error="status.conditions 必须是列表（Reconcile 循环通过 conditions 报告状态）",
                hints=[
                    "Reconcile 循环会将处理结果写入 status.conditions",
                    "conditions 是一个列表，每项包含 type/status/lastTransitionTime",
                    "示例: status:\\n  conditions:\\n  - type: Ready\\n    status: \"True\"\\n    lastTransitionTime: \"2024-01-01T00:00:00Z\"",
                ],
            )

        if not conditions:
            return CheckResult(
                ok=False,
                error="status.conditions 是空列表（需要至少一个 condition）",
                hints=["Reconcile 循环至少会写入一个 condition 来反映处理结果"],
            )

        required_cond_fields = ["type", "status", "lastTransitionTime"]
        for i, cond in enumerate(conditions):
            if not isinstance(cond, dict):
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}] 必须是映射（dict）",
                    hints=["每个 condition 是一个对象"],
                )
            missing = [f for f in required_cond_fields if not cond.get(f)]
            if missing:
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}] 缺少必需字段: {', '.join(missing)}",
                    hints=[
                        "每个 condition 必须包含: type, status, lastTransitionTime",
                        "这些字段由 Reconcile 循环在处理 CR 时写入",
                    ],
                )

        # 验证: status.observedGeneration 存在（表示 controller 已处理）
        observed_gen = status.get("observedGeneration")
        if observed_gen is None:
            return CheckResult(
                ok=False,
                error="status 缺少 observedGeneration 字段（表示 controller 已处理当前 generation）",
                hints=[
                    "observedGeneration 表示 Controller 已经观察并处理了 CR 的第几代版本",
                    "当用户更新 spec 时，metadata.generation 会递增",
                    "Controller 处理后会更新 status.observedGeneration，使其与 generation 一致",
                    "示例: status:\\n  observedGeneration: 1",
                ],
            )

        return CheckResult(
            ok=True, state=ClusterState(),
            hints=[
                "CR 的 status 结构符合 Reconcile 循环写入的模式 🔄",
                f"  conditions: {len(conditions)} 个, observedGeneration: {observed_gen}",
                "水平触发 + 优雅退出 + Requeue 是 Operator 可靠性的基石",
            ],
        )

    return CheckResult(
        ok=False,
        error="未找到有效的 status 字段（Reconcile 循环会通过 status 子资源写入处理结果）",
        hints=[
            "提交一个包含 status 字段的 CR YAML",
            "status 应包含 conditions 列表和 observedGeneration",
            "示例:\napiVersion: blog.example.com/v1\nkind: Blog\nmetadata:\n  name: my-blog\nspec:\n  title: Hello\nstatus:\n  observedGeneration: 1\n  conditions:\n  - type: Ready\n    status: \"True\"\n    lastTransitionTime: \"2024-01-01T00:00:00Z\"",
        ],
    )


LEVEL_Q17_6 = Level(
    id="Q17.6",
    chapter="ch17",
    title="Reconcile 循环骨架",
    description="""
# Reconcile 循环骨架 🔄

Reconcile 循环是 Operator 的核心。理解它如何通过 status 字段反映处理结果是掌握 Operator 开发的基础。

## 代码示例

以下是一个典型的 Reconcile 函数骨架：

```python
def Reconcile(ctx, req):
    # 1. Watch: 获取 CR 当前状态
    blog = get_blog(req.name)
    if blog is NotFound:
        return Result{}  # 优雅退出：资源已删除

    # 2. Compare: 比较期望状态与实际状态
    desired_deploy = make_deploy(blog)
    actual_deploy = get_deploy(blog.name)
    if actual_deploy != desired_deploy:
        # 3. Act: 执行操作使实际状态趋近期望状态
        update_deploy(desired_deploy)

    # 如果有 error，返回 error 并 requeue
    if error:
        return Result{requeue: true}

    return Result{}  # 完成，等待下一次事件
```

## 任务

Reconcile 循环处理完 CR 后，会通过 `/status` 子资源写入处理结果。请提交一个 **Blog CR YAML**，其 `status` 字段需要符合 Reconcile 循环写入的模式：

- `status.conditions` 是列表，每项包含 `type`、`status`、`lastTransitionTime`
- `status.observedGeneration` 存在（表示 controller 已处理当前 generation）

## 提示

```yaml
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
```
""",
    starter_yaml="""\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
# status:
#   observedGeneration: 1
#   conditions:
#   - type: Ready
#     status: "True"
#     lastTransitionTime: "2024-01-01T00:00:00Z"
""",
    check_fn=_check_176_reconcile_loop,
    lesson=Lesson(
        concept="""\
## Reconcile 循环详解

Reconcile 循环是 Kubernetes 控制器的核心设计模式。它不是事件驱动的，而是**状态驱动**的——每次执行都试图将实际状态调整到期望状态。

### 水平触发 vs 边沿触发

```
边沿触发（事件驱动）：              水平触发（状态驱动 / Reconcile）：
┌────────────────────┐             ┌────────────────────┐
│ 事件发生 -> 执行一次│             │ 检查状态            │
│ 如果错过事件，永远   │             │   不一致？ -> 修复  │
│ 不会重试            │             │   一致？ -> 等待    │
│                    │             │                    │
│ 问题：容错性差      │             │ 优势：自动恢复      │
│ 事件丢失 = 状态漂移 │             │ 即使错过事件也能修复│
└────────────────────┘             └────────────────────┘
```

K8s 控制器使用**水平触发**：不关心"发生了什么事件"，只关心"当前状态对不对"。

### Reconcile 的三个关键步骤

```
┌─────────────────────────────────────────────┐
│           Reconcile(req)                     │
│                                              │
│  1. Watch（监听/获取状态）                    │
│     └─ 获取 CR 和相关资源的当前状态           │
│     └─ 如果 NotFound -> 优雅退出             │
│                                              │
│  2. Compare（比较）                          │
│     └─ 比较 期望状态（CR spec）vs 实际状态    │
│     └─ 一致？-> 返回，等待下次事件           │
│                                              │
│  3. Act（操作）                              │
│     └─ 不一致 -> 创建/更新/删除子资源        │
│     └─ 更新 CR status                       │
│                                              │
│  4. Requeue（重新排队）                      │
│     └─ 如果有 error -> requeue 重试          │
│     └─ 如果需要定期检查 -> requeueAfter      │
└─────────────────────────────────────────────┘
```

### NotFound 优雅退出

```python
blog = get_blog(req.name)
if blog is NotFound:
    # 资源已被删除，子资源应该已被垃圾回收
    # （如果设置了 OwnerReference）
    return Result{}  # 正常退出，不报错
```

这是水平触发的优势：即使错过了删除事件，下次 Reconcile 时发现资源不存在就会正常退出。

### Requeue 机制

```python
# 错误时自动 requeue
if err:
    return Result{requeue: True}

# 定期 requeue（如每 5 分钟检查一次）
return Result{requeueAfter: 300}  # 300 秒后重试
```

Requeue 确保了：
- 临时错误（如 API 不可用）会自动重试
- 需要定期检查的场景（如证书过期）能持续运行
- Operator 重启后能自动恢复所有 CR 的状态
""",
        key_fields=[
            {"name": "Watch", "description": "获取 CR 和相关资源的当前状态", "required": True, "example": "get_blog(name) -> NotFound 则优雅退出"},
            {"name": "Compare", "description": "比较期望状态与实际状态", "required": True, "example": "desired != actual -> 需要操作"},
            {"name": "Act", "description": "执行操作使实际状态趋近期望状态", "required": True, "example": "create/update/delete 子资源"},
            {"name": "Requeue", "description": "错误或定期检查时重新排队", "required": True, "example": "Result{requeue: true} 或 Result{requeueAfter: 300}"},
        ],
        diagram="""\
  ┌──────────────── Reconcile 循环 ────────────────────┐
  │                                                     │
  │   ┌──────────┐                                     │
  │   │  Watch   │ ← 获取 CR + 子资源状态              │
  │   │ (获取)   │   NotFound? → 优雅退出              │
  │   └────┬─────┘                                     │
  │        │                                           │
  │        ▼                                           │
  │   ┌──────────┐                                     │
  │   │ Compare  │ ← 期望状态 vs 实际状态              │
  │   │ (比较)   │   一致? → 返回（等待下次事件）      │
  │   └────┬─────┘                                     │
  │        │ 不一致                                    │
  │        ▼                                           │
  │   ┌──────────┐                                     │
  │   │   Act    │ ← 创建/更新/删除子资源              │
  │   │ (操作)   │   更新 CR status                    │
  │   └────┬─────┘                                     │
  │        │                                           │
  │        ▼                                           │
  │   ┌──────────┐                                     │
  │   │ Requeue  │ ← error? → requeue 重试             │
  │   │ (重排)   │   定期? → requeueAfter              │
  │   └────┬─────┘                                     │
  │        │                                           │
  │        └───────────► 回到 Watch（水平触发）         │
  │                                                     │
  └─────────────────────────────────────────────────────┘

  关键特性:
  ├── 水平触发: 不依赖事件，只看状态
  ├── 优雅退出: NotFound 时正常返回
  ├── 幂等性: 多次执行结果相同
  └── 自动恢复: Operator 重启后自动 Reconcile 所有 CR
""",
        example_yaml="""\
apiVersion: blog.example.com/v1          # CR API 版本
kind: Blog                                # CR 类型
metadata:                                 # 元数据
  name: reconciled-blog                   # CR 名称
spec:                                     # 用户期望状态
  title: "Reconciled Blog"
  content: "Hello K8s"
status:                                   # Reconcile 循环写入的状态
  observedGeneration: 1                   # Controller 已处理的 generation
  conditions:                             # 条件列表
  - type: Ready                           # 条件类型
    status: "True"                        # 状态值
    lastTransitionTime: "2024-01-01T00:00:00Z"  # 最后转换时间
    reason: DeploymentReady
    message: "Blog deployment is running"
""",
        common_errors=[
            "将 Reconcile 理解为事件驱动而非状态驱动（应为水平触发）",
            "NotFound 时抛异常而非优雅退出",
            "忘记 requeue 导致临时错误后不会重试",
            "Reconcile 函数不是幂等的（多次执行结果不同）",
            "在 Reconcile 中阻塞等待（应快速返回，通过 requeue 重试）",
        ],
        tips=[
            "Reconcile 应该是幂等的：无论执行多少次，结果都一样",
            "Reconcile 应该快速返回，不要阻塞等待（用 requeueAfter 代替 sleep）",
            "OwnerReference 配合 Reconcile 可以实现自动垃圾回收",
            "kubebuilder 和 Operator SDK 自动处理了 Watch 机制，你只需实现 Reconcile 函数",
        ],
    ),
)


# ==================== Q17.7 OwnerReference 与级联删除 ====================

def _check_177_owner_reference(user_yaml: str) -> CheckResult:
    """Q17.7 OwnerReference 与级联删除 - 用户写包含 ownerReference 的 CR YAML"""
    try:
        docs = list(yaml.safe_load_all(user_yaml))
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])
    except RecursionError:
        return CheckResult(ok=False, error="YAML 嵌套层级过深", hints=[])

    for doc in docs:
        if doc is None or not isinstance(doc, dict):
            continue

        metadata = doc.get("metadata")
        if not isinstance(metadata, dict):
            continue

        owner_refs = metadata.get("ownerReferences")
        if not isinstance(owner_refs, list) or not owner_refs:
            continue

        ref = owner_refs[0]
        if not isinstance(ref, dict):
            continue

        # 检查必需字段: apiVersion, kind, name, uid
        required = ["apiVersion", "kind", "name", "uid"]
        missing = [f for f in required if not ref.get(f)]
        if missing:
            return CheckResult(
                ok=False,
                error=f"ownerReferences 缺少必需字段: {', '.join(missing)}",
                hints=[
                    "ownerReferences 每项必须包含 apiVersion, kind, name, uid",
                    "例如: {apiVersion: apps/v1, kind: Deployment, name: blog-operator, uid: abc-123}",
                ],
            )

        # 严格校验: apiVersion 不能为空字符串
        api_version = ref.get("apiVersion")
        if not isinstance(api_version, str) or not api_version.strip():
            return CheckResult(
                ok=False,
                error="ownerReferences[0].apiVersion 不能为空字符串",
                hints=[
                    "apiVersion 必须是有效的 API 版本字符串，如 'apps/v1' 或 'blog.example.com/v1'",
                ],
            )

        # 严格校验: name 不能为空
        ref_name = ref.get("name")
        if not isinstance(ref_name, str) or not ref_name.strip():
            return CheckResult(
                ok=False,
                error="ownerReferences[0].name 不能为空字符串",
                hints=[
                    "name 必须是 Owner 资源的有效名称，如 'blog-operator'",
                ],
            )

        # 检查 controller 字段（建议但不强制）
        return CheckResult(
            ok=True, state=ClusterState(),
            hints=[
                "OwnerReference 正确！子资源会在 Owner 被删除时自动清理 🗑️",
                f"  Owner: {ref.get('kind')}/{ref.get('name')} (uid: {ref.get('uid')})",
            ],
        )

    return CheckResult(
        ok=False,
        error="未找到有效的 metadata.ownerReferences",
        hints=[
            "在 CR 的 metadata 中添加 ownerReferences 字段",
            "ownerReferences 是一个列表，每项引用一个 Owner 资源",
            "必需字段: apiVersion, kind, name, uid",
            "示例: metadata:\\n  ownerReferences:\\n  - apiVersion: apps/v1\\n    kind: Deployment\\n    name: blog-operator\\n    uid: abc-123\\n    controller: true",
        ],
    )


LEVEL_Q17_7 = Level(
    id="Q17.7",
    chapter="ch17",
    title="OwnerReference 与级联删除",
    description="""
# OwnerReference 与级联删除 🔗

**OwnerReference** 建立资源间的所有权关系。当 Owner 被删除时，K8s 垃圾回收器会自动删除所有关联的子资源。

## 任务

编写一个 Blog CR YAML，包含 `metadata.ownerReferences`，使其指向一个 Deployment 作为 Owner。

### 要求

`ownerReferences` 列表中每一项必须包含：
- `apiVersion`: Owner 的 API 版本（如 `apps/v1`）
- `kind`: Owner 的类型（如 `Deployment`）
- `name`: Owner 的名称（如 `blog-operator`）
- `uid`: Owner 的唯一标识（如 `abc-123-def`）
- `controller: true`（建议，标识该 Owner 是控制器）

## 提示

```yaml
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: owned-blog
  ownerReferences:
  - apiVersion: apps/v1
    kind: Deployment
    name: blog-operator
    uid: abc-123-def-456
    controller: true
spec:
  title: "Owned Blog"
```
""",
    starter_yaml="""\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: owned-blog
  # ownerReferences:
  # - apiVersion: apps/v1
  #   kind: Deployment
  #   name: blog-operator
  #   uid: abc-123-def-456
  #   controller: true
spec:
  title: "Owned Blog"
""",
    check_fn=_check_177_owner_reference,
    lesson=Lesson(
        concept="""\
## OwnerReference 与级联删除

当 Operator 创建子资源（Deployment、Service 等）时，需要建立所有权关系，这样当 CR 被删除时，子资源会自动被清理。

### 工作原理

```
用户创建 Blog CR
       │
       Operator 检测到新 CR
       │
       Operator 创建 Deployment
       │  └─ 设置 ownerReferences:
       │       apiVersion: blog.example.com/v1
       │       kind: Blog
       │       name: my-blog
       │       uid: <blog-uid>
       │       controller: true
       ▼
  ┌──────────┐         ┌──────────────┐
  │  Blog CR │ ◄────── │  Deployment  │
  │ (Owner)  │  owns   │ (子资源)      │
  └────┬─────┘         └──────────────┘
       │
  用户删除 Blog CR
       │
  K8s 垃圾回收器检测到 Owner 被删除
       │
  自动删除 Deployment (级联删除)
```

### ownerReferences 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| apiVersion | string | ✅ | Owner 的 API 版本 |
| kind | string | ✅ | Owner 的资源类型 |
| name | string | ✅ | Owner 的名称 |
| uid | string | ✅ | Owner 的唯一标识 |
| controller | bool | ❌ | 是否为控制器（建议设为 true） |
| blockOwnerDeletion | bool | ❌ | 是否阻止 Owner 删除直到子资源删除 |

### 级联删除策略

K8s 支持三种级联删除策略：

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| Foreground | 先删子资源，再删 Owner | 确保子资源清理完成 |
| Background | 先删 Owner，异步删子资源 | 快速删除，默认策略 |
| Orphan | 只删 Owner，保留子资源 | 资源迁移 |

### Operator 中的使用

Operator 在创建子资源时自动设置 OwnerReference：

```python
def Reconcile(ctx, req):
    blog = get_blog(req.name)

    # 创建 Deployment，设置 Blog 为 Owner
    deploy = make_deploy(blog)
    set_owner_reference(deploy, blog)  # 关键！
    create_or_update(deploy)
```

使用 kubebuilder/Operator SDK 时，这通常是自动完成的：

```go
// kubebuilder 自动设置 OwnerReference
controllerutil.SetControllerReference(blog, deploy, scheme)
```
""",
        key_fields=[
            {"name": "metadata.ownerReferences", "description": "Owner 引用列表", "required": True, "example": "[{apiVersion: apps/v1, kind: Deployment, name: blog-operator, uid: abc-123}]"},
            {"name": "ownerReferences[].apiVersion", "description": "Owner 的 API 版本", "required": True, "example": "apps/v1"},
            {"name": "ownerReferences[].kind", "description": "Owner 的资源类型", "required": True, "example": "Deployment"},
            {"name": "ownerReferences[].name", "description": "Owner 的名称", "required": True, "example": "blog-operator"},
            {"name": "ownerReferences[].uid", "description": "Owner 的唯一标识", "required": True, "example": "abc-123-def"},
            {"name": "ownerReferences[].controller", "description": "是否为控制器（建议 true）", "required": False, "example": "true"},
        ],
        diagram="""\
  ┌─────────── OwnerReference 级联删除 ───────────────┐
  │                                                    │
  │  ┌──────────────────┐                             │
  │  │   Blog CR (Owner)│                             │
  │  │   uid: abc-123   │                             │
  │  └────────┬─────────┘                             │
  │           │                                       │
  │     ownerReferences                               │
  │     ┌─────┴──────────────────────────┐            │
  │     │                                │            │
  │     ▼                                ▼            │
  │  ┌──────────┐              ┌──────────────┐      │
  │  │Deployment│              │   Service    │      │
  │  │(子资源)  │              │  (子资源)    │      │
  │  └──────────┘              └──────────────┘      │
  │                                                    │
  │  当 Blog CR 被删除时:                              │
  │  ┌──────────────────────────────────────────┐     │
  │  │  K8s 垃圾回收器                           │     │
  │  │  1. 检测到 Owner (Blog) 被删除            │     │
  │  │  2. 查找所有 ownerReferences 指向 Blog 的 │     │
  │  │     资源                                  │     │
  │  │  3. 自动删除 Deployment + Service        │     │
  │  └──────────────────────────────────────────┘     │
  └────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: blog.example.com/v1          # CR API 版本
kind: Blog                                # CR 类型
metadata:                                 # 元数据
  name: owned-blog                        # CR 名称
  ownerReferences:                        # Owner 引用列表
  - apiVersion: apps/v1                   # Owner API 版本（必填）
    kind: Deployment                      # Owner 类型（必填）
    name: blog-operator                   # Owner 名称（必填）
    uid: abc-123-def-456                 # Owner UID（必填）
    controller: true                      # 标记为控制器（建议）
    blockOwnerDeletion: true             # 阻止 Owner 删除直到子资源清理
spec:                                     # CR 规格
  title: "Owned Blog"
""",
        common_errors=[
            "ownerReferences 缺少 uid 字段（uid 是必填的）",
            "apiVersion/kind/name 与实际 Owner 不匹配",
            "忘记设置 controller: true（虽然不强制，但建议设置）",
            "在 Operator 代码中忘记设置 OwnerReference（导致子资源泄漏）",
            "uid 使用了名称而非真正的 UID（uid 是 K8s 自动生成的唯一标识）",
        ],
        tips=[
            "用 kubectl get blog my-blog -o yaml 查看 ownerReferences",
            "Operator SDK / kubebuilder 会自动获取 Owner 的 uid 并设置 OwnerReference",
            "级联删除是 K8s 垃圾回收器的核心功能，不需要 Operator 参与",
            "Foreground 级联删除会等待子资源的 finalizer 完成后才删除 Owner",
        ],
    ),
)


# ==================== Q17.8 Finalizer 概念 ====================

def _check_178_finalizer(user_yaml: str) -> CheckResult:
    """Q17.8 Finalizer 概念 - 用户写包含 finalizers 的 YAML"""
    try:
        docs = list(yaml.safe_load_all(user_yaml))
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])
    except RecursionError:
        return CheckResult(ok=False, error="YAML 嵌套层级过深", hints=[])

    for doc in docs:
        if doc is None or not isinstance(doc, dict):
            continue

        metadata = doc.get("metadata")
        if not isinstance(metadata, dict):
            continue

        finalizers = metadata.get("finalizers")
        if not isinstance(finalizers, list):
            continue

        if not finalizers:
            return CheckResult(
                ok=False,
                error="metadata.finalizers 是空列表（需要至少一个 finalizer）",
                hints=["finalizers 应为非空列表，如 ['blog.example.com/cleanup']"],
            )

        # 检查每个 finalizer 是字符串
        for i, f in enumerate(finalizers):
            if not isinstance(f, str) or not f:
                return CheckResult(
                    ok=False,
                    error=f"finalizers[{i}] 必须是非空字符串",
                    hints=["finalizer 名称通常使用 <domain>/<action> 格式，如 'blog.example.com/cleanup'"],
                )

            # 严格校验: 每个 finalizer 名称必须包含 '/' （标准格式: domain/resource）
            if "/" not in f:
                return CheckResult(
                    ok=False,
                    error=f"finalizers[{i}] '{f}' 不符合标准格式（应包含 '/'，格式为 <domain>/<action>）",
                    hints=[
                        "Finalizer 名称应使用 <domain>/<action> 格式",
                        "例如: 'blog.example.com/cleanup' 或 'kubernetes.io/pv-protection'",
                        "域名前缀确保不同 Operator 的 finalizer 不会冲突",
                    ],
                )

        return CheckResult(
            ok=True, state=ClusterState(),
            hints=[
                "Finalizer 配置正确！资源在被删除前会先执行清理逻辑 🛡️",
                f"  Finalizers: {finalizers}",
            ],
        )

    return CheckResult(
        ok=False,
        error="未找到有效的 metadata.finalizers",
        hints=[
            "在资源的 metadata 中添加 finalizers 字段",
            "finalizers 是一个字符串列表",
            "示例: metadata:\\n  finalizers:\\n  - blog.example.com/cleanup",
        ],
    )


LEVEL_Q17_8 = Level(
    id="Q17.8",
    chapter="ch17",
    title="Finalizer 概念",
    description="""
# Finalizer 概念 🛡️

**Finalizer** 是 K8s 的资源清理机制。当资源带有 finalizer 时，K8s 不会立即删除它，而是等待 Operator 执行清理逻辑后移除 finalizer，然后才真正删除资源。

## 任务

编写一个 Blog CR YAML，包含 `metadata.finalizers` 字段。

### 要求

- `metadata.finalizers` 是一个**非空字符串列表**
- 每个 finalizer 使用 `<domain>/<action>` 格式
- 例如: `blog.example.com/cleanup`

## 提示

```yaml
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: protected-blog
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Protected Blog"
```
""",
    starter_yaml="""\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: protected-blog
  # finalizers:
  # - blog.example.com/cleanup
spec:
  title: "Protected Blog"
""",
    check_fn=_check_178_finalizer,
    lesson=Lesson(
        concept="""\
## Finalizer 机制

Finalizer 是 K8s 中确保资源被**妥善清理**的机制。没有 finalizer 的资源会被立即删除；有 finalizer 的资源会进入 `Terminating` 状态，等待 finalizer 被移除后才真正删除。

### 工作流程

```
用户执行 kubectl delete blog my-blog
       │
       ▼
  ┌──────────────────────────────────────┐
  │  K8s API Server                      │
  │  1. 检查 metadata.finalizers         │
  │  2. 有 finalizer?                    │
  │     → 不删除资源，设置                │
  │       deletionTimestamp              │
  │     → 资源进入 Terminating 状态       │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │  Operator Reconcile 循环              │
  │  1. 检测到 deletionTimestamp          │
  │  2. 执行清理逻辑                      │
  │     - 删除外部资源（如数据库）         │
  │     - 发送通知                        │
  │     - 释放许可证                      │
  │  3. 移除 finalizer                    │
  │     metadata.finalizers.remove(...)   │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │  K8s API Server                      │
  │  finalizers 为空?                     │
  │  → 真正删除资源 ✅                    │
  └──────────────────────────────────────┘
```

### Finalizer 命名规范

Finalizer 使用 `<domain>/<action>` 格式：

| 示例 | 说明 |
|------|------|
| blog.example.com/cleanup | Blog Operator 的清理 finalizer |
| kubernetes.io/pv-protection | PV 保护 finalizer（内置） |
| foregroundDeletion | 前台级联删除（内置） |

### Operator 中的 Finalizer 模式

```python
FINALIZER = "blog.example.com/cleanup"

def Reconcile(ctx, req):
    blog = get_blog(req.name)

    # 新建 CR 时添加 finalizer
    if blog.metadata.deletionTimestamp is None:
        if FINALIZER not in blog.metadata.finalizers:
            blog.metadata.finalizers.append(FINALIZER)
            update_blog(blog)
        return

    # CR 正在被删除，执行清理
    if FINALIZER in blog.metadata.finalizers:
        # 执行清理逻辑
        cleanup_external_resources(blog)

        # 移除 finalizer（K8s 随后真正删除资源）
        blog.metadata.finalizers.remove(FINALIZER)
        update_blog(blog)
```

### 为什么需要 Finalizer？

没有 Finalizer 时：
```
用户删除 CR → K8s 立即删除 → 外部资源泄漏！
（如云数据库实例未被删除，持续计费）
```

有 Finalizer 时：
```
用户删除 CR → K8s 标记 Terminating → Operator 清理外部资源
→ Operator 移除 Finalizer → K8s 真正删除 ✅
```
""",
        key_fields=[
            {"name": "metadata.finalizers", "description": "Finalizer 列表（非空字符串数组）", "required": True, "example": "['blog.example.com/cleanup']"},
        ],
        diagram="""\
  ┌──────────── Finalizer 生命周期 ──────────────────┐
  │                                                  │
  │  创建 CR                                         │
  │  ┌──────────────────────┐                        │
  │  │ metadata:            │                        │
  │  │   finalizers:        │                        │
  │  │   - blog.example.com │                        │
  │  │     /cleanup         │                        │
  │  └──────────┬───────────┘                        │
  │             │                                    │
  │  用户 kubectl delete blog my-blog                │
  │             │                                    │
  │             ▼                                    │
  │  ┌──────────────────────┐                        │
  │  │ K8s 设置              │                        │
  │  │ deletionTimestamp     │                        │
  │  │ 状态: Terminating     │                        │
  │  │ (资源未被真正删除)    │                        │
  │  └──────────┬───────────┘                        │
  │             │                                    │
  │             ▼                                    │
  │  ┌──────────────────────┐                        │
  │  │ Operator Reconcile   │                        │
  │  检测到 deletionTime    │                        │
  │  执行清理逻辑:          │                        │
  │  - 删除外部数据库       │                        │
  │  - 释放 IP 地址         │                        │
  │  - 发送通知             │                        │
  │  移除 finalizer         │                        │
  │  └──────────┬───────────┘                        │
  │             │                                    │
  │             ▼                                    │
  │  ┌──────────────────────┐                        │
  │  │ finalizers 为空       │                        │
  │  K8s 真正删除资源 ✅    │                        │
  │  └──────────────────────┘                        │
  └──────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: blog.example.com/v1          # CR API 版本
kind: Blog                                # CR 类型
metadata:                                 # 元数据
  name: protected-blog                    # CR 名称
  finalizers:                             # Finalizer 列表（非空）
  - blog.example.com/cleanup              # <domain>/<action> 格式
spec:                                     # CR 规格
  title: "Protected Blog"
""",
        common_errors=[
            "finalizers 为空列表（需要至少一个 finalizer）",
            "finalizer 名称不使用 <domain>/<action> 格式",
            "Operator 忘记在清理后移除 finalizer（资源永远卡在 Terminating）",
            "在 Reconcile 中不检查 deletionTimestamp（清理逻辑不触发）",
            "finalizer 名称与其他 Operator 冲突（应使用唯一域名前缀）",
        ],
        tips=[
            "用 kubectl get blog my-blog -o yaml 查看 finalizers 和 deletionTimestamp",
            "如果资源卡在 Terminating，可以手动移除 finalizer: kubectl patch blog my-blog --type=merge -p '{\"metadata\":{\"finalizers\":[]}}'",
            "Finalizer 是 Operator 实现优雅删除的核心机制",
            "每个 Operator 应该只管理自己的 finalizer，不要移除其他 Operator 的 finalizer",
        ],
    ),
)


# ==================== Q17.9 Conditions 状态管理 ====================

def _check_179_conditions(user_yaml: str) -> CheckResult:
    """Q17.9 Conditions 状态管理 - 用户写包含 status.conditions 的 CR"""
    try:
        docs = list(yaml.safe_load_all(user_yaml))
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])
    except RecursionError:
        return CheckResult(ok=False, error="YAML 嵌套层级过深", hints=[])

    for doc in docs:
        if doc is None or not isinstance(doc, dict):
            continue

        status = doc.get("status")
        if not isinstance(status, dict):
            continue

        conditions = status.get("conditions")
        if not isinstance(conditions, list):
            continue

        if not conditions:
            return CheckResult(
                ok=False,
                error="status.conditions 是空列表（需要至少一个 condition）",
                hints=["添加至少一个 condition 对象"],
            )

        # 检查每个 condition 有必需字段
        required = ["type", "status", "lastTransitionTime"]
        for i, cond in enumerate(conditions):
            if not isinstance(cond, dict):
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}] 必须是映射（dict）",
                    hints=["每个 condition 是一个对象"],
                )

            missing = [f for f in required if not cond.get(f)]
            if missing:
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}] 缺少必需字段: {', '.join(missing)}",
                    hints=[
                        "每个 condition 必须包含: type, status, lastTransitionTime",
                        "例如: {type: Ready, status: 'True', lastTransitionTime: '2024-01-01T00:00:00Z'}",
                    ],
                )

            # 严格校验: type 是字符串且非空
            cond_type = cond.get("type")
            if not isinstance(cond_type, str) or not cond_type.strip():
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}].type 必须是非空字符串",
                    hints=[
                        "type 是条件类型，如 'Ready', 'Available', 'Progressing'",
                    ],
                )

            # 严格校验: status 是 'True'/'False'/'Unknown' 之一
            cond_status = cond.get("status")
            if cond_status not in ("True", "False", "Unknown"):
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}].status 必须是 'True'、'False' 或 'Unknown'，实际为 '{cond_status}'",
                    hints=[
                        "K8s condition 的 status 只接受三个值: True, False, Unknown",
                        "注意首字母大写，不要用小写 'true' 或 'false'",
                    ],
                )

            # 严格校验: reason 字段存在（K8s 最佳实践）
            cond_reason = cond.get("reason")
            if not cond_reason or (isinstance(cond_reason, str) and not cond_reason.strip()):
                return CheckResult(
                    ok=False,
                    error=f"conditions[{i}] 缺少 reason 字段（K8s 最佳实践要求每个 condition 提供 reason）",
                    hints=[
                        "reason 是一个 CamelCase 字符串，表示状态的原因",
                        "例如: reason: DeploymentReady, reason: DeploymentNotFound",
                        "reason 帮助用户和监控系统理解 condition 为何处于当前状态",
                    ],
                )

        return CheckResult(
            ok=True, state=ClusterState(),
            hints=[
                "Conditions 状态管理正确！Operator 可以通过 conditions 反映详细状态 📊",
                f"  Conditions: {len(conditions)} 个",
            ],
        )

    return CheckResult(
        ok=False,
        error="未找到有效的 status.conditions",
        hints=[
            "在 CR 中添加 status.conditions 字段",
            "conditions 是一个列表，每项包含 type, status, lastTransitionTime",
            "示例: status:\\n  conditions:\\n  - type: Ready\\n    status: 'True'\\n    lastTransitionTime: '2024-01-01T00:00:00Z'",
        ],
    )


LEVEL_Q17_9 = Level(
    id="Q17.9",
    chapter="ch17",
    title="Conditions 状态管理",
    description="""
# Conditions 状态管理 📊

**Conditions** 是 K8s 中表示资源详细状态的标准模式。通过 `status.conditions` 列表，Operator 可以报告多个维度的状态信息。

## 任务

编写一个 Blog CR YAML，包含 `status.conditions` 字段。

### 要求

`status.conditions` 是一个列表，每一项必须包含：
- `type`: 条件类型（如 `Ready`, `Available`）
- `status`: 条件状态（`True`, `False`, `Unknown`）
- `lastTransitionTime`: 最后转换时间（RFC 3339 格式）

## 提示

```yaml
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
status:
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: "DeploymentReady"
    message: "Blog deployment is running"
```
""",
    starter_yaml="""\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
# status:
#   conditions:
#   - type: Ready
#     status: "True"
#     lastTransitionTime: "2024-01-01T00:00:00Z"
""",
    check_fn=_check_179_conditions,
    lesson=Lesson(
        concept="""\
## Conditions 状态管理

`status.conditions` 是 K8s 中表示资源状态的**标准模式**。它让 Operator 可以报告多个维度的状态，而不仅仅是一个简单的 phase 字段。

### Conditions vs Phase

```
简单 phase（不推荐）:               Conditions（推荐）:
┌──────────────────┐               ┌──────────────────────────────┐
│ status:          │               │ status:                      │
│   phase: Running │               │   conditions:                │
│                  │               │   - type: Ready              │
│ 问题：            │               │     status: "True"           │
│ - 只有一个状态    │               │   - type: Available          │
│ - 无法表达细节    │               │     status: "True"           │
│ - 无法记录历史    │               │   - type: Progressing        │
│                  │               │     status: "False"          │
│                  │               │   - type: Degraded           │
│                  │               │     status: "False"          │
└──────────────────┘               └──────────────────────────────┘
                                     多维度状态 ✅
```

### Condition 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | ✅ | 条件类型（如 Ready, Available） |
| status | string | ✅ | True / False / Unknown |
| lastTransitionTime | string | ✅ | 最后一次状态转换的时间 |
| reason | string | ❌ | 状态原因（CamelCase） |
| message | string | ❌ | 人类可读的消息 |
| observedGeneration | int | ❌ | 观察到的 CR generation |

### 常见 Condition 类型

| Type | 说明 | 示例 |
|------|------|------|
| Ready | 资源是否就绪 | Ready=True 表示可以接受流量 |
| Available | 资源是否可用 | Available=True 表示服务正常运行 |
| Progressing | 是否正在处理 | Progressing=True 表示正在滚动更新 |
| Degraded | 是否降级 | Degraded=True 表示部分功能不可用 |

### Operator 更新 Conditions

```python
def Reconcile(ctx, req):
    blog = get_blog(req.name)

    # 检查 Deployment 状态
    deploy = get_deploy(blog.name)
    if deploy is None:
        set_condition(blog, "Ready", "False",
                      reason="DeploymentNotFound",
                      message="Deployment has not been created yet")
    elif deploy.ready:
        set_condition(blog, "Ready", "True",
                      reason="DeploymentReady",
                      message="Deployment is running and healthy")
    else:
        set_condition(blog, "Ready", "False",
                      reason="DeploymentNotReady",
                      message="Deployment is not ready")

    # 更新 status（通过 status 子资源）
    update_status(blog)
```

### lastTransitionTime 的重要性

`lastTransitionTime` 记录了 condition 状态最后一次变化的时间：
- 只在 status **从 True→False 或 False→True** 时更新
- status 不变时不更新（即使 Reconcile 多次执行）
- 用于监控和告警：判断资源处于异常状态多久了
""",
        key_fields=[
            {"name": "status.conditions", "description": "条件列表（非空数组）", "required": True, "example": "[{type: Ready, status: True, lastTransitionTime: ...}]"},
            {"name": "conditions[].type", "description": "条件类型", "required": True, "example": "Ready"},
            {"name": "conditions[].status", "description": "条件状态: True/False/Unknown", "required": True, "example": "True"},
            {"name": "conditions[].lastTransitionTime", "description": "最后转换时间（RFC 3339）", "required": True, "example": "2024-01-01T00:00:00Z"},
            {"name": "conditions[].reason", "description": "状态原因（CamelCase）", "required": False, "example": "DeploymentReady"},
            {"name": "conditions[].message", "description": "人类可读消息", "required": False, "example": "Deployment is running"},
        ],
        diagram="""\
  ┌────────── Conditions 状态管理 ──────────────────────┐
  │                                                     │
  │  ┌─────────────────────────────────────────────┐   │
  │  │           Blog CR status                     │   │
  │  │                                              │   │
  │  │  conditions:                                 │   │
  │  │  ┌─────────────────────────────────────┐    │   │
  │  │  │ type: Ready                         │    │   │
  │  │  │ status: "True"                      │    │   │
  │  │  │ lastTransitionTime: 2024-01-01T...  │    │   │
  │  │  │ reason: DeploymentReady             │    │   │
  │  │  │ message: "Deployment is running"    │    │   │
  │  │  └─────────────────────────────────────┘    │   │
  │  │  ┌─────────────────────────────────────┐    │   │
  │  │  │ type: Available                     │    │   │
  │  │  │ status: "True"                      │    │   │
  │  │  │ lastTransitionTime: 2024-01-01T...  │    │   │
  │  │  └─────────────────────────────────────┘    │   │
  │  │  ┌─────────────────────────────────────┐    │   │
  │  │  │ type: Progressing                   │    │   │
  │  │  │ status: "False"                     │    │   │
  │  │  │ lastTransitionTime: 2024-01-01T...  │    │   │
  │  │  └─────────────────────────────────────┘    │   │
  │  └─────────────────────────────────────────────┘   │
  │                                                     │
  │  Operator Reconcile 更新流程:                       │
  │  ┌──────────────────────────────────────────┐      │
  │  │ 1. 检查 Deployment 状态                   │      │
  │  │ 2. 比较 condition 当前值与期望值          │      │
  │  │ 3. 如果不同 -> 更新 status + 时间戳       │      │
  │  │ 4. 通过 /status 子资源写入                │      │
  │  └──────────────────────────────────────────┘      │
  └─────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: blog.example.com/v1          # CR API 版本
kind: Blog                                # CR 类型
metadata:                                 # 元数据
  name: status-blog                       # CR 名称
spec:                                     # CR 规格
  title: "Status Blog"
status:                                   # 状态（通过 /status 子资源更新）
  conditions:                             # 条件列表（非空）
  - type: Ready                           # 条件类型（必填）
    status: "True"                        # True/False/Unknown（必填）
    lastTransitionTime: "2024-01-01T00:00:00Z"  # 最后转换时间（必填）
    reason: DeploymentReady               # 原因（可选）
    message: "Blog deployment is running" # 消息（可选）
  - type: Available
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: PodsAvailable
    message: "All pods are ready"
""",
        common_errors=[
            "conditions 为空列表（需要至少一个 condition）",
            "condition 缺少 type/status/lastTransitionTime 中的某个字段",
            "status 值不是 True/False/Unknown（不要用小写 true/false）",
            "lastTransitionTime 格式不正确（应为 RFC 3339 格式）",
            "每次 Reconcile 都更新 lastTransitionTime（只在状态变化时才更新）",
        ],
        tips=[
            "Conditions 是 K8s 社区推荐的状态表示方式（优于简单的 phase 字段）",
            "使用 kubectl get blog my-blog -o jsonpath='{.status.conditions}' 查看 conditions",
            "kubectl wait 命令可以等待特定 condition 达到期望状态",
            "Operator SDK 提供了 conditions 管理的辅助函数，自动处理 lastTransitionTime",
        ],
    ),
)


# ==================== Q17.10 Operator 最佳实践总结 ====================

def _check_1710_best_practices(user_yaml: str) -> CheckResult:
    """Q17.10 Operator 最佳实践总结 - 综合校验完整 CR YAML 的最佳实践字段"""
    try:
        docs = list(yaml.safe_load_all(user_yaml))
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])
    except RecursionError:
        return CheckResult(ok=False, error="YAML 嵌套层级过深", hints=[])

    for doc in docs:
        if doc is None or not isinstance(doc, dict):
            continue

        missing_items = []

        # 1. 有 spec（用户期望状态）
        spec = doc.get("spec")
        if not isinstance(spec, dict) or not spec:
            missing_items.append("spec（用户期望状态）")

        # 2. 有 status（controller 写入的实际状态）
        status = doc.get("status")
        if not isinstance(status, dict) or not status:
            missing_items.append("status（controller 写入的实际状态）")

        # 3. 有 metadata.ownerReferences（级联删除）
        metadata = doc.get("metadata")
        if isinstance(metadata, dict):
            owner_refs = metadata.get("ownerReferences")
            if not isinstance(owner_refs, list) or not owner_refs:
                missing_items.append("metadata.ownerReferences（级联删除）")
        else:
            missing_items.append("metadata.ownerReferences（级联删除）")

        # 4. 有 metadata.finalizers（优雅删除）
        if isinstance(metadata, dict):
            finalizers = metadata.get("finalizers")
            if not isinstance(finalizers, list) or not finalizers:
                missing_items.append("metadata.finalizers（优雅删除）")
        else:
            missing_items.append("metadata.finalizers（优雅删除）")

        # 5. 有 status.conditions（状态管理）
        if isinstance(status, dict):
            conditions = status.get("conditions")
            if not isinstance(conditions, list) or not conditions:
                missing_items.append("status.conditions（状态管理）")
        else:
            missing_items.append("status.conditions（状态管理）")

        if missing_items:
            return CheckResult(
                ok=False,
                error=f"CR YAML 缺少以下最佳实践字段: {', '.join(missing_items)}",
                hints=[
                    "一个符合 Operator 最佳实践的 CR 应包含以下 5 个部分:",
                    "  1. spec - 用户期望状态",
                    "  2. status - controller 写入的实际状态",
                    "  3. metadata.ownerReferences - 级联删除",
                    "  4. metadata.finalizers - 优雅删除",
                    "  5. status.conditions - 状态管理",
                ],
            )

        return CheckResult(
            ok=True, state=ClusterState(),
            hints=[
                "优秀！你的 CR YAML 包含了所有 Operator 最佳实践字段 🏆",
                "  ✅ spec - 用户期望状态",
                "  ✅ status - controller 写入的实际状态",
                "  ✅ metadata.ownerReferences - 级联删除",
                "  ✅ metadata.finalizers - 优雅删除",
                "  ✅ status.conditions - 状态管理",
            ],
        )

    return CheckResult(
        ok=False,
        error="未找到有效的 YAML 文档",
        hints=[
            "请提交一个完整的 CR YAML，包含 Operator 最佳实践的所有字段",
            "需要: spec, status, metadata.ownerReferences, metadata.finalizers, status.conditions",
        ],
    )


LEVEL_Q17_10 = Level(
    id="Q17.10",
    chapter="ch17",
    title="Operator 最佳实践总结",
    description="""
# Operator 最佳实践总结 🏆

通过前面 9 关的学习，你已经掌握了 CRD & Operator 的核心知识。这一关是总结性测试，验证你能否综合运用所有最佳实践。

## 任务

提交一个**完整的 Blog CR YAML**，包含以下 5 个 Operator 最佳实践字段：

1. **`spec`** - 用户期望状态（如 title, author）
2. **`status`** - controller 写入的实际状态
3. **`metadata.ownerReferences`** - 级联删除（指向 Owner 资源）
4. **`metadata.finalizers`** - 优雅删除（清理机制）
5. **`status.conditions`** - 状态管理（多维度状态报告）

全部符合 -> 通过 ✅，否则会指出缺少哪个字段。

## 提示

```yaml
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  ownerReferences:
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def
    controller: true
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Best Practice Blog"
  author: "operator"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: DeploymentReady
    message: "Blog deployment is running"
```
""",
    starter_yaml="""\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  # ownerReferences:
  # - apiVersion: blog.example.com/v1
  #   kind: Blog
  #   name: parent-blog
  #   uid: abc-123-def
  #   controller: true
  # finalizers:
  # - blog.example.com/cleanup
spec:
  title: "Best Practice Blog"
  author: "operator"
# status:
#   observedGeneration: 1
#   conditions:
#   - type: Ready
#     status: "True"
#     lastTransitionTime: "2024-01-01T00:00:00Z"
#     reason: DeploymentReady
#     message: "Blog deployment is running"
""",
    check_fn=_check_1710_best_practices,
    lesson=Lesson(
        concept="""\
## Operator 最佳实践总结

### 1. 幂等性（Idempotency）

Reconcile 循环**必须是幂等的**——无论执行多少次，结果都一样。

```
非幂等（错误 ❌）：                幂等（正确 ✅）：
Reconcile 执行 1 次:              Reconcile 执行 1 次:
  创建 Deployment "blog-1"          检查 Deployment 是否存在
                                     不存在 → 创建
Reconcile 执行 2 次（重试）:       Reconcile 执行 2 次（重试）:
  再创建 Deployment "blog-2"        检查 Deployment 是否存在
  （重复创建！）                     已存在 → 不做任何事
```

实现要点：
- 先检查再操作（get → compare → create/update）
- 不要假设 Reconcile 只执行一次
- 使用 generateName 或固定名称避免重复创建

### 2. Requeue 机制

```python
def Reconcile(ctx, req):
    try:
        # 处理逻辑
        ...
        return Result{requeueAfter: 300}  # 5 分钟后再检查
    except Exception as e:
        return Result{requeue: True}       # 出错时立即重试
```

- `requeue: true` - 立即重新排队
- `requeueAfter: N` - N 秒后重新排队
- 不要在 Reconcile 中使用 `time.sleep()`（会阻塞工作队列）

### 3. Finalizer

确保资源被妥善清理，避免外部资源泄漏：

```python
FINALIZER = "blog.example.com/cleanup"

def Reconcile(ctx, req):
    blog = get_blog(req.name)

    if blog.deletionTimestamp is None:
        # CR 正常运行，确保有 finalizer
        if FINALIZER not in blog.finalizers:
            blog.finalizers.append(FINALIZER)
            update(blog)
    else:
        # CR 正在被删除，执行清理
        cleanup_external_resources(blog)
        blog.finalizers.remove(FINALIZER)
        update(blog)
```

### 4. OwnerReference

建立父子关系，实现自动级联删除：

```python
def Reconcile(ctx, req):
    blog = get_blog(req.name)

    deploy = make_deploy(blog)
    # 设置 Blog 为 Deployment 的 Owner
    set_owner_reference(deploy, owner=blog)
    create_or_update(deploy)
    # 当 Blog 被删除时，Deployment 会被自动清理
```

### 完整的最佳实践清单

| 实践 | 说明 |
|------|------|
| 幂等 Reconcile | 多次执行结果相同 |
| Requeue 重试 | 错误时自动重试，不阻塞 |
| Finalizer 清理 | 删除前执行清理逻辑 |
| OwnerReference | 自动级联删除子资源 |
| Status 子资源 | spec/status 隔离更新 |
| Conditions | 多维度状态报告 |
| 最小权限 RBAC | 只授予必要的权限 |
| Leader Election | 高可用场景下选主 |
| 监控 Metrics | 暴露 Prometheus 指标 |
| 资源限制 | 设置 limits 防止资源泄漏 |
""",
        key_fields=[
            {"name": "幂等性", "description": "Reconcile 多次执行结果相同", "required": True, "example": "先 get 再 create/update，不假设只执行一次"},
            {"name": "requeue", "description": "错误时重新排队重试", "required": True, "example": "Result{requeue: true} 或 Result{requeueAfter: 300}"},
            {"name": "finalizer", "description": "资源删除前的清理机制", "required": True, "example": "blog.example.com/cleanup"},
            {"name": "ownerReference", "description": "父子资源关系与级联删除", "required": True, "example": "{apiVersion: blog.example.com/v1, kind: Blog, name: my-blog, uid: ...}"},
        ],
        diagram="""\
  ┌─────────── Operator 最佳实践全景图 ───────────────────┐
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │              Reconcile 循环                      │ │
  │  │                                                  │ │
  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │ │
  │  │  │  幂等性   │  │ requeue  │  │ 快速返回  │      │ │
  │  │  │ Idempotent│  │ 重试机制  │  │ 不阻塞   │      │ │
  │  │  └──────────┘  └──────────┘  └──────────┘      │ │
  │  └─────────────────────────────────────────────────┘ │
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │              资源管理                             │ │
  │  │                                                  │ │
  │  │  ┌──────────────┐  ┌────────────────────┐       │ │
  │  │  │ finalizer    │  │ ownerReference     │       │ │
  │  │  │ 删除前清理   │  │ 级联删除子资源     │       │ │
  │  │  └──────────────┘  └────────────────────┘       │ │
  │  └─────────────────────────────────────────────────┘ │
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │              状态管理                             │ │
  │  │                                                  │ │
  │  │  ┌──────────────┐  ┌────────────────────┐       │ │
  │  │  │ status 子资源│  │ conditions         │       │ │
  │  │  │ spec隔离    │  │ 多维度状态         │       │ │
  │  │  └──────────────┘  └────────────────────┘       │ │
  │  └─────────────────────────────────────────────────┘ │
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │              生产就绪                             │ │
  │  │                                                  │ │
  │  │  最小权限RBAC | Leader Election | 监控Metrics    │ │
  │  │  资源限制 | 健康检查 | 优雅升级                  │ │
  │  └─────────────────────────────────────────────────┘ │
  └───────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: blog.example.com/v1          # CR API 版本
kind: Blog                                # CR 类型
metadata:                                 # 元数据
  name: best-practice-blog                # CR 名称
  ownerReferences:                        # 级联删除（最佳实践 4）
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def-456
  finalizers:                             # 优雅删除（最佳实践 3）
  - blog.example.com/cleanup
spec:                                     # 用户期望状态（最佳实践 1）
  title: "Best Practice Blog"
  content: "Following all Operator best practices"
status:                                   # Controller 写入的状态（最佳实践 2）
  observedGeneration: 1
  conditions:                             # 状态管理（最佳实践 6）
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: DeploymentReady
    message: "Blog deployment is running"
""",
        common_errors=[
            "Reconcile 不是幂等的（重复创建资源）",
            "遇到错误时不 requeue（临时错误无法恢复）",
            "忘记使用 finalizer（外部资源泄漏）",
            "忘记设置 ownerReference（子资源不会被自动清理）",
            "不使用 status 子资源（spec 被 Operator 意外覆盖）",
        ],
        tips=[
            "Operator SDK 和 kubebuilder 提供了大量辅助函数来简化最佳实践的实现",
            "生产环境部署前，用 chaos engineering 测试 Operator 的恢复能力",
            "监控 Reconcile 的执行时间和错误率，及时发现性能问题",
            "参考成熟 Operator 的实现（如 Prometheus Operator、Cert Manager）学习最佳实践",
        ],
    ),
)


# ==================== 章节关卡列表 ====================

CHAPTER_17_LEVELS: list[Level] = [
    LEVEL_Q17_1, LEVEL_Q17_2, LEVEL_Q17_3, LEVEL_Q17_4, LEVEL_Q17_5,
    LEVEL_Q17_6, LEVEL_Q17_7, LEVEL_Q17_8, LEVEL_Q17_9, LEVEL_Q17_10,
]
