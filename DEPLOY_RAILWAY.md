# 智能阅卷系统 - Railway 部署配置

**Railway.app 部署步骤：**

## 1. 准备 GitHub 仓库

把 `E:\GradingSystem` 文件夹上传到 GitHub：
- 在 GitHub 创建新仓库 `grading-system`
- 本地执行：
```bash
cd E:\GradingSystem
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/grading-system.git
git push -u origin main
```

## 2. Railway 部署

1. 访问 https://railway.app
2. 用 GitHub 登录
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择 `grading-system` 仓库
5. Railway 会自动检测为 Python 项目

## 3. 配置环境变量

在 Railway 项目设置中添加：
- `PORT` = `5000`
- `RENDER_DISK` = `/app/data` （用于存储数据）

## 4. 修改启动命令

Railway 会自动运行 `python app.py`，但我们需要用 `app_cloud.py`：
- 在项目设置中修改 Start Command 为：
```
cd backend && python app_cloud.py
```

## 5. 部署完成

Railway 会分配一个免费域名，例如：
`https://grading-system.up.railway.app`

---

## 访问方式

部署成功后，用分配的域名访问即可：
- 老师端：`域名` （阅卷管理）
- 学生端：同一界面，可查询成绩

---

## 注意事项

1. 免费额度：500小时/月（足够使用）
2. 数据持久化：Railway 免费版数据会在冷启动后重置
3. 如需永久保存：升级付费版或使用数据库服务