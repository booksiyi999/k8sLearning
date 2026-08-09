"""Chapter 7: Job / CronJob（批量任务）（5 关）

Q7.1 创建第一个 Job
Q7.2 Job 并行执行
Q7.3 创建 CronJob
Q7.4 CronJob 并发策略
Q7.5 集群实战 - 部署 Job 计算
"""
from app.validator import Level, CheckResult, Lesson
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError


# ==================== Q7.1 创建第一个 Job ====================

def _check_71_create_job(user_yaml: str) -> CheckResult:
    """Q7.1 创建一个计算 π 的 Job"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.jobs:
        return CheckResult(
            ok=False,
            error="没有创建任何 Job",
            hints=["你需要 apply 一个 kind: Job 的 YAML"],
        )

    job_name = next(iter(state.jobs))
    job = state.jobs[job_name]
    spec = job.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Job 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="Job 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="Job 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Job 缺少 spec.template.spec.containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    if not c.get("image"):
        return CheckResult(ok=False, error="容器缺少 image", hints=["spec.template.spec.containers[0].image 必须指定"])

    if not c.get("command"):
        return CheckResult(
            ok=False,
            error="容器缺少 command",
            hints=["Job 容器通常需要指定 command 来执行任务"],
        )

    # 验证 Job 创建了对应的 Pod
    pod_name = f"{job_name}-pod"
    if pod_name not in state.pods:
        return CheckResult(
            ok=False,
            error=f"Job '{job_name}' 没有创建对应的 Pod",
            hints=["模拟器应为每个 Job 创建一个执行 Pod"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["干得漂亮！Job 会运行到完成然后退出，不像 Deployment 那样持续运行 🧮"],
    )


LEVEL_Q7_1 = Level(
    id="Q7.1",
    chapter="ch07",
    title="创建第一个 Job",
    description="""
# 创建第一个 Job 🧮

**Job** 是 K8s 中用于运行**一次性批量任务**的工作负载。与 Deployment 不同，Job 中的 Pod 执行完任务后会正常退出（exit code 0），而不是持续运行。

## 任务

创建一个计算 π 的 Job：
- `kind: Job`
- 容器镜像使用 `perl:5.38`
- command 执行计算 π 的命令

## 提示

Job 的结构与 Deployment 类似，但不需要 selector：
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.38
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```
""",
    starter_yaml="""\
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  template:
    spec:
      containers:
      - name: pi
        # image 和 command 在这里补全
      restartPolicy: Never
""",
    check_fn=_check_71_create_job,
    lesson=Lesson(
        concept="""\
## 什么是 Job？

**Job** 是 Kubernetes 中负责运行**一次性任务（batch job）**的工作负载控制器。与 Deployment 持续维持运行状态不同，Job 创建的 Pod 在成功完成任务后会正常退出，Job 会跟踪 Pod 的完成状态。

### Job 的核心行为

1. **创建 Pod 执行任务**：Job 根据 `spec.template` 创建 Pod
2. **跟踪完成状态**：Pod 成功退出（exit code 0）后，Job 标记为完成
3. **失败重试**：Pod 失败时，根据 `spec.backoffLimit`（默认 6）决定重试次数
4. **执行完毕退出**：与 Deployment 的 Pod 不同，Job 的 Pod 完成后不会重启

### restartPolicy

Job 的 Pod 模板中 `restartPolicy` 只能是 `Never` 或 `OnFailure`，**不能**是 `Always`（那是 Deployment 的行为）。

- `Never`：Pod 失败后直接创建新 Pod 重试
- `OnFailure`：Pod 失败后在同一 Pod 内重启容器

### 失败重试策略：backoffLimit

`spec.backoffLimit` 控制 Job 失败后的重试次数（默认 6）。每次重试的间隔按指数增长（10s, 20s, 40s, ...），避免频繁重试压垮依赖服务：

```yaml
spec:
  backoffLimit: 4          # 最多重试 4 次
  template:
    spec:
      containers:
      - name: task
        image: busybox:1.36
        command: ["sh", "-c", "exit 1"]   # 模拟失败
      restartPolicy: Never
```

重试行为与 restartPolicy 的关系：

| restartPolicy | Pod 失败行为 | backoffLimit 作用 |
|---------------|-------------|-------------------|
| `Never` | 删除旧 Pod，创建新 Pod | 限制创建新 Pod 的次数 |
| `OnFailure` | 同一 Pod 内重启容器 | 限制重启次数 |

超过 backoffLimit 后，Job 标记为 Failed，不再重试。

### 超时控制：activeDeadlineSeconds

`spec.activeDeadlineSeconds` 设置 Job 的最长运行时间。超时后 Job 被强制终止并标记为 Failed，即使 Pod 还在运行：

```yaml
spec:
  activeDeadlineSeconds: 300   # 最长运行 5 分钟
  backoffLimit: 3
  template:
    spec:
      containers:
      - name: task
        image: myapp/batch:latest
      restartPolicy: Never
