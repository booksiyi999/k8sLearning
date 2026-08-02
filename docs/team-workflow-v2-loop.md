# K8s Quest 团队 Agent 工作流 — Loop Engineering 架构 v2

> 版本: v2.0 | 日期: 2026-07-25 | 作者: cherry
> 变更: 从 Pipeline 模式升级为 Loop Engineering 三层循环架构
> 前版: v1.0 (2025-07-05) 基于 Kanban 的单向流水线

---

## 一、架构变更说明

### 1.1 为什么要改

现有 Pipeline 模式（PM→Researcher→Engineer→QA 单向流转）存在三个问题：

1. **反馈延迟高**：QA 发现 bug→block→等 cherry 转发→Engineer 修复→unblock→QA 重测，一个循环要小时级
2. **Master 介入频繁**：每个阶段完成后都要 cherry 汇报→Master 决策，打断心流
3. **质量保障后置**：只有 QA 阶段才测试，Engineer 写完代码不自测就提交

### 1.2 Loop Engineering 核心改变

| 维度 | v1 Pipeline | v2 Loop Engineering |
|---|---|---|
| Engineer 行为 | 写完代码就提交 | **写完→自跑测试→失败自修→循环到全绿才提交** |
| QA 行为 | 跑现有测试→block/unblock | **跑现有测试→自己生成攻击用例→发现 bug 自动回传 Engineer→循环攻击** |
| PM 行为 | 分解→派发→等完成 | **分解→派发→监控中循环→质量门禁→3次失败才升级 Master** |
| Master 介入 | 每阶段 1-2 次 | **每个目标 1 次验收** |
| bug 发现到修复 | 小时级 | **秒级（内循环自动）** |

---

## 二、三层循环架构

```
┌───────────────────────────────────────────────────────────────────┐
│  外循环（Outer Loop）— 天/周级，Master 驱动                        │
│                                                                   │
│  ┌→ Master 下发目标+验收标准                                      │
│  │    → PM Orchestrator 分解为子任务                              │
│  │    → Agent 团队自主完成（中循环+内循环）                       │
│  │    → PM 收集结果，质量门禁检查                                 │
│  │    → Master 验收                                               │
│  │       → 满意：进入下一个目标                                   │
│  └────── 不满意：给修正方向，Agent 进入新一轮外循环               │
│                                                                   │
│  介入频率：每个目标 1 次                                          │
│  终止条件：Master 验收通过                                        │
├───────────────────────────────────────────────────────────────────┤
│  中循环（Middle Loop）— 小时级，PM Orchestrator 驱动               │
│                                                                   │
│  ┌→ PM 分解目标为子任务列表                                       │
│  │    → 每个子任务派给 Engineer（触发内循环）                     │
│  │    → Engineer 内循环完成（代码+测试全绿）                      │
│  │    → PM 派给 QA（触发攻击循环）                                │
│  │    → QA 攻击循环：跑测试→生成攻击用例→发现bug→自动回传Engineer │
│  │       → Engineer 修复→QA 再攻击                                │
│  │    → QA 3轮攻击无 bug → 派给 Code Review                       │
│  │    → Review 通过 → 标记子任务完成                              │
│  │    → 所有子任务完成 → 触发外循环验收                           │
│  └── 任何环节 3 次失败 → 升级 Master                              │
│                                                                   │
│  介入频率：0 次（PM 自主管理）                                    │
│  终止条件：所有子任务通过 OR 3 次升级                              │
├───────────────────────────────────────────────────────────────────┤
│  内循环（Inner Loop）— 秒/分钟级，Engineer 自驱动                  │
│                                                                   │
│  ┌→ Engineer 收到子任务                                           │
│  │    → 写代码（TDD: 先写测试再写实现）                           │
│  │    → 运行测试 (npm test / pytest / go test)                    │
│  │       → 失败：分析报错→自动修复→回到运行测试                   │
│  │       → 全绿：提交给 QA                                        │
│  └── 循环上限 5 次，超过则升级 Orchestrator                       │
│                                                                   │
│  介入频率：0 次（完全自主）                                       │
│  终止条件：测试全绿 OR 5 次迭代上限                                │
└───────────────────────────────────────────────────────────────────┘
```

### QA 攻击循环（Attack Loop）— 中循环内嵌

```
┌→ QA 收到 Engineer 提交的代码
│    → Phase 1: 运行 Engineer 已有的测试用例
│       → 失败：直接打回 Engineer（附失败详情）
│       → 通过：进入 Phase 2
│    → Phase 2: QA 自己生成攻击性测试用例
│       - 边界值攻击（空值/极大值/负数/特殊字符）
│       - 异常输入攻击（类型错误/格式错误/注入）
│       - 并发攻击（竞态条件/资源争抢）
│       - 退化攻击（旧版本数据兼容/回滚场景）
│    → 运行攻击用例
│       → 发现 bug：自动创建修复任务给 Engineer（附 bug 详情+复现步骤+预期结果）
│       → Engineer 修复后回到 Phase 1
│    → Phase 3: 3 轮攻击无新 bug → APPROVED → 派给 Code Review
└── 循环上限 3 轮攻击，3 轮无 bug 才放行
```

