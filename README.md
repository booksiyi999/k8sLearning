# 🍒 K8s Quest

> 樱桃的 K8s 闯关学习 App - 6 章 30 关，从零到 K8s 实战（含真实集群模式）

## 📊 当前状态

**v0.4 - 教学模式 + 真实集群** | 6 章 30 关 · 701 测试全绿 · 教学Tab + 集群实战

| 维度 | 数据 |
|------|------|
| 章节数 | 6 章（Pod / Deployment / Service / ConfigMap / Storage / Scheduling） |
| 关卡数 | 30 关（每章 5 关：4 模拟器 + 1 集群实战） |
| 功能测试 | 701 passed, 0 failed |
| 教学文档 | 30 关全部含 Lesson（概念/关键字段/图解/示例/常见错误/建议） |
| 集群模式 | 可选，K8S_QUEST_MODE=cluster + KUBECONFIG 启用 |
| 后端 | FastAPI + PyYAML 模拟器 + kubectl 集群连接 |
| 前端 | Alpine.js 单页（教学Tab / 练习Tab / 集群实战Tab） |

## ✨ 特性

- 📖 **教学模式**：每关含知识点讲解（概念/关键字段/图解/示例YAML/常见错误/学习建议）
- 🔧 **真实集群模式**：可选连接真实 K8s 集群，kubectl apply 部署 + 资源查看 + Pod 日志 + 连通性测试
- 🎮 **游戏化闯关**：XP 系统、等级称号、连击计数、徽章成就
- 🎯 **双模式校验**：模拟器模式（零依赖）+ 集群模式（真实 K8s）
- 📊 **结业报告**：知识掌握度分析、薄弱项识别、成绩评定
- 🚀 **单进程架构**：FastAPI 同时服务 API + 前端
- 🧪 **TDD + Loop Engineering**：701 测试（含 E2E + 前端逻辑 + QA 攻击 + 集群模块）
- 📦 **一键部署**：Docker / systemd / 本地开发 / 集群模式

## 🚀 快速开始

> ⚠️ **重要**：前端 JS 库（Alpine.js/marked/confetti）已本地化到 `frontend/vendor/`，**不依赖任何外网 CDN**，国内部署无空白页问题。

### 本地开发（秒级试玩）

```bash
cd ~/k8s-quest
./setup.sh --dev
```

