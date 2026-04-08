# -*- coding: utf-8 -*-
"""
答题卡生成器
生成可打印的PDF答题卡
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, gray, white
import os

class AnswerSheetGenerator:
    """答题卡生成器"""
    
    def __init__(self):
        # 注册中文字体
        try:
            pdfmetrics.registerFont(TTFont('SimHei', 'C:\\Windows\\Fonts\\simhei.ttf'))
            self.font_name = 'SimHei'
        except:
            self.font_name = 'Helvetica'
    
    def generate(self, output_path, exam_info):
        """
        生成答题卡PDF
        
        exam_info = {
            'school': '学校名称',
            'class_name': '班级',
            'exam_name': '考试名称',
            'subject': '科目',
            'choice_count': 20,  # 选择题数量
            'fill_count': 5,     # 填空题数量
            'essay_count': 3,    # 大题数量
            'student_count': 30  # 学生人数（生成相应份数）
        }
        """
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        
        for i in range(exam_info.get('student_count', 1)):
            self._draw_single_sheet(c, width, height, exam_info, i + 1)
            c.showPage()
        
        c.save()
        return output_path
    
    def _draw_single_sheet(self, c, width, height, exam_info, sheet_no):
        """绘制单张答题卡"""
        # 标题
        c.setFont(self.font_name, 16)
        c.drawCentredString(width/2, height - 2*cm, 
                           f"{exam_info.get('school', '')} {exam_info.get('exam_name', '答题卡')}")
        
        # 基本信息区
        y = height - 3.5*cm
        c.setFont(self.font_name, 11)
        
        # 姓名、班级、学号填写区
        c.drawString(2*cm, y, "姓名：________________")
        c.drawString(7*cm, y, f"班级：{exam_info.get('class_name', '________')}")
        c.drawString(12*cm, y, "学号：________________")
        
        y -= 1.2*cm
        c.drawString(2*cm, y, f"科目：{exam_info.get('subject', '________')}")
        c.drawString(7*cm, y, f"第 {sheet_no} 页")
        
        # 总分区（放在右上角显眼位置）
        c.setStrokeColor(gray)
        c.setLineWidth(1)
        # 总分框
        c.rect(width - 5*cm, y - 0.3*cm, 3*cm, 1*cm, fill=0)
        c.setFont(self.font_name, 9)
        c.drawString(width - 4.8*cm, y + 0.1*cm, "总分")
        c.setFont(self.font_name, 12)
        c.drawString(width - 3.5*cm, y + 0.1*cm, "_____")
        c.setStrokeColor(black)
        
        # 填涂说明
        y -= 1.5*cm
        c.setFont(self.font_name, 9)
        c.setFillColor(gray)
        c.drawString(2*cm, y, "填涂说明：用2B铅笔将选中项涂黑涂满，修改时用橡皮擦干净")
        c.setFillColor(black)
        
        # 选择题区域
        y -= 1.5*cm
        c.setFont(self.font_name, 12)
        c.drawString(2*cm, y, "一、选择题（请用2B铅笔填涂）")
        
        choice_count = exam_info.get('choice_count', 20)
        y -= 1*cm
        
        # 每行5题
        cols = 5
        rows = (choice_count + cols - 1) // cols
        
        for row in range(rows):
            x = 2*cm
            for col in range(cols):
                q_num = row * cols + col + 1
                if q_num > choice_count:
                    break
                
                # 题号
                c.setFont(self.font_name, 10)
                c.drawString(x, y, f"{q_num:2d}.")
                
                # 选项框
                box_size = 4*mm
                for opt_idx, opt in enumerate(['A', 'B', 'C', 'D']):
                    box_x = x + 8*mm + opt_idx * 8*mm
                    c.rect(box_x, y - 1*mm, box_size, box_size, fill=0)
                    c.setFont(self.font_name, 8)
                    c.drawString(box_x + 1*mm, y + 1*mm, opt)
                
                x += 4.5*cm
            
            y -= 0.8*cm
            if y < 10*cm:  # 换列
                y = height - 8*cm
        
        # 填空题区域
        y -= 1.5*cm
        if y < 6*cm:
            y = height - 8*cm
        
        c.setFont(self.font_name, 12)
        c.drawString(2*cm, y, "二、填空题（请在横线上填写答案）")
        
        fill_count = exam_info.get('fill_count', 5)
        y -= 1*cm
        c.setFont(self.font_name, 10)
        
        for i in range(fill_count):
            c.drawString(2*cm, y, f"{i+1}. ________________________________")
            y -= 0.8*cm
        
        # 大题区域
        y -= 1.5*cm
        if y < 8*cm:
            c.showPage()
            y = height - 3*cm
        
        c.setFont(self.font_name, 12)
        c.drawString(2*cm, y, "三、解答题（请在下方空白处作答，写出必要步骤）")
        
        essay_count = exam_info.get('essay_count', 3)
        y -= 1*cm
        
        for i in range(essay_count):
            c.setFont(self.font_name, 10)
            # 题号和分值填写区
            c.drawString(2*cm, y, f"{i+1}.")
            # 分值框
            c.setStrokeColor(gray)
            c.rect(2.8*cm, y - 2*mm, 2*cm, 6*mm, fill=0)
            c.setFont(self.font_name, 8)
            c.drawString(3*cm, y, "分值")
            c.setFont(self.font_name, 10)
            c.setStrokeColor(black)
            
            y -= 0.6*cm
            
            # 答题框
            box_height = 4*cm
            c.setStrokeColor(gray)
            c.setLineWidth(0.5)
            c.rect(2*cm, y - box_height, width - 4*cm, box_height, fill=0)
            
            # 网格线 - 极浅色虚点
            c.setStrokeColorRGB(0.85, 0.85, 0.85)  # 极浅灰色
            c.setLineWidth(0.3)
            c.setDash(1, 3)  # 虚线：1点长，3点间隔
            
            # 水平虚线（每8mm一条）
            for grid_y in range(int(y - box_height), int(y), 8):
                c.line(2*cm, grid_y, width - 2*cm, grid_y)
            
            # 垂直虚线（每15mm一条）
            for grid_x in range(int(2*cm), int(width - 2*cm), 15):
                c.line(grid_x, y - box_height, grid_x, y)
            
            # 恢复默认样式
            c.setDash()
            c.setStrokeColor(black)
            c.setLineWidth(1)
            
            y -= box_height + 0.5*cm
            
            if y < 5*cm and i < essay_count - 1:
                c.showPage()
                y = height - 3*cm
        
        # 底部提示
        c.setFont(self.font_name, 8)
        c.setFillColor(gray)
        c.drawCentredString(width/2, 1.5*cm, 
                           "请认真检查，确认无误后再交卷 | 答题卡编号：________")
        c.setFillColor(black)
    
    def generate_template(self, output_path, template_type='standard'):
        """生成标准答题卡模板"""
        templates = {
            'standard': {
                'school': '________学校',
                'exam_name': '期中考试',
                'subject': '数学',
                'choice_count': 20,
                'fill_count': 5,
                'essay_count': 3,
                'student_count': 1
            },
            'math': {
                'school': '________学校',
                'exam_name': '数学考试',
                'subject': '数学',
                'choice_count': 12,
                'fill_count': 6,
                'essay_count': 4,
                'student_count': 1
            },
            'english': {
                'school': '________学校',
                'exam_name': '英语考试',
                'subject': '英语',
                'choice_count': 30,
                'fill_count': 10,
                'essay_count': 2,
                'student_count': 1
            }
        }
        
        info = templates.get(template_type, templates['standard'])
        return self.generate(output_path, info)


if __name__ == '__main__':
    # 测试生成
    generator = AnswerSheetGenerator()
    
    # 生成标准模板
    output = r'C:\Users\X380\WorkBuddy\Claw\grading-system\答题卡模板.pdf'
    generator.generate_template(output, 'math')
    print(f'答题卡模板已生成：{output}')