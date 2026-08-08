"""Chapter 0: K8s 架构总览（3 关）

基于 Claude Code review 建议新增的第 0 章，让零基础学员在写第一行
YAML 前建立 K8s 全景认知。涵盖控制面/数据面架构、声明式模型与
期望状态、kubectl 与 API 交互全链路。

Reconcile 循环的深入讲解放在 Ch17 CRD & Operator 章节。
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, ClusterState, K8sError


# ==================== Q0.1 K8s 架构总览 ====================

def _check_01_architecture(user_yaml: str) -> CheckResult:
    """Q0.1 K8s 架构总览 - 控制面 + 数据面 + 资源对象全景图"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if len(state.nodes) < 2:
        return CheckResult(
            ok=False,
            error=f"需要创建 2 个 Node（控制面节点 + 工作节点），当前只有 {len(state.nodes)} 个",
            hints=["使用 --- 分隔多文档 YAML，分别创建两个 Node"],
        )

    # 检查控制面节点
    if "control-plane-node" not in state.nodes:
        return CheckResult(
            ok=False,
            error="没找到名为 'control-plane-node' 的 Node",
            hints=["控制面节点的 metadata.name 应为 control-plane-node"],
        )

    cp_node = state.nodes["control-plane-node"]
    cp_labels = cp_node.get("metadata", {}).get("labels", {})
    if not isinstance(cp_labels, dict):
        cp_labels = {}
    has_cp_role = any(
        "control-plane" in k for k in cp_labels.keys()
    )
    if not has_cp_role:
        return CheckResult(
            ok=False,
            error="control-plane-node 缺少控制面角色标签",
            hints=["在 metadata.labels 中添加 node-role.kubernetes.io/control-plane: \"\""],
        )

    # 检查工作节点
    if "worker-node-1" not in state.nodes:
        return CheckResult(
            ok=False,
            error="没找到名为 'worker-node-1' 的 Node",
            hints=["工作节点的 metadata.name 应为 worker-node-1"],
        )

    worker_node = state.nodes["worker-node-1"]
    worker_labels = worker_node.get("metadata", {}).get("labels", {})
    if not isinstance(worker_labels, dict):
        worker_labels = {}
    has_worker_role = any(
        "worker" in k for k in worker_labels.keys()
    )
    if not has_worker_role:
        return CheckResult(
            ok=False,
            error="worker-node-1 缺少工作节点角色标签",
            hints=["在 metadata.labels 中添加 node-role.kubernetes.io/worker: \"\""],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["完美！控制面管理集群状态，工作节点运行实际工作负载 🏗️"],
    )


