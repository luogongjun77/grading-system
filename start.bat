@echo off
chcp 65001 >nul
echo ==========================================
echo       智能阅卷系统 - 启动脚本 (E盘)
echo ==========================================
echo.

REM 设置Python路径
set PYTHON_PATH=C:\Program Files\Python312\python.exe
set PIP_PATH=C:\Program Files\Python312\Scripts\pip.exe

REM 检查Python
if not exist "%PYTHON_PATH%" (
    echo [错误] 未找到Python，请确保Python已安装
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
cd /d "E:\GradingSystem\backend"
"%PIP_PATH%" install flask flask-cors pillow pytesseract openpyxl -q

echo [2/3] 正在启动后端服务...
start "阅卷系统后端" cmd /k "cd /d "E:\GradingSystem\backend" && "%PYTHON_PATH%" app.py"

timeout /t 3 /nobreak >nul

echo [3/3] 正在打开前端界面...
start http://localhost:5000

echo.
echo ==========================================
echo  系统已启动！
echo  访问地址：http://localhost:5000
echo  手机/其他电脑：同一WiFi下访问 http://你的电脑IP:5000
echo ==========================================
echo.
echo 按任意键关闭此窗口（服务继续在后台运行）
pause >nul