@echo off
echo ========================================
echo AI 教学助手 - 一键部署脚本 (Windows 版)
echo ========================================
echo.

REM 设置服务器 IP
set /p SERVER_IP="请输入服务器 IP 地址："
if "%SERVER_IP%"=="" (
    echo 错误：未输入服务器 IP
    pause
    exit /b 1
)

echo.
echo 服务器 IP: %SERVER_IP%
echo.

REM 检查 SSH 连接
echo 正在测试 SSH 连接...
ssh -o BatchMode=yes root@%SERVER_IP% exit 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo 首次连接需要手动输入密码
    echo.
    echo 请按以下步骤操作：
    echo 1. 手动连接服务器：ssh root@%SERVER_IP%
    echo 2. 输入密码登录
    echo 3. 然后运行此脚本
    echo.
    pause
)

echo.
echo 开始上传文件...
echo.

REM 创建临时目录
set TEMP_DIR=%TEMP%\ai-teaching-deploy
if exist %TEMP_DIR% rmdir /s /q %TEMP_DIR%
mkdir %TEMP_DIR%

REM 复制必要文件
echo 复制部署文件...
xcopy /E /I /Y backend %TEMP_DIR%\backend\ 2>nul
xcopy /E /I /Y frontend %TEMP_DIR%\frontend\ 2>nul
copy docker-compose.yml %TEMP_DIR%\ 2>nul
copy deploy.sh %TEMP_DIR%\ 2>nul
copy check-server.sh %TEMP_DIR%\ 2>nul

REM 使用 scp 上传
echo 上传文件到服务器...
scp -r %TEMP_DIR%\* root@%SERVER_IP%:/opt/ai-teaching/

if %ERRORLEVEL% neq 0 (
    echo.
    echo 上传失败，请手动上传或使用以下命令：
    echo scp -r e:\AI-Educator root@%SERVER_IP%:/opt/ai-teaching
    echo.
    pause
    exit /b 1
)

echo.
echo 文件上传成功！
echo.
echo ========================================
echo 下一步操作：
echo ========================================
echo.
echo 1. SSH 登录服务器：
echo    ssh root@%SERVER_IP%
echo.
echo 2. 运行环境检查：
echo    cd /opt/ai-teaching
echo    chmod +x check-server.sh
echo    ./check-server.sh
echo.
echo 3. 安装 Docker（如未安装）：
echo    curl -fsSL https://get.docker.com -o get-docker.sh
echo    sh get-docker.sh
echo.
echo 4. 启用 Swap（重要！）：
echo    dd if=/dev/zero of=/swapfile bs=1M count=2048
echo    chmod 600 /swapfile
echo    mkswap /swapfile
echo    swapon /swapfile
echo    echo '/swapfile none swap sw 0 0' ^>^> /etc/fstab
echo.
echo 5. 配置应用：
echo    mkdir -p uploads data
echo    cp backend/config.production.json backend/config.json
echo    nano backend/config.json
echo    # 修改 api_key、cors_origins 和 jwt.secret_key
echo.
echo 6. 启动服务：
echo    cd /opt/ai-teaching
echo    docker-compose up -d
echo    docker-compose ps
echo.
echo 7. 访问应用：
echo    http://%SERVER_IP%
echo.
echo ========================================
echo 详细指南请查看：DEPLOY_2GB.md
echo ========================================
echo.

REM 清理临时文件
rmdir /s /q %TEMP_DIR%

pause
