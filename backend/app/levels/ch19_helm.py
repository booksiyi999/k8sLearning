"""Chapter 19: Helm 包管理（5 关）

Q19.1 创建第一个 Helm Chart
Q19.2 Helm values 配置
Q19.3 Helm 模板渲染
Q19.4 Helm 依赖管理
Q19.5 集群实战 - 部署完整 Helm Chart
"""
import re
import yaml
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, ClusterState, K8sError


# ==================== Q19.1 创建第一个 Helm Chart ====================

def _check_191_create_chart(user_yaml: str) -> CheckResult:
    """Q19.1 创建第一个 Helm Chart - 验证 Chart.yaml 结构"""
    try:
        doc = yaml.safe_load(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])

    if doc is None or not isinstance(doc, dict):
        return CheckResult(
            ok=False,
            error="YAML 内容为空或格式错误",
            hints=["Chart.yaml 必须是一个 YAML 映射（dict）"],
        )

    # 检查 apiVersion
    api_version = doc.get("apiVersion")
    if not api_version:
        return CheckResult(
            ok=False,
            error="Chart.yaml 缺少 apiVersion",
            hints=["添加 apiVersion: v2（Helm 3 推荐使用 v2）"],
        )
    if api_version != "v2":
        return CheckResult(
            ok=False,
            error=f"apiVersion 应为 'v2'，实际为 '{api_version}'",
            hints=["Helm 3 推荐使用 apiVersion: v2"],
        )

    # 检查 name
    name = doc.get("name")
    if not name:
        return CheckResult(
            ok=False,
            error="Chart.yaml 缺少 name",
            hints=["添加 name: my-app（chart 名称）"],
        )

    # 检查 version
    version = doc.get("version")
    if not version:
        return CheckResult(
            ok=False,
            error="Chart.yaml 缺少 version",
            hints=["添加 version: 0.1.0（chart 版本，遵循 SemVer）"],
        )

    # 检查 description
    description = doc.get("description")
    if not description:
        return CheckResult(
            ok=False,
            error="Chart.yaml 缺少 description",
            hints=["添加 description 描述 chart 的用途"],
        )

    # 检查 type
    chart_type = doc.get("type")
    if not chart_type:
        return CheckResult(
            ok=False,
            error="Chart.yaml 缺少 type",
            hints=["添加 type: application（或 library）"],
        )

    if chart_type not in ("application", "library"):
        return CheckResult(
            ok=False,
            error=f"type 应为 'application' 或 'library'，实际为 '{chart_type}'",
            hints=["type: application 表示应用 chart，library 表示库 chart"],
        )

    return CheckResult(
        ok=True,
        hints=["Chart.yaml 结构正确！Helm chart 的核心配置文件就绪 📦"],
    )


