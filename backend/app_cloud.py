# -*- coding: utf-8 -*-
"""
智能阅卷系统 - 云部署版本
支持 Railway / Render / PythonAnywhere
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import base64
from PIL import Image
import pytesseract
import re

# 导入AI评分模块
from ai_grading import ai_grader

# 导入答题卡生成器
from answer_sheet_generator import AnswerSheetGenerator

# 导入分数标注模块
from score_annotator import ScoreAnnotator

app = Flask(__name__)
CORS(app)

# 云部署配置 - 使用环境变量或默认路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 尝试从环境变量获取路径
RENDER_DISK = os.environ.get('RENDER_DISK', '')
if RENDER_DISK:
    # 云服务器路径
    UPLOAD_FOLDER = os.path.join(RENDER_DISK, 'uploads')
    DATA_FOLDER = os.path.join(RENDER_DISK, 'data')
else:
    # 本地路径
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'uploads')
    DATA_FOLDER = os.path.join(BASE_DIR, '..', 'data')

DATABASE = os.path.join(DATA_FOLDER, 'grading.db')

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # 班级表
    c.execute('''CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 学生表
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        student_no TEXT NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )''')
    
    # 考试表
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
    
    # 成绩表
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

# 1. 班级管理
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

# 2. 学生管理
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

# 3. 考试管理
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
            'id': row[0],
            'name': row[2],
            'subject': row[3],
            'total_score': row[4],
            'choice_score': row[5],
            'fill_score': row[6],
            'essay_score': row[7],
            'created_at': row[9]
        })
    conn.close()
    return jsonify(exams)

# 4. OCR识别
@app.route('/api/ocr', methods=['POST'])
def ocr_grade():
    ocr_type = request.form.get('type', '')
    exam_id = request.form.get('exam_id')
    
    if 'image' not in request.files:
        text = request.form.get('question', '')
        if text:
            if ocr_type == 'generate_answer':
                return jsonify(generate_answer_by_text(text))
            return jsonify({'error': '没有上传图片也没有文本'})
        return jsonify({'error': '没有上传图片'}), 400
    
    file = request.files['image']
    
    # 保存图片
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    try:
        # 尝试使用Tesseract（如果可用）
        try:
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        except:
            text = "[OCR不可用，请使用文本输入]"
        
        if ocr_type == 'answer_key':
            result = parse_answer_key(text)
        elif ocr_type == 'generate_answer':
            result = generate_answer_by_text(text)
        else:
            result = parse_answer_sheet(text, exam_id)
        
        result['image_path'] = filepath
        result['raw_text'] = text
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'image_path': filepath}), 500

def generate_answer_by_text(text):
    result = {'choices': {}, 'fills': {}, 'essays': {}, 'essay_text': ''}
    
    choice_pattern = r'[AaBbCcDd]\s*[\.、\)]?\s*([^\n]+?)(?=\s*[BbCcDd]\s|$)'
    for match in re.finditer(choice_pattern, text, re.MULTILINE):
        result['essay_text'] += match.group(0) + '\n'
    
    fill_pattern = r'[（\(]\s*([^\n]+?)\s*[）\)]'
    fills = re.findall(fill_pattern, text)
    for i, fill in enumerate(fills[:10], 1):
        result['fills'][str(i)] = fill.strip()
    
    if not result['fills'] and not result['essay_text']:
        result['essay_text'] = text
    
    return result

def parse_answer_key(text):
    result = {'choices': {}, 'fills': {}, 'essays': {}, 'essay_text': ''}
    
    patterns = [
        r'(\d+)[\.、\s]+([ABCD])',
        r'第\s*(\d+)\s*题?\s*[:：]?\s*([ABCD])',
        r'(\d+)\s*[-－—]\s*([ABCD])',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            if len(groups) == 2:
                if groups[0].isdigit():
                    result['choices'][groups[0]] = groups[1].upper()
                elif groups[1].isdigit():
                    result['choices'][groups[1]] = groups[0].upper()
    
    fill_patterns = [r'空\s*(\d+)\s*[:：]?\s*([^\n]+)', r'填空\s*(\d+)\s*[:：]?\s*([^\n]+)']
    for pattern in fill_patterns:
        for match in re.finditer(pattern, text):
            result['fills'][match.group(1)] = match.group(2).strip()
    
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
    if lines:
        result['essay_text'] = '\n'.join(lines[:20])
    
    return result

def parse_answer_sheet(text, exam_id):
    student_no_match = re.search(r'学号[：:]?\s*(\d+)', text)
    student_no = student_no_match.group(1) if student_no_match else None
    
    name_match = re.search(r'姓名[：:]?\s*(\S+)', text)
    name = name_match.group(1) if name_match else None
    
    choices = {}
    choice_pattern = r'(?:第?\s*(\d+)\s*[题\.]\s*[:：]?\s*)([ABCD])'
    for match in re.finditer(choice_pattern, text):
        choices[match.group(1)] = match.group(2)
    
    fills = {}
    fill_pattern = r'(?:第?\s*(\d+)\s*空\s*[:：]?\s*)([^\n]+)'
    for match in re.finditer(fill_pattern, text):
        fills[match.group(1)] = match.group(2).strip()
    
    return {'student_no': student_no, 'name': name, 'choices': choices, 'fills': fills, 'essay_text': text}

# 5. 自动评分
@app.route('/api/grade/auto', methods=['POST'])
def auto_grade():
    data = request.json
    exam_id = data['exam_id']
    student_id = data['student_id']
    answers = data['answers']
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT answer_key, choice_score, fill_score FROM exams WHERE id = ?', (exam_id,))
    exam = c.fetchone()
    if not exam:
        return jsonify({'error': '考试不存在'}), 404
    
    answer_key = json.loads(exam[0]) if exam[0] else {}
    choice_total = exam[1] or 0
    fill_total = exam[2] or 0
    
    # 选择题评分
    choice_score = 0
    choice_details = {}
    student_choices = answers.get('choices', {})
    correct_choices = answer_key.get('choices', {})
    
    if correct_choices:
        per_score = choice_total / len(correct_choices)
        for q_num, correct in correct_choices.items():
            student_ans = student_choices.get(q_num, '')
            is_correct = student_ans.upper() == correct.upper()
            if is_correct:
                choice_score += per_score
            choice_details[q_num] = {
                'student': student_ans,
                'correct': correct,
                'is_correct': is_correct,
                'score': per_score if is_correct else 0
            }
    
    # 填空题AI评分
    fill_score = 0
    fill_details = {}
    student_fills = answers.get('fills', {})
    correct_fills = answer_key.get('fills', {})
    
    if correct_fills:
        per_score = fill_total / len(correct_fills)
        for q_num, correct in correct_fills.items():
            student_ans = student_fills.get(q_num, '')
            ai_result = ai_grader.grade_fill_blank(student_ans, correct, per_score)
            fill_score += ai_result['score']
            fill_details[q_num] = {
                'student': student_ans,
                'correct': correct,
                'score': ai_result['score'],
                'similarity': ai_result['similarity'],
                'feedback': ai_result['feedback'],
                'method': ai_result['method'],
                'details': ai_result.get('details', {})
            }
    
    # 大题评分
    essay_score = 0
    essay_details = {}
    essay_total = exam[3] or 0
    essay_text = answers.get('essay_text', '')
    
    if essay_total > 0 and essay_text:
        c.execute('SELECT subject FROM exams WHERE id = ?', (exam_id,))
        subject_row = c.fetchone()
        subject = subject_row[0] if subject_row else 'math'
        correct_essays = answer_key.get('essays', {})
        
        if correct_essays:
            per_essay_score = essay_total / len(correct_essays)
            for q_num, correct in correct_essays.items():
                ai_result = ai_grader.grade_essay(essay_text, correct, per_essay_score, subject.lower())
                essay_score += ai_result['score']
                essay_details[q_num] = ai_result
    
    # 保存成绩
    details = json.dumps({'choices': choice_details, 'fills': fill_details, 'essays': essay_details})
    
    c.execute('''INSERT OR REPLACE INTO scores 
                 (exam_id, student_id, choice_score, fill_score, essay_score, total_score, details, image_path)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (exam_id, student_id, choice_score, fill_score, essay_score, 
               choice_score + fill_score + essay_score, details, answers.get('image_path', '')))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'choice_score': round(choice_score, 2),
        'fill_score': round(fill_score, 2),
        'essay_score': round(essay_score, 2),
        'total_score': round(choice_score + fill_score + essay_score, 2),
        'details': {'choices': choice_details, 'fills': fill_details, 'essays': essay_details}
    })

# 6. 修改分数
@app.route('/api/scores/<int:score_id>', methods=['PUT'])
def update_score(score_id):
    data = request.json
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('''UPDATE scores SET 
                 choice_score = ?, fill_score = ?, essay_score = ?, total_score = ?, 
                 details = ?, teacher_comment = ?, manual_reviewed = ?
                 WHERE id = ?''',
              (data.get('choice_score'), data.get('fill_score'), 
               data.get('essay_score'), data.get('total_score'),
               json.dumps(data.get('details', {})),
               data.get('comment', ''), 1, score_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': '人工批阅已保存'})

@app.route('/api/scores/<int:score_id>/question', methods=['PUT'])
def update_question_score(score_id):
    data = request.json
    question_type = data.get('type')
    question_num = data.get('question')
    new_score = data.get('score')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT details, choice_score, fill_score, essay_score FROM scores WHERE id = ?', (score_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': '成绩不存在'}), 404
    
    details = json.loads(row[0]) if row[0] else {}
    choice_score = row[1]
    fill_score = row[2]
    essay_score = row[3]
    
    if question_type == 'fill' and 'fills' in details and question_num in details['fills']:
        details['fills'][question_num]['score'] = new_score
        details['fills'][question_num]['manual_reviewed'] = True
        fill_score = sum(d.get('score', 0) for d in details.get('fills', {}).values())
    
    elif question_type == 'essay' and 'essays' in details and question_num in details['essays']:
        details['essays'][question_num]['score'] = new_score
        details['essays'][question_num]['manual_reviewed'] = True
        essay_score = sum(d.get('score', 0) for d in details.get('essays', {}).values())
    
    total_score = choice_score + fill_score + essay_score
    
    c.execute('''UPDATE scores SET 
                 fill_score = ?, essay_score = ?, total_score = ?, details = ?,
                 teacher_comment = ?, manual_reviewed = ?
                 WHERE id = ?''',
              (fill_score, essay_score, total_score, json.dumps(details), '已人工批阅', 1, score_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '分数已更新', 'total_score': total_score, 'fill_score': fill_score, 'essay_score': essay_score})

# 7. 成绩统计
@app.route('/api/exams/<int:exam_id>/statistics')
def exam_statistics(exam_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('''SELECT s.total_score, st.student_no, st.name, s.id
                 FROM scores s JOIN students st ON s.student_id = st.id WHERE s.exam_id = ?''', (exam_id,))
    scores = c.fetchall()
    
    if not scores:
        return jsonify({'message': '暂无成绩数据'})
    
    total_scores = [s[0] for s in scores]
    count = len(scores)
    
    stats = {
        'count': count,
        'max_score': max(total_scores),
        'min_score': min(total_scores),
        'avg_score': round(sum(total_scores) / count, 2),
        'pass_rate': round(sum(1 for s in total_scores if s >= 60) / count * 100, 2),
        'excellent_rate': round(sum(1 for s in total_scores if s >= 90) / count * 100, 2),
        'scores': [{'student_no': s[1], 'name': s[2], 'score': s[0], 'score_id': s[3]} for s in scores]
    }
    
    conn.close()
    return jsonify(stats)

# 8. 成绩详情
@app.route('/api/scores/<int:score_id>/details')
def get_score_details(score_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('''SELECT s.*, st.student_no, st.name, e.name as exam_name, e.subject
                 FROM scores s JOIN students st ON s.student_id = st.id JOIN exams e ON s.exam_id = e.id
                 WHERE s.id = ?''', (score_id,))
    row = c.fetchone()
    
    if not row:
        return jsonify({'error': '成绩不存在'}), 404
    
    details = json.loads(row[7]) if row[7] else {}
    
    result = {
        'score_id': row[0], 'exam_id': row[1], 'student_id': row[2],
        'student_no': row[10], 'student_name': row[11], 'exam_name': row[12], 'subject': row[13],
        'choice_score': row[3], 'fill_score': row[4], 'essay_score': row[5],
        'total_score': row[6], 'details': details, 'image_path': row[8], 'graded_at': row[9]
    }
    
    conn.close()
    return jsonify(result)

# 9. 答题卡/模板
@app.route('/api/answer-sheet/generate', methods=['POST'])
def generate_answer_sheet():
    data = request.json
    filename = f"答题卡_{data.get('exam_name', '考试')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(DATA_FOLDER, filename)
    
    generator = AnswerSheetGenerator()
    generator.generate(filepath, data)
    
    return send_from_directory(DATA_FOLDER, filename, as_attachment=True)

@app.route('/api/answer-sheet/template/<template_type>')
def get_answer_sheet_template(template_type):
    filename = f"答题卡模板_{template_type}.pdf"
    filepath = os.path.join(DATA_FOLDER, filename)
    
    if not os.path.exists(filepath):
        generator = AnswerSheetGenerator()
        generator.generate_template(filepath, template_type)
    
    return send_from_directory(DATA_FOLDER, filename, as_attachment=True)

@app.route('/api/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# 静态文件
@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, '..'), 'frontend/index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(os.path.join(BASE_DIR, '..'), 'frontend/' + path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
