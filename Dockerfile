# k8s-quest/Dockerfile
# 🍒 K8s Quest MVP v0.1 — 单容器全栈部署
# 构建好的镜像同时包含 FastAPI 后端 + 前端静态文件

FROM python:3.11-slim

# 设置时区（日志时间戳对得上）
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 系统依赖（最小集）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 层缓存：代码改了不重装依赖）
COPY backend/pyproject.toml /app/
COPY backend/ /app/backend_tmp/
RUN pip install --no-cache-dir -e /app/backend_tmp

# 拷贝应用代码
COPY backend/app /app/app
COPY frontend /app/frontend

# 清理临时目录
RUN rm -rf /app/backend_tmp

# 健康检查（容器自检）
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

EXPOSE 8000

# 生产配置：2 worker + preload 省内存 + proxy-headers（反代场景）
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--preload", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
