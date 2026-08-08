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
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/kubernetes-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update && apt-get install -y --no-install-recommends kubectl \
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
