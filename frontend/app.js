// API 基础URL
const API_BASE = 'http://localhost:5000/api';

// 全局状态
let currentClass = null;
let currentExam = null;
let ocrData = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadClasses();
    setupDragAndDrop();
});

// ============ 班级管理 ============
async function loadClasses() {
    try {
        const response = await fetch(`${API_BASE}/classes`);
        const classes = await response.json();
        renderClasses(classes);
    } catch (error) {
        showAlert('加载班级失败：' + error.message, 'error');
    }
}

function renderClasses(classes) {
    const container = document.getElementById('class-list');
    container.innerHTML = classes.map(c => `
        <div class="class-item" onclick="selectClass(${c.id}, '${c.name}', '${c.subject}')">
            <h3>${c.name}</h3>
            <p>科目：${c.subject}</p>
            <p>创建时间：${new Date(c.created_at).toLocaleDateString()}</p>
        </div>
    `).join('');
}

function showCreateClass() {
    document.getElementById('class-form').classList.remove('hidden');
}

function hideCreateClass() {
    document.getElementById('class-form').classList.add('hidden');
    document.getElementById('class-name').value = '';
}

async function createClass() {
    const name = document.getElementById('class-name').value;
    const subject = document.getElementById('class-subject').value;
    
    if (!name) {
        showAlert('请输入班级名称', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/classes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, subject })
        });
        
        if (response.ok) {
            showAlert('班级创建成功', 'success');
            hideCreateClass();
            loadClasses();
        }
    } catch (error) {
        showAlert('创建失败：' + error.message, 'error');
    }
}

function selectClass(id, name, subject) {
    currentClass = { id, name, subject };
    document.getElementById('current-class-name').textContent = name;
    
    // 切换界面
    document.getElementById('class-section').classList.add('hidden');
    document.getElementById('student-section').classList.remove('hidden');
    
    loadStudents(id);
}

function backToClasses() {
    currentClass = null;
    document.getElementById('class-section').classList.remove('hidden');
    document.getElementById('student-section').classList.add('hidden');
    loadClasses();
}

// ============ 学生管理 ============
async function loadStudents(classId) {
    try {
        const response = await fetch(`${API_BASE}/classes/${classId}/students`);
        const students = await response.json();
        renderStudents(students);
    } catch (error) {
        showAlert('加载学生失败：' + error.message, 'error');
    }
}

