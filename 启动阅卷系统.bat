@echo off
chcp 65001 >nul
title 智能阅卷系统
color 0A

echo ======================================================
echo           智能阅卷系统 - 一键启动
echo ======================================================
echo.

:: ──── 第一步：检查 Python ────
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] 未检测到 Python！
    echo.
    echo 请先安装 Python 3.9+：
    echo   下载地址：https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ──── 第二步：安装依赖 ────
echo.
echo [2/5] 安装依赖包（首次运行较慢）...
pip install -r requirements.txt -q --disable-pip-version-check
if %errorlevel% neq 0 (
    echo [!] 依赖安装失败，尝试使用国内镜像...
    pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check
)
echo [OK] 依赖安装完成

:: ──── 第三步：放行防火墙 ────
echo.
echo [3/5] 配置防火墙（允许手机访问）...
netsh advfirewall firewall delete rule name="智能阅卷系统" >nul 2>&1
netsh advfirewall firewall add rule name="智能阅卷系统" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
echo [OK] 防火墙已放行 5000 端口

:: ──── 第四步：获取本机IP ────
echo.
echo [4/5] 获取本机局域网IP...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" ^| findstr /v "127.0.0.1"') do (
    for /f "tokens=1" %%b in ("%%a") do set LOCAL_IP=%%b
)
if not defined LOCAL_IP set LOCAL_IP=127.0.0.1

:: ──── 第五步：启动服务 ────
echo.
echo [5/5] 启动阅卷系统服务...
echo.
echo ======================================================
echo   [电脑] 浏览器打开：http://127.0.0.1:5000
echo   [手机] 浏览器打开：http://%LOCAL_IP%:5000
echo   (手机需和电脑连同一个WiFi)
echo.
echo   管理员：admin / admin123
echo   按 Ctrl+C 停止服务
echo ======================================================
echo.

:: 启动 Flask 服务，绑定所有网卡
python app.py

pause