LEVEL_Q19_1 = Level(
    id="Q19.1",
    chapter="ch19",
    title="创建第一个 Helm Chart",
    description="""
# 创建第一个 Helm Chart 📦

**Helm** 是 Kubernetes 的包管理工具，类似于 Ubuntu 的 apt 或 CentOS 的 yum。Helm Chart 是一组描述 K8s 资源的文件集合。

## 任务

编写一个 **Chart.yaml** 文件，包含以下字段：
- `apiVersion: v2`（Helm 3 推荐版本）
- `name: my-web-app`
- `version: 0.1.0`（chart 版本）
- `description: A Helm chart for web application`
- `type: application`

## 提示

Chart.yaml 是 Helm chart 的元数据文件，类似于 `package.json`：
```yaml
apiVersion: v2
name: my-web-app
description: A Helm chart for web application
type: application
version: 0.1.0
appVersion: "1.0"
```
""",
    starter_yaml="""\
apiVersion: v2
# name: my-web-app
# version: 0.1.0
# description: A Helm chart for web application
# type: application
""",
    check_fn=_check_191_create_chart,
    lesson=Lesson(
        concept="""\
## 什么是 Helm？

**Helm** 是 Kubernetes 的**包管理工具**，它将一组 K8s 资源打包为一个可复用、可版本管理的单元——**Chart**。

### Helm 的核心概念

1. **Chart**：K8s 应用的打包格式，包含一组模板文件和配置
2. **Release**：Chart 的一个运行实例（同一 chart 可多次安装，每次创建一个 release）
3. **Repository**：Chart 仓库，用于存储和共享 chart

### Chart.yaml 的作用

Chart.yaml 是 chart 的**元数据文件**，定义 chart 的基本信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| `apiVersion` | Chart API 版本（v2 用于 Helm 3） | `v2` |
| `name` | Chart 名称 | `my-web-app` |
| `version` | Chart 版本（SemVer） | `0.1.0` |
| `description` | Chart 描述 | `A Helm chart...` |
| `type` | Chart 类型 | `application` / `library` |
| `appVersion` | 应用版本 | `"1.0"` |
| `icon` | Chart 图标 URL | `https://...` |
| `maintainers` | 维护者列表 | `- name: dev` |

### Helm Chart 目录结构

```
my-web-app/
├── Chart.yaml          # Chart 元数据
├── values.yaml         # 默认配置值
├── templates/          # K8s 资源模板
│   ├── deployment.yaml
│   ├── service.yaml
│   └── _helpers.tpl    # 模板辅助函数
├── charts/             # 依赖的子 chart
└── README.md           # 说明文档
```
""",
        key_fields=[
            {"name": "apiVersion", "description": "Chart API 版本，Helm 3 使用 v2", "required": True, "example": "v2"},
            {"name": "name", "description": "Chart 名称", "required": True, "example": "my-web-app"},
            {"name": "version", "description": "Chart 版本，遵循语义化版本", "required": True, "example": "0.1.0"},
            {"name": "description", "description": "Chart 描述", "required": True, "example": "A Helm chart..."},
            {"name": "type", "description": "Chart 类型: application 或 library", "required": True, "example": "application"},
            {"name": "appVersion", "description": "应用版本（非 chart 版本）", "required": False, "example": '"1.0"'},
        ],
        diagram="""\
  Helm Chart 结构

  ┌─────────────────── my-web-app/ ──────────────────┐
  │                                                   │
  │   Chart.yaml          ← 你在这里编写              │
  │   ┌─────────────────────────────────────┐        │
  │   │ apiVersion: v2                      │        │
  │   │ name: my-web-app                    │        │
  │   │ version: 0.1.0                      │        │
  │   │ description: A Helm chart...        │        │
  │   │ type: application                   │        │
  │   │ appVersion: "1.0"                   │        │
  │   └─────────────────────────────────────┘        │
  │                                                   │
  │   values.yaml         ← 默认配置                  │
  │   templates/          ← K8s 资源模板              │
  │   charts/             ← 依赖子 chart              │
  │   README.md           ← 文档                      │
  │                                                   │
  └───────────────────────────────────────────────────┘

  helm install my-release my-web-app/
        │
        ▼
  Release: my-release (chart 的运行实例)
""",
        example_yaml="""\
apiVersion: v2              # Helm 3 Chart API 版本
name: my-web-app            # Chart 名称
description: A Helm chart for web application  # 描述
type: application           # 应用类型 chart
version: 0.1.0             # Chart 版本 (SemVer)
appVersion: "1.0"          # 应用版本
icon: https://example.com/logo.png
maintainers:
- name: dev-team
  email: dev@example.com
""",
        common_errors=[
            "apiVersion 写成 v1（v1 是 Helm 2 的格式，Helm 3 推荐 v2）",
            "version 和 appVersion 搞混：version 是 chart 自身版本，appVersion 是应用的版本",
            "type 写成 app（应为 application 或 library）",
            "version 不遵循 SemVer 格式（如 0.1 而非 0.1.0）",
        ],
        tips=[
            "用 helm create my-chart 可以生成标准 chart 骨架",
            "用 helm lint my-chart 检查 chart 结构是否正确",
            "version 字段必须遵循 SemVer 2.0 格式（如 1.0.0、0.1.0-beta）",
        ],
    ),
)


# ==================== Q19.2 Helm values 配置 ====================

def _check_192_values_config(user_yaml: str) -> CheckResult:
    """Q19.2 Helm values 配置 - 验证 values.yaml 结构"""
    try:
        doc = yaml.safe_load(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])

    if doc is None or not isinstance(doc, dict):
        return CheckResult(
            ok=False,
            error="values.yaml 内容为空或格式错误",
            hints=["values.yaml 必须是一个 YAML 映射（dict）"],
        )

    # 检查 replicaCount
    replica_count = doc.get("replicaCount")
    if replica_count is None:
        return CheckResult(
            ok=False,
            error="values.yaml 缺少 replicaCount",
            hints=["添加 replicaCount: 3（副本数量）"],
        )
    if not isinstance(replica_count, int) or replica_count < 1:
        return CheckResult(
            ok=False,
            error=f"replicaCount 应为正整数，实际为 {replica_count}",
            hints=["replicaCount: 3"],
        )

    # 检查 image
    image = doc.get("image")
    if not isinstance(image, dict):
        return CheckResult(
            ok=False,
            error="values.yaml 缺少 image（应为映射）",
            hints=["添加 image 配置：image: { repository: nginx, tag: '1.25' }"],
        )
    if not image.get("repository"):
        return CheckResult(
            ok=False,
            error="image 缺少 repository",
            hints=["添加 image.repository: nginx"],
        )
    if not image.get("tag"):
        return CheckResult(
            ok=False,
            error="image 缺少 tag",
            hints=["添加 image.tag: '1.25'"],
        )

    # 检查 service
    service = doc.get("service")
    if not isinstance(service, dict):
        return CheckResult(
            ok=False,
            error="values.yaml 缺少 service（应为映射）",
            hints=["添加 service 配置：service: { type: ClusterIP, port: 80 }"],
        )
    if not service.get("type"):
        return CheckResult(
            ok=False,
            error="service 缺少 type",
            hints=["添加 service.type: ClusterIP"],
        )
    if not service.get("port"):
        return CheckResult(
            ok=False,
            error="service 缺少 port",
            hints=["添加 service.port: 80"],
        )

    return CheckResult(
        ok=True,
        hints=["values.yaml 配置完整！values 文件让 chart 可参数化复用 ⚙️"],
    )


