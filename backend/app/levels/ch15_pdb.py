"""Chapter 15: PodDisruptionBudget（PDB 中断预算）（5 关）

Q15.1 创建第一个 PDB
Q15.2 PDB with minAvailable（百分比）
Q15.3 PDB with maxUnavailable
Q15.4 PDB 保护场景分析（selector + 中断类型）
Q15.5 集群实战 - 保护生产应用
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, ClusterState, K8sError


# ==================== Q15.1 创建第一个 PDB ====================

def _check_151_create_pdb(user_yaml: str) -> CheckResult:
    """Q15.1 创建一个 minAvailable: 2 的 PDB"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.poddisruptionbudgets:
        return CheckResult(
            ok=False,
            error="没有创建任何 PodDisruptionBudget",
            hints=["你需要 apply 一个 kind: PodDisruptionBudget 的 YAML"],
        )

    pdb_name = next(iter(state.poddisruptionbudgets))
    pdb = state.poddisruptionbudgets[pdb_name]
    spec = pdb.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PDB 缺少 spec", hints=[])

    if "minAvailable" not in spec:
        return CheckResult(
            ok=False,
            error="PDB 缺少 spec.minAvailable",
            hints=["添加 spec.minAvailable: 2"],
        )

    min_available = spec.get("minAvailable")
    if isinstance(min_available, bool) or not isinstance(min_available, int):
        return CheckResult(
            ok=False,
            error=f"spec.minAvailable 应为整数，实际为 {type(min_available).__name__}: {min_available}",
            hints=["设置 spec.minAvailable: 2（整数）"],
        )
    if min_available != 2:
        return CheckResult(
            ok=False,
            error=f"spec.minAvailable 应为 2，实际为 {min_available}",
            hints=["设置 spec.minAvailable: 2"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["PDB 确保自愿中断时至少保持 2 个副本可用 🛡️"],
    )


LEVEL_Q15_1 = Level(
    id="Q15.1",
    chapter="ch15",
    title="创建第一个 PDB",
    description="""
# 创建第一个 PDB 🛡️

**PodDisruptionBudget（PDB）** 用于限制**自愿中断**（如节点维护、滚动更新）时可以同时驱逐的 Pod 数量，保证应用始终有足够的副本可用。

## 任务

创建一个 PDB，保证至少 2 个副本可用：
- `kind: PodDisruptionBudget`
- `apiVersion: policy/v1`
- `spec.minAvailable: 2`
- `spec.selector` 匹配 `app: web`

## 提示

PDB 的核心字段是 `minAvailable` 或 `maxUnavailable`，二选一：
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```
""",
    starter_yaml="""\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  # minAvailable: 2
  selector:
    matchLabels:
      app: web
""",
    check_fn=_check_151_create_pdb,
    lesson=Lesson(
        concept="""\
## 什么是 PodDisruptionBudget？

**PodDisruptionBudget（PDB）** 是 Kubernetes 中用于保护应用在**自愿中断**期间可用性的资源。它告诉控制器在驱逐 Pod 时必须保留多少副本。

### 自愿中断 vs 非自愿中断

| 类型 | 说明 | PDB 是否生效 |
|------|------|-------------|
| **自愿中断** | 节点维护、滚动更新、HPA 缩容、kubectl drain | ✅ 生效 |
| **非自愿中断** | 硬件故障、内核崩溃、网络分区、断电 | ❌ 不生效 |

### PDB 的两个关键字段

- **`minAvailable`**：中断后至少保持多少 Pod 可用
- **`maxUnavailable`**：最多允许多少 Pod 不可用

两个字段**只能指定其中一个**，不能同时设置。

### PDB 如何工作

1. 管理员执行 `kubectl drain node` 驱逐节点上的 Pod
2. PDB Controller 检查驱逐是否违反预算
3. 如果违反（可用 Pod < minAvailable），驱逐被**阻止或延迟**
4. 直到有足够 Pod 恢复，驱逐才会继续

### 典型使用场景

- 生产环境 Deployment（至少保持 N 个副本）
- 数据库 StatefulSet（避免同时驱逐多个实例）
- 关键微服务（确保服务不中断）
""",
        key_fields=[
            {"name": "spec.minAvailable", "description": "中断后至少保持可用的 Pod 数量（整数或百分比）", "required": False, "example": "2 或 50%"},
            {"name": "spec.maxUnavailable", "description": "最多允许不可用的 Pod 数量（整数或百分比）", "required": False, "example": "1 或 25%"},
            {"name": "spec.selector", "description": "标签选择器，匹配受保护的 Pod", "required": True, "example": "matchLabels: {app: web}"},
        ],
        diagram="""\
  ┌─────────── PodDisruptionBudget (web-pdb) ───────────┐
  │  spec:                                              │
  │    minAvailable: 2   ◄── 至少保持 2 个可用           │
  │    selector:                                        │
  │      matchLabels:                                   │
  │        app: web       ◄── 匹配 app=web 的 Pod       │
  └───────────────────────┬────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
     ┌─────────┐     ┌─────────┐     ┌─────────┐
     │ Pod-web │     │ Pod-web │     │ Pod-web │
     │  (1)    │     │  (2)    │     │  (3)    │
     └─────────┘     └─────────┘     └─────────┘
                          │
                    kubectl drain
                    (自愿中断)
                          │
              ┌────── PDB 检查 ──────┐
              │ 可用 Pod >= 2?       │
              │ 是 → 允许驱逐 1 个    │
              │ 否 → 阻止/等待       │
              └─────────────────────┘
""",
        example_yaml="""\
apiVersion: policy/v1              # PDB API 版本
kind: PodDisruptionBudget          # 资源类型
metadata:                          # 元数据
  name: web-pdb                    # PDB 名称
spec:                              # 规格定义
  minAvailable: 2                  # 至少保持 2 个可用
  selector:                        # 标签选择器
    matchLabels:                   # 精确匹配标签
      app: web                     # 匹配 app=web 的 Pod
""",
        common_errors=[
            "同时设置 minAvailable 和 maxUnavailable（只能二选一）",
            "apiVersion 写成 apps/v1 而非 policy/v1",
            "忘记写 selector（PDB 必须指定保护哪些 Pod）",
            "minAvailable 设得大于 Pod 总数（PDB 会永远阻止驱逐）",
        ],
        tips=[
            "用 kubectl get pdb 查看 PDB 状态和 ALLOWED DISRUPTIONS 列",
            "PDB 只对自愿中断生效，硬件故障等非自愿中断不受 PDB 约束",
            "minAvailable 和 maxUnavailable 可以用百分比（如 50%）",
        ],
    ),
)


# ==================== Q15.2 PDB with minAvailable（百分比） ====================

def _check_152_min_available_percent(user_yaml: str) -> CheckResult:
    """Q15.2 使用百分比形式的 minAvailable"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.poddisruptionbudgets:
        return CheckResult(
            ok=False,
            error="没有创建任何 PodDisruptionBudget",
            hints=["你需要 apply 一个 kind: PodDisruptionBudget 的 YAML"],
        )

    pdb_name = next(iter(state.poddisruptionbudgets))
    pdb = state.poddisruptionbudgets[pdb_name]
    spec = pdb.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PDB 缺少 spec", hints=[])

    if "minAvailable" not in spec:
        return CheckResult(
            ok=False,
            error="PDB 缺少 spec.minAvailable",
            hints=["使用百分比形式: spec.minAvailable: '50%'"],
        )

    min_available = spec.get("minAvailable")
    # 百分比形式是字符串（如 "50%"），整数形式是 int
    import re
    if isinstance(min_available, str) and re.match(r'^\d+%$', min_available):
        pct_num = int(min_available.rstrip('%'))
        if pct_num < 0 or pct_num > 100:
            return CheckResult(
                ok=False,
                error=f"minAvailable 百分比应在 0-100 范围内，实际为 {min_available}",
                hints=["使用 0%-100% 范围内的百分比"],
            )
        return CheckResult(
            ok=True, state=state,
            hints=["百分比形式的 minAvailable 会根据实际 Pod 数量动态计算 📊"],
        )
    else:
        return CheckResult(
            ok=False,
            error=f"minAvailable 应为百分比字符串（如 '50%'），实际为 {min_available}",
            hints=["百分比形式必须加引号: minAvailable: '50%'"],
        )


LEVEL_Q15_2 = Level(
    id="Q15.2",
    chapter="ch15",
    title="PDB with minAvailable（百分比）",
    description="""
# PDB minAvailable 百分比 📊

`minAvailable` 不仅支持整数，还支持**百分比**字符串。当 Pod 数量动态变化时，百分比更灵活。

## 任务

创建一个 PDB，使用百分比形式的 `minAvailable`：
- `spec.minAvailable: "50%"`
- `spec.selector` 匹配 `app: api`

## 提示

百分比必须是**字符串**类型，需要加引号：
```yaml
spec:
  minAvailable: "50%"   # 字符串，加引号
  # minAvailable: 50    # 这是整数，不是百分比
```
""",
    starter_yaml="""\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
spec:
  # minAvailable: "50%"
  selector:
    matchLabels:
      app: api
""",
    check_fn=_check_152_min_available_percent,
    lesson=Lesson(
        concept="""\
## minAvailable 的百分比形式

`minAvailable` 支持两种格式：

| 格式 | 类型 | 示例 | 说明 |
|------|------|------|------|
| 整数 | int | `2` | 固定保持 2 个 Pod 可用 |
| 百分比 | string | `"50%"` | 保持 50% 的 Pod 可用 |

### 百分比的计算方式

假设有 6 个 Pod，`minAvailable: "50%"`：
- 向上取整：ceil(6 × 0.5) = 3 → 至少保持 3 个可用
- 允许驱逐：6 - 3 = 3 个

### 什么时候用百分比？

- **Pod 数量动态变化**：配合 HPA 自动伸缩时，百分比能自适应
- **大规模集群**：不需要手动调整 PDB 数字
- **通用模板**：同一份 PDB 配置可用于不同规模的部署

### 整数 vs 百分比

```
场景: Deployment replicas=4

整数: minAvailable: 2
  → 固定保持 2 个可用，允许驱逐 2 个
  → 如果扩容到 10 个，仍然只保证 2 个（可能不够安全）

百分比: minAvailable: "50%"
  → 4 个 Pod 时保证 2 个可用
  → 10 个 Pod 时保证 5 个可用（自动适应）
```
""",
        key_fields=[
            {"name": "spec.minAvailable (int)", "description": "整数形式，固定数量", "required": False, "example": "2"},
            {"name": "spec.minAvailable (string)", "description": "百分比字符串，自适应数量", "required": False, "example": "'50%'"},
            {"name": "spec.selector", "description": "标签选择器", "required": True, "example": "matchLabels: {app: api}"},
        ],
        diagram="""\
  minAvailable: "50%"  (百分比模式)

  replicas=4 时:
  ┌────────────────────────────────────┐
  │  Pod-1  Pod-2  Pod-3  Pod-4       │  4 个 Pod
  │  ✅     ✅     ✅     ✅           │  全部可用
  └────────────────────────────────────┘
  minAvailable = ceil(4 × 0.5) = 2
  允许驱逐 = 4 - 2 = 2

  replicas=10 时 (自动适应):
  ┌──────────────────────────────────────────────────┐
  │  Pod-1 ... Pod-5  ✅✅✅✅✅  (必须保持)       │  至少 5 个
  │  Pod-6 ... Pod-10  可被驱逐                      │  允许驱逐 5 个
  └──────────────────────────────────────────────────┘
  minAvailable = ceil(10 × 0.5) = 5
""",
        example_yaml="""\
apiVersion: policy/v1              # PDB API 版本
kind: PodDisruptionBudget          # 资源类型
metadata:                          # 元数据
  name: api-pdb                    # PDB 名称
spec:                              # 规格定义
  minAvailable: "50%"              # 百分比形式（字符串）
  selector:                        # 标签选择器
    matchLabels:                   # 精确匹配
      app: api                     # 匹配 app=api 的 Pod
""",
        common_errors=[
            "百分比没加引号，YAML 把 50% 解析成字符串 50%（巧合正确但不规范）或报错",
            "同时设置 minAvailable 和 maxUnavailable",
            "百分比设为 100% 等于完全阻止驱逐（慎用）",
            "百分比设为 0% 等于没有保护（失去 PDB 意义）",
        ],
        tips=[
            "百分比形式向上取整：ceil(N × percent)",
            "用 kubectl get pdb -o yaml 查看 PDB 详情",
            "推荐在配合 HPA 使用时采用百分比形式",
        ],
    ),
)


# ==================== Q15.3 PDB with maxUnavailable ====================

def _check_153_max_unavailable(user_yaml: str) -> CheckResult:
    """Q15.3 使用 maxUnavailable 的 PDB"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.poddisruptionbudgets:
        return CheckResult(
            ok=False,
            error="没有创建任何 PodDisruptionBudget",
            hints=["你需要 apply 一个 kind: PodDisruptionBudget 的 YAML"],
        )

    pdb_name = next(iter(state.poddisruptionbudgets))
    pdb = state.poddisruptionbudgets[pdb_name]
    spec = pdb.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PDB 缺少 spec", hints=[])

    if "maxUnavailable" not in spec:
        return CheckResult(
            ok=False,
            error="PDB 缺少 spec.maxUnavailable",
            hints=["使用 maxUnavailable 而非 minAvailable: spec.maxUnavailable: 1"],
        )

    max_unavail = spec.get("maxUnavailable")
    if isinstance(max_unavail, bool) or not isinstance(max_unavail, int):
        return CheckResult(
            ok=False,
            error=f"spec.maxUnavailable 应为整数，实际为 {type(max_unavail).__name__}: {max_unavail}",
            hints=["设置 spec.maxUnavailable: 1（整数）"],
        )
    if max_unavail != 1:
        return CheckResult(
            ok=False,
            error=f"spec.maxUnavailable 应为 1，实际为 {max_unavail}",
            hints=["设置 spec.maxUnavailable: 1"],
        )

    # 不能同时设置 minAvailable
    if "minAvailable" in spec:
        return CheckResult(
            ok=False,
            error="不能同时设置 minAvailable 和 maxUnavailable",
            hints=["PDB 只能设置其中一个，删除 minAvailable"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["maxUnavailable: 1 表示最多允许 1 个 Pod 不可用 🔢"],
    )


LEVEL_Q15_3 = Level(
    id="Q15.3",
    chapter="ch15",
    title="PDB with maxUnavailable",
    description="""
# PDB maxUnavailable 🔢

`maxUnavailable` 是另一种 PDB 策略：限制**最多允许多少 Pod 不可用**，而不是要求最少保持多少可用。

## 任务

创建一个 PDB，使用 `maxUnavailable: 1`：
- `spec.maxUnavailable: 1`
- `spec.selector` 匹配 `app: db`
- **不要**同时设置 minAvailable

## 提示

maxUnavailable 和 minAvailable 的关系：
```
maxUnavailable = total - minAvailable

示例: 5 个 Pod
  minAvailable: 4      ⟺  maxUnavailable: 1
  minAvailable: 3      ⟺  maxUnavailable: 2
```
""",
    starter_yaml="""\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: db-pdb
spec:
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: db
""",
    check_fn=_check_153_max_unavailable,
    lesson=Lesson(
        concept="""\
## maxUnavailable 策略

`maxUnavailable` 从另一个角度保护应用：限制**最多**允许多少 Pod 同时不可用。

### minAvailable vs maxUnavailable

| 字段 | 语义 | 示例 | 效果 |
|------|------|------|------|
| `minAvailable` | 至少保持多少可用 | `minAvailable: 4` | 5 个 Pod 时允许驱逐 1 个 |
| `maxUnavailable` | 最多允许多少不可用 | `maxUnavailable: 1` | 5 个 Pod 时允许驱逐 1 个 |

两者在数学上是等价的：`maxUnavailable = total - minAvailable`，但语义不同：

- **minAvailable**：关注"保底可用数"，适合关注 SLA 的场景
- **maxUnavailable**：关注"允许的破坏量"，适合滚动更新场景

### maxUnavailable 的优势

1. **更直观表达"允许的破坏量"**：比如"每次只允许 1 个不可用"
2. **配合滚动更新**：与 Deployment 的 `maxUnavailable` 字段语义一致
3. **零值语义清晰**：`maxUnavailable: 0` = 完全阻止驱逐

### 选择建议

```
如果你关心"至少 N 个可用"       → 用 minAvailable
如果你关心"最多允许 N 个不可用"  → 用 maxUnavailable
如果配合 HPA 动态伸缩            → 用百分比形式的 minAvailable
```
""",
        key_fields=[
            {"name": "spec.maxUnavailable", "description": "最多允许不可用的 Pod 数量（整数或百分比）", "required": False, "example": "1 或 '25%'"},
            {"name": "spec.minAvailable", "description": "至少保持可用的 Pod 数量（与 maxUnavailable 互斥）", "required": False, "example": "4"},
            {"name": "spec.selector", "description": "标签选择器", "required": True, "example": "matchLabels: {app: db}"},
        ],
        diagram="""\
  maxUnavailable: 1  (最多允许 1 个不可用)

  ┌─────────── PodDisruptionBudget (db-pdb) ───────────┐
  │  spec:                                             │
  │    maxUnavailable: 1  ◄── 最多 1 个不可用           │
  │    selector:                                       │
  │      matchLabels:                                  │
  │        app: db        ◄── 匹配 app=db 的 Pod       │
  └───────────────────────┬───────────────────────────┘
                          │
  ┌─────── 5 个 Pod ──────┐
  │  Pod-db-1  ✅         │
  │  Pod-db-2  ✅         │  允许驱逐 1 个
  │  Pod-db-3  ✅         │  (maxUnavailable=1)
  │  Pod-db-4  ✅         │
  │  Pod-db-5  ✅         │
  └───────────────────────┘
        ↓ kubectl drain
  Pod-db-1 被驱逐 → 驱逐停止（已达上限）
  剩余 4 个可用，1 个不可用
""",
        example_yaml="""\
apiVersion: policy/v1              # PDB API 版本
kind: PodDisruptionBudget          # 资源类型
metadata:                          # 元数据
  name: db-pdb                     # PDB 名称
spec:                              # 规格定义
  maxUnavailable: 1               # 最多允许 1 个不可用
  selector:                        # 标签选择器
    matchLabels:                   # 精确匹配
      app: db                      # 匹配 app=db 的 Pod
""",
        common_errors=[
            "同时设置 minAvailable 和 maxUnavailable（API 会拒绝）",
            "maxUnavailable 设为 0 导致完全无法驱逐（节点维护被阻塞）",
            "maxUnavailable 设得过大失去保护意义",
            "apiVersion 写错（PDB 使用 policy/v1）",
        ],
        tips=[
            "maxUnavailable: 0 用于完全阻止自愿驱逐（如单实例数据库）",
            "maxUnavailable 也支持百分比形式（如 '25%'）",
            "选择 minAvailable 还是 maxUnavailable 取决于团队的思维习惯",
        ],
    ),
)


# ==================== Q15.4 PDB 保护场景分析 ====================

def _check_154_protection_scenario(user_yaml: str) -> CheckResult:
    """Q15.4 PDB 保护场景：selector + maxUnavailable 保护 Nginx"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.poddisruptionbudgets:
        return CheckResult(
            ok=False,
            error="没有创建任何 PodDisruptionBudget",
            hints=["你需要 apply 一个 kind: PodDisruptionBudget 的 YAML"],
        )

    pdb_name = next(iter(state.poddisruptionbudgets))
    pdb = state.poddisruptionbudgets[pdb_name]
    spec = pdb.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="PDB 缺少 spec", hints=[])

    # 验证 selector 匹配 app=nginx
    selector = spec.get("selector", {})
    if not isinstance(selector, dict):
        return CheckResult(ok=False, error="PDB 缺少 spec.selector", hints=[])

    match_labels = selector.get("matchLabels", {})
    if not isinstance(match_labels, dict) or match_labels.get("app") != "nginx":
        return CheckResult(
            ok=False,
            error="selector.matchLabels.app 应为 nginx",
            hints=["设置 selector.matchLabels: {app: nginx}"],
        )

    # 验证使用 maxUnavailable: 1
    if "maxUnavailable" not in spec:
        return CheckResult(
            ok=False,
            error="PDB 应使用 maxUnavailable 来限制中断",
            hints=["添加 spec.maxUnavailable: 1"],
        )

    max_unavail = spec.get("maxUnavailable")
    if isinstance(max_unavail, bool) or not isinstance(max_unavail, int):
        return CheckResult(
            ok=False,
            error=f"spec.maxUnavailable 应为整数，实际为 {type(max_unavail).__name__}: {max_unavail}",
            hints=["设置 spec.maxUnavailable: 1（整数）"],
        )
    if max_unavail != 1:
        return CheckResult(
            ok=False,
            error=f"spec.maxUnavailable 应为 1，实际为 {max_unavail}",
            hints=["设置 spec.maxUnavailable: 1"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["PDB 通过 selector 精确定位需要保护的 Pod，maxUnavailable 控制中断上限 🎯"],
    )


LEVEL_Q15_4 = Level(
    id="Q15.4",
    chapter="ch15",
    title="PDB 保护场景分析",
    description="""
# PDB 保护场景分析 🎯

PDB 通过 `selector` 精确定位需要保护的 Pod，结合 `maxUnavailable` 控制中断上限。理解自愿中断与非自愿中断的区别是正确使用 PDB 的关键。

## 任务

创建一个 PDB 保护 Nginx 应用：
- `spec.selector.matchLabels.app: nginx`
- `spec.maxUnavailable: 1`
- PDB 名称为 `nginx-pdb`

## 提示

PDB 只保护**自愿中断**，以下是中断类型对照：
```
自愿中断（PDB 生效）:
  - kubectl drain（节点维护）
  - 滚动更新
  - HPA 缩容
  - kubectl delete pod

非自愿中断（PDB 不生效）:
  - 硬件故障
  - 内核崩溃
  - 网络分区
```
""",
    starter_yaml="""\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  # maxUnavailable: 1
  selector:
    matchLabels:
      # app: nginx
""",
    check_fn=_check_154_protection_scenario,
    lesson=Lesson(
        concept="""\
## PDB 保护场景深度分析

### 自愿中断 vs 非自愿中断

PDB 只能保护**自愿中断**，不能阻止**非自愿中断**。

#### 自愿中断（Voluntary Disruption）

由管理员或控制器主动发起的 Pod 驱逐：

| 操作 | 触发者 | 说明 |
|------|--------|------|
| `kubectl drain` | 管理员 | 节点维护前驱逐所有 Pod |
| 滚动更新 | Deployment Controller | 逐个替换旧版本 Pod |
| HPA 缩容 | HPA Controller | 根据负载减少 Pod 数量 |
| `kubectl delete pod` | 管理员 | 手动删除 Pod |
| 节点压力驱逐 | Kubelet | 资源不足时驱逐（部分场景） |

#### 非自愿中断（Involuntary Disruption）

由不可控因素导致的 Pod 失效：

| 原因 | 说明 |
|------|------|
| 硬件故障 | 节点机器物理损坏 |
| 内核崩溃 | 操作系统 panic |
| 网络分区 | 节点与集群失联 |
| 断电 | 突然断电导致节点宕机 |
| OOM Kill | 容器内存超出限制被杀 |

### PDB 的 selector 机制

PDB 通过 `selector` 匹配 Pod 标签，只有被匹配到的 Pod 才受保护：

```yaml
selector:
  matchLabels:
    app: nginx      # 只保护带 app=nginx 标签的 Pod
```

也可以使用 `matchExpressions` 进行更复杂的匹配：

```yaml
selector:
  matchExpressions:
    - key: app
      operator: In
      values: [nginx, api]
```

### PDB 的工作流程

```
1. 管理员执行 kubectl drain node-1
2. Eviction Controller 收到驱逐请求
3. 检查该 Pod 是否被 PDB 保护
4. 计算当前可用 Pod 数 vs PDB 要求
5. 如果满足预算 → 允许驱逐
6. 如果违反预算 → 阻止或等待（返回 429 Too Many Requests）
```
""",
        key_fields=[
            {"name": "spec.selector", "description": "标签选择器，精确匹配受保护的 Pod", "required": True, "example": "matchLabels: {app: nginx}"},
            {"name": "spec.maxUnavailable", "description": "最多允许不可用的 Pod 数量", "required": False, "example": "1"},
            {"name": "spec.minAvailable", "description": "至少保持可用的 Pod 数量", "required": False, "example": "2"},
        ],
        diagram="""\
  ┌─────────── PodDisruptionBudget (nginx-pdb) ──────────┐
  │  spec:                                               │
  │    maxUnavailable: 1                                 │
  │    selector:                                         │
  │      matchLabels:                                    │
  │        app: nginx      ◄── 精确匹配                  │
  └────────────────────────┬────────────────────────────┘
                           │ selector 匹配
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │Pod-nginx│       │Pod-nginx│       │Pod-nginx│
    │app=nginx│       │app=nginx│       │app=nginx│
    └─────────┘       └─────────┘       └─────────┘
         │
         │ kubectl drain (自愿中断)
         ▼
    ┌─────────────────────────────┐
    │  Eviction Controller        │
    │  检查 PDB: maxUnavailable=1 │
    │  当前不可用: 0 < 1          │
    │  → 允许驱逐 ✓               │
    └─────────────────────────────┘
""",
        example_yaml="""\
apiVersion: policy/v1              # PDB API 版本
kind: PodDisruptionBudget          # 资源类型
metadata:                          # 元数据
  name: nginx-pdb                  # PDB 名称
spec:                              # 规格定义
  maxUnavailable: 1                # 最多允许 1 个不可用
  selector:                        # 标签选择器
    matchLabels:                   # 精确匹配
      app: nginx                   # 保护 app=nginx 的 Pod
""",
        common_errors=[
            "selector 匹配不到任何 Pod（PDB 不起作用）",
            "selector 匹配范围过大，保护了不该保护的 Pod",
            "误以为 PDB 能防止硬件故障（只对自愿中断有效）",
            "PDB 与 Deployment 的 selector 不一致",
        ],
        tips=[
            "PDB 的 selector 应该与对应 Deployment 的 selector 一致",
            "用 kubectl get pdb 查看 ALLOWED DISRUPTIONS 列，-1 表示不满足预算",
            "单实例应用设 maxUnavailable: 0 可防止驱逐，但会阻塞节点维护",
        ],
    ),
)


# ==================== Q15.5 集群实战 - 保护生产应用 ====================

def _check_155_production_protection(user_yaml: str) -> CheckResult:
    """Q15.5 多文档 YAML：Deployment (3 replicas) + PDB (minAvailable: 2)"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 检查 Deployment
    if not state.deployments:
        return CheckResult(
            ok=False,
            error="没有创建任何 Deployment",
            hints=["多文档 YAML 中应包含一个 kind: Deployment"],
        )

    dep_name = next(iter(state.deployments))
    dep = state.deployments[dep_name]
    dep_spec = dep.get("spec", {})
    if not isinstance(dep_spec, dict):
        return CheckResult(ok=False, error="Deployment 缺少 spec", hints=[])

    replicas = dep_spec.get("replicas")
    if replicas != 3:
        return CheckResult(
            ok=False,
            error=f"Deployment replicas 应为 3，实际为 {replicas}",
            hints=["设置 spec.replicas: 3"],
        )

    # 检查 PDB
    if not state.poddisruptionbudgets:
        return CheckResult(
            ok=False,
            error="没有创建任何 PodDisruptionBudget",
            hints=["多文档 YAML 中应包含一个 kind: PodDisruptionBudget"],
        )

    pdb_name = next(iter(state.poddisruptionbudgets))
    pdb = state.poddisruptionbudgets[pdb_name]
    pdb_spec = pdb.get("spec", {})
    if not isinstance(pdb_spec, dict):
        return CheckResult(ok=False, error="PDB 缺少 spec", hints=[])

    if "minAvailable" not in pdb_spec:
        return CheckResult(
            ok=False,
            error="PDB 缺少 spec.minAvailable",
            hints=["设置 PDB 的 spec.minAvailable: 2"],
        )

    min_avail = pdb_spec.get("minAvailable")
    if isinstance(min_avail, bool) or not isinstance(min_avail, int):
        return CheckResult(
            ok=False,
            error=f"PDB minAvailable 应为整数，实际为 {type(min_avail).__name__}: {min_avail}",
            hints=["设置 spec.minAvailable: 2（整数）"],
        )
    if min_avail != 2:
        return CheckResult(
            ok=False,
            error=f"PDB minAvailable 应为 2，实际为 {min_avail}",
            hints=["设置 spec.minAvailable: 2"],
        )

    # 验证 PDB selector 存在且非空，matchLabels 至少有一个 key
    selector = pdb_spec.get("selector", {})
    match_labels = selector.get("matchLabels", {}) if isinstance(selector, dict) else {}
    if not isinstance(match_labels, dict) or not match_labels:
        return CheckResult(
            ok=False,
            error="PDB 缺少有效的 selector.matchLabels（至少需要一个标签）",
            hints=["添加 selector.matchLabels 至少一个键值对"],
        )
    dep_labels = dep_spec.get("template", {}).get("metadata", {}).get("labels", {})
    if isinstance(match_labels, dict) and isinstance(dep_labels, dict):
        app_label = match_labels.get("app")
        if app_label and app_label != dep_labels.get("app"):
            return CheckResult(
                ok=False,
                error=f"PDB selector (app={app_label}) 与 Deployment label (app={dep_labels.get('app')}) 不匹配",
                hints=["PDB 的 selector 应与 Deployment 的 Pod label 一致"],
            )

    return CheckResult(
        ok=True, state=state,
        hints=["Deployment + PDB 组合是生产应用的标配保护方案 🏭"],
    )


LEVEL_Q15_5 = Level(
    id="Q15.5",
    chapter="ch15",
    title="集群实战 - 保护生产应用",
    description="""
# 集群实战 - 保护生产应用 🏭

在生产环境中，通常将 **Deployment + PDB** 组合使用，确保应用在节点维护或滚动更新时保持高可用。

## 任务

用**多文档 YAML**（`---` 分隔）创建：
1. **Deployment**：3 个副本的 Nginx 应用
2. **PDB**：`minAvailable: 2`，selector 匹配 `app: nginx`

## 提示

多文档 YAML 用 `---` 分隔：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: nginx
```
""",
    starter_yaml="""\
# --- Deployment ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  # replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
---
# --- PDB ---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  # minAvailable: 2
  selector:
    matchLabels:
      app: nginx
""",
    check_fn=_check_155_production_protection,
    lesson=Lesson(
        concept="""\
## 生产应用保护方案

在生产环境中，**Deployment + PDB** 是标准的高可用保护组合。

### 完整的生产保护配置

```
┌─────────────────────────────────────────────┐
│              生产应用保护方案                  │
├─────────────────────────────────────────────┤
│  1. Deployment (replicas=3)                 │
│     → 保证 3 个副本运行                      │
│     → Pod 故障自动重建                        │
│                                              │
│  2. PDB (minAvailable=2)                    │
│     → 自愿中断时至少保持 2 个可用             │
│     → 阻止同时驱逐 2 个以上 Pod              │
│                                              │
│  3. Anti-Affinity (可选)                    │
│     → Pod 分散到不同节点                      │
│     → 防止单节点故障影响多个 Pod             │
└─────────────────────────────────────────────┘
```

### 为什么 replicas=3 + minAvailable=2？

- **3 副本**：容忍 1 个 Pod 故障仍能服务
- **minAvailable=2**：自愿中断时最多驱逐 1 个
- **组合效果**：无论自愿还是非自愿中断，至少 2 个 Pod 可用

### 多文档 YAML

Kubernetes 支持在单个 YAML 文件中定义多个资源，用 `---` 分隔：

```yaml
apiVersion: apps/v1
kind: Deployment
# ... Deployment 内容
---
apiVersion: policy/v1
kind: PodDisruptionBudget
# ... PDB 内容
```

好处：
- 相关资源放在一起，便于管理
- 一次 `kubectl apply -f` 部署全部
- 版本控制更清晰

### 生产环境 PDB 最佳实践

1. **selector 与 Deployment 一致**：PDB 必须保护正确的 Pod
2. **minAvailable < replicas**：留出至少 1 个驱逐余量
3. **配合 Pod Anti-Affinity**：确保 Pod 分散在不同节点
4. **定期检查 PDB 状态**：`kubectl get pdb` 查看 ALLOWED DISRUPTIONS
5. **避免 maxUnavailable: 0**：除非是单实例关键应用，否则会阻塞节点维护
""",
        key_fields=[
            {"name": "Deployment spec.replicas", "description": "副本数，生产环境建议 >= 3", "required": True, "example": "3"},
            {"name": "PDB spec.minAvailable", "description": "至少保持可用的 Pod 数量", "required": True, "example": "2"},
            {"name": "PDB spec.selector", "description": "必须与 Deployment 的 Pod label 一致", "required": True, "example": "matchLabels: {app: nginx}"},
            {"name": "--- (多文档分隔)", "description": "YAML 多文档分隔符", "required": True, "example": "---"},
        ],
        diagram="""\
  ┌─────────── 多文档 YAML ───────────┐
  │                                    │
  │  ---                               │
  │  Deployment (nginx-deploy)         │
  │    replicas: 3                     │
  │    template:                       │
  │      labels: {app: nginx}          │
  │                                    │
  │  ---                               │
  │  PodDisruptionBudget (nginx-pdb)   │
  │    minAvailable: 2                 │
  │    selector: {app: nginx}          │
  │                                    │
  └───────────────┬────────────────────┘
                  │ kubectl apply -f
                  ▼
  ┌─────── 集群状态 ───────────────────┐
  │                                    │
  │  Pod-nginx-1  ✅ (node-1)         │
  │  Pod-nginx-2  ✅ (node-2)         │
  │  Pod-nginx-3  ✅ (node-3)         │
  │                                    │
  │  PDB: minAvailable=2               │
  │  → 节点维护时最多驱逐 1 个          │
  │  → 始终保持 2 个 Pod 可用           │
  └────────────────────────────────────┘
""",
        example_yaml="""\
# --- Deployment ---
apiVersion: apps/v1               # Deployment API 版本
kind: Deployment                  # 资源类型
metadata:                         # 元数据
  name: nginx-deploy              # Deployment 名称
spec:                             # 规格定义
  replicas: 3                     # 3 个副本
  selector:                       # 标签选择器
    matchLabels:
      app: nginx
  template:                       # Pod 模板
    metadata:
      labels:
        app: nginx                # Pod 标签
    spec:
      containers:
      - name: nginx               # 容器名
        image: nginx:1.25         # 镜像
---
# --- PodDisruptionBudget ---
apiVersion: policy/v1             # PDB API 版本
kind: PodDisruptionBudget         # 资源类型
metadata:                         # 元数据
  name: nginx-pdb                 # PDB 名称
spec:                             # 规格定义
  minAvailable: 2                 # 至少 2 个可用
  selector:                       # 与 Deployment 一致
    matchLabels:
      app: nginx
""",
        common_errors=[
            "PDB selector 与 Deployment label 不匹配（保护了错误的 Pod）",
            "minAvailable 设为等于 replicas（完全阻止驱逐，阻塞维护）",
            "多文档 YAML 忘记用 --- 分隔",
            "只创建 PDB 没有创建 Deployment（PDB 保护了不存在的 Pod）",
        ],
        tips=[
            "生产环境建议 replicas >= 3 且 minAvailable = replicas - 1",
            "配合 podAntiAffinity 将 Pod 分散到不同节点",
            "用 kubectl get pdb 定期检查 ALLOWED DISRUPTIONS 是否为正数",
            "kubectl drain 时加 --ignore-daemonsets --delete-emptydir-data 参数",
        ],
    ),
)


CHAPTER_15_LEVELS: list[Level] = [
    LEVEL_Q15_1, LEVEL_Q15_2, LEVEL_Q15_3, LEVEL_Q15_4, LEVEL_Q15_5,
]
