# 智能阅卷系统

基于 Flask 的智能阅卷与成绩管理系统，支持 AI 辅助阅卷、答题卡识别、成绩统计分析。

## ✨ 功能特性

- 🏫 **班级管理** — 创建班级、批量导入学生（支持 Excel/CSV）
- 📝 **考试管理** — 设置考试、题目分组、分值配置
- 📄 **答题卡设计** — 自定义答题卡布局，支持图片和 PDF 格式
- 🤖 **AI 辅助阅卷** — 拍照识别题目，AI 生成参考答案并辅助批改
  - 支持 DeepSeek、智谱 GLM、OpenAI GPT-4o、Moonshot 等
- 📊 **成绩分析** — 平均分、中位数、标准差、分数段分布、班级对比
- 🔍 **成绩查询** — 学生可查询个人成绩，查看答题卡逐题评分
- 📱 **手机访问** — 同一 WiFi 下手机浏览器直接访问
- 🌐 **远程访问** — 支持 Cloudflare Tunnel 外网访问

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 方式一：一键启动（Windows）

1. 双击 `智能阅卷系统.py` 即可启动
2. 首次运行会自动安装依赖，等待 1-2 分钟
3. 浏览器打开 http://127.0.0.1:5000

### 方式二：命令行启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动系统
python app.py

# 或使用单文件版本
python 智能阅卷系统.py
```

### 方式三：Windows 批处理

双击 `启动阅卷系统.bat`，自动安装依赖、配置防火墙、启动服务。

## 🔐 登录信息

| 角色 | 账号 | 密码 |
|------|------|------|
| 管理员 | admin | admin123 |

> ⚠️ 首次登录后请立即修改密码！

## 📁 项目结构

```
├── app.py                  # 主应用程序（多文件版）
├── 智能阅卷系统.py           # 单文件版（含所有模板）
├── requirements.txt        # Python 依赖
├── Procfile               # 部署配置
├── export_data.py         # 数据导出工具
├── 安装智能阅卷系统.py        # 自安装脚本
├── 启动阅卷系统.bat          # Windows 一键启动
├── 手机远程访问.bat          # 远程访问配置
├── 数据备份.bat             # 数据备份/恢复
├── 安装使用说明.md           # 详细安装指南
├── templates/             # HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── query.html
│   ├── admin_*.html       # 管理后台页面
│   └── ...
└── static/                # 静态资源
    ├── css/
    └── js/
```

## 🤖 AI 服务配置

系统支持多种 AI 服务，在管理后台 → 考试设置中配置：

| 服务 | 配置项 | 说明 |
|------|--------|------|
| DeepSeek | API Key | 推荐，性价比高 |
| 智谱 GLM | API Key | 国产大模型 |
| OpenAI GPT-4o | API Key + Base URL | 支持自定义端点 |
| Moonshot | API Key | 月之暗面 |
| Demo 模式 | 无需配置 | 演示用，自动生成模拟评分 |

## 📱 手机访问

### 同一 WiFi 下

1. 电脑上运行 `ipconfig` 获取本机 IP（如 `192.168.1.100`）
2. 手机浏览器输入 `http://192.168.1.100:5000`

### 外网远程访问

运行 `手机远程访问.bat`，选择 Cloudflare Tunnel 方式获取公网地址。

## 📊 成绩分析功能

- 全班/全年级统计：平均分、中位数、标准差、最高/最低分
- 分数段分布图
- 各题得分率分析
- 班级对比分析
- CSV 导出（含逐题得分明细）

## 🛠️ 技术栈

- **后端**：Flask 3.0 + SQLAlchemy
- **前端**：Bootstrap 5 + Jinja2
- **数据库**：SQLite
- **AI**：OpenAI API 兼容接口
- **PDF**：PyMuPDF + ReportLab
- **图像**：Pillow

## 📄 License

MIT License