LEVEL_Q0_1 = Level(
    id="Q0.1",
    chapter="ch00",
    title="K8s 架构总览",
    description="""
# K8s 架构总览 🏗️

## 为什么学 K8s？

### 容器化时代的挑战

Docker 解决了应用打包问题——「一次构建，到处运行」不再是梦。但当你从 1 个容器
走向 100 个、1000 个容器时，新问题接踵而至：

- 多容器怎么**编排**？谁负责把它们调度到合适的机器上？
- 容器挂了谁来**自动重启**？深夜告警你愿意爬起来吗？
- 流量高峰怎么**自动扩容**、低谷怎么**缩容**省钱？
- 跨多台机器怎么保证**网络互通**和**服务发现**？

Docker 只解决了「打包」，而 **Kubernetes 解决了「编排」**——它是容器时代的操作系统。

### K8s 成为业界标准

- **Google 开源**：基于 Google 内部十余年大规模容器编排经验（Borg 系统）
- **CNCF 护航**：2015 年捐赠给 CNCF（云原生计算基金会），成为其第一个「毕业」项目
- **全云原生支持**：AWS EKS / Azure AKS / 阿里云 ACK / 华为云 CCE 均基于 K8s
- **GitHub 10 万+ Star**，CNCF 生态中最大的项目，社区极其活跃

### 企业为什么拥抱 K8s

| 能力 | 价值 |
|---|---|
| **声明式运维** | 写 YAML 而非手动操作，可版本控制、可审计、可回溯 |
| **自愈能力** | Pod 挂了自动重建，Node 挂了自动迁移，无需人工干预 |
| **弹性伸缩** | HPA 按负载自动扩缩容，应对流量波动 |
| **多云不锁定** | 同一套 YAML 可部署到任何 K8s 集群，不被单一云厂商绑架 |
| **生态丰富** | Helm / Istio / Prometheus / Grafana 等周边工具成熟 |

> 零基础也不用怕——本教程从架构概念开始，一步步带你从 YAML 小白到 K8s 实战达人。

---

欢迎来到 k8s-quest 第 0 章！在写第一行 YAML 之前，先建立 K8s 全景认知。

## K8s 集群架构

一个 K8s 集群由 **控制面（Control Plane）** 和 **数据面（Data Plane / Worker Nodes）** 组成：

- **控制面**：集群的"大脑"，负责管理集群状态
  - API Server：所有操作的唯一入口
  - etcd：键值存储，保存集群所有数据
  - kube-scheduler：决定 Pod 放到哪个 Node
  - kube-controller-manager：运行控制器（Deployment、Node 等）

- **数据面（工作节点）**：运行实际应用
  - kubelet：与 API Server 通信，管理 Pod 生命周期
  - kube-proxy：维护网络规则，实现 Service 负载均衡
  - 容器运行时（containerd）：运行容器

## 要求

用多文档 YAML（`---` 分隔）创建两个 Node：
1. `control-plane-node`：带标签 `node-role.kubernetes.io/control-plane: ""`
2. `worker-node-1`：带标签 `node-role.kubernetes.io/worker: ""`

## 提示

Node 的 YAML 结构：
```yaml
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    node-role.kubernetes.io/control-plane: ""
```
用 `---` 分隔多个资源。
""",
    starter_yaml="""\
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    # 添加控制面角色标签
---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    # 添加工作节点角色标签
""",
    check_fn=_check_01_architecture,
    lesson=Lesson(
        concept="""\
## Kubernetes 的历史由来

Kubernetes 并非凭空诞生，它站在巨人的肩膀上——Google 内部十余年大规模容器编排经验的结晶。

### 从 Borg 到 Kubernetes

| 时间 | 里程碑 | 说明 |
|---|---|---|
| **2003** | **Borg 系统** | Google 内部开始大规模使用 Borg，管理数万台服务器上的海量容器（内部称为「任务」），支撑 Google 搜索、Gmail 等核心服务长达十余年 |
| **2013** | **Omega 项目** | Borg 的下一代，采用分层架构和乐观并发控制，是 Borg 到 Kubernetes 的过渡研究 |
| **2014** | **Kubernetes 开源** | Google 基于 Borg/Omega 的经验，由 Joe Beda、Brendan Burns、Craig McLuckie 等人主导开源 Kubernetes。名字源自希腊语「舵手」，缩写 K8s |
| **2015** | **捐赠 CNCF** | Kubernetes 成为 CNCF（云原生计算基金会）的第一个托管项目，标志着它从 Google 主导走向社区共治 |
| **2018** | **首个毕业项目** | Kubernetes 成为 CNCF 首个「毕业」（Graduated）项目，标志着其成熟度和社区治理达到业界标准 |
| **2018+** | **业界事实标准** | 从此 K8s 成为容器编排领域的事实标准，各大云厂商纷纷推出托管服务 |

### 当前生态

今天，所有主流云厂商都提供 K8s 托管服务：

- **AWS EKS**（Amazon Elastic Kubernetes Service）
- **Azure AKS**（Azure Kubernetes Service）
- **阿里云 ACK**（Alibaba Cloud Container Service for Kubernetes）
- **华为云 CCE**（Cloud Container Engine）
- **Google GKE**（Google Kubernetes Engine，K8s 的「老家」）

> 💡 K8s 的名字由来：K**8**s = Kubernetes 中首尾字母 K 和 s 之间有 8 个字母（ubernete）。

## 企业拥抱 K8s 的核心价值

为什么从初创公司到世界 500 强都在用 K8s？核心价值如下：

1. **声明式运维**
   - 你写 YAML 声明「想要什么状态」，K8s 负责让集群达到并维持这个状态
   - YAML 文件可以纳入 Git 版本控制，每次变更可审计、可回溯
   - 告别人肉操作，运维从「手艺活」变成「工程化」

2. **自愈能力**
   - Pod 崩溃 → K8s 自动重建新 Pod 补上
   - Node 宕机 → K8s 自动将该 Node 上的 Pod 迁移到其他健康 Node
   - 凌晨 3 点容器挂了？你不用醒，K8s 帮你搞定

3. **弹性伸缩**
   - HPA（Horizontal Pod Autoscaler）按 CPU/内存/自定义指标自动扩缩容
   - 流量高峰自动加 Pod，流量低谷自动减 Pod，省钱又稳定

4. **滚动更新与回滚**
   - `kubectl rollout` 一键滚动更新，零停机部署
   - 新版本有问题？`kubectl rollout undo` 一键回滚到上一个版本

5. **多云不锁定**
   - 同一套 YAML 可以部署到任何 K8s 集群（本地、AWS、Azure、阿里云……）
   - 不被单一云厂商绑架，迁移成本大幅降低

6. **生态丰富**
   - **Helm**：K8s 的「包管理器」，一键安装复杂应用
   - **Istio**：服务网格，管理微服务间流量和安全
   - **Prometheus + Grafana**：监控与可视化
   - **ArgoCD**：GitOps 持续部署
   - 周边工具链极其成熟，开箱即用

7. **社区活跃**
   - CNCF 生态中最大的项目，GitHub **10 万+ Star**
   - 全球数万名贡献者，版本快速迭代（每年 3-4 个大版本）
   - 遇到问题？社区早已有人解答

## Kubernetes 架构全景

Kubernetes 集群采用**主从架构**，分为**控制面（Control Plane）**和**数据面（Worker Nodes）**两大平面。

### 控制面（Control Plane）

控制面是集群的"大脑"，负责全局决策和事件响应：

1. **kube-apiserver** — 所有组件通信的唯一入口。无论是 kubectl 还是其他组件，都通过 API Server 交互。它负责认证、授权、准入控制。
2. **etcd** — 高可用键值存储（Raft 共识算法），保存集群的**所有**状态数据。是 K8s 的"唯一真相来源"（single source of truth）。
3. **kube-scheduler** — 监听新建的 Pod，根据资源请求、亲和性、污点等策略，决定 Pod 调度到哪个 Node。
4. **kube-controller-manager** — 运行各种控制器的进程集合，包括 Deployment Controller、ReplicaSet Controller、Node Controller 等。

### 数据面（Worker Nodes）

工作节点是"手脚"，负责运行实际容器：

1. **kubelet** — 每个 Node 上的代理，与 API Server 通信，负责 Pod 的创建、启动、停止和健康检查。
2. **kube-proxy** — 维护 Node 上的网络规则（iptables/ipvs），实现 Service 的负载均衡和流量转发。
3. **容器运行时（Container Runtime）** — 负责拉取镜像和运行容器，主流选择是 containerd（Docker 已弃用）。

### 资源对象全景图

K8s 中一切皆资源（Resource），核心资源包括：
- **工作负载**：Pod、Deployment、StatefulSet、DaemonSet、Job
- **网络**：Service、Ingress、NetworkPolicy
- **配置**：ConfigMap、Secret
- **存储**：PV、PVC、StorageClass
- **安全**：ServiceAccount、Role、RoleBinding

所有资源都通过相同的模式管理：**YAML 声明 → API Server → etcd → 控制器协调 → kubelet 执行**。
""",
        key_fields=[
            {"name": "kind: Node", "description": "资源类型，Node 表示集群中的一个节点", "required": True, "example": "Node"},
            {"name": "metadata.name", "description": "节点名称，集群内唯一", "required": True, "example": "control-plane-node"},
            {"name": "metadata.labels", "description": "节点标签，标识节点角色", "required": True, "example": "{node-role.kubernetes.io/control-plane: \"\"}"},
            {"name": "---（多文档分隔符）", "description": "在一个 YAML 文件中定义多个资源", "required": True, "example": "---"},
        ],
        diagram="""\
┌─────────────────────── K8s 集群 ───────────────────────┐
│                                                        │
│  ┌─────────────── 控制面 (Control Plane) ────────────┐ │
│  │                                                    │ │
│  │  ┌──────────────┐  ┌───────────┐  ┌────────────┐  │ │
│  │  │ API Server   │  │   etcd    │  │ Scheduler  │  │ │
│  │  │ (唯一入口)    │◄─┤ (状态存储) │  │ (调度器)    │  │ │
│  │  └──────┬───────┘  └───────────┘  └────────────┘  │ │
│  │         │                            ┌────────────┐│ │
│  │         │                            │Controller  ││ │
│  │         │                            │Manager     ││ │
│  │         │                            └────────────┘│ │
│  └─────────┼──────────────────────────────────────────┘ │
│            │                                            │
│  ┌─────────┼──── 数据面 (Worker Nodes) ────────────────┐│
│  │         ▼                                            ││
│  │  ┌───────────── Node: worker-node-1 ──────────────┐ ││
│  │  │  kubelet  ◄──→  API Server (watch & report)    │ ││
│  │  │  kube-proxy ──→  iptables/ipvs (Service 规则)   │ ││
│  │  │  containerd ──→  运行 Pod 容器                   │ ││
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐                    │ ││
│  │  │  │ Pod A │ │ Pod B │ │ Pod C │  ← 业务容器       │ ││
│  │  │  └──────┘ └──────┘ └──────┘                    │ ││
│  │  └────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- 控制面节点 ---
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    node-role.kubernetes.io/control-plane: ""
---
# --- 工作节点 ---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    node-role.kubernetes.io/worker: ""
""",
        common_errors=[
            "忘记用 --- 分隔多个资源（两个 Node 必须在同一个 YAML 中）",
            "标签键拼写错误（正确格式：node-role.kubernetes.io/control-plane）",
            "标签值忘了加引号（空字符串需要用 \"\" 表示）",
            "把 Node 的 kind 写成了 node（K8s 区分大小写）",
        ],
        tips=[
            "控制面组件不直接运行用户容器，它只管理集群状态",
            "etcd 是集群唯一的持久化存储，备份 etcd = 备份整个集群",
            "kubelet 是唯一知道如何启动容器的组件（通过 CRI 接口）",
            "所有 K8s 操作都必须经过 API Server，没有后门",
        ],
    ),
)


