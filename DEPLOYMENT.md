# AI 教学助手 - 云服务器部署指南

## 📋 目录

- [方案一：Docker 部署（推荐）](#方案一 docker-部署推荐)
- [方案二：传统部署](#方案二传统部署)
- [方案三：Vercel + 云服务器混合部署](#方案三 verel--云服务器混合部署)
- [Nginx 配置](#nginx-配置)
- [HTTPS 配置](#https-配置)
- [常见问题](#常见问题)

---

## 方案一：Docker 部署（推荐）

### 前置要求

- 云服务器（Ubuntu 20.04+ 或 CentOS 7+）
- Docker 和 Docker Compose
- 域名（可选，用于访问）

### 1. 服务器环境准备

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# sudo yum update -y  # CentOS/RHEL

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 2. 创建 Docker 配置文件

#### docker-compose.yml

```yaml
version: '3.8'

services:
  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai-teaching-backend
    restart: always
    environment:
      - ENV=production
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/data:/app/data
    networks:
      - app-network
    expose:
      - "8000"

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_BASE_URL=/api
    container_name: ai-teaching-frontend
    restart: always
    depends_on:
      - backend
    networks:
      - app-network
    expose:
      - "80"

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: ai-teaching-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

#### backend/Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p uploads data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### frontend/Dockerfile

```dockerfile
# 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app

# 复制 package.json
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建参数
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### frontend/nginx.conf

```nginx
server {
    listen 80;
    server_name localhost;
    
    root /usr/share/nginx/html;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 缓存静态资源
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 3. 更新后端配置

创建 `backend/config.production.json`:

```json
{
  "app": {
    "name": "AI 教学助手",
    "version": "1.0.0",
    "debug": false
  },
  "api": {
    "prefix": "/api",
    "cors_origins": [
      "http://your-domain.com",
      "https://your-domain.com"
    ]
  },
  "database": {
    "url": "sqlite+aiosqlite:///./data/teaching_assistant.db"
  },
  "ai": {
    "api_key": "your-production-api-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-model/v1",
    "ocr_model": "qwen3-vl-235b-a22b-thinking",
    "grader_model": "qwen3.5-27b",
    "lessonplan_model": "qwen3.5-27b"
  },
  "upload": {
    "dir": "./uploads",
    "max_file_size": 10485760,
    "allowed_extensions": ["jpg", "jpeg", "png", "gif"]
  },
  "jwt": {
    "secret_key": "CHANGE-THIS-TO-A-STRONG-SECRET-KEY-IN-PRODUCTION",
    "algorithm": "HS256",
    "access_token_expire_minutes": 30
  }
}
```

### 4. 部署到服务器

```bash
# 1. 上传代码到服务器
scp -r e:\AI-Educator root@your-server-ip:/opt/ai-teaching

# 2. SSH 登录服务器
ssh root@your-server-ip

# 3. 进入项目目录
cd /opt/ai-teaching

# 4. 更新后端配置为生产环境
cd backend
cp config.json config.json.backup
cp config.production.json config.json

# 5. 返回项目根目录
cd ..

# 6. 创建 Nginx 配置目录
mkdir -p nginx/ssl

# 7. 启动服务
docker-compose up -d

# 8. 查看日志
docker-compose logs -f
```

### 5. 配置域名（可选）

在域名服务商处添加 A 记录：
```
@    A    你的服务器 IP
www  A    你的服务器 IP
```

---

## 方案二：传统部署

### 1. 服务器环境准备

```bash
# 安装 Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 Nginx
sudo apt install nginx -y

# 安装 Git
sudo apt install git -y
```

### 2. 克隆代码

```bash
cd /opt
sudo git clone <your-repo-url> ai-teaching
sudo chown -R $USER:$USER ai-teaching
cd ai-teaching
```

### 3. 部署后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 更新配置
cp config.json config.json.backup
# 编辑 config.json，修改为生产环境配置

# 创建 systemd 服务
sudo nano /etc/systemd/system/ai-teaching-backend.service
```

systemd 服务配置：

```ini
[Unit]
Description=AI Teaching Assistant Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-teaching/backend
Environment="PATH=/opt/ai-teaching/backend/venv/bin"
ExecStart=/opt/ai-teaching/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-teaching-backend
sudo systemctl start ai-teaching-backend
sudo systemctl status ai-teaching-backend
```

### 4. 部署前端

```bash
cd /opt/ai-teaching/frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 复制构建产物到 Nginx 目录
sudo cp -r dist/* /var/www/html/
```

### 5. 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/ai-teaching
```

Nginx 配置：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    root /var/www/html;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 反向代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/ai-teaching /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 方案三：Vercel + 云服务器混合部署

### 前端部署到 Vercel（免费 CDN）

1. 访问 [Vercel](https://vercel.com)
2. 连接 GitHub 仓库
3. 配置构建设置：
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. 设置环境变量：
   - `VITE_API_BASE_URL`: `https://your-server-ip/api`
5. 部署

### 后端部署到云服务器

参考方案二的后端部署步骤，只部署后端服务。

---

## Nginx 配置

### 完整生产配置示例

```nginx
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL 证书
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL 优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    root /var/www/html;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 反向代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 上传文件大小限制
        client_max_body_size 10M;
    }

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }
}
```

---

## HTTPS 配置

### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

Certbot 会自动配置 Nginx 的 SSL 设置。

---

## 常见问题

### 1. 跨域问题

确保后端 `config.json` 中的 `cors_origins` 包含你的域名：

```json
{
  "api": {
    "cors_origins": [
      "https://your-domain.com",
      "https://www.your-domain.com"
    ]
  }
}
```

### 2. 文件上传大小限制

Nginx 配置中添加：

```nginx
client_max_body_size 10M;
```

### 3. 数据库权限问题

```bash
sudo chown -R www-data:www-data /opt/ai-teaching/backend/data
sudo chmod -R 755 /opt/ai-teaching/backend/data
```

### 4. 服务无法启动

查看日志：

```bash
# 后端日志
sudo journalctl -u ai-teaching-backend -f

# Nginx 日志
sudo tail -f /var/log/nginx/error.log
```

### 5. 前端页面刷新 404

确保 Nginx 配置中有：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### 6. WebSocket 连接失败

确保 Nginx 配置中有 WebSocket 支持：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

---

## 快速部署脚本

创建 `deploy.sh`：

```bash
#!/bin/bash

set -e

echo "🚀 开始部署 AI 教学助手..."

# 1. 更新系统
echo "📦 更新系统..."
sudo apt update && sudo apt upgrade -y

# 2. 安装依赖
echo "📦 安装依赖..."
sudo apt install -y python3.11 python3.11-venv python3-pip nginx git

# 3. 安装 Node.js
echo " 安装 Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 4. 克隆代码
echo "📦 克隆代码..."
cd /opt
sudo git clone <your-repo-url> ai-teaching || true
sudo chown -R $USER:$USER ai-teaching
cd ai-teaching

# 5. 部署后端
echo "🔧 部署后端..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 创建 systemd 服务
sudo bash -c "cat > /etc/systemd/system/ai-teaching-backend.service << EOF
[Unit]
Description=AI Teaching Assistant Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-teaching/backend
Environment=\"PATH=/opt/ai-teaching/backend/venv/bin\"
ExecStart=/opt/ai-teaching/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable ai-teaching-backend
sudo systemctl start ai-teaching-backend

# 6. 部署前端
echo "🔧 部署前端..."
cd ../frontend
npm install
npm run build
sudo cp -r dist/* /var/www/html/

# 7. 配置 Nginx
echo "🔧 配置 Nginx..."
sudo bash -c "cat > /etc/nginx/sites-available/ai-teaching << 'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/html;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control \"public, immutable\";
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        client_max_body_size 10M;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF"

sudo ln -s /etc/nginx/sites-available/ai-teaching /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 8. 设置权限
echo "🔒 设置权限..."
sudo chown -R www-data:www-data /opt/ai-teaching/backend/data
sudo chmod -R 755 /opt/ai-teaching/backend/data

echo "✅ 部署完成！"
echo "🌐 访问地址：http://your-server-ip"
```

使用：

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 推荐云服务商

### 国内
- **阿里云**：https://www.aliyun.com
- **腾讯云**：https://cloud.tencent.com
- **华为云**：https://www.huaweicloud.com

### 国际
- **AWS**：https://aws.amazon.com
- **DigitalOcean**：https://www.digitalocean.com
- **Vultr**：https://www.vultr.com
- **Linode**：https://www.linode.com

### 最低配置建议
- CPU: 2 核
- 内存：4GB
- 硬盘：40GB
- 带宽：3Mbps+

---

## 部署后检查清单

- [ ] 后端服务运行正常
- [ ] 前端页面可以访问
- [ ] API 接口可以调用
- [ ] 文件上传功能正常
- [ ] 数据库正常读写
- [ ] HTTPS 证书配置
- [ ] 域名解析正确
- [ ] 防火墙规则配置
- [ ] 定期备份策略
- [ ] 监控告警配置

---

## 技术支持

如有问题，请查看：
- 应用日志：`docker-compose logs -f`
- Nginx 日志：`/var/log/nginx/error.log`
- 系统日志：`journalctl -xe`

祝部署顺利！🎉