```

> **注意**：activeDeadlineSeconds 优先于 backoffLimit。如果 Job 运行超时，即使还有重试次数也会被终止。这在防止 Job 卡死（如死锁、网络挂起）时非常重要。

### Job 清理策略：ttlSecondsAfterFinished

Job 完成后默认保留 Pod 和 Job 对象（方便查看日志和状态）。但在生产环境中，大量已完成 Job 会占用 etcd 存储。`spec.ttlSecondsAfterFinished` 可以自动清理：

```yaml
spec:
  ttlSecondsAfterFinished: 100   # 完成 100 秒后自动删除 Job 和关联 Pod
  template:
    spec:
      containers:
      - name: task
        image: busybox:1.36
        command: ["echo", "done"]
      restartPolicy: Never
```

| ttlSecondsAfterFinished | 行为 |
|--------------------------|------|
| 未设置（默认） | Job 和 Pod 永久保留，需手动删除 |
| `0` | 完成后立即删除 |
| `100` | 完成 100 秒后自动删除 |

TTL Controller 会在 Job 完成（成功或失败）后等待指定秒数，然后自动删除 Job 及其关联的 Pod。

### 典型使用场景

- 批量数据处理（ETL）
- 数据库迁移
- 机器学习模型训练
- 一次性配置脚本
- 定时备份任务（配合 CronJob）
""",
        key_fields=[
            {"name": "spec.template", "description": "Pod 模板，定义 Job 创建的 Pod 规格", "required": True, "example": "template: { spec: { containers: [...] } }"},
            {"name": "spec.template.spec.containers", "description": "容器列表，至少一个", "required": True, "example": "[{name: pi, image: perl:5.38}]"},
            {"name": "spec.template.spec.containers[].command", "description": "容器启动命令，执行具体任务", "required": True, "example": "[perl, -Mbignum=bpi, -wle, print bpi(2000)]"},
            {"name": "spec.template.spec.restartPolicy", "description": "重启策略: Never 或 OnFailure", "required": True, "example": "Never"},
            {"name": "spec.backoffLimit", "description": "失败重试次数上限，默认 6", "required": False, "example": "4"},
        ],
        diagram="""\
┌─────────────── Job (pi) ──────────────────────┐
│  spec:                                        │
│    template:                                  │
│      spec:                                    │
│        containers:                            │
│        - name: pi                             │
│          image: perl:5.38                     │
│          command: [perl, -Mbignum=bpi, ...]   │
│        restartPolicy: Never                   │
│    backoffLimit: 6  (默认)                    │
└───────────────────┬───────────────────────────┘
                    │
                    ▼ 创建 Pod
            ┌───────────────┐
            │  Pod (pi-pod)  │
            │  执行计算 π     │
            │  exit 0  ✓     │
            └───────────────┘
                    │
                    ▼ Pod 完成
            Job 状态: Complete
""",
        example_yaml="""\
apiVersion: batch/v1       # Job API 版本
kind: Job                  # 资源类型: Job
metadata:                  # 元数据
  name: pi                 # Job 名称
spec:                      # 规格定义
  template:                # Pod 模板
    spec:                  # Pod 规格
      containers:          # 容器列表
      - name: pi           # 容器名
        image: perl:5.38   # Perl 镜像
        command:           # 启动命令
        - perl
        - "-Mbignum=bpi"
        - "-wle"
        - "print bpi(2000)"
      restartPolicy: Never # 失败不重启，创建新 Pod
  backoffLimit: 4          # 最多重试 4 次
""",
        common_errors=[
            "restartPolicy 写成了 Always（Job 只支持 Never 和 OnFailure）",
            "忘记写 command，容器启动后立即退出导致 Job 失败",
            "把 spec.template 写成了 spec.containers（Job 和 Deployment 一样使用 template）",
            "apiVersion 写成了 v1 而非 batch/v1",
        ],
        tips=[
            "用 kubectl get jobs 查看 Job 完成状态（COMPLETIONS 列）",
            "用 kubectl logs job/pi 查看 Job Pod 的输出",
            "Job 的 Pod 完成后默认不会被删除，方便查看日志",
        ],
    ),
)


# ==================== Q7.2 Job 并行执行 ====================

def _check_72_parallel_job(user_yaml: str) -> CheckResult:
    """Q7.2 创建一个 parallelism=3 的 Job"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.jobs:
        return CheckResult(
            ok=False,
            error="没有创建任何 Job",
            hints=["你需要 apply 一个 kind: Job 的 YAML"],
        )

    job_name = next(iter(state.jobs))
    job = state.jobs[job_name]
    spec = job.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Job 缺少 spec", hints=[])

    parallelism = spec.get("parallelism")
    if parallelism is None:
        return CheckResult(
            ok=False,
            error="Job 缺少 spec.parallelism",
            hints=["添加 spec.parallelism: 3"],
        )

    if parallelism != 3:
        return CheckResult(
            ok=False,
            error=f"spec.parallelism 应为 3，实际为 {parallelism}",
            hints=["设置 spec.parallelism: 3"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["并行 Job 可以同时运行多个 Pod 加速任务执行 ⚡"],
    )


LEVEL_Q7_2 = Level(
    id="Q7.2",
    chapter="ch07",
    title="Job 并行执行",
    description="""
# Job 并行执行 ⚡

当批量任务可以拆分成多个子任务并行执行时，可以用 `parallelism` 控制**同时运行**的 Pod 数量。

## 任务

创建一个 parallelism=3 的 Job：
- `kind: Job`
- `spec.parallelism: 3`
- 容器使用 `busybox:1.36`，执行简单命令
- `spec.completions: 6`（总共完成 6 个任务）

## 提示

```yaml
spec:
  parallelism: 3    # 同时运行 3 个 Pod
  completions: 6    # 总共完成 6 个任务
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.36
        command: ["echo", "hello"]
      restartPolicy: Never
