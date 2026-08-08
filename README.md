# 🚀 K8s 实战学堂

> 闯关式 K8s 学习平台 — 通过实操+文档让新员工快速上手 Kubernetes

## 📊 当前状态

**v2.0** | 29 章 150 关 · 3140 测试全绿 · 模拟器+真实集群双模式

| 维度 | 数据 |
|------|------|
| 章节数 | 29 章（Ch00 架构总览 ~ Ch28 CKA 模拟考试） |
| 关卡数 | 150 关（每章 5 关，Ch17 Operator 10 关） |
| 测试数 | 3140 passed, 0 failed |
| 教学文档 | 150 关全部含 Lesson（概念/关键字段/图解/示例/常见错误/建议） |
| 模拟器 | 26 种 K8s 资源类型，含 RBAC 权限模拟 + NetworkPolicy 流量模拟 |
| 集群模式 | 可选，K8S_QUEST_MODE=cluster + KUBECONFIG 启用 |
| 交互终端 | 内置 kubectl 终端，支持 30+ 子命令，危险命令确认 |
| 后端 | FastAPI + PyYAML 模拟器 + kubectl 集群连接 |
| 前端 | Alpine.js 单页（教学Tab / 练习Tab / 终端Tab / 集群实战Tab） |

## ✨ 特性

- 📖 **闯关式教学**：每关含六节结构（概念→关键字段→图解→示例YAML→常见错误→学习建议），从 K8s 历史由来到 CKA 考试全覆盖
- 🖥️ **交互式 Kubectl 终端**：关卡内直接执行 kubectl 命令到真实集群，命令白名单+注入防护+危险命令确认
- 🔧 **真实集群模式**：连接真实 K8s 集群，kubectl apply 部署 + 资源查看 + Pod 日志 + 连通性测试
- 🎮 **游戏化激励**：XP 系统、8 级称号、连击计数、10 个徽章成就、结业报告
- 🎯 **双模式校验**：模拟器模式（零依赖开箱即用）+ 集群模式（真实 K8s 运维体验）
- 📊 **结业报告**：28 个知识域掌握度分析、薄弱项识别、S/A/B/C/D 五级评定
- 🧪 **3140 测试**：含 E2E + 前端逻辑 + QA 攻击 + 模拟器集成 + RBAC/NetworkPolicy 行为验证
- 📦 **零外网依赖**：所有 JS 库本地化到 vendor/，国内部署无空白页问题

## 🚀 快速开始

### 方式一：本地开发（推荐校招生试用）

```bash
cd ~/k8s-quest
./setup.sh --dev
```

或手动：
```bash
cd ~/k8s-quest/backend
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 启动开发服务器
.venv/bin/uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://localhost:8000 — 从 **Q0.1 K8s 架构总览** 开始闯关！

### 方式二：Docker 一键部署

```bash
cd ~/k8s-quest
docker build -t k8s-quest:v2 .
docker run -d --name k8s-quest --restart unless-stopped -p 8000:8000 k8s-quest:v2
curl http://localhost:8000/api/health  # 确认启动
```

### 方式三：连接真实 K8s 集群

```bash
# 前提：kubectl 已安装 + KUBECONFIG 已配置
cd ~/k8s-quest
./setup.sh --cluster