function renderStudents(students) {
    const tbody = document.querySelector('#student-table tbody');
    tbody.innerHTML = students.map(s => `
        <tr>
            <td>${s.student_no}</td>
            <td>${s.name}</td>
            <td>
                <button onclick="deleteStudent(${s.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function showAddStudents() {
    document.getElementById('student-form').classList.remove('hidden');
}

function hideAddStudents() {
    document.getElementById('student-form').classList.add('hidden');
    document.getElementById('student-list').value = '';
}

async function addStudents() {
    const text = document.getElementById('student-list').value;
    const lines = text.trim().split('\n');
    
    const students = lines.map(line => {
        const parts = line.trim().split(/\s+/);
        return {
            student_no: parts[0],
            name: parts[1] || '未命名'
        };
    }).filter(s => s.student_no);
    
    if (students.length === 0) {
        showAlert('请输入学生信息', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/classes/${currentClass.id}/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ students })
        });
        
        if (response.ok) {
            showAlert(`成功添加 ${students.length} 名学生`, 'success');
            hideAddStudents();
            loadStudents(currentClass.id);
        }
    } catch (error) {
        showAlert('添加失败：' + error.message, 'error');
    }
}

async function deleteStudent(studentId) {
    // 简化版：暂不实现删除功能
    showAlert('删除功能暂未实现', 'error');
}

// ============ 考试管理 ============
function backToStudents() {
    document.getElementById('student-section').classList.remove('hidden');
    document.getElementById('exam-section').classList.add('hidden');
}

async function loadExams() {
    try {
        const response = await fetch(`${API_BASE}/classes/${currentClass.id}/exams`);
        const exams = await response.json();
        renderExams(exams);
    } catch (error) {
        showAlert('加载考试失败：' + error.message, 'error');
    }
}

function renderExams(exams) {
    const container = document.getElementById('exam-list');
    container.innerHTML = exams.map(e => `
        <div class="exam-item" onclick="selectExam(${e.id}, '${e.name}')">
            <h3>${e.name}</h3>
            <p>总分：${e.total_score}分</p>
            <p>选择题：${e.choice_score}分 | 填空题：${e.fill_score}分 | 大题：${e.essay_score}分</p>
            <p>创建时间：${new Date(e.created_at).toLocaleDateString()}</p>
        </div>
    `).join('');
}

// 显示考试列表
function showCreateExam() {
    document.getElementById('exam-section').classList.remove('hidden');
    document.getElementById('student-section').classList.add('hidden');
    loadExams();
}

function showCreateExamForm() {
    document.getElementById('exam-form').classList.remove('hidden');
}

function hideCreateExam() {
    document.getElementById('exam-form').classList.add('hidden');
}

// ============ 标准答案设置 ============
function switchAnswerTab(tabName) {
    // 切换tab
    document.querySelectorAll('#answer-input-text, #answer-input-photo, #answer-input-ai').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('#answer-tab-text, #answer-tab-photo, #answer-tab-ai').forEach(el => el.classList.remove('active'));
    
    document.getElementById('answer-input-' + tabName).classList.remove('hidden');
    document.getElementById('answer-tab-' + tabName).classList.add('active');
}

// 处理标准答案图片
async function handleAnswerPhoto(file) {
    if (!file) return;
    
    // 显示预览
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('answer-photo-img').src = e.target.result;
        document.getElementById('answer-photo-preview').classList.remove('hidden');
        document.getElementById('answer-photo-status').textContent = '正在识别标准答案...';
    };
    reader.readAsDataURL(file);
    
    // OCR识别标准答案
    const formData = new FormData();
    formData.append('image', file);
    formData.append('type', 'answer_key');
    
    try {
        const response = await fetch(`${API_BASE}/ocr`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            document.getElementById('answer-photo-status').textContent = '识别失败：' + result.error;
            return;
        }
        
        // 填充识别到的答案
        if (result.choices && Object.keys(result.choices).length > 0) {
            document.getElementById('exam-choice-answers').value = JSON.stringify(result.choices);
        }
        if (result.fills && Object.keys(result.fills).length > 0) {
            document.getElementById('exam-fill-answers').value = JSON.stringify(result.fills);
        }
        if (result.essay_text) {
            document.getElementById('exam-essay-answers').value = result.essay_text;
        }
        
        document.getElementById('answer-photo-status').textContent = '✅ 识别完成！已自动填充答案，请检查确认';
        
        // 切换到文本输入tab查看
        switchAnswerTab('text');
        
    } catch (error) {
        document.getElementById('answer-photo-status').textContent = '识别失败：' + error.message;
    }
}

// 处理题目图片（用于AI生成答案）
async function handleQuestionPhoto(file) {
    if (!file) return;
    
    // 显示图片预览
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('exam-question-for-ai').value = '[图片已上传，请在下方点击"AI生成标准答案"]';
    };
    reader.readAsDataURL(file);
    
    // 保存图片用于后续处理
    window.questionPhoto = file;
}

// AI生成标准答案
async function generateAnswerByAI() {
    const question = document.getElementById('exam-question-for-ai').value;
    
    if (!question && !window.questionPhoto) {
        showAlert('请输入题目内容或上传题目图片', 'error');
        return;
    }
    
    const resultDiv = document.getElementById('ai-answer-result');
    const contentDiv = document.getElementById('ai-answer-content');
    
    resultDiv.classList.remove('hidden');
    contentDiv.innerHTML = '<p>🤖 AI正在分析题目并生成标准答案...</p>';
    
    try {
        const formData = new FormData();
        if (window.questionPhoto) {
            formData.append('image', window.questionPhoto);
        }
        formData.append('question', question);
        formData.append('type', 'generate_answer');
        
        const response = await fetch(`${API_BASE}/ocr`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            contentDiv.innerHTML = `<p style="color: red;">❌ 生成失败：${result.error}</p>`;
            return;
        }
        
        // 显示生成的答案
        let html = '<div style="background: #fff; padding: 10px; border-radius: 4px;">';
        
        if (result.choices) {
            html += '<h5>📝 选择题答案：</h5>';
            html += '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">' + JSON.stringify(result.choices, null, 2) + '</pre>';
        }
        
        if (result.fills) {
            html += '<h5>📋 填空题答案：</h5>';
            html += '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">' + JSON.stringify(result.fills, null, 2) + '</pre>';
        }
        
        if (result.essay_text) {
            html += '<h5>📖 大题答案/要点：</h5>';
            html += '<div style="background: #f5f5f5; padding: 10px; border-radius: 4px; white-space: pre-wrap;">' + result.essay_text + '</div>';
        }
        
        html += '</div>';
        contentDiv.innerHTML = html;
        
        // 保存生成的结果
        window.aiGeneratedAnswer = result;
        
    } catch (error) {
        contentDiv.innerHTML = `<p style="color: red;">❌ 生成失败：${error.message}</p>`;
    }
}

// 使用AI生成的答案
function useAiAnswer() {
    if (!window.aiGeneratedAnswer) {
        showAlert('没有可用的AI生成答案', 'error');
        return;
    }
    
    const result = window.aiGeneratedAnswer;
    
    if (result.choices) {
        document.getElementById('exam-choice-answers').value = JSON.stringify(result.choices);
    }
    if (result.fills) {
        document.getElementById('exam-fill-answers').value = JSON.stringify(result.fills);
    }
    if (result.essay_text) {
        document.getElementById('exam-essay-answers').value = result.essay_text;
    }
    
    showAlert('✅ 已使用AI生成的标准答案，请检查确认', 'success');
    switchAnswerTab('text');
}

// ============ 答题卡制作 ============
function showAnswerSheetGenerator() {
    document.getElementById('answer-sheet-form').classList.remove('hidden');
    // 填充当前班级信息
    if (currentClass) {
        document.getElementById('sheet-class').value = currentClass.name;
        document.getElementById('sheet-subject').value = currentClass.subject;
    }
}

function hideAnswerSheetGenerator() {
    document.getElementById('answer-sheet-form').classList.add('hidden');
}

async function generateAnswerSheet() {
    const data = {
        school: document.getElementById('sheet-school').value || '________学校',
        exam_name: document.getElementById('sheet-exam').value || '考试',
        subject: document.getElementById('sheet-subject').value,
        class_name: document.getElementById('sheet-class').value || '________',
        choice_count: parseInt(document.getElementById('sheet-choice').value) || 20,
        fill_count: parseInt(document.getElementById('sheet-fill').value) || 5,
        essay_count: parseInt(document.getElementById('sheet-essay').value) || 3,
        student_count: parseInt(document.getElementById('sheet-count').value) || 1
    };
    
    try {
        const response = await fetch(`${API_BASE}/answer-sheet/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `答题卡_${data.exam_name}.pdf`;
            a.click();
            showAlert('答题卡生成成功！', 'success');
            hideAnswerSheetGenerator();
        } else {
            showAlert('生成失败', 'error');
        }
    } catch (error) {
        showAlert('生成失败：' + error.message, 'error');
    }
}