```
""",
    starter_yaml="""\
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  # parallelism: 3
  # completions: 6
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.36
        command: ["echo", "hello"]
      restartPolicy: Never
""",
    check_fn=_check_72_parallel_job,
    lesson=Lesson(
        concept="""\
## Job 并行执行

Job 支持通过 `parallelism` 和 `completions` 两个字段控制并行任务的执行策略。

### parallelism 与 completions

- **`spec.parallelism`**：同时运行的 Pod 数量（并发度）
- **`spec.completions`**：总共需要成功完成的 Pod 数量

| 配置 | 行为 |
|------|------|
| 只有 parallelism=3 | 同时运行 3 个 Pod，任一完成即 Job 完成 |
| 只有 completions=6 | 逐个运行 6 个 Pod（parallelism 默认 1） |
| parallelism=3 + completions=6 | 每次并行 3 个，共完成 6 个 |

### 执行过程示例

```
parallelism=3, completions=6

时间线:
t0: Pod-0  Pod-1  Pod-2  (3 个并行启动)
t1: Pod-0 ✓ -> Pod-3 启动 (维持 3 个并行)
t2: Pod-1 ✓ -> Pod-4 启动
t3: Pod-2 ✓ -> Pod-5 启动
t4: Pod-3 ✓ Pod-4 ✓ Pod-5 ✓ -> Job Complete
```

### 失败处理

- 如果 Pod 失败且未超过 `backoffLimit`，Job 会创建新 Pod 补充
- 如果已完成的 Pod 数 + 运行中的 Pod 数 >= completions，不再创建新 Pod
""",
        key_fields=[
            {"name": "spec.parallelism", "description": "同时运行的 Pod 最大数量", "required": True, "example": "3"},
            {"name": "spec.completions", "description": "总共需要成功完成的 Pod 数量", "required": False, "example": "6"},
            {"name": "spec.backoffLimit", "description": "失败重试上限，默认 6", "required": False, "example": "4"},
            {"name": "spec.template", "description": "Pod 模板", "required": True, "example": "..."},
        ],
        diagram="""\
  parallelism=3, completions=6

  ┌─────────────── Job (parallel-job) ────────────┐
  │  spec:                                        │
  │    parallelism: 3  ◄── 最大并发 3             │
  │    completions: 6  ◄── 总共完成 6 个           │
  └───────────────────┬───────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
     ┌────────┐  ┌────────┐  ┌────────┐
     │ Pod-0  │  │ Pod-1  │  │ Pod-2  │  并行运行
     └───┬────┘  └───┬────┘  └───┬────┘
         │ ✓         │ ✓         │ ✓
         ▼           ▼           ▼
     ┌────────┐  ┌────────┐  ┌────────┐
     │ Pod-3  │  │ Pod-4  │  │ Pod-5  │  补充并行
     └───┬────┘  └───┬────┘  └───┬────┘
         │ ✓         │ ✓         │ ✓
         └───────────┴───────────┘
                     │
                     ▼
              Job: Complete (6/6)
""",
        example_yaml="""\
apiVersion: batch/v1       # Job API 版本
kind: Job                  # 资源类型
metadata:                  # 元数据
  name: parallel-job       # Job 名称
spec:                      # 规格定义
  parallelism: 3           # 最大并发 3 个 Pod
  completions: 6           # 总共完成 6 个任务
  backoffLimit: 4          # 最多重试 4 次
  template:                # Pod 模板
    spec:                  # Pod 规格
      containers:          # 容器列表
      - name: worker       # 容器名
        image: busybox:1.36 # 镜像
        command:           # 启动命令
        - echo
        - hello
      restartPolicy: Never # 失败不重启
""",
        common_errors=[
            "parallelism 和 completions 搞混：parallelism 控制并发，completions 控制总数",
            "parallelism 设得过大导致资源耗尽（应根据集群容量合理设置）",
            "忘记写 completions 但期望所有 Pod 都完成（只有 parallelism 时，任一 Pod 成功 Job 就完成）",
            "restartPolicy 写成 Always 导致 Job 无法正常工作",
        ],
        tips=[
            "用 kubectl get jobs -w 观察 COMPLETIONS 列的变化（如 3/6）",
            "parallelism 适合可拆分的批量任务，如数据分片处理",
            "如果不设 completions，Job 只需 1 个 Pod 成功即完成",
        ],
    ),
)


# ==================== Q7.3 创建 CronJob ====================

def _check_73_create_cronjob(user_yaml: str) -> CheckResult:
    """Q7.3 创建每分钟执行的 CronJob"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.cronjobs:
        return CheckResult(
            ok=False,
            error="没有创建任何 CronJob",
            hints=["你需要 apply 一个 kind: CronJob 的 YAML"],
        )

    cj_name = next(iter(state.cronjobs))
    cronjob = state.cronjobs[cj_name]
    spec = cronjob.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="CronJob 缺少 spec", hints=[])

    schedule = spec.get("schedule")
    if not schedule:
        return CheckResult(
            ok=False,
            error="CronJob 缺少 spec.schedule",
            hints=["添加 spec.schedule: '*/1 * * * *'"],
        )

    expected_schedule = "*/1 * * * *"
    if schedule != expected_schedule:
        return CheckResult(
            ok=False,
            error=f"schedule 应为 '{expected_schedule}'，实际为 '{schedule}'",
            hints=["schedule 格式: 分 时 日 月 周，*/1 表示每分钟"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["CronJob 会按照 schedule 定期创建 Job 执行任务 🕐"],
    )


LEVEL_Q7_3 = Level(
    id="Q7.3",
    chapter="ch07",
    title="创建 CronJob",
    description="""
# 创建 CronJob 🕐

**CronJob** 类似 Linux 的 cron，按照固定时间表（schedule）定期创建 Job 执行任务。

## 任务

创建一个**每分钟执行**的 CronJob：
- `kind: CronJob`
- `spec.schedule: "*/1 * * * *"`（每分钟）
- 容器使用 `busybox:1.36`，执行 `echo "hello from cron"`

## 提示

CronJob 的 schedule 使用标准 cron 格式：`分 时 日 月 周`
```
*/1 * * * *  →  每分钟执行
0 */1 * * *  →  每小时整点执行
0 0 * * 0    →  每周日凌晨执行
```
""",
    starter_yaml="""\
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello-cron
spec:
  # schedule: "*/1 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.36
            command: ["echo", "hello from cron"]
          restartPolicy: Never
""",
    check_fn=_check_73_create_cronjob,
    lesson=Lesson(
        concept="""\
## 什么是 CronJob？

**CronJob** 是 Kubernetes 中用于**定期定时**执行任务的工作负载。它按照 cron 格式的 schedule 定期创建 Job，每个 Job 再创建 Pod 执行任务。

### CronJob vs Job

| 特性 | Job | CronJob |
|------|-----|--------|
| 触发方式 | 手动创建 | 按 schedule 自动触发 |
| 执行次数 | 一次 | 多次（定期重复） |
| 典型场景 | 数据迁移 | 定时备份、日志清理 |

### Schedule 格式（Cron 表达式）

```
┌───── 分钟 (0-59)
│ ┌───── 小时 (0-23)
│ │ ┌───── 日 (1-31)
│ │ │ ┌───── 月 (1-12)
│ │ │ │ ┌───── 星期 (0-6, 0=周日)
│ │ │ │ │
* * * * *
```

常见 schedule：
- `*/1 * * * *` - 每分钟
- `0 * * * *` - 每小时整点
- `0 0 * * *` - 每天午夜
- `0 0 * * 0` - 每周日午夜
- `*/30 * * * *` - 每 30 分钟

### CronJob 的工作流程

1. CronJob Controller 监控 schedule
2. 到达执行时间时，创建一个 Job
3. Job 创建 Pod 执行任务
4. 下一个调度时间到达时，再创建新 Job
""",
        key_fields=[
            {"name": "spec.schedule", "description": "Cron 表达式，定义执行时间表", "required": True, "example": "*/1 * * * *"},
            {"name": "spec.jobTemplate", "description": "Job 模板，定义每次触发时创建的 Job", "required": True, "example": "jobTemplate: { spec: { ... } }"},
            {"name": "spec.concurrencyPolicy", "description": "并发策略: Allow/Forbid/Replace", "required": False, "example": "Allow"},
            {"name": "spec.successfulJobsHistoryLimit", "description": "保留已完成 Job 的数量，默认 3", "required": False, "example": "3"},
            {"name": "spec.failedJobsHistoryLimit", "description": "保留失败 Job 的数量，默认 1", "required": False, "example": "1"},
        ],
        diagram="""\
  CronJob (hello-cron)
  ┌──────────────────────────────────┐
  │  spec:                           │
  │    schedule: "*/1 * * * *"       │
  │    jobTemplate:                  │
  │      spec:                       │
  │        template:                 │
  │          spec:                   │
  │            containers:           │
  │            - name: hello         │
  │              image: busybox      │
  └──────────────┬───────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
  00:00       00:01       00:02    (每分钟触发)
     │           │           │
     ▼           ▼           ▼
  Job-1       Job-2       Job-3    (创建 Job)
     │           │           │
     ▼           ▼           ▼
  Pod-1       Pod-2       Pod-3    (执行任务)
  echo hello  echo hello  echo hello
""",
        example_yaml="""\
apiVersion: batch/v1           # CronJob API 版本
kind: CronJob                 # 资源类型
metadata:                     # 元数据
  name: hello-cron            # CronJob 名称
spec:                         # 规格定义
  schedule: "*/1 * * * *"     # 每分钟执行
  jobTemplate:                # Job 模板
    spec:                     # Job 规格
      template:               # Pod 模板
        spec:                 # Pod 规格
          containers:         # 容器列表
          - name: hello       # 容器名
            image: busybox:1.36 # 镜像
            command:          # 启动命令
            - echo
            - "hello from cron"
          restartPolicy: Never # 重启策略
""",
        common_errors=[
            "schedule 格式错误（5 个字段用空格分隔，不是逗号）",
            "apiVersion 写成了 v1 而非 batch/v1",
            "忘记写 jobTemplate（CronJob 的核心是嵌套 Job 模板）",
            "schedule 中 * 和 */1 混淆：*/1 是每分钟，* 也是每分钟，但写法不同",
        ],
        tips=[
            "用 kubectl get cronjobs 查看 CronJob 的 SCHEDULE 和 LAST SCHEDULE 时间",
            "用 kubectl get jobs 查看被 CronJob 触发创建的 Job",
            "时区问题：CronJob 默认使用 UTC 时间，注意转换",
        ],
    ),
)


# ==================== Q7.4 CronJob 并发策略 ====================

def _check_74_concurrency_policy(user_yaml: str) -> CheckResult:
    """Q7.4 创建 CronJob，concurrencyPolicy 设为 Forbid"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.cronjobs:
        return CheckResult(
            ok=False,
            error="没有创建任何 CronJob",
            hints=["你需要 apply 一个 kind: CronJob 的 YAML"],
        )

    cj_name = next(iter(state.cronjobs))
    cronjob = state.cronjobs[cj_name]
    spec = cronjob.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="CronJob 缺少 spec", hints=[])

    concurrency = spec.get("concurrencyPolicy")
    if not concurrency:
        return CheckResult(
            ok=False,
            error="CronJob 缺少 spec.concurrencyPolicy",
            hints=["添加 spec.concurrencyPolicy: Forbid"],
        )

    if concurrency != "Forbid":
        return CheckResult(
            ok=False,
            error=f"concurrencyPolicy 应为 'Forbid'，实际为 '{concurrency}'",
            hints=["可选值: Allow(默认)/Forbid/Replace"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=["Forbid 策略可以防止任务重叠执行，适合不可并行的任务 🚫"],
    )


LEVEL_Q7_4 = Level(
    id="Q7.4",
    chapter="ch07",
    title="CronJob 并发策略",
    description="""
# CronJob 并发策略 🚫

当上一次触发的 Job 还在运行时，CronJob 下一次触发该如何处理？这就是 `concurrencyPolicy` 的作用。

## 任务

创建一个 CronJob，将 `concurrencyPolicy` 设为 `Forbid`：
- `kind: CronJob`
- `spec.schedule: "*/1 * * * *"`
- `spec.concurrencyPolicy: Forbid`
- 容器使用 `busybox:1.36`

## 提示

三种并发策略：
- `Allow`（默认）：允许新旧 Job 同时运行
- `Forbid`：如果上一次 Job 还在运行，跳过本次触发
- `Replace`：终止旧 Job，启动新 Job
""",
    starter_yaml="""\
apiVersion: batch/v1
kind: CronJob
metadata:
  name: forbid-cron
spec:
  schedule: "*/1 * * * *"
  # concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: task
            image: busybox:1.36
            command: ["sleep", "30"]
          restartPolicy: Never
""",
    check_fn=_check_74_concurrency_policy,
    lesson=Lesson(
        concept="""\
## CronJob 并发策略

当 CronJob 的某个 Job 执行时间超过调度间隔时，会出现新旧 Job 并行的情况。`concurrencyPolicy` 控制这种行为。

### 三种并发策略

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| **Allow**（默认） | 允许新旧 Job 同时运行 | 任务互不干扰，可并行 |
| **Forbid** | 跳过本次触发（如果旧 Job 还在运行） | 任务不可并行，如数据库迁移 |
| **Replace** | 终止旧 Job，启动新 Job | 只需要最新结果，如数据同步 |

### Forbid 策略详解

```
schedule: */1 * * * *
concurrencyPolicy: Forbid

