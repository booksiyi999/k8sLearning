# K8s Quest 团队 Agent 工作流

> 基于 Hermes Profile + Kanban 的多角色协作架构
> 创建日期：2025-07-05

## 🏗️ 架构概览

```
[Master] ⇄ [cherry:default]  ← 飞书入口 / 决策对话
                │
                │ kanban_create (派发任务)
                ▼
         ┌─────────────────────────────────────┐
         │       Kanban 任务板 (SQLite)         │
         │  任务依赖自动 gating (parents=...)    │
         └────┬──────────┬──────────┬──────────┘
              │          │          │
         ┌────▼───┐ ┌───▼────┐ ┌──▼───┐
         │   PM   │ │Researcher│Engineer│
         │ 决策大脑│ │产品调研  │开发    │
         └────────┘ └────────┘ └──────┘
                                          ┌──────┐
                                          │  QA  │
                                          │测试  │
                                          └──────┘
```

## 👥 4 个 Profile 角色

| Profile | 角色 | 职责 | 工具集 | 输出 |
|---|---|---|---|---|
| `pm` | 决策大脑 | 分解需求、路由任务、综合结果 | kanban-orchestrator | 任务图 |
| `researcher` | 产品调研员 | 技术选型、市场调研、对比分析 | web/arxiv/brave-search | Markdown 调研报告 |
| `engineer` | 开发 Owner | TDD 写代码、commit、技术实现 | terminal/file/code + claude-code | 代码 + 测试 |
| `qa` | 测试 Owner | Code Review、边界测试、回归测试 | terminal/file + test-driven-development | APPROVED / REQUEST_CHANGES |

每个 Profile 拥有：
- 独立 SOUL.md（角色人格）
- 独立 memory（积累职业经验）
- 独立 sessions（任务历史）
- 共享 config（API key / 模型 / 工具集）

## 🔄 任务流设计

### 标准流水线（调研→开发→测试）

```python
# 1. 创建调研任务（独立）
t1 = kanban_create(
    title="调研: [主题]",
    assignee="researcher",
    body="调研目标 + 输出要求 + 文件路径"
)

# 2. 创建开发任务（依赖 T1）
t2 = kanban_create(
    title="实现: [功能]",
    assignee="engineer",
    parent=t1,  # 自动 gating：T1 完成后才 promote
    body="需求 + TDD 流程 + commit 规范"
)

# 3. 创建测试任务（依赖 T2）
t3 = kanban_create(
    title="QA: 审查 [功能]",
    assignee="qa",
    parent=t2,  # 等 engineer 完成后 promote
    body="两阶段 review checklist"
)
```

### 任务状态机

```
ready ──claimed──> running ──completed──> done
                      │
                      └──blocked──> blocked ──unblock──> ready
```

- `ready`: 等待 dispatcher 派发
- `running`: worker profile 正在执行
- `done`: 完成
- `blocked`: 等待人工/上游反馈
- `todo`: 有未完成的 parent，等 parent done 后自动 promote 到 ready

## 🚀 使用示例

### 场景：实现一个新关卡

**Step 1**: cherry 收到 Master 需求 → 直接派发任务到 Kanban

```bash
# 调研
hermes kanban create "调研: [主题]" \
  --assignee researcher \
  --body "..." \
  --created-by cherry

# 开发（依赖调研）
hermes kanban create "实现: [功能]" \
  --assignee engineer \
  --parent <调研任务id> \
  --body "..."

# QA（依赖开发）
hermes kanban create "QA: 审查 [功能]" \
  --assignee qa \
  --parent <开发任务id> \
  --body "..."
```

**Step 2**: Dispatcher 自动接力（gateway 内运行，无需手动启动）

- T1 ready → researcher 自动 spawn → 完成 → done
- T2 todo → 自动 promote 到 ready → engineer spawn → 完成 → done
- T3 todo → 自动 promote → qa spawn → APPROVED / REQUEST_CHANGES

**Step 3**: cherry 跟踪进度

```bash
hermes kanban ls                    # 任务总览
hermes kanban show <task_id>        # 任务详情 + 事件流
hermes kanban tail <task_id>        # 实时日志
```

## 📋 Profile 管理命令

```bash
# 查看
hermes profile list

# 切换默认
hermes profile use engineer

# 单次运行
hermes -p researcher chat -q "调研 K8s 1.30 新特性"

# 编辑 SOUL.md（改人格）
vim ~/.hermes/profiles/researcher/SOUL.md

# 删除
hermes profile delete researcher
```

## 🛠️ Kanban 高级用法

### 并行 fan-out（多调研同时跑）

```python
t1 = kanban_create(title="调研 A", assignee="researcher", ...)
t2 = kanban_create(title="调研 B", assignee="researcher", ...)  # 不 link，并行
t3 = kanban_create(title="综合 A+B", assignee="pm", parents=[t1, t2])
```

### Goal mode（长任务循环）

```bash
hermes kanban create "翻译全部文档" \
  --assignee engineer \
  --goal --goal-max-turns 15
```

### Block 反馈循环

```python
# QA 发现 bug
kanban_block(task_id=t3, reason="OOMKilled 边界用例没覆盖")

# Engineer 修复后
kanban_unblock(task_id=t2)  # 重新触发 engineer
```

## ⚠️ 已知坑

1. **Profile 名必须存在**：dispatcher 静默忽略未知 assignee，任务卡在 ready
2. **scratch workspace 是临时的**：worker 完成后会被清理。要保留产出，在 body 里指定输出到 `~/k8s-quest/docs/` 等持久路径
3. **Unicode 字符**：kanban create 的 body 含某些 Unicode 字符会被 tirith 拦截（如 `→`），用 ASCII 替代
4. **多任务并行上限**：dispatcher 默认每 tick 最多 spawn 3 个 worker
5. **API 配额**：4 个 profile 共享同一套 API key，并发可能触发 rate limit

## 📊 实战记录

### 2025-07-05 Q1.4 关卡（首次完整工作流）

| 阶段 | Profile | 用时 | 产出 |
|---|---|---|---|
| T1 调研 | researcher | 292s | 460 行 Markdown，7 个引用 |
| T2 实现 | engineer | 进行中 | - |
| T3 QA | qa | 等待 | - |

**T1 产出文件**：`~/k8s-quest/docs/research/q1.4-resource-limits.md` (16KB)

## 🔮 后续演进

- **方案 C 升级**：每个 profile 用 tmux 跑独立 hermes 进程，支持 7×24 自治
- **Cron 例会**：每天 9:00 触发 PM 汇总昨日进度
- **Webhook 事件驱动**：GitHub PR 创建自动触发 qa 评审
- **跨项目隔离**：用 `hermes kanban --board <slug>` 创建多个独立看板
