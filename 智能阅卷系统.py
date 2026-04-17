import os
import csv
import io
import base64
import json
import uuid
import math
from datetime import datetime
from functools import wraps
from collections import defaultdict

import jinja2
from flask import (Flask, render_template_string, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, send_file)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import reportlab.lib.pagesizes as pagesizes
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

TEMPLATES = {
    'admin_answer_sheet_design.html': r"""{% extends "base.html" %}
{% block title %}答题卡设计 - {{ exam.name }}{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-file-earmark-ruled"></i> 答题卡设计 - {{ exam.name }}</h4>
        <a href="{{ url_for('admin_exams') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> 返回</a>
    </div>

    <div class="row g-4">
        <div class="col-md-6">
            <div class="card p-4">
                <h5>答题卡结构</h5>
                {% for g, qs in questions_by_group %}
                <div class="mt-3">
                    <strong>{{ g.name }}</strong> <span class="badge bg-primary">{{ g.total_points }}分</span>
                    <ul class="mt-1 small">
                        {% for q in qs %}<li>第{{ q.question_number }}题 ({{ q.total_points }}分)</li>{% endfor %}
                    </ul>
                </div>
                {% endfor %}
                {% if not questions_by_group or not questions_by_group[0][1] %}
                <div class="text-muted mt-3">请先在"题目设置"中添加题目</div>
                {% endif %}
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-4">
                <h5>生成答题卡PDF</h5>
                <p class="text-muted">系统将根据题目结构自动生成答题卡PDF，包含姓名、学号填写区和各题答题区。</p>
                <form method="POST" action="{{ url_for('admin_answer_sheet_generate', id=exam.id) }}">
                    <button type="submit" class="btn btn-primary btn-lg w-100"><i class="bi bi-file-earmark-pdf"></i> 生成答题卡PDF</button>
                </form>

                <hr>
                <h5 class="mt-3">后续操作</h5>
                <ol class="small">
                    <li>生成答题卡PDF → 打印发给学生</li>
                    <li>学生填写后扫描/拍照 → <a href="{{ url_for('admin_upload_sheets', id=exam.id) }}">批量上传答题卡</a></li>
                    <li>AI辅助批改 → 教师确认 → 成绩汇总</li>
                </ol>
                <a href="{{ url_for('admin_upload_sheets', id=exam.id) }}" class="btn btn-success mt-2">
                    <i class="bi bi-upload"></i> 批量上传答题卡图片
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    'admin_change_password.html': r"""{% extends "base.html" %}
{% block title %}修改密码{% endblock %}
{% block content %}
<div class="container mt-4"><div class="row justify-content-center"><div class="col-md-5">
    <h4 class="mb-3"><i class="bi bi-key"></i> 修改密码</h4>
    <div class="card p-4"><form method="POST">
        <div class="mb-3"><label class="form-label">原密码</label><input type="password" name="old_password" class="form-control" required></div>
        <div class="mb-3"><label class="form-label">新密码</label><input type="password" name="new_password" class="form-control" required minlength="6"></div>
        <div class="mb-3"><label class="form-label">确认新密码</label><input type="password" name="confirm_password" class="form-control" required></div>
        <button type="submit" class="btn btn-primary"><i class="bi bi-check-lg"></i> 修改</button>
    </form></div>
</div></div></div>
{% endblock %}
""",
    'admin_class_form.html': r"""{% extends "base.html" %}
{% block title %}{{ '编辑' if action == 'edit' else '添加' }}班级{% endblock %}
{% block content %}
<div class="container mt-4"><div class="row justify-content-center"><div class="col-md-6">
    <h4 class="mb-3">{{ '编辑' if action == 'edit' else '添加' }}班级</h4>
    <div class="card p-4">
        <form method="POST">
            <div class="mb-3"><label class="form-label">班级名称</label><input type="text" name="name" class="form-control" value="{{ cls.name if action == 'edit' else '' }}" placeholder="如：高三1班" required></div>
            <div class="mb-3"><label class="form-label">年级</label><input type="text" name="grade" class="form-control" value="{{ cls.grade if action == 'edit' else '' }}" placeholder="如：高三"></div>
            <div class="mb-3"><label class="form-label">班主任</label><input type="text" name="teacher" class="form-control" value="{{ cls.teacher if action == 'edit' else '' }}"></div>
            <button type="submit" class="btn btn-primary"><i class="bi bi-check-lg"></i> 保存</button>
            <a href="{{ url_for('admin_classes') }}" class="btn btn-outline-secondary">取消</a>
        </form>
    </div>
</div></div></div>
{% endblock %}
""",
    'admin_classes.html': r"""{% extends "base.html" %}
{% block title %}班级管理{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-building"></i> 班级管理</h4>
        <a href="{{ url_for('admin_class_add') }}" class="btn btn-primary btn-sm"><i class="bi bi-plus-circle"></i> 添加班级</a>
    </div>
    <div class="row g-4">
    {% for c in classes %}
    <div class="col-md-4">
        <div class="card p-4">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h5 class="mb-1">{{ c.name }}</h5>
                    <span class="text-muted">{{ c.grade }} · {{ c.teacher }}</span>
                </div>
                <span class="badge bg-primary fs-6">{{ c.student_count }}人</span>
            </div>
            <div class="d-flex gap-2 mt-3">
                <a href="{{ url_for('admin_students', class_id=c.id) }}" class="btn btn-sm btn-outline-primary"><i class="bi bi-people"></i> 学生</a>
                <a href="{{ url_for('admin_class_edit', id=c.id) }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-pencil"></i></a>
                <form method="POST" action="{{ url_for('admin_class_delete', id=c.id) }}" onsubmit="return confirm('删除班级？学生不会被删除')">
                    <button type="submit" class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
                </form>
            </div>
        </div>
    </div>
    {% endfor %}
    {% if not classes %}
    <div class="col-12"><div class="card p-5 text-center text-muted"><i class="bi bi-building" style="font-size:3rem"></i><p class="mt-2">暂无班级，点击右上角添加</p></div></div>
    {% endif %}
    </div>
</div>
{% endblock %}
""",
    'admin_dashboard.html': r"""{% extends "base.html" %}
{% block title %}管理控制台{% endblock %}
{% block content %}
<div class="container-fluid mt-3">
<div class="row">
<div class="col-lg-2 col-md-3">
    <div class="card p-3 nav-side">
        <h6 class="text-muted mb-2"><i class="bi bi-menu-button-wide"></i> 导航</h6>
        <nav class="nav flex-column">
            <a class="nav-link active" href="{{ url_for('admin_dashboard') }}"><i class="bi bi-speedometer2"></i> 控制台</a>
            <a class="nav-link" href="{{ url_for('admin_classes') }}"><i class="bi bi-building"></i> 班级管理</a>
            <a class="nav-link" href="{{ url_for('admin_students') }}"><i class="bi bi-people"></i> 学生管理</a>
            <a class="nav-link" href="{{ url_for('admin_students_batch') }}"><i class="bi bi-person-plus"></i> 批量录入</a>
            <hr>
            <a class="nav-link" href="{{ url_for('admin_exams') }}"><i class="bi bi-journal-text"></i> 考试管理</a>
            <a class="nav-link" href="{{ url_for('admin_grading', exam_id=1) if exam_count > 0 else '#' }}"><i class="bi bi-pencil-square"></i> 批改</a>
            <hr>
            <a class="nav-link" href="{{ url_for('admin_change_password') }}"><i class="bi bi-key"></i> 改密码</a>
            <a class="nav-link" href="{{ url_for('admin_logout') }}"><i class="bi bi-box-arrow-right"></i> 退出</a>
        </nav>
    </div>
</div>
<div class="col-lg-10 col-md-9">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-speedometer2"></i> 控制台 <span class="ai-badge">{{ ai_provider }}</span></h4>
        <span class="text-muted">{{ session.get('admin_username','admin') }}</span>
    </div>
    <div class="row g-3 mb-4">
        <div class="col-md-2"><div class="card stat-card p-3"><div class="text-muted small">班级</div><div class="fs-3 fw-bold">{{ class_count }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#059669"><div class="text-muted small">学生</div><div class="fs-3 fw-bold">{{ student_count }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#7c3aed"><div class="text-muted small">考试</div><div class="fs-3 fw-bold">{{ exam_count }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#dc2626"><div class="text-muted small">待批改</div><div class="fs-3 fw-bold text-danger">{{ ungraded }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#0891b2"><div class="text-muted small">答题卡</div><div class="fs-3 fw-bold">{{ sheet_count }}</div></div></div>
    </div>

    <div class="row g-3 mb-4">
        <div class="col-md-4"><a href="{{ url_for('admin_exams') }}" class="card feature-card p-3 text-decoration-none text-dark d-block">
            <div class="d-flex align-items-center"><i class="bi bi-journal-text text-primary me-3" style="font-size:1.8rem"></i><div><h6 class="mb-0">考试管理</h6><small class="text-muted">创建考试·设置题目·分数</small></div></div></a></div>
        <div class="col-md-4"><a href="{{ url_for('admin_students_batch') }}" class="card feature-card p-3 text-decoration-none text-dark d-block">
            <div class="d-flex align-items-center"><i class="bi bi-person-plus text-success me-3" style="font-size:1.8rem"></i><div><h6 class="mb-0">批量录入</h6><small class="text-muted">班级学生·答题卡上传</small></div></div></a></div>
        <div class="col-md-4"><a href="{{ url_for('admin_classes') }}" class="card feature-card p-3 text-decoration-none text-dark d-block">
            <div class="d-flex align-items-center"><i class="bi bi-building text-warning me-3" style="font-size:1.8rem"></i><div><h6 class="mb-0">班级管理</h6><small class="text-muted">建班·分班·统计</small></div></div></a></div>
    </div>

    {% if exams %}
    <div class="card p-4">
        <h5>最近考试</h5>
        <div class="table-responsive mt-2">
            <table class="table table-hover mb-0">
                <thead class="table-light"><tr><th>考试</th><th>科目</th><th>总分</th><th>状态</th><th>操作</th></tr></thead>
                <tbody>
                {% for e in exams %}
                <tr>
                    <td>{{ e.name }}</td><td>{{ e.subject }}</td><td>{{ e.total_score }}</td>
                    <td><span class="badge {{ 'bg-success' if e.status=='已发布' else ('bg-warning text-dark' if e.status=='已结束' else 'bg-info') }}">{{ e.status }}</span></td>
                    <td>
                        <a href="{{ url_for('admin_exam_setup', id=e.id) }}" class="btn btn-sm btn-outline-primary">设置</a>
                        <a href="{{ url_for('admin_grading', exam_id=e.id) }}" class="btn btn-sm btn-outline-success">批改</a>
                        <a href="{{ url_for('admin_exam_analysis', id=e.id) }}" class="btn btn-sm btn-outline-info">分析</a>
                    </td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endif %}
</div></div></div>
{% endblock %}
""",
    'admin_exam_analysis.html': r"""{% extends "base.html" %}
{% block title %}成绩分析 - {{ exam.name }}{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-bar-chart"></i> 成绩分析 - {{ exam.name }}</h4>
        <div class="d-flex gap-2">
            <a href="{{ url_for('admin_exam_export', id=exam.id) }}" class="btn btn-success btn-sm"><i class="bi bi-download"></i> 导出CSV</a>
            {% if exam.status == '已结束' and exam.status != '已发布' %}
            <form method="POST" action="{{ url_for('admin_exam_publish', id=exam.id) }}">
                <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-broadcast"></i> 发布成绩</button>
            </form>
            {% endif %}
            <a href="{{ url_for('admin_exams') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> 返回</a>
        </div>
    </div>

    {% if stats %}
    <!-- 总览 -->
    <div class="row g-3 mb-4">
        <div class="col-md-2"><div class="card stat-card p-3"><div class="text-muted small">人数</div><div class="fs-4 fw-bold">{{ stats.count }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#059669"><div class="text-muted small">平均分</div><div class="fs-4 fw-bold">{{ stats.avg }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#7c3aed"><div class="text-muted small">中位数</div><div class="fs-4 fw-bold">{{ stats.median }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#0891b2"><div class="text-muted small">最高分</div><div class="fs-4 fw-bold text-success">{{ stats.max }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#dc2626"><div class="text-muted small">最低分</div><div class="fs-4 fw-bold text-danger">{{ stats.min }}</div></div></div>
        <div class="col-md-2"><div class="card stat-card p-3" style="border-left-color:#d97706"><div class="text-muted small">标准差</div><div class="fs-4 fw-bold">{{ stats.stdev }}</div></div></div>
    </div>

    <div class="row g-3 mb-4">
        <div class="col-md-3"><div class="card p-3 text-center"><div class="fs-2 fw-bold text-success">{{ stats.pass_rate }}%</div><div class="text-muted">及格率</div></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><div class="fs-2 fw-bold text-primary">{{ stats.excellent_rate }}%</div><div class="text-muted">优秀率</div></div></div>
    </div>

    <!-- 分数段分布 -->
    {% if stats.bins %}
    <div class="card p-4 mb-4">
        <h5>分数段分布</h5>
        <div class="mt-3">
        {% for label, count in stats.bins.items() %}
        <div class="d-flex align-items-center mb-1">
            <span style="width:80px" class="small">{{ label }}</span>
            <div class="progress flex-grow-1" style="height:22px">
                <div class="progress-bar {% if label.split('-')[0]|int >= exam.total_score * 0.9 %}bg-success{% elif label.split('-')[0]|int >= exam.total_score * 0.6 %}bg-info{% else %}bg-danger{% endif %}"
                     style="width:{{ (count / stats.count * 100)|int if stats.count > 0 else 0 }}%">{{ count }}人</div>
            </div>
        </div>
        {% endfor %}
        </div>
    </div>
    {% endif %}

    {% endif %}

    <!-- 各题得分分析 -->
    {% if question_stats %}
    <div class="card p-4 mb-4">
        <h5>各题得分分析</h5>
        <div class="table-responsive mt-2">
            <table class="table table-sm table-bordered">
                <thead class="table-light"><tr><th>题号</th><th>满分</th><th>平均分</th><th>得分率</th><th>零分人数</th><th>满分人数</th></tr></thead>
                <tbody>
                {% for qs in question_stats %}
                <tr>
                    <td>第{{ qs.question.question_number }}题</td><td>{{ qs.question.total_points }}</td>
                    <td>{{ qs.avg }}</td>
                    <td>
                        <div class="progress" style="height:18px;min-width:60px">
                            <div class="progress-bar {% if qs.rate >= 80 %}bg-success{% elif qs.rate >= 60 %}bg-warning{% else %}bg-danger{% endif %}"
                                 style="width:{{ qs.rate|round }}%">{{ qs.rate|round }}%</div>
                        </div>
                    </td>
                    <td>{{ qs.zero_count }}</td><td>{{ qs.full_count }}</td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endif %}

    <!-- 班级对比 -->
    {% if class_stats %}
    <div class="card p-4 mb-4">
        <h5>班级对比</h5>
        <div class="table-responsive mt-2">
            <table class="table table-sm table-bordered">
                <thead class="table-light"><tr><th>班级</th><th>人数</th><th>平均分</th><th>最高分</th><th>最低分</th><th>及格率</th></tr></thead>
                <tbody>
                {% for cs in class_stats %}
                <tr>
                    <td>{{ cs.class.name }}</td><td>{{ cs.count }}</td><td>{{ cs.avg }}</td>
                    <td>{{ cs.max }}</td><td>{{ cs.min }}</td>
                    <td><span class="badge {{ 'bg-success' if cs.pass_rate >= 80 else 'bg-warning text-dark' }}">{{ cs.pass_rate }}%</span></td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endif %}

    <!-- 成绩明细 -->
    <div class="card p-4">
        <h5>成绩汇总</h5>
        <div class="table-responsive mt-2">
            <table class="table table-sm table-hover">
                <thead class="table-light">
                    <tr><th>年级排名</th><th>班级排名</th><th>学号</th><th>姓名</th><th>班级</th><th>总分</th><th>答题卡</th></tr>
                </thead>
                <tbody>
                {% for sm in summaries %}
                <tr>
                    <td>{{ sm.rank_in_grade or '-' }}</td>
                    <td>{{ sm.rank_in_class or '-' }}</td>
                    <td>{{ sm.student_id }}</td><td>{{ sm.student.name }}</td>
                    <td>{{ sm.student.class_info.name if sm.student.class_info else '-' }}</td>
                    <td class="fw-bold">{{ sm.total_score }}</td>
                    <td>
                        {% set sheet = sm.student.answer_sheets|selectattr('exam_id','equalto',exam.id)|list %}
                        {% if sheet and sheet[0].annotated_path %}
                        <a href="/{{ sheet[0].annotated_path }}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-image"></i></a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
""",
    'admin_exam_form.html': r"""{% extends "base.html" %}
{% block title %}{{ '编辑' if action == 'edit' else '创建' }}考试{% endblock %}
{% block content %}
<div class="container mt-4"><div class="row justify-content-center"><div class="col-md-7">
    <h4 class="mb-3">{{ '编辑' if action == 'edit' else '创建' }}考试</h4>
    <div class="card p-4"><form method="POST">
        <div class="mb-3"><label class="form-label">考试名称</label><input type="text" name="name" class="form-control" value="{{ exam.name if action == 'edit' else '' }}" placeholder="如：2024期末考试" required></div>
        <div class="row g-3">
            <div class="col-md-4"><label class="form-label">科目</label><input type="text" name="subject" class="form-control" value="{{ exam.subject if action == 'edit' else '数学' }}" required></div>
            <div class="col-md-4"><label class="form-label">满分</label><input type="number" name="total_score" class="form-control" value="{{ exam.total_score if action == 'edit' else 100 }}" required></div>
            <div class="col-md-4"><label class="form-label">日期</label><input type="date" name="exam_date" class="form-control" value="{{ exam.exam_date if action == 'edit' else '' }}"></div>
        </div>
        <button type="submit" class="btn btn-primary mt-3"><i class="bi bi-check-lg"></i> 保存</button>
        <a href="{{ url_for('admin_exams') }}" class="btn btn-outline-secondary mt-3">取消</a>
    </form></div>
</div></div></div>
{% endblock %}
""",
    'admin_exam_setup.html': r"""{% extends "base.html" %}
{% block title %}题目设置 - {{ exam.name }}{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-gear"></i> {{ exam.name }} - 题目与分数设置</h4>
        <a href="{{ url_for('admin_exams') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> 返回</a>
    </div>

    <div class="card p-3 mb-3">
        <div class="d-flex gap-3 flex-wrap">
            <span class="badge bg-primary">{{ exam.subject }}</span>
            <span>总分：<strong>{{ exam.total_score }}</strong></span>
            <span>已设：{% set ns = namespace(t=0) %}{% for g in groups %}{% set ns.t = ns.t + g.total_points %}{% endfor %}<strong>{{ ns.t }}</strong></span>
        </div>
    </div>

    <!-- 添加题目组 -->
    <div class="card p-4 mb-3">
        <h6><i class="bi bi-plus-circle"></i> 添加题目组（大题）</h6>
        <form method="POST" action="{{ url_for('admin_group_add', exam_id=exam.id) }}" class="row g-2 mt-2">
            <div class="col-md-3"><input type="text" name="name" class="form-control form-control-sm" placeholder="如：一、选择题" required></div>
            <div class="col-md-2">
                <select name="question_type" class="form-select form-select-sm">
                    <option>选择题</option><option>填空题</option><option>解答题</option><option>计算题</option><option>证明题</option><option>作文</option>
                </select>
            </div>
            <div class="col-md-2"><input type="number" name="total_points" class="form-control form-control-sm" placeholder="总分" value="0"></div>
            <div class="col-md-2"><input type="number" name="sort_order" class="form-control form-control-sm" placeholder="排序" value="{{ groups|length + 1 }}"></div>
            <div class="col-md-2"><button type="submit" class="btn btn-sm btn-primary w-100">添加</button></div>
        </form>
    </div>

    <!-- 各题目组 -->
    {% for g in groups %}
    <div class="card p-4 mb-3">
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0">{{ g.name }} <span class="badge bg-primary">{{ g.total_points }}分</span> <span class="badge bg-info">{{ g.question_type }}</span></h5>
            <form method="POST" action="{{ url_for('admin_group_delete', id=g.id) }}" onsubmit="return confirm('删除此大题及所有小题？')">
                <button type="submit" class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
            </form>
        </div>

        <!-- 小题列表 -->
        {% if g.questions %}
        <div class="table-responsive mt-3">
            <table class="table table-sm table-bordered mb-0">
                <thead class="table-light"><tr><th>题号</th><th>分值</th><th>内容</th><th>参考答案</th><th>操作</th></tr></thead>
                <tbody>
                {% for q in g.questions %}
                <tr>
                    <td><strong>{{ q.question_number }}</strong></td>
                    <td>{{ q.total_points }}</td>
                    <td class="text-truncate" style="max-width:200px">{{ q.content_text[:60] }}{% if not q.content_text %}-{% endif %}</td>
                    <td>{% if q.reference_answer %}<i class="bi bi-check-circle text-success"></i>{% else %}<i class="bi bi-x-circle text-danger"></i>{% endif %}</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <a href="{{ url_for('admin_question_edit', id=q.id) }}" class="btn btn-outline-secondary"><i class="bi bi-pencil"></i></a>
                            <form method="POST" action="{{ url_for('admin_generate_answer', id=q.id) }}"><button type="submit" class="btn btn-outline-warning" title="AI生成答案"><i class="bi bi-robot"></i></button></form>
                            <form method="POST" action="{{ url_for('admin_question_delete', id=q.id) }}" onsubmit="return confirm('删除？')"><button class="btn btn-outline-danger"><i class="bi bi-trash"></i></button></form>
                        </div>
                    </td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <!-- 添加小题 -->
        <form method="POST" action="{{ url_for('admin_question_add', group_id=g.id) }}" enctype="multipart/form-data" class="row g-2 mt-3">
            <div class="col-md-1"><input type="text" name="question_number" class="form-control form-control-sm" placeholder="题号" required></div>
            <div class="col-md-1"><input type="number" name="total_points" class="form-control form-control-sm" placeholder="分值" value="5" step="0.5" required></div>
            <div class="col-md-4"><input type="text" name="content_text" class="form-control form-control-sm" placeholder="题目内容（可选）"></div>
            <div class="col-md-2"><input type="file" name="image" class="form-control form-control-sm" accept="image/*"></div>
            <div class="col-md-1"><button type="submit" class="btn btn-sm btn-success w-100"><i class="bi bi-plus"></i></button></div>
        </form>
    </div>
    {% endfor %}

    {% if not groups %}
    <div class="card p-5 text-center text-muted"><i class="bi bi-list-task" style="font-size:3rem"></i><p class="mt-2">请先添加题目组（大题），再添加小题</p></div>
    {% endif %}
</div>
{% endblock %}
""",
    'admin_exams.html': r"""{% extends "base.html" %}
{% block title %}考试管理{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-journal-text"></i> 考试管理</h4>
        <a href="{{ url_for('admin_exam_add') }}" class="btn btn-primary btn-sm"><i class="bi bi-plus-circle"></i> 创建考试</a>
    </div>
    <div class="card">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light"><tr><th>考试名称</th><th>科目</th><th>满分</th><th>答题卡</th><th>已出分</th><th>状态</th><th>操作</th></tr></thead>
                <tbody>
                {% for e in exams %}
                <tr>
                    <td><strong>{{ e.name }}</strong><br><small class="text-muted">{{ e.exam_date }}</small></td>
                    <td>{{ e.subject }}</td><td>{{ e.total_score }}</td>
                    <td>{{ e.sheet_count }}</td><td>{{ e.student_count }}</td>
                    <td><span class="badge {{ 'bg-success' if e.status=='已发布' else ('bg-warning text-dark' if e.status=='已结束' else 'bg-info') }}">{{ e.status }}</span></td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <a href="{{ url_for('admin_exam_setup', id=e.id) }}" class="btn btn-outline-primary" title="题目设置"><i class="bi bi-gear"></i></a>
                            <a href="{{ url_for('admin_answer_sheet_design', id=e.id) }}" class="btn btn-outline-secondary" title="答题卡"><i class="bi bi-file-earmark-ruled"></i></a>
                            <a href="{{ url_for('admin_upload_sheets', id=e.id) }}" class="btn btn-outline-success" title="上传答题卡"><i class="bi bi-upload"></i></a>
                            <a href="{{ url_for('admin_grading', exam_id=e.id) }}" class="btn btn-outline-warning" title="批改"><i class="bi bi-pencil-square"></i></a>
                            <a href="{{ url_for('admin_exam_analysis', id=e.id) }}" class="btn btn-outline-info" title="分析"><i class="bi bi-bar-chart"></i></a>
                            <a href="{{ url_for('admin_exam_edit', id=e.id) }}" class="btn btn-outline-dark" title="编辑"><i class="bi bi-pencil"></i></a>
                        </div>
                    </td>
                </tr>
                {% endfor %}
                {% if not exams %}
                <tr><td colspan="7" class="text-center text-muted py-4">暂无考试</td></tr>
                {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
""",
    'admin_grading.html': r"""{% extends "base.html" %}
{% block title %}批改 - {{ exam.name }}{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-pencil-square"></i> 批改管理 - {{ exam.name }} <span class="ai-badge">AI</span></h4>
        <div class="d-flex gap-2">
            <form method="POST" action="{{ url_for('admin_grading_finalize', exam_id=exam.id) }}" onsubmit="return confirm('完成批改？将生成成绩汇总和排名')">
                <button type="submit" class="btn btn-success btn-sm"><i class="bi bi-check2-all"></i> 完成批改</button>
            </form>
            <a href="{{ url_for('admin_exams') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> 返回</a>
        </div>
    </div>

    <div class="card p-3 mb-3">
        <div class="d-flex gap-3 small">
            <span>答题卡：<strong>{{ sheets|length }}</strong></span>
            <span>题目数：<strong>{{ questions|length }}</strong></span>
            <span>总分：<strong>{{ exam.total_score }}</strong></span>
        </div>
    </div>

    <div class="card">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light"><tr><th>学号</th><th>姓名</th><th>班级</th><th>已批/总题</th><th>总分</th><th>操作</th></tr></thead>
                <tbody>
                {% for s in sheets %}
                <tr>
                    <td>{{ s.student_id }}</td>
                    <td>{{ s.student.name if s.student else '-' }}</td>
                    <td>{{ s.student.class_info.name if s.student and s.student.class_info else '-' }}</td>
                    <td>
                        <div class="progress" style="height:18px;min-width:100px">
                            {% if s.total_q > 0 %}
                            <div class="progress-bar bg-{{ 'success' if s.graded_count == s.total_q else 'warning' }}"
                                 style="width:{{ (s.graded_count/s.total_q*100)|int }}%">{{ s.graded_count }}/{{ s.total_q }}</div>
                            {% endif %}
                        </div>
                    </td>
                    <td class="fw-bold">{{ s.total_score if s.total_score >= 0 else '-' }}</td>
                    <td><a href="{{ url_for('admin_grading_sheet', sheet_id=s.id) }}" class="btn btn-sm btn-outline-primary"><i class="bi bi-pencil-square"></i> 批改</a></td>
                </tr>
                {% endfor %}
                {% if not sheets %}
                <tr><td colspan="6" class="text-center text-muted py-4">暂无答题卡，请先上传</td></tr>
                {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
""",
    'admin_grading_sheet.html': r"""{% extends "base.html" %}
{% block title %}批改答题卡{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-pencil-square"></i> 批改 - {{ sheet.student.name }}({{ sheet.student_id }}) <span class="ai-badge">AI</span></h4>
        <div class="d-flex gap-2">
            <form method="POST" action="{{ url_for('admin_grading_score', detail_id=details[0].id) if details else '#' }}">
                <input type="hidden" name="action" value="batch_ai">
                <button type="submit" class="btn btn-warning btn-sm" {% if not details %}disabled{% endif %}><i class="bi bi-robot"></i> 批量AI批改</button>
            </form>
            <a href="{{ url_for('admin_grading', exam_id=exam.id) }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> 返回</a>
        </div>
    </div>

    <div class="row g-4">
        <!-- 答题卡 -->
        <div class="col-md-5">
            <div class="card p-3">
                <h6><i class="bi bi-file-earmark-ruled"></i> 答题卡
                    {% if sheet.pdf_path %}
                    <span class="badge bg-danger"><i class="bi bi-file-earmark-pdf-fill"></i> PDF{{ ' (' ~ sheet.page_number ~ '页)' if sheet.page_number > 1 else '' }}</span>
                    {% elif sheet.image_path %}
                    <span class="badge bg-info"><i class="bi bi-image"></i> 图片</span>
                    {% endif %}
                </h6>

                {% if sheet.pdf_path %}
                <!-- PDF答题卡：用iframe或链接展示 -->
                <div class="mt-2">
                    {% if sheet.annotated_path %}
                    <iframe src="/{{ sheet.annotated_path }}" width="100%" height="500" style="border:1px solid #e2e8f0;border-radius:8px"></iframe>
                    <div class="d-flex gap-2 mt-2 flex-wrap">
                        <a href="/{{ sheet.pdf_path }}" target="_blank" class="btn btn-sm btn-outline-danger"><i class="bi bi-file-earmark-pdf"></i> 原始PDF</a>
                        <a href="/{{ sheet.annotated_path }}" target="_blank" class="btn btn-sm btn-success"><i class="bi bi-file-earmark-check"></i> 标注PDF（含评分）</a>
                    </div>
                    {% else %}
                    <iframe src="/{{ sheet.pdf_path }}" width="100%" height="500" style="border:1px solid #e2e8f0;border-radius:8px"></iframe>
                    <a href="/{{ sheet.pdf_path }}" target="_blank" class="btn btn-sm btn-outline-danger mt-2"><i class="bi bi-file-earmark-pdf"></i> 全屏查看PDF</a>
                    {% endif %}
                </div>
                {% elif sheet.image_path %}
                <img src="/{{ sheet.annotated_path or sheet.image_path }}" class="img-fluid rounded mt-2" id="sheetImg">
                {% if sheet.annotated_path %}
                <div class="mt-2">
                    <a href="/{{ sheet.image_path }}" target="_blank" class="btn btn-sm btn-outline-secondary">查看原图</a>
                    <a href="/{{ sheet.annotated_path }}" target="_blank" class="btn btn-sm btn-outline-primary">查看标注PDF</a>
                </div>
                {% endif %}
                {% else %}
                <div class="text-center text-muted py-4">无答题卡</div>
                {% endif %}

                <div class="mt-3 text-center">
                    <div class="score-circle {% if sheet.total_score >= exam.total_score * 0.8 %}score-high{% elif sheet.total_score >= exam.total_score * 0.6 %}score-mid{% elif sheet.total_score >= 0 %}score-low{% endif %}">
                        {{ sheet.total_score if sheet.total_score >= 0 else '-' }}
                    </div>
                    <div class="small text-muted mt-1">总分 / {{ exam.total_score }}</div>
                </div>
            </div>
        </div>

        <!-- 逐题评分 -->
        <div class="col-md-7">
            {% for sd in details %}
            {% set q = sd.question %}
            {% set score = sd.final_score if sd.final_score >= 0 else (sd.ai_score if sd.ai_score >= 0 else None) %}
            <div class="card p-3 mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">第{{ q.question_number }}题 <span class="badge bg-secondary">{{ q.total_points }}分</span></h6>
                    {% if score != None %}
                    <div class="d-flex align-items-center gap-2">
                        <span class="fw-bold {% if score >= q.total_points * 0.8 %}text-success{% elif score >= q.total_points * 0.6 %}text-warning{% else %}text-danger{% endif %}">
                            {{ score }}/{{ q.total_points }}
                        </span>
                        {% if sd.final_score >= 0 %}<span class="badge bg-success">已确认</span>{% elif sd.ai_score >= 0 %}<span class="badge bg-warning text-dark">AI评分</span>{% else %}<span class="badge bg-danger">未批</span>{% endif %}
                    </div>
                    {% endif %}
                </div>

                {% if q.content_text %}
                <div class="question-box mt-2 small">{{ q.content_text }}</div>
                {% endif %}

                {% if sd.ai_feedback %}
                {% set fb = sd.ai_feedback %}
                {% if fb.startswith('{') %}
                {% set fb_data = fb | tojson %}
                <div class="alert alert-info mt-2 py-1 px-2 small">
                    <i class="bi bi-robot"></i> AI：{{ fb[:200] }}
                </div>
                {% else %}
                <div class="alert alert-info mt-2 py-1 px-2 small"><i class="bi bi-robot"></i> {{ fb[:200] }}</div>
                {% endif %}
                {% endif %}

                <form method="POST" action="{{ url_for('admin_grading_score', detail_id=sd.id) }}" class="row g-2 mt-2 align-items-end">
                    {% if sd.ai_score < 0 %}
                    <div class="col-md-3"><input type="hidden" name="action" value="ai_grade">
                        <button type="submit" class="btn btn-sm btn-warning w-100"><i class="bi bi-robot"></i> AI批改</button></div>
                    {% else %}
                    <div class="col-md-3"><input type="hidden" name="action" value="confirm">
                        <input type="number" name="final_score" class="form-control form-control-sm" value="{{ sd.ai_score }}" min="0" max="{{ q.total_points }}" step="0.5"></div>
                    <div class="col-md-4"><input type="text" name="teacher_comment" class="form-control form-control-sm" placeholder="评语"></div>
                    <div class="col-md-2"><button type="submit" class="btn btn-sm btn-success w-100">确认</button></div>
                    {% endif %}
                </form>
            </div>
            {% endfor %}

            {% if not details %}
            <div class="card p-4 text-center text-muted">无评分明细，请确认已设置题目</div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
""",
    'admin_login.html': r"""{% extends "base.html" %}
{% block title %}管理员登录{% endblock %}
{% block content %}
<div class="container mt-5"><div class="row justify-content-center"><div class="col-md-5">
    <div class="card p-4"><div class="text-center mb-4">
        <i class="bi bi-shield-lock" style="font-size:3rem;color:var(--pri)"></i><h4 class="mt-2">管理员登录</h4>
    </div>
    <form method="POST">
        <div class="mb-3"><input type="text" class="form-control" name="username" placeholder="用户名" required autofocus></div>
        <div class="mb-3"><input type="password" class="form-control" name="password" placeholder="密码" required></div>
        <button type="submit" class="btn btn-primary w-100"><i class="bi bi-box-arrow-in-right"></i> 登录</button>
    </form>
    <div class="text-center mt-3"><small class="text-muted">默认: admin / admin123</small></div>
</div></div></div></div>
{% endblock %}
""",
    'admin_question_edit.html': r"""{% extends "base.html" %}
{% block title %}编辑题目{% endblock %}
{% block content %}
<div class="container mt-4"><div class="row justify-content-center"><div class="col-md-8">
    <h4 class="mb-3">编辑题目 第{{ question.question_number }}题</h4>
    <div class="card p-4"><form method="POST" enctype="multipart/form-data">
        <div class="row g-3">
            <div class="col-md-3"><label class="form-label">题号</label><input type="text" name="question_number" class="form-control" value="{{ question.question_number }}"></div>
            <div class="col-md-3"><label class="form-label">分值</label><input type="number" name="total_points" class="form-control" value="{{ question.total_points }}" step="0.5"></div>
            <div class="col-md-6"><label class="form-label">更换图片</label><input type="file" name="image" class="form-control" accept="image/*"></div>
        </div>
        <div class="mt-3"><label class="form-label">题目内容</label><textarea name="content_text" class="form-control" rows="4">{{ question.content_text }}</textarea></div>
        {% if question.image_path %}<div class="mt-2"><img src="/{{ question.image_path }}" class="preview-img"></div>{% endif %}
        <div class="mt-3"><label class="form-label">参考答案</label><textarea name="reference_answer" class="form-control" rows="4">{{ question.reference_answer }}</textarea></div>
        <div class="mt-3"><label class="form-label">评分标准</label><textarea name="scoring_criteria" class="form-control" rows="3">{{ question.scoring_criteria }}</textarea></div>
        <div class="d-flex gap-2 mt-3">
            <button type="submit" class="btn btn-primary"><i class="bi bi-check-lg"></i> 保存</button>
            <a href="{{ url_for('admin_exam_setup', id=question.exam_id) }}" class="btn btn-outline-secondary">取消</a>
        </div>
    </form></div>
</div></div></div>
{% endblock %}
""",
    'admin_student_form.html': r"""{% extends "base.html" %}
{% block title %}{{ '编辑' if action == 'edit' else '添加' }}学生{% endblock %}
{% block content %}
<div class="container mt-4"><div class="row justify-content-center"><div class="col-md-6">
    <h4 class="mb-3">{{ '编辑' if action == 'edit' else '添加' }}学生</h4>
    <div class="card p-4"><form method="POST">
        <div class="mb-3"><label class="form-label">学号</label><input type="text" name="student_id" class="form-control" value="{{ student.student_id if action == 'edit' else '' }}" {% if action == 'edit' %}readonly{% endif %} required></div>
        <div class="mb-3"><label class="form-label">姓名</label><input type="text" name="name" class="form-control" value="{{ student.name if action == 'edit' else '' }}" required></div>
        <div class="mb-3"><label class="form-label">班级</label>
            <select name="class_id" class="form-select">
                <option value="">未分配</option>
                {% for c in classes %}<option value="{{ c.id }}" {% if action == 'edit' and student.class_id == c.id %}selected{% endif %}>{{ c.name }}</option>{% endfor %}
            </select></div>
        <button type="submit" class="btn btn-primary"><i class="bi bi-check-lg"></i> 保存</button>
        <a href="{{ url_for('admin_students') }}" class="btn btn-outline-secondary">取消</a>
    </form></div>
</div></div></div>
{% endblock %}
""",
    'admin_students.html': r"""{% extends "base.html" %}
{% block title %}学生管理{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-people"></i> 学生管理</h4>
        <div class="d-flex gap-2">
            <a href="{{ url_for('admin_students_batch') }}" class="btn btn-success btn-sm"><i class="bi bi-person-plus"></i> 批量录入</a>
            <a href="{{ url_for('admin_student_add') }}" class="btn btn-primary btn-sm"><i class="bi bi-plus-circle"></i> 添加</a>
        </div>
    </div>
    <div class="card p-3 mb-3">
        <form method="GET" class="row g-2">
            <div class="col-md-3">
                <select name="class_id" class="form-select form-select-sm">
                    <option value="">全部班级</option>
                    {% for c in classes %}<option value="{{ c.id }}" {% if c.id == class_filter %}selected{% endif %}>{{ c.name }}</option>{% endfor %}
                </select>
            </div>
            <div class="col-md-4"><input type="text" name="search" class="form-control form-control-sm" placeholder="搜索学号/姓名" value="{{ search }}"></div>
            <div class="col-md-2"><button type="submit" class="btn btn-sm btn-outline-primary"><i class="bi bi-funnel"></i></button></div>
        </form>
    </div>
    <div class="card">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light"><tr><th>学号</th><th>姓名</th><th>班级</th><th>操作</th></tr></thead>
                <tbody>
                {% for s in students %}
                <tr><td>{{ s.student_id }}</td><td>{{ s.name }}</td><td>{{ s.class_info.name if s.class_info else '-' }}</td>
                    <td><div class="btn-group btn-group-sm">
                        <a href="{{ url_for('admin_student_edit', id=s.id) }}" class="btn btn-outline-secondary"><i class="bi bi-pencil"></i></a>
                        <form method="POST" action="{{ url_for('admin_student_delete', id=s.id) }}" onsubmit="return confirm('确定删除？')"><button class="btn btn-outline-danger"><i class="bi bi-trash"></i></button></form>
                    </div></td></tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
""",
    'admin_students_batch.html': r"""{% extends "base.html" %}
{% block title %}批量录入学生{% endblock %}
{% block content %}
<div class="container mt-4"><div class="row justify-content-center"><div class="col-md-9">
    <h4 class="mb-3"><i class="bi bi-person-plus"></i> 批量录入学生</h4>
    <div class="row g-4">
        <div class="col-md-6">
            <div class="card p-4">
                <h5><i class="bi bi-file-text"></i> 文本输入</h5>
                <form method="POST">
                    <div class="mb-3"><label class="form-label">班级</label>
                        <select name="class_id" class="form-select">
                            <option value="">不指定</option>
                            {% for c in classes %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}
                        </select></div>
                    <div class="mb-3"><label class="form-label">学生数据（每行一个：学号 姓名，空格分隔）</label>
                        <textarea name="students_text" class="form-control" rows="10" placeholder="2024001 张三&#10;2024002 李四&#10;2024003 王五"></textarea></div>
                    <button type="submit" class="btn btn-primary w-100"><i class="bi bi-upload"></i> 导入</button>
                </form>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-4">
                <h5><i class="bi bi-file-earmark-spreadsheet"></i> CSV文件上传</h5>
                <form method="POST" enctype="multipart/form-data">
                    <div class="mb-3"><label class="form-label">班级</label>
                        <select name="class_id" class="form-select">
                            <option value="">不指定</option>
                            {% for c in classes %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}
                        </select></div>
                    <div class="mb-3"><label class="form-label">CSV文件</label>
                        <input type="file" name="file" class="form-control" accept=".csv"></div>
                    <div class="mb-3"><label class="form-label">编码</label>
                        <select name="encoding" class="form-select"><option value="utf-8">UTF-8</option><option value="gbk">GBK</option></select></div>
                    <button type="submit" class="btn btn-success w-100"><i class="bi bi-upload"></i> CSV导入</button>
                </form>
                <div class="alert alert-light mt-3 small">
                    <strong>CSV格式：</strong>首行为表头<br>
                    <code>学号,姓名</code> 或 <code>student_id,name,class_name</code><br>
                    示例：<code>2024001,张三</code>
                </div>
            </div>
        </div>
    </div>
</div></div></div>
{% endblock %}
""",
    'admin_upload_sheets.html': r"""{% extends "base.html" %}
{% block title %}上传答题卡 - {{ exam.name }}{% endblock %}
{% block extra_css %}
<style>.upload-zone{min-height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.pdf-icon{color:#dc2626;font-size:1.5rem}</style>
{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4><i class="bi bi-upload"></i> 批量上传答题卡 - {{ exam.name }}</h4>
        <a href="{{ url_for('admin_exams') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> 返回</a>
    </div>

    <!-- PDF上传模式说明 -->
    <div class="alert alert-info mb-3">
        <i class="bi bi-info-circle"></i> <strong>答题卡上传支持以下格式：</strong>
        <ul class="mb-0 mt-1 small">
            <li><strong>图片格式</strong>：JPG / PNG / WEBP，文件名格式：<code>学号_姓名.jpg</code></li>
            <li><strong>PDF格式</strong>（推荐）：
                <ul>
                    <li><strong>一人一PDF</strong>：每个PDF是一个学生的答题卡，文件名格式：<code>学号_姓名.pdf</code></li>
                    <li><strong>多人一PDF</strong>：整个班级的答题卡合在一个PDF中，每页一人，选择对应班级后系统按学号顺序自动匹配</li>
                </ul>
            </li>
            <li>批改完成后，标注评分的答题卡会自动生成为 <strong>PDF格式</strong>，学生可在线查看或下载</li>
        </ul>
    </div>

    <div class="card p-4 mb-4">
        <form method="POST" enctype="multipart/form-data">
            <div class="row g-3">
                <div class="col-md-3">
                    <label class="form-label">班级</label>
                    <select name="class_id" class="form-select" id="classSelect">
                        <option value="">不指定</option>
                        {% for c in classes %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label">PDF上传模式</label>
                    <select name="mode" class="form-select" id="modeSelect">
                        <option value="auto">一人一PDF（每个PDF=一个学生）</option>
                        <option value="multi_pdf">多人一PDF（每页=一个学生）</option>
                    </select>
                    <small class="text-muted" id="modeHint">图片上传时此选项无效</small>
                </div>
                <div class="col-md-6">
                    <label class="form-label">答题卡文件（支持多选）</label>
                    <div class="upload-zone" id="dropZone" onclick="document.getElementById('files').click()">
                        <div id="uploadPlaceholder">
                            <i class="bi bi-cloud-arrow-up"></i>
                            <p class="mt-2 mb-0">点击或拖拽上传答题卡</p>
                            <small class="text-muted">支持 JPG/PNG/WEBP/PDF，可多选</small>
                        </div>
                    </div>
                    <input type="file" name="files" id="files" multiple accept="image/*,.pdf" style="display:none" onchange="showFiles(this)">
                    <div id="fileList" class="mt-2 small"></div>
                </div>
            </div>
            <button type="submit" class="btn btn-primary btn-lg mt-3"><i class="bi bi-upload"></i> 上传</button>
        </form>
    </div>

    {% if sheets %}
    <div class="card p-4">
        <h5>已上传答题卡 ({{ sheets|length }}份)</h5>
        <div class="table-responsive mt-2">
            <table class="table table-sm table-hover mb-0">
                <thead class="table-light"><tr><th>学号</th><th>姓名</th><th>格式</th><th>答题卡</th><th>总分</th><th>操作</th></tr></thead>
                <tbody>
                {% for s in sheets %}
                <tr>
                    <td>{{ s.student_id }}</td>
                    <td>{{ s.student.name if s.student else '-' }}</td>
                    <td>
                        {% if s.pdf_path %}
                        <span class="badge bg-danger"><i class="bi bi-file-earmark-pdf"></i> PDF{{ ' (' ~ s.page_number ~ '页)' if s.page_number > 1 else '' }}</span>
                        {% else %}
                        <span class="badge bg-info"><i class="bi bi-image"></i> 图片</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if s.pdf_path %}
                        <a href="/{{ s.pdf_path }}" target="_blank" class="btn btn-sm btn-outline-danger"><i class="bi bi-file-earmark-pdf"></i> 原始PDF</a>
                        {% endif %}
                        {% if s.image_path %}
                        <a href="/{{ s.image_path }}" target="_blank" class="btn btn-sm btn-outline-info"><i class="bi bi-image"></i> 预览</a>
                        {% endif %}
                        {% if s.annotated_path %}
                        <a href="/{{ s.annotated_path }}" target="_blank" class="btn btn-sm btn-outline-success"><i class="bi bi-file-earmark-check"></i> 标注</a>
                        {% endif %}
                    </td>
                    <td>{{ s.total_score if s.total_score >= 0 else '-' }}</td>
                    <td><a href="{{ url_for('admin_grading_sheet', sheet_id=s.id) }}" class="btn btn-sm btn-outline-primary"><i class="bi bi-pencil-square"></i> 批改</a></td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
{% block extra_js %}
<script>
function showFiles(input) {
    const list = document.getElementById('fileList');
    const files = Array.from(input.files);
    const pdfs = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    const imgs = files.filter(f => !f.name.toLowerCase().endsWith('.pdf'));

    let html = '';
    if (pdfs.length > 0) {
        html += `<span class="pdf-icon"><i class="bi bi-file-earmark-pdf-fill"></i></span> ${pdfs.length} 个PDF文件：`;
        html += pdfs.map(f => `<span class="badge bg-danger">${f.name}</span>`).join(' ');
    }
    if (imgs.length > 0) {
        html += `<br><i class="bi bi-image text-info"></i> ${imgs.length} 个图片文件`;
    }
    list.innerHTML = html;

    // 自动切换模式提示
    const modeSelect = document.getElementById('modeSelect');
    const modeHint = document.getElementById('modeHint');
    if (pdfs.length > 0) {
        modeHint.textContent = pdfs.length + ' 个PDF待上传';
    } else {
        modeHint.textContent = '图片上传时此选项无效';
    }
}

// 拖拽上传
const dropZone = document.getElementById('dropZone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.style.borderColor = 'var(--pri)'; });
dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = ''; });
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.style.borderColor = '';
    const input = document.getElementById('files');
    const dt = new DataTransfer();
    for (const f of e.dataTransfer.files) dt.items.add(f);
    input.files = dt.files;
    showFiles(input);
});
</script>
{% endblock %}
""",
    'base.html': r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}智能阅卷系统{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root{--pri:#4f46e5;--pri-l:#818cf8;--bg:#f8fafc}
        body{background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
        .navbar{background:linear-gradient(135deg,#4f46e5,#7c3aed)!important}
        .card{border:none;box-shadow:0 1px 3px rgba(0,0,0,.1);border-radius:12px}
        .btn-primary{background:var(--pri);border-color:var(--pri)}
        .btn-primary:hover{background:#4338ca;border-color:#4338ca}
        .hero{background:linear-gradient(135deg,#4f46e5,#7c3aed,#a855f7);color:#fff;padding:3rem 0;border-radius:0 0 2rem 2rem}
        .feature-card{transition:transform .2s}.feature-card:hover{transform:translateY(-4px)}
        .stat-card{border-left:4px solid var(--pri)}
        .ai-badge{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;padding:2px 10px;border-radius:20px;font-size:.75rem;font-weight:600}
        .upload-zone{border:2px dashed #cbd5e1;border-radius:12px;padding:2rem;text-align:center;cursor:pointer;transition:all .2s}
        .upload-zone:hover,.upload-zone.dragover{border-color:var(--pri);background:#eef2ff}
        .upload-zone i{font-size:3rem;color:var(--pri-l)}
        .question-box{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:1rem}
        .answer-box{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:1rem}
        .score-circle{width:70px;height:70px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:700}
        .score-high{background:#dcfce7;color:#166534}.score-mid{background:#fef9c3;color:#854d0e}.score-low{background:#fee2e2;color:#991b1b}
        .nav-side .nav-link{color:#475569;border-radius:8px;margin-bottom:2px;padding:.5rem .8rem;font-size:.88rem}
        .nav-side .nav-link:hover,.nav-side .nav-link.active{background:#eef2ff;color:var(--pri)}
        .table th{font-size:.85rem;font-weight:600}
        .preview-img{max-height:300px;border-radius:8px;border:1px solid #e2e8f0}
        .grade-badge{font-size:.8rem}
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container">
        <a class="navbar-brand fw-bold" href="{{ url_for('index') }}"><i class="bi bi-journal-check"></i> 智能阅卷系统</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav"><span class="navbar-toggler-icon"></span></button>
        <div class="collapse navbar-collapse" id="nav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">首页</a></li>
                <li class="nav-item"><a class="nav-link" href="{{ url_for('query') }}">成绩查询</a></li>
                <li class="nav-item"><a class="nav-link" href="{{ url_for('admin_login') }}"><i class="bi bi-shield-lock"></i> 管理</a></li>
            </ul>
        </div>
    </div>
</nav>
{% with messages=get_flashed_messages(with_categories=true) %}
{% if messages %}<div class="container mt-3">{% for cat,msg in messages %}
<div class="alert alert-{{cat}} alert-dismissible fade show">{{msg}}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
{% endfor %}</div>{% endif %}{% endwith %}
{% block content %}{% endblock %}
<footer class="text-center text-muted py-4 mt-5"><small>智能阅卷系统 &copy; 2024 · <span class="ai-badge">AI</span> 辅助批改</small></footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
{% block extra_js %}{% endblock %}
</body>
</html>
""",
    'index.html': r"""{% extends "base.html" %}
{% block title %}智能阅卷系统{% endblock %}
{% block content %}
<div class="hero text-center">
    <div class="container">
        <h1 class="fw-bold"><i class="bi bi-journal-check"></i> 智能阅卷系统</h1>
        <p class="lead mt-2 mb-4">班级管理 · 拍题AI · 答题卡设计 · 智能批改 · 成绩分析 · 学生查询</p>
        <div class="d-flex justify-content-center gap-3 flex-wrap">
            <a href="{{ url_for('query') }}" class="btn btn-light btn-lg"><i class="bi bi-search"></i> 查询成绩</a>
            <a href="{{ url_for('admin_login') }}" class="btn btn-outline-light btn-lg"><i class="bi bi-shield-lock"></i> 管理入口</a>
        </div>
    </div>
</div>

<!-- 下载提示 -->
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card p-4 border-success" style="border-width:2px">
                <div class="d-flex align-items-center">
                    <i class="bi bi-download text-success me-3" style="font-size:2.5rem"></i>
                    <div class="flex-grow-1">
                        <h5 class="mb-1">下载本系统到本地电脑</h5>
                        <p class="text-muted mb-0 small">只需下载1个文件(130KB)，双击即可运行，手机也能访问</p>
                    </div>
                    <a href="{{ url_for('download_app') }}" class="btn btn-success btn-lg">
                        <i class="bi bi-download"></i> 点击下载
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="container mt-4">
    <div class="row g-4">
        <div class="col-md-3"><div class="card feature-card p-4 text-center"><i class="bi bi-people text-primary" style="font-size:2.5rem"></i><h6 class="mt-2">班级学生管理</h6><small class="text-muted">建班级·批量录入学号姓名</small></div></div>
        <div class="col-md-3"><div class="card feature-card p-4 text-center"><i class="bi bi-camera-fill text-primary" style="font-size:2.5rem"></i><h6 class="mt-2">拍题AI答题</h6><small class="text-muted">拍照识别·AI生成答案</small></div></div>
        <div class="col-md-3"><div class="card feature-card p-4 text-center"><i class="bi bi-file-earmark-ruled text-primary" style="font-size:2.5rem"></i><h6 class="mt-2">答题卡设计</h6><small class="text-muted">生成PDF·批量上传评分</small></div></div>
        <div class="col-md-3"><div class="card feature-card p-4 text-center"><i class="bi bi-bar-chart text-primary" style="font-size:2.5rem"></i><h6 class="mt-2">成绩分析</h6><small class="text-muted">汇总排名·班级对比·导出</small></div></div>
    </div>
    <div class="row mt-5"><div class="col-md-8 mx-auto"><div class="card p-4">
        <h5><i class="bi bi-speedometer2"></i> 快速查成绩</h5>
        <form method="POST" action="{{ url_for('query') }}" class="mt-3">
            <div class="row g-3">
                <div class="col-md-4"><input type="text" class="form-control" name="student_id" placeholder="学号" required></div>
                <div class="col-md-4"><input type="text" class="form-control" name="name" placeholder="姓名" required></div>
                <div class="col-md-4"><button type="submit" class="btn btn-primary w-100"><i class="bi bi-search"></i> 查询</button></div>
            </div>
        </form>
    </div></div></div>
</div>
{% endblock %}
""",
    'query.html': r"""{% extends "base.html" %}
{% block title %}成绩查询{% endblock %}
{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-10">
            <div class="card p-4">
                <h4><i class="bi bi-search"></i> 成绩查询</h4>
                <form method="POST" class="row g-3 mt-2">
                    <div class="col-md-5"><input type="text" class="form-control" name="student_id" placeholder="学号" value="{{ request.form.get('student_id','') }}" required></div>
                    <div class="col-md-5"><input type="text" class="form-control" name="name" placeholder="姓名" value="{{ request.form.get('name','') }}" required></div>
                    <div class="col-md-2"><button type="submit" class="btn btn-primary w-100"><i class="bi bi-search"></i></button></div>
                </form>
            </div>

            {% if student_info %}
            {% for ed in exams_data %}
            <div class="card p-4 mt-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <h5 class="mb-1">{{ student_info.name }}
                            <small class="text-muted">{{ student_info.student_id }} · {{ student_info.class_info.name if student_info.class_info else '' }}</small>
                        </h5>
                        <span class="badge bg-primary">{{ ed.exam.name }}</span>
                        <span class="badge bg-info">{{ ed.exam.subject }}</span>
                    </div>
                    <div class="text-end">
                        <div class="fs-3 fw-bold text-primary">{{ ed.summary.total_score }}</div>
                        <small class="text-muted">满分 {{ ed.exam.total_score }}</small>
                    </div>
                </div>

                <!-- 各题得分明细 -->
                {% if ed.details %}
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr><th>题号</th><th>满分</th><th>得分</th><th>得分率</th></tr>
                        </thead>
                        <tbody>
                            {% for d in ed.details %}
                            <tr>
                                <td>第{{ d.question_number }}题</td>
                                <td>{{ d.total_points }}</td>
                                <td class="fw-bold {% if d.score != None and d.score >= d.total_points * 0.8 %}text-success{% elif d.score != None and d.score >= d.total_points * 0.6 %}text-warning{% elif d.score != None %}text-danger{% endif %}">
                                    {{ d.score if d.score != None else '-' }}
                                </td>
                                <td>
                                    {% if d.score != None and d.total_points > 0 %}
                                    <div class="progress" style="height:18px">
                                        <div class="progress-bar {% if d.score/d.total_points >= 0.8 %}bg-success{% elif d.score/d.total_points >= 0.6 %}bg-warning{% else %}bg-danger{% endif %}"
                                             style="width:{{ (d.score/d.total_points*100)|int }}%">{{ (d.score/d.total_points*100)|int }}%</div>
                                    </div>
                                    {% else %}-{% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% endif %}

                <!-- 查看标注答题卡 -->
                {% if ed.sheet and ed.sheet.annotated_path %}
                <a href="/{{ ed.sheet.annotated_path }}" target="_blank" class="btn btn-outline-primary btn-sm mt-2">
                    {% if ed.sheet.pdf_path or ed.sheet.annotated_path.endswith('.pdf') %}
                    <i class="bi bi-file-earmark-pdf"></i> 查看答题卡评分标注（PDF）
                    {% else %}
                    <i class="bi bi-image"></i> 查看答题卡评分标注
                    {% endif %}
                </a>
                {% elif ed.sheet and ed.sheet.image_path %}
                <a href="/{{ ed.sheet.image_path }}" target="_blank" class="btn btn-outline-secondary btn-sm mt-2">
                    <i class="bi bi-image"></i> 查看答题卡
                </a>
                {% endif %}

                <!-- 排名 -->
                {% if ed.summary.rank_in_class or ed.summary.rank_in_grade %}
                <div class="mt-2">
                    {% if ed.summary.rank_in_class %}<span class="badge bg-info">班级排名：第{{ ed.summary.rank_in_class }}名</span>{% endif %}
                    {% if ed.summary.rank_in_grade %}<span class="badge bg-primary">年级排名：第{{ ed.summary.rank_in_grade }}名</span>{% endif %}
                </div>
                {% endif %}
            </div>
            {% endfor %}

            {% if not exams_data %}
            <div class="card p-5 text-center mt-4 text-muted"><i class="bi bi-inbox" style="font-size:3rem"></i><p class="mt-2">暂无成绩记录</p></div>
            {% endif %}
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
""",
}

class DictLoader(jinja2.BaseLoader):
    """Custom Jinja2 loader that loads templates from TEMPLATES dict"""
    def __init__(self, templates):
        self.templates = templates
    def get_source(self, environment, template):
        if template in self.templates:
            source = self.templates[template]
            return source, template, lambda: True
        raise jinja2.TemplateNotFound(template)


def render_tpl(name, **kwargs):
    return render_template_string(TEMPLATES[name], **kwargs)

app = Flask(__name__)
app.jinja_loader = DictLoader(TEMPLATES)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///grading.db'
).replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['ANSWER_SHEET_FOLDER'] = os.path.join(BASE_DIR, 'static', 'answer_sheets')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'uploads', 'pdf_pages'), exist_ok=True)
os.makedirs(app.config['ANSWER_SHEET_FOLDER'], exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB for PDF
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf'}

# AI配置
app.config['AI_PROVIDER'] = os.environ.get('AI_PROVIDER', 'demo')
app.config['AI_API_KEY'] = os.environ.get('AI_API_KEY', '')
app.config['AI_API_URL'] = os.environ.get('AI_API_URL', '')
app.config['AI_MODEL'] = os.environ.get('AI_MODEL', '')

db = SQLAlchemy(app)

# ════════════════ 数据模型 ════════════════

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)


class Class(db.Model):
    """班级"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 如：高三1班
    grade = db.Column(db.String(50), default='')  # 年级
    teacher = db.Column(db.String(100), default='')  # 班主任
    students = db.relationship('Student', backref='class_info', lazy=True)


class Student(db.Model):
    """学生"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True, index=True)


class Exam(db.Model):
    """考试"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # 如：2024期末考试
    subject = db.Column(db.String(100), nullable=False)
    total_score = db.Column(db.Float, default=100)  # 总分
    exam_date = db.Column(db.String(20), default='')
    status = db.Column(db.String(20), default='进行中')  # 进行中/已结束/已发布


class QuestionGroup(db.Model):
    """题目组（大题）"""
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)  # 如：一、选择题
    question_type = db.Column(db.String(50), default='解答题')
    total_points = db.Column(db.Float, default=0)  # 该大题总分
    sort_order = db.Column(db.Integer, default=0)

    exam = db.relationship('Exam', backref=db.backref('question_groups', lazy=True,
                                                       order_by='QuestionGroup.sort_order'))


class Question(db.Model):
    """小题"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('question_group.id'), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False, index=True)
    question_number = db.Column(db.String(20), nullable=False)  # 如：1, 2, 13(1)
    content_text = db.Column(db.Text, default='')
    image_path = db.Column(db.String(500), default='')
    reference_answer = db.Column(db.Text, default='')
    scoring_criteria = db.Column(db.Text, default='')
    total_points = db.Column(db.Float, default=5)

    group = db.relationship('QuestionGroup', backref=db.backref('questions', lazy=True,
                                                                  order_by='Question.id'))


class AnswerSheet(db.Model):
    """答题卡（学生提交的）"""
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False, index=True)
    student_id = db.Column(db.String(50), db.ForeignKey('student.student_id'), nullable=False, index=True)
    image_path = db.Column(db.String(500), default='')  # 答题卡预览图（首页或原图）
    pdf_path = db.Column(db.String(500), default='')  # 原始PDF路径（如果是PDF上传）
    page_number = db.Column(db.Integer, default=1)  # PDF页数
    annotated_path = db.Column(db.String(500), default='')  # 标注后的路径（图片或PDF）
    total_score = db.Column(db.Float, default=-1)  # 总分 -1=未批改
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    exam = db.relationship('Exam', backref=db.backref('answer_sheets', lazy=True))
    student = db.relationship('Student', backref=db.backref('answer_sheets', lazy=True))


class ScoreDetail(db.Model):
    """每小题得分明细"""
    id = db.Column(db.Integer, primary_key=True)
    answer_sheet_id = db.Column(db.Integer, db.ForeignKey('answer_sheet.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False, index=True)
    ai_score = db.Column(db.Float, default=-1)
    ai_feedback = db.Column(db.Text, default='')
    final_score = db.Column(db.Float, default=-1)
    teacher_comment = db.Column(db.Text, default='')

    answer_sheet = db.relationship('AnswerSheet', backref=db.backref('score_details', lazy=True))
    question = db.relationship('Question', backref=db.backref('score_details', lazy=True))


class ScoreSummary(db.Model):
    """成绩汇总（按学生+考试）"""
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False, index=True)
    student_id = db.Column(db.String(50), db.ForeignKey('student.student_id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True, index=True)
    total_score = db.Column(db.Float, default=0)
    rank_in_class = db.Column(db.Integer, default=0)
    rank_in_grade = db.Column(db.Integer, default=0)

    exam = db.relationship('Exam', backref=db.backref('score_summaries', lazy=True))
    student = db.relationship('Student', backref=db.backref('score_summaries', lazy=True))
    class_info = db.relationship('Class', backref=db.backref('score_summaries', lazy=True))


# ════════════════ AI 服务 ════════════════

class AIService:
    @staticmethod
    def _call_api(messages, json_mode=False):
        import requests as req
        provider = app.config['AI_PROVIDER']
        if provider == 'demo': return None
        api_key, api_url, model = app.config['AI_API_KEY'], app.config['AI_API_URL'], app.config['AI_MODEL']
        if not api_key or not api_url: return None
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {'model': model, 'messages': messages, 'temperature': 0.3, 'max_tokens': 2000}
        if json_mode: payload['response_format'] = {'type': 'json_object'}
        try:
            resp = req.post(api_url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f'AI API error: {e}')
            return None

    @staticmethod
    def _call_vision_api(messages):
        import requests as req
        provider = app.config['AI_PROVIDER']
        if provider == 'demo': return None
        api_key, api_url, model = app.config['AI_API_KEY'], app.config['AI_API_URL'], app.config['AI_MODEL']
        if not api_key or not api_url: return None
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {'model': model, 'messages': messages, 'temperature': 0.3, 'max_tokens': 2000}
        try:
            resp = req.post(api_url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except: return None

    @staticmethod
    def _image_to_base64(image_path):
        full = os.path.join(BASE_DIR, image_path)
        if not os.path.exists(full): return None
        with open(full, 'rb') as f:
            ext = os.path.splitext(full)[1].lower()
            mime = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg',
                    '.gif':'image/gif','.webp':'image/webp'}.get(ext, 'image/jpeg')
            return f'data:{mime};base64,{base64.b64encode(f.read()).decode()}'

    @staticmethod
    def recognize_question(image_path, subject='', question_type=''):
        if app.config['AI_PROVIDER'] == 'demo':
            return '【演示模式】AI识别内容：\n已知函数 f(x) = x² - 2x + 1\n（1）求f(x)最小值\n（2）求f(x)=0的解集'
        b64 = AIService._image_to_base64(image_path)
        if not b64: return '无法读取图片'
        messages = [{'role':'user','content':[
            {'type':'text','text':f'识别图片中{subject}题目，数学公式用LaTeX，只输出题目文字。'},
            {'type':'image_url','image_url':{'url':b64}}
        ]}]
        r = AIService._call_vision_api(messages)
        return r if r else 'AI识别失败，请手动输入'

    @staticmethod
    def generate_answer(question_text, subject='', total_points=10):
        if app.config['AI_PROVIDER'] == 'demo':
            return {'reference_answer':'(1) f(x)=(x-1)², 最小值=0\n(2) x=1，解集{1}',
                    'scoring_criteria':f'满分{total_points}分\n(1) 配方3分+最小值2分=5分\n(2) 列方程2分+求解3分=5分'}
        messages = [{'role':'user','content':f'''你是{subject}教师。为以下题目生成参考答案和评分标准（满分{total_points}分）：
{question_text}
JSON格式：{{"reference_answer":"答案","scoring_criteria":"评分标准"}}'''}]
        r = AIService._call_api(messages, json_mode=True)
        if r:
            try: return json.loads(r)
            except: pass
        return {'reference_answer': r or '生成失败','scoring_criteria':'请根据完整性酌情给分'}

    @staticmethod
    def grade_question(question_text, reference_answer, scoring_criteria,
                       student_answer, total_points=10, subject=''):
        if app.config['AI_PROVIDER'] == 'demo':
            score = round(total_points * 0.7, 1)
            return {'score': score, 'feedback': f'演示批改：建议{score}分', 'correctness': '部分正确'}
        messages = [{'role':'user','content':f'''你是{subject}阅卷教师，批改学生答案。
题目：{question_text}
参考答案：{reference_answer}
评分标准：{scoring_criteria}
满分：{total_points}分
学生答案：{student_answer}
JSON格式：{{"score":分数,"feedback":"反馈","correctness":"正确/部分正确/错误"}}'''}]
        r = AIService._call_api(messages, json_mode=True)
        if r:
            try:
                d = json.loads(r)
                d['score'] = min(float(d.get('score', 0)), total_points)
                return d
            except: pass
        return {'score': 0, 'feedback': 'AI批改失败', 'correctness': '未知'}


# ════════════════ PDF 处理工具 ════════════════

def pdf_to_images(pdf_path, output_dir, dpi=200, prefix='page'):
    """将PDF每页转为图片，返回图片路径列表"""
    full_path = os.path.join(BASE_DIR, pdf_path) if not os.path.isabs(pdf_path) else pdf_path
    if not os.path.exists(full_path):
        return []

    doc = fitz.open(full_path)
    image_paths = []
    os.makedirs(output_dir, exist_ok=True)

    for page_num in range(len(doc)):
        page = doc[page_num]
        # 高DPI渲染
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        img_filename = f'{prefix}_p{page_num+1}_{uuid.uuid4().hex[:6]}.png'
        img_path = os.path.join(output_dir, img_filename)
        pix.save(img_path)
        image_paths.append(img_path)

    doc.close()
    return image_paths


def annotate_pdf_with_scores(pdf_path, score_details, questions, total_score, exam_name=''):
    """在PDF答题卡上直接标注评分，输出标注后的PDF"""
    full_path = os.path.join(BASE_DIR, pdf_path) if not os.path.isabs(pdf_path) else pdf_path
    if not os.path.exists(full_path):
        return pdf_path

    doc = fitz.open(full_path)

    # 在第一页右侧添加评分栏
    page = doc[0]
    page_rect = page.rect
    page_w = page_rect.width
    page_h = page_rect.height

    # 扩展页面宽度，右侧添加评分区
    col_w = 120  # 评分栏宽度（点）
    new_w = page_w + col_w
    page.set_cropbox(fitz.Rect(0, 0, new_w, page_h))

    # 评分栏背景
    rect = fitz.Rect(page_w, 0, new_w, page_h)
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=(0.8, 0.8, 0.8), fill=(0.97, 0.97, 0.97))
    shape.commit()

    # 标题
    text_point = fitz.Point(page_w + 10, 25)
    page.insert_text(text_point, f"{exam_name} Scores",
                     fontsize=10, color=(0, 0, 0.5), fontname="helv")

    # 各题分数
    y = 45
    line_h = max(18, (page_h - 80) // max(len(score_details), 1))

    for sd in score_details:
        q = next((q for q in questions if q.id == sd.question_id), None)
        if not q:
            continue

        score = sd.final_score if sd.final_score >= 0 else (sd.ai_score if sd.ai_score >= 0 else -1)
        label = f"Q{q.question_number}: {score}/{q.total_points}" if score >= 0 else f"Q{q.question_number}: -/{q.total_points}"

        # 颜色
        if score >= 0:
            ratio = score / q.total_points if q.total_points > 0 else 0
            if ratio >= 0.8:
                color = (0, 0.5, 0)
            elif ratio >= 0.6:
                color = (0.7, 0.5, 0)
            else:
                color = (0.8, 0, 0)
        else:
            color = (0.4, 0.4, 0.4)

        page.insert_text(fitz.Point(page_w + 10, y), label, fontsize=9, color=color, fontname="helv")
        y += line_h
        if y > page_h - 50:
            break

    # 总分
    total = sum(sd.final_score for sd in score_details if sd.final_score >= 0)
    if total == 0:
        total = sum(sd.ai_score for sd in score_details if sd.ai_score >= 0)

    # 底部分隔线
    shape2 = page.new_shape()
    shape2.draw_line(fitz.Point(page_w, page_h - 35), fitz.Point(new_w, page_h - 35))
    shape2.finish(color=(0, 0, 0))
    shape2.commit()
    page.insert_text(fitz.Point(page_w + 10, page_h - 18),
                     f"Total: {total}/{total_score}",
                     fontsize=11, color=(0, 0, 0.8), fontname="helv")

    # 保存标注PDF
    annotated = pdf_path.replace('/uploads/', '/answer_sheets/')
    if annotated.endswith('.pdf'):
        annotated = annotated.replace('.pdf', '_annotated.pdf')
    else:
        # 如果原始是图片，也输出为PDF
        annotated = annotated.rsplit('.', 1)[0] + '_annotated.pdf'
    full_out = os.path.join(BASE_DIR, annotated) if not os.path.isabs(annotated) else annotated
    os.makedirs(os.path.dirname(full_out), exist_ok=True)
    doc.save(full_out)
    doc.close()
    return annotated


# ════════════════ 答题卡图片标注 ════════════════

def annotate_answer_sheet(image_path, score_details, questions):
    """在答题卡图片上标注各题得分"""
    full = os.path.join(BASE_DIR, image_path) if not os.path.isabs(image_path) else image_path
    if not os.path.exists(full): return image_path

    img = Image.open(full)
    draw = ImageDraw.Draw(img)

    # 尝试加载中文字体
    font_size = 18
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()
        font_small = font

    w, h = img.size
    # 右侧添加分数列
    col_w = 120
    new_img = Image.new('RGB', (w + col_w, h), 'white')
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)

    # 画分数列
    draw.line([(w, 0), (w, h)], fill='black', width=2)
    draw.text((w + 10, 10), "Score", fill='black', font=font)

    y_offset = 50
    line_h = max(30, h // max(len(score_details), 1))

    for sd in score_details:
        q = next((q for q in questions if q.id == sd.question_id), None)
        if not q: continue

        score = sd.final_score if sd.final_score >= 0 else (sd.ai_score if sd.ai_score >= 0 else -1)
        label = f"{q.question_number}: {score}/{q.total_points}" if score >= 0 else f"{q.question_number}: -/{q.total_points}"

        # 根据得分率选色
        if score >= 0:
            ratio = score / q.total_points if q.total_points > 0 else 0
            if ratio >= 0.8: color = (0, 128, 0)
            elif ratio >= 0.6: color = (200, 150, 0)
            else: color = (200, 0, 0)
        else:
            color = (100, 100, 100)

        draw.text((w + 10, y_offset), label, fill=color, font=font_small)
        y_offset += line_h
        if y_offset > h - 40: break

    # 底部总分
    total = sum(sd.final_score for sd in score_details if sd.final_score >= 0)
    if total == 0:
        total = sum(sd.ai_score for sd in score_details if sd.ai_score >= 0)
    draw.line([(w, h - 40), (w + col_w, h - 40)], fill='black', width=2)
    draw.text((w + 10, h - 35), f"Total: {total}", fill='blue', font=font)

    # 保存
    annotated = image_path.replace('/uploads/', '/answer_sheets/')
    annotated = annotated.rsplit('.', 1)
    annotated = annotated[0] + '_annotated.' + annotated[1]
    full_out = os.path.join(BASE_DIR, annotated)
    os.makedirs(os.path.dirname(full_out), exist_ok=True)
    new_img.save(full_out, quality=90)
    return annotated


def annotate_image_as_pdf(image_path, score_details, questions, total_score, exam_name=''):
    """将图片答题卡转PDF并标注评分，输出PDF格式"""
    full = os.path.join(BASE_DIR, image_path) if not os.path.isabs(image_path) else image_path
    if not os.path.exists(full): return ''

    # 先做图片标注
    annotated_img = annotate_answer_sheet(image_path, score_details, questions)
    annotated_full = os.path.join(BASE_DIR, annotated_img) if not os.path.isabs(annotated_img) else annotated_img

    if not os.path.exists(annotated_full):
        return ''

    # 将标注后的图片嵌入PDF
    img = Image.open(annotated_full)
    img_w, img_h = img.size

    # A4尺寸（点），根据图片比例调整
    a4_w, a4_h = pagesizes.A4
    ratio = img_w / img_h
    if ratio > a4_w / a4_h:
        pdf_w = a4_w
        pdf_h = a4_w / ratio
    else:
        pdf_h = a4_h
        pdf_w = a4_h * ratio

    filename = f'annotated_{uuid.uuid4().hex[:6]}.pdf'
    filepath = os.path.join(app.config['ANSWER_SHEET_FOLDER'], filename)

    c = canvas.Canvas(filepath, pagesize=(pdf_w, pdf_h))
    c.drawImage(annotated_full, 0, 0, width=pdf_w, height=pdf_h)
    c.save()

    return f'static/answer_sheets/{filename}'


def generate_answer_sheet_pdf(exam, questions_by_group):
    """生成空白答题卡PDF"""
    filename = f'answer_sheet_exam{exam.id}_{uuid.uuid4().hex[:6]}.pdf'
    filepath = os.path.join(app.config['ANSWER_SHEET_FOLDER'], filename)

    c = canvas.Canvas(filepath, pagesize=pagesizes.A4)
    w, h = pagesizes.A4
    y = h - 30*mm

    # 标题
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w/2, y, f"{exam.name} - Answer Sheet")
    y -= 10*mm
    c.setFont("Helvetica", 10)
    c.drawString(30*mm, y, f"Subject: {exam.subject}    Total: {exam.total_score}")
    y -= 8*mm
    c.drawString(30*mm, y, "Name: ______________    Student ID: ______________    Class: ______________")
    y -= 12*mm

    # 题目区域
    for group, qs in questions_by_group:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20*mm, y, f"{group.name} ({group.total_points}pts)")
        y -= 8*mm

        for q in qs:
            c.setFont("Helvetica", 10)
            c.drawString(25*mm, y, f"Q{q.question_number} ({q.total_points}pts)")
            y -= 5*mm

            # 画答题框
            box_h = 25*mm if q.total_points >= 10 else 18*mm
            c.rect(25*mm, y - box_h, w - 50*mm, box_h)
            y -= box_h + 3*mm

            if y < 40*mm:
                c.showPage()
                y = h - 20*mm

    c.save()
    return f'static/answer_sheets/{filename}'


# ════════════════ 辅助函数 ════════════════

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_file(file_obj, prefix='img'):
    if file_obj and allowed_file(file_obj.filename):
        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        fn = f'{prefix}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}'
        fp = os.path.join(app.config['UPLOAD_FOLDER'], fn)
        file_obj.save(fp)
        return f'static/uploads/{fn}'
    return ''

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def recalc_summary(exam_id, student_id):
    """重算成绩汇总"""
    sheet = AnswerSheet.query.filter_by(exam_id=exam_id, student_id=student_id).first()
    if not sheet: return

    total = 0
    for sd in sheet.score_details:
        s = sd.final_score if sd.final_score >= 0 else (sd.ai_score if sd.ai_score >= 0 else 0)
        total += s
    sheet.total_score = total

    summary = ScoreSummary.query.filter_by(exam_id=exam_id, student_id=student_id).first()
    if not summary:
        stu = Student.query.filter_by(student_id=student_id).first()
        summary = ScoreSummary(exam_id=exam_id, student_id=student_id, class_id=stu.class_id if stu else None)
        db.session.add(summary)
    summary.total_score = total
    db.session.commit()


def recalc_ranks(exam_id):
    """重算排名"""
    summaries = ScoreSummary.query.filter_by(exam_id=exam_id).order_by(ScoreSummary.total_score.desc()).all()

    # 年级排名
    for i, s in enumerate(summaries, 1):
        s.rank_in_grade = i

    # 班级排名
    by_class = defaultdict(list)
    for s in summaries:
        by_class[s.class_id].append(s)
    for cid, ss in by_class.items():
        ss.sort(key=lambda x: x.total_score, reverse=True)
        for i, s in enumerate(ss, 1):
            s.rank_in_class = i

    db.session.commit()


# ════════════════ 前台路由 ════════════════

@app.route('/')
def index():
    return render_tpl('index.html')


@app.route('/download')
def download_app():
    """下载本系统单文件版本"""
    this_file = os.path.abspath(__file__)
    if os.path.exists(this_file):
        return send_file(this_file, as_attachment=True,
                         download_name='智能阅卷系统.py',
                         mimetype='text/x-python')
    return '文件未找到', 404


@app.route('/query', methods=['GET', 'POST'])
def query():
    results = []
    student_info = None
    exams_data = []

    if request.method == 'POST':
        sid = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()

        student = Student.query.filter_by(student_id=sid, name=name).first()
        if not student:
            flash('学号或姓名不正确', 'danger')
            return render_tpl('query.html', results=[], student_info=None, exams_data=[])

        student_info = student
        summaries = ScoreSummary.query.filter_by(student_id=sid).all()

        for sm in summaries:
            exam = sm.exam
            sheet = AnswerSheet.query.filter_by(exam_id=exam.id, student_id=sid).first()
            details = []
            if sheet:
                for sd in sheet.score_details:
                    q = sd.question
                    score = sd.final_score if sd.final_score >= 0 else (sd.ai_score if sd.ai_score >= 0 else None)
                    details.append({
                        'question_number': q.question_number,
                        'total_points': q.total_points,
                        'score': score,
                        'comment': sd.teacher_comment or sd.ai_feedback
                    })

            exams_data.append({
                'exam': exam,
                'summary': sm,
                'sheet': sheet,
                'details': details
            })

        if not exams_data:
            flash('未找到成绩记录', 'info')

    return render_tpl('query.html', results=results, student_info=student_info, exams_data=exams_data)


# ════════════════ 管理员 ════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '')
        admin = Admin.query.filter_by(username=u).first()
        if admin and admin.check_password(p):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            flash('登录成功', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('用户名或密码错误', 'danger')
    return render_tpl('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('已退出', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    ctx = {
        'class_count': Class.query.count(),
        'student_count': Student.query.count(),
        'exam_count': Exam.query.count(),
        'sheet_count': AnswerSheet.query.count(),
        'ungraded': AnswerSheet.query.filter_by(total_score=-1).count(),
        'classes': Class.query.all(),
        'exams': Exam.query.order_by(Exam.id.desc()).limit(10).all(),
        'ai_provider': app.config['AI_PROVIDER']
    }
    return render_tpl('admin_dashboard.html', **ctx)


# ── 班级管理 ──

@app.route('/admin/classes')
@admin_required
def admin_classes():
    classes = Class.query.all()
    for c in classes:
        c.student_count = Student.query.filter_by(class_id=c.id).count()
    return render_tpl('admin_classes.html', classes=classes)


@app.route('/admin/class/add', methods=['GET', 'POST'])
@admin_required
def admin_class_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        grade = request.form.get('grade', '').strip()
        teacher = request.form.get('teacher', '').strip()
        if Class.query.filter_by(name=name).first():
            flash(f'班级 {name} 已存在', 'danger')
            return render_tpl('admin_class_form.html', action='add')
        db.session.add(Class(name=name, grade=grade, teacher=teacher))
        db.session.commit()
        flash('班级添加成功', 'success')
        return redirect(url_for('admin_classes'))
    return render_tpl('admin_class_form.html', action='add')


@app.route('/admin/class/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_class_edit(id):
    c = Class.query.get_or_404(id)
    if request.method == 'POST':
        c.name = request.form.get('name', '').strip()
        c.grade = request.form.get('grade', '').strip()
        c.teacher = request.form.get('teacher', '').strip()
        db.session.commit()
        flash('修改成功', 'success')
        return redirect(url_for('admin_classes'))
    return render_tpl('admin_class_form.html', action='edit', cls=c)


@app.route('/admin/class/delete/<int:id>', methods=['POST'])
@admin_required
def admin_class_delete(id):
    c = Class.query.get_or_404(id)
    Student.query.filter_by(class_id=id).update({'class_id': None})
    db.session.delete(c)
    db.session.commit()
    flash('班级已删除', 'success')
    return redirect(url_for('admin_classes'))


# ── 学生管理 ──

@app.route('/admin/students')
@admin_required
def admin_students():
    class_filter = request.args.get('class_id', 0, type=int)
    search = request.args.get('search', '').strip()

    q = Student.query
    if class_filter:
        q = q.filter_by(class_id=class_filter)
    if search:
        q = q.filter((Student.name.contains(search)) | (Student.student_id.contains(search)))
    students = q.order_by(Student.student_id).all()
    classes = Class.query.all()
    return render_tpl('admin_students.html', students=students, classes=classes,
                           class_filter=class_filter, search=search)


@app.route('/admin/student/add', methods=['GET', 'POST'])
@admin_required
def admin_student_add():
    if request.method == 'POST':
        sid = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()
        cid = request.form.get('class_id', 0, type=int)
        if Student.query.filter_by(student_id=sid).first():
            flash(f'学号 {sid} 已存在', 'danger')
            return render_tpl('admin_student_form.html', action='add', classes=Class.query.all())
        db.session.add(Student(student_id=sid, name=name, class_id=cid if cid else None))
        db.session.commit()
        flash('添加成功', 'success')
        return redirect(url_for('admin_students'))
    return render_tpl('admin_student_form.html', action='add', classes=Class.query.all())


@app.route('/admin/student/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_student_edit(id):
    s = Student.query.get_or_404(id)
    if request.method == 'POST':
        s.student_id = request.form.get('student_id', '').strip()
        s.name = request.form.get('name', '').strip()
        s.class_id = request.form.get('class_id', 0, type=int) or None
        db.session.commit()
        flash('修改成功', 'success')
        return redirect(url_for('admin_students'))
    return render_tpl('admin_student_form.html', action='edit', student=s, classes=Class.query.all())


@app.route('/admin/student/delete/<int:id>', methods=['POST'])
@admin_required
def admin_student_delete(id):
    s = Student.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('admin_students'))


@app.route('/admin/students/batch', methods=['GET', 'POST'])
@admin_required
def admin_students_batch():
    """批量录入学生"""
    if request.method == 'POST':
        class_id = request.form.get('class_id', 0, type=int)
        text = request.form.get('students_text', '').strip()

        # 支持CSV文件
        file = request.files.get('file')
        if file and file.filename:
            encoding = request.form.get('encoding', 'utf-8')
            stream = io.StringIO(file.stream.read().decode(encoding))
            reader = csv.DictReader(stream)
            count = 0
            for row in reader:
                sid = row.get('学号', row.get('student_id', '')).strip()
                name = row.get('姓名', row.get('name', '')).strip()
                cid = class_id or None
                if sid and name and not Student.query.filter_by(student_id=sid).first():
                    db.session.add(Student(student_id=sid, name=name, class_id=cid))
                    count += 1
            db.session.commit()
            flash(f'成功导入 {count} 名学生', 'success')
            return redirect(url_for('admin_students'))

        # 支持文本批量输入（每行：学号 姓名）
        if text:
            count = 0
            for line in text.split('\n'):
                line = line.strip()
                if not line: continue
                parts = line.split(None, 1)  # 空格分隔
                if len(parts) >= 2:
                    sid, name = parts[0].strip(), parts[1].strip()
                else:
                    continue
                if not Student.query.filter_by(student_id=sid).first():
                    db.session.add(Student(student_id=sid, name=name, class_id=class_id or None))
                    count += 1
            db.session.commit()
            flash(f'成功导入 {count} 名学生', 'success')
            return redirect(url_for('admin_students'))

        flash('请输入学生数据或上传CSV文件', 'danger')

    classes = Class.query.all()
    return render_tpl('admin_students_batch.html', classes=classes)


# ── 考试管理 ──

@app.route('/admin/exams')
@admin_required
def admin_exams():
    exams = Exam.query.order_by(Exam.id.desc()).all()
    for e in exams:
        e.sheet_count = AnswerSheet.query.filter_by(exam_id=e.id).count()
        e.student_count = ScoreSummary.query.filter_by(exam_id=e.id).count()
    return render_tpl('admin_exams.html', exams=exams)


@app.route('/admin/exam/add', methods=['GET', 'POST'])
@admin_required
def admin_exam_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        total = request.form.get('total_score', 100, type=float)
        date = request.form.get('exam_date', '').strip()
        db.session.add(Exam(name=name, subject=subject, total_score=total, exam_date=date))
        db.session.commit()
        flash('考试创建成功，接下来请设置题目和分数', 'success')
        return redirect(url_for('admin_exam_setup', id=Exam.query.order_by(Exam.id.desc()).first().id))
    return render_tpl('admin_exam_form.html', action='add')


@app.route('/admin/exam/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_exam_edit(id):
    e = Exam.query.get_or_404(id)
    if request.method == 'POST':
        e.name = request.form.get('name', '').strip()
        e.subject = request.form.get('subject', '').strip()
        e.total_score = request.form.get('total_score', 100, type=float)
        e.exam_date = request.form.get('exam_date', '').strip()
        db.session.commit()
        flash('修改成功', 'success')
        return redirect(url_for('admin_exams'))
    return render_tpl('admin_exam_form.html', action='edit', exam=e)


@app.route('/admin/exam/delete/<int:id>', methods=['POST'])
@admin_required
def admin_exam_delete(id):
    e = Exam.query.get_or_404(id)
    # 级联删除
    for qg in e.question_groups:
        for q in qg.questions:
            ScoreDetail.query.filter_by(question_id=q.id).delete()
            db.session.delete(q)
        db.session.delete(qg)
    for s in e.answer_sheets:
        ScoreDetail.query.filter_by(answer_sheet_id=s.id).delete()
        db.session.delete(s)
    ScoreSummary.query.filter_by(exam_id=id).delete()
    db.session.delete(e)
    db.session.commit()
    flash('考试及相关数据已删除', 'success')
    return redirect(url_for('admin_exams'))


# ── 考试设置（题目+分数） ──

@app.route('/admin/exam/setup/<int:id>')
@admin_required
def admin_exam_setup(id):
    exam = Exam.query.get_or_404(id)
    groups = QuestionGroup.query.filter_by(exam_id=id).order_by(QuestionGroup.sort_order).all()
    return render_tpl('admin_exam_setup.html', exam=exam, groups=groups)


@app.route('/admin/exam/group/add/<int:exam_id>', methods=['POST'])
@admin_required
def admin_group_add(exam_id):
    name = request.form.get('name', '').strip()
    qtype = request.form.get('question_type', '解答题').strip()
    total = request.form.get('total_points', 0, type=float)
    sort = request.form.get('sort_order', 0, type=int)
    db.session.add(QuestionGroup(exam_id=exam_id, name=name, question_type=qtype,
                                  total_points=total, sort_order=sort))
    db.session.commit()
    flash('题目组添加成功', 'success')
    return redirect(url_for('admin_exam_setup', id=exam_id))


@app.route('/admin/exam/group/delete/<int:id>', methods=['POST'])
@admin_required
def admin_group_delete(id):
    g = QuestionGroup.query.get_or_404(id)
    for q in g.questions:
        ScoreDetail.query.filter_by(question_id=q.id).delete()
        db.session.delete(q)
    db.session.delete(g)
    db.session.commit()
    flash('题目组已删除', 'success')
    return redirect(url_for('admin_exam_setup', id=g.exam_id))


@app.route('/admin/exam/question/add/<int:group_id>', methods=['POST'])
@admin_required
def admin_question_add(group_id):
    g = QuestionGroup.query.get_or_404(group_id)
    qnum = request.form.get('question_number', '').strip()
    points = request.form.get('total_points', 5, type=float)
    content = request.form.get('content_text', '').strip()

    # 保存图片
    img_path = ''
    file = request.files.get('image')
    if file and file.filename:
        img_path = save_file(file, prefix='q')

    q = Question(group_id=group_id, exam_id=g.exam_id, question_number=qnum,
                 total_points=points, content_text=content, image_path=img_path)
    db.session.add(q)

    # 更新大题总分
    g.total_points = sum(q2.total_points for q2 in g.questions) + points

    db.session.commit()
    flash('小题添加成功', 'success')
    return redirect(url_for('admin_exam_setup', id=g.exam_id))


@app.route('/admin/exam/question/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_question_edit(id):
    q = Question.query.get_or_404(id)
    if request.method == 'POST':
        q.question_number = request.form.get('question_number', '').strip()
        q.total_points = request.form.get('total_points', 5, type=float)
        q.content_text = request.form.get('content_text', '').strip()
        q.reference_answer = request.form.get('reference_answer', '').strip()
        q.scoring_criteria = request.form.get('scoring_criteria', '').strip()
        file = request.files.get('image')
        if file and file.filename:
            q.image_path = save_file(file, prefix='q')
        # 更新大题总分
        g = q.group
        g.total_points = sum(q2.total_points for q2 in g.questions)
        db.session.commit()
        flash('修改成功', 'success')
        return redirect(url_for('admin_exam_setup', id=q.exam_id))
    return render_tpl('admin_question_edit.html', question=q)


@app.route('/admin/exam/question/delete/<int:id>', methods=['POST'])
@admin_required
def admin_question_delete(id):
    q = Question.query.get_or_404(id)
    ScoreDetail.query.filter_by(question_id=id).delete()
    g = q.group
    db.session.delete(q)
    g.total_points = sum(q2.total_points for q2 in g.questions)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('admin_exam_setup', id=q.exam_id))


@app.route('/admin/exam/generate_answer/<int:id>', methods=['POST'])
@admin_required
def admin_generate_answer(id):
    q = Question.query.get_or_404(id)
    result = AIService.generate_answer(q.content_text, subject=q.group.exam.subject,
                                        total_points=q.total_points)
    if isinstance(result, dict):
        q.reference_answer = result.get('reference_answer', '')
        q.scoring_criteria = result.get('scoring_criteria', '')
    db.session.commit()
    flash('AI答案生成完成', 'success')
    return redirect(url_for('admin_exam_setup', id=q.exam_id))


# ── 答题卡设计 ──

@app.route('/admin/exam/answer_sheet/<int:id>')
@admin_required
def admin_answer_sheet_design(id):
    exam = Exam.query.get_or_404(id)
    groups = QuestionGroup.query.filter_by(exam_id=id).order_by(QuestionGroup.sort_order).all()
    questions_by_group = [(g, g.questions) for g in groups]
    return render_tpl('admin_answer_sheet_design.html', exam=exam, groups=groups,
                           questions_by_group=questions_by_group)


@app.route('/admin/exam/answer_sheet/generate/<int:id>', methods=['POST'])
@admin_required
def admin_answer_sheet_generate(id):
    exam = Exam.query.get_or_404(id)
    groups = QuestionGroup.query.filter_by(exam_id=id).order_by(QuestionGroup.sort_order).all()
    questions_by_group = [(g, g.questions) for g in groups]
    pdf_path = generate_answer_sheet_pdf(exam, questions_by_group)
    flash('答题卡PDF已生成', 'success')
    return redirect(url_for('admin_answer_sheet_design', id=id))


# ── 批量上传答题卡 ──

@app.route('/admin/exam/upload_sheets/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_upload_sheets(id):
    exam = Exam.query.get_or_404(id)
    if request.method == 'POST':
        class_id = request.form.get('class_id', 0, type=int)
        files = request.files.getlist('files')
        mode = request.form.get('mode', 'auto')  # auto / multi_pdf / single_pdf

        count = 0
        pdf_count = 0

        for f in files:
            if not f or not f.filename: continue
            if not allowed_file(f.filename): continue

            is_pdf = f.filename.lower().endswith('.pdf')

            if is_pdf:
                # ── PDF答题卡处理 ──
                pdf_path = save_file(f, prefix='sheet')
                if not pdf_path: continue

                full_pdf = os.path.join(BASE_DIR, pdf_path)

                if mode == 'multi_pdf':
                    # 模式1：一个PDF里每页是一个学生的答题卡
                    # 文件名格式：考试名_班级.pdf 或任意.pdf
                    output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'pdf_pages', f'exam{id}_{uuid.uuid4().hex[:6]}')
                    page_images = pdf_to_images(pdf_path, output_dir, dpi=200, prefix=f'sheet')

                    for i, img_full in enumerate(page_images):
                        # 将绝对路径转为相对路径
                        rel_img = img_full.replace(BASE_DIR + '/', '').replace(BASE_DIR + os.sep, '')
                        page_num = i + 1

                        # 尝试从页面内容或序号匹配学生
                        # 方案A：按学号顺序匹配班级学生
                        sid = ''
                        if class_id:
                            class_students = Student.query.filter_by(class_id=class_id).order_by(Student.student_id).all()
                            if i < len(class_students):
                                sid = class_students[i].student_id

                        if sid:
                            student = Student.query.filter_by(student_id=sid).first()
                        else:
                            student = None

                        if student:
                            existing = AnswerSheet.query.filter_by(exam_id=id, student_id=student.student_id).first()
                            if not existing:
                                sheet = AnswerSheet(exam_id=id, student_id=student.student_id,
                                                    image_path=rel_img, pdf_path=pdf_path, page_number=page_num)
                                db.session.add(sheet)
                                questions = Question.query.filter_by(exam_id=id).all()
                                for q in questions:
                                    db.session.add(ScoreDetail(answer_sheet_id=sheet.id, question_id=q.id))
                                count += 1

                else:
                    # 模式2：一个PDF = 一个学生的答题卡（可能多页）
                    # 文件名格式：学号_姓名.pdf
                    basename = os.path.splitext(secure_filename(f.filename))[0]
                    parts = basename.split('_')
                    sid_guess = parts[0] if parts else basename

                    student = Student.query.filter_by(student_id=sid_guess).first()
                    if not student:
                        student = Student.query.filter(Student.student_id.contains(sid_guess)).first()

                    if student:
                        # PDF转图片（首页用于预览）
                        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'pdf_pages', f'exam{id}_{uuid.uuid4().hex[:6]}')
                        page_images = pdf_to_images(pdf_path, output_dir, dpi=200, prefix=f'sheet_{student.student_id}')
                        preview_img = page_images[0].replace(BASE_DIR + '/', '').replace(BASE_DIR + os.sep, '') if page_images else ''

                        existing = AnswerSheet.query.filter_by(exam_id=id, student_id=student.student_id).first()
                        if not existing:
                            sheet = AnswerSheet(exam_id=id, student_id=student.student_id,
                                                image_path=preview_img, pdf_path=pdf_path,
                                                page_number=len(page_images))
                            db.session.add(sheet)
                            questions = Question.query.filter_by(exam_id=id).all()
                            for q in questions:
                                db.session.add(ScoreDetail(answer_sheet_id=sheet.id, question_id=q.id))
                            count += 1
                        else:
                            existing.image_path = preview_img or existing.image_path
                            existing.pdf_path = pdf_path
                            count += 1

                    pdf_count += 1

            else:
                # ── 图片答题卡处理（原有逻辑）──
                img_path = save_file(f, prefix='sheet')
                if not img_path: continue

                basename = os.path.splitext(secure_filename(f.filename))[0]
                parts = basename.split('_')
                sid = parts[0] if parts else basename

                student = Student.query.filter_by(student_id=sid).first()
                if not student:
                    student = Student.query.filter(Student.student_id.contains(sid)).first()

                if student:
                    existing = AnswerSheet.query.filter_by(exam_id=id, student_id=student.student_id).first()
                    if not existing:
                        sheet = AnswerSheet(exam_id=id, student_id=student.student_id, image_path=img_path)
                        db.session.add(sheet)
                        questions = Question.query.filter_by(exam_id=id).all()
                        for q in questions:
                            db.session.add(ScoreDetail(answer_sheet_id=sheet.id, question_id=q.id))
                        count += 1
                    else:
                        existing.image_path = img_path
                        count += 1

        db.session.commit()
        msg = f'成功上传 {count} 份答题卡'
        if pdf_count > 0:
            msg += f'（其中 {pdf_count} 个PDF文件）'
        flash(msg, 'success')
        return redirect(url_for('admin_upload_sheets', id=id))

    sheets = AnswerSheet.query.filter_by(exam_id=id).all()
    classes = Class.query.all()
    return render_tpl('admin_upload_sheets.html', exam=exam, sheets=sheets, classes=classes)


# ── 批改 ──

@app.route('/admin/grading/<int:exam_id>')
@admin_required
def admin_grading(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    sheets = AnswerSheet.query.filter_by(exam_id=exam_id).all()
    questions = Question.query.filter_by(exam_id=exam_id).all()

    for s in sheets:
        s.graded_count = ScoreDetail.query.filter_by(answer_sheet_id=s.id).filter(
            (ScoreDetail.ai_score >= 0) | (ScoreDetail.final_score >= 0)).count()
        s.total_q = len(questions)

    return render_tpl('admin_grading.html', exam=exam, sheets=sheets, questions=questions)


@app.route('/admin/grading/sheet/<int:sheet_id>')
@admin_required
def admin_grading_sheet(sheet_id):
    sheet = AnswerSheet.query.get_or_404(sheet_id)
    exam = sheet.exam
    details = ScoreDetail.query.filter_by(answer_sheet_id=sheet_id).all()
    return render_tpl('admin_grading_sheet.html', sheet=sheet, exam=exam, details=details)


@app.route('/admin/grading/score/<int:detail_id>', methods=['POST'])
@admin_required
def admin_grading_score(detail_id):
    """批改单题"""
    sd = ScoreDetail.query.get_or_404(detail_id)
    action = request.form.get('action', '')

    if action == 'ai_grade':
        q = sd.question
        result = AIService.grade_question(
            q.content_text, q.reference_answer, q.scoring_criteria,
            '（答题卡图片答案）', q.total_points, subject=exam.subject if (exam:=q.group.exam) else ''
        )
        sd.ai_score = result.get('score', 0)
        sd.ai_feedback = json.dumps(result, ensure_ascii=False)
        db.session.commit()
        flash(f'AI评分：{sd.ai_score}/{q.total_points}', 'success')

    elif action == 'confirm':
        sd.final_score = request.form.get('final_score', 0, type=float)
        sd.teacher_comment = request.form.get('teacher_comment', '').strip()
        db.session.commit()

        # 重算总分
        recalc_summary(sd.answer_sheet.exam_id, sd.answer_sheet.student_id)
        flash('评分已确认', 'success')

    elif action == 'batch_ai':
        # 批量AI批改此答题卡
        details = ScoreDetail.query.filter_by(answer_sheet_id=sd.answer_sheet_id, ai_score=-1).all()
        for d in details:
            q = d.question
            result = AIService.grade_question(
                q.content_text, q.reference_answer, q.scoring_criteria,
                '（答题卡图片答案）', q.total_points,
                subject=q.group.exam.subject if q.group else ''
            )
            d.ai_score = result.get('score', 0)
            d.ai_feedback = json.dumps(result, ensure_ascii=False)
        db.session.commit()
        flash(f'批量AI批改完成，共 {len(details)} 题', 'success')

    return redirect(url_for('admin_grading_sheet', sheet_id=sd.answer_sheet_id))


@app.route('/admin/grading/finalize/<int:exam_id>', methods=['POST'])
@admin_required
def admin_grading_finalize(exam_id):
    """完成批改 - 生成成绩汇总和标注答题卡"""
    exam = Exam.query.get_or_404(exam_id)
    sheets = AnswerSheet.query.filter_by(exam_id=exam_id).all()
    questions = Question.query.filter_by(exam_id=exam_id).all()

    for sheet in sheets:
        # 汇总成绩
        recalc_summary(exam_id, sheet.student_id)

        # 标注答题卡
        questions = Question.query.filter_by(exam_id=exam_id).all()
        total_score = exam.total_score

        if sheet.pdf_path:
            # PDF答题卡 → 在PDF上直接标注评分
            annotated = annotate_pdf_with_scores(
                sheet.pdf_path, sheet.score_details, questions,
                total_score, exam_name=exam.name
            )
            sheet.annotated_path = annotated
        elif sheet.image_path:
            # 图片答题卡 → 图片标注 + 同时生成PDF
            annotated_img = annotate_answer_sheet(sheet.image_path, sheet.score_details, questions)
            # 也生成标注PDF版本
            annotated_pdf = annotate_image_as_pdf(
                sheet.image_path, sheet.score_details, questions, total_score, exam.name
            )
            sheet.annotated_path = annotated_pdf or annotated_img

    # 计算排名
    recalc_ranks(exam_id)

    exam.status = '已结束'
    db.session.commit()
    flash('批改完成！成绩汇总和排名已生成', 'success')
    return redirect(url_for('admin_exam_analysis', id=exam_id))


@app.route('/admin/exam/publish/<int:id>', methods=['POST'])
@admin_required
def admin_exam_publish(id):
    exam = Exam.query.get_or_404(id)
    exam.status = '已发布'
    db.session.commit()
    flash('成绩已发布，学生可查询', 'success')
    return redirect(url_for('admin_exam_analysis', id=id))


# ── 成绩汇总与分析 ──

@app.route('/admin/exam/analysis/<int:id>')
@admin_required
def admin_exam_analysis(id):
    exam = Exam.query.get_or_404(id)
    summaries = ScoreSummary.query.filter_by(exam_id=id).order_by(ScoreSummary.total_score.desc()).all()
    questions = Question.query.filter_by(exam_id=id).order_by(Question.id).all()
    classes = Class.query.all()

    # 基本统计
    import statistics
    scores = [s.total_score for s in summaries if s.total_score is not None]
    stats = {}
    if scores:
        stats = {
            'count': len(scores),
            'avg': round(statistics.mean(scores), 2),
            'median': round(statistics.median(scores), 2),
            'max': max(scores),
            'min': min(scores),
            'stdev': round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            'pass_rate': round(sum(1 for s in scores if s >= exam.total_score * 0.6) / len(scores) * 100, 1),
            'excellent_rate': round(sum(1 for s in scores if s >= exam.total_score * 0.9) / len(scores) * 100, 1),
        }

    # 分数段统计
    if scores and exam.total_score > 0:
        step = 10
        bins = {}
        for i in range(0, int(exam.total_score) + step, step):
            lo, hi = i, i + step
            label = f'{lo}-{hi}'
            bins[label] = sum(1 for s in scores if lo <= s < hi)
        stats['bins'] = bins

    # 各题得分率
    question_stats = []
    for q in questions:
        q_details = ScoreDetail.query.filter_by(question_id=q.id).all()
        final_scores = [d.final_score for d in q_details if d.final_score >= 0]
        ai_scores = [d.ai_score for d in q_details if d.ai_score >= 0 and d.final_score < 0]
        all_scores = final_scores or ai_scores
        if all_scores:
            question_stats.append({
                'question': q,
                'avg': round(statistics.mean(all_scores), 2),
                'rate': round(statistics.mean(all_scores) / q.total_points * 100, 1) if q.total_points > 0 else 0,
                'max': max(all_scores),
                'min': min(all_scores),
                'zero_count': sum(1 for s in all_scores if s == 0),
                'full_count': sum(1 for s in all_scores if s >= q.total_points),
            })

    # 班级对比
    class_stats = []
    for c in classes:
        class_summaries = [s for s in summaries if s.class_id == c.id]
        class_scores = [s.total_score for s in class_summaries if s.total_score is not None]
        if class_scores:
            class_stats.append({
                'class': c,
                'count': len(class_scores),
                'avg': round(statistics.mean(class_scores), 2),
                'max': max(class_scores),
                'min': min(class_scores),
                'pass_rate': round(sum(1 for s in class_scores if s >= exam.total_score * 0.6) / len(class_scores) * 100, 1),
            })

    return render_tpl('admin_exam_analysis.html', exam=exam, summaries=summaries,
                           stats=stats, question_stats=question_stats, class_stats=class_stats,
                           classes=classes, questions=questions)


@app.route('/admin/exam/export/<int:id>')
@admin_required
def admin_exam_export(id):
    """导出成绩CSV"""
    exam = Exam.query.get_or_404(id)
    summaries = ScoreSummary.query.filter_by(exam_id=id).order_by(ScoreSummary.rank_in_grade).all()
    questions = Question.query.filter_by(exam_id=id).order_by(Question.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    header = ['排名', '学号', '姓名', '班级', '总分']
    for q in questions:
        header.append(f'第{q.question_number}题({q.total_points}分)')
    writer.writerow(header)

    for sm in summaries:
        row = [sm.rank_in_grade, sm.student_id, sm.student.name,
               sm.student.class_info.name if sm.student.class_info else '',
               sm.total_score]
        sheet = AnswerSheet.query.filter_by(exam_id=id, student_id=sm.student_id).first()
        if sheet:
            for q in questions:
                sd = ScoreDetail.query.filter_by(answer_sheet_id=sheet.id, question_id=q.id).first()
                score = sd.final_score if sd and sd.final_score >= 0 else (sd.ai_score if sd and sd.ai_score >= 0 else '')
                row.append(score)
        else:
            row.extend([''] * len(questions))
        writer.writerow(row)

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     as_attachment=True, download_name=f'{exam.name}_成绩.csv',
                     mimetype='text/csv')


# ── 查看标注答题卡 ──

@app.route('/admin/sheet/annotated/<int:sheet_id>')
@admin_required
def admin_sheet_annotated(sheet_id):
    sheet = AnswerSheet.query.get_or_404(sheet_id)
    path = sheet.annotated_path or sheet.image_path
    if path:
        return redirect('/' + path)
    flash('未找到答题卡图片', 'danger')
    return redirect(request.referrer or url_for('admin_dashboard'))


# ── 修改密码 ──

@app.route('/admin/change_password', methods=['GET', 'POST'])
@admin_required
def admin_change_password():
    if request.method == 'POST':
        old = request.form.get('old_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        admin = Admin.query.get(session['admin_id'])
        if not admin.check_password(old): flash('原密码错误', 'danger')
        elif new != confirm: flash('两次密码不一致', 'danger')
        elif len(new) < 6: flash('密码至少6位', 'danger')
        else:
            admin.set_password(new)
            db.session.commit()
            flash('密码修改成功', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_tpl('admin_change_password.html')


# ════════════════ 初始化 ════════════════

def init_db():
    db.create_all()
    if Admin.query.count() == 0:
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # 示例数据
        classes = [
            Class(name='高三1班', grade='高三', teacher='李老师'),
            Class(name='高三2班', grade='高三', teacher='王老师'),
        ]
        db.session.add_all(classes)
        db.session.flush()

        students_data = [
            ('2024001', '张三', classes[0].id), ('2024002', '李四', classes[0].id),
            ('2024003', '王五', classes[0].id), ('2024004', '赵六', classes[1].id),
            ('2024005', '钱七', classes[1].id), ('2024006', '孙八', classes[1].id),
            ('2024007', '周九', classes[0].id), ('2024008', '吴十', classes[1].id),
        ]
        for sid, name, cid in students_data:
            db.session.add(Student(student_id=sid, name=name, class_id=cid))

        exam = Exam(name='2024期末考试', subject='数学', total_score=100, exam_date='2024-06-15')
        db.session.add(exam)
        db.session.flush()

        # 大题
        g1 = QuestionGroup(exam_id=exam.id, name='一、选择题', question_type='选择题', total_points=30, sort_order=1)
        g2 = QuestionGroup(exam_id=exam.id, name='二、填空题', question_type='填空题', total_points=20, sort_order=2)
        g3 = QuestionGroup(exam_id=exam.id, name='三、解答题', question_type='解答题', total_points=50, sort_order=3)
        db.session.add_all([g1, g2, g3])
        db.session.flush()

        # 小题
        qs = [
            Question(group_id=g1.id, exam_id=exam.id, question_number='1', total_points=5, content_text='已知集合A={1,2,3}，B={2,3,4}，则A∩B='),
            Question(group_id=g1.id, exam_id=exam.id, question_number='2', total_points=5, content_text='函数f(x)=x²-2x+1的最小值为'),
            Question(group_id=g1.id, exam_id=exam.id, question_number='3', total_points=5, content_text='等差数列{an}中，a1=1,d=2，则a5='),
            Question(group_id=g1.id, exam_id=exam.id, question_number='4', total_points=5, content_text='sin30°的值为'),
            Question(group_id=g1.id, exam_id=exam.id, question_number='5', total_points=5, content_text='log₂8的值为'),
            Question(group_id=g1.id, exam_id=exam.id, question_number='6', total_points=5, content_text='向量a=(1,2)，b=(2,1)，则a·b='),
            Question(group_id=g2.id, exam_id=exam.id, question_number='7', total_points=5, content_text='已知f(x)=2x+1，则f(3)=___'),
            Question(group_id=g2.id, exam_id=exam.id, question_number='8', total_points=5, content_text='若|a|=3,|b|=4,a⊥b，则|a+b|=___'),
            Question(group_id=g2.id, exam_id=exam.id, question_number='9', total_points=5, content_text='C(5,2)=___'),
            Question(group_id=g2.id, exam_id=exam.id, question_number='10', total_points=5, content_text='lim(n→∞) 1/n =___'),
            Question(group_id=g3.id, exam_id=exam.id, question_number='11', total_points=12, content_text='求函数f(x)=x³-3x的极值'),
            Question(group_id=g3.id, exam_id=exam.id, question_number='12', total_points=12, content_text='证明：对任意正整数n，1+2+...+n=n(n+1)/2'),
            Question(group_id=g3.id, exam_id=exam.id, question_number='13', total_points=13, content_text='已知数列{an}满足a1=1，an+1=2an+1，求通项公式an'),
            Question(group_id=g3.id, exam_id=exam.id, question_number='14', total_points=13, content_text='在△ABC中，已知a=3,b=4,C=60°，求c和面积S'),
        ]
        db.session.add_all(qs)
        db.session.commit()
        print('✅ 初始化完成 admin/admin123')


if __name__ == '__main__':
    # Auto-install dependencies
    import subprocess, sys
    REQUIRED = {'flask': 'flask', 'flask_sqlalchemy': 'flask_sqlalchemy', 
                'Pillow': 'Pillow', 'PyMuPDF': 'fitz', 'reportlab': 'reportlab', 
                'requests': 'requests', 'werkzeug': 'werkzeug'}
    for pkg_name, import_name in REQUIRED.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"正在安装 {pkg_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name, "-q",
                                   "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
    print("所有依赖已就绪")

    with app.app_context():
        init_db()
    port = int(os.environ.get('PORT', 5000))

    import socket as _socket
    local_ip = '127.0.0.1'
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print(f'\n{"="*55}')
    print(f'  智能阅卷系统已启动！')
    print(f'  电脑访问：http://127.0.0.1:{port}')
    print(f'  手机访问：http://{local_ip}:{port}')
    print(f'  管理员：admin / admin123')
    print(f'  按 Ctrl+C 停止服务')
    print(f'{"="*55}\n')

    app.run(host='0.0.0.0', port=port, debug=False)
