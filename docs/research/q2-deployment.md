# Chapter 2: Deployment 技术调研 + Simulator 扩展方案

> K8s Quest Q2.1-Q2.4 关卡配套技术资料 + 实现方案
> 调研员: Researcher | 日期: 2026-07-06
> 依据: K8s 官方文档 + 现有 simulator/validator 源码

---

## 🎯 调研目标

为 Chapter 2 (Deployment, 4 关) 提供：(1) Deployment/滚动更新/回滚的深度技术原理；
(2) simulator 必须扩展的三个能力 (preset / rollout history / rollback) 的数据结构与接口设计；
(3) Q2.1-Q2.4 每关 check_fn 的伪代码草稿 (happy path + ≥2 错误分支)，engineer 可直接照着实现。

---

## 1. Deployment 核心概念

### 1.1 三层级关系：Deployment → ReplicaSet → Pod

真实 K8s 中，Deployment 不直接管 Pod，而是通过 **ReplicaSet (RS)** 间接管理 [1]：

```
Deployment (apps/v1)
  └─ owns ── ReplicaSet #1 (revision 1, template: nginx:1.24)  → 3 Pods [hash-a]
  └─ owns ── ReplicaSet #2 (revision 2, template: nginx:1.25)  → 3 Pods [hash-b]   (滚动更新后)
```

关键点 [1][2]：
- Deployment **拥有** ReplicaSet（通过 RS 的 `metadata.ownerReferences` 反向指向 Deployment）
- ReplicaSet **拥有** Pod（同理 ownerReferences）
- 每个 Pod 被打上 `pod-template-hash` 标签（由 Deployment controller 计算 template 的 hash 生成），用于区分不同 revision 产生的 Pod
- 滚动更新 = 新建一个 RS（新 template → 新 hash），扩容新 RS 的 Pod、缩容旧 RS 的 Pod；旧 RS 保留（revisionHistoryLimit 个），便于回滚

> 💡 **教学映射**：k8s-quest 的 simulator 当前是"扁平"的——Deployment 直接实例化 Pod，没有 RS 中间层。对 Q2.1/Q2.2（创建/扩缩容）足够；对 Q2.3/Q2.4（滚动/回滚）需要补 revision 概念，但**不必引入完整 RS**（见 §5）。

### 1.2 API 与关键字段

| 字段 | 位置 | 类型 | 默认 | 作用 | 引用 |
|---|---|---|---|---|---|
| `apiVersion` | 顶层 | string | `apps/v1` | Deployment 属 apps 组 | [1] |
| `kind` | 顶层 | string | `Deployment` | 资源类型 | [1] |
| `metadata.name` | metadata | string | 必填 | Deployment 名 | [1] |
| `spec.replicas` | spec | int | `1` | 期望副本数 | [1] |
| `spec.selector` | spec | LabelSelector | 必填 | 选 Pod 的标签，**必须匹配 template.labels** | [1] |
| `spec.template` | spec | PodTemplateSpec | 必填 | Pod 模板（含 labels/containers） | [1] |
| `spec.strategy` | spec | DeploymentStrategy | `RollingUpdate` | 更新策略 | [1] |
| `spec.strategy.type` | strategy | enum | `RollingUpdate` | `RollingUpdate` / `Recreate` | [1] |
| `spec.strategy.rollingUpdate.maxSurge` | strategy | int\|str | `25%` | 滚动时可超过 replicas 的最大值 | [1] |
| `spec.strategy.rollingUpdate.maxUnavailable` | strategy | int\|str | `25%` | 滚动时不可用 Pod 最大值 | [1] |
| `spec.revisionHistoryLimit` | spec | int | `10` | 保留旧 RS 数量（被 GC 的旧 RS 不能回滚） | [1] |
| `spec.minReadySeconds` | spec | int | `0` | Pod 就绪多久才算 available | [1] |
| `spec.progressDeadlineSeconds` | spec | int | `600` | 超过此秒数判定 rollout 失败 | [1] |

**selector 必须匹配 template.labels 的硬规则** [1]：这是 Deployment controller 区分"哪些 Pod 归我管"的依据。若 selector 与 template.labels 不匹配，K8s 会拒绝创建（api-server 校验）。

