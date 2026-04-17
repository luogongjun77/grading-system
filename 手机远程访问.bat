@echo off
chcp 65001 >nul
title 智能阅卷系统 - 手机远程访问
color 0B

echo ╔══════════════════════════════════════════════════════╗
echo ║     智能阅卷系统 - 手机远程访问（内网穿透）           ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo 此脚本将启动阅卷系统并通过内网穿透，让你在任何地方
echo （包括手机流量网络）都能访问。
echo.

:: 先启动主服务（后台）
echo [1/3] 启动阅卷系统...
start /b python app.py > nul 2>&1
timeout /t 3 /nobreak > nul

:: 获取本机IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" ^| findstr /v "127.0.0.1"') do (
    for /f "tokens=1" %%b in ("%%a") do set LOCAL_IP=%%b
)
if not defined LOCAL_IP set LOCAL_IP=127.0.0.1

echo ✅ 服务已启动
echo.

:: 选择穿透方式
echo [2/3] 选择内网穿透方式：
echo.
echo   1. 同一WiFi局域网访问（无需穿透，手机连同一WiFi即可）
echo      手机浏览器打开：http://%LOCAL_IP%:5000
echo.
echo   2. 使用 cloudflared 穿透（推荐，免费，无需注册）
echo.
echo   3. 使用 localtunnel 穿透（免费，简单）
echo.
set /p CHOICE="请选择 (1/2/3): "

if "%CHOICE%"=="1" (
    echo.
    echo ╔══════════════════════════════════════════════════════╗
    echo ║  手机连同一WiFi，浏览器打开：                          ║
    echo ║  http://%LOCAL_IP%:5000                      ║
    echo ║                                                      ║
    echo ║  管理员：admin / admin123                             ║
    echo ╚══════════════════════════════════════════════════════╝
    echo.
    echo 服务运行中，按 Ctrl+C 停止...
    pause
    goto :end
)

if "%CHOICE%"=="2" (
    echo.
    echo [3/3] 启动 Cloudflare Tunnel...
    echo.
    where cloudflared >nul 2>&1
    if %errorlevel% neq 0 (
        echo 正在下载 cloudflared...
        curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
        if not exist cloudflared.exe (
            echo ❌ 下载失败，请手动下载：https://github.com/cloudflare/cloudflared/releases
            pause
            goto :end
        )
    )
    echo.
    echo ✅ 正在创建公网访问链接，请稍候...
    echo （首次运行可能需要几秒钟）
    echo.
    cloudflared.exe tunnel --url http://127.0.0.1:5000
    goto :end
)

if "%CHOICE%"=="3" (
    echo.
    echo [3/3] 启动 LocalTunnel...
    where npx >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 需要 Node.js，请先安装：https://nodejs.org/
        pause
        goto :end
    )
    echo ✅ 正在创建公网访问链接...
    npx localtunnel --port 5000
    goto :end
)

echo 无效选择
:end
