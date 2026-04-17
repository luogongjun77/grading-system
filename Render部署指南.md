# 智能阅卷系统 - Render 免费部署指南

## 📋 部署前准备

代码已推送到 GitHub：https://github.com/luogongjun77/grading-system

---

## 🚀 Render 部署步骤（完全免费）

### 第一步：注册 Render

1. 打开 👉 **https://dashboard.render.com/register**
2. 点击 **"GitHub"** 按钮用 GitHub 账号登录
3. 授权 Render 访问你的 GitHub

### 第二步：创建 Web Service

1. 登录后进入 Dashboard，点击 **"New +"** 按钮
2. 选择 **"Web Service"**
3. 在仓库列表中找到 **`grading-system`**，点击 **"Connect"**
   - 如果看不到，点击 "Configure account" 授权更多仓库

### 第三步：配置服务

| 配置项 | 填写内容 |
|--------|----------|
| **Name** | `grading-system`（或你喜欢的名字） |
| **Region** | `Oregon, USA` 或 `Frankfurt, Germany` |
| **Branch** | `main` |
| **Root Directory** | 留空 |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Instance Type** | **Free** ← 重要！选免费的 |

### 第四步：添加环境变量

在 "Environment" 部分，点击 **"Add Environment Variable"**，添加以下变量：

| Key | Value | 说明 |
|-----|-------|------|
| `SECRET_KEY` | （点击Generate生成） | 安全密钥 |
| `AI_PROVIDER` | `demo` | AI模式（后续可改为deepseek等） |
| `DATA_DIR` | `/opt/render/project/src/static` | 文件存储目录 |

> 💡 如果你有 DeepSeek 的 API Key，可以额外添加：
> - `AI_PROVIDER` = `deepseek`
> - `AI_API_KEY` = `你的DeepSeek API Key`

### 第五步：部署

1. 点击页面底部的 **"Create Web Service"** 按钮
2. 等待 3-5 分钟，Render 会自动构建和部署
3. 部署成功后，页面顶部会显示你的网址：
   ```
   https://grading-system-xxxx.onrender.com
   ```
4. 点击这个链接即可访问！🎉

### 第六步：初始化

首次访问时，系统会自动创建数据库和默认管理员账号：
- 账号：`admin`
- 密码：`admin123`

> ⚠️ 登录后请立即修改密码！

---

## ⚠️ Render 免费版注意事项

| 事项 | 说明 |
|------|------|
| **冷启动** | 15分钟无访问会休眠，下次访问需等待约30秒唤醒 |
| **运行时间** | 每月750小时免费（足够1个服务24/7运行） |
| **文件存储** | 上传的图片/PDF重启后会丢失（成绩数据在数据库中不会丢失） |
| **数据库** | SQLite数据库在重启后也会重置（免费版限制） |

### 💡 解决文件丢失问题的方案

如果需要持久化存储，可以：
1. 升级 Render 付费版（$7/月）
2. 使用 Render PostgreSQL 免费版（数据库不丢失）
3. 本地运行（推荐，数据完全保存）

---

## 🔄 更新部署

代码推送到 GitHub 后，Render 会自动重新部署：

```bash
git add .
git commit -m "更新说明"
git push origin main
```

---

## ❓ 常见问题

**Q: 部署失败，提示依赖安装错误？**
A: 检查 requirements.txt 中的包版本是否兼容

**Q: 访问网址显示502错误？**
A: 等待1-2分钟，服务可能还在启动中

**Q: 上传的图片看不到？**
A: Render免费版文件系统是临时的，重启后会丢失

**Q: 想用PostgreSQL数据库？**
A: 在Render中创建PostgreSQL数据库，将DATABASE_URL环境变量设置为数据库URL