> 💡 **Q2.1 教学点**：玩家最容易漏 `selector`。check_fn 应明确提示。

### 1.3 Recreate vs RollingUpdate [1]

| 策略 | 行为 | 停机 | 适用 |
|---|---|---|---|
| `RollingUpdate`（默认） | 先起新 Pod，再杀旧 Pod，渐进替换 | 无/少 | 生产默认 |
| `Recreate` | 先杀全部旧 Pod，再起新 Pod | 有 | 不支持多版本并存（如单写 DB） |

---

## 2. 滚动更新机制

### 2.1 maxSurge / maxUnavailable 的约束 [1]

官方约束（已核对原文）：

> the number of availableReplicas must be between `replicas - maxUnavailable` and `replicas + maxSurge`

即滚动期间，**可用 Pod 数** ∈ [replicas − maxUnavailable, replicas + maxSurge]。

| 参数 | 默认 | 可为 | 约束 |
|---|---|---|---|
| `maxSurge` | `25%` | 绝对数(5) 或百分比(10%) | 不能为 0 当 maxUnavailable=0 时（否则无法滚动） |
| `maxUnavailable` | `25%` | 绝对数 或百分比（向下取整） | 不能为 0 当 maxSurge=0 时 [1] |

举例（replicas=3, 默认 25%）：
- maxSurge = ceil(3 × 0.25) = 1 → 最多 4 个 Pod 同时存在
- maxUnavailable = floor(3 × 0.25) = 0 → 不可用 Pod 最多 0 个
- 结果：先 +1 新 Pod（达 4），确认新 Pod ready 后再 −1 旧 Pod（回 3），循环至全部替换

> ⚠️ 注意：K8s **不把 terminating Pod 计入 unavailable**，所以实际可能短暂超过 replicas+maxSurge [1]。

### 2.2 滚动更新流程（Deployment controller 内部）[1]

```
1. 玩家更新 Deployment spec.template（如改 image）
2. Deployment controller 检测 template 变化 → 计算新 hash
3. 创建新 ReplicaSet（revision N+1, 新 hash）
4. 新 RS 扩容：+1 Pod（受 maxSurge 上限）
5. 旧 RS 缩容：−1 Pod（受 maxUnavailable 上限）
6. 重复 4-5 直到旧 RS replicas=0
7. 旧 RS 保留（revisionHistoryLimit 个），其余 GC
```

### 2.3 Revision 原理 [1][3]

- 每次 **spec.template** 变化 → 产生新 revision（revision 号递增，从 1 开始）
- revision 号存在 Deployment annotation `deployment.kubernetes.io/revision`
- 仅改 `spec.replicas`（扩缩容）**不**产生新 revision
- `kubectl rollout history deployment/<name>` 查看所有 revision
- `kubectl rollout history deployment/<name> --revision=2` 看某个 revision 详情

> 💡 **关键**：revision 是按 template 变化算的，不是按 spec 变化。这对 Q2.3（改 image = 改 template = 新 revision）和 Q2.2（改 replicas ≠ 新 revision）的设计很重要。

---

## 3. 回滚机制

### 3.1 kubectl rollout undo [3]

| 命令 | 作用 |
|---|---|
| `kubectl rollout undo deployment/<name>` | 回滚到**上一个** revision |
| `kubectl rollout undo deployment/<name> --to-revision=2` | 回滚到**指定** revision |
| `kubectl rollout status deployment/<name>` | 查看 rollout 进度 |
| `kubectl rollout history deployment/<name>` | 列出所有 revision |
| `kubectl rollout pause/resume` | 暂停/恢复 rollout |
| `kubectl rollout restart` | 重启（触发同 template 的新 rollout） |

**回滚本质** [1]：把指定 revision 的 template 复制回当前 Deployment.spec.template，**这本身又是一次 template 变化，会产生新 revision 号**（不是回到旧号）。

### 3.2 revisionHistoryLimit [1]

- 默认 10。超过的旧 RS 被 GC。
- 设为 0 → 不能回滚（无历史）。
- 注意：被 GC 的 RS 对应 revision **无法回滚**。

### 3.3 回滚触发条件（教学要点）