# 启动集群模式
cd backend
K8S_QUEST_MODE=cluster .venv/bin/uvicorn app.main:app --port 8000
```

集群模式下每关有 4 个 Tab：
- **📖 知识讲解** — 概念/图解/示例
- **✏️ 动手练习** — YAML 编辑器 + 模拟器校验
- **🖥️ 终端** — 直接执行 kubectl 命令（get/describe/logs/apply/delete 等）
- **🔧 集群实战** — 资源列表 + Pod 日志 + Service 连通性测试

## 📚 课程概览

| 章节 | 图标 | 关卡 | 学习目标 |
|------|------|------|----------|
| **Ch00: 架构总览** | 🏗️ | Q0.1-Q0.3 | K8s 历史由来、控制面/数据面、声明式模型、kubectl 全链路 |
| Ch01: Pod 基础 | 🌱 | Q1.1-Q1.7 | 创建、标签、资源限制、Pod 探针(liveness/readiness)、集群实战 |
| Ch02: Deployment | 🚀 | Q2.1-Q2.5 | 副本管理、扩缩容、滚动更新、回滚、集群实战 |
| Ch03: Service 网络 | 🔗 | Q3.1-Q3.5 | ClusterIP、NodePort、DNS、Headless、集群实战 |
| Ch04: 配置管理 | ⚙️ | Q4.1-Q4.5 | ConfigMap 创建/注入/挂载、Secret、集群实战 |
| Ch05: 存储 | 💾 | Q5.1-Q5.5 | PV/PVC、Pod 挂载、emptyDir、集群实战 |
| Ch06: 调度 | 🎯 | Q6.1-Q6.5 | nodeSelector、Affinity、Taints、资源调度、集群实战 |
| Ch07: Job/CronJob | 📋 | Q7.1-Q7.5 | 一次性任务、并行执行、定时任务、并发策略 |
| Ch08: StatefulSet | 🗄️ | Q8.1-Q8.5 | 有状态应用、扩缩容、Headless+STS、持久化 |
| Ch09: RBAC | 🔐 | Q9.1-Q9.5 | Role、RoleBinding、ClusterRole、权限模拟验证 |
| Ch10: HPA | 📈 | Q10.1-Q10.5 | CPU阈值、扩缩容配置、多指标、行为配置 |
| Ch11: Ingress | 🌐 | Q11.1-Q11.5 | 单路由、多域名、路径路由、TLS |
| Ch12: NetworkPolicy | 🛡️ | Q12.1-Q12.5 | 默认拒绝、命名空间隔离、流量模拟验证 |
| Ch13: DaemonSet | 🛡️ | Q13.1-Q13.5 | 节点守护进程、日志收集、网络插件 |
| Ch14: Namespace & Quota | 📦 | Q14.1-Q14.5 | 命名空间隔离、资源配额、LimitRange |
| Ch15: PDB | 🛡️ | Q15.1-Q15.5 | 中断预算、维护保护、优先级 |
| Ch16: PriorityClass | ⭐ | Q16.1-Q16.5 | 优先级抢占、驱逐机制 |
| Ch17: CRD & Operator | 🔧 | Q17.1-Q17.10 | CRD Schema、Status子资源、Reconcile循环、OwnerReference、Finalizer、Conditions |
| Ch18: SA & 安全上下文 | 🛡️ | Q18.1-Q18.5 | ServiceAccount、安全上下文、PSA |
| Ch19: Helm | 📦 | Q19.1-Q19.5 | Chart 结构、模板渲染、Repository |
| Ch20: 存储进阶 | 💽 | Q20.1-Q20.5 | StorageClass、CSI、VolumeSnapshot |
| Ch21: 集群维护 | 🔧 | Q21.1-Q21.5 | etcd 备份恢复、证书续期、kubeadm upgrade |
| Ch22: 故障排查 | 🔍 | Q22.1-Q22.5 | CrashLoopBackOff、Pending Pod、节点故障 |
| Ch23: 监控与日志 | 📊 | Q23.1-Q23.5 | Metrics Server、Prometheus、日志聚合 |
| Ch24: 安全策略进阶 | 🔒 | Q24.1-Q24.5 | PSS 策略、Seccomp、降权 |
| Ch25: 多容器模式 | 📦 | Q25.1-Q25.5 | Sidecar、Ambassador、Adapter |
| Ch26: 高级调度 | 🎯 | Q26.1-Q26.5 | 拓扑分布、优先级混合、Node Affinity |
| Ch27: Service Mesh | 🌐 | Q27.1-Q27.5 | Istio sidecar 注入、VirtualService、Gateway |
| Ch28: CKA 模拟考试 | 🎓 | Q28.1-Q28.5 | kubectl 操作挑战、故障排查、网络诊断、RBAC 检查 |

## 🎮 游戏化系统

### XP 与等级

- 每关通过 +10 XP，章节全通关 +50 XP
- 8 级称号：🎓 萌新 → 🌱 学徒 → 🚀 行者 → 🔗 武者 → ⚙️ 大师 → 💾 宗师 → 🎯 贤者 → 👑 传奇

### 结业报告

完成关卡后生成结业报告，包含：
- **28 个知识域掌握度**（架构基础/工作负载/网络/存储/调度/RBAC/Operator 等）
- **薄弱项识别**：未完成或多次尝试的关卡
- **S/A/B/C/D 五级评定** + 个性化学习建议

## 🧪 跑测试

```bash
cd ~/k8s-quest/backend
.venv/bin/pytest -q                    # 全部 3140 测试
.venv/bin/pytest tests/test_ch00.py -v # 按章节跑
.venv/bin/pytest tests/test_kubectl_terminal.py -v  # 终端测试
```

## 🔌 API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/levels` | GET | 关卡列表（150 关） |
| `/api/level/{id}` | GET | 关卡详情 |
| `/api/lesson/{id}` | GET | 教学文档 |
| `/api/check` | POST | 模拟器 YAML 校验 |
| `/api/deploy` | POST | 双模式部署（模拟器/集群） |
| `/api/meta` | GET | 游戏化元数据 |
| `/api/report` | POST | 生成结业报告 |
| `/api/kubectl` | POST | 执行 kubectl 命令（集群模式） |
| `/api/kubectl/whitelist` | GET | 允许的 kubectl 子命令 |
| `/api/cluster/status` | GET | 集群连接状态 |
| `/api/resources` | GET | 集群资源列表 |
| `/api/logs/{pod}` | GET | Pod 日志 |
| `/api/test-connectivity` | POST | Service 连通性测试 |
| `/api/admin/all-levels` | GET | 全部关卡内容（管理后台） |