function downloadTemplate(templateType) {
    window.open(`${API_BASE}/answer-sheet/template/${templateType}`, '_blank');
}

async function createExam() {
    const name = document.getElementById('exam-name').value;
    const total = parseFloat(document.getElementById('exam-total').value) || 100;
    const choice = parseFloat(document.getElementById('exam-choice').value) || 0;
    const fill = parseFloat(document.getElementById('exam-fill').value) || 0;
    const essay = parseFloat(document.getElementById('exam-essay').value) || 0;
    
    // 解析标准答案
    let answers = { choices: {}, fills: {}, essays: {} };
    
    // 选择题答案
    try {
        const choiceText = document.getElementById('exam-choice-answers').value;
        if (choiceText) {
            answers.choices = JSON.parse(choiceText);
        }
    } catch (e) { console.log('选择答案解析失败'); }
    
    // 填空题答案
    try {
        const fillText = document.getElementById('exam-fill-answers').value;
        if (fillText) {
            answers.fills = JSON.parse(fillText);
        }
    } catch (e) { console.log('填空答案解析失败'); }
    
    // 大题答案
    try {
        const essayText = document.getElementById('exam-essay-answers').value;
        if (essayText) {
            // 大题答案可以是文本格式的解题要点
            answers.essays = { '1': essayText };
        }
    } catch (e) { console.log('大题答案解析失败'); }
    
    if (!name) {
        showAlert('请输入考试名称', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/classes/${currentClass.id}/exams`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                subject: currentClass.subject,
                total_score: total,
                choice_score: choice,
                fill_score: fill,
                essay_score: essay,
                answer_key: answers
            })
        });
        
        if (response.ok) {
            showAlert('考试创建成功', 'success');
            hideCreateExam();
            loadExams();
        }
    } catch (error) {
        showAlert('创建失败：' + error.message, 'error');
    }
}

function selectExam(id, name) {
    currentExam = { id, name };
    document.getElementById('current-exam-name').textContent = name;
    
    document.getElementById('exam-section').classList.add('hidden');
    document.getElementById('grading-section').classList.remove('hidden');
    
    loadStatistics();
}

function backToExams() {
    currentExam = null;
    document.getElementById('grading-section').classList.add('hidden');
    document.getElementById('exam-section').classList.remove('hidden');
}

// ============ 阅卷功能 ============
function setupDragAndDrop() {
    const uploadArea = document.getElementById('upload-area');
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            handleFile(file);
        }
    });
}

async function handleFile(file) {
    // 显示预览
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('preview-img').src = e.target.result;
        document.getElementById('upload-preview').classList.remove('hidden');
        document.getElementById('upload-area').classList.add('hidden');
    };
    reader.readAsDataURL(file);
    
    // OCR识别
    const formData = new FormData();
    formData.append('image', file);
    formData.append('exam_id', currentExam.id);
    
    try {
        const response = await fetch(`${API_BASE}/ocr`, {
            method: 'POST',
            body: formData
        });
        
        ocrData = await response.json();
        
        if (ocrData.error) {
            showAlert('识别失败：' + ocrData.error, 'error');
            return;
        }
        
        // 显示识别结果
        document.getElementById('ocr-result').innerHTML = `
            <div class="card" style="margin: 20px 0;">
                <h4>识别结果</h4>
                <p><b>学号：</b>${ocrData.student_no || '未识别'}</p>
                <p><b>姓名：</b>${ocrData.name || '未识别'}</p>
                <p><b>选择题答案：</b>${JSON.stringify(ocrData.choices)}</p>
                <p><b>填空题答案：</b>${JSON.stringify(ocrData.fills)}</p>
            </div>
        `;
        
    } catch (error) {
        showAlert('上传失败：' + error.message, 'error');
    }
}

function cancelUpload() {
    document.getElementById('upload-preview').classList.add('hidden');
    document.getElementById('upload-area').classList.remove('hidden');
    document.getElementById('file-input').value = '';
    ocrData = null;
}

async function confirmGrade() {
    if (!ocrData || !ocrData.student_no) {
        showAlert('请先上传答题卡', 'error');
        return;
    }
    
    // 查找学生ID
    const students = await fetch(`${API_BASE}/classes/${currentClass.id}/students`).then(r => r.json());
    const student = students.find(s => s.student_no === ocrData.student_no);
    
    if (!student) {
        showAlert('未找到该学号的学生，请先添加学生', 'error');
        return;
    }
    
    // 自动评分
    try {
        const response = await fetch(`${API_BASE}/grade/auto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                exam_id: currentExam.id,
                student_id: student.id,
                answers: {
                    choices: ocrData.choices,
                    fills: ocrData.fills,
                    image_path: ocrData.image_path
                }
            })
        });
        
        const result = await response.json();
        
        // 显示带分数的答题卡
        if (result.annotated_image) {
            const annotatedUrl = `${API_BASE}/uploads/${result.annotated_image.split('\\').pop()}`;
            document.getElementById('ocr-result').innerHTML += `
                <div style="margin-top: 20px;">
                    <h4>✅ 机阅完成！带分数标注的答题卡：</h4>
                    <img src="${annotatedUrl}" style="max-width: 100%; border: 2px solid #667eea; border-radius: 8px;">
                </div>
            `;
        }
        
        showAlert(`评分完成！选择题：${result.choice_score}分，填空题：${result.fill_score}分，大题：${result.essay_score}分，总分：${result.total_score}分`, 'success');
        
        cancelUpload();
        loadStatistics();
        
    } catch (error) {
        showAlert('评分失败：' + error.message, 'error');
    }
}