真实 K8s 中回滚通常在以下情况触发：
1. `progressDeadlineSeconds` 超时（rollout 卡住）→ Deployment status 出现 `Progressing=False, TimedOutReason`
2. 手动 `kubectl rollout undo`（最常见）
3. 新 Pod 一直 CrashLoopBackOff（人为判断后回滚）

---

## 4. 4 关知识点 + 通过条件映射

| 关卡 | 知识点 | 通过条件 | simulator 依赖 |
|---|---|---|---|
| **Q2.1** 创建 Deployment | Deployment 结构 / selector / replicas / template | `nginx-deploy`, 3 replicas, `nginx:1.25` | 现有 `_apply_deployment` 即可 |
| **Q2.2** 扩缩容 | replicas 字段 / 水平扩展 | `api-deploy`, 5 replicas, `python:3.11-slim` | 现有即可 |
| **Q2.3** 滚动更新 | template 变化 = 新 revision / 声明式升级 | 已有 `web-deploy` v1 → 玩家改 image 为 `nginx:1.25` → 所有 Pod 升级 | **需 preset 机制** |
| **Q2.4** 回滚 | revision history / rollback 触发 | 模拟失败升级 → 玩家 rollback 回上一版 | **需 rollout history + rollback** |

---

## 5. Simulator 扩展设计方案（最关键）

### 5.0 设计原则

1. **自包含**：preset/失败升级由 check_fn 内部 seed，不污染 Level dataclass（参考 ch01 风格——每关 _check 自建 ClusterState）
2. **最小侵入**：不引入完整 ReplicaSet 层，用 revision 列表模拟 RS 历史
3. **YAML 范式**：所有玩家交互仍走 `apply_manifest(state, yaml)`，回滚用 annotation 触发（见 §5.3）
4. **向后兼容**：扩展不破坏 ch01 现有行为

---

### 5.1 (a) Preset 机制

**问题**：Q2.3 需要"集群里已有 web-deploy v1"。当前 check_fn 只 apply 玩家 YAML，无初始状态。

**方案对比**：

| 方案 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A. Level 加 `preset_yaml` 字段 | Level dataclass 增字段，validator 在 check_fn 前 apply preset | 通用、声明式 | 改 dataclass + validator + 所有调用点；preset 与 check 强耦合时不灵活 |
| B. check_fn 内部 seed（**推荐**） | check_fn 自己 `apply_manifest(state, PRESET_YAML)` 再 apply 玩家 YAML | 自包含、零框架改动、灵活、符合 ch01 风格 | preset YAML 重复在每关（可接受，4 关而已） |

**推荐方案 B**：check_fn 内部 seed。理由：
- ch01 每关 `_check` 都是 `state = ClusterState(); state = apply_manifest(state, user_yaml)` 自包含
- preset 是关卡逻辑的一部分，由 check_fn 拥有最自然
- 零框架改动，engineer 只加 ch02_deployment.py 一个文件即可

**Preset YAML 草稿（Q2.3 用）**：

```yaml
# web-deploy v1: 预置状态，3 副本 nginx:1.24
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  labels:
    app: web
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
          image: nginx:1.24
```

**check_fn 内 seed 模式（伪代码）**：

```python
# 复用 helper，避免每关重复
def _seed(state: ClusterState, preset_yaml: str) -> ClusterState:
    """在玩家 YAML 之前预置集群状态。"""
    return apply_manifest(state, preset_yaml)

def _check_23_rolling_update(user_yaml: str) -> CheckResult:
    state = ClusterState()
    state = _seed(state, WEB_DEPLOY_V1)        # 预置 v1
    state = apply_manifest(state, user_yaml)   # 玩家升级
    ...  # 校验所有 Pod = nginx:1.25
```

> 工程建议：把 `_seed` 放在 `app/levels/ch02_deployment.py` 顶部作模块级 helper，或抽到 `app/simulator.py` 作 `seed_state(state, yaml)` 公开函数。后者更通用（ch03 Service 也要 preset）。**推荐抽到 simulator.py**。

---

### 5.2 (b) Rollout History 数据结构 + 接口

**问题**：Q2.4 需要记录 Deployment 的 revision 历史，并支持回滚到指定 revision。

#### 5.2.1 数据结构（改 ClusterState）

在 `app/simulator.py` 的 `ClusterState` 增字段：

