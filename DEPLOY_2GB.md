# 🚀 2GB 内存服务器部署指南

## 服务器配置

- **CPU**: 2 核 ✅
- **内存**: 2GB ⚠️（需要优化）
- **硬盘**: 50GB SSD ✅
- **地域**: 新加坡 ✅（无需备案）
- **系统**: OpenClaw (Clawbot) - 应该是 Linux 系统

---

## 优化后的部署方案

由于内存只有 2GB，我们做了以下优化：

### ✅ 已优化的配置

1. **移除了独立的 Nginx 容器** - 使用前端内置的 Nginx
2. **简化了 Docker 网络** - 减少内存占用
3. **优化了数据卷映射** - 简化目录结构

### 📦 部署步骤

#### 1️⃣ SSH 登录服务器

```bash
ssh root@你的服务器 IP
```

#### 2️⃣ 检查系统信息

```bash
# 查看系统版本
cat /etc/os-release

# 查看内存
free -h

# 查看磁盘
df -h
```

#### 3️⃣ 安装 Docker

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker（使用官方脚本）
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# 验证安装
docker --version
docker-compose --version
```

#### 4️⃣ 上传代码

**方法 A：使用 Git（推荐）**

```bash
# 安装 Git
apt install git -y

# 克隆代码
cd /opt
git clone <你的仓库地址> ai-teaching
cd ai-teaching
```

**方法 B：使用 SCP 上传**

在本地电脑执行：
```powershell
scp -r e:\AI-Educator root@你的服务器 IP:/opt/ai-teaching
```

#### 5️⃣ 配置应用

```bash
cd /opt/ai-teaching

# 创建数据目录
mkdir -p uploads data

# 复制生产配置
cp backend/config.production.json backend/config.json

# 编辑配置
nano backend/config.json
```

**必须修改的配置项**：
```json
{
  "app": {
    "debug": false  // 生产环境必须关闭 debug
  },
  "api": {
    "cors_origins": [
      "http://你的服务器 IP"  // 改为你的服务器 IP
    ]
  },
  "jwt": {
    "secret_key": "生成一个随机字符串"  // 必须修改
  }
}
```

生成随机字符串的方法：
```bash
# 生成随机字符串
openssl rand -hex 32
```

#### 6️⃣ 启动服务

```bash
cd /opt/ai-teaching

# 启动 Docker 服务
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

按 `Ctrl+C` 退出日志查看。

#### 7️⃣ 检查服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看内存使用
docker stats --no-stream
```

#### 8️⃣ 访问应用

在浏览器打开：
```
http://你的服务器 IP
```

---

## 内存优化建议

### 1. 添加 Swap 交换空间（重要！）

2GB 内存建议添加 2GB Swap：

```bash
# 创建 Swap 文件
dd if=/dev/zero of=/swapfile bs=1M count=2048

# 设置权限
chmod 600 /swapfile

# 格式化为 Swap
mkswap /swapfile

# 启用 Swap
swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 验证
free -h
```

### 2. 限制 Docker 内存使用

创建或修改 `/etc/docker/daemon.json`：

```bash
nano /etc/docker/daemon.json
```

添加：
```json
{
  "default-shm-size": "128m"
}
```

重启 Docker：
```bash
systemctl restart docker
```

### 3. 关闭不必要的服务

```bash
# 查看运行的服务
systemctl list-units --type=service --state=running

# 关闭不需要的服务（根据实际系统）
systemctl stop 不需要的服务
systemctl disable 不需要的服务
```

### 4. 监控系统资源

```bash
# 安装监控工具
apt install htop -y

# 监控资源使用
htop
```

---

## 常见问题解决

### 问题 1：内存不足

**症状**：容器频繁重启或无法启动

**解决方案**：
```bash
# 1. 添加 Swap（见上文）

# 2. 查看内存使用
docker stats

# 3. 停止不需要的容器
docker-compose down

# 4. 清理 Docker 资源
docker system prune -a
```

### 问题 2：容器启动失败

**症状**：`docker-compose up -d` 报错

**解决方案**：
```bash
# 查看详细日志
docker-compose logs

# 检查 Docker 状态
systemctl status docker

# 重启 Docker
systemctl restart docker
```

### 问题 3：无法访问

**症状**：浏览器无法打开页面

**解决方案**：
```bash
# 1. 检查防火墙
ufw status
ufw allow 80/tcp
ufw allow 443/tcp

# 2. 检查端口占用
netstat -tulpn | grep :80

# 3. 测试后端 API
curl http://localhost:8000/
curl http://localhost:8000/health

# 4. 查看容器日志
docker-compose logs backend
docker-compose logs frontend
```

### 问题 4：系统不是 Linux

**症状**：Docker 安装命令不兼容

**解决方案**：

如果是 Windows Server：
```powershell
# 使用 Docker Desktop for Windows
# 或者使用传统部署方案
```

---

## 性能监控

### 实时监控

```bash
# 安装监控工具
apt install htop iotop -y

# 监控 CPU 和内存
htop

# 监控磁盘 IO
iotop
```

### Docker 资源监控

```bash
# 实时查看容器资源使用
docker stats

# 查看容器详细信息
docker inspect ai-teaching-backend
docker inspect ai-teaching-frontend
```

### 日志管理

```bash
# 查看日志
docker-compose logs -f

# 查看最近 100 行
docker-compose logs --tail=100

# 清理日志
docker-compose logs --tail=0
```

---

## 定期维护

### 每周

```bash
# 清理未使用的 Docker 资源
docker system prune -f

# 更新系统包
apt update && apt upgrade -y
```

### 每月

```bash
# 重启服务（释放内存）
cd /opt/ai-teaching
docker-compose restart

# 检查磁盘空间
df -h

# 检查日志大小
du -sh /var/log/*
```

### 备份

```bash
# 备份数据库
cd /opt/ai-teaching
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# 备份到本地
scp root@你的服务器 IP:/opt/ai-teaching/backup-*.tar.gz ./
```

---

## 升级配置（可选）

如果后续发现 2GB 内存不够用：

### 方案 1：增加内存

联系云服务商升级到 4GB 内存

### 方案 2：使用外部数据库

使用云数据库服务（如阿里云 RDS），减少服务器内存占用

### 方案 3：优化应用

- 减少并发连接数
- 优化数据库查询
- 使用缓存

---

## 检查清单

部署完成后请检查：

- [ ] Docker 安装成功
- [ ] 容器正常运行（`docker-compose ps`）
- [ ] 可以通过 IP 访问
- [ ] Swap 已启用（`free -h`）
- [ ] 防火墙已配置
- [ ] API 密钥已修改
- [ ] CORS 配置正确
- [ ] 数据库正常读写

---

## 性能基准

**正常情况下的资源使用**：
- 空闲时内存：~800MB
- 运行时内存：~1.2-1.5GB
- CPU 使用率：< 20%

**如果超过这些值**，需要检查是否有问题。

---

## 联系支持

如有问题，请查看：
- 系统日志：`journalctl -xe`
- Docker 日志：`docker-compose logs -f`
- 应用日志：查看容器内日志

祝部署顺利！🎉