LEVEL_Q19_2 = Level(
    id="Q19.2",
    chapter="ch19",
    title="Helm values 配置",
    description="""
# Helm values 配置 ⚙️

**values.yaml** 是 Helm chart 的默认配置文件，让 chart 可以通过参数化实现复用。同一份 chart 模板，用不同的 values 就能部署到不同环境。

## 任务

编写一个 **values.yaml**，包含以下配置：
- `replicaCount: 3`（副本数）
- `image` 映射，包含 `repository` 和 `tag`
- `service` 映射，包含 `type` 和 `port`

## 提示

values.yaml 是纯键值对配置，在模板中通过 `.Values` 引用：
```yaml
replicaCount: 3
image:
  repository: nginx
  tag: "1.25"
service:
  type: ClusterIP
  port: 80
```
""",
    starter_yaml="""\
# replicaCount: 3
# image:
#   repository: nginx
#   tag: "1.25"
# service:
#   type: ClusterIP
#   port: 80
""",
    check_fn=_check_192_values_config,
    lesson=Lesson(
        concept="""\
## Helm Values 配置

**values.yaml** 是 Helm chart 的**默认配置文件**，它让模板可以参数化，实现一份模板多场景复用。

### Values 的层级结构

values.yaml 支持任意层级的嵌套映射：

```yaml
# 顶层配置
replicaCount: 3

# 嵌套映射
image:
  repository: nginx
  tag: "1.25"
  pullPolicy: IfNotPresent

# 更深层嵌套
service:
  type: ClusterIP
  port: 80
  targetPort: 8080

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

### Values 覆盖机制

Helm 支持多层 values 覆盖，优先级从低到高：

1. **chart 内的 values.yaml** — 默认值
2. **父 chart 的 values.yaml** — 覆盖子 chart
3. **`-f` / `--values` 指定的文件** — 自定义 values 文件
4. **`--set` 命令行参数** — 单个值覆盖（优先级最高）

```bash
# 用自定义 values 文件覆盖
helm install my-app ./my-chart -f prod-values.yaml

# 用 --set 覆盖单个值
helm install my-app ./my-chart --set replicaCount=5

# 用 --set 覆盖嵌套值
helm install my-app ./my-chart --set image.tag=1.26
```

### 模板中引用 Values

在模板文件中，通过 `.Values` 对象引用配置：

```yaml
# templates/deployment.yaml
spec:
  replicas: {{ .Values.replicaCount }}
  containers:
  - name: {{ .Chart.Name }}
    image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```
""",
        key_fields=[
            {"name": "replicaCount", "description": "Pod 副本数量", "required": True, "example": "3"},
            {"name": "image.repository", "description": "容器镜像仓库地址", "required": True, "example": "nginx"},
            {"name": "image.tag", "description": "容器镜像标签", "required": True, "example": '"1.25"'},
            {"name": "service.type", "description": "Service 类型", "required": True, "example": "ClusterIP"},
            {"name": "service.port", "description": "Service 端口", "required": True, "example": "80"},
        ],
        diagram="""\
  Values 配置与模板的关系

  values.yaml                    templates/deployment.yaml
  ┌──────────────────────┐       ┌────────────────────────────┐
  │ replicaCount: 3      │       │ spec:                      │
  │ image:               │       │   replicas: {{ .Values.    │
  │   repository: nginx  │──────▶│     replicaCount }}        │
  │   tag: "1.25"        │       │   containers:              │
  │ service:             │       │   - image: "{{ .Values.    │
  │   type: ClusterIP    │──────▶│     image.repository }}:   │
  │   port: 80           │       │     {{ .Values.image.tag }}"│
  └──────────────────────┘       └────────────────────────────┘
           │                                │
           ▼                                ▼
     覆盖方式:                     渲染结果:
     -f prod.yaml                  replicas: 3
     --set image.tag=1.26          image: "nginx:1.25"
""",
        example_yaml="""\
# values.yaml — Helm chart 默认配置
replicaCount: 3              # Pod 副本数

image:                       # 镜像配置
  repository: nginx          # 镜像仓库
  tag: "1.25"               # 镜像标签
  pullPolicy: IfNotPresent   # 拉取策略

service:                     # Service 配置
  type: ClusterIP            # Service 类型
  port: 80                   # Service 端口

resources:                   # 资源限制
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
""",
        common_errors=[
            "tag 用数字而非字符串（如 tag: 1.25 会被解析为浮点数，应加引号 tag: \"1.25\"）",
            "嵌套层级缩进错误导致 image.repository 变成顶层字段",
            "忘记 values 文件与模板中 .Values.xxx 的路径必须完全对应",
            "把 values.yaml 的字段名与 Chart.yaml 的字段名搞混",
        ],
        tips=[
            "用 helm show values <chart-name> 查看已有 chart 的默认 values",
            "用 --dry-run 渲染模板而不实际部署：helm install --dry-run my-app ./my-chart",
            "建议将生产配置和开发配置分别放在不同的 values 文件中",
        ],
    ),
)


