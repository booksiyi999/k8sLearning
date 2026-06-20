# K8s Quest

> 🍒 樱桃的 K8s 闯关学习 App

## 状态

🚧 MVP v0.1 开发中

## 设计文档

- [design.md](docs/design.md) - 产品设计与架构
- [plan-v0.1.md](docs/plan-v0.1.md) - MVP 实施计划

## 快速开始（开发中）

```bash
cd backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000
```

打开 http://localhost:8000

## 作者

- **PM**: 🍒 樱桃（Hermes Agent 猫娘助手）
- **工程师**: Claude Code (glm-5.2)
- **Boss**: 李航宇（Master）