# ==================== Q0.2 声明式模型与期望状态 ====================

def _check_02_declarative(user_yaml: str) -> CheckResult:
    """Q0.2 声明式模型与期望状态"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "web-deploy" not in state.deployments:
        return CheckResult(
            ok=False,
            error="没找到名为 'web-deploy' 的 Deployment",
            hints=["kind 应为 Deployment，metadata.name 为 web-deploy"],
        )

    deploy = state.deployments["web-deploy"]
    spec = deploy.get("spec", {})
    replicas = spec.get("replicas", 1)

    if replicas != 3:
        return CheckResult(
            ok=False,
            error=f"replicas 应为 3，实际 {replicas}",
            hints=["在 spec.replicas 中设置 3 个副本"],
        )

    # 验证 K8s 自动创建了 3 个 Pod（声明式的体现：你说 3 个，K8s 帮你创建）
    deploy_pods = [
        name for name, pod in state.pods.items()
        if pod.get("metadata", {}).get("labels", {}).get("pod-template-hash") == "web-deploy"
    ]
    if len(deploy_pods) != 3:
        return CheckResult(
            ok=False,
            error=f"K8s 应自动创建 3 个 Pod，实际 {len(deploy_pods)} 个",
            hints=["你声明了 replicas: 3，K8s 会自动帮你创建对应数量的 Pod"],
        )

    # 验证容器镜像
    template = spec.get("template", {})
    containers = template.get("spec", {}).get("containers", [])
    if not containers:
        return CheckResult(ok=False, error="Deployment template 缺少 containers", hints=[])

    image = containers[0].get("image", "")
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"容器镜像应为 nginx:1.25，实际 {image}",
            hints=["检查 spec.template.spec.containers[0].image"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "你声明了 3 个副本，K8s 自动创建了 3 个 Pod — 这就是声明式的力量 ✨",
        ],
    )


LEVEL_Q0_2 = Level(
    id="Q0.2",
    chapter="ch00",
    title="声明式模型与期望状态",
    description="""
