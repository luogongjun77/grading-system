FROM python:3.11-slim

# 安装系统依赖（PyMuPDF需要）
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用缓存加速
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY app.py .
COPY export_data.py .
COPY Procfile .
COPY templates/ templates/
COPY static/ static/

# 创建上传目录
RUN mkdir -p static/uploads static/answer_sheets static/uploads/pdf_pages

# 环境变量
ENV PORT=7860
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--timeout", "120"]
