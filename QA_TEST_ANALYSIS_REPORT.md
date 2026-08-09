# QA 测试分析与攻击测试方案 - 完整报告

> K8s Quest 产品体验报告 - 测试角度分析与攻击测试设计

---

## 一、现有测试结构概览

### 已有测试文件（40个）

| 类别 | 文件 | 说明 |
|------|------|------|
| 前端测试 | `test_playwright_ui.py` | 7个 Playwright 测试（页面加载/章节导航/终端/Playground） |
| QA攻击测试 | `qa_attack_frontend.py` | 5维度前端攻击（类型混淆/边界值/状态篡改/并发/异常恢复） |
| QA攻击测试 | `qa_attack_v04.py` | v0.4端点攻击（lesson/deploy/resources/logs/connectivity） |
| QA攻击测试 | `qa_attack_ch03_ch06.py` | ch03-ch06 check_fn攻击（类型混淆/资源耗尽/注入/绕过/边界） |
| QA攻击测试 | `qa_e2e_repro_r4.py` | E2E边界扫描（回归验证+新发现） |
| QA攻击测试 | `qa_boundary_q1_4.py` | Q1.4边界测试 |
| 章节测试 | `test_ch00.py` ~ `test_ch28_cluster.py` | 各章节单元测试 |
| API测试 | `test_api.py`, `test_api_full_state.py` | API端点测试 |
| 终端测试 | `test_kubectl_terminal.py` | kubectl终端安全测试 |
| 其他 | `test_simulator.py`, `test_cluster.py` 等 | 模拟器/集群测试 |

### 已有测试的覆盖盲区

1. **ch25-ch28 的 check_fn 缺少对抗性测试**：现有 `test_qa_ch23_ch28.py` 只测了空输入/垃圾输入/类型混淆，没有测"结构正确但内容错误"
2. **章节门控逻辑无 Playwright 测试**：只有 `test_ch00_unlocked` 验证 ch00 解锁，没有验证门控传播/绕过
3. **终端安全只测了模拟器模式**：`test_kubectl_terminal.py` 在模拟器模式下运行，无法测试真实集群模式的安全风险
4. **example_yaml 回归测试缺失**：没有测试验证 lesson 的 example_yaml 能通过 check_fn

---

## 二、按问题ID的测试盲区分析与新增测试设计

### P2-1: 3关误判错答为通过

#### 测试盲区分析

**为什么3202个测试没发现：**

1. **`state=None` 的关卡绕过了模拟器验证**：
   - ch25（5关）、ch26（5关）、ch28（5关）的 `check_fn` 返回 `state=None`
   - 这些关卡不经过 `apply_manifest()`，只做 YAML 结构检查或关键词匹配
   - 现有测试（`test_qa_ch23_ch28.py`）的 `TestWrongKind` 提交了一个普通 Pod 给 ch28 关卡，但 ch28 是命令型关卡（接收文本不是 YAML），这个测试的逻辑就不对

2. **ch28 纯关键词匹配过于宽松**：
   ```python
   # _check_281_kubectl_ops 的核心逻辑：
   has_run = "kubectl" in lower and "run" in lower
   has_expose = "expose" in lower
   has_scale = "scale" in lower
   ```
   输入 `"I want to kubectl run expose scale"` 即可通过。`"run"` 出现在 `"running"` 中也会匹配。

3. **ch25 结构检查不验证具体值**：
   - `_check_251_init_container()` 检查 `kind == "Pod"`、有 `initContainers`、有 `name`/`image`/`command`
   - 但不检查 Pod 名称是否为 `init-demo`、镜像是否为 `busybox:1.36`、命令内容是否正确
   - 提交名称完全错误、镜像用 `ubuntu`、命令为 `["sleep", "999999"]` 的 Pod 也能通过

4. **现有QA攻击测试的覆盖范围**：
   - `qa_attack_frontend.py`：只用了 Q1.1/Q1.2 等早期关卡
   - `qa_attack_ch03_ch06.py`：只覆盖 ch03-ch06
   - ch25+ 完全没有对抗性测试

#### 确认的3个误判关卡

| 关卡 | check_fn | 误判原因 | 攻击向量 |
|------|----------|----------|----------|
| **Q28.1** | `_check_281_kubectl_ops` | 纯关键词匹配，不验证命令语法 | `"kubectl run expose scale"` 任意文本 |
| **Q25.1** | `_check_251_init_container` | 只检查结构存在性，不检查 Pod名/镜像/命令内容 | Pod名=`totally-wrong-name`, image=`ubuntu:latest` |
| **Q25.2** | `_check_252_sidecar` | 只检查2+容器+共享卷，不检查容器名/镜像/命令 | 容器名=`main`/`helper`, image=`alpine` |