# 声明式模型与期望状态 ✨

K8s 的核心设计哲学是**声明式（Declarative）**：你告诉 K8s "我想要 3 个 nginx Pod"，K8s 自动帮你维持这个状态。

## 命令式 vs 声明式

| | 命令式 (Imperative) | 声明式 (Declarative) |
|---|---|---|
| 你说什么 | "帮我启动 3 个 Pod" | "我想要 3 个 Pod 运行" |
| 谁负责 | 你手动管理 | K8s 自动维持 |
| Pod 挂了 | 你手动重启 | K8s 自动重建 |
| 扩缩容 | 你手动加减 | 改 replicas 数字 |

## 期望状态

你在 YAML 中写的是**期望状态（Desired State）**："我想要 3 个 nginx Pod"。
K8s 负责让**实际状态**不断靠近**期望状态**。你不需要关心怎么启动、在哪启动，只需要声明"想要什么"。

> Reconcile 循环（K8s 如何自动维持状态的内部机制）将在 Ch17 CRD & Operator 章节详细讲解。

## 要求

创建一个 Deployment：
- 名字 `web-deploy`
- `replicas: 3`
- 容器镜像 `nginx:1.25`

apply 后，K8s 会自动创建 3 个 Pod — 你只声明了"想要 3 个"，不需要手动创建。