---

## 三、Profile 角色调整

### 3.1 PM → Orchestrator（中循环管理者）

**变更说明**：PM 从"分解+派发"升级为"中循环管理者"

| 旧职责 | 新增职责 |
|---|---|
| 分解需求为任务图 | 不变 |
| 派发任务到 Kanban | 不变 |
| 等待任务完成后综合 | **主动监控中循环进度** |
| 汇报给 Master | **质量门禁检查：所有子任务通过才触发外循环验收** |
| — | **3 次失败升级 Master（而非每次失败都汇报）** |
| — | **控制中循环节奏：并行子任务不超 3 个** |

**关键行为变化**：
- 旧：PM 派发后被动等待，任何问题都汇报 Master
- 新：PM 派发后主动监控，Engineer↔QA 之间的 bug 修复循环由 PM 协调但不升级 Master，只有 3 次修复失败才升级

### 3.2 Engineer → 自驱动循环编码者

**变更说明**：Engineer 从"写完提交"升级为"自驱动测试循环"

| 旧职责 | 新增职责 |
|---|---|
| TDD 写代码 | 不变 |
| commit + push | 不变 |
| 等 QA 反馈后修复 | **写完代码立刻自己跑测试** |
| — | **测试失败自己分析自己修，循环到全绿** |
| — | **5 次迭代上限，超过升级 PM** |
| — | **收到 QA 回传的 bug，自动进入修复循环** |

**关键行为变化**：
- 旧：写完代码 push 就完了，等 QA 测出问题再修
- 新：写完代码**必须自己跑测试通过才提交**，QA 发现的 bug **自动接收并修复**，不需要 PM 转发

**内循环伪代码**：
```python
def engineer_inner_loop(task):
    code = write_code(task)          # TDD: 先写测试再写实现
    for i in range(5):               # 最多 5 次迭代
        result = run_tests(code)
        if result.all_passed:
            submit_to_qa(code)
            return SUCCESS
        else:
            code = analyze_and_fix(result.errors, code)
    escalate_to_pm(task, "内循环5次未通过")
    return ESCALATE
```

### 3.3 QA → 攻击性循环测试者

**变更说明**：QA 从"跑测试+block"升级为"攻击循环+自动回传"

| 旧职责 | 新增职责 |
|---|---|
| Code Review | 不变 |
| 运行现有测试 | 不变 |
| 发现 bug → block 任务 | **发现 bug → 自动创建修复任务给 Engineer** |
| 等 Engineer 修复后 unblock | **Engineer 修复后自动重新进入攻击循环** |
| — | **自己生成攻击性测试用例（不依赖已有用例）** |
| — | **3 轮攻击无 bug 才 APPROVED** |

**关键行为变化**：
- 旧：跑 QA 已有用例→发现 bug→block→等 PM 协调→Engineer 修→unblock→重测
- 新：跑已有用例→**自己生成新攻击用例**→发现 bug→**直接创建修复任务给 Engineer**（附 bug 详情）→Engineer 修完→**自动重新攻击**→3 轮无 bug 才放行

**攻击循环伪代码**：
```python
def qa_attack_loop(submitted_code):
    for round in range(3):           # 最多 3 轮攻击
        # Phase 1: 跑已有测试
        if not run_existing_tests(submitted_code):
            send_bug_to_engineer(failures)
            submitted_code = wait_for_fix()
            continue  # 重新进入本轮攻击

        # Phase 2: 生成攻击用例
        attack_cases = generate_attack_cases(submitted_code)
        failures = run_attack_cases(attack_cases)
        if failures:
            send_bug_to_engineer(failures)
            submitted_code = wait_for_fix()
        else:
            continue  # 本轮无 bug，进入下一轮

    # 3 轮无新 bug
    send_to_code_review(submitted_code)
    return APPROVED
```

### 3.4 Researcher / Market（不变）

Researcher 和 Market 角色不变，仍负责调研工作。但调研完成后结果直接进入 PM 的中循环，不再需要 Master 中转。

---

## 四、任务流设计（v2）

### 4.1 标准循环流