```python
@dataclass
class ClusterState:
    pods: dict[str, dict] = field(default_factory=dict)
    deployments: dict[str, dict] = field(default_factory=dict)
    services: dict[str, dict] = field(default_factory=dict)
    # ---- 新增：Deployment revision 历史 ----
    # key: deployment name, value: 有序 revision 列表
    revisions: dict[str, list["Revision"]] = field(default_factory=dict)
```

新增 `Revision` dataclass（模块级，放 simulator.py）：

```python
@dataclass
class Revision:
    """一次 Deployment template 变更的快照。"""
    number: int                      # revision 号，从 1 递增
    template: dict                  # 当时的 spec.template 快照（深拷贝）
    annotations: dict[str, str]     # 至少含 deployment.kubernetes.io/revision
    created_at: float               # 时间戳（time.time()）
```

#### 5.2.2 apply_manifest 记录 revision（改 `_apply_deployment`）

```python
def _apply_deployment(state: ClusterState, doc: dict) -> None:
    _validate_deployment(doc)
    name = doc["metadata"]["name"]
    spec = doc["spec"]
    template = spec["template"]

    is_new = name not in state.deployments
    if is_new:
        # 新 Deployment → revision 1
        state.deployments[name] = doc
        _record_revision(state, name, template, number=1)
        _materialize_pods(state, name, spec)        # 实例化 Pod（抽出现有逻辑）
    else:
        # 已存在 → 检查 template 是否变化
        old_template = state.deployments[name]["spec"]["template"]
        if _template_changed(old_template, template):
            # template 变化 → 新 revision
            next_rev = _next_revision_number(state, name)
            state.deployments[name] = doc           # 覆盖
            _record_revision(state, name, template, number=next_rev)
            _materialize_pods(state, name, spec)   # 用新 template 重建 Pod（模拟滚动结果）
        else:
            # 仅 replicas 变化（扩缩容）→ 不产生新 revision，但更新 replicas
            state.deployments[name]["spec"]["replicas"] = spec.get("replicas", 1)
            _materialize_pods(state, name, state.deployments[name]["spec"])
```

**helper 函数签名**（engineer 照实现）：

```python
def _record_revision(state: ClusterState, name: str, template: dict, number: int) -> None:
    """记录一次 revision。template 深拷贝。"""
    state.revisions.setdefault(name, []).append(Revision(
        number=number,
        template=copy.deepcopy(template),
        annotations={"deployment.kubernetes.io/revision": str(number)},
        created_at=time.time(),
    ))

def _template_changed(old: dict, new: dict) -> bool:
    """比较 template（忽略 pod-template-hash 等自动注入字段）。"""
    return _strip_auto_fields(old) != _strip_auto_fields(new)

def _next_revision_number(state: ClusterState, name: str) -> int:
    revs = state.revisions.get(name, [])
    return (revs[-1].number + 1) if revs else 1
```

> ⚠️ **注意现有 `_apply_deployment` 的副作用**：它直接 `template.setdefault("metadata",{}).setdefault("labels",{})["pod-template-hash"] = name`。这会污染玩家传入的 doc。扩展时应改为用真实 hash（如 `hashlib.md5(json.dumps(template, sort_keys=True).encode()).hexdigest()[:10]`），且**不要原地改 doc**——先 deepcopy 再注入。

#### 5.2.3 回滚接口

新增公开函数（simulator.py）：

```python
def rollback(state: ClusterState, name: str, to_revision: int | None = None) -> ClusterState:
    """回滚 Deployment 到指定 revision。
    to_revision=None → 回滚到上一个 revision。
    返回 state（in-place 修改）。
    抛 K8sError: Deployment 不存在 / 无历史 / revision 不存在。
    """
    if name not in state.deployments:
        raise K8sError(f"Deployment {name} 不存在，无法回滚")
    revs = state.revisions.get(name, [])
    if len(revs) < 2:
        raise K8sError(f"Deployment {name} 历史不足 2 个 revision，无法回滚")

    if to_revision is None:
        target = revs[-2]  # 上一个
    else:
        target = next((r for r in revs if r.number == to_revision), None)
        if target is None:
            raise K8sError(f"revision {to_revision} 不存在，可用: {[r.number for r in revs]}")

    # 回滚 = 把目标 template 写回，并记录新 revision（符合 K8s 真实行为）
    new_template = copy.deepcopy(target.template)
    state.deployments[name]["spec"]["template"] = new_template
    next_num = _next_revision_number(state, name)
    _record_revision(state, name, new_template, number=next_num)
    _materialize_pods(state, name, state.deployments[name]["spec"])
    return state
```

