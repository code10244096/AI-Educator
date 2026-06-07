@echo off
chcp 65001 >nul
echo ========================================
echo AI 教学助手系统 - 快速启动
echo ========================================
echo.

echo [1/3] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [2/4] 清理旧端口 (8000, 3000, 5173)...
for %%P in (8000 3000 5173) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
        taskkill /PID %%A /F >nul 2>&1
    )
)
timeout /t 2 >nul

echo [3/4] 启动后端服务...
cd backend
start "AI后端服务" cmd /k "uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo [4/4] 启动前端服务...
cd ..\frontend
start "AI前端服务" cmd /k "npm run dev"

echo.
echo ========================================
echo 服务已启动！
echo ========================================
echo 前端：http://localhost:3000
echo 后端：http://localhost:8000
echo API文档：http://localhost:8000/docs
echo.
echo 关闭终端窗口即可停止服务
echo ========================================
pause
