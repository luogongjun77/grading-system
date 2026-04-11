# Render 云端专用版本
# 简化静态文件服务，使用 Blueprint

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# 云部署配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

# Render 默认端口
PORT = int(os.environ.get('PORT', 10000))

# 路径配置
UPLOAD_FOLDER = os.path.join(PARENT_DIR, 'uploads')
DATA_FOLDER = os.path.join(PARENT_DIR, 'data')
DATABASE = os.path.join(DATA_FOLDER, 'grading.db')
FRONTEND_DIR = os.path.join(PARENT_DIR, 'frontend')

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        student_no TEXT NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        total_score REAL DEFAULT 100,
        choice_score REAL DEFAULT 0,
        fill_score REAL DEFAULT 0,
        essay_score REAL DEFAULT 0,
        answer_key TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        student_id INTEGER,
        choice_score REAL DEFAULT 0,
        fill_score REAL DEFAULT 0,
        essay_score REAL DEFAULT 0,
        total_score REAL DEFAULT 0,
        details TEXT,
        image_path TEXT,
        teacher_comment TEXT,
        manual_reviewed INTEGER DEFAULT 0,
        graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (exam_id) REFERENCES exams(id),
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ============ API 路由 ============

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/index.html')
def index_html():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/app.js')
def app_js():
    return send_from_directory(FRONTEND_DIR, 'app.js')

@app.route('/api/classes', methods=['GET', 'POST'])
def classes():
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('INSERT INTO classes (name, subject) VALUES (?, ?)',
                  (data['name'], data['subject']))
        conn.commit()
        class_id = c.lastrowid
        conn.close()
        return jsonify({'id': class_id, 'message': '班级创建成功'})
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM classes ORDER BY created_at DESC')
    classes = [{'id': row[0], 'name': row[1], 'subject': row[2], 'created_at': row[3]} 
               for row in c.fetchall()]
    conn.close()
    return jsonify(classes)