> 💡 **K8s 真实行为**：rollback 本身产生新 revision 号（不是回到旧号）。上面实现遵循此行为，revision 号单调递增，但 template 指向旧的。这对教学有意义——回滚不是"时间倒流"而是"用一个旧 template 再做一次更新"。

#### 5.2.4 查询接口（可选，给 check_fn 用）

```python
def get_revisions(state: ClusterState, name: str) -> list[Revision]:
    """返回某 Deployment 的全部 revision 历史。"""
    return list(state.revisions.get(name, []))

def current_image(state: ClusterState, name: str) -> str | None:
    """返回 Deployment 当前 template 第一个 container 的 image。"""
    if name not in state.deployments:
        return None
    tmpl = state.deployments[name]["spec"]["template"]
    cs = tmpl.get("spec", {}).get("containers", [])
    return cs[0].get("image") if cs else None
```

---

### 5.3 (c) Q2.4 回滚 UX 方案

**问题**：玩家如何通过提交 YAML 触发回滚？游戏是 YAML 提交式，不能用 `kubectl` 命令。

**方案对比**：

| 方案 | 玩家操作 | 优点 | 缺点 |
|---|---|---|---|
| **A. 特殊 annotation** | 提交 Deployment YAML，带 `metadata.annotations["kubectl.quest/rollback"]: "true"`（或 `rollback-to-revision: "1"`） | 纯 YAML、贴近真实 annotation 机制、语义清晰、支持指定 revision | 需 simulator 识别 annotation 并调 `rollback()` |
| B. 重新提交旧 image | 玩家手写 `image: nginx:1.24` 重新 apply | 零扩展（复用滚动更新） | 不教"回滚"概念，等于再做一次滚动；无法体现 revision history 价值 |
| C. 专用伪资源 `kind: Rollback` | 玩家写 `kind: Rollback, spec: {deployment: web-deploy, toRevision: 1}` | 语义最明确 | 脱离真实 K8s（无此资源），玩家学到的语法迁移性差 |

**推荐方案 A（annotation 触发）**，理由：
1. **纯 YAML 范式**：与游戏"提交 YAML"一致，无需新资源类型
2. **贴近真实**：真实 K8s 大量用 annotation 携带元数据（如 `deployment.kubernetes.io/revision` 本身就是 annotation），玩家学到 annotation 用法
3. **语义清晰**：`kubectl.quest/rollback: "true"` 一眼能懂
4. **可扩展**：`rollback-to-revision: "2"` 支持指定 revision（后续进阶关可用）

**simulator 识别逻辑（改 `_apply_deployment` 开头）**：

```python
def _apply_deployment(state: ClusterState, doc: dict) -> None:
    _validate_deployment(doc)
    name = doc["metadata"]["name"]
    annotations = doc.get("metadata", {}).get("annotations", {}) or {}

    # ---- 回滚触发（annotation 优先）----
    if annotations.get("kubectl.quest/rollback") == "true":
        to_rev = annotations.get("kubectl.quest/rollback-to-revision")
        to_rev = int(to_rev) if to_rev else None
        rollback(state, name, to_revision=to_rev)   # 见 5.2.3
        return
    # ---- 正常 apply ----
    ...（现有 + revision 记录逻辑）
```

**Q2.4 玩家提交示例**：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    kubectl.quest/rollback: "true"
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
          image: nginx:1.24   # 回滚目标（也可留空，simulator 从 revision 取）
```

> 💡 **教学提示文案**（写进 Q2.4 description）："K8s 用 `kubectl rollout undo` 回滚。在我们这里，给 Deployment 加 annotation `kubectl.quest/rollback: \"true\"` 即可触发回滚到上一版本。"

---

## 6. 每关 check_fn 逻辑草稿

> 参考 `ch01_pod.py` 的 `_check` 模式：`ClusterState() → apply_manifest → 找资源 → 逐项校验 → CheckResult`。
> 每关覆盖 happy path + ≥2 错误分支。所有代码为**草稿**，engineer 据此实现并补类型守卫（参考 ch01 的 isinstance 守卫风格）。