00:00 - Job-A 启动（预计运行 90 秒）
00:01 - Job-A 仍在运行 -> 跳过本次触发
00:02 - Job-A 完成 -> 下次 00:03 正常触发 Job-B
```

Forbid 策略保证同一时间最多只有一个 Job 在运行，适合：
- 数据库备份（不能同时写同一个备份文件）
- 状态同步（不能同时修改同一份数据）
- 资源密集型任务（避免资源争抢）

### Replace 策略详解

```
schedule: */1 * * * *
concurrencyPolicy: Replace

00:00 - Job-A 启动（数据同步任务）
00:01 - Job-A 仍在运行，触发时间到达
       -> 终止 Job-A，启动 Job-B
       -> 只有最新的同步结果保留
```

Replace 策略会主动终止正在运行的旧 Job，适合：
- 数据同步（只需要最新数据）
- 缓存刷新（旧任务结果已过时）
- 报表生成（只需要最新报表）

### Allow 策略详解

Allow 是默认策略，新旧 Job 可以同时运行。适合：
- 独立的数据分片处理
- 日志清理（每次清理不同时间段）
- 发送通知邮件（互不影响）

> **注意**：Allow 策略下，如果任务执行时间持续超过调度间隔，可能堆积大量并行 Job，消耗集群资源。建议配合 `startingDeadlineSeconds` 和资源限制使用。

### startingDeadlineSeconds

如果 CronJob 错过了调度时间（如 Forbid 跳过），`startingDeadlineSeconds` 设置错过多久后不再执行。默认不设限制：

```yaml
spec:
  schedule: "*/1 * * * *"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 200   # 错过 200 秒后不再补执行
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: task
            image: busybox:1.36
            command: ["sleep", "90"]
          restartPolicy: Never
