# k8s-quest/Dockerfile
# K8s 实战学堂 - 单容器全栈部署 (v2.0)
# 构建: docker build -t k8s-quest:v2 .
# 运行: docker run -d --name k8s-quest -p 8000:8000 k8s-quest:v2

FROM python:3.11-slim

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 系统依赖（curl + kubectl for 集群模式）
# 注意：官方 apt 源 apt.kubernetes.io/kubernetes-xenial 已下架（404），
#       改用官方推荐的二进制直装方式，兼容 amd64/arm64，不依赖 apt 仓库。
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && ARCH="$(dpkg --print-architecture)" \
    && curl -fsSL "https://dl.k8s.io/release/v1.31.0/bin/linux/${ARCH}/kubectl" -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && rm -rf /var/lib/apt/lists/*

# 保持与本地开发一致的目录结构，使 main.py 中的路径解析正确
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

WORKDIR /app/backend

# 安装依赖
RUN pip install --no-cache-dir -e .

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--preload", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
