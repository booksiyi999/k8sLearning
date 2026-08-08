# K8s Quest v2.0 迭代计划

> 基于 Claude Code review agent 评判报告（68/100）+ Master 新需求（交互式 kubectl 终端）
> 日期：2026-08-08
> 当前状态：28章 / 140关 / 2850测试全绿

## 评审核心发现

| 严重度 | 问题 | 影响 |
|---|---|---|
| P0 | 缺 Ch0 架构总览 | 校招生无全景图 |
| P0 | Operator 章偏浅(38分) | 学完不会开发 Operator |
| P0 | 缺 Pod 探针 | 核心概念遗漏 |
| P1 | 模拟器假阳性 | 高阶章"通过"≠"掌握" |
| P1 | 章节顺序倒置 | 依赖前置知识缺失 |
| P1 | ch21 偏薄 | CKA 必考内容不够 |
| P2 | 代码架构 | 扩展性差 |

## Sprint 分解

### Sprint 1: 交互式 Kubectl 终端 ⭐(Master 新需求)
- **后端**: `POST /api/kubectl` 执行任意 kubectl 命令
- **安全**: 子命令白名单 + namespace 隔离 + 危险命令确认
- **前端**: 终端组件（命令历史 + 输出高亮 + 自动补全）
- **集成**: 实战章节（每章第5关）增加"终端"Tab
- **预计**: 1-2h

### Sprint 2: P0 - Ch0 架构总览 + Pod 探针
- 新增 Ch00: 3关（架构总览/Reconcile循环/kubectl与API交互）
- Ch01 新增 2关（Pod 探针：liveness/readiness/startup）
- 总关卡: 140 -> 145
- **预计**: 2h（并行 agent）

### Sprint 3: P1 - 模拟器升级
- RBAC: `simulate_rbac_check(state, sa, verb, resource) -> bool`
- NetworkPolicy: `simulate_traffic(state, src, dst, port) -> bool`
- 重写 ch22.3/22.4（真实故障场景）
- 重写 ch27.1（istio 结构检查）
- **预计**: 2h（并行 agent）

### Sprint 4: P0 - Operator 章重做
- ch17 扩展 5->10 关
- Q17.1-5: 增强模拟器（CRD Schema/Status子资源）
- Q17.6-10: kubebuilder 实战（Reconcile/Finalizer/Webhook）
- **预计**: 3h（并行 agent）

### Sprint 5: P1 - ch21 增强 + ch28 CKA 重做
- ch21: etcd备份恢复原理 + 证书续期 + kubeadm upgrade
- ch28: 真实 kubectl 操作挑战（非纯YAML结构校验）
- **预计**: 2h（并行 agent）

### Sprint 6: P2 - 代码架构改进
- `@register_level` 装饰器（消除28个import）
- `check_fn(user_yaml, context: CheckContext)` 扩展签名
- `/api/check` 返回全量资源类型
- **预计**: 1h

## 验收标准

- [ ] kubectl 终端可执行 get/describe/logs/apply/delete 等命令
- [ ] 危险命令有确认提示
- [ ] Ch00 3关 + Pod 探针 2关，测试全绿
- [ ] RBAC/NetworkPolicy 模拟器行为验证
- [ ] Operator 章扩展到 10 关
- [ ] 全部测试通过（2850 -> 3000+）
- [ ] README 与实现一致

## 执行方式

- Loop Engineering 三层循环
- PM(樱桃) 设计 -> Solo Inner Loop / delegate_task 并行
- 每完成一个 Sprint 立即推送 + 进入下一个
- QA 攻击测试跟随每个 Sprint
