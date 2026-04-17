@echo off
chcp 65001 >nul
title 数据备份与恢复
color 0E

echo ╔══════════════════════════════════════════════════════╗
echo ║          智能阅卷系统 - 数据备份与恢复                ║
echo ╚══════════════════════════════════════════════════════╝
echo.

set DB_FILE=instance\grading.db
set BACKUP_DIR=backups

if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%

echo 请选择操作：
echo   1. 备份数据（导出当前数据）
echo   2. 恢复数据（从备份还原）
echo   3. 导出为CSV（Excel可打开）
echo.
set /p CHOICE="请选择 (1/2/3): "

if "%CHOICE%"=="1" (
    if not exist %DB_FILE% (
        echo ❌ 数据库文件不存在，请先启动系统
        pause
        exit /b
    )
    set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%
    set TIMESTAMP=%TIMESTAMP: =0%
    copy %DB_FILE% %BACKUP_DIR%\grading_%TIMESTAMP%.db
    echo.
    echo ✅ 备份完成！文件位于：%BACKUP_DIR%\grading_%TIMESTAMP%.db
    echo.
    echo 💡 你可以将备份文件复制到其他电脑的 backups 目录，
    echo    然后用"恢复数据"功能导入，实现多台电脑数据同步。
)

if "%CHOICE%"=="2" (
    echo.
    echo 可用的备份文件：
    echo.
    dir /b %BACKUP_DIR%\*.db 2>nul
    if %errorlevel% neq 0 (
        echo ❌ 没有找到备份文件
        pause
        exit /b
    )
    echo.
    set /p FILENAME="请输入要恢复的文件名："
    if not exist %BACKUP_DIR%\%FILENAME% (
        echo ❌ 文件不存在
        pause
        exit /b
    )
    copy /y %BACKUP_DIR%\%FILENAME% %DB_FILE%
    echo.
    echo ✅ 数据恢复完成！请重新启动阅卷系统。
)

if "%CHOICE%"=="3" (
    python export_data.py
)

echo.
pause