# ==================== Q19.3 Helm 模板渲染 ====================

def _check_193_template_rendering(user_yaml: str) -> CheckResult:
    """Q19.3 Helm 模板渲染 - 验证模板中使用了 Helm 模板函数"""
    # 检查是否包含 Helm 模板语法
    if "{{" not in user_yaml or "}}" not in user_yaml:
        return CheckResult(
            ok=False,
            error="模板中未使用 Helm 模板语法 {{ }}",
            hints=["使用 {{ .Values.xxx }} 引用 values 中的值"],
        )

    # 检查 .Values 引用
    if ".Values." not in user_yaml:
        return CheckResult(
            ok=False,
            error="模板中未使用 .Values 引用",
            hints=["用 {{ .Values.replicaCount }} 引用 values 中的值"],
        )

    # 检查 .Release 引用
    if ".Release." not in user_yaml:
        return CheckResult(
            ok=False,
            error="模板中未使用 .Release 引用",
            hints=["用 {{ .Release.Name }} 引用 release 名称"],
        )

    # 检查模板是否为有效 YAML 结构（忽略 {{ }} 占位符）
    # 用占位符替换 {{ }} 内容来验证 YAML 结构
    sanitized = re.sub(r"\{\{[^}]*\}\}", "placeholder", user_yaml)
    try:
        docs = list(yaml.safe_load_all(sanitized))
    except yaml.YAMLError as e:
        return CheckResult(
            ok=False,
            error=f"模板的 YAML 结构无效：{e}",
            hints=["确保模板在渲染后是合法的 YAML"],
        )

    # 检查是否包含 K8s 资源定义
    found_kind = False
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind"):
            found_kind = True
            break

    if not found_kind:
        return CheckResult(
            ok=False,
            error="模板中未找到 K8s 资源定义（缺少 kind 字段）",
            hints=["模板应包含 kind: Deployment 等 K8s 资源类型"],
        )

    return CheckResult(
        ok=True,
        hints=["模板使用了 .Values 和 .Release 引用，渲染后会生成 K8s 资源 🎨"],
    )


LEVEL_Q19_3 = Level(
    id="Q19.3",
    chapter="ch19",
    title="Helm 模板渲染",
    description="""
# Helm 模板渲染 🎨

Helm 模板使用 Go template 语法，在 `helm install` 时将模板渲染为最终的 K8s YAML。通过 `.Values`、`.Release`、`.Chart` 等内置对象实现参数化。

## 任务

编写一个 **Deployment 模板**，使用以下模板函数：
- `{{ .Release.Name }}` — 引用 release 名称
- `{{ .Values.replicaCount }}` — 引用 values 中的副本数
- `{{ .Values.image.repository }}` 和 `{{ .Values.image.tag }}` — 引用镜像配置

## 提示

模板在渲染时会把 `{{ }}` 替换为实际值：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-deploy
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: web
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: # {{ .Release.Name }}-deploy
spec:
  # replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
      - name: web
        # image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
""",
    check_fn=_check_193_template_rendering,
    lesson=Lesson(
        concept="""\
## Helm 模板渲染

Helm 模板使用 **Go template** 语法，在安装时渲染为最终的 K8s YAML 清单。

### 内置对象

Helm 提供了多个内置对象，可在模板中引用：

| 对象 | 说明 | 示例 |
|------|------|------|
| `.Values` | values.yaml 中的值 | `{{ .Values.replicaCount }}` |
| `.Release` | Release 信息 | `{{ .Release.Name }}` |
| `.Chart` | Chart.yaml 中的值 | `{{ .Chart.Name }}` |
| `.Template` | 模板自身信息 | `{{ .Template.Name }}` |
| `.Files` | chart 中的文件 | `{{ .Files.Get "config.txt" }}` |
| `.Capabilities` | 集群能力 | `{{ .Capabilities.KubeVersion }}` |

### .Release 对象字段

- `.Release.Name` — release 名称
- `.Release.Namespace` — 目标命名空间
- `.Release.Service` — 执行安装的服务（通常是 Helm）
- `.Release.Revision` — release 修订版本号
- `.Release.IsInstall` — 是否为首次安装
- `.Release.IsUpgrade` — 是否为升级操作

### 常用模板函数

```yaml
# 引用 values
image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"

# 条件判断
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
...
{{- end }}

# 循环
{{- range .Values.extraEnv }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}

# 管道函数
name: {{ .Values.name | default "my-app" | quote }}

# include 引用辅助模板
{{ include "my-app.labels" . }}
```

### 模板渲染流程

```
values.yaml + Chart.yaml + templates/*.yaml
              │
              ▼
    helm template 命令
              │
              ▼
    渲染后的 K8s YAML（纯 YAML，无 {{ }}）
              │
              ▼
    kubectl apply（由 helm 自动执行）
```
""",
        key_fields=[
            {"name": ".Values", "description": "引用 values.yaml 中的配置值", "required": True, "example": "{{ .Values.replicaCount }}"},
            {"name": ".Release.Name", "description": "当前 release 的名称", "required": True, "example": "{{ .Release.Name }}"},
            {"name": ".Chart", "description": "引用 Chart.yaml 中的元数据", "required": False, "example": "{{ .Chart.Name }}"},
            {"name": "条件判断", "description": "if/else 控制资源生成", "required": False, "example": "{{- if .Values.enabled }}...{{- end }}"},
            {"name": "管道函数", "description": "对值进行转换处理", "required": False, "example": "{{ .Values.name | quote }}"},
        ],
        diagram="""\
  Helm 模板渲染流程

  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐
  │   values.yaml   │   │   Chart.yaml    │   │  templates/      │
  │                 │   │                 │   │  deployment.yaml │
  │ replicaCount: 3 │   │ name: my-app    │   │                  │
  │ image:          │   │ version: 0.1.0  │   │ kind: Deployment │
  │   repository:   │   │                 │   │ metadata:        │
  │     nginx       │   └─────────────────┘   │   name: {{ .Re-  │
  │   tag: "1.25"   │                         │     lease.Name }}│
  └─────────────────┘                         │ spec:            │
         │                                    │   replicas:      │
         │  .Values                           │   {{ .Values.    │
         └─────────────────────────────────▶ │     replicaCount}}│
                                              │   containers:    │
                         .Chart ──────────▶  │   - image: {{...}}│
                                              └────────┬─────────┘
                       .Release ──────────────────────┘
                                                       │
                                                       ▼
                                              helm template 渲染
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │ 最终 K8s YAML     │
                                              │ (无 {{ }} 占位符) │
                                              └──────────────────┘
""",
        example_yaml="""\
# templates/deployment.yaml — Helm 模板文件
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-deploy       # 引用 release 名称
  labels:
    app: {{ .Release.Name }}
    chart: {{ .Chart.Name }}-{{ .Chart.Version }}  # 引用 chart 信息
spec:
  replicas: {{ .Values.replicaCount }}   # 引用 values 中的副本数
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
      - name: web
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: {{ .Values.service.port }}
""",
        common_errors=[
            "忘记引号：image: {{ .Values.image }} 会被解析为空（应加引号 image: \"{{ ... }}\"）",
            ".Values.xxx 路径与 values.yaml 中的层级不匹配",
            "模板渲染后不是合法的 YAML（如多余的空行、缩进错误）",
            "混淆 .Release.Name 和 .Chart.Name：前者是 release 实例名，后者是 chart 名称",
        ],
        tips=[
            "用 helm template my-release ./my-chart 在本地预览渲染结果",
            "用 --debug 查看 helm 渲染过程中的详细信息",
            "在模板中使用 {{- 和 -}} 可以去除前后空白（防止渲染后的 YAML 有多余空行）",
        ],
    ),
)


