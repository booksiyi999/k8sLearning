#!/bin/bash
# 🍒 K8s Quest 一键安装脚本
# 用法: ./setup.sh [--docker | --dev]
# --docker: Docker 部署（默认）
# --dev: 本地开发模式

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "🍒 K8s Quest 一键安装"
echo "========================"

MODE="${1:---docker}"

if [ "$MODE" = "--docker" ]; then
    # Docker 部署
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker 未安装，请先安装 Docker"
        echo "   或者使用本地开发模式: ./setup.sh --dev"
        exit 1
    fi

    echo "📦 构建 Docker 镜像..."
    docker build -t k8s-quest:0.3 .

    # 停止旧容器（如果有）
    docker rm -f k8s-quest 2>/dev/null || true

    echo "🚀 启动容器..."
    docker run -d --name k8s-quest --restart unless-stopped \
        -p 8000:8000 k8s-quest:0.3

    echo "⏳ 等待服务启动..."
    sleep 3

    if curl -fsS http://localhost:8000/api/health &> /dev/null; then
        echo ""
        echo "✅ 安装成功！"
        echo "🌐 浏览器打开: http://localhost:8000"
        echo ""
        echo "管理命令:"
        echo "  查看日志: docker logs -f k8s-quest"
        echo "  停止:     docker stop k8s-quest"
        echo "  重启:     docker restart k8s-quest"
    else
        echo "❌ 服务启动失败，查看日志:"
        docker logs k8s-quest
        exit 1
    fi

elif [ "$MODE" = "--dev" ]; then
    # 本地开发模式
    BACKEND_DIR="$PROJECT_DIR/backend"

    if ! command -v python3.11 &> /dev/null; then
        echo "❌ Python 3.11 未安装"
        echo "   安装: sudo apt install python3.11 python3.11-venv"
        exit 1
    fi

    echo "🐍 创建 Python 虚拟环境..."
    cd "$BACKEND_DIR"
    python3.11 -m venv .venv

    echo "📦 安装依赖..."
    .venv/bin/pip install -e ".[dev]" -q

    echo "🧪 运行测试..."
    .venv/bin/pytest -q

    echo ""
    echo "✅ 安装成功！"
    echo "🚀 启动开发服务器: cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000"
    echo "🌐 浏览器打开: http://localhost:8000"

else
    echo "用法: ./setup.sh [--docker | --dev]"
    echo "  --docker  Docker 部署（默认）"
    echo "  --dev     本地开发模式"
    exit 1
fi