#### 新增测试用例

**文件：`backend/tests/qa_attack_misjudge.py`**

| 测试类 | 测试函数 | 测试逻辑 |
|--------|----------|----------|
| `TestQ28KeywordBypass` | `test_english_sentence_with_keywords` | 英文句子含关键词应被拒绝 |
| | `test_keywords_in_wrong_order` | 关键词乱序应被拒绝 |
| | `test_keywords_without_actual_commands` | 注释中的关键词应被拒绝 |
| | `test_partial_command_missing_image` | 缺少 --image 应被拒绝 |
| | `test_completely_wrong_commands` | 无参数命令组合应被拒绝 |
| `TestQ251InitContainerMisjudge` | `test_wrong_pod_name_accepted_bug` | Pod名错误应被拒绝 |
| | `test_wrong_image_accepted_bug` | 镜像错误应被拒绝 |
| | `test_missing_volume_share_accepted_bug` | 缺少共享卷应被拒绝 |
| | `test_garbage_init_command_accepted_bug` | 命令内容错误应被拒绝 |
| `TestQ252SidecarMisjudge` | `test_wrong_pod_name_accepted_bug` | Pod名错误应被拒绝 |
| | `test_wrong_container_names_accepted_bug` | 容器名错误应被拒绝 |
| | `test_wrong_images_accepted_bug` | 镜像错误应被拒绝 |
| | `test_missing_sidecar_command_accepted_bug` | 缺少 command 应被拒绝 |
| `TestQ28AllLevelsKeywordBypass` | `test_keyword_bypass[parametrized]` | Q28.2-Q28.5 所有关键词拼凑应被拒绝 |

**测试类型：后端API攻击测试**（通过 TestClient 调用 `/api/check`）

---

### P0-1: 章节门控把零基础新生锁在 ch00

#### 测试盲区分析

**为什么3202个测试没发现：**

1. **章节门控是纯前端逻辑**：`isChapterUnlocked()` 在 `frontend/app.js` 第733行，后端 API 无关
2. **现有 Playwright 测试只验证了 ch00 解锁**：`test_ch00_unlocked` 只检查第一个章节卡片有 `unlocked` class
3. **没有测试门控传播**：没有测试"完成 ch00 所有关卡后 ch01 是否解锁"
4. **没有测试门控严格性**：没有验证新用户是否被锁在 ch00（`unlocked:1, locked:28`）
5. **没有测试门控绕过**：没有测试篡改 localStorage 是否能绕过门控

**门控逻辑代码**：
```javascript
isChapterUnlocked(chId) {
    const chNum = parseInt(chId.replace('ch', ''));
    if (isNaN(chNum) || chNum <= 0) return true;  // ch00 始终解锁
    const prevNum = chNum - 1;
    const prevLevels = this.levels.filter(l => l.id.startsWith(`Q${prevNum}.`));
    return prevLevels.length > 0 && prevLevels.every(l => this.progress.completed_levels.includes(l.id));
}
```
- ch01 需要 ch00 所有关卡完成
- ch00 有3关（Q0.1/Q0.2/Q0.3），是架构概念关
- 新用户 `completed_levels` 为空 → ch01-ch28 全部锁定

#### 新增测试用例

**文件：`backend/tests/test_playwright_gating.py`**

| 测试类 | 测试函数 | 测试逻辑 |
|--------|----------|----------|
| `TestFreshUserChapterGating` | `test_fresh_user_only_ch00_unlocked` | 新用户只有 ch00 解锁 |
| | `test_ch01_locked_for_fresh_user` | 新用户 ch01 被锁定（BUG确认） |
| | `test_locked_chapter_cannot_expand` | 锁定章节不能展开 |
| | `test_locked_level_shows_lock_icon` | 锁定关卡显示锁图标 |
| `TestChapterUnlockProgression` | `test_complete_ch00_unlocks_ch01` | 完成 ch00 全部关卡后 ch01 解锁 |
| | `test_partial_ch00_does_not_unlock_ch01` | 只完成 ch00 部分关卡 ch01 不解锁 |
| `TestGateBypassAttack` | `test_progress_tampering_unlock_all` | 篡改 localStorage 解锁所有章节 |
| | `test_negative_progress_does_not_break` | 异常进度数据不导致前端崩溃 |

