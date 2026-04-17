#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt

# 初始化数据目录
mkdir -p /data/uploads /data/answer_sheets /data/uploads/pdf_pages

# 初始化数据库
python -c "
import os
os.environ.setdefault('DATA_DIR', '/data')
from app import app, db, init_db
with app.app_context():
    db.create_all()
    init_db()
    print('✅ 数据库初始化完成')
"