```

如果 CronJob Controller 本身不可用（如集群维护），恢复后会在 `startingDeadlineSeconds` 时间窗口内统计错过的触发次数。超过 100 次错过的触发会被标记为 Failed。
""",
        key_fields=[
            {"name": "spec.concurrencyPolicy", "description": "并发策略: Allow/Forbid/Replace", "required": True, "example": "Forbid"},
            {"name": "spec.schedule", "description": "Cron 表达式时间表", "required": True, "example": "*/1 * * * *"},
            {"name": "spec.startingDeadlineSeconds", "description": "错过调度的宽限期（秒）", "required": False, "example": "200"},
            {"name": "spec.jobTemplate", "description": "Job 模板", "required": True, "example": "..."},
        ],
        diagram="""\
  concurrencyPolicy: Forbid

  时间轴:
  00:00 ─────────── 00:01 ─────────── 00:02 ─────────── 00:03
    │                  │                 │                  │
    ▼                  ▼                 ▼                  ▼
  Job-A 启动       触发时间到达       Job-A 完成          触发时间到达
  (运行 90s)       但 Job-A 在运行     ✓                 → Job-B 启动
                   → Forbid: 跳过

  ┌───────────────────┐
  │  并发策略对比      │
  ├───────────────────┤
  │ Allow:  Job-A + Job-B 同时运行
  │ Forbid: 跳过 Job-B（Job-A 还在跑）
  │ Replace: 终止 Job-A, 启动 Job-B
  └───────────────────┘
""",
        example_yaml="""\
apiVersion: batch/v1              # CronJob API 版本
kind: CronJob                    # 资源类型
metadata:                        # 元数据
  name: forbid-cron              # CronJob 名称
spec:                            # 规格定义
  schedule: "*/1 * * * *"        # 每分钟执行
  concurrencyPolicy: Forbid      # 禁止并发：跳过本次触发
  successfulJobsHistoryLimit: 3  # 保留 3 个成功 Job
  failedJobsHistoryLimit: 1      # 保留 1 个失败 Job
  jobTemplate:                   # Job 模板
    spec:                        # Job 规格
      template:                  # Pod 模板
        spec:                    # Pod 规格
          containers:            # 容器列表
          - name: task           # 容器名
            image: busybox:1.36  # 镜像
            command:             # 启动命令
            - sleep
            - "30"
          restartPolicy: Never   # 重启策略
""",
        common_errors=[
            "concurrencyPolicy 写成了小写 forbid（K8s 要求首字母大写: Forbid）",
            "把 concurrencyPolicy 写成了 parallelism（后者是 Job 的字段）",
            "不理解 Forbid 和 Replace 的区别：Forbid 跳过，Replace 替换",
            "忘记设 schedule 导致 CronJob 无法触发",
        ],
        tips=[
            "用 kubectl get cronjobs 查看 LAST SCHEDULE 时间确认是否跳过",
            "Forbid 适合不可并行的任务，Replace 适合只需要最新结果的任务",
            "startingDeadlineSeconds 可以防止 CronJob 长时间错过执行后补执行大量任务",
        ],
    ),
)


# ==================== Q7.5 集群实战 - 部署 Job 计算 ====================

def _check_75_deploy_job(user_yaml: str) -> CheckResult:
    """Q7.5 集群实战 - 部署一个真实 Job 到集群"""
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    if not state.jobs:
        return CheckResult(
            ok=False,
            error="没有创建任何 Job",
            hints=["你需要 apply 一个 kind: Job 的 YAML"],
        )

    job_name = next(iter(state.jobs))
    job = state.jobs[job_name]
    spec = job.get("spec", {})
    if not isinstance(spec, dict):
        return CheckResult(ok=False, error="Job 缺少 spec", hints=[])

    template = spec.get("template", {})
    if not isinstance(template, dict) or not template:
        return CheckResult(ok=False, error="Job 缺少 spec.template", hints=[])

    tmpl_spec = template.get("spec", {})
    if not isinstance(tmpl_spec, dict):
        return CheckResult(ok=False, error="Job 缺少 spec.template.spec", hints=[])

    containers = tmpl_spec.get("containers", [])
    if not isinstance(containers, list) or not containers:
        return CheckResult(ok=False, error="Job 缺少 containers", hints=[])

    c = containers[0]
    if not isinstance(c, dict):
        return CheckResult(ok=False, error="containers[0] 格式错误", hints=[])

    image = c.get("image", "")
    if not image:
        return CheckResult(
            ok=False,
            error="容器缺少 image",
            hints=["spec.template.spec.containers[0].image 必须指定"],
        )

    # 检查 restartPolicy
    restart_policy = tmpl_spec.get("restartPolicy", "")
    if restart_policy not in ("Never", "OnFailure"):
        return CheckResult(
            ok=False,
            error=f"restartPolicy 应为 Never 或 OnFailure，实际为 '{restart_policy}'",
            hints=["Job 的 Pod restartPolicy 只能是 Never 或 OnFailure"],
        )

    return CheckResult(
        ok=True, state=state,
        hints=[
            "YAML 校验通过！在真实集群上执行：",
            "  kubectl apply -f <your-yaml>",
            "  kubectl get jobs",
            "  kubectl get pods  # 查看 Job 创建的 Pod",
            "  kubectl logs <pod-name>  # 查看计算结果",
        ],
    )


LEVEL_Q7_5 = Level(
    id="Q7.5",
    chapter="ch07",
    title="集群实战: 部署 Job 计算",
    description="""
# 集群实战: 部署 Job 计算 🏗️

来真实集群上部署一个 Job，观察它的完整生命周期！

## 任务

1. 编写一个 Job YAML（计算任务或数据处理）
2. 用 `kubectl apply` 部署到集群
3. 观察 Job 从启动到完成的过程
4. 查看 Pod 的输出日志

## 要求

- `kind: Job`
- 容器有 `image` 和 `command`
- `restartPolicy: Never` 或 `OnFailure`

## 验证步骤

```bash
# 1. 部署 Job
kubectl apply -f job.yaml

