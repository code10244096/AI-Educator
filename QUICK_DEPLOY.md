# 🚀 快速部署指南

## 三种部署方案

### 方案一：Docker 部署（⭐⭐⭐⭐⭐ 强烈推荐）

**优点**：
- ✅ 一键部署，简单快速
- ✅ 环境隔离，无依赖冲突
- ✅ 自动重启，稳定可靠
- ✅ 易于更新和维护

**步骤**：

1. **准备云服务器**
   - 系统：Ubuntu 20.04+ 或 CentOS 7+
   - 配置：2 核 CPU / 4GB 内存 / 40GB 硬盘
   - 带宽：3Mbps+

2. **上传代码到服务器**
   ```bash
   # 在本地电脑执行（Windows PowerShell）
   scp -r e:\AI-Educator root@你的服务器 IP:/opt/
   ```

3. **SSH 登录服务器**
   ```bash
   ssh root@你的服务器 IP
   cd /opt/AI-Educator
   ```

4. **执行一键部署脚本**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

5. **配置 API 密钥**
   ```bash
   cd /opt/AI-Educator/backend
   nano config.json
   # 修改 api_key 为你的实际密钥
   # 修改 cors_origins 为你的域名或服务器 IP
   ```

6. **重启服务**
   ```bash
   cd /opt/AI-Educator
   docker-compose restart backend
   ```

7. **访问应用**
   ```
   http://你的服务器 IP
   ```

---

### 方案二：手动 Docker 部署

如果不想用脚本，可以手动执行：

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 2. 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. 进入项目目录
cd /opt/AI-Educator

# 4. 修改配置
cp backend/config.production.json backend/config.json
nano backend/config.json
# 修改 api_key 和 cors_origins

# 5. 创建 Nginx 目录
mkdir -p nginx/ssl

# 6. 启动服务
docker-compose up -d

# 7. 查看日志
docker-compose logs -f
```

---

### 方案三：传统部署（不推荐）

详细步骤请参考 [DEPLOYMENT.md](DEPLOYMENT.md) 中的"方案二：传统部署"

---

## 🎯 配置域名（可选）

### 1. 在域名服务商添加解析

```
类型：A
主机记录：@
记录值：你的服务器 IP
TTL：600

类型：A
主机记录：www
记录值：你的服务器 IP
TTL：600
```

### 2. 修改后端配置

```bash
cd /opt/AI-Educator/backend
nano config.json
```

修改 `cors_origins`：
```json
{
  "api": {
    "cors_origins": [
      "http://your-domain.com",
      "https://your-domain.com",
      "http://www.your-domain.com",
      "https://www.your-domain.com"
    ]
  }
}
```

### 3. 重启服务

```bash
cd /opt/AI-Educator
docker-compose restart backend
```

---

## 🔒 配置 HTTPS（强烈推荐）

使用 Let's Encrypt 免费证书：

```bash
# 1. 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 2. 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 3. 自动续期
sudo crontab -e
# 添加：0 3 * * * certbot renew --quiet
```

---

##  服务管理命令

```bash
# 进入项目目录
cd /opt/AI-Educator

# 查看服务状态
docker-compose ps

# 查看所有服务日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 查看 Nginx 日志
docker-compose logs -f nginx

# 停止服务
docker-compose down

# 启动服务
docker-compose up -d

# 重启服务
docker-compose restart

# 更新服务
git pull  # 如果有代码更新
docker-compose pull
docker-compose up -d

# 重建服务（会删除容器）
docker-compose down
docker-compose up -d --build
```

---

## 🔍 故障排查

### 1. 服务无法启动

```bash
# 查看日志
docker-compose logs

# 检查端口占用
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :8000
```

### 2. 页面无法访问

```bash
# 检查防火墙
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 检查 Docker 容器
docker-compose ps

# 测试后端 API
curl http://localhost:8000/
curl http://localhost:8000/health
```

### 3. API 调用失败

```bash
# 检查后端日志
docker-compose logs backend

# 检查 CORS 配置
cat /opt/AI-Educator/backend/config.json

# 测试 API
curl http://localhost:8000/api/
```

### 4. 文件上传失败

```bash
# 检查目录权限
docker-compose exec backend ls -la uploads/

# 修复权限
docker-compose exec backend chmod 755 uploads/
```

---

##  云服务器推荐

### 国内（需要备案）
- **阿里云**：https://www.aliyun.com
  - 入门款：约 ¥99/月
- **腾讯云**：https://cloud.tencent.com
  - 入门款：约 ¥88/月

### 国际（无需备案）
- **DigitalOcean**：https://www.digitalocean.com
  - 入门款：$6/月
- **Vultr**：https://www.vultr.com
  - 入门款：$5/月
- **Linode**：https://www.linode.com
  - 入门款：$5/月

### 最低配置建议
- CPU: 2 核
- 内存：4GB
- 硬盘：40GB SSD
- 带宽：3Mbps+

---

## ✅ 部署检查清单

- [ ] 云服务器已购买
- [ ] SSH 可以登录服务器
- [ ] 代码已上传到服务器
- [ ] Docker 和 Docker Compose 已安装
- [ ] 部署脚本已执行
- [ ] API 密钥已配置
- [ ] CORS 设置已修改
- [ ] 服务状态正常（docker-compose ps）
- [ ] 可以通过 IP 访问
- [ ] 域名解析已配置（如有域名）
- [ ] HTTPS 证书已配置（如有域名）
- [ ] 防火墙规则已配置

---

## 🎉 完成！

部署成功后，所有人都可以通过以下地址访问：

- **有域名**：https://your-domain.com
- **无域名**：http://你的服务器 IP

**下一步**：
1. 测试所有功能（作业批改、错题本、教案生成）
2. 配置监控和告警
3. 设置定期备份
4. 优化性能

---

## 📞 技术支持

如有问题，请查看：
- 完整部署文档：[DEPLOYMENT.md](DEPLOYMENT.md)
- 应用日志：`docker-compose logs -f`
- Nginx 日志：`docker-compose logs nginx`
- 系统日志：`journalctl -xe`

祝部署顺利！🎊
