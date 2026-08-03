"""Chapter 17: CRD & Operator 概念（5 关）

Q17.1 创建 CRD - 自定义资源定义基础
Q17.2 创建自定义资源实例 - 使用 CRD
Q17.3 CRD Schema 验证 - OpenAPI v3 验证
Q17.4 Operator 模式概念 - 控制器循环 (watch -> compare -> act)
Q17.5 集群实战 - 部署自定义控制器
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# 预置 CRD YAML（供 Q17.2 等关卡使用）
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
"""


# ==================== Q17.1 创建 CRD ====================

def _check_171_create_crd(user_yaml: str) -> CheckResult:
    """Q17.1 创建一个 Blog CRD"""
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
    if not group:
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

    return CheckResult(
        ok=True, state=state,
        hints=["CRD 创建成功！现在你可以用 kubectl get blogs 来查看自定义资源了 🎉"],
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

### 资源命名规则

- **metadata.name**：必须为 `<plural>.<group>` 格式
- **spec.names.kind**：PascalCase，如 `Blog`、`Database`
- **spec.names.plural**：小写复数，如 `blogs`、`databases`
- **spec.names.shortNames**：kubectl 快捷别名

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
            {"name": "spec.group", "description": "API 组名，自定义资源的命名空间", "required": True, "example": "blog.example.com"},
            {"name": "spec.names.kind", "description": "资源类型名（PascalCase）", "required": True, "example": "Blog"},
            {"name": "spec.names.plural", "description": "资源复数名（小写）", "required": True, "example": "blogs"},
            {"name": "spec.versions", "description": "API 版本列表", "required": True, "example": "[{name: v1, served: true, storage: true}]"},
            {"name": "spec.scope", "description": "资源作用域: Namespaced 或 Cluster", "required": True, "example": "Namespaced"},
            {"name": "metadata.name", "description": "CRD 名称，格式: <plural>.<group>", "required": True, "example": "blogs.blog.example.com"},
        ],
        diagram="""\
  ┌─────────────── CRD ────────────────────┐
  │  kind: CustomResourceDefinition         │
  │  metadata:                              │
  │    name: blogs.blog.example.com         │
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


# ==================== Q17.2 创建自定义资源实例 ====================

def _check_172_create_cr(user_yaml: str) -> CheckResult:
    """Q17.2 使用 CRD 创建一个 Blog 实例"""
    try:
        state = ClusterState()
        # 预置 CRD，使模拟器能识别 Blog 资源
        state = preset_state(state, _PRESET_CRD_YAML)
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.customresources:
        return CheckResult(
            ok=False,
            error="没有创建任何自定义资源实例",
            hints=[
                "你需要创建一个 kind: Blog 的资源",
                "apiVersion 应为 blog.example.com/v1",
            ],
        )

    # 获取第一个 CR
    cr_key = next(iter(state.customresources))
    cr = state.customresources[cr_key]

    # 检查 kind
    if cr.get("kind") != "Blog":
        return CheckResult(
            ok=False,
            error=f"资源 kind 应为 'Blog'，实际为 '{cr.get('kind')}'",
            hints=["kind 必须与 CRD 的 spec.names.kind 一致"],
        )

    # 检查 apiVersion
    api_version = cr.get("apiVersion", "")
    if "blog.example.com" not in api_version:
        return CheckResult(
            ok=False,
            error=f"apiVersion 应包含 'blog.example.com'，实际为 '{api_version}'",
            hints=["apiVersion 格式: <group>/<version>，如 blog.example.com/v1"],
        )

    # 检查 spec 字段
    spec = cr.get("spec", {})
    if not isinstance(spec, dict) or not spec:
        return CheckResult(
            ok=False,
            error="Blog 资源缺少 spec",
            hints=["spec 中应包含 title、author 等字段"],
        )

    if not spec.get("title"):
        return CheckResult(
            ok=False,
            error="Blog spec 缺少 title 字段",
            hints=["添加 spec.title: '我的第一篇博客'"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["自定义资源创建成功！CRD + CR 就构成了 K8s 的扩展能力 ✨"],
    )


LEVEL_Q17_2 = Level(
    id="Q17.2",
    chapter="ch17",
    title="创建自定义资源实例",
    description="""