## 提示

```yaml
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
      - name: nginx
        image: nginx:1.25
```
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
      - name: nginx
        # 在这里设置镜像
""",
    check_fn=_check_02_declarative,
    lesson=Lesson(
        concept="""\
## 声明式模型与期望状态

Kubernetes 的核心设计哲学是**声明式（Declarative）**模型，这是它与传统运维方式的根本区别。

### 命令式 vs 声明式

- **命令式**：`docker run nginx` — 你发出指令，系统执行一次就结束。容器挂了？你得自己重启。
- **声明式**：`kubectl apply -f deploy.yaml`（YAML 里写 replicas: 3）— 你声明**期望状态**，K8s 持续维持这个状态。Pod 挂了？K8s 自动重建。

### 期望状态（Desired State）

你在 YAML 中写的 `spec` 就是期望状态：
```yaml
spec:
  replicas: 3        # 我期望有 3 个 Pod
  containers:
  - image: nginx:1.25  # 我期望用这个镜像
```

K8s 的工作就是让**实际状态**不断靠近**期望状态**：
- 你说 3 个 Pod → K8s 创建 3 个
- 某个 Pod 崩溃 → K8s 自动新建一个补上
- 你改成 5 个 → K8s 再创建 2 个
- 你删除 Deployment → K8s 清理所有 Pod

### kubectl apply vs kubectl create

| 命令 | 类型 | 特点 |
|---|---|---|
| `kubectl create` | 命令式 | 创建一次，重复执行会报错 |
| `kubectl apply` | 声明式 | 可重复执行，K8s 会对比差异只更新变化的部分 |

日常使用推荐 `kubectl apply`，因为它是声明式的 — 你只需维护 YAML 文件，K8s 负责让集群状态匹配你的声明。

### 关键概念

- **期望状态（Desired State）**：你在 YAML 中声明的 `spec` 部分
- **实际状态（Actual State）**：集群当前的运行状况
- K8s 自动让实际状态趋近期望状态 — 你不需要关心"怎么做"，只需要声明"想要什么"

