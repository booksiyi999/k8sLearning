# K8s Quest

> 🍒 樱桃的 K8s 闯关学习 App — 30 天从小白到专家

## 状态

🚧 **MVP v0.1 已完成** — 第一个关卡（创建 Pod）已跑通完整体验闭环。

## ✨ 特性

- 🎯 **模拟器闯关**：纯 YAML/命令闯关，零集群成本（单用户 $0 vs 同类 $5-15/月）
- 🚀 **单进程架构**：FastAPI 同时服务 API + 前端，部署极简
- 🧪 **TDD 全覆盖**：13 个单元测试 + 端到端 curl 验证全过
- 📦 **三档部署**：Docker / systemd / Nginx+HTTPS 全文档

## 📚 文档

| 文档 | 用途 |
|---|---|
| [docs/design.md](docs/design.md) | 产品设计与架构决策 |
| [docs/plan-v0.1.md](docs/plan-v0.1.md) | MVP 实施计划 |
| [docs/deployment.md](docs/deployment.md) | 🚀 **部署文档（本地/Docker/systemd/生产）** |

## 🚀 快速开始（本地开发）

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 启动开发服务器（热重载）
.venv/bin/uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://localhost:8000

## 🐳 快速部署（Docker）

```bash
docker build -t k8s-quest:0.1 .
docker run -d --name k8s-quest --restart unless-stopped -p 8000:8000 k8s-quest:0.1
curl http://localhost:8000/api/health
```

详见 [docs/deployment.md](docs/deployment.md)。

## 🧪 跑测试

```bash
cd backend
.venv/bin/pytest -v
```

## 🏗️ 技术栈

- **后端**: FastAPI + Uvicorn + PyYAML
- **前端**: 纯 HTML + Alpine.js（无需 build）
- **模拟器**: 自研 Python YAML 校验引擎
- **部署**: Docker / systemd / Nginx

## 🎯 MVP v0.1 范围

- ✅ FastAPI 后端骨架 + 健康检查
- ✅ YAML 模拟器（Pod/Deployment/Service CRUD）
- ✅ Q1.1 关卡（创建第一个 Pod）
- ✅ 自动校验 + 友好错误提示
- ✅ Alpine.js 单页前端

## 🗺️ 路线图

- v0.2: 扩充到 12 关（Pod + Deployment + Service 三章）
- v0.3: 集群状态可视化 + 进度保存
- v1.0: 完整 30 天课程 + 用户系统

## 团队

- **PM**: 🍒 樱桃（Hermes Agent 猫娘助手，glm-5.2）
- **工程师**: Claude Code（glm-5.2）
- **Boss**: 李航宇（Master）

## License

MIT