# 2. 查看 Job 状态
kubectl get jobs

# 3. 观察 Pod（等待 Completed）
kubectl get pods -w

# 4. 查看计算结果
kubectl logs <pod-name>

# 5. 查看 Job 完成详情
kubectl describe job <job-name>
```
""",
    starter_yaml="""\
apiVersion: batch/v1
kind: Job
metadata:
  name: compute-job
spec:
  template:
    spec:
      containers:
      - name: compute
        # 补全 image 和 command
      restartPolicy: Never
""",
    check_fn=_check_75_deploy_job,
    lesson=Lesson(
        concept="""\
## Job 在真实集群中的完整生命周期

在真实 K8s 集群中部署 Job 时，理解其完整生命周期至关重要。

### Job 状态流转

```
创建 Job -> 创建 Pod -> Pod Running -> Pod Succeeded -> Job Complete
                                    ↓ Pod Failed
                                    -> 重试 (backoffLimit)
                                    -> 超过限制 -> Job Failed
```

### 关键状态字段

- **COMPLETIONS**: `已完成/期望` (如 1/1 表示完成)
- **DURATION**: Job 已运行时长
- **AGE**: Job 创建以来的时间

### Pod 的 restartPolicy 与 Job 的 backoffLimit

| restartPolicy | Pod 失败行为 | backoffLimit 作用 |
|---------------|-------------|-------------------|
| Never | 删除旧 Pod，创建新 Pod | 限制创建新 Pod 的次数 |
| OnFailure | 同一 Pod 内重启容器 | 限制重启次数 |

### Job 完成后的清理策略

Job 完成后默认保留 Pod 和 Job 对象，方便查看日志和排查问题。但在生产环境中，大量已完成 Job 会占用 etcd 存储，需要清理策略：

**1. ttlSecondsAfterFinished（自动清理）**

```yaml
spec:
  ttlSecondsAfterFinished: 60    # 完成 60 秒后自动删除
  template:
    spec:
      containers:
      - name: task
        image: busybox:1.36
        command: ["echo", "done"]
      restartPolicy: Never