**测试类型：Playwright 前端测试**

---

### P0-2: 终端 Tab 是真实 kubectl 代理（安全风险）

#### 测试盲区分析

**为什么3202个测试没发现：**

1. **`apply` 不在 DANGEROUS 列表中**：
   ```python
   ALLOWED_SUBCOMMANDS = {"get", "describe", "logs", "apply", "delete", "create", ...}
   DANGEROUS_SUBCOMMANDS = {"delete", "drain", "cordon", "uncordon", "taint", "scale", "rollout", "edit", "exec"}
   ```
   `kubectl apply -f <destructive.yaml>` 可以直接执行无需确认。`create`、`patch` 同样不在 DANGEROUS 中。

2. **现有终端测试在模拟器模式下运行**：`test_kubectl_terminal.py` 的所有测试都在模拟器模式下执行，所有命令返回"集群模式未启用"，无法测试真实执行路径

3. **ch21 破坏性操作无风险提示**：ch21 的 lesson 内容包含 `drain`、`cordon` 等破坏性操作，但没有测试验证 lesson 是否包含风险警告

4. **命令注入防护有遗漏**：当前禁止了 `;|&\`$()<>\n\r` 但没有禁止 `{}`（YAML花括号）和全角字符

5. **`FORBIDDEN_SUBCOMMANDS` 过少**：只有 `destroy`、`reset`、`init`，没有禁止 `replace`、`replace --force`、`rollout undo` 等

#### 新增测试用例

**文件：`backend/tests/qa_attack_terminal_security.py`**

| 测试类 | 测试函数 | 测试逻辑 |
|--------|----------|----------|
| `TestWhitelistBoundary` | `test_apply_not_in_dangerous` | apply 不在 DANGEROUS（安全风险确认） |
| | `test_create_not_in_dangerous` | create 不在 DANGEROUS |
| | `test_patch_not_in_dangerous` | patch 不在 DANGEROUS |
| | `test_forbidden_subcommands` | FORBIDDEN 列表验证 |
| `TestCommandInjectionAttack` | `test_shell_metacharacter_blocked[parametrized]` | 11种 shell 注入变体被阻止 |
| | `test_command_with_quotes` | jsonpath 含 {} 的处理 |
| | `test_unicode_bypass_attempt` | 全角字符绕过尝试 |
| | `test_null_byte_injection` | Null 字节注入 |
| | `test_chained_kubectl_commands` | 链式 kubectl 命令 |
| `TestDangerousCommandConfirm` | `test_delete_needs_confirm_in_simulator` | delete 在模拟器模式的行为 |
| | `test_force_bypasses_confirm` | force=true 绕过确认 |
| | `test_apply_no_confirm_needed` | apply 不需要确认（安全风险） |
| `TestCh21DestructiveOps` | `test_drain_in_dangerous` | drain 在 DANGEROUS 中 |
| | `test_ch21_lesson_contains_warning` | ch21 lesson 含风险提示 |
| | `test_ch21_check_fn_rejects_empty` | ch21 拒绝空输入 |
| | `test_ch21_check_fn_rejects_garbage` | ch21 拒绝垃圾输入 |
| `TestKubectlWhitelistEndpoint` | `test_whitelist_returns_allowed_and_dangerous` | 白名单端点结构 |
| | `test_apply_not_flagged_dangerous_in_whitelist` | apply 不在 dangerous 返回中 |
| `TestKubectlRequestValidation` | `test_missing_command_field` | 缺少 command 字段 |
| | `test_very_long_command` | 超长命令处理 |
| | `test_non_string_command` | 非字符串 command |
| | `test_null_command` | null command |

**测试类型：后端API攻击测试 + 安全配置验证**

---

### P1-1: ch28 CKA 关 example 全失败（0/5）

#### 测试盲区分析

**为什么3202个测试没发现：**

1. **没有 example_yaml 回归测试**：没有任何测试验证 `level.lesson.example_yaml` 能通过 `level.check_fn`
2. **ch28 check_fn 是关键词匹配型**：接收文本输入（kubectl命令序列），但 lesson 的 example_yaml 是多行命令文本
3. **ch28 的 example_yaml 含注释行**：example 中有 `# 步骤 1: 创建 Deployment` 等注释，但 check_fn 的关键词检测是全文本搜索，注释中的关键词会被匹配

#### 根因分析

