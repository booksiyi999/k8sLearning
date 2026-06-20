# 🚀 K8s Quest 部署文档

> 🍒 从本地试玩到公网生产，覆盖所有部署场景。

---

## 📋 架构概览

```
用户浏览器  ──HTTP──▶  Nginx (反代 + HTTPS)  ──▶  Uvicorn (FastAPI :8000)
                                                            │
                                                  ┌─────────┴─────────┐
                                                  │  app/main.py       │
                                                  │  ├─ /api/*  接口   │
                                                  │  └─ /      前端    │
                                                  └────────────────────┘
```

**单进程架构**：FastAPI 直接服务 API (`/api/*`) 和前端静态文件 (`/`)。
无需独立前端服务器，无需数据库，**单二进制起跑即可**。

---

## 🐳 方式一：Docker 部署（推荐，最简单）

### 1. 准备 Dockerfile

在仓库根目录创建：

```dockerfile
# k8s-quest/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 装依赖（利用 Docker 层缓存）
COPY backend/pyproject.toml backend/ ./
RUN pip install --no-cache-dir -e .

# 拷代码
COPY backend/app ./app
COPY frontend ./frontend

EXPOSE 8000

# 生产用多 worker，--preload 省内存
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 2. 构建并运行

```bash
cd ~/k8s-quest

# 构建
docker build -t k8s-quest:0.1 .

# 跑起来（前台，方便看日志）
docker run --rm -p 8000:8000 k8s-quest:0.1

# 或后台常驻
docker run -d --name k8s-quest --restart unless-stopped \
  -p 8000:8000 k8s-quest:0.1
```

### 3. 验证

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}

# 浏览器打开 http://服务器IP:8000
```

### 4. 查看/管理

```bash
docker logs -f k8s-quest      # 看日志
docker restart k8s-quest      # 重启
docker stop k8s-quest         # 停止
docker pull <new> && docker ...  # 更新镜像
```

---

## 🖥️ 方式二：Systemd 服务（Linux VPS 推荐）

**适用**：Master 的 VPS，开机自启 + 崩溃自动重启。

### 1. 创建专用用户和目录

```bash
sudo useradd -r -s /bin/false k8squest || true
sudo mkdir -p /opt/k8s-quest
sudo chown admin:admin /opt/k8s-quest

# 拉代码
cd /opt/k8s-quest
git clone https://github.com/lhy9816/k8s-quest.git .
```

### 2. 装依赖（用 venv）

```bash
cd /opt/k8s-quest/backend
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
```

### 3. 写 systemd unit

```bash
sudo tee /etc/systemd/system/k8s-quest.service > /dev/null <<'EOF'
[Unit]
Description=K8s Quest Learning App
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/opt/k8s-quest/backend
ExecStart=/opt/k8s-quest/backend/.venv/bin/uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --proxy-headers \
    --forwarded-allow-ips='*'
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
```

### 4. 启用并启动

```bash
sudo systemctl daemon-reload
sudo systemctl enable k8s-quest       # 开机自启
sudo systemctl start k8s-quest         # 启动
sudo systemctl status k8s-quest        # 看状态
sudo journalctl -u k8s-quest -f        # 实时日志
```

---

## 🌐 方式三：Nginx 反向代理 + HTTPS（公网生产）

**适用**：Master 想用域名 + HTTPS 公网访问，比如 `k8s-quest.lhy9816.com`。

### 1. 配置 Nginx

```bash
sudo tee /etc/nginx/sites-available/k8s-quest > /dev/null <<'EOF'
server {
    listen 80;
    server_name k8s-quest.lhy9816.com;   # ← 改成你的域名

    # WebSocket 支持（终端要长连接）
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    client_max_body_size 10M;
}
EOF

sudo ln -sf /etc/nginx/sites-available/k8s-quest /etc/nginx/sites-enabled/
sudo nginx -t              # 测试配置
sudo systemctl reload nginx
```

### 2. 上 HTTPS（用 Let's Encrypt，免费）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d k8s-quest.lhy9816.com
# 按提示走，自动续期也配好了
```

### 3. 配置防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 4. 验证

```bash
curl https://k8s-quest.lhy9816.com/api/health
# {"status":"ok"}

# 浏览器打开 https://k8s-quest.lhy9816.com
```

---

## 🧪 方式四：本地开发（最简单，秒级试玩）

```bash
cd ~/k8s-quest/backend
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 开发热重载（改代码自动重启）
.venv/bin/uvicorn app.main:app --reload --port 8000

# 跑测试
.venv/bin/pytest -v
```

浏览器 → http://localhost:8000

---

## ✅ 部署后验证清单

部署完后，依次跑这些命令确认都 OK：

```bash
# 1. 健康检查
curl -s https://你的域名/api/health | jq
# 期望：{"status":"ok"}

# 2. 关卡列表
curl -s https://你的域名/api/levels | jq '.levels[0] | keys'
# 期望：["chapter","description","id","title"]