## 🏗️ 技术栈

- **后端**: FastAPI + Uvicorn + PyYAML
- **前端**: 纯 HTML + Alpine.js（无需 build，JS 库本地化）
- **模拟器**: 自研 Python YAML 校验引擎（26 种资源 + RBAC/NetworkPolicy 行为模拟）
- **集群连接**: subprocess 调用 kubectl（命令白名单 + 注入防护）
- **部署**: Docker / 本地开发 / 集群模式
- **测试**: pytest + Loop Engineering（3140 测试）

## 📖 文档

| 文档 | 用途 |
|------|------|
| [docs/loop-iteration-plan-v2.0.md](docs/loop-iteration-plan-v2.0.md) | v2.0 迭代计划（Sprint 1-6） |
| [docs/design.md](docs/design.md) | 产品设计与架构决策 |

## 🗺️ 版本历史

| 版本 | 关卡 | 测试 | 关键特性 |
|------|------|------|----------|
| v0.1 | 1 | - | MVP demo |
| v0.3 | 24 | 461 | 游戏化 + 结业报告 |
| v0.4 | 30 | 593 | 教学内容 + 集群模式 |
| v0.5 | 60 | 701 | Job/StatefulSet/RBAC/HPA/Ingress/NetworkPolicy |
| v0.6 | 90 | 1570 | DaemonSet/Namespace/PDB/PriorityClass/CRD/SA + QA |
| v1.0 | 140 | 2850 | 28 章完整课程 + Multi-Container/ServiceMesh/CKA |
| **v2.0** | **150** | **3140** | **Ch00 架构总览 + Pod 探针 + Operator 扩展 + 模拟器行为验证 + Kubectl 交互终端 + Ch21/Ch28 重写** |

## License

MIT