# ==================== Q19.4 Helm 依赖管理 ====================

def _check_194_dependencies(user_yaml: str) -> CheckResult:
    """Q19.4 Helm 依赖管理 - 验证 Chart.yaml 中的 dependencies"""
    try:
        doc = yaml.safe_load(user_yaml)
    except yaml.YAMLError as e:
        return CheckResult(ok=False, error=f"YAML 解析失败：{e}", hints=[])

    if doc is None or not isinstance(doc, dict):
        return CheckResult(
            ok=False,
            error="YAML 内容为空或格式错误",
            hints=["Chart.yaml 必须是一个 YAML 映射"],
        )

    # 检查 dependencies 存在
    dependencies = doc.get("dependencies")
    if not dependencies:
        return CheckResult(
            ok=False,
            error="Chart.yaml 缺少 dependencies",
            hints=["添加 dependencies 列表"],
        )

    if not isinstance(dependencies, list) or not dependencies:
        return CheckResult(
            ok=False,
            error="dependencies 必须是非空列表",
            hints=["dependencies: [{ name: redis, version: 17.0.0, repository: ... }]"],
        )

    # 检查每个依赖
    for i, dep in enumerate(dependencies):
        if not isinstance(dep, dict):
            return CheckResult(
                ok=False,
                error=f"dependencies[{i}] 必须是映射（dict）",
                hints=[],
            )
        if not dep.get("name"):
            return CheckResult(
                ok=False,
                error=f"dependencies[{i}] 缺少 name",
                hints=["每个依赖必须有 name 字段"],
            )
        if not dep.get("version"):
            return CheckResult(
                ok=False,
                error=f"dependencies[{i}] 缺少 version",
                hints=["每个依赖必须有 version 字段"],
            )
        if not dep.get("repository"):
            return CheckResult(
                ok=False,
                error=f"dependencies[{i}] 缺少 repository",
                hints=["每个依赖必须有 repository 字段（chart 仓库 URL）"],
            )

    # 至少需要一个依赖
    return CheckResult(
        ok=True,
        hints=["dependencies 配置正确！子 chart 会被下载到 charts/ 目录 🔗"],
    )


