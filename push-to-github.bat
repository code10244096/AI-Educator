@echo off
chcp 65001 >nul
echo ========================================
echo AI 教学助手 - 推送到 GitHub
echo ========================================
echo.

REM 检查是否已配置 git
git config user.name >nul 2>&1
if errorlevel 1 (
    echo [配置] 设置 Git 用户信息...
    set /p git_name="请输入你的 Git 用户名："
    git config --global user.name "%git_name%"
    
    set /p git_email="请输入你的 Git 邮箱："
    git config --global user.email "%git_email%"
)

echo.
echo 当前 Git 配置:
git config user.name
git config user.email
echo.

REM 检查是否已添加远程仓库
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [提示] 请先在 GitHub 上创建仓库，然后输入仓库地址
    echo.
    echo 创建仓库步骤:
    echo 1. 访问 https://github.com/new
    echo 2. 仓库名：ai-teaching-assistant
    echo 3. 选择 Public 或 Private
    echo 4. 不要勾选 "Initialize with README"
    echo 5. 点击 "Create repository"
    echo.
    set /p repo_url="输入 GitHub 仓库地址 (格式：https://github.com/用户名/仓库名.git): "
    git remote add origin %repo_url%
) else (
    echo [远程仓库] 已配置:
    git remote get-url origin
)

echo.
echo ========================================
echo 推送到 GitHub
echo ========================================
echo.

REM 显示将要推送的文件
echo 以下文件将被推送:
git status --short
echo.

set /p confirm="确认推送？(Y/N): "
if /i not "%confirm%"=="Y" (
    echo 已取消
    pause
    exit /b 1
)

REM 推送
echo.
echo 正在推送到 GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo 推送失败！可能的原因:
    echo 1. 未配置 GitHub 认证
    echo 2. 仓库不存在
    echo 3. 网络连接问题
    echo.
    echo 解决方案:
    echo 1. 使用 Personal Access Token:
    echo    git push https://用户名:TOKEN@github.com/用户名/ai-teaching-assistant.git
    echo.
    echo 2. 配置 SSH 密钥 (推荐):
    echo    ssh-keygen -t ed25519 -C "your_email@example.com"
    echo    然后将公钥添加到 GitHub: https://github.com/settings/keys
    echo.
) else (
    echo.
    echo ========================================
    echo ✓ 推送成功！
    echo ========================================
    echo.
    echo 仓库地址: %repo_url%
    echo.
    echo 下一步:
    echo 1. 访问你的 GitHub 仓库
    echo 2. 更新 README.md 中的用户名
    echo 3. 添加项目 topics
    echo 4. 邀请协作者（可选）
    echo.
)

pause
