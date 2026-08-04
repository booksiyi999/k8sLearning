"""Chapter 23: 监控与日志（Monitoring & Logging）（5 关）

Q23.1 Prometheus ServiceMonitor - 监控配置
Q23.2 Grafana Dashboard ConfigMap - 可视化配置
Q23.3 Fluent Bit DaemonSet - 日志采集
Q23.4 告警规则 - PrometheusRule
Q23.5 集群实战 - 完整监控日志栈
"""
import yaml
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q23.1 Prometheus ServiceMonitor ====================

def _check_231_service_monitor(user_yaml: str) -> CheckResult:
    """Q23.1 创建一个 ServiceMonitor 让 Prometheus 自动发现并抓取 metrics"""
    # ServiceMonitor 是 Prometheus Operator 的 CRD，模拟器不支持直接 apply，
    # 我们先尝试注册 CRD 再 apply，若失败则直接解析 YAML
    crd_yaml = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: servicemonitors.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  names:
    kind: ServiceMonitor
    plural: servicemonitors
    singular: servicemonitor
  scope: Namespaced
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

    # ServiceMonitor 会存入 customresources
    sm_docs = [
        doc for doc in state.customresources.values()
        if doc.get("kind") == "ServiceMonitor"
    ]
    if not sm_docs:
        return CheckResult(
            ok=False,
            error="没有创建任何 ServiceMonitor",
            hints=["你需要 apply 一个 kind: ServiceMonitor 的 YAML 📊"],
        )

    sm = sm_docs[0]
    spec = sm.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="ServiceMonitor 缺少 spec", hints=[])

    # 检查 selector
    selector = spec.get("selector", {})
    if not isinstance(selector, dict) or not selector:
        return CheckResult(
            ok=False,
            error="ServiceMonitor 缺少 spec.selector",
            hints=["spec.selector 用于选择要监控的 Service，通过 labels 匹配"],
        )

    match_labels = selector.get("matchLabels", {})
    if not isinstance(match_labels, dict) or not match_labels:
        return CheckResult(
            ok=False,
            error="ServiceMonitor 的 spec.selector 缺少 matchLabels",
            hints=["selector.matchLabels 定义要匹配的标签，如 app: nginx"],
        )

    # 检查 endpoints
    endpoints = spec.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        return CheckResult(
            ok=False,
            error="ServiceMonitor 缺少 spec.endpoints",
            hints=["spec.endpoints 定义 Prometheus 抓取配置，至少需要一个端点"],
        )

    ep = endpoints[0]
    if not isinstance(ep, dict):
        return CheckResult(ok=False, error="endpoints[0] 格式错误", hints=[])

    # 检查 port 或 targetPort
    port = ep.get("port") or ep.get("targetPort")
    if not port:
        return CheckResult(
            ok=False,
            error="endpoints[0] 缺少 port 字段",
            hints=["每个 endpoint 需要指定 port（Service 端口名）或 targetPort"],
        )

    # 检查 interval（可选但推荐）
    interval = ep.get("interval")
    if interval:
        if not isinstance(interval, str):
            return CheckResult(
                ok=False,
                error=f"interval 应为字符串（如 '30s'），实际为 {type(interval).__name__}",
                hints=["interval 格式如 '30s', '1m', '5m'"],
            )

    # 检查 apiVersion
    api_version = sm.get("apiVersion", "")
    if "monitoring.coreos.com" not in api_version:
        return CheckResult(
            ok=False,
            error=f"apiVersion 应包含 'monitoring.coreos.com'，实际为 '{api_version}'",
            hints=["ServiceMonitor 的 apiVersion 通常为 monitoring.coreos.com/v1"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！ServiceMonitor 让 Prometheus Operator 自动发现并抓取目标服务的指标 📊"],
    )


LEVEL_Q23_1 = Level(
    id="Q23.1",
    chapter="ch23",
    title="创建 ServiceMonitor",
    description="""
# 创建 ServiceMonitor 📊

**ServiceMonitor** 是 Prometheus Operator 提供的自定义资源，用于**声明式**定义 Prometheus 应该抓取哪些服务的指标。

## 任务

创建一个 ServiceMonitor，监控带有 `app: web` 标签的 Service：
- `kind: ServiceMonitor`
- `apiVersion: monitoring.coreos.com/v1`
- `spec.selector.matchLabels` 匹配 `app: web`
- `spec.endpoints` 指定抓取端口和间隔

## 提示

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: web-monitor
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: web
  endpoints:
  - port: http
    interval: 30s
```
""",
    starter_yaml="""\
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: web-monitor
  labels:
    release: prometheus
spec:
  # selector: 匹配要监控的 Service
  # endpoints: 定义抓取配置
""",
    check_fn=_check_231_service_monitor,
    lesson=Lesson(
        concept="""\
## 什么是 ServiceMonitor？

**ServiceMonitor** 是 [Prometheus Operator](https://prometheus-operator.dev/) 提供的 CRD（自定义资源定义），让你用**声明式**的方式管理 Prometheus 的抓取目标。

### 核心价值

- **声明式配置**：用 YAML 定义监控目标，而非手动修改 prometheus.yml
- **自动发现**：Prometheus Operator 自动 watch ServiceMonitor 变化并更新配置
- **标签选择**：通过 `selector.matchLabels` 自动匹配 Service
- **多端点支持**：一个 ServiceMonitor 可以定义多个抓取端点

### 工作流程

```
1. 创建 Service（带 labels）
2. 创建 ServiceMonitor（selector 匹配 Service labels）
3. Prometheus Operator 发现 ServiceMonitor
4. Prometheus 自动开始抓取目标 Service 的 /metrics
```

### ServiceMonitor vs 传统配置

| 方式 | 配置位置 | 更新方式 | 适用场景 |
|------|---------|---------|---------|
| 传统 prometheus.yml | 配置文件 | 手动 reload | 独立 Prometheus |
| ServiceMonitor | K8s CRD | Operator 自动更新 | Prometheus Operator |

### endpoints 常用字段

- `port`：要抓取的 Service 端口名（不是端口号）
- `interval`：抓取间隔，如 `30s`、`1m`
- `path`：指标路径，默认 `/metrics`
- `scrapeTimeout`：抓取超时
- `scheme`：`http` 或 `https`
""",
        key_fields=[
            {"name": "spec.selector", "description": "标签选择器，匹配要监控的 Service", "required": True, "example": "selector: { matchLabels: { app: web } }"},
            {"name": "spec.endpoints", "description": "抓取端点列表，定义如何抓取指标", "required": True, "example": "[{port: http, interval: 30s}]"},
            {"name": "spec.endpoints[].port", "description": "Service 端口名（非数字端口号）", "required": True, "example": "http"},
            {"name": "spec.endpoints[].interval", "description": "抓取间隔", "required": False, "example": "30s"},
            {"name": "metadata.labels.release", "description": "用于被 Prometheus 实例选择的标签", "required": False, "example": "prometheus"},
        ],
        diagram="""\
┌──────────── ServiceMonitor ─────────────────┐
│  spec:                                      │
│    selector:                                │
│      matchLabels:                           │
│        app: web                             │
│    endpoints:                               │
│    - port: http                             │
│      interval: 30s                          │
│      path: /metrics                         │
└──────────────────┬──────────────────────────┘
                   │ 标签匹配 app=web
                   ▼
┌──────────── Service (web) ──────────────────┐
│  metadata.labels.app: web                   │
│  spec.ports: [{name: http, port: 80}]       │
└──────────────────┬──────────────────────────┘
                   │ Prometheus 抓取 /metrics
                   ▼
            ┌──────────────┐
            │  Prometheus  │
            │  TSDB 存储    │
            └──────────────┘
""",
        example_yaml="""\
apiVersion: monitoring.coreos.com/v1   # Prometheus Operator CRD
kind: ServiceMonitor                   # 资源类型
metadata:                              # 元数据
  name: web-monitor                    # 名称
  labels:                              # 标签
    release: prometheus                # 用于 Prometheus 选择
spec:                                  # 规格定义
  selector:                            # Service 选择器
    matchLabels:                       # 标签匹配
      app: web                         # 匹配 app=web 的 Service
  endpoints:                           # 抓取端点列表
  - port: http                         # Service 端口名
    interval: 30s                      # 抓取间隔
    path: /metrics                     # 指标路径（默认）
    scrapeTimeout: 10s                 # 抓取超时
""",
        common_errors=[
            "port 写成数字端口号（如 80）而非端口名（如 http）",
            "selector.matchLabels 不匹配目标 Service 的标签，导致 Prometheus 抓取不到数据",
            "忘记在 metadata.labels 中设置 release 标签，导致 Prometheus 实例不选择此 ServiceMonitor",
            "apiVersion 写错，应为 monitoring.coreos.com/v1",
        ],
        tips=[
            "用 kubectl get servicemonitor 查看 ServiceMonitor 状态",
            "在 Prometheus Web UI 的 Status → Targets 中确认抓取目标已加入",
            "ServiceMonitor 的 selector 匹配的是 Service 的 labels，不是 Pod 的",
            "一个 ServiceMonitor 可以定义多个 endpoints，适合多端口服务",
        ],
    ),
)


# ==================== Q23.2 Grafana Dashboard ConfigMap ====================

def _check_232_grafana_dashboard(user_yaml: str) -> CheckResult:
    """Q23.2 创建一个 Grafana Dashboard ConfigMap"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.configmaps:
        return CheckResult(
            ok=False,
            error="没有创建任何 ConfigMap",
            hints=["你需要 apply 一个 kind: ConfigMap 的 YAML 📊"],
        )

    cm_name = next(iter(state.configmaps))
    cm = state.configmaps[cm_name]
    metadata = cm.get("metadata", {})
    labels = metadata.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}

    # 检查 grafana_dashboard 标签
    has_dashboard_label = (
        labels.get("grafana_dashboard") == "1"
        or labels.get("grafana_dashboard") == "true"
    )
    if not has_dashboard_label:
        return CheckResult(
            ok=False,
            error="ConfigMap 缺少 grafana_dashboard 标签",
            hints=["添加 labels: { grafana_dashboard: '1' } 让 Grafana 自动发现此 Dashboard"],
        )

    # 检查 data 中包含 dashboard JSON
    data = cm.get("data", {})
    if not isinstance(data, dict) or not data:
        return CheckResult(
            ok=False,
            error="ConfigMap 缺少 data 字段或 data 为空",
            hints=["data 中应包含 Dashboard 的 JSON 定义"],
        )

    # 至少有一个 key 包含 JSON 内容
    has_json = False
    for key, val in data.items():
        if isinstance(val, str) and ("dashboard" in val.lower() or "panels" in val.lower() or "title" in val.lower()):
            has_json = True
            break
    if not has_json:
        return CheckResult(
            ok=False,
            error="data 中未找到 Dashboard JSON 内容",
            hints=["data 的某个 key 应包含 Grafana Dashboard 的 JSON 定义（含 title/panels 等字段）"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！Grafana Sidecar 会自动加载带 grafana_dashboard 标签的 ConfigMap 📈"],
    )


LEVEL_Q23_2 = Level(
    id="Q23.2",
    chapter="ch23",
    title="Grafana Dashboard ConfigMap",
    description="""
# Grafana Dashboard ConfigMap 📈

**Grafana** 是流行的可视化平台，可以通过 **ConfigMap** 声明式管理 Dashboard。

## 任务

创建一个 Grafana Dashboard 的 ConfigMap：
- `kind: ConfigMap`
- `metadata.labels` 包含 `grafana_dashboard: "1"`
- `data` 中包含 Dashboard JSON 定义

## 提示

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-dashboard
  labels:
    grafana_dashboard: "1"
data:
  nginx-dashboard.json: |
    {
      "title": "Nginx Dashboard",
      "panels": [
        {
          "title": "Request Rate",
          "type": "graph",
          "datasource": "Prometheus"
        }
      ]
    }
```
""",
    starter_yaml="""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-dashboard
  labels:
    # grafana_dashboard: "1"
data:
  nginx-dashboard.json: |
    # 在此填写 Dashboard JSON
""",
    check_fn=_check_232_grafana_dashboard,
    lesson=Lesson(
        concept="""\
## Grafana Dashboard as ConfigMap

在 Kubernetes 环境中，推荐用 **ConfigMap** 管理 Grafana Dashboard，实现**声明式**的可视化配置。

### 工作原理

```
ConfigMap (grafana_dashboard: "1")
        │
        ▼
Grafana Sidecar (自动发现)
        │
        ▼
Grafana 自动加载 Dashboard
```

### Grafana Sidecar

[kiwigrid/grafana-sidecar](https://github.com/kiwigrid/grafana-sidecar) 是一个 Sidecar 容器，运行在 Grafana Pod 旁边：
- Watch 集群中带 `grafana_dashboard: "1"` 标签的 ConfigMap
- 自动将 Dashboard JSON 导入 Grafana
- ConfigMap 更新时自动同步 Dashboard

### Dashboard JSON 结构

```json
{
  "title": "Dashboard 名称",
  "panels": [
    {
      "title": "面板标题",
      "type": "graph|stat|table|...",
      "datasource": "Prometheus",
      "targets": [
        { "expr": "rate(http_requests_total[5m])" }
      ]
    }
  ],
  "templating": { ... },
  "time": { "from": "now-1h", "to": "now" }
}
```

### 标签约定

| 标签 | 值 | 作用 |
|------|---|------|
| `grafana_dashboard` | `"1"` | 标记为 Dashboard ConfigMap |
| `grafana_dashboard_folder` | 文件夹名 | 指定 Dashboard 存放的文件夹 |
""",
        key_fields=[
            {"name": "metadata.labels.grafana_dashboard", "description": "标记此 ConfigMap 为 Grafana Dashboard", "required": True, "example": '"1"'},
            {"name": "data.<key>.json", "description": "Dashboard JSON 定义，key 通常以 .json 结尾", "required": True, "example": '{"title": "My Dashboard", "panels": [...]}'},
            {"name": "metadata.labels.grafana_dashboard_folder", "description": "指定 Dashboard 存放的 Grafana 文件夹", "required": False, "example": "Monitoring"},
        ],
        diagram="""\
┌──────── ConfigMap (nginx-dashboard) ─────────┐
│  metadata:                                   │
│    labels:                                   │
│      grafana_dashboard: "1"   ◄── 关键标签   │
│  data:                                       │
│    nginx-dashboard.json: |                   │
│      { "title": "Nginx Dashboard", ... }     │
└───────────────────┬──────────────────────────┘
                    │ Sidecar Watch
                    ▼
┌──────── Grafana Pod ─────────────────────────┐
│  ┌──────────┐  ┌──────────────────────┐     │
│  │ Grafana  │  │ Grafana Sidecar      │     │
│  │ Server   │◄─│ (发现 & 同步 ConfigMap)│    │
│  └──────────┘  └──────────────────────┘     │
└──────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: v1                       # 核心 API
kind: ConfigMap                      # 资源类型
metadata:                            # 元数据
  name: nginx-dashboard              # 名称
  labels:                            # 标签
    grafana_dashboard: "1"           # 关键：标记为 Dashboard
    grafana_dashboard_folder: Monitoring  # 可选：指定文件夹
data:                                # 数据
  nginx-dashboard.json: |            # JSON 格式 Dashboard
    {
      "title": "Nginx Dashboard",
      "panels": [
        {
          "title": "Request Rate",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            { "expr": "rate(http_requests_total[5m])" }
          ]
        }
      ]
    }
""",
        common_errors=[
            "忘记添加 grafana_dashboard: '1' 标签，导致 Grafana Sidecar 不加载此 Dashboard",
            "data 的值不是合法 JSON，导致 Grafana 解析失败",
            "ConfigMap name 包含大写字母（K8s 命名规范要求小写）",
            "JSON 中 datasource 名称与实际配置的 Prometheus 数据源名称不匹配",
        ],
        tips=[
            "用 kubectl get configmap -l grafana_dashboard=1 查看所有 Dashboard",
            "Grafana Sidecar 默认每 10 秒扫描一次 ConfigMap 变更",
            "可以在 ConfigMap 中放多个 key（多个 JSON），每个 key 变成一个 Dashboard",
            "用 kubectl edit configmap 修改 Dashboard 会自动同步到 Grafana",
        ],
    ),
)


# ==================== Q23.3 Fluent Bit DaemonSet ====================

def _check_233_fluent_bit_daemonset(user_yaml: str) -> CheckResult:
    """Q23.3 创建 Fluent Bit 日志采集 DaemonSet"""
    try:
        state = ClusterState()
        # 预置节点
        state = preset_state(state, """\
apiVersion: v1
kind: Node
metadata:
  name: node-1
  labels:
    kubernetes.io/os: linux
---
apiVersion: v1
kind: Node
metadata:
  name: node-2
  labels:
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.daemonsets:
        return CheckResult(
            ok=False,
            error="没有创建任何 DaemonSet",
            hints=["你需要 apply 一个 kind: DaemonSet 的 YAML 📝"],
        )

    ds_name = next(iter(state.daemonsets))
    ds = state.daemonsets[ds_name]
    spec = ds.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="DaemonSet 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="DaemonSet 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    # 检查镜像是否为 fluent-bit
    image = c.get("image", "")
    if "fluent-bit" not in image.lower():
        return CheckResult(
            ok=False,
            error=f"容器镜像应为 fluent-bit 系列，实际为 '{image}'",
            hints=["使用 fluent/fluent-bit:3.0 或类似镜像"],
        )

    # 检查 hostPath 挂载（日志目录）
    volumes = tmpl_spec.get("volumes", [])
    if not isinstance(volumes, list) or not volumes:
        return CheckResult(
            ok=False,
            error="DaemonSet 缺少 volumes",
            hints=["Fluent Bit 需要挂载 /var/log 和 /var/lib/docker/containers 来读取容器日志"],
        )

    has_log_volume = False
    for vol in volumes:
        if not isinstance(vol, dict):
            continue
        host_path = vol.get("hostPath", {})
        path = ""
        if isinstance(host_path, dict):
            path = host_path.get("path", "")
        if "/var/log" in path or "docker/containers" in path:
            has_log_volume = True
            break

    if not has_log_volume:
        return CheckResult(
            ok=False,
            error="缺少日志目录的 hostPath 挂载",
            hints=["需要挂载 hostPath: /var/log 或 /var/lib/docker/containers 来读取容器日志"],
        )

    # 检查 volumeMounts
    volume_mounts = c.get("volumeMounts", [])
    if not isinstance(volume_mounts, list) or not volume_mounts:
        return CheckResult(
            ok=False,
            error="容器缺少 volumeMounts",
            hints=["需要将日志目录 volume 挂载到容器内"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！Fluent Bit DaemonSet 会在每个节点上运行，采集容器日志并发送到后端 📝"],
    )


LEVEL_Q23_3 = Level(
    id="Q23.3",
    chapter="ch23",
    title="Fluent Bit DaemonSet",
    description="""
# Fluent Bit DaemonSet 📝

**Fluent Bit** 是轻量级日志采集器，用 **DaemonSet** 部署确保每个节点都有一个日志采集 Pod。

## 任务

创建一个 Fluent Bit DaemonSet：
- `kind: DaemonSet`
- 容器镜像使用 `fluent/fluent-bit:3.0`
- 挂载 hostPath `/var/log` 到容器内读取节点日志
- 挂载对应的 volumeMounts

## 提示

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:3.0
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```
""",
    starter_yaml="""\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        # image: fluent/fluent-bit:3.0
        # volumeMounts: ...
      # volumes: ...
""",
    check_fn=_check_233_fluent_bit_daemonset,
    lesson=Lesson(
        concept="""\
## Fluent Bit DaemonSet 日志采集

**Fluent Bit** 是 [Fluentd 生态](https://fluentbit.io/) 中的轻量级日志处理器，专为 Kubernetes 日志采集设计。

### 为什么用 DaemonSet？

```
Node 1: [Fluent Bit Pod] ──读取──> /var/log/containers/*.log
Node 2: [Fluent Bit Pod] ──读取──> /var/log/containers/*.log
Node 3: [Fluent Bit Pod] ──读取──> /var/log/containers/*.log
         │              │              │
         └──────────────┴──────────────┘
                        │
                        ▼
              [Elasticsearch / Loki / Kafka]
```

DaemonSet 确保每个节点运行一个 Fluent Bit Pod，实现：
- **全节点覆盖**：不遗漏任何节点的日志
- **资源高效**：每个节点一个实例，不需要中央采集器
- **自动扩展**：新节点加入集群自动部署

### 容器日志位置

Kubernetes 容器日志默认存放在节点上：
- `/var/log/containers/` → 符号链接到实际日志文件
- `/var/lib/docker/containers/` → Docker JSON 日志
- `/var/log/pods/` → Pod 级别日志目录

### Fluent Bit 配置

Fluent Bit 通常通过 ConfigMap 配置：
```ini
[SERVICE]
    Flush         5
    Log_Level     info

[INPUT]
    Name          tail
    Path          /var/log/containers/*.log
    Parser        docker
    Tag           kube.*

[OUTPUT]
    Name          es
    Match         *
    Host          elasticsearch
    Port          9200
```

### hostPath 挂载要点

| 挂载路径 | 作用 |
|---------|------|
| `/var/log` | 节点日志目录 |
| `/var/lib/docker/containers` | Docker 容器日志 |
| `/etc/machine-id` | 节点标识 |
| `/var/lib/kubelet/pods` | Pod 元数据 |
""",
        key_fields=[
            {"name": "spec.template.spec.containers[].image", "description": "Fluent Bit 镜像", "required": True, "example": "fluent/fluent-bit:3.0"},
            {"name": "spec.template.spec.volumes[].hostPath", "description": "节点日志目录的 hostPath 挂载", "required": True, "example": "{path: /var/log}"},
            {"name": "spec.template.spec.containers[].volumeMounts", "description": "将 hostPath 挂载到容器内", "required": True, "example": "[{name: varlog, mountPath: /var/log}]"},
            {"name": "spec.selector", "description": "匹配 Pod 模板的标签", "required": True, "example": "{matchLabels: {app: fluent-bit}}"},
        ],
        diagram="""\
┌──────── DaemonSet (fluent-bit) ──────────────┐
│  spec:                                       │
│    template:                                 │
│      spec:                                   │
│        containers:                           │
│        - name: fluent-bit                    │
│          image: fluent/fluent-bit:3.0        │
│          volumeMounts:                       │
│          - name: varlog                      │
│            mountPath: /var/log               │
│        volumes:                              │
│        - name: varlog                        │
│          hostPath:                           │
│            path: /var/log                    │
└──────────────────┬───────────────────────────┘
                   │ DaemonSet → 每节点一个 Pod
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
  Node 1       Node 2       Node 3
  /var/log     /var/log     /var/log
     │             │             │
     └─────────────┴─────────────┘
                   │ 日志转发
                   ▼
           [Elasticsearch / Loki]
""",
        example_yaml="""\
apiVersion: apps/v1                  # DaemonSet API 版本
kind: DaemonSet                      # 资源类型
metadata:                            # 元数据
  name: fluent-bit                   # 名称
  labels:                            # 标签
    app: fluent-bit
spec:                                # 规格定义
  selector:                          # Pod 选择器
    matchLabels:
      app: fluent-bit
  template:                          # Pod 模板
    metadata:
      labels:
        app: fluent-bit
    spec:                            # Pod 规格
      containers:                    # 容器列表
      - name: fluent-bit             # 容器名
        image: fluent/fluent-bit:3.0 # Fluent Bit 镜像
        volumeMounts:                # 卷挂载
        - name: varlog               # 挂载名
          mountPath: /var/log        # 容器内路径
        - name: varlibdockerlogs
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:                       # 卷定义
      - name: varlog                 # 节点日志目录
        hostPath:
          path: /var/log
      - name: varlibdockerlogs       # Docker 容器日志
        hostPath:
          path: /var/lib/docker/containers
""",
        common_errors=[
            "忘记挂载 /var/log，Fluent Bit 无法读取容器日志",
            "hostPath 路径写错，如写成 /var/logs 或 /var/log/containers（应挂载父目录）",
            "volumeMounts 的 name 与 volumes 的 name 不匹配",
            "未设置 readOnly: true 挂载日志目录，可能导致意外的日志修改",
        ],
        tips=[
            "用 kubectl get ds fluent-bit -o wide 查看每个节点的 Pod 状态",
            "用 kubectl logs ds/fluent-bit 查看 Fluent Bit 自身日志",
            "Fluent Bit 配置通常通过 ConfigMap 挂载到 /fluent-bit/etc/fluent-bit.conf",
            "生产环境建议配合 resource limits 防止 Fluent Bit 占用过多节点资源",
        ],
    ),
)


# ==================== Q23.4 PrometheusRule 告警规则 ====================

def _check_234_prometheus_rule(user_yaml: str) -> CheckResult:
    """Q23.4 创建一个 PrometheusRule 定义告警规则"""
    # PrometheusRule 是 CRD，需要先注册
    crd_yaml = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: prometheusrules.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  names:
    kind: PrometheusRule
    plural: prometheusrules
    singular: promethestrule
  scope: Namespaced
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

    # PrometheusRule 会存入 customresources
    pr_docs = [
        doc for doc in state.customresources.values()
        if doc.get("kind") == "PrometheusRule"
    ]
    if not pr_docs:
        return CheckResult(
            ok=False,
            error="没有创建任何 PrometheusRule",
            hints=["你需要 apply 一个 kind: PrometheusRule 的 YAML 🔔"],
        )

    pr = pr_docs[0]
    spec = pr.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PrometheusRule 缺少 spec", hints=[])

    # 检查 groups
    groups = spec.get("groups")
    if not isinstance(groups, list) or not groups:
        return CheckResult(
            ok=False,
            error="PrometheusRule 缺少 spec.groups",
            hints=["spec.groups 是告警规则组列表，至少需要一个组"],
        )

    group = groups[0]
    if not isinstance(group, dict):
        return CheckResult(ok=False, error="groups[0] 格式错误", hints=[])

    # 检查 group name
    group_name = group.get("name")
    if not group_name:
        return CheckResult(
            ok=False,
            error="groups[0] 缺少 name",
            hints=["每个规则组需要一个 name 字段"],
        )

    # 检查 rules
    rules = group.get("rules")
    if not isinstance(rules, list) or not rules:
        return CheckResult(
            ok=False,
            error="groups[0] 缺少 rules",
            hints=["每个组需要包含至少一条告警规则"],
        )

    rule = rules[0]
    if not isinstance(rule, dict):
        return CheckResult(ok=False, error="rules[0] 格式错误", hints=[])

    # 检查 alert 名称
    alert_name = rule.get("alert")
    if not alert_name:
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 alert 字段",
            hints=["每条告警规则需要 alert 字段定义告警名称"],
        )

    # 检查 expr（PromQL 表达式）
    expr = rule.get("expr")
    if not expr:
        return CheckResult(
            ok=False,
            error="rules[0] 缺少 expr 字段",
            hints=["expr 是 PromQL 表达式，定义触发告警的条件"],
        )

    # 检查 for（持续时间，可选但推荐）
    for_duration = rule.get("for")
    if for_duration and not isinstance(for_duration, str):
        return CheckResult(
            ok=False,
            error=f"for 应为字符串（如 '5m'），实际为 {type(for_duration).__name__}",
            hints=["for 字段格式如 '5m', '1h'"],
        )

    # 检查 labels 和 annotations（可选但推荐）
    labels = rule.get("labels", {})
    annotations = rule.get("annotations", {})

    hints = ["干得漂亮！Prometheus Operator 会自动加载这些告警规则 🔔"]
    if not labels:
        hints.append("💡 建议添加 labels（如 severity: warning）方便告警分类和路由")
    if not annotations:
        hints.append("💡 建议添加 annotations（如 summary/description）提供告警详情")

    return CheckResult(ok=True, state=state, hints=hints)


LEVEL_Q23_4 = Level(
    id="Q23.4",
    chapter="ch23",
    title="PrometheusRule 告警规则",
    description="""
# PrometheusRule 告警规则 🔔

**PrometheusRule** 是 Prometheus Operator 的 CRD，让你用声明式方式管理告警规则。

## 任务

创建一个 PrometheusRule，定义一个 Pod 重启告警：
- `kind: PrometheusRule`
- `apiVersion: monitoring.coreos.com/v1`
- `spec.groups` 包含至少一个告警规则组
- 每个规则需要 `alert`、`expr` 字段
- 建议添加 `for`、`labels`、`annotations`

## 提示

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-alerts
  labels:
    prometheus: kube-prometheus
spec:
  groups:
  - name: pod.rules
    rules:
    - alert: PodRestartAlert
      expr: rate(kube_pod_container_status_restarts_total[5m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.pod }} 频繁重启"
        description: "Pod {{ $labels.pod }} 在过去 5 分钟内重启"
```
""",
    starter_yaml="""\
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-alerts
  labels:
    prometheus: kube-prometheus
spec:
  groups:
  - name: pod.rules
    rules:
    # - alert: PodRestartAlert
    #   expr: rate(kube_pod_container_status_restarts_total[5m]) > 0
    #   for: 5m
    #   labels:
    #     severity: warning
    #   annotations:
    #     summary: "Pod 频繁重启"
""",
    check_fn=_check_234_prometheus_rule,
    lesson=Lesson(
        concept="""\
## PrometheusRule 告警规则

**PrometheusRule** 是 Prometheus Operator 的 CRD，实现告警规则的**声明式管理**。

### 告警生命周期

```
指标采集 → PromQL 评估 → 条件触发 → 等待 for 持续时间 → 告警触发 → Alertmanager → 通知
```

### 规则结构

```yaml
groups:                    # 规则组列表
- name: pod.rules          # 组名（同组规则一起评估）
  rules:                   # 规则列表
  - alert: PodRestartAlert # 告警名称
    expr: <PromQL>         # 触发条件
    for: 5m                # 持续 5 分钟才触发
    labels:                # 告警标签
      severity: warning
    annotations:           # 告警注解
      summary: "简要描述"
      description: "详细描述"
```

### PromQL 常用函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `rate()` | 每秒增长率 | `rate(http_requests_total[5m])` |
| `increase()` | 时间段内总增长 | `increase(errors[1h])` |
| `histogram_quantile()` | 分位数计算 | `histogram_quantile(0.95, ...)` |
| `avg_over_time()` | 时间段平均值 | `avg_over_time(cpu_usage[10m])` |

### severity 级别约定

| 级别 | 含义 | 响应时间 |
|------|------|---------|
| `critical` | 严重故障 | 立即响应 |
| `warning` | 需要关注 | 1 小时内 |
| `info` | 信息通知 | 工作时间内 |

### for 的作用

`for` 字段指定表达式持续满足多久才真正触发告警：
- 避免**瞬时抖动**导致的误告警
- `for: 5m` 表示连续 5 分钟满足条件才触发
- 不设 for 则条件满足立即触发
""",
        key_fields=[
            {"name": "spec.groups", "description": "规则组列表，同组规则一起评估", "required": True, "example": "[{name: pod.rules, rules: [...]}]"},
            {"name": "spec.groups[].name", "description": "规则组名称", "required": True, "example": "pod.rules"},
            {"name": "spec.groups[].rules", "description": "规则列表", "required": True, "example": "[{alert: PodRestart, expr: ...}]"},
            {"name": "rules[].alert", "description": "告警名称", "required": True, "example": "PodRestartAlert"},
            {"name": "rules[].expr", "description": "PromQL 表达式，触发条件", "required": True, "example": "rate(kube_pod_container_status_restarts_total[5m]) > 0"},
            {"name": "rules[].for", "description": "持续满足时间，防抖动", "required": False, "example": "5m"},
            {"name": "rules[].labels", "description": "告警标签，用于路由和分类", "required": False, "example": "{severity: warning}"},
            {"name": "rules[].annotations", "description": "告警注解，提供详情", "required": False, "example": "{summary: 'Pod 重启'}"},
        ],
        diagram="""\
┌─────────── PrometheusRule ───────────────────┐
│  spec:                                       │
│    groups:                                   │
│    - name: pod.rules                         │
│      rules:                                  │
│      - alert: PodRestartAlert                │
│        expr: rate(restarts[5m]) > 0          │
│        for: 5m                               │
│        labels:                               │
│          severity: warning                   │
│        annotations:                          │
│          summary: "Pod 频繁重启"              │
└───────────────────┬──────────────────────────┘
                    │ Operator 同步
                    ▼
┌─────────── Prometheus ───────────────────────┐
│  每 evaluation_interval 评估一次 expr        │
│  连续 for 时长满足 → 触发告警                 │
└───────────────────┬──────────────────────────┘
                    │ 发送告警
                    ▼
┌─────────── Alertmanager ─────────────────────┐
│  按 labels.severity 路由通知                  │
│  → Slack / Email / PagerDuty                 │
└──────────────────────────────────────────────┘
""",
        example_yaml="""\
apiVersion: monitoring.coreos.com/v1   # Prometheus Operator CRD
kind: PrometheusRule                   # 资源类型
metadata:                              # 元数据
  name: pod-alerts                     # 名称
  labels:                              # 标签
    prometheus: kube-prometheus        # 用于 Prometheus 选择
spec:                                  # 规格定义
  groups:                              # 规则组列表
  - name: pod.rules                    # 组名
    rules:                             # 规则列表
    - alert: PodRestartAlert           # 告警名称
      expr: rate(kube_pod_container_status_restarts_total[5m]) > 0  # PromQL
      for: 5m                          # 持续 5 分钟才触发
      labels:                          # 告警标签
        severity: warning              # 严重级别
      annotations:                     # 告警注解
        summary: "Pod {{ $labels.pod }} 频繁重启"
        description: "Pod {{ $labels.pod }} 在 namespace {{ $labels.namespace }} 中频繁重启"
""",
        common_errors=[
            "expr 中的 PromQL 语法错误，导致规则加载失败",
            "忘记设置 for，导致瞬时抖动触发误告警",
            "labels 中缺少 severity，导致 Alertmanager 无法正确路由",
            "annotations 中未使用 {{ $labels.xxx }} 模板变量，告警信息不够具体",
        ],
        tips=[
            "用 kubectl get prometheusrule 查看告警规则状态",
            "在 Prometheus Web UI 的 Alerts 页面查看规则加载状态",
            "分组（groups）中的规则会一起评估，适合相关性强的规则",
            "annotations 支持 Go template 语法引用 $labels 变量",
        ],
    ),
)


# ==================== Q23.5 集群实战 - 完整监控日志栈 ====================

def _check_235_monitoring_stack(user_yaml: str) -> CheckResult:
    """Q23.5 部署完整的监控日志栈：ServiceMonitor + ConfigMap(Dashboard) + DaemonSet(Fluent Bit)"""
    crd_yaml = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: servicemonitors.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  names:
    kind: ServiceMonitor
    plural: servicemonitors
    singular: servicemonitor
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: prometheusrules.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  names:
    kind: PrometheusRule
    plural: prometheusrules
    singular: promethestrule
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
"""
    try:
        state = ClusterState()
        state = preset_state(state, crd_yaml)
        # 预置节点
        state = preset_state(state, """\
apiVersion: v1
kind: Node
metadata:
  name: node-1
  labels:
    kubernetes.io/os: linux
""")
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    hints = []
    missing = []

    # 检查 ServiceMonitor
    sm_docs = [
        doc for doc in state.customresources.values()
        if doc.get("kind") == "ServiceMonitor"
    ]
    if not sm_docs:
        missing.append("ServiceMonitor（监控采集配置）")
    else:
        sm = sm_docs[0]
        sm_spec = sm.get("spec", {})
        if not isinstance(sm_spec, dict) or not sm_spec.get("endpoints"):
            missing.append("ServiceMonitor 的 endpoints 配置")
        elif not sm_spec.get("selector"):
            missing.append("ServiceMonitor 的 selector 配置")

    # 检查 Grafana Dashboard ConfigMap
    dashboard_cm = None
    for cm_name, cm in state.configmaps.items():
        labels = cm.get("metadata", {}).get("labels", {})
        if isinstance(labels, dict) and labels.get("grafana_dashboard") in ("1", "true"):
            dashboard_cm = cm
            break
    if not dashboard_cm:
        missing.append("Grafana Dashboard ConfigMap（带 grafana_dashboard 标签）")

    # 检查 Fluent Bit DaemonSet
    if not state.daemonsets:
        missing.append("Fluent Bit DaemonSet（日志采集）")
    else:
        ds_name = next(iter(state.daemonsets))
        ds = state.daemonsets[ds_name]
        ds_containers = (
            ds.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        )
        if ds_containers and isinstance(ds_containers[0], dict):
            image = ds_containers[0].get("image", "")
            if "fluent-bit" not in image.lower():
                missing.append("Fluent Bit DaemonSet 的镜像配置（应为 fluent-bit）")
        else:
            missing.append("Fluent Bit DaemonSet 的容器配置")

    if missing:
        return CheckResult(
            ok=False,
            error=f"监控日志栈不完整，缺少：{', '.join(missing)}",
            hints=[
                "完整监控栈需要：1️⃣ ServiceMonitor（指标采集）2️⃣ ConfigMap（Grafana Dashboard）3️⃣ DaemonSet（Fluent Bit 日志采集）",
                "使用多文档 YAML（--- 分隔）在一个文件中定义所有资源",
            ],
        )

    hints.append("🎉 完整监控日志栈部署成功！")
    hints.append("📊 ServiceMonitor → Prometheus 采集指标")
    hints.append("📈 ConfigMap → Grafana 可视化 Dashboard")
    hints.append("📝 DaemonSet → Fluent Bit 采集日志")

    return CheckResult(ok=True, state=state, hints=hints)


LEVEL_Q23_5 = Level(
    id="Q23.5",
    chapter="ch23",
    title="集群实战: 完整监控日志栈",
    description="""
# 集群实战: 完整监控日志栈 🎉

将前面学到的监控和日志组件组合起来，构建一个完整的可观测性栈！

## 任务

在一个 YAML 文件中定义以下 3 个资源（用 `---` 分隔）：

1. **ServiceMonitor** - 监控 `app: web` 的 Service
2. **ConfigMap** - Grafana Dashboard（带 `grafana_dashboard: "1"` 标签）
3. **DaemonSet** - Fluent Bit 日志采集（镜像 `fluent/fluent-bit:3.0`，挂载 `/var/log`）

## 验证步骤

```bash
# 1. 部署监控栈
kubectl apply -f monitoring-stack.yaml

# 2. 检查各组件
kubectl get servicemonitor
kubectl get configmap -l grafana_dashboard=1
kubectl get ds fluent-bit

# 3. 在 Grafana 中查看 Dashboard
# 4. 在 Elasticsearch/Loki 中查看日志
```

## 提示

- 使用 `---` 分隔多个 YAML 文档
- ServiceMonitor 需要 `apiVersion: monitoring.coreos.com/v1`
- ConfigMap 需要 `labels: { grafana_dashboard: "1" }`
- DaemonSet 需要挂载 `/var/log` 的 hostPath
""",
    starter_yaml="""\
# 1. ServiceMonitor - 监控配置
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: web-monitor
  labels:
    release: prometheus
spec:
  # selector + endpoints ...

---
# 2. ConfigMap - Grafana Dashboard
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-dashboard
  labels:
    # grafana_dashboard: "1"
data:
  dashboard.json: |
    {"title": "Web Dashboard", "panels": []}

---
# 3. DaemonSet - Fluent Bit 日志采集
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      # - name: fluent-bit
      #   image: fluent/fluent-bit:3.0
      #   volumeMounts: ...
      # volumes: ...
""",
    check_fn=_check_235_monitoring_stack,
    lesson=Lesson(
        concept="""\
## 完整可观测性栈

可观测性（Observability）三大支柱：

```
┌─────────────────────────────────────────────────────┐
│                  可观测性 (Observability)            │
├─────────────┬───────────────┬───────────────────────┤
│   指标       │    日志        │    追踪 (Tracing)     │
│  Metrics    │    Logs       │    Traces             │
├─────────────┼───────────────┼───────────────────────┤
│ Prometheus  │  Fluent Bit   │  Jaeger / Tempo       │
│ ServiceMonitor│ DaemonSet   │                       │
├─────────────┼───────────────┼───────────────────────┤
│  Grafana Dashboard 可视化                           │
└─────────────────────────────────────────────────────┘
```

### 数据流

```
应用 Pod ──expose /metrics──> Service ──ServiceMonitor──> Prometheus
     │                                                      │
     └──stdout/stderr──> /var/log ──Fluent Bit DS──> Loki/ES
                                                        │
                                           Grafana Dashboard 查询
```

### 组件职责

| 组件 | 职责 | 资源类型 |
|------|------|---------|
| ServiceMonitor | 声明式定义指标抓取目标 | CRD |
| Prometheus | 时序数据库 + 查询引擎 | StatefulSet |
| Grafana Dashboard | 可视化面板 | ConfigMap |
| Fluent Bit | 日志采集与转发 | DaemonSet |
| Loki/Elasticsearch | 日志存储与查询 | StatefulSet |

### 生产环境建议

1. **资源限制**：为所有监控组件设置 resources.limits
2. **数据保留**：配置 Prometheus/Loki 的数据保留策略
3. **高可用**：Prometheus 多副本 + Thanos/Cortex
4. **告警分级**：合理使用 severity 标签路由告警
5. **Dashboard 版本控制**：ConfigMap 配合 GitOps 管理
""",
        key_fields=[
            {"name": "ServiceMonitor.spec.selector", "description": "选择要监控的 Service", "required": True, "example": "{matchLabels: {app: web}}"},
            {"name": "ServiceMonitor.spec.endpoints", "description": "抓取端点配置", "required": True, "example": "[{port: http, interval: 30s}]"},
            {"name": "ConfigMap.metadata.labels.grafana_dashboard", "description": "标记为 Grafana Dashboard", "required": True, "example": '"1"'},
            {"name": "DaemonSet.spec.template.spec.containers[].image", "description": "Fluent Bit 镜像", "required": True, "example": "fluent/fluent-bit:3.0"},
            {"name": "DaemonSet.spec.template.spec.volumes[].hostPath", "description": "节点日志目录挂载", "required": True, "example": "{path: /var/log}"},
        ],
        diagram="""\
┌─────────────────── 完整监控日志栈 ──────────────────────────┐
│                                                            │
│  ┌── ServiceMonitor ──┐  ┌── ConfigMap ────┐  ┌── DS ───┐ │
│  │ selector: app=web  │  │ grafana_dash: 1 │  │FluentBit│ │
│  │ endpoints:         │  │ dashboard.json  │  │/var/log │ │
│  │   - port: http     │  └────────┬────────┘  └────┬────┘ │
│  └─────────┬──────────┘           │                 │      │
│            │                      │                 │      │
│            ▼                      ▼                 ▼      │
│     ┌──────────┐          ┌──────────┐       ┌──────────┐ │
│     │Prometheus│          │ Grafana  │       │Loki / ES │ │
│     │  TSDB    │          │ Dashboard│       │日志存储   │ │
│     └──────────┘          └──────────┘       └──────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# 1. ServiceMonitor - 指标采集
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: web-monitor
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: web
  endpoints:
  - port: http
    interval: 30s
---
# 2. ConfigMap - Grafana Dashboard
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-dashboard
  labels:
    grafana_dashboard: "1"
data:
  dashboard.json: |
    {"title": "Web Dashboard", "panels": [{"title": "QPS", "type": "graph"}]}
---
# 3. DaemonSet - Fluent Bit 日志采集
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:3.0
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
""",
        common_errors=[
            "多文档 YAML 中忘记用 --- 分隔不同资源",
            "ServiceMonitor 的 apiVersion 写错，应为 monitoring.coreos.com/v1",
            "ConfigMap 缺少 grafana_dashboard 标签",
            "DaemonSet 的 volumes 和 volumeMounts 名称不匹配",
            "所有资源放在同一 namespace（不一致会导致关联失败）",
        ],
        tips=[
            "使用 kubectl apply -f 监控栈.yaml 一次性部署所有组件",
            "用 kubectl get all -l app=fluent-bit 查看 Fluent Bit 状态",
            "Grafana Dashboard 编辑后通过 ConfigMap 版本控制管理",
            "生产环境建议为每个组件配置 resources.requests 和 limits",
        ],
    ),
)


CHAPTER_23_LEVELS: list[Level] = [
    LEVEL_Q23_1, LEVEL_Q23_2, LEVEL_Q23_3, LEVEL_Q23_4, LEVEL_Q23_5,
]