查看 `_check_281_kubectl_ops`：
```python
lower = text.lower()
has_run = "kubectl" in lower and "run" in lower
has_expose = "expose" in lower
has_scale = "scale" in lower
```

example_yaml 中包含：
```bash
# 步骤 1: 创建 Deployment
kubectl run nginx-app --image=nginx:1.25 --port=80
# 步骤 2: 暴露 Service
kubectl expose deployment nginx-app --port=80 --target-port=80
# 步骤 3: 扩容到 3 个副本
kubectl scale deployment nginx-app --replicas=3
```

这个 example 应该能通过（所有关键词都在）。如果 example 全失败，可能是：
- check_fn 对 example_yaml 的处理有 bug（比如注释行干扰）
- 或者 check_fn 的参数名是 `user_input` 而非 `user_yaml`，可能有类型转换问题

#### 新增测试用例

**文件：`backend/tests/qa_attack_ch17_ch28_concepts.py`**

| 测试类 | 测试函数 | 测试逻辑 |
|--------|----------|----------|
| `TestCh28ExamplePasses` | `test_example_yaml_passes_check[parametrized Q28.1-Q28.5]` | 每关 example_yaml 必须通过 check_fn |
| `TestCh28KeywordMatchingWeakness` | `test_q281_keyword_order_irrelevant` | 关键词顺序不影响通过 |
| | `test_q281_keywords_in_comments` | 注释中的关键词不应通过 |
| | `test_q282_keywords_without_pod_name` | 缺少 pod 名称应被拒绝 |
| | `test_q281_completely_wrong_commands` | 无参数命令组合应被拒绝 |

**测试类型：后端单元测试**

---

### P1-2: ch17 概念关 example 不过（3/10）

#### 测试盲区分析

**为什么3202个测试没发现：**

1. **没有 example_yaml 回归测试**（同 P1-1）
2. **ch17 概念关校验比 example 严格**：
   - **Q17.6 (Reconcile)**: example_yaml 是 **Python 伪代码**（`def Reconcile(ctx, req):...`），但 check_fn 期望 **Blog CR YAML**（检查 `status.conditions` + `status.observedGeneration`）。YAML 解析 Python 代码不会产生有效的 CR 文档 → **必定失败**
   - Q17.8 (Finalizer): example_yaml 是有效的 YAML（含 `finalizers: [blog.example.com/cleanup]`），check_fn 检查 finalizer 含 `/` → 可能通过，需验证
   - Q17.10 (Best Practices): example_yaml 包含 5 个必需字段 → 可能通过，需验证

3. **现有 ch17 测试只测了 Q17.1-Q17.2**：`test_qa_ch17_ch18.py` 主要测试 Q17.1（CRD创建）和 Q17.2（Schema验证），没有测试 Q17.6/Q17.8/Q17.10

#### 新增测试用例

**文件：`backend/tests/qa_attack_ch17_ch28_concepts.py`**

| 测试类 | 测试函数 | 测试逻辑 |
|--------|----------|----------|
| `TestCh17ExamplePasses` | `test_example_yaml_passes_check[parametrized Q17.1-Q17.10]` | 每关 example_yaml 必须通过 check_fn |
| `TestCh17ExamplePasses` | `test_concept_level_example_detailed[parametrized Q17.6/Q17.8/Q17.10]` | 重点验证3个概念关 |
| `TestCh17ConceptDepth` | `test_q176_rejects_wrong_condition_status` | status="Maybe" 应被拒绝 |
| | `test_q176_rejects_missing_observed_generation` | 缺少 observedGeneration 应被拒绝 |
| | `test_q178_rejects_finalizer_without_slash` | finalizer 不含 / 应被拒绝 |
| | `test_q178_rejects_empty_finalizer` | 空 finalizer 应被拒绝 |
| | `test_q1710_rejects_partial_fields` | 缺少部分字段应被拒绝 |
| | `test_q1710_accepts_complete_yaml` | 完整 YAML 应通过 |
| `TestAllLevelsExamplePasses` | `test_chapter_examples_pass[parametrized ch0-ch28]` | 全局回归：所有150关 example 通过 |

**测试类型：后端单元测试**

---

### P2-2: ch25/ch07/ch26 讲解偏薄

#### 测试盲区分析

这个问题是内容质量问题，不是代码缺陷。但可以通过测试度量内容长度。

#### 新增测试建议