LEVEL_Q19_4 = Level(
    id="Q19.4",
    chapter="ch19",
    title="Helm 依赖管理",
    description="""
# Helm 依赖管理 🔗

一个 Helm Chart 可以依赖其他 chart（子 chart），在 `Chart.yaml` 中通过 `dependencies` 字段声明。

## 任务

编写一个 **Chart.yaml**，包含以下内容：
- 基本信息字段（apiVersion、name、version）
- `dependencies` 列表，至少包含一个子 chart 依赖：
  - `name: redis`
  - `version: 17.0.0`
  - `repository: https://charts.bitnami.com/bitnami`

## 提示

dependencies 声明了 chart 所需的子 chart：
```yaml
apiVersion: v2
name: my-app
version: 0.1.0
dependencies:
  - name: redis
    version: 17.0.0
    repository: https://charts.bitnami.com/bitnami
```
""",
    starter_yaml="""\
apiVersion: v2
name: my-app
version: 0.1.0
# dependencies:
#   - name: redis
#     version: 17.0.0
#     repository: https://charts.bitnami.com/bitnami
""",
    check_fn=_check_194_dependencies,
    lesson=Lesson(
        concept="""\
## Helm 依赖管理

Helm 允许 chart 声明对其他 chart 的**依赖关系**，这些子 chart 会被自动下载并随父 chart 一起安装。

### dependencies 字段

在 `Chart.yaml` 中通过 `dependencies` 声明子 chart：

```yaml
dependencies:
  - name: redis              # 子 chart 名称
    version: 17.0.0          # 子 chart 版本范围
    repository: https://charts.bitnami.com/bitnami  # 仓库 URL
    condition: redis.enabled # 条件：values 中的字段控制是否启用
    alias: cache             # 别名（同一 chart 可安装多次）
    import-values:           # 导入子 chart 的 values
      - child: defaults
        parent: redisDefaults
```

### 依赖管理命令

```bash
# 下载依赖到 charts/ 目录
helm dependency update ./my-chart

# 列出依赖
helm dependency list ./my-chart

# 从 Chart.yaml 重建 Chart.lock
helm dependency build ./my-chart
```

### 子 chart 的 Values 覆盖

父 chart 可以通过 values 覆盖子 chart 的配置：

```yaml
# 父 chart 的 values.yaml
redis:
  enabled: true              # 启用子 chart
  auth:
    enabled: false           # 覆盖子 chart 的 auth 配置
  replica:
    replicaCount: 3          # 覆盖副本数
```

### condition 和 tags

通过 `condition` 和 `tags` 控制子 chart 是否安装：

```yaml
# Chart.yaml
dependencies:
  - name: redis
    version: 17.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled    # values 中 redis.enabled 为 true 才安装
    tags:
      - cache                   # 用 --set tags.cache=false 禁用
```

### Chart.lock

`helm dependency update` 会生成 `Chart.lock` 文件，锁定依赖的确切版本，类似于 `package-lock.json` 或 `go.sum`。
""",
        key_fields=[
            {"name": "dependencies", "description": "子 chart 依赖列表", "required": True, "example": "[{name: redis, ...}]"},
            {"name": "dependencies[].name", "description": "子 chart 名称", "required": True, "example": "redis"},
            {"name": "dependencies[].version", "description": "子 chart 版本范围", "required": True, "example": "17.0.0"},
            {"name": "dependencies[].repository", "description": "Chart 仓库 URL", "required": True, "example": "https://charts.bitnami.com/bitnami"},
            {"name": "dependencies[].condition", "description": "条件控制是否安装子 chart", "required": False, "example": "redis.enabled"},
            {"name": "dependencies[].alias", "description": "别名，允许同一 chart 安装多次", "required": False, "example": "cache"},
        ],
        diagram="""\
  Helm 依赖管理结构

  ┌──────────────── Parent Chart (my-app) ────────────────┐
  │                                                        │
  │  Chart.yaml                                            │
  │  ┌──────────────────────────────────────┐             │
  │  │ apiVersion: v2                       │             │
  │  │ name: my-app                         │             │
  │  │ version: 0.1.0                       │             │
  │  │ dependencies:                        │             │
  │  │   - name: redis                      │             │
  │  │     version: 17.0.0                  │             │
  │  │     repository: https://...          │             │
  │  │     condition: redis.enabled         │             │
  │  └──────────────────────────────────────┘             │
  │                                                        │
  │  values.yaml                                           │
  │  ┌──────────────────────────────────────┐             │
  │  │ redis:                               │             │
  │  │   enabled: true  ← condition 控制    │             │
  │  │   auth:                              │             │
  │  │     enabled: false ← 覆盖子 chart    │             │
  │  └──────────────────────────────────────┘             │
  │                                                        │
  │  charts/           ← helm dependency update 下载       │
  │  ┌──────────────────────────────────────┐             │
  │  │ redis-17.0.0.tgz                     │             │
  │  └──────────────────────────────────────┘             │
  │                                                        │
  │  Chart.lock        ← 版本锁定                          │
  │  ┌──────────────────────────────────────┐             │
  │  │ dependencies:                        │             │
  │  │   - name: redis                      │             │
  │  │     version: 17.0.0                  │             │
  │  │     repository: https://...          │             │
  │  └──────────────────────────────────────┘             │
  │                                                        │
  └────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v2              # Chart API 版本
name: my-app               # 父 chart 名称
version: 0.1.0            # 父 chart 版本
description: My application with Redis dependency
type: application

dependencies:              # 子 chart 依赖列表
  - name: redis            # 子 chart 名称
    version: 17.0.0        # 子 chart 版本
    repository: https://charts.bitnami.com/bitnami  # 仓库 URL
    condition: redis.enabled  # 条件: values 中 redis.enabled 控制
    import-values:         # 导入子 chart values
      - child: defaults
        parent: redisDefaults
""",
        common_errors=[
            "忘记执行 helm dependency update，导致 charts/ 目录为空",
            "repository URL 写错，导致 helm 找不到子 chart",
            "version 写成范围表达式但格式不对（如 17.x 而非 17.x.x 或 ^17.0.0）",
            "condition 字段路径与 values.yaml 中的层级不匹配",
        ],
        tips=[
            "用 helm dependency update ./my-chart 下载依赖到 charts/ 目录",
            "用 helm dependency list ./my-chart 查看已声明的依赖",
            "Chart.lock 应该提交到版本控制，确保可重复构建",
        ],
    ),
)