# 创建自定义资源实例 📝

CRD 只是"定义"，你还需要创建**自定义资源实例（CR）**才能真正使用它。就像 Class 是定义，Object 是实例。

## 任务

集群中已注册了 `Blog` CRD（group: `blog.example.com`）。请创建一个 Blog 实例：

- `apiVersion: blog.example.com/v1`
- `kind: Blog`
- `metadata.name`: 你的博客名
- `spec.title`: 博客标题
- `spec.author`: 作者名

## 提示

CR 的 apiVersion = `<group>/<version>`：
```yaml
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-first-blog
spec:
  title: "Hello K8s"
  author: "dev"
```
""",
    starter_yaml="""\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-first-blog
spec:
  # title: "Hello K8s"
  # author: "dev"
""",
    check_fn=_check_172_create_cr,
    lesson=Lesson(
        concept="""\
## 自定义资源实例（CR）

CRD 定义了资源类型，**CR（Custom Resource）** 是该类型的实例。就像 Deployment 是一个类型，`my-deploy` 是一个具体的 Deployment 实例。

### CR 与 CRD 的关系

```
CRD (定义)               CR (实例)
┌──────────────┐         ┌──────────────────┐
│ kind: Blog   │         │ kind: Blog       │
│ group: ...   │ ──────► │ apiVersion:      │
│ versions:    │  实例化  │   blog.example   │
│   v1         │         │   .com/v1        │
│ properties:  │         │ metadata:        │
│   spec.title │         │   name: my-blog  │
│   spec.author│         │ spec:            │
└──────────────┘         │   title: Hello   │
                         │   author: dev    │
                         └──────────────────┘
```

### apiVersion 的组成

CR 的 apiVersion 由 CRD 的 `group` 和 `version` 拼接而成：
- `group`: `blog.example.com`
- `version`: `v1`
- `apiVersion`: `blog.example.com/v1`

### kubectl 操作 CR

```bash
# 创建
kubectl apply -f blog.yaml

# 列出所有 Blog
kubectl get blogs

# 查看详情
kubectl describe blog my-first-blog

# 编辑
kubectl edit blog my-first-blog

# 删除
kubectl delete blog my-first-blog
```

### CR 存储在哪里？

CR 的数据存储在 etcd 中（与原生 K8s 资源一样）。API Server 负责 CRUD 操作，
但**不会自动对 CR 做任何业务逻辑处理**——那是 Operator 的工作。
""",
        key_fields=[
            {"name": "apiVersion", "description": "格式: <group>/<version>，来自 CRD", "required": True, "example": "blog.example.com/v1"},
            {"name": "kind", "description": "与 CRD 的 spec.names.kind 一致", "required": True, "example": "Blog"},
            {"name": "metadata.name", "description": "资源实例名称", "required": True, "example": "my-first-blog"},
            {"name": "spec", "description": "自定义规格，由 CRD schema 定义", "required": True, "example": "{title: Hello, author: dev}"},
        ],
        diagram="""\
  CRD 注册                    创建 CR
  
  ┌──────────────┐           ┌───────────────────────┐
  │  CRD: Blog   │           │  apiVersion:          │
  │  group: ...  │           │    blog.example.com   │
  │  kind: Blog  │           │    /v1                │
  │  version: v1 │           │  kind: Blog           │
  └──────┬───────┘           │  metadata:            │
         │                   │    name: my-first-blog│
         │  kubectl apply    │  spec:               │
         │  -f blog.yaml     │    title: Hello K8s  │
         │                   │    author: dev       │
         ▼                   └───────────┬───────────┘
  ┌──────────────┐                       │
  │  API Server  │ ◄─── 验证 kind+group ─┘
  │  接受 CR     │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │    etcd      │   存储 CR 数据
  │  (持久化)    │
  └──────────────┘
""",
        example_yaml="""\
