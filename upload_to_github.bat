@echo off
chcp 65001 >nul
cd /d E:\GradingSystem

echo 正在初始化Git仓库...
git init

echo 正在添加文件...
git add .

echo 正在提交...
git commit -m "智能阅卷系统初始版本"

echo 正在切换到main分支...
git branch -M main

echo 正在添加远程仓库...
git remote add origin https://github.com/luogongjun77/grading-system.git

echo 正在上传到GitHub...
git push -u origin main

echo.
echo ==========================================
echo  上传完成！
echo ==========================================
pause