# ==================== Q19.5 集群实战 - 部署完整 Helm Chart ====================

def _check_195_deploy_chart(user_yaml: str) -> CheckResult:
    """Q19.5 集群实战 - 部署完整 Helm Chart（渲染后的 K8s 资源）"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查是否有 Deployment
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="缺少 Deployment",
            hints=["Helm chart 渲染后应包含 Deployment 资源"],
        )

    # 检查是否有 Service
    if not state.services:
        return CheckResult(
            ok=False,
            error="缺少 Service",
            hints=["Helm chart 渲染后应包含 Service 资源"],
        )

    # 检查 Deployment 基本配置
    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {})
    if not isinstance(dep_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    replicas = dep_spec.get("replicas")
    if replicas is None:
        return CheckResult(
            ok=False,
            error="Deployment 缺少 replicas",
            hints=["Helm 渲染后的 Deployment 应包含 replicas"],
        )

    # 检查 Service 配置
    svc_name = next(iter(state.services))
    svc = state.services[svc_name]
    svc_spec = svc.get("spec", {})
    if not isinstance(svc_spec, dict):
        return CheckResult(ok=False, error="Service 缺少 spec", hints=[])

    ports = svc_spec.get("ports")
    if not isinstance(ports, list) or not ports:
        return CheckResult(
            ok=False,
            error="Service 缺少 ports",
            hints=["Service 应包含 ports 配置"],
        )

    # 检查 Deployment 和 Service 的 selector 匹配
    dep_template_labels = dep_spec.get("template", {}).get("metadata", {}).get("labels", {})
    svc_selector = svc_spec.get("selector", {})
    if isinstance(dep_template_labels, dict) and isinstance(svc_selector, dict):
        if svc_selector and not all(dep_template_labels.get(k) == v for k, v in svc_selector.items()):
            return CheckResult(
                ok=False,
                error="Service selector 与 Deployment Pod labels 不匹配",
                hints=["确保 Service selector 能匹配到 Deployment 的 Pod"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "Helm chart 渲染后的资源校验通过！在真实集群上执行：",
            "  helm install my-release ./my-chart",
            "  helm list                       # 查看 release",
            "  helm status my-release          # 查看 release 状态",
            "  helm uninstall my-release       # 卸载 release",
        ],
    )


LEVEL_Q19_5 = Level(
    id="Q19.5",
    chapter="ch19",
    title="集群实战: 部署完整 Helm Chart",
    description="""
# 集群实战: 部署完整 Helm Chart 🏗️

将 Helm chart 模板渲染后的 K8s 资源部署到集群！

## 任务

编写多文档 YAML，包含 Helm chart 渲染后的完整应用：
1. **Deployment** — 应用工作负载（含 replicas、image、labels）
2. **Service** — 对外暴露服务（含 selector、ports）

确保 Deployment 的 Pod labels 与 Service 的 selector 匹配。

## 验证步骤

```bash
# 方式一: 用 helm 直接安装 chart
helm install my-release ./my-chart
helm list
helm status my-release

# 方式二: 先渲染再 kubectl apply
helm template my-release ./my-chart > rendered.yaml
kubectl apply -f rendered.yaml

# 查看
kubectl get deployments
kubectl get services
kubectl get pods

# 升级
helm upgrade my-release ./my-chart -f prod-values.yaml

# 回滚
helm rollback my-release 1

# 卸载
helm uninstall my-release
```
""",
    starter_yaml="""\
# --- Deployment (Helm 渲染后) ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-release-web
  labels:
    app: my-release-web
spec:
  # replicas: 3
  selector:
    matchLabels:
      app: my-release-web
  template:
    metadata:
      labels:
        app: my-release-web
    spec:
      containers:
      - name: web
        # image: nginx:1.25
        ports:
        - containerPort: 80