apiVersion: blog.example.com/v1   # <group>/<version>
kind: Blog                        # 与 CRD names.kind 一致
metadata:                         # 元数据
  name: my-first-blog             # 实例名称
spec:                             # 自定义规格
  title: "Hello K8s"              # 博客标题
  author: "dev"                   # 作者
""",
        common_errors=[
            "apiVersion 写成了 v1（应该是 group/version 如 blog.example.com/v1）",
            "kind 与 CRD 定义的不一致（CRD 定义 Blog，CR 写了 blog）",
            "试图创建 CR 但 CRD 还没注册（会报 'no matches for kind' 错误）",
            "spec 字段不符合 CRD schema 定义（如有 schema 验证的话）",
        ],
        tips=[
            "用 kubectl get blogs 列出所有 Blog 实例",
            "用 kubectl get crd 查看已注册的 CRD 列表",
            "CR 创建后存储在 etcd 中，即使没有 Operator 也能正常 CRUD",
        ],
    ),
)


# ==================== Q17.3 CRD Schema 验证 ====================

def _check_173_crd_schema(user_yaml: str) -> CheckResult:
    """Q17.3 创建带 OpenAPI v3 Schema 验证的 CRD"""
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

    # 检查 properties
    properties = open_api_schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return CheckResult(
            ok=False,
            error="openAPIV3Schema 缺少 properties",
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


LEVEL_Q17_3 = Level(
    id="Q17.3",
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
    check_fn=_check_173_crd_schema,
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
            {"name": "openAPIV3Schema.properties", "description": "字段定义", "required": True, "example": "{spec: {type: object, properties: {...}}}"},
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
  │        properties:                           │
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


# ==================== Q17.4 Operator 模式概念 ====================

def _check_174_operator_pattern(user_yaml: str) -> CheckResult:
    """Q17.4 创建一个 Operator 控制器 Deployment"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.deployments:
        return CheckResult(
            ok=False,
            error="没有创建任何 Deployment",
            hints=["Operator 通常以 Deployment 形式运行控制器"],
        )

    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    spec = dep.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec.template.spec", hints=[])

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

    # 检查环境变量（Operator 通常有 WATCH_NAMESPACE 等配置）
    env = c.get("env", [])
    has_watch_env = False
    if isinstance(env, list):
        for e in env:
            if isinstance(e, dict):
                name = e.get("name", "")
                if "WATCH" in name.upper() or "NAMESPACE" in name.upper() or "CRD" in name.upper():
                    has_watch_env = True
                    break

    if not has_watch_env:
        return CheckResult(
            ok=False,
            error="Operator 容器缺少 WATCH_NAMESPACE 或类似环境变量",
            hints=[
                "Operator 控制器通常通过环境变量配置监听范围 💡",
                "添加 env: [{name: WATCH_NAMESPACE, value: \"\"}]",
            ],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Operator = CRD + 控制器循环。它持续 Watch 资源变化并做出响应 🔄"],
    )


