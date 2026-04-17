"""导出所有数据为CSV文件，方便Excel打开和数据迁移"""
import os
import sys
import csv

# 确保在项目目录下运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Student, Class, Exam, Question, QuestionGroup, AnswerSheet, ScoreDetail, ScoreSummary

EXPORT_DIR = 'exports'

def export_all():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    with app.app_context():
        # 1. 班级
        classes = Class.query.all()
        with open(os.path.join(EXPORT_DIR, '班级.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['班级ID', '班级名称', '年级', '班主任'])
            for c in classes:
                w.writerow([c.id, c.name, c.grade, c.teacher])
        print(f'  ✅ 班级.csv ({len(classes)}条)')

        # 2. 学生
        students = Student.query.all()
        with open(os.path.join(EXPORT_DIR, '学生.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['学号', '姓名', '班级'])
            for s in students:
                cname = s.class_info.name if s.class_info else ''
                w.writerow([s.student_id, s.name, cname])
        print(f'  ✅ 学生.csv ({len(students)}条)')

        # 3. 考试
        exams = Exam.query.all()
        with open(os.path.join(EXPORT_DIR, '考试.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['考试ID', '考试名称', '科目', '总分', '日期', '状态'])
            for e in exams:
                w.writerow([e.id, e.name, e.subject, e.total_score, e.exam_date, e.status])
        print(f'  ✅ 考试.csv ({len(exams)}条)')

        # 4. 题目
        questions = Question.query.all()
        with open(os.path.join(EXPORT_DIR, '题目.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['考试名称', '大题名称', '题号', '类型', '满分', '题目内容', '参考答案'])
            for q in questions:
                exam_name = q.group.exam.name if q.group and q.group.exam else ''
                group_name = q.group.name if q.group else ''
                w.writerow([exam_name, group_name, q.question_number, q.question_type,
                           q.total_points, q.content_text, q.reference_answer])
        print(f'  ✅ 题目.csv ({len(questions)}条)')

        # 5. 成绩汇总
        summaries = ScoreSummary.query.all()
        with open(os.path.join(EXPORT_DIR, '成绩汇总.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['考试', '学号', '姓名', '班级', '总分', '班级排名', '年级排名'])
            for s in summaries:
                w.writerow([s.exam.name if s.exam else '', s.student_id,
                           s.student.name if s.student else '',
                           s.class_info.name if s.class_info else '',
                           s.total_score, s.rank_in_class, s.rank_in_grade])
        print(f'  ✅ 成绩汇总.csv ({len(summaries)}条)')

        # 6. 逐题得分
        details = ScoreDetail.query.all()
        with open(os.path.join(EXPORT_DIR, '逐题得分.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['学号', '姓名', '考试', '题号', '满分', 'AI评分', '最终分数', '教师评语'])
            for d in details:
                q = d.question
                sheet = d.answer_sheet
                w.writerow([
                    sheet.student_id if sheet else '',
                    sheet.student.name if sheet and sheet.student else '',
                    sheet.exam.name if sheet and sheet.exam else '',
                    q.question_number if q else '',
                    q.total_points if q else '',
                    d.ai_score if d.ai_score >= 0 else '',
                    d.final_score if d.final_score >= 0 else '',
                    d.teacher_comment
                ])
        print(f'  ✅ 逐题得分.csv ({len(details)}条)')

    print(f'\n📁 所有文件已导出到 {EXPORT_DIR}/ 目录')

if __name__ == '__main__':
    print('正在导出数据...\n')
    export_all()