> K8s 内部是如何自动维持状态的？这涉及 **Reconcile 循环**（控制循环）机制，将在后续 Ch17 CRD & Operator 章节深入讲解。
""",
        key_fields=[
            {"name": "spec.replicas", "description": "期望的 Pod 副本数量", "required": True, "example": "3"},
            {"name": "spec.selector", "description": "标签选择器，指定 Deployment 管理哪些 Pod", "required": True, "example": "{matchLabels: {app: web}}"},
            {"name": "spec.template", "description": "Pod 模板，描述如何创建 Pod", "required": True, "example": "见下方 example_yaml"},
            {"name": "spec.template.spec.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
        ],
        diagram="""\
  你（声明期望状态）              K8s 集群

  ┌──────────────┐
  │ YAML 文件     │
  │ replicas: 3  │──apply──►  K8s 自动维持
  │ image: nginx │            ┌─────────────────────┐
  └──────────────┘            │  Pod 1 ✅ running   │
                              │  Pod 2 ✅ running   │
  你只说"想要什么"              │  Pod 3 ✅ running   │
  不关心"怎么做"               └─────────────────────┘
                                        │
                               Pod 2 崩溃！
                                        ▼
                              ┌─────────────────────┐
                              │  Pod 1 ✅ running   │
                              │  Pod 4 ✅ running   │  ← K8s 自动补一个
                              │  Pod 3 ✅ running   │
                              └─────────────────────┘
""",
        example_yaml="""\
apiVersion: apps/v1          # Deployment 的 API 版本
kind: Deployment             # 资源类型: Deployment
metadata:                    # 元数据
  name: web-deploy           # Deployment 名称
spec:                        # 期望状态声明
  replicas: 3                # 期望 3 个 Pod 副本
  selector:                  # 标签选择器
    matchLabels:             # 精确匹配标签
      app: web               # 选择 label app=web 的 Pod
  template:                  # Pod 模板
    metadata:                # Pod 元数据
      labels:                # Pod 标签（必须与 selector 匹配）
        app: web
    spec:                    # Pod 规格
      containers:            # 容器列表
      - name: nginx          # 容器名
        image: nginx:1.25    # 容器镜像
""",
        common_errors=[
            "selector 的 matchLabels 与 template.metadata.labels 不匹配（Deployment 会拒绝创建）",
            "忘记写 replicas（默认为 1，但任务要求 3）",
            "把 apiVersion 写成 v1（Deployment 应该用 apps/v1）",
            "把 image 写在 spec.containers 而不是 spec.template.spec.containers 下",
        ],
        tips=[
            "声明式意味着你不需要关心'怎么做'，只需要声明'想要什么'",
            "kubectl apply 可以重复执行，K8s 只更新变化的部分",
            "改 replicas 数字就能扩缩容，不需要手动增删 Pod",
            "kubectl get deploy web-deploy 查看 READY 列可以确认期望 vs 实际",
        ],
    ),
)


# ==================== Q0.3 kubectl 与 API 交互 ====================

def _check_03_api_interaction(user_yaml: str) -> CheckResult:
    """Q0.3 kubectl 与 API 交互 - apply 全链路"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 Pod 存在
    if "api-demo-pod" not in state.pods:
        return CheckResult(
            ok=False,
            error="没找到名为 'api-demo-pod' 的 Pod",
            hints=["在 YAML 中创建一个 kind: Pod, name: api-demo-pod 的资源"],
        )

    # 检查 Pod 标签
    pod = state.pods["api-demo-pod"]
    pod_labels = pod.get("metadata", {}).get("labels", {})
    if not isinstance(pod_labels, dict):
        pod_labels = {}
    if pod_labels.get("app") != "api-demo":
        return CheckResult(
            ok=False,
            error=f"Pod 标签 app 应为 'api-demo'，实际 '{pod_labels.get('app', '(缺失)')}'",
            hints=["在 Pod 的 metadata.labels 中设置 app: api-demo"],
        )

    # 检查 Pod 容器
    containers = pod.get("spec", {}).get("containers", [])
    if not containers:
        return CheckResult(ok=False, error="Pod 缺少 containers", hints=[])
    image = containers[0].get("image", "")
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"Pod 容器镜像应为 nginx:1.25，实际 {image}",
            hints=["检查 spec.containers[0].image"],
        )

    # 检查 Service 存在
    if "api-demo-svc" not in state.services:
        return CheckResult(
            ok=False,
            error="没找到名为 'api-demo-svc' 的 Service",
            hints=["用 --- 分隔，再创建一个 kind: Service, name: api-demo-svc"],
        )

    svc = state.services["api-demo-svc"]
    svc_spec = svc.get("spec", {})
    selector = svc_spec.get("selector", {})
    if not isinstance(selector, dict):
        selector = {}

    # 检查 Service selector 匹配 Pod 标签
    if selector.get("app") != "api-demo":
        return CheckResult(
            ok=False,
            error=f"Service selector.app 应为 'api-demo'，实际 '{selector.get('app', '(缺失)')}'",
            hints=["Service 的 spec.selector.app 必须与 Pod 的 label 匹配"],
        )

    # 检查 Service 端口
    ports = svc_spec.get("ports", [])
    if not isinstance(ports, list) or not ports:
        return CheckResult(
            ok=False,
            error="Service 缺少 spec.ports",
            hints=["在 spec.ports 中定义端口映射，如 port: 80, targetPort: 80"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "完美！你刚刚走完了 kubectl apply 的全链路："
            "YAML → API Server(认证/授权/准入) → etcd → controller watch → kubelet 执行 🔗",
        ],
    )