---
# --- Service (Helm 渲染后) ---
apiVersion: v1
kind: Service
metadata:
  name: my-release-web
spec:
  # type: ClusterIP
  selector:
    app: my-release-web
  ports:
  - port: 80
    # targetPort: 80
""",
    check_fn=_check_195_deploy_chart,
    lesson=Lesson(
        concept="""\
## Helm Chart 部署实战

在真实集群中使用 Helm chart 的完整生命周期管理。

### Helm 生命周期命令

```bash
# 安装 chart（创建 release）
helm install <release-name> <chart-path>

# 查看已安装的 release
helm list
helm list --all-namespaces

# 查看 release 状态
helm status <release-name>

# 升级 release（修改配置或更新版本）
helm upgrade <release-name> <chart-path> -f new-values.yaml

# 查看 release 历史
helm history <release-name>

# 回滚到指定版本
helm rollback <release-name> <revision>

# 卸载 release
helm uninstall <release-name>
```

### helm install 详解

```bash
helm install my-app ./my-chart \
  --namespace production \           # 指定命名空间
  --create-namespace \               # 不存在则创建
  -f prod-values.yaml \              # 使用自定义 values
  --set image.tag=1.26 \             # 覆盖单个值
  --set replicaCount=5 \             # 覆盖另一个值
  --dry-run \                        # 预览渲染结果
  --debug                            # 调试输出
```

### Helm vs kubectl

| 特性 | Helm | kubectl |
|------|------|---------|
| 部署方式 | chart 打包部署 | 单个 YAML 文件 |
| 版本管理 | release 修订历史 | 无（需手动管理） |
| 配置覆盖 | values + --set | 手动修改 YAML |
| 回滚 | helm rollback | 需要重新 apply |
| 依赖管理 | 子 chart 自动下载 | 无 |
| 模板渲染 | Go template | 无 |

### 生产环境最佳实践

1. **使用 Chart.lock**：锁定依赖版本
2. **分离 values 文件**：dev-values.yaml、prod-values.yaml
3. **CI/CD 集成**：用 helm template + kubectl apply 实现 GitOps
4. **命名空间隔离**：每个环境使用独立命名空间
5. **资源限制**：在 values 中配置 resources
6. **健康检查**：在模板中包含 livenessProbe/readinessProbe
""",
        key_fields=[
            {"name": "Deployment.replicas", "description": "Pod 副本数", "required": True, "example": "3"},
            {"name": "Deployment.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
            {"name": "Service.selector", "description": "匹配 Pod labels", "required": True, "example": "{app: my-release-web}"},
            {"name": "Service.ports[].port", "description": "Service 端口", "required": True, "example": "80"},
            {"name": "selector 匹配", "description": "Service selector 与 Pod labels 一致", "required": True, "example": "app: my-release-web"},
        ],
        diagram="""\
  Helm Chart 部署全流程

  ┌─────────────── Helm Chart ───────────────┐
  │  Chart.yaml    values.yaml   templates/  │
  └───────────────────┬──────────────────────┘
                      │
                      ▼
           helm install my-release ./my-chart
                      │
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
     ┌─────────────┐    ┌─────────────┐
     │ Deployment   │    │ Service     │
     │ my-release-  │    │ my-release- │
     │ web          │    │ web         │
     │ replicas: 3  │    │ port: 80    │
     │ labels:      │◄──▶│ selector:   │
     │   app: ...   │    │   app: ...  │
     └──────┬───────┘    └─────────────┘
            │
     ┌──────┼──────┐
     ▼      ▼      ▼
   Pod-0  Pod-1  Pod-2

  helm list           → 查看 release
  helm status         → 查看状态
  helm upgrade        → 升级
  helm rollback       → 回滚
  helm uninstall      → 卸载
""",
        example_yaml="""\
# --- Deployment (Helm 渲染后) ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-release-web
  labels:
    app: my-release-web
    chart: my-web-app-0.1.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-release-web
  template:
    metadata:
      labels:
        app: my-release-web
    spec:
      containers:
      - name: web
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
---
# --- Service (Helm 渲染后) ---
apiVersion: v1
kind: Service
metadata:
  name: my-release-web
spec:
  type: ClusterIP
  selector:
    app: my-release-web
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
""",
        common_errors=[
            "Deployment Pod labels 与 Service selector 不匹配，导致 Service 没有 endpoints",
            "忘记 helm dependency update 导致子 chart 缺失",
            "helm install 时命名空间不存在（加 --create-namespace）",
            "values 中的值与模板路径不匹配，导致渲染出空值",
        ],
        tips=[
            "用 helm status <release> 查看 release 的资源和状态",
            "用 helm get values <release> 查看当前 release 使用的 values",
            "用 helm get manifest <release> 查看已部署的渲染后 YAML",
            "helm rollback 可以快速回滚到历史版本，无需手动修改 YAML",
        ],
    ),
)


CHAPTER_19_LEVELS: list[Level] = [
    LEVEL_Q19_1, LEVEL_Q19_2, LEVEL_Q19_3, LEVEL_Q19_4, LEVEL_Q19_5,
]
