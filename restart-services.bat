@echo off
chcp 65001 >nul
echo ========================================
echo AI 教学助手 - 清理端口并重启服务
echo ========================================
echo.

echo [1/4] 停止占用端口的旧进程 (8000, 3000, 5173)...
for %%P in (8000 3000 5173) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
        echo   终止端口 %%P 的进程 PID=%%A
        taskkill /PID %%A /F >nul 2>&1
    )
)
timeout /t 2 >nul

echo [2/4] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    pause
    exit /b 1
)
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Node.js
    pause
    exit /b 1
)

echo [3/4] 启动后端 (端口 8000)...
cd /d "%~dp0backend"
start "AI后端-8000" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo [4/4] 启动前端 (端口 3000)...
cd /d "%~dp0frontend"
start "AI前端-3000" cmd /k "npm run dev"

echo.
echo ========================================
echo 服务已重启！
echo ========================================
echo 前端：http://localhost:3000
echo 后端：http://localhost:8000
echo 健康检查：http://localhost:8000/health
echo API文档：http://localhost:8000/docs
echo.
echo 关闭弹出的终端窗口即可停止服务
echo ========================================
pause
