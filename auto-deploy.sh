#!/bin/bash

# AI 教学助手 - 自动化部署脚本
# 适用于 2GB 内存服务器

set -e

echo "=========================================="
echo "AI 教学助手 - 自动化部署脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用 root 用户运行此脚本"
    exit 1
fi

# 1. 更新系统
print_info "步骤 1/10: 更新系统..."
apt update && apt upgrade -y
print_success "系统更新完成"
echo ""

# 2. 安装必要工具
print_info "步骤 2/10: 安装必要工具..."
apt install -y curl wget git vim net-tools htop
print_success "工具安装完成"
echo ""

# 3. 安装 Docker
print_info "步骤 3/10: 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    print_success "Docker 安装完成"
else
    print_warning "Docker 已安装，跳过"
fi

# 启动 Docker 服务
systemctl start docker
systemctl enable docker
print_success "Docker 服务已启动"
echo ""

# 4. 安装 Docker Compose
print_info "步骤 4/10: 安装 Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose 安装完成"
else
    print_warning "Docker Compose 已安装，跳过"
fi
echo ""

# 5. 启用 Swap（2GB 内存必须）
print_info "步骤 5/10: 配置 Swap..."
if [ ! -f /swapfile ]; then
    print_info "创建 2GB Swap 文件..."
    dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    print_success "Swap 配置完成"
else
    print_warning "Swap 已存在，跳过"
fi
echo ""

# 6. 配置防火墙
print_info "步骤 6/10: 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    print_success "防火墙配置完成"
else
    print_warning "未检测到 UFW，跳过"
fi
echo ""

# 7. 进入项目目录
print_info "步骤 7/10: 配置项目目录..."
cd /opt/ai-teaching

# 创建数据目录
mkdir -p uploads data

# 设置权限
chmod 755 uploads data
print_success "目录创建完成"
echo ""

# 8. 配置应用
print_info "步骤 8/10: 配置应用..."

# 备份原配置
if [ -f backend/config.json ]; then
    cp backend/config.json backend/config.json.backup.$(date +%Y%m%d%H%M%S)
fi

# 使用生产配置
if [ -f backend/config.production.json ]; then
    cp backend/config.production.json backend/config.json
    print_success "使用生产配置"
else
    print_error "未找到 config.production.json"
    exit 1
fi

# 生成随机 JWT 密钥
JWT_SECRET=$(openssl rand -hex 32)
print_info "生成 JWT 密钥：${JWT_SECRET:0:10}..."

# 更新配置
print_info "更新配置文件..."
sed -i "s/\"debug\": true/\"debug\": false/g" backend/config.json
sed -i "s/CHANGE-THIS-TO-A-STRONG-SECRET-KEY-IN-PRODUCTION/$JWT_SECRET/g" backend/config.json

# 更新 CORS 设置（获取本机 IP）
SERVER_IP=$(curl -s ifconfig.me)
print_info "检测到服务器 IP: $SERVER_IP"

# 创建新的 CORS 配置
cat > /tmp/cors_config.json << EOF
      "cors_origins": [
        "http://$SERVER_IP",
        "https://$SERVER_IP",
        "http://localhost:3000",
        "http://localhost:5173"
      ],
EOF

# 替换 CORS 配置（简化处理）
print_warning "请手动更新 backend/config.json 中的 cors_origins 为你的服务器 IP: $SERVER_IP"
print_warning "或使用以下命令自动替换："
echo "sed -i 's/your-domain.com/$SERVER_IP/g' backend/config.json"
echo ""

print_success "应用配置完成"
echo ""

# 9. 启动 Docker 服务
print_info "步骤 9/10: 启动 Docker 服务..."
docker-compose up -d

# 等待服务启动
print_info "等待服务启动（约 30 秒）..."
sleep 30

# 检查服务状态
print_info "检查服务状态..."
docker-compose ps
echo ""

# 10. 查看日志
print_info "步骤 10/10: 查看服务日志..."
docker-compose logs --tail=20
echo ""

# 部署完成
echo "=========================================="
print_success "部署完成！"
echo "=========================================="
echo ""

# 显示访问信息
print_info "访问地址："
echo "  http://$SERVER_IP"
echo "  http://$(curl -s ifconfig.me)"
echo ""

# 显示常用命令
print_info "常用命令："
echo "  查看服务状态：cd /opt/ai-teaching && docker-compose ps"
echo "  查看日志：cd /opt/ai-teaching && docker-compose logs -f"
echo "  重启服务：cd /opt/ai-teaching && docker-compose restart"
echo "  停止服务：cd /opt/ai-teaching && docker-compose down"
echo "  启动服务：cd /opt/ai-teaching && docker-compose up -d"
echo ""

# 显示注意事项
print_warning "注意事项："
echo "  1. 请确保 backend/config.json 中的 cors_origins 已更新为你的服务器 IP"
echo "  2. 请确保 backend/config.json 中的 api_key 已更新为你的实际 API 密钥"
echo "  3. 建议配置域名和 HTTPS 证书"
echo "  4. 定期备份数据：tar -czf backup-$(date +%Y%m%d).tar.gz data/"
echo ""

# 显示资源使用情况
print_info "当前资源使用情况："
free -h
echo ""
df -h /
echo ""
docker stats --no-stream
echo ""

print_success "祝使用愉快！"
