#!/bin/bash

echo "========================================"
echo "AI 教学助手系统 - 快速启动"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.11+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "[错误] 未检测到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "[1/4] 配置后端环境..."
cd backend

if [ ! -f .env ]; then
    cp .env.example .env
    echo "[提示] 请编辑 backend/.env 配置 API 密钥"
fi

if [ ! -d venv ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -r requirements.txt -q

echo "[2/4] 配置前端环境..."
cd ../frontend

if [ ! -d node_modules ]; then
    echo "安装前端依赖..."
    npm install
fi

echo ""
echo "========================================"
echo "环境配置完成！"
echo "========================================"
echo ""
echo "启动方式选择:"
echo "  1. 使用 Docker（推荐）"
echo "  2. 本地开发模式"
echo ""
read -p "请选择 (1/2): " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "启动 Docker 服务..."
    cd ..
    docker-compose up -d
    echo ""
    echo "服务已启动！"
    echo "前端：http://localhost:3000"
    echo "后端：http://localhost:8000"
    echo "API 文档：http://localhost:8000/docs"
else
    echo ""
    echo "正在启动本地开发服务..."
    echo ""
    echo "启动后端..."
    cd backend
    source venv/bin/activate
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    
    sleep 3
    
    echo "启动前端..."
    cd ../frontend
    npm run dev &
    
    echo ""
    echo "服务已启动！"
    echo "前端：http://localhost:3000"
    echo "后端：http://localhost:8000"
    echo ""
    echo "按 Ctrl+C 停止所有服务"
    wait
fi