```python
# === 外循环：Master 下发目标 ===
goal = master_dispatch(
    objective="实现 K8s Pod 概念交互式学习模块",
    acceptance_criteria=[
        "用户能理解 Pod 是什么",
        "有交互式练习环节",
        "测试覆盖率 > 80%"
    ]
)

# === 中循环：PM Orchestrator 接管 ===
subtasks = pm_decompose(goal)
for subtask in subtasks:
    # 派给 Engineer → 触发内循环
    eng_task = kanban_create(
        title=f"实现: {subtask.name}",
        assignee="engineer",
        body=subtask.spec + "\n## 内循环要求\n写完后自己跑测试，全绿才提交。5次迭代上限。"
    )

    # Engineer 内循环完成后，PM 派给 QA → 触发攻击循环
    qa_task = kanban_create(
        title=f"QA攻击: {subtask.name}",
        assignee="qa",
        parent=eng_task,
        body="## 攻击循环要求\n1.跑已有测试 2.自己生成攻击用例 3.3轮无bug才APPROVED"
    )

    # QA 通过后，Code Review
    review_task = kanban_create(
        title=f"Review: {subtask.name}",
        assignee="qa",  # QA 兼 Reviewer
        parent=qa_task,
        body="Code Review checklist"
    )

# 所有子任务完成 → PM 质量门禁 → 通知 Master 验收
pm_quality_gate(all_subtasks) → master_verify(goal)
```

### 4.2 bug 自动回传机制

```python
# QA 发现 bug 时的自动回传（不需要 PM/Master 介入）
def qa_found_bug(bug_detail):
    # 直接创建修复任务给 Engineer，不经过 PM
    kanban_create(
        title=f"修复: {bug_detail.name}",
        assignee="engineer",
        parent=current_qa_task,
        body=f"""
## Bug 详情
{bug_detail.description}

## 复现步骤
{bug_detail.reproduce_steps}

## 预期结果
{bug_detail.expected}

## 实际结果
{bug_detail.actual}

## 内循环要求
修复后自己跑测试全绿，再提交给 QA 重新攻击。
"""
    )
    # Engineer 修复后自动回到 QA 攻击循环
```

### 4.3 升级机制

| 循环层 | 触发条件 | 升级目标 |
|---|---|---|
| 内循环 | Engineer 5 次迭代未通过 | → PM（PM 决定：换方案 or 升级 Master）|
| 中循环 | 同一子任务 3 次 bug 修复失败 | → Master（Master 决定：调整需求 or 放宽标准）|
| 中循环 | PM 质量门禁未通过 | → Master（Master 验收决定）|
| 外循环 | Master 验收不满意 | → 新一轮外循环（Agent 重新执行）|

---

## 五、防发散与可观测性

### 5.1 防发散机制

| 机制 | 说明 |
|---|---|
| 内循环上限 5 次 | Engineer 超过 5 次自动升级，防止无限自修 |
| 攻击循环上限 3 轮 | QA 3 轮无 bug 即放行，防止无限攻击 |
| 升级上限 3 次 | 同一子任务 3 次升级 Master 后强制人工介入 |
| Token 预算 | 每个子任务设置 token 上限，超预算自动停止 |
| 修复范围约束 | Engineer 修复 bug 时只改当前文件，不重构其他代码 |

### 5.2 可观测性

```bash
# 查看循环状态
hermes kanban ls --status running  # 当前正在循环的任务

# 查看内循环日志
hermes kanban tail <engineer_task_id>  # Engineer 内循环过程

# 查看攻击循环日志
hermes kanban tail <qa_task_id>  # QA 攻击用例和结果

# 循环统计
hermes kanban stats --by-profile  # 各 Profile 的平均循环次数
```

### 5.3 循环日志格式

每个循环记录：
```
[Loop] task=xxx type=inner|attack|middle
  iteration=1/5 action=write_code result=FAIL
  iteration=2/5 action=fix_error result=FAIL
  iteration=3/5 action=fix_error result=PASS
  total_iterations=3 duration=45s status=SUCCESS
```

---

## 六、与 v1 的兼容性

| v1 组件 | v2 处理 |
|---|---|
| Kanban 任务板 | 保留，任务流不变 |
| Profile 独立性 | 保留，各 Profile 仍独立运行 |
| Dispatcher 自动接力 | 保留，仍是任务 ready→spawn 的机制 |
| Block/Unblock | **废弃**，改为 QA 直接创建修复任务给 Engineer |
| Goal mode | 保留，用于长任务循环 |
| SOUL.md | **更新**，加入循环行为指令 |

---

## 七、落地步骤

### Step 1: 更新 Engineer SOUL.md（加入内循环指令）
### Step 2: 更新 QA SOUL.md（加入攻击循环指令）
### Step 3: 更新 PM SOUL.md（加入中循环管理指令）
### Step 4: 实测验证一个完整循环
### Step 5: 根据实测调优循环参数（5次/3轮等上限）

---

*文档版本: v2.0 | 作者: cherry | 日期: 2026-07-25*
