# Loop Engineering 迭代计划 v3.0 - 产品体验报告修复

> 基于 Claude Code 产品体验报告 (78/100) 的系统性修复
> 日期: 2026-08-09
> PM: Cherry (自主决策，无需 Master 介入)

## 多角色分析结论

### Designer 分析
- P0-1: 推荐"自由浏览+练习锁定"+前2章默认解锁 (复杂度:低)
- P0-2: 风险横幅(常驻)+Modal确认+讲解层⚠️标注 (复杂度:中)
- P1-1: 模拟器模式降级为概念题 (复杂度:中)
- P1-2: 短期文本+关键词匹配，长期关卡类型标签 (复杂度:低/中)

### Developer 分析
- P0-1: `isChapterUnlocked` L733-738 `every`→渐进解锁，仅改1文件 (1-2h)
- P0-2: 后端加 READONLY_SUBCOMMANDS + 扩展 DANGEROUS + 前端只读切换 + ch21风险提示 (4-6h)
- P1-1: ch28 添加命令解析器 + 重写5个check_fn + verify_ch28容错 (6-8h)
- P1-2: Q17.6 example是Python伪代码非YAML，需替换 (2-3h)
- P2-1: Q25.1/Q25.3/Q25.4 check_fn 过宽，需加 volumeMounts/共享卷校验 (3-4h)
- P2-2: ch25/ch07/ch26 Lesson.concept 扩充 (4-6h)

### Tester 分析
- 确认3关误判: Q28.1(关键词匹配)、Q25.1(结构检查无内容验证)、Q25.2(同上)
- 创建4个测试文件共127个攻击测试用例
- 测试盲区根因: 现有测试只验证"正确答案通过"和"垃圾输入拒绝"，缺少"结构正确但内容错误"的对抗性测试

## PM 决策

| 问题 | 优先级 | PM 决策 | Sprint | 工作量 |
|------|--------|---------|--------|--------|
| P0-1 章节门控 | P0 | 渐进式解锁(完成1关即解锁下章)+默认解锁ch00-ch01 | G-1 | 1h |
| P0-2 终端安全 | P0 | 后端扩展DANGEROUS+只读模式; 前端只读切换+风险横幅; ch21风险提示 | G-2 | 4h |
| P1-1 ch28 CKA | P1 | 命令解析器+重写check_fn+标注集群实操 | G-3 | 4h |
| P1-2 ch17概念关 | P1 | Q17.6 example从伪代码改YAML + Q17.8/Q17.10验证修复 | G-1 | 1h |
| P2-1 误判 | P2 | 修复Q28.1/Q25.1/Q25.2 check_fn增加内容校验 | G-1 | 2h |
| P2-2 内容偏薄 | P2 | 扩充ch25/ch07/ch26讲解 | G-3 | 3h |

## Sprint 计划

### Sprint G-1: Quick Wins (P0-1 + P1-2 + P2-1) ~4h
1. P0-1: 修改 isChapterUnlocked 渐进解锁 + 默认解锁 ch00-ch01
2. P1-2: 修复 Q17.6/Q17.8/Q17.10 example_yaml
3. P2-1: 修复 Q28.1/Q25.1/Q25.2 check_fn
4. 运行测试验证

### Sprint G-2: Security Hardening (P0-2) ~4h
1. 后端: 扩展 DANGEROUS_SUBCOMMANDS 含 apply/create/patch
2. 后端: 新增 READONLY_SUBCOMMANDS + readonly 参数
3. 前端: 终端只读模式切换 + 风险横幅
4. ch21: 教学内容加风险提示
5. 运行测试验证

### Sprint G-3: Content + ch28 (P1-1 + P2-2) ~7h
1. P1-1: ch28 命令解析器 + 5个check_fn重写 + 集群实操标注
2. P2-2: 扩充 ch25/ch07/ch26 讲解
3. 运行测试验证

### Sprint G-4: QA Loop + Polish ~2h
1. 运行全量测试(含新增127个攻击测试)
2. 修复QA发现的bug
3. 更新README/docs
4. 提交推送

## 质量目标
- 当前评分: 78/100
- 目标评分: 85+
- 验收标准: 全量测试绿 + QA攻击测试绿 + 产品报告问题全部修复

## 升级条件
- 无需升级Master的决策点(PM可自主判断所有6个问题)
