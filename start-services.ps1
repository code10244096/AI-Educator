# AI 教学助手 - 快速启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AI 教学助手 - 服务启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Node.js
Write-Host "[1/3] 检查 Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "  Node.js 已安装：$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  错误：未找到 Node.js，请先安装 Node.js" -ForegroundColor Red
    pause
    exit 1
}

# 检查 Python
Write-Host "[2/3] 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "  Python 已安装：$pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  错误：未找到 Python，请先安装 Python" -ForegroundColor Red
    pause
    exit 1
}

# 启动后端服务
Write-Host "[3/3] 启动服务..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  启动后端服务 (端口 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; uvicorn main:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

Write-Host "  启动前端服务 (端口 3000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "服务启动成功！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址：" -ForegroundColor White
Write-Host "  前端：http://localhost:3000" -ForegroundColor Blue
Write-Host "  后端：http://localhost:8000" -ForegroundColor Blue
Write-Host "  API 文档：http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Yellow
pause > $null