LEVEL_Q17_4 = Level(
    id="Q17.4",
    chapter="ch17",
    title="Operator 模式概念",
    description="""
# Operator 模式概念 🔄

**Operator** = CRD + 控制器。它像一个"自动化运维员"，持续监控自定义资源的变化，并执行相应的操作。

## 任务

创建一个 Operator 控制器的 Deployment：
- `kind: Deployment`
- 容器 image 使用 `operator-sdk/example-operator:v1`
- 添加环境变量 `WATCH_NAMESPACE` 用于配置监听范围
- replicas: 1

## 提示

Operator 的控制器以 Deployment 形式运行：
```yaml
spec:
  template:
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
        # image: operator-sdk/example-operator:v1
        # env:
        # - name: WATCH_NAMESPACE
        #   value: ""
""",
    check_fn=_check_174_operator_pattern,
    lesson=Lesson(
        concept="""\
## Operator 模式

**Operator** 是 CRD + 控制器的组合，用于将**人类运维知识**编码成软件。

### 控制器循环（Reconcile Loop）

Operator 的核心是**控制循环**（也叫 Reconcile Loop）：

```
┌─────────────────────────────────────────────┐
│           控制器循环 (Reconcile)              │
│                                              │
│  ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │  Watch   │───►│ Compare  │───►│  Act   │ │
│  │ (监听)   │    │ (比较)   │    │ (操作) │ │
│  └──────────┘    └──────────┘    └────────┘ │
│       ▲                               │      │
│       └───────────────────────────────┘      │
│              (循环往复)                       │
└─────────────────────────────────────────────┘
```

1. **Watch（监听）**：监听 CR 和相关资源的变化事件
2. **Compare（比较）**：比较当前状态与期望状态（CR 中定义的）
3. **Act（操作）**：执行操作使当前状态趋近期望状态

### Operator vs 内置控制器

| 特性 | 内置控制器 | Operator |
|------|-----------|----------|
| 管理资源 | Pod/Service 等 | 自定义资源 (CR) |
| 领域知识 | 通用 | 特定领域 |
| 开发方式 | K8s 内置 | 用户开发 |
| 示例 | Deployment Controller | etcd Operator |

### 常见 Operator 框架

- **Operator SDK**：Red Hat 出品，支持 Go/Ansible/Helm
- **kubebuilder**：官方推荐，Go 语言
- **Metacontroller**：轻量级，支持 Lambda 函数

### Operator 的典型行为

以 Blog Operator 为例：
```
用户创建 Blog CR ──► Watch 检测到新 CR
                  ──► Compare: 期望有 Deployment 运行博客
                  ──► Act: 创建 Deployment + Service
                  ──► Watch: 检测到 Deployment 就绪
                  ──► Compare: 期望 Blog 状态为 published
                  ──► Act: 更新 CR status 为 published
```
""",
        key_fields=[
            {"name": "spec.template.spec.containers[].image", "description": "Operator 控制器镜像", "required": True, "example": "operator-sdk/example-operator:v1"},
            {"name": "spec.template.spec.containers[].env", "description": "环境变量，通常包含 WATCH_NAMESPACE 等", "required": True, "example": "[{name: WATCH_NAMESPACE, value: \"\"}]"},
            {"name": "spec.replicas", "description": "副本数，通常为 1", "required": False, "example": "1"},
        ],
        diagram="""\
  ┌─────────── Operator 架构 ────────────────────────┐
  │                                                   │
  │  ┌──────────┐    Watch     ┌─────────────────┐   │
  │  │  CRD     │ ───────────► │  Controller     │   │
  │  │  (Blog)  │              │  (Deployment)   │   │
  │  └──────────┘              │                 │   │
  │                            │  Reconcile:     │   │
  │  ┌──────────┐    Watch     │  1. Watch CR    │   │
  │  │  CR      │ ───────────► │  2. Compare     │   │
  │  │ (Blog实例)│              │  3. Act         │   │
  │  └──────────┘              └────────┬────────┘   │
  │                                     │             │
  │                              Act (创建/更新)      │
  │                                     │             │
  │                    ┌────────────────┼──────────┐  │
  │                    ▼                ▼          ▼  │
  │              ┌──────────┐  ┌──────────┐ ┌──────┐ │
  │              │Deployment│  │ Service  │ │Config│ │
  │              │ (博客App) │  │ (网络)   │ │Map   │ │
  │              └──────────┘  └──────────┘ └──────┘ │
  └───────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: apps/v1                    # Deployment API
kind: Deployment                       # 资源类型
metadata:                              # 元数据
  name: blog-operator                  # Operator 名称
spec:                                  # 规格定义
  replicas: 1                          # 1 个副本
  selector:                            # 标签选择器
    matchLabels:
      app: blog-operator
  template:                            # Pod 模板
    metadata:
      labels:
        app: blog-operator
    spec:
      containers:                      # 容器列表
      - name: operator                 # 容器名
        image: operator-sdk/example-operator:v1  # 镜像
        env:                           # 环境变量
        - name: WATCH_NAMESPACE        # 监听的命名空间
          value: ""                    # 空字符串 = 所有命名空间
        resources:                     # 资源限制
          limits:
            memory: "128Mi"
            cpu: "250m"
""",
        common_errors=[
            "把 Operator 和 CRD 搞混：CRD 是定义，Operator 是运行控制器",
            "忘记设置 WATCH_NAMESPACE 环境变量",
            "replicas 设得过高（Operator 通常只需 1 个副本，除非需要高可用）",
            "没有理解 Reconcile Loop：Operator 不是事件驱动的，而是状态驱动的",
        ],
        tips=[
            "用 kubectl logs deploy/blog-operator 查看 Operator 的 Reconcile 日志",
            "Operator 的核心思想是把运维知识编码成代码",
            "热门 Operator 示例：Prometheus Operator、Cert Manager、ArgoCD",
        ],
    ),
)


