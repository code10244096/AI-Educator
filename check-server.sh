#!/bin/bash

echo " 开始检查服务器环境..."
echo ""

# 检查系统
echo "📋 系统信息:"
echo "============"
if [ -f /etc/os-release ]; then
    cat /etc/os-release | grep -E "PRETTY_NAME|ID="
else
    echo "无法识别系统版本"
fi
echo ""

# 检查 CPU
echo "💻 CPU 信息:"
echo "=========="
if command -v lscpu &> /dev/null; then
    CPU_CORES=$(lscpu | grep "CPU(s):" | awk '{print $2}')
    echo "CPU 核心数：$CPU_CORES"
    if [ "$CPU_CORES" -ge 2 ]; then
        echo "✅ CPU 核心数满足要求（2 核）"
    else
        echo "⚠️  CPU 核心数不足（建议 2 核以上）"
    fi
else
    echo "无法获取 CPU 信息"
fi
echo ""

# 检查内存
echo " 内存信息:"
echo "=========="
if command -v free &> /dev/null; then
    free -h | grep -E "^Mem:"
    TOTAL_MEM=$(free | grep -E "^Mem:" | awk '{print $2}')
    if [ "$TOTAL_MEM" -ge 2000000 ]; then
        echo "✅ 内存满足要求（2GB+）"
    else
        echo "⚠️  内存较小（建议 2GB 以上）"
    fi
else
    echo "无法获取内存信息"
fi
echo ""

# 检查磁盘
echo "💾 磁盘信息:"
echo "=========="
if command -v df &> /dev/null; then
    df -h / | tail -1 | awk '{print "总空间："$2", 已用："$3", 可用："$4", 使用率："$5}'
    AVAILABLE=$(df / | tail -1 | awk '{print $4}')
    if [ "$AVAILABLE" -gt 10000000 ]; then
        echo "✅ 磁盘空间充足（10GB+）"
    else
        echo "⚠️  磁盘空间不足（建议 10GB 以上）"
    fi
else
    echo "无法获取磁盘信息"
fi
echo ""

# 检查 Docker
echo "🐳 Docker 状态:"
echo "============"
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo "Docker 已安装：$docker_version"
    echo "✅ Docker 检查通过"
else
    echo " Docker 未安装"
    echo "安装命令：curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
fi
echo ""

# 检查 Docker Compose
echo " Docker Compose 状态:"
echo "===================="
if command -v docker-compose &> /dev/null; then
    compose_version=$(docker-compose --version)
    echo "Docker Compose 已安装：$compose_version"
    echo "✅ Docker Compose 检查通过"
else
    echo "❌ Docker Compose 未安装"
    echo "安装命令：curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose"
fi
echo ""

# 检查网络端口
echo "🌐 网络端口:"
echo "=========="
if command -v netstat &> /dev/null; then
    echo "端口 80 状态:"
    if netstat -tulpn | grep -q ":80"; then
        echo "️  端口 80 已被占用"
        netstat -tulpn | grep ":80"
    else
        echo "✅ 端口 80 可用"
    fi
    
    echo "端口 443 状态:"
    if netstat -tulpn | grep -q ":443"; then
        echo "⚠️  端口 443 已被占用"
        netstat -tulpn | grep ":443"
    else
        echo "✅ 端口 443 可用"
    fi
else
    echo "无法检查端口状态"
fi
echo ""

# 检查防火墙
echo "🔒 防火墙状态:"
echo "============"
if command -v ufw &> /dev/null; then
    ufw_status=$(ufw status | head -1)
    echo "$ufw_status"
    if echo "$ufw_status" | grep -q "active"; then
        echo "⚠️  防火墙已启用，请确保开放 80 和 443 端口"
    else
        echo "✅ 防火墙未启用（开发环境可以）"
    fi
else
    echo "未检测到 UFW 防火墙"
fi
echo ""

# 检查 Swap
echo "💾 Swap 状态:"
echo "==========="
if command -v swapon &> /dev/null; then
    if swapon --show | grep -q .; then
        echo "✅ Swap 已启用:"
        swapon --show
    else
        echo "️  Swap 未启用（2GB 内存建议启用）"
        echo "启用命令："
        echo "  dd if=/dev/zero of=/swapfile bs=1M count=2048"
        echo "  chmod 600 /swapfile"
        echo "  mkswap /swapfile"
        echo "  swapon /swapfile"
    fi
else
    echo "无法检查 Swap 状态"
fi
echo ""

# 总结
echo "📊 检查总结:"
echo "=========="
echo "如果所有检查都通过（✅），则可以开始部署！"
echo ""
echo "下一步："
echo "1. 如果 Docker 未安装，请先安装 Docker"
echo "2. 如果 Swap 未启用且内存<=2GB，建议启用 Swap"
echo "3. 上传代码到 /opt/ai-teaching 目录"
echo "4. 执行：cd /opt/ai-teaching && docker-compose up -d"
echo ""
echo "详细部署指南请查看：DEPLOY_2GB.md"