或手动：
```bash
cd ~/k8s-quest/backend
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 启动开发服务器（热重载）
.venv/bin/uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://localhost:8000

### 集群模式（连接真实 K8s）

```bash
cd ~/k8s-quest
./setup.sh --cluster
# 然后启动:
K8S_QUEST_MODE=cluster cd backend && .venv/bin/uvicorn app.main:app --port 8000
```

需要：kubectl 已安装 + KUBECONFIG 已配置。每关有 [📖 知识讲解] [✏️ 动手练习] [🔧 集群实战] 三个 Tab。

### Docker 一键部署

```bash
cd ~/k8s-quest
docker build -t k8s-quest:0.5 .
docker run -d --name k8s-quest --restart unless-stopped -p 8000:8000 k8s-quest:0.5
curl http://localhost:8000/api/health
```

浏览器打开 http://localhost:8000

## 🧪 跑测试

```bash
cd ~/k8s-quest/backend
.venv/bin/pytest -v          # 全部测试
.venv/bin/pytest -q          # 简洁输出
.venv/bin/pytest tests/test_ch01_levels.py -v  # 按章节跑
```

## 📚 课程概览

| 章节 | 图标 | 关卡 | 学习目标 |
|------|------|------|----------|
| Ch1: Pod 基础 | 🌱 | Q1.1-Q1.5 | 创建、标签、多容器、资源限制、集群实战 |
| Ch2: Deployment | 🚀 | Q2.1-Q2.5 | 副本管理、扩缩容、滚动更新、回滚、集群实战 |
| Ch3: Service 网络 | 🔗 | Q3.1-Q3.5 | ClusterIP、NodePort、DNS、Headless、集群实战 |
| Ch4: 配置管理 | ⚙️ | Q4.1-Q4.5 | ConfigMap 创建/注入/挂载、Secret、集群实战 |
| Ch5: 存储 | 💾 | Q5.1-Q5.5 | PV/PVC、Pod 挂载、emptyDir、集群实战 |
| Ch6: 调度 | 🎯 | Q6.1-Q6.5 | nodeSelector、Affinity、Taints、资源调度、集群实战 |
| Ch7: Job/CronJob | 📋 | Q7.1-Q7.5 | 一次性任务、并行执行、定时任务、并发策略、集群实战 |
| Ch8: StatefulSet | 🗄️ | Q8.1-Q8.5 | 有状态应用、扩缩容、Headless+STS、持久化、集群实战 |
| Ch9: RBAC | 🔐 | Q9.1-Q9.5 | Role、RoleBinding、ClusterRole、CRB、集群实战 |
| Ch10: HPA | 📈 | Q10.1-Q10.5 | CPU阈值、扩缩容配置、多指标、行为配置、集群实战 |
| Ch11: Ingress | 🌐 | Q11.1-Q11.5 | 单路由、多域名、路径路由、TLS、集群实战 |
| Ch12: NetworkPolicy | 🛡️ | Q12.1-Q12.5 | 默认拒绝、命名空间隔离、Pod白名单、双向控制、集群实战 |

## 🎮 游戏化系统

### XP 与等级

- 每关通过 +10 XP
- 章节全通关 +50 XP
- 8 级称号：🎓 萌新 → 🌱 学徒 → 🚀 行者 → 🔗 武者 → ⚙️ 大师 → 💾 宗师 → 🎯 贤者 → 👑 传奇

### 结业报告

完成关卡后可生成结业报告，包含：
- **知识域掌握度**：5 大知识域（工作负载/网络/配置/存储/调度）的完成率
- **薄弱项识别**：未完成或多次尝试的关卡及其关联知识点
- **优势项**：一次通过的关卡
- **成绩评定**：S/A/B/C/D 五级评定
- **学习建议**：基于完成情况的个性化推荐

## 🏗️ 技术栈

- **后端**: FastAPI + Uvicorn + PyYAML
- **前端**: 纯 HTML + Alpine.js（无需 build）
- **模拟器**: 自研 Python YAML 校验引擎
- **部署**: Docker / systemd / Nginx
- **测试**: pytest + Loop Engineering（内循环自测 + QA 攻击循环）

## 📖 文档

| 文档 | 用途 |
|------|------|
| [docs/design.md](docs/design.md) | 产品设计与架构决策 |
| [docs/content-design-v0.3.md](docs/content-design-v0.3.md) | 课程内容设计（24 关详细设计） |
| [docs/deployment.md](docs/deployment.md) | 部署文档（本地/Docker/systemd/生产） |
| [docs/team-workflow-v2-loop.md](docs/team-workflow-v2-loop.md) | Loop Engineering 团队工作流 |

## 🔌 API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/levels` | GET | 关卡列表（30 关） |
| `/api/level/{id}` | GET | 关卡详情（含知识点、XP） |
| `/api/lesson/{id}` | GET | 教学文档（概念/关键字段/图解/示例/常见错误） |
| `/api/check` | POST | 模拟器 YAML 校验 |
| `/api/deploy` | POST | 双模式部署（模拟器 or 真实集群） |
| `/api/meta` | GET | 游戏化元数据（章节/知识点/XP/称号） |
| `/api/report` | POST | 生成结业报告 |
| `/api/cluster/status` | GET | 集群连接状态 |
| `/api/resources` | GET | 集群资源列表（kubectl get） |
| `/api/logs/{pod}` | GET | Pod 日志（kubectl logs） |
| `/api/test-connectivity` | POST | Service 连通性测试 |

## 🗺️ 路线图

- ✅ v0.1: MVP 单关 demo（Pod 创建）
- ✅ v0.2: 12 关完整课程（Pod + Deployment + Service）
- ✅ v0.3: 24 关 + 游戏化 + 结业报告
- ✅ v0.4: 教学模式 + 真实集群连接 + 30 关 + 701 测试
- 🔜 v0.5: AI 答题助手 + 集群状态实时刷新
- 🔜 v1.0: 用户系统 + 进度云端同步 + CKA 模拟器

## 团队

- **PM**: 🍒 樱桃（Hermes Agent，glm-5.2）
- **工程师**: Loop Engineering Agent Team
- **Boss**: 李航宇（Master）

## License

MIT
