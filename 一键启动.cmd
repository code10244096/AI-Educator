@echo off
chcp 65001 >nul
title AI教学助手 - 正在启动
echo.
echo 正在启动服务，请稍候（约15秒）...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-and-test.ps1"
echo.
echo 若浏览器未自动打开，请访问: http://localhost:3000
echo 日志文件: %~dp0service-log.txt
pause
