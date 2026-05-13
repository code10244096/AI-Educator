@echo off
echo ========================================
echo AI 教学助手系统 - 快速启动
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [1/4] 配置后端环境...
cd backend

if not exist .env (
    copy .env.example .env
    echo [提示] 请编辑 backend\.env 配置 API 密钥
)

if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

echo 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo [2/4] 配置前端环境...
cd ..\frontend

if not exist node_modules (
    echo 安装前端依赖...
    call npm install
)

echo.
echo ========================================
echo 环境配置完成！
echo ========================================
echo.
echo 启动方式选择:
echo   1. 使用 Docker（推荐）
echo   2. 本地开发模式
echo.
set /p choice="请选择 (1/2): "

if "%choice%"=="1" (
    echo.
    echo 启动 Docker 服务...
    cd ..
    docker-compose up -d
    echo.
    echo 服务已启动！
    echo 前端：http://localhost:3000
    echo 后端：http://localhost:8000
    echo API 文档：http://localhost:8000/docs
) else (
    echo.
    echo 正在启动本地开发服务...
    echo.
    echo 启动后端...
    start cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    
    timeout /t 3 /nobreak >nul
    
    echo 启动前端...
    start cmd /k "cd frontend && npm run dev"
    
    echo.
    echo 服务已启动！
    echo 前端：http://localhost:3000
    echo 后端：http://localhost:8000
    echo.
    echo 按任意键退出...
)

pause >nul
