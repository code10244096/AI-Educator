# AI 教学助手 - 启动并自检（输出日志到项目目录）
$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent
$LogFile = Join-Path $Root "service-log.txt"

function Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

Set-Content -Path $LogFile -Value "=== AI Educator Service Log ==="

Log "项目目录: $Root"

# 1. 清理端口
foreach ($port in 3000, 8000, 5173) {
    $lines = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $lines) {
        if ($line -match '\s(\d+)\s*$') {
            $procId = $matches[1]
            Log "终止端口 $port 的进程 PID=$procId"
            taskkill /PID $procId /F 2>$null | Out-Null
        }
    }
}
Start-Sleep -Seconds 2

# 2. 检查环境
try { Log "Python: $(python --version 2>&1)" } catch { Log "ERROR: 未安装 Python" }
try { Log "Node: $(node --version 2>&1)" } catch { Log "ERROR: 未安装 Node.js" }

# 3. 安装依赖
Log "检查后端依赖..."
Push-Location (Join-Path $Root "backend")
pip install -r requirements.txt -q 2>&1 | Out-Null
Pop-Location

Log "检查前端依赖..."
Push-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) {
    npm install 2>&1 | Tee-Object -FilePath $LogFile -Append
}
Pop-Location

# 4. 启动后端
$backendDir = Join-Path $Root "backend"
Log "启动后端 127.0.0.1:8000 ..."
Start-Process -FilePath "python" `
    -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","8000" `
    -WorkingDirectory $backendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Root "backend-out.log") `
    -RedirectStandardError (Join-Path $Root "backend-err.log")

Start-Sleep -Seconds 4

# 5. 启动前端
$frontendDir = Join-Path $Root "frontend"
Log "启动前端 :3000 ..."
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c","npm run dev > `"$(Join-Path $Root 'frontend-out.log')`" 2> `"$(Join-Path $Root 'frontend-err.log')`"" `
    -WorkingDirectory $frontendDir `
    -WindowStyle Hidden

Log "等待服务就绪..."
Start-Sleep -Seconds 12

# 6. 自检
Log "--- 自检结果 ---"
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5
    Log "后端 OK: $($health.Content)"
} catch {
    Log "后端 FAIL: $($_.Exception.Message)"
    if (Test-Path (Join-Path $Root "backend-err.log")) {
        Log "backend-err.log:"
        Get-Content (Join-Path $Root "backend-err.log") -Tail 15 | ForEach-Object { Log "  $_" }
    }
}

foreach ($port in 3000, 5173) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port" -UseBasicParsing -TimeoutSec 5
        Log "前端 OK 端口 $port : HTTP $($r.StatusCode)"
        Log ">>> 请打开: http://localhost:$port"
    } catch {
        Log "前端 端口 $port FAIL: $($_.Exception.Message)"
    }
}

if (Test-Path (Join-Path $Root "frontend-err.log")) {
    $fe = Get-Content (Join-Path $Root "frontend-err.log") -Tail 20 -ErrorAction SilentlyContinue
    if ($fe) { Log "frontend-err.log:"; $fe | ForEach-Object { Log "  $_" } }
}

Log "=== 完成。日志: $LogFile ==="
Start-Process "http://localhost:3000"
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"
