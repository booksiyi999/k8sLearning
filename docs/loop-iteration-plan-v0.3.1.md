# K8s Quest v0.3 Loop Engineering 迭代方案

> PM: 🍒 樱桃 | 日期: 2026-07-15 | 目标: v0.3 原型 → v0.3.1 QA Hardened

---

## 一、当前状态

| 维度 | 状态 |
|---|---|
| 前端 | ✅ 2005行（HTML 416 + JS 512 + CSS 1077） |
| 后端 | ✅ 189 测试全绿 + 88 QA 攻击测试全绿 |
| API | ✅ 6 端点验证通过 |
| 文档 | ✅ README/design.md 已对齐 |
| Docker | ⚠️ 未实测（本机无 Docker） |
| 前端 QA | ❌ 未执行 |

## 二、迭代目标

1. **前端 QA 攻击**：发现并修复游戏化逻辑 bug
2. **端到端验证**：模拟学员完整通关流程
3. **部署验证**：Docker build + setup.sh 一键安装
4. **打磨**：UI/UX + 性能 + 文档终检

## 三、Loop Engineering 架构

```
PM（樱桃）
  ├── 设计方案 -> Master 确认
  ├── 派发任务 -> Engineer
  ├── 监控进度（每30分钟汇报 Master）
  └── 3次失败才升级 Master
       
Engineer（内循环，秒级）
  ├── 写测试 -> 跑测试 -> 失败自修（5次上限）
  ├── 修复 QA 发现的 bug
  └── 全绿才提交 QA

QA（攻击循环，分钟级）
  ├── Phase 1: 跑已有测试（基线验证）
  ├── Phase 2: 生成攻击用例（5维度）
  ├── Phase 3: 发现 bug -> 回传 Engineer
  └── 3轮无 bug 才 APPROVED
```

## 四、任务拆分

### Sprint 1: 前端 QA 攻击循环（预计 2 小时）

**Engineer 内循环任务：**
1. 编写前端逻辑测试文件 `tests/test_frontend_logic.py`
   - XP 计算边界（0/负数/溢出/章节奖励重复）
   - 连击重置逻辑（失败->归零/页面刷新->保持）
   - 徽章解锁条件（10个徽章逐一验证）
   - 关卡解锁逻辑（跳章/逆序/全通）
   - localStorage 序列化/反序列化/损坏恢复
   - 报告生成（空数据/部分数据/全数据）
2. 修复 QA 发现的 bug

**QA 攻击循环任务：**
1. Phase 1: 跑 Engineer 写的测试（基线）
2. Phase 2: 生成攻击用例（5维度）：
   - **类型混淆**：传非标准数据给 API
   - **边界值**：空 YAML / 超长 YAML / 多文档混合
   - **状态篡改**：直接修改 localStorage 跳关
   - **并发竞争**：快速连续提交
   - **异常恢复**：API 500 / 网络断开 / 超时
3. Phase 3: 发现 bug -> REQUEST_CHANGES -> 回传 Engineer
4. 3轮无 bug -> APPROVED

### Sprint 2: 端到端验证（预计 1 小时）

**Engineer 任务：**
1. 编写 E2E 测试 `tests/test_e2e_journey.py`
   - 模拟学员从 Q1.1 到 Q6.4 完整通关
   - 验证 XP 累积（10*24 + 50*6 = 540）
   - 验证称号升级序列（萌新→...→传奇）
   - 验证徽章解锁时序
   - 验证报告生成（25%/50%/75%/100% 完成度）
2. 验证 localStorage 持久化（保存->重载->继续）

### Sprint 3: 部署验证（预计 30 分钟）

**Engineer 任务：**
1. 验证 `setup.sh --dev` 全流程
2. 验证 `setup.sh --docker`（如有 Docker）
3. 验证 Dockerfile 构建产物包含所有前端文件
4. 验证生产模式（workers=2）下静态文件正确服务

### Sprint 4: 打磨与交付（预计 30 分钟）

**PM 任务：**
1. UI/UX 审视（配色/布局/动画流畅度）
2. 性能检查（首屏加载/API响应时间）
3. 文档终检（README/design.md/部署文档）
4. 推送双仓库 + 更新归档

## 五、验收标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | 前端逻辑测试全绿 | pytest tests/test_frontend_logic.py |
| 2 | QA 攻击 3 轮无 bug | QA APPROVED |
| 3 | E2E 通关测试全绿 | pytest tests/test_e2e_journey.py |
| 4 | setup.sh --dev 一键启动 | health check OK |
| 5 | 所有 24 关可完整试炼 | E2E 验证 |
| 6 | 文档与实现一致 | 校验清单 5 项全过 |

## 六、时间线

| 阶段 | 预计耗时 | 预计完成 |
|---|---|---|
| Sprint 1: QA 攻击 | 2h | 02:30 |
| Sprint 2: E2E 验证 | 1h | 03:30 |
| Sprint 3: 部署验证 | 30min | 04:00 |
| Sprint 4: 打磨交付 | 30min | 04:30 |
| 缓冲 | 1.5h | 06:00 |

**Master 验收时间：06:00 前**

## 七、汇报机制

- cron 每 30 分钟自动汇报进度到 Master 飞书私聊
- 汇报内容：当前 Sprint / 已完成 / 剩余 / 阻塞
- 重大 bug 或阻塞立即汇报（不等 30 分钟周期）

---

*由 🍒 樱桃 PM 设计 | 等待 Master 确认后自行开展*