### 6.1 Q2.1 创建第一个 Deployment

```python
def _check_21_create_deployment(user_yaml: str) -> CheckResult:
    """Q2.1 创建第一个 Deployment: nginx-deploy, 3 replicas, nginx:1.25"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 找 Deployment
    if "nginx-deploy" not in state.deployments:
        names = list(state.deployments.keys())
        return CheckResult(
            ok=False,
            error=f"没找到 Deployment 'nginx-deploy'，当前: {names}",
            hints=["Deployment 的 metadata.name 决定名字"],
        )

    dep = state.deployments["nginx-deploy"]
    spec = dep.get("spec", {})

    # 错误分支1: replicas 不对
    replicas = spec.get("replicas", 1)
    if replicas != 3:
        return CheckResult(
            ok=False,
            error=f"replicas 应为 3，实际 {replicas}",
            hints=["spec.replicas 控制副本数"],
        )

    # 错误分支2: image 不对
    tmpl = spec.get("template", {})
    containers = tmpl.get("spec", {}).get("containers", [])
    if not containers:
        return CheckResult(ok=False, error="template 缺少 containers", hints=[])
    image = containers[0].get("image", "")
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"image 应为 nginx:1.25，实际 {image}",
            hints=["image 在 spec.template.spec.containers[0].image"],
        )

    # 错误分支3（教学）: 缺 selector
    if "selector" not in spec:
        return CheckResult(
            ok=False,
            error="缺少 spec.selector（Deployment 必须声明如何选 Pod）",
            hints=["selector.matchLabels 应与 template.labels 一致"],
        )

    # 校验 Pod 实例化数量（simulator 应已生成 3 个 Pod）
    deploy_pods = [n for n, p in state.pods.items() if n.startswith("nginx-deploy-")]
    if len(deploy_pods) != 3:
        return CheckResult(
            ok=False,
            error=f"期望 3 个 Pod，实际 {len(deploy_pods)}",
            hints=["simulator 应根据 replicas 实例化 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！Deployment 自动维持 3 个副本 🚀"],
    )
```

### 6.2 Q2.2 扩缩容

```python
def _check_22_scale(user_yaml: str) -> CheckResult:
    """Q2.2 扩缩容: api-deploy, 5 replicas, python:3.11-slim"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "api-deploy" not in state.deployments:
        return CheckResult(
            ok=False,
            error="没找到 Deployment 'api-deploy'",
            hints=["Deployment 名字应为 api-deploy"],
        )

    dep = state.deployments["api-deploy"]
    spec = dep.get("spec", {})
    replicas = spec.get("replicas", 1)

    # 错误分支1: replicas 不是 5
    if replicas != 5:
        return CheckResult(
            ok=False,
            error=f"replicas 应为 5，实际 {replicas}（水平扩展 = 改 replicas）",
            hints=["spec.replicas: 5"],
        )

    # 错误分支2: image 不对
    containers = spec.get("template", {}).get("spec", {}).get("containers", [])
    if not containers or containers[0].get("image") != "python:3.11-slim":
        return CheckResult(
            ok=False,
            error=f"image 应为 python:3.11-slim，实际 {containers[0].get('image') if containers else '无'}",
            hints=["image 在 template.spec.containers[0]"],
        )

    # 校验 Pod 数量同步到 5
    pods = [n for n in state.pods if n.startswith("api-deploy-")]
    if len(pods) != 5:
        return CheckResult(
            ok=False,
            error=f"期望 5 个 Pod，实际 {len(pods)}（simulator 未正确扩容）",
            hints=[],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["扩容完成！改 replicas 就是水平扩展 📈"],
    )
```

### 6.3 Q2.3 滚动更新