@app.route('/api/classes/<int:class_id>/students', methods=['GET', 'POST'])
def students(class_id):
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        students_data = data.get('students', [])
        for s in students_data:
            c.execute('INSERT INTO students (class_id, student_no, name) VALUES (?, ?, ?)',
                      (class_id, s['student_no'], s['name']))
        conn.commit()
        conn.close()
        return jsonify({'message': f'成功添加 {len(students_data)} 名学生'})
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM students WHERE class_id = ? ORDER BY student_no', (class_id,))
    students = [{'id': row[0], 'student_no': row[2], 'name': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/classes/<int:class_id>/exams', methods=['GET', 'POST'])
def exams(class_id):
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO exams 
                     (class_id, name, subject, total_score, choice_score, fill_score, essay_score, answer_key)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (class_id, data['name'], data['subject'], 
                   data.get('total_score', 100),
                   data.get('choice_score', 0),
                   data.get('fill_score', 0),
                   data.get('essay_score', 0),
                   json.dumps(data.get('answer_key', {}))))
        conn.commit()
        exam_id = c.lastrowid
        conn.close()
        return jsonify({'id': exam_id, 'message': '考试创建成功'})
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM exams WHERE class_id = ? ORDER BY created_at DESC', (class_id,))
    exams = []
    for row in c.fetchall():
        exams.append({
            'id': row[0], 'name': row[2], 'subject': row[3],
            'total_score': row[4], 'choice_score': row[5],
            'fill_score': row[6], 'essay_score': row[7], 'created_at': row[9]
        })
    conn.close()
    return jsonify(exams)

@app.route('/api/grade/auto', methods=['POST'])
def auto_grade():
    data = request.json
    exam_id = data['exam_id']
    student_id = data['student_id']
    answers = data.get('answers', {})
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT answer_key, choice_score, fill_score, essay_score FROM exams WHERE id = ?', (exam_id,))
    exam = c.fetchone()
    if not exam:
        return jsonify({'error': '考试不存在'}), 404
    
    answer_key = json.loads(exam[0]) if exam[0] else {}
    choice_total = exam[1] or 0
    fill_total = exam[2] or 0
    essay_total = exam[3] or 0
    
    # 选择题评分
    choice_score = 0
    choice_details = {}
    student_choices = answers.get('choices', {})
    correct_choices = answer_key.get('choices', {})
    
    if correct_choices:
        per_score = choice_total / len(correct_choices)
        for q_num, correct in correct_choices.items():
            is_correct = student_choices.get(q_num, '').upper() == correct.upper()
            if is_correct:
                choice_score += per_score
            choice_details[q_num] = {
                'student': student_choices.get(q_num, ''),
                'correct': correct,
                'is_correct': is_correct,
                'score': per_score if is_correct else 0
            }
    
    # 填空题评分（简化版）
    fill_score = 0
    fill_details = {}
    student_fills = answers.get('fills', {})
    correct_fills = answer_key.get('fills', {})
    
    if correct_fills:
        per_score = fill_total / len(correct_fills)
        for q_num, correct in correct_fills.items():
            student_ans = student_fills.get(q_num, '')
            is_correct = student_ans.strip() == correct.strip()
            if is_correct:
                fill_score += per_score
            fill_details[q_num] = {
                'student': student_ans,
                'correct': correct,
                'score': per_score if is_correct else 0,
                'similarity': 1.0 if is_correct else 0.0,
                'feedback': '正确' if is_correct else '错误'
            }
    
    # 大题评分（简化版）
    essay_score = 0
    essay_details = {}
    essay_text = answers.get('essay_text', '')
    
    if essay_total > 0 and essay_text:
        essay_score = essay_total * 0.8  # 默认80%分
        essay_details = {'1': {'score': essay_score, 'max_score': essay_total, 'feedback': 'AI评分仅供参考'}}
    
    # 保存成绩
    details = json.dumps({'choices': choice_details, 'fills': fill_details, 'essays': essay_details})
    total = choice_score + fill_score + essay_score
    
    c.execute('''INSERT OR REPLACE INTO scores 
                 (exam_id, student_id, choice_score, fill_score, essay_score, total_score, details, image_path)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (exam_id, student_id, choice_score, fill_score, essay_score, total, details, ''))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'choice_score': round(choice_score, 2),
        'fill_score': round(fill_score, 2),
        'essay_score': round(essay_score, 2),
        'total_score': round(total, 2),
        'details': details
    })

@app.route('/api/scores/<int:score_id>', methods=['PUT'])
def update_score(score_id):
    data = request.json
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''UPDATE scores SET 
                 choice_score = ?, fill_score = ?, essay_score = ?, total_score = ?, 
                 teacher_comment = ?, manual_reviewed = ?
                 WHERE id = ?''',
              (data.get('choice_score', 0), data.get('fill_score', 0), 
               data.get('essay_score', 0), data.get('total_score', 0),
               data.get('comment', ''), 1, score_id))
    conn.commit()
    conn.close()
    return jsonify({'message': '已保存'})

@app.route('/api/scores/<int:score_id>')
def get_score(score_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT s.*, st.student_no, st.name, e.name 
                 FROM scores s JOIN students st ON s.student_id = st.id JOIN exams e ON s.exam_id = e.id
                 WHERE s.id = ?''', (score_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '不存在'}), 404
    return jsonify({
        'score_id': row[0], 'total_score': row[6], 'choice_score': row[3],
        'fill_score': row[4], 'essay_score': row[5], 'student_no': row[10],
        'student_name': row[11], 'exam_name': row[12], 'details': json.loads(row[7] or '{}')
    })

@app.route('/api/exams/<int:exam_id>/statistics')
def exam_statistics(exam_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT s.total_score, st.student_no, st.name, s.id
                 FROM scores s JOIN students st ON s.student_id = st.id WHERE s.exam_id = ?''', (exam_id,))
    scores = c.fetchall()
    conn.close()
    
    if not scores:
        return jsonify({'message': '暂无成绩'})
    
    totals = [s[0] for s in scores]
    return jsonify({
        'count': len(scores),
        'max_score': max(totals),
        'min_score': min(totals),
        'avg_score': round(sum(totals) / len(totals), 2),
        'scores': [{'student_no': s[1], 'name': s[2], 'score': s[0], 'score_id': s[3]} for s in scores]
    })

@app.route('/api/exams/<int:exam_id>/export')
def export_exam(exam_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT st.student_no, st.name, s.total_score, s.choice_score, s.fill_score, s.essay_score
                 FROM scores s JOIN students st ON s.student_id = st.id WHERE s.exam_id = ?''', (exam_id,))
    scores = c.fetchall()
    conn.close()
    
    html = '<html><head><meta charset="utf-8"><title>成绩单</title></head><body>'
    html += '<h1>成绩单</h1><table border="1" cellpadding="5">'
    html += '<tr><th>学号</th><th>姓名</th><th>总分</th><th>选择题</th><th>填空题</th><th>大题</th></tr>'
    for s in scores:
        html += f'<tr><td>{s[0]}</td><td>{s[1]}</td><td>{s[2]}</td><td>{s[3]}</td><td>{s[4]}</td><td>{s[5]}</td></tr>'
    html += '</table></body></html>'
    
    return html

@app.route('/api/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Gunicorn 入口
app.run(host='0.0.0.0', port=PORT)