| 测试类 | 测试函数 | 测试逻辑 |
|--------|----------|----------|
| `TestLessonContentDepth` | `test_ch25_lesson_length` | ch25 每关 lesson.concept >= 1000字 |
| | `test_ch07_lesson_length` | ch07 每关 lesson.concept >= 1000字 |
| | `test_ch26_lesson_length` | ch26 每关 lesson.concept >= 1000字 |
| | `test_all_chapters_minimum_depth` | 所有章节 lesson.concept >= 500字 |

**测试类型：后端单元测试（内容度量）**

---

## 三、测试优先级排序

### 🔴 P0 - 立即执行

1. **P2-1 误判攻击测试** (`qa_attack_misjudge.py`)
   - 风险：用户提交错误答案被判通过，损害学习效果
   - 估时：已创建15个测试用例
   - 修复方向：ch28 check_fn 增加命令语法验证；ch25 check_fn 增加 Pod名/镜像/命令内容验证

2. **P0-1 章节门控 Playwright 测试** (`test_playwright_gating.py`)
   - 风险：新用户被锁在 ch00 无法学习，直接流失
   - 估时：已创建8个测试用例
   - 修复方向：ch00 完成后自动解锁 ch01，或降低门控要求（完成50%即可解锁）

### 🟠 P1 - 本周执行

3. **P0-2 终端安全攻击测试** (`qa_attack_terminal_security.py`)
   - 风险：`apply`/`create`/`patch` 不需确认即可执行破坏性操作
   - 估时：已创建25个测试用例
   - 修复方向：将 `apply`/`create`/`patch` 加入 DANGEROUS_SUBCOMMANDS

4. **P1-1/P1-2 example回归测试** (`qa_attack_ch17_ch28_concepts.py`)
   - 风险：用户按教程操作但无法通过，损害信任
   - 估时：已创建20+个测试用例
   - 修复方向：修复 check_fn 或修复 example_yaml 使两者一致

### 🟡 P2 - 下个迭代

5. **P2-2 内容深度度量测试**
   - 风险：讲解偏薄影响学习体验
   - 估时：4个测试用例
   - 修复方向：补充 ch25/ch07/ch26 的 lesson.concept 内容

---

## 四、新增测试文件清单

| 文件路径 | 测试用例数 | 覆盖问题 | 测试类型 |
|----------|-----------|----------|----------|
| `backend/tests/qa_attack_misjudge.py` | 15 | P2-1 | 后端API攻击 |
| `backend/tests/test_playwright_gating.py` | 8 | P0-1 | Playwright前端 |
| `backend/tests/qa_attack_terminal_security.py` | 25 | P0-2 | 后端API攻击+安全配置 |
| `backend/tests/qa_attack_ch17_ch28_concepts.py` | 20+ | P1-1, P1-2 | 后端单元测试 |
| **合计** | **68+** | **5个问题** | **3种测试类型** |

---

## 五、关键发现总结

### 1. 测试盲区根因

现有3202个测试的主要盲区：

1. **"正例测试"偏多，"反例测试"不足**：大量测试验证"正确答案能通过"，但缺少"看起来正确但实质错误"的对抗性测试
2. **`state=None` 关卡无模拟器验证**：15个关卡（ch25×5 + ch26×5 + ch28×5）不经过模拟器，只做结构检查
3. **example_yaml 无回归测试**：没有任何测试验证教程示例能通过校验
4. **前端门控逻辑无自动化测试**：章节门控是纯前端逻辑，现有7个 Playwright 测试没有覆盖
5. **终端安全只在模拟器模式测试**：无法验证真实集群模式下的安全风险

### 2. 最严重的安全发现

**`apply` 不在 DANGEROUS_SUBCOMMANDS 中**：用户可以在终端中直接执行 `kubectl apply -f` 提交任意 YAML，包括删除命名空间、创建特权 Pod 等破坏性操作，无需任何确认。这是 P0-2 报告中"ch21 含破坏性操作无风险提示"的根因。

### 3. 修复建议优先级

1. **立即修复**：ch25/ch28 的 check_fn 增加内容验证（Pod名/镜像/命令语法）
2. **立即修复**：章节门控改为"完成 ch00 50% 即解锁 ch01"或"ch00 不作为前置条件"
3. **本周修复**：将 `apply`/`create`/`patch` 加入 DANGEROUS_SUBCOMMANDS
4. **本周修复**：修复 ch17/ch28 的 example_yaml 使其通过 check_fn
5. **下个迭代**：补充 ch25/ch07/ch26 的 lesson 内容
