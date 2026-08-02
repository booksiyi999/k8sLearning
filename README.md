# 🍒 K8s Quest

> 樱桃的 K8s 闯关学习 App — 6 章 24 关，从零到 K8s 实战

## 📊 当前状态

**v0.3 - 游戏化学习体验** | 6 章 24 关 · 189 测试全绿 · 前端游戏化已完成

| 维度 | 数据 |
|------|------|
| 章节数 | 6 章（Pod / Deployment / Service / ConfigMap / Storage / Scheduling） |
| 关卡数 | 24 关（每章 4 关） |
| 功能测试 | 593 passed, 0 failed (461功能 + 132 QA攻击) |
| QA 攻击测试 | 132 passed（3轮：88后端 + 44前端，0应用bug） |
| 后端 | FastAPI + PyYAML 模拟器 |
| 前端 | Alpine.js 单页（游戏化已完成） |

## ✨ 特性

- 🎮 **游戏化闯关**：XP 系统、等级称号、连击计数、徽章成就
- 🎯 **模拟器闯关**：纯 YAML 校验，零集群成本
- 📊 **结业报告**：知识掌握度分析、薄弱项识别、成绩评定
- 🚀 **单进程架构**：FastAPI 同时服务 API + 前端
- 🧪 **TDD + Loop Engineering**：593 测试（含 E2E 旅程 + 前端逻辑 + QA 攻击）
- 📦 **一键部署**：Docker / systemd / 本地开发

## 🚀 快速开始

### 本地开发（秒级试玩）

```bash
cd ~/k8s-quest/backend
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 启动开发服务器（热重载）
.venv/bin/uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://localhost:8000

### Docker 一键部署

```bash
cd ~/k8s-quest
docker build -t k8s-quest:0.3 .
docker run -d --name k8s-quest --restart unless-stopped -p 8000:8000 k8s-quest:0.3
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
| Ch1: Pod 基础 | 🌱 | Q1.1-Q1.4 | 创建、标签、多容器、资源限制 |
| Ch2: Deployment | 🚀 | Q2.1-Q2.4 | 副本管理、扩缩容、滚动更新、回滚 |
| Ch3: Service 网络 | 🔗 | Q3.1-Q3.4 | ClusterIP、NodePort、DNS、Headless |
| Ch4: 配置管理 | ⚙️ | Q4.1-Q4.4 | ConfigMap 创建/注入/挂载、Secret |
| Ch5: 存储 | 💾 | Q5.1-Q5.4 | PV/PVC、Pod 挂载、emptyDir |
| Ch6: 调度 | 🎯 | Q6.1-Q6.4 | nodeSelector、Affinity、Taints、资源调度 |

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
| `/api/levels` | GET | 关卡列表 |
| `/api/level/{id}` | GET | 关卡详情（含知识点、XP） |
| `/api/check` | POST | 提交 YAML 答案校验 |
| `/api/meta` | GET | 游戏化元数据（章节/知识点/XP/称号） |
| `/api/report` | POST | 生成结业报告 |

## 🗺️ 路线图

- ✅ v0.1: MVP 单关 demo（Pod 创建）
- ✅ v0.2: 12 关完整课程（Pod + Deployment + Service）
- ✅ v0.3: 24 关 + 游戏化 + 结业报告
- 🔜 v0.4: 集群状态可视化 + AI 答题助手
- 🔜 v1.0: 用户系统 + 进度云端同步 + CKA 模拟器

## 团队

- **PM**: 🍒 樱桃（Hermes Agent，glm-5.2）
- **工程师**: Loop Engineering Agent Team
- **Boss**: 李航宇（Master）

## License

MIT
