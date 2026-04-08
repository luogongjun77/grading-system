# 智能阅卷系统

## 系统位置

```
E:\GradingSystem\
├── backend/              # 后端代码
│   ├── app.py          # 本地运行版本
│   ├── app_cloud.py     # 云服务器版本
│   ├── ai_grading.py   # AI评分模块
│   ├── answer_sheet_generator.py  # 答题卡生成器
│   ├── score_annotator.py          # 分数标注器
│   └── requirements.txt           # Python依赖
├── frontend/            # 前端界面
│   ├── index.html
│   └── app.js
├── uploads/            # 上传的图片
├── data/               # 数据库
├── start.bat          # 启动脚本
├── railway.json       # Railway部署配置
├── DEPLOY_RAILWAY.md  # Railway部署指南
└── README.md          # 本文件

## 本地运行

双击 `start.bat` 启动系统

访问：http://localhost:5000

## 云服务器部署

详见 `DEPLOY_RAILWAY.md`

推荐使用 Railway.app（免费500小时/月）

## 功能清单

- 班级/学生管理（200人）
- 考试创建与标准答案设置
- 答题卡制作（PDF可打印）
- 拍照OCR识别答题卡
- AI辅助评分（填空题/大题）
- 人工批阅修正分数
- 成绩统计与导出
- 答题卡分数标注

## 注意事项

1. 首次使用需安装 Python 3.8+
2. OCR功能需要 Tesseract OCR
3. 定期备份 `data/grading.db` 数据库