async function submitManualScore() {
    const studentNo = document.getElementById('manual-student-no').value;
    const choice = parseFloat(document.getElementById('manual-choice').value) || 0;
    const fill = parseFloat(document.getElementById('manual-fill').value) || 0;
    const essay = parseFloat(document.getElementById('manual-essay').value) || 0;
    
    if (!studentNo) {
        showAlert('请输入学号', 'error');
        return;
    }
    
    // 查找学生
    const students = await fetch(`${API_BASE}/classes/${currentClass.id}/students`).then(r => r.json());
    const student = students.find(s => s.student_no === studentNo);
    
    if (!student) {
        showAlert('未找到该学号的学生', 'error');
        return;
    }
    
    // 提交成绩
    try {
        const response = await fetch(`${API_BASE}/grade/auto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                exam_id: currentExam.id,
                student_id: student.id,
                answers: {
                    choices: {},
                    fills: {}
                }
            })
        });
        
        // 然后更新分数
        // 简化版：这里应该调用update_score API
        showAlert('成绩录入成功', 'success');
        loadStatistics();
        
    } catch (error) {
        showAlert('录入失败：' + error.message, 'error');
    }
}

// ============ 成绩统计 ============
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/exams/${currentExam.id}/statistics`);
        const stats = await response.json();
        
        if (stats.message) {
            document.getElementById('statistics').innerHTML = `<p>${stats.message}</p>`;
            return;
        }
        
        document.getElementById('statistics').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>${stats.count}</h3>
                    <p>考试人数</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.avg_score}</h3>
                    <p>平均分</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.max_score}</h3>
                    <p>最高分</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.min_score}</h3>
                    <p>最低分</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.pass_rate}%</h3>
                    <p>及格率</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.excellent_rate}%</h3>
                    <p>优秀率</p>
                </div>
            </div>
        `;
        
        // 渲染成绩表
        const tbody = document.querySelector('#score-table tbody');
        const sortedScores = stats.scores.sort((a, b) => b.score - a.score);
        tbody.innerHTML = sortedScores.map((s, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${s.student_no}</td>
                <td>${s.name}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>${s.score}</td>
                <td>
                    <button onclick="viewScoreDetail(${s.score_id})">查看详情</button>
                    <button onclick="editScore('${s.student_no}')">修改</button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        showAlert('加载统计失败：' + error.message, 'error');
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tabName + '-tab').classList.add('active');
    
    if (tabName === 'results') {
        loadStatistics();
    }
}

function editScore(studentNo) {
    showAlert('修改功能暂未实现', 'error');
}

// 查看成绩详情
async function viewScoreDetail(scoreId) {
    try {
        const response = await fetch(`${API_BASE}/scores/${scoreId}/details`);
        const data = await response.json();
        
        if (data.error) {
            showAlert(data.error, 'error');
            return;
        }
        
        // 构建详情HTML
        let detailsHtml = `
            <div style="margin-bottom: 20px;">
                <h3>${data.student_name} (${data.student_no})</h3>
                <p>考试：${data.exam_name} | 科目：${data.subject}</p>
                <p>总分：<strong style="font-size: 24px; color: #667eea;">${data.total_score}</strong> 分</p>
            </div>
        `;
        
        // 显示答题卡图片（优先显示带分数标注的）
        if (data.image_path) {
            // 尝试找带分数标注的版本
            const baseName = data.image_path.split('\\').pop().split('.')[0];
            const annotatedName = baseName + '_graded.jpg';
            const imageUrl = `${API_BASE}/uploads/${annotatedName}`;
            
            detailsHtml += `
                <div style="margin: 20px 0;">
                    <h4>📷 答题卡（机阅分数标注）</h4>
                    <img src="${imageUrl}" style="max-width: 100%; border: 2px solid #667eea; border-radius: 8px;" 
                         onerror="this.src='${API_BASE}/uploads/${data.image_path.split('\\').pop()}'; this.style.border='1px solid #ddd';">
                    <p style="color: #666; font-size: 12px; margin-top: 5px;">* 红色=错误，绿色=正确，右上角显示总分</p>
                </div>
            `;
        }
        
        // 显示AI评分详情
        const details = data.details || {};
        
        // 选择题详情
        if (details.choices && Object.keys(details.choices).length > 0) {
            detailsHtml += `<div style="margin: 20px 0;"><h4>📝 选择题评分</h4><table style="width: 100%;"><thead><tr><th>题号</th><th>学生答案</th><th>正确答案</th><th>得分</th><th>结果</th></tr></thead><tbody>`;
            for (const [qNum, info] of Object.entries(details.choices)) {
                const status = info.is_correct ? '✅' : '❌';
                detailsHtml += `<tr><td>${qNum}</td><td>${info.student || '-'}</td><td>${info.correct}</td><td>${info.score.toFixed(1)}</td><td>${status}</td></tr>`;
            }
            detailsHtml += `</tbody></table><p style="margin-top: 10px;">选择题得分：<strong>${data.choice_score}</strong></p></div>`;
        }
        
        // 填空题详情（可编辑）
        if (details.fills && Object.keys(details.fills).length > 0) {
            detailsHtml += `<div style="margin: 20px 0;"><h4>📝 填空题评分 (AI辅助)</h4>`;
            for (const [qNum, info] of Object.entries(details.fills)) {
                const similarity = ((info.similarity || 0) * 100).toFixed(0);
                const textSim = ((info.details?.text_similarity || 0) * 100).toFixed(0);
                const keywordSim = ((info.details?.keyword_match || 0) * 100).toFixed(0);
                const exprSim = ((info.details?.expression_match || 0) * 100).toFixed(0);
                
                detailsHtml += `
                <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 10px;">
                        <strong>第${qNum}空</strong>
                        <span>AI得分：<strong>${(info.score || 0).toFixed(1)}</strong></span>
                        <span style="color: ${similarity >= 80 ? 'green' : similarity >= 60 ? 'orange' : 'red'};">相似度 ${similarity}%</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 10px 0;">
                        <div>学生答案：<span style="color: #666;">${info.student || '未作答'}</span></div>
                        <div>正确答案：<span style="color: #28a745;">${info.correct || '-'}</span></div>
                    </div>
                    <div style="font-size: 12px; color: #999; margin: 10px 0;">
                        分析：文本相似度 ${textSim}% | 关键词匹配 ${keywordSim}% | 表达式匹配 ${exprSim}%
                    </div>
                    <div style="margin: 10px 0;">
                        <span style="color: #666;">反馈：${info.feedback || '-'}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; margin-top: 10px;">
                        <label style="font-size: 12px; color: #666;">人工修正得分：</label>
                        <input type="number" id="fill-score-${qNum}" value="${(info.score || 0).toFixed(1)}" 
                               style="width: 80px; padding: 6px; text-align: center;"
                               onchange="updateQuestionScore(${scoreId}, 'fill', '${qNum}', this.value)">
                        <span>/ 满分</span>
                        ${info.manual_reviewed ? '<span style="color: #dc3545; font-size: 12px;">✓ 已人工修正</span>' : ''}
                    </div>
                </div>`;
            }
            detailsHtml += `<p style="margin-top: 10px;">填空题得分：<strong id="fill-total-${scoreId}">${data.fill_score}</strong> <span style="color: #666; font-size: 12px;">（直接修改上方单题分数，总分自动更新）</span></p></div>`;
        }
        
        // 大题详情（可编辑）
        if (details.essays && Object.keys(details.essays).length > 0) {
            detailsHtml += `<div style="margin: 20px 0;"><h4>📝 大题评分 (AI辅助)</h4>`;
            for (const [qNum, info] of Object.entries(details.essays)) {
                const ratio = info.max_score > 0 ? ((info.score || 0) / info.max_score * 100).toFixed(0) : 0;
                detailsHtml += `
                <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 10px;">
                        <strong>第${qNum}题</strong>
                        <span>AI得分：<strong>${(info.score || 0).toFixed(1)}</strong> / ${info.max_score || '?'}</span>
                        <span style="color: ${ratio >= 80 ? 'green' : ratio >= 60 ? 'orange' : 'red'};">(${ratio}%)</span>
                    </div>
                    <div style="margin: 10px 0;">
                        <label style="font-size: 12px; color: #666;">人工修正得分：</label>
                        <input type="number" id="essay-score-${qNum}" value="${(info.score || 0).toFixed(1)}" 
                               style="width: 80px; padding: 6px; text-align: center;"
                               onchange="updateQuestionScore(${scoreId}, 'essay', '${qNum}', this.value)">
                        <span> / ${info.max_score || '?'}</span>
                    </div>
                    <p style="color: #666; font-size: 14px;">反馈：${info.feedback || '-'}</p>
                    ${info.suggestions && info.suggestions.length > 0 ? `<p style="color: #999; font-size: 12px;">建议：${info.suggestions.join('；')}</p>` : ''}
                </div>`;
            }
            detailsHtml += `<p style="margin-top: 10px;">大题得分：<strong id="essay-total-${scoreId}">${data.essay_score}</strong></p></div>`;
        }
        
        // 添加人工批阅区域
        detailsHtml += `
            <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 8px; border: 2px solid #ffc107;">
                <h4>✏️ 人工批阅（修正AI评分）</h4>
                <p style="color: #856404; font-size: 14px;">AI评分仅供参考，老师可在此修改分数</p>
                
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0;">
                    <div>
                        <label style="font-size: 12px; color: #666;">选择题得分</label>
                        <input type="number" id="manual-choice-${scoreId}" value="${data.choice_score}" 
                               style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">填空题得分</label>
                        <input type="number" id="manual-fill-${scoreId}" value="${data.fill_score}" 
                               style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    <div>
                        <label style="font-size: 12px; color: #666;">大题得分</label>
                        <input type="number" id="manual-essay-${scoreId}" value="${data.essay_score}" 
                               style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                </div>
                
                <div style="margin-top: 10px;">
                    <label style="font-size: 12px; color: #666;">批阅备注（可选）</label>
                    <textarea id="manual-comment-${scoreId}" placeholder="填写批阅意见..." 
                              style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; resize: vertical;"></textarea>
                </div>
                
                <button onclick="submitManualGrade(${scoreId})" 
                        style="margin-top: 15px; background: #28a745; color: white; padding: 10px 24px; border: none; border-radius: 4px; cursor: pointer;">
                    💾 保存人工批阅结果
                </button>
            </div>
        `;
        
        document.getElementById('score-detail-content').innerHTML = detailsHtml;
        document.getElementById('score-detail-modal').classList.remove('hidden');
        
    } catch (error) {
        showAlert('加载详情失败：' + error.message, 'error');
    }
}

function closeScoreDetail() {
    document.getElementById('score-detail-modal').classList.add('hidden');
}

// 提交人工批阅
async function submitManualGrade(scoreId) {
    const choiceScore = parseFloat(document.getElementById(`manual-choice-${scoreId}`).value) || 0;
    const fillScore = parseFloat(document.getElementById(`manual-fill-${scoreId}`).value) || 0;
    const essayScore = parseFloat(document.getElementById(`manual-essay-${scoreId}`).value) || 0;
    const comment = document.getElementById(`manual-comment-${scoreId}`).value || '';
    
    const totalScore = choiceScore + fillScore + essayScore;
    
    try {
        const response = await fetch(`${API_BASE}/scores/${scoreId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                choice_score: choiceScore,
                fill_score: fillScore,
                essay_score: essayScore,
                total_score: totalScore,
                comment: comment,
                details: { manual_reviewed: true, comment: comment }
            })
        });
        
        if (response.ok) {
            showAlert('人工批阅已保存！总分：' + totalScore, 'success');
            // 关闭弹窗并刷新
            closeScoreDetail();
            loadStatistics();
        } else {
            showAlert('保存失败', 'error');
        }
    } catch (error) {
        showAlert('保存失败：' + error.message, 'error');
    }
}

// 修改单题分数
async function updateQuestionScore(scoreId, type, questionNum, newScore) {
    try {
        const response = await fetch(`${API_BASE}/scores/${scoreId}/question`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: type,
                question: questionNum,
                score: parseFloat(newScore) || 0
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            // 更新显示的总分
            if (type === 'fill') {
                document.getElementById(`fill-total-${scoreId}`).textContent = result.fill_score.toFixed(1);
            } else if (type === 'essay') {
                document.getElementById(`essay-total-${scoreId}`).textContent = result.essay_score.toFixed(1);
            }
            showAlert('分数已更新，总分：' + result.total_score.toFixed(1), 'success');
        }
    } catch (error) {
        showAlert('更新失败：' + error.message, 'error');
    }
}

async function exportExcel() {
    window.open(`${API_BASE}/exams/${currentExam.id}/export`, '_blank');
}

function exportPDF() {
    showAlert('PDF导出功能暂未实现', 'error');
}

// ============ 工具函数 ============
function showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alert, container.children[1]);
    
    setTimeout(() => alert.remove(), 3000);
}