# 3. 提交答案（应该 ok=true）
curl -s -X POST https://你的域名/api/check \
  -H "Content-Type: application/json" \
  -d '{
    "level_id": "Q1.1",
    "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n    - name: nginx\n      image: nginx:1.25"
  }' | jq '.ok'
# 期望：true

# 4. 提交错误答案（应该 ok=false + 有 hints）
curl -s -X POST https://你的域名/api/check \
  -H "Content-Type: application/json" \
  -d '{"level_id":"Q1.1","user_yaml":"invalid yaml :::"}' | jq '.ok'
# 期望：false
```

---

## 🔧 运维与监控

### 日志

```bash
# Docker
docker logs -f k8s-quest
docker logs --tail 100 k8s-quest

# Systemd
sudo journalctl -u k8s-quest -f
sudo journalctl -u k8s-quest --since "1 hour ago"
```

### 更新版本

```bash
# Docker
cd ~/k8s-quest
git pull
docker build -t k8s-quest:0.2 .
docker stop k8s-quest && docker rm k8s-quest
docker run -d --name k8s-quest --restart unless-stopped -p 8000:8000 k8s-quest:0.2

# Systemd
cd /opt/k8s-quest && git pull
sudo systemctl restart k8s-quest
```

### 备份

> 当前 v0.1 无数据库，**只需备份仓库**（已在 GitHub 私仓）。
> 未来加用户进度后，需要加 PostgreSQL/SQLite 备份。

---

## ⚙️ 生产环境调优

### uvicorn worker 数量

公式：`workers = 2 * CPU 核数 + 1`

```bash
# 查看 CPU 核数
nproc

# 改 systemd 里的 --workers 参数，比如 4 核就设 9
```

### 用 Gunicorn + Uvicorn worker（生产更稳）

```bash
.venv/bin/pip install gunicorn
```

```bash
# systemd ExecStart 改为：
ExecStart=/opt/k8s-quest/backend/.venv/bin/gunicorn \
    app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    --timeout 120
```

### 前端缓存（Nginx 层加速）

在 Nginx server 块加：

```nginx
location ~* \.(js|css|png|jpg|woff2?)$ {
    proxy_pass http://127.0.0.1:8000;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

---

## 🐛 常见问题排查

### Q1: 启动报错 `Address already in use`

```bash
# 看谁占了 8000
sudo lsof -i :8000
# 干掉它
sudo kill -9 <PID>
```

### Q2: 浏览器访问白屏

```bash
# 1. 检查后端是否在跑
curl http://localhost:8000/api/health

# 2. 检查前端目录是否存在
ls ~/k8s-quest/frontend/index.html
# 如果不存在，重新拉代码：git pull

# 3. 看 uvicorn 日志有没有 404
sudo journalctl -u k8s-quest -f
```

### Q3: 公网访问不到

```bash
# 1. 安全组 / 防火墙放行 80/443
sudo ufw status

# DNS 解析对不对
dig k8s-quest.lhy9816.com +short

# 2. Nginx 配置对不对
sudo nginx -t

# 3. HTTPS 证书是否有效
curl -vI https://k8s-quest.lhy9816.com 2>&1 | grep -E "(expire|subject)"
```

### Q4: systemd 服务起不来

```bash
sudo systemctl status k8s-quest
sudo journalctl -u k8s-quest -n 50 --no-pager

# 常见原因：
# - venv 路径不对 → 检查 ExecStart 的路径
# - 工作目录权限 → chown -R admin:admin /opt/k8s-quest
# - 端口被占 → 改 port 或 kill 老进程
```

### Q5: Docker 构建慢

```bash
# 配国内镜像源
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com"
  ]
}
EOF
sudo systemctl restart docker
```

---

## 🚨 安全清单（公网部署必读）

- [ ] **改 SSH 端口**（默认 22 容易被扫）
- [ ] **禁 root SSH 登录**（`PermitRootLogin no`）
- [ ] **UFW 防火墙**只开 22/80/443
- [ ] **HTTPS 证书**自动续期（`certbot renew --dry-run` 测试）
- [ ] **定期更新系统**：`sudo apt update && sudo apt upgrade`
- [ ] **Fail2ban** 挡暴力破解：`sudo apt install fail2ban`
- [ ] **限制 CORS**（生产环境别用 `*`）—— 改 `backend/app/main.py`
- [ ] **API 限流**（防刷）—— 后续加 `slowapi` 中间件

---

## 📞 樱桃的快速支持

Master 如果要部署，跟樱桃说一声，樱桃可以：

1. **直接帮你部署**：你说"部署到 VPS"，樱桃会：
   - SSH 上你的 VPS（需要凭证）
   - 配置 Docker 或 systemd
   - 上 HTTPS
   - 跑完整验证
   - 给你域名链接

2. **加监控**：接 UptimeRobot / 飞书机器人，挂了自动通知

3. **绑域名**：帮你做 DNS 解析 + HTTPS 证书

3. **加功能**：例如多用户、进度保存、更多关卡

---

**当前部署状态**: 🚧 MVP v0.1 已通过本地验证，**生产部署文档已就绪**。

🍒 樱桃 2026-06-20