```python
WEB_DEPLOY_V1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  labels:
    app: web
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
          image: nginx:1.24
"""

def _check_23_rolling_update(user_yaml: str) -> CheckResult:
    """Q2.3 滚动更新: 已有 web-deploy v1(nginx:1.24) → 玩家升级到 nginx:1.25"""
    state = ClusterState()
    try:
        state = _seed(state, WEB_DEPLOY_V1)       # 预置 v1
        state = apply_manifest(state, user_yaml)  # 玩家升级
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 错误分支1: 玩家没改 web-deploy，而是新建了别的
    if "web-deploy" not in state.deployments:
        return CheckResult(
            ok=False,
            error="应更新已有的 web-deploy，而非新建别的 Deployment",
            hints=["metadata.name 必须是 web-deploy"],
        )

    dep = state.deployments["web-deploy"]
    containers = dep["spec"]["template"]["spec"]["containers"]
    image = containers[0].get("image", "")

    # 错误分支2: image 没改
    if image == "nginx:1.24":
        return CheckResult(
            ok=False,
            error="image 还是 nginx:1.24，需升级到 nginx:1.25",
            hints=["改 spec.template.spec.containers[0].image"],
        )

    # 错误分支3: 改成了错误的版本
    if image != "nginx:1.25":
        return CheckResult(
            ok=False,
            error=f"image 应为 nginx:1.25，实际 {image}",
            hints=[],
        )

    # 校验所有 Pod 都升级到新版本（滚动完成的标志）
    web_pods = [p for n, p in state.pods.items() if n.startswith("web-deploy-")]
    if not web_pods:
        return CheckResult(ok=False, error="没有 web-deploy 的 Pod", hints=[])
    not_upgraded = [p for p in web_pods
                    if p["spec"]["containers"][0].get("image") != "nginx:1.25"]
    if not_upgraded:
        return CheckResult(
            ok=False,
            error=f"还有 {len(not_upgraded)}/{len(web_pods)} 个 Pod 未升级到 nginx:1.25",
            hints=["滚动更新应替换所有 Pod"],
        )

    # 教学点：检查是否产生了新 revision（template 变了 = 新 revision）
    revs = get_revisions(state, "web-deploy")
    if len(revs) < 2:
        return CheckResult(
            ok=False,
            error="升级应产生新 revision，但历史只有 1 条（template 未变化？）",
            hints=["改 image 会触发新 revision"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["滚动更新完成！声明式升级——你只声明目标，K8s 自动滚动 🔄"],
    )
```

### 6.4 Q2.4 回滚

```python
# 失败升级用的"坏 image"（不存在的版本）
WEB_DEPLOY_BAD = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  labels:
    app: web
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
          image: nginx:9.99.99   # 故意写错的版本
"""

def _check_24_rollback(user_yaml: str) -> CheckResult:
    """Q2.4 回滚: 模拟失败升级 → 玩家 rollback 回上一版(nginx:1.24)"""
    state = ClusterState()
    try:
        state = _seed(state, WEB_DEPLOY_V1)       # revision 1: nginx:1.24
        state = apply_manifest(state, WEB_DEPLOY_BAD)  # revision 2: 失败升级
        state = apply_manifest(state, user_yaml)  # 玩家触发回滚
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if "web-deploy" not in state.deployments:
        return CheckResult(
            ok=False,
            error="web-deploy 不存在",
            hints=[],
        )

    # 校验当前 image 回到了 nginx:1.24
    dep = state.deployments["web-deploy"]
    image = dep["spec"]["template"]["spec"]["containers"][0].get("image", "")

    # 错误分支1: 还停在坏版本（没触发回滚）
    if image == "nginx:9.99.99":
        return CheckResult(
            ok=False,
            error="还在坏版本 nginx:9.99.99，回滚未生效",
            hints=[
              "给 Deployment 加 annotation: "
              "kubectl.quest/rollback: \"true\" 来触发回滚",
            ],
        )

    # 错误分支2: 回滚到了错误的版本
    if image != "nginx:1.24":
        return CheckResult(
            ok=False,
            error=f"回滚后 image 应为 nginx:1.24，实际 {image}",
            hints=["rollback 默认回到上一个 revision（nginx:1.24）"],
        )

    # 校验所有 Pod 也回到旧版本
    web_pods = [p for n, p in state.pods.items() if n.startswith("web-deploy-")]
    bad_pods = [p for p in web_pods
                if p["spec"]["containers"][0].get("image") != "nginx:1.24"]
    if bad_pods:
        return CheckResult(
            ok=False,
            error=f"还有 {len(bad_pods)} 个 Pod 未回到 nginx:1.24",
            hints=[],
        )

    # 教学点：rollback 应产生新 revision 号（K8s 真实行为）
    revs = get_revisions(state, "web-deploy")
    # 预期: rev1(1.24) → rev2(9.99.99) → rev3(1.24, 回滚产生)
    if len(revs) < 3:
        return CheckResult(
            ok=False,
            error=f"回滚应产生新 revision，实际历史 {len(revs)} 条（预期 ≥3）",
            hints=["rollback 本身是一次 template 变更，会产生新 revision"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["回滚成功！Deployment 自带撤销，version 历史是你的后悔药 🔙"],
    )
```