```

TTL Controller 会在 Job 完成（成功或失败）后等待指定秒数，然后自动删除 Job 及其关联的 Pod。

**2. 手动清理**

```bash
# 删除单个 Job（同时删除关联 Pod）
kubectl delete job <name>

# 删除所有已完成 Job
kubectl delete jobs -n <namespace> --field-selector=status.successful=1

# 清理失败的 Job
kubectl delete jobs -n <namespace> --field-selector=status.failed=1
```

**3. CronJob 历史限制**

CronJob 可以通过 `successfulJobsHistoryLimit` 和 `failedJobsHistoryLimit` 控制保留的 Job 数量：

```yaml
spec:
  schedule: "*/1 * * * *"
  successfulJobsHistoryLimit: 3   # 保留 3 个成功 Job（默认 3）
  failedJobsHistoryLimit: 1       # 保留 1 个失败 Job（默认 1）
```

### 真实场景注意事项

1. **资源请求**：为 Job 设置合理的 resources.requests，避免资源不足导致 Pending
2. **超时控制**：使用 `activeDeadlineSeconds` 限制 Job 最长运行时间，防止卡死
3. **并发控制**：大任务拆分用 parallelism/completions，注意集群容量
4. **日志收集**：Job Pod 完成后日志仍可查看，但 Pod 被删除后丢失，建议提前收集
5. **幂等性**：设计 Job 任务时确保幂等（重试不会产生副作用），因为 backoffLimit 可能触发多次执行
""",
        key_fields=[
            {"name": "spec.template.spec.containers[].image", "description": "容器镜像", "required": True, "example": "perl:5.38"},
            {"name": "spec.template.spec.containers[].command", "description": "容器启动命令", "required": True, "example": "[perl, -Mbignum=bpi, -wle, print bpi(2000)]"},
            {"name": "spec.template.spec.restartPolicy", "description": "重启策略: Never 或 OnFailure", "required": True, "example": "Never"},
            {"name": "spec.activeDeadlineSeconds", "description": "Job 最长运行时间（秒）", "required": False, "example": "300"},
            {"name": "spec.ttlSecondsAfterFinished", "description": "完成后自动清理的延迟秒数", "required": False, "example": "100"},
        ],
        diagram="""\
  Job 部署到集群的完整流程

  kubectl apply ──> API Server
                        │
                   ┌────┴────┐
                   │  Job     │  创建 Job 资源
                   │ Controller│
                   └────┬────┘
                        │
                   ┌────┴────┐
                   │  Pod     │  Pending → Running
                   │ (compute)│
                   └────┬────┘
                        │
              ┌─────────┼─────────┐
              ▼                   ▼
        Pod Succeeded        Pod Failed
        exit code 0          exit code != 0
              │                   │
              ▼                   ▼
        Job Complete        重试? (backoffLimit)
              │                   │
              ▼                   ▼
        kubectl logs        超过限制 → Job Failed
        查看输出结果
""",
        example_yaml="""\
apiVersion: batch/v1              # Job API 版本
kind: Job                        # 资源类型
metadata:                        # 元数据
  name: compute-job              # Job 名称
spec:                            # 规格定义
  activeDeadlineSeconds: 300     # 最长运行 5 分钟
  ttlSecondsAfterFinished: 60    # 完成后 60 秒自动清理
  template:                      # Pod 模板
    spec:                        # Pod 规格
      containers:                # 容器列表
      - name: compute            # 容器名
        image: perl:5.38         # Perl 镜像
        command:                 # 启动命令
        - perl
        - "-Mbignum=bpi"
        - "-wle"
        - "print bpi(2000)"
      restartPolicy: Never       # 失败不重启
""",
        common_errors=[
            "Job 一直不完成：检查 Pod 日志，可能是 command 错误导致容器无法正常退出",
            "Job 反复失败：检查 backoffLimit 和 Pod 的错误日志",
            "忘记设 restartPolicy 导致默认值不适用 Job 场景",
            "资源不足导致 Pod 一直 Pending，用 kubectl describe pod 排查",
        ],
        tips=[
            "用 kubectl get jobs -w 实时观察 Job 完成状态",
            "用 kubectl describe job <name> 查看 Job 事件和 Pod 状态",
            "Job 完成后 Pod 仍在，用 kubectl logs <pod> 查看输出",
            "设置 ttlSecondsAfterFinished 可以自动清理完成的 Job 和 Pod",
        ],
    ),
)


CHAPTER_7_LEVELS: list[Level] = [
    LEVEL_Q7_1, LEVEL_Q7_2, LEVEL_Q7_3, LEVEL_Q7_4, LEVEL_Q7_5,
]