# ==================== Q17.5 集群实战 - 部署自定义控制器 ====================

def _check_175_deploy_operator(user_yaml: str) -> CheckResult:
    """Q17.5 集群实战 - 部署完整的 Operator 栈"""
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
            hints=["一个完整的 Operator 部署需要 CRD + Deployment + ServiceAccount"],
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

    # 检查 Deployment 使用了 ServiceAccount
    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {}).get("template", {}).get("spec", {})
    sa_name = dep_spec.get("serviceAccountName", "")

    if not sa_name:
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
            "完整的 Operator 栈已就绪！在真实集群上执行：",
            "  kubectl apply -f operator-stack.yaml",
            "  kubectl get crd          # 查看注册的 CRD",
            "  kubectl get pods         # 查看 Operator 运行状态",
            "  kubectl logs <operator-pod>  # 查看 Reconcile 日志",
        ],
    )


LEVEL_Q17_5 = Level(
    id="Q17.5",
    chapter="ch17",
    title="集群实战: 部署自定义控制器",
    description="""
# 集群实战: 部署自定义控制器 🚀

部署一个完整的 Operator 栈：CRD + ServiceAccount + Deployment。

## 任务

使用多文档 YAML（`---` 分隔）创建：
1. **CustomResourceDefinition** - 定义 Blog 资源类型
2. **ServiceAccount** - Operator 使用的身份
3. **Deployment** - Operator 控制器，使用上述 ServiceAccount

## 要求

- CRD: group=`blog.example.com`, kind=`Blog`, versions 含 `v1`
- ServiceAccount: name=`blog-operator-sa`
- Deployment: 引用上述 ServiceAccount，image=`operator-sdk/example-operator:v1`

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
""",
        key_fields=[
            {"name": "CustomResourceDefinition", "description": "定义自定义资源类型", "required": True, "example": "blogs.blog.example.com"},
            {"name": "ServiceAccount", "description": "Operator 的身份标识", "required": True, "example": "blog-operator-sa"},
            {"name": "Deployment.spec.template.spec.serviceAccountName", "description": "Pod 使用的 SA", "required": True, "example": "blog-operator-sa"},
            {"name": "Deployment.spec.template.spec.containers[].image", "description": "控制器镜像", "required": True, "example": "operator-sdk/example-operator:v1"},
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
  │  │  Deployment: blog-operator (uses SA)         │    │
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
  replicas: 1
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
        - name: WATCH_NAMESPACE
          value: ""
""",
        common_errors=[
            "多文档 YAML 忘记用 --- 分隔",
            "Deployment 的 serviceAccountName 与 ServiceAccount 名称不匹配",
            "CRD 的 versions 缺少 schema（K8s 1.16+ 强制要求）",
            "忘记在 Deployment 的 Pod 模板中设置 serviceAccountName",
        ],
        tips=[
            "用 kubectl get crd,sa,deploy 一次性查看所有部署的资源",
            "生产环境还应添加 Role + RoleBinding 赋予 SA 权限",
            "用 kubectl describe deploy blog-operator 检查 SA 是否正确挂载",
        ],
    ),
)


# ==================== 章节关卡列表 ====================

CHAPTER_17_LEVELS: list[Level] = [
    LEVEL_Q17_1, LEVEL_Q17_2, LEVEL_Q17_3, LEVEL_Q17_4, LEVEL_Q17_5,
]