---

## 7. Engineer 实现清单（todo 列表）

按依赖顺序：

1. **simulator.py 扩展**（阻塞后续所有）
   - [ ] `ClusterState` 加 `revisions: dict[str, list[Revision]]` 字段
   - [ ] 新增 `Revision` dataclass
   - [ ] 新增 `seed_state(state, yaml)` / 或文档化 `_seed` helper
   - [ ] 改 `_apply_deployment`：识别 rollback annotation → 调 `rollback()`；否则记录 revision + 用 deepcopy 避免污染 doc + 真实 pod-template-hash
   - [ ] 新增 `rollback(state, name, to_revision=None)` 公开函数
   - [ ] 新增 `get_revisions(state, name)` / `current_image(state, name)` 查询函数
   - [ ] 修复现有 `_apply_deployment` 原地改 doc 的副作用（deepcopy template 后注入 hash）
2. **ch02_deployment.py**（依赖 1）
   - [ ] Q2.1-Q2.4 四个 `_check` 函数 + `Level` 对象
   - [ ] 模块级 `WEB_DEPLOY_V1` / `WEB_DEPLOY_BAD` preset YAML
   - [ ] `CHAPTER_2_LEVELS = [...]`
3. **validator.py 注册**（依赖 2）
   - [ ] `get_level` / `list_levels` 合并 ch01 + ch02
4. **测试**（TDD）
   - [ ] 每关 happy path
   - [ ] 每关 ≥2 错误分支
   - [ ] 回滚到指定 revision（to_revision=N）
   - [ ] revision 号单调递增 + rollback 产生新号

---

## 8. ⚠️ 风险与不确定性

| 风险 | 说明 | 缓解 |
|---|---|---|
| **pod-template-hash 真实算法** | 真实 K8s 用 controller hash + 随机后缀，simulator 用 md5(template)[:10] 即可，不必精确复现 | 文档说明这是"模拟" |
| **滚动过程的中间态** | 当前 `_apply_deployment` 直接用新 template 重建所有 Pod，不模拟"渐进替换"。Q2.3 只校验终态（所有 Pod=新 image），可接受 | 若后续要教 maxSurge 过程，再扩展 |
| **rollback 产生新 revision** | 真实 K8s rollback 会产生新 revision 号但 template 是旧的。本设计遵循此行为，但 check_fn 校验"≥3 条历史"依赖此语义 | engineer 实现时注意：rollback 后 revision 列表 append 新条目，number 递增 |
| **annotation 命名空间冲突** | `kubectl.quest/*` 是自定义前缀，需确认不与真实 K8s annotation 冲突 | `kubectl.quest` 前缀安全（非 k8s.io 域） |
| **selector 校验** | 真实 K8s api-server 强制 selector 匹配 template.labels。simulator 当前不校验。Q2.1 建议加校验以教学 | 在 `_validate_deployment` 加匹配检查 |
| **Q2.3 玩家可能直接 apply 完整新 Deployment** | 玩家可能不从 starter 改，而是重写整个 YAML。check_fn 只看终态，OK | starter_yaml 给出 v1 框架，引导玩家只改 image |

---

## 9. 📚 引用

[1] Kubernetes 官方文档 - Deployment:
https://kubernetes.io/docs/concepts/workloads/controllers/deployment/

[2] Kubernetes 官方文档 - ReplicaSet:
https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/

[3] Kubernetes 官方文档 - kubectl rollout:
https://kubernetes.io/docs/reference/kubectl/conventions/#rolling-back-to-a-previous-revision
（rollout undo / history / status 命令族）

---

*调研员: Researcher | 为 k8s-quest Chapter 2 提供 | 2026-07-06*