LEVEL_Q0_3 = Level(
    id="Q0.3",
    chapter="ch00",
    title="kubectl 与 API 交互",
    description="""
# kubectl 与 API 交互 🔗

当你执行 `kubectl apply -f deploy.yaml` 时，背后发生了什么？

## kubectl apply 全链路

```
kubectl apply
    │
    ▼
API Server ──→ 认证（你是谁？） ──→ 授权（你能做什么？） ──→ 准入控制（合规吗？）
    │
    ▼
  etcd（持久化存储）
    │
    ▼
Controller watch（监听到变化） ──→ Reconcile（创建 Pod）
    │
    ▼
kubelet（在目标 Node 上启动容器）
```

## 要求

用多文档 YAML（`---` 分隔）创建两个资源：
1. **Pod**：名字 `api-demo-pod`，标签 `app: api-demo`，镜像 `nginx:1.25`
2. **Service**：名字 `api-demo-svc`，selector 匹配 `app: api-demo`，端口 80→80

这模拟了 `kubectl apply` 一次性提交多个资源的场景。

## 提示

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod
  labels:
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc
spec:
  selector:
    app: api-demo
  ports:
  - port: 80
    targetPort: 80
```
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod
  labels:
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc
spec:
  selector:
    # 设置 selector 匹配 Pod 标签
  ports:
    # 定义端口映射
""",
    check_fn=_check_03_api_interaction,
    lesson=Lesson(
        concept="""\
## kubectl 与 API 交互全链路

当你执行 `kubectl apply -f app.yaml` 时，请求经过一条完整的处理链路，最终在 Node 上启动容器。

### 第一步：kubectl 客户端处理

kubectl 读取 YAML 文件，解析为 JSON，然后向 API Server 发送 HTTP REST 请求（POST/PUT）。kubectl 本身不做任何"执行"操作，它只是一个 API 客户端。

### 第二步：API Server 三道关卡

1. **认证（Authentication）** — "你是谁？" 通过证书、Token 或 OIDC 验证客户端身份。
2. **授权（Authorization）** — "你能做什么？" 通过 RBAC（Role-Based Access Control）检查该用户是否有权限操作该资源。
3. **准入控制（Admission Control）** — "请求合规吗？" 分为两种：
   - **Mutating（变更）**：可以修改请求内容（如注入 sidecar、添加默认标签）
   - **Validating（验证）**：只验证不修改（如检查资源配额、镜像来源限制）

### 第三步：写入 etcd

通过三道关卡后，API Server 将资源对象序列化为 JSON，写入 etcd。此时资源已"存在"于集群中，但还没有实际运行。

### 第四步：Controller Watch 触发

控制器通过 API Server 的 **watch 机制**（长轮询）实时感知资源变化。例如：
- Deployment Controller 监听到新 Deployment → 创建 ReplicaSet → 创建 Pod
- Service Controller 监听到新 Service → 分配 ClusterIP

### 第五步：kubelet 执行

新建的 Pod 被 kube-scheduler 调度到某个 Node 后，该 Node 上的 **kubelet** 通过 watch 感知到：
1. 调用 CRI（容器运行时接口）让 containerd 拉取镜像并启动容器
2. 调用 CNI（容器网络接口）配置 Pod 网络
3. 调用 CSI（容器存储接口）挂载存储卷
4. 持续执行健康检查（livenessProbe / readinessProbe）

### Service 与 Pod 的关联

Service 通过 **selector** 匹配 Pod 的 **labels**，建立 Endpoints 映射。当 Pod IP 变化时，Endpoints 控制器自动更新，Service 对外暴露的地址不变 — 这就是服务发现的核心机制。
""",
        key_fields=[
            {"name": "metadata.labels", "description": "Pod 标签，Service 通过它匹配 Pod", "required": True, "example": "{app: api-demo}"},
            {"name": "spec.containers[].image", "description": "容器镜像", "required": True, "example": "nginx:1.25"},
            {"name": "spec.selector", "description": "Service 标签选择器，匹配目标 Pod", "required": True, "example": "{app: api-demo}"},
            {"name": "spec.ports[].port", "description": "Service 暴露的端口", "required": True, "example": "80"},
            {"name": "spec.ports[].targetPort", "description": "转发到 Pod 容器的端口", "required": True, "example": "80"},
        ],
        diagram="""\
  kubectl apply -f app.yaml
         │
         │  HTTP POST (JSON)
         ▼
  ┌──────────────────────────────────────────────────┐
  │                API Server                         │
  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
  │  │  认证     │→│  授权     │→│  准入控制       │ │
  │  │(AuthN)   │  │(AuthZ)   │  │(Admission)     │ │
  │  │你是谁？  │  │能做什么？│  │合规吗？        │ │
  │  └──────────┘  └──────────┘  └───────┬────────┘ │
  └──────────────────────────────────────┼──────────┘
                                         │
                                    写入 etcd
                                         │
          ┌──────────────────────────────┘
          │ watch 事件
          ▼
  ┌─────────────────┐         ┌──────────────────┐
  │ Service         │         │ Pod Controller    │
  │ Controller      │         │ (kubelet)         │
  │                 │         │                   │
  │ 分配 ClusterIP  │         │ CRI: 启动容器      │
  │ 创建 Endpoints  │         │ CNI: 配置网络      │
  └────────┬────────┘         │ CSI: 挂载存储      │
           │                  └──────────────────┘
           │ selector: app=api-demo
           │        匹配
           ▼
  ┌──────────────────────────────────────────────┐
  │  Pod (api-demo-pod)                          │
  │  labels: app=api-demo                        │
  │  IP: 10.244.1.5    Container: nginx:1.25     │
  └──────────────────────────────────────────────┘
           ▲
           │ Service → Endpoints → Pod IP
           │
  ┌────────┴─────────────────────────────────────┐
  │  Service (api-demo-svc)                      │
  │  ClusterIP: 10.96.0.100    Port: 80          │
  │  selector: app=api-demo                      │
  └──────────────────────────────────────────────┘
""",
        example_yaml="""\
# --- Pod 资源 ---
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod          # Pod 名称
  labels:                     # 标签（Service 通过它匹配）
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25         # 容器镜像
    ports:
    - containerPort: 80       # 容器监听端口
---
# --- Service 资源 ---
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc          # Service 名称
spec:
  selector:                   # 标签选择器
    app: api-demo             # 匹配 label app=api-demo 的 Pod
  ports:
  - port: 80                  # Service 暴露端口
    targetPort: 80            # 转发到 Pod 的端口
""",
        common_errors=[
            "Service 的 selector 与 Pod 的 labels 不匹配（最常见错误！）",
            "忘记用 --- 分隔 Pod 和 Service（导致 YAML 解析失败）",
            "targetPort 与 containerPort 不一致（流量无法到达容器）",
            "把 selector 写成了 select（拼写错误）",
        ],
        tips=[
            "kubectl 是 API 客户端，本身不执行任何容器操作",
            "Service + Pod 的关联靠 selector ↔ labels 匹配，这是 K8s 服务发现的核心",
            "用 kubectl describe svc <name> 查看 Endpoints 是否正确匹配到 Pod",
            "API Server 的三道关卡（认证→授权→准入）是 K8s 安全的基石",
        ],
    ),
)


# ==================== Chapter 0 关卡汇总 ====================

CHAPTER_0_LEVELS = [LEVEL_Q0_1, LEVEL_Q0_2, LEVEL_Q0_3]
