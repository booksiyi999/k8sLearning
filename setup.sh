#!/bin/bash
# 🍒 K8s Quest 一键安装脚本
# 用法: ./setup.sh [--docker | --dev | --cluster]
# --docker:  Docker 部署（默认）
# --dev:     本地开发模式（模拟器）
# --cluster: 集群模式（连接真实 K8s）

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
    docker build -t k8s-quest:v2 .

    # 停止旧容器（如果有）
    docker rm -f k8s-quest 2>/dev/null || true

    echo "🚀 启动容器..."
    docker run -d --name k8s-quest --restart unless-stopped \
        -p 8000:8000 k8s-quest:v2

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

elif [ "$MODE" = "--cluster" ]; then
    # 集群模式（连接真实 K8s）
    BACKEND_DIR="$PROJECT_DIR/backend"

    if ! command -v python3.11 &> /dev/null; then
        echo "❌ Python 3.11 未安装"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl 未安装，集群模式需要 kubectl"
        echo "   安装: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    if [ -z "$KUBECONFIG" ] && [ ! -f "$HOME/.kube/config" ]; then
        echo "❌ 未找到 kubeconfig，请设置 KUBECONFIG 环境变量"
        echo "   export KUBECONFIG=/path/to/kubeconfig"
        exit 1
    fi

    echo "🐍 创建 Python 虚拟环境..."
    cd "$BACKEND_DIR"
    python3.11 -m venv .venv 2>/dev/null || true

    echo "📦 安装依赖..."
    .venv/bin/pip install -e ".[dev]" -q

    echo "🔧 验证集群连接..."
    kubectl get nodes --request-timeout=5s || {
        echo "❌ 无法连接到 K8s 集群，请检查 kubeconfig"
        exit 1
    }

    echo ""
    echo "✅ 集群模式就绪！"
    echo "🚀 启动: K8S_QUEST_MODE=cluster .venv/bin/uvicorn app.main:app --reload --port 8000"
    echo "🌐 浏览器打开: http://localhost:8000"
    echo "📖 每关有 [知识讲解] [动手练习] [集群实战] 三个 Tab"

else
    echo "用法: ./setup.sh [--docker | --dev | --cluster]"
    echo "  --docker   Docker 部署（默认）"
    echo "  --dev      本地开发模式（模拟器）"
    echo "  --cluster  集群模式（连接真实 K8s）"
    exit 1
fi
