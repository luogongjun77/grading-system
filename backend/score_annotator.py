# -*- coding: utf-8 -*-
"""
答题卡分数标注模块
在答题卡图片上标注机阅分数
"""
from PIL import Image, ImageDraw, ImageFont
import os

class ScoreAnnotator:
    """分数标注器"""
    
    def __init__(self):
        # 尝试加载字体
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        
        font_paths = [
            'C:\\Windows\\Fonts\\simhei.ttf',
            'C:\\Windows\\Fonts\\msyh.ttc',
            'C:\\Windows\\Fonts\\simsun.ttc'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.font_large = ImageFont.truetype(font_path, 36)
                    self.font_medium = ImageFont.truetype(font_path, 24)
                    self.font_small = ImageFont.truetype(font_path, 18)
                    break
                except:
                    continue
        
        if not self.font_large:
            # 使用默认字体
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def annotate(self, image_path, score_data, output_path=None):
        """
        在答题卡图片上标注分数
        
        score_data = {
            'total_score': 85,
            'choice_score': 28,
            'fill_score': 15,
            'essay_score': 42,
            'details': {
                'choices': {'1': {'score': 3, 'is_correct': True}, ...},
                'fills': {'1': {'score': 5, 'similarity': 1.0}, ...},
                'essays': {'1': {'score': 14, 'max_score': 15}, ...}
            }
        }
        """
        # 打开图片
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # 创建半透明遮罩层（顶部区域）
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 绘制分数信息区域（右上角）
        info_x = width - 250
        info_y = 20
        info_width = 230
        info_height = 120
        
        # 背景框
        overlay_draw.rectangle(
            [info_x, info_y, info_x + info_width, info_y + info_height],
            fill=(255, 255, 255, 230),
            outline=(102, 126, 234, 255),
            width=2
        )
        
        # 合并图层
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # 绘制分数信息
        text_x = info_x + 10
        text_y = info_y + 10
        
        # 总分（大号字体，红色）
        total = score_data.get('total_score', 0)
        draw.text((text_x, text_y), f"总分: {total}", fill=(220, 53, 69), font=self.font_large)
        text_y += 45
        
        # 各题型分数
        choice = score_data.get('choice_score', 0)
        fill = score_data.get('fill_score', 0)
        essay = score_data.get('essay_score', 0)
        
        draw.text((text_x, text_y), f"选择: {choice}  填空: {fill}  大题: {essay}", 
                 fill=(0, 0, 0), font=self.font_small)
        
        # 在答题卡各区域标注小题分数
        self._annotate_question_scores(draw, score_data, width, height)
        
        # 保存或返回
        if output_path:
            img.save(output_path)
            return output_path
        else:
            # 生成带分数标记的文件名
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_graded{ext}"
            img.save(output_path)
            return output_path
    
    def _annotate_question_scores(self, draw, score_data, width, height):
        """在答题卡各题目位置标注分数"""
        details = score_data.get('details', {})
        
        # 标注选择题分数（假设在答题卡上方区域）
        choices = details.get('choices', {})
        if choices:
            # 选择题分数标注区域
            start_y = 200
            col_width = 80
            row_height = 40
            
            for idx, (q_num, info) in enumerate(choices.items()):
                col = idx % 5
                row = idx // 5
                x = 50 + col * col_width
                y = start_y + row * row_height
                
                score = info.get('score', 0)
                is_correct = info.get('is_correct', False)
                
                # 正确绿色，错误红色
                color = (40, 167, 69) if is_correct else (220, 53, 69)
                draw.text((x, y), f"{q_num}:{score}", fill=color, font=self.font_small)
        
        # 标注填空题分数
        fills = details.get('fills', {})
        if fills:
            start_y = 400
            for idx, (q_num, info) in enumerate(fills.items()):
                y = start_y + idx * 35
                score = round(info.get('score', 0), 1)
                similarity = info.get('similarity', 0)
                
                # 根据相似度显示颜色
                if similarity >= 0.8:
                    color = (40, 167, 69)
                elif similarity >= 0.5:
                    color = (255, 193, 7)
                else:
                    color = (220, 53, 69)
                
                draw.text((50, y), f"填空{q_num}: {score}分", fill=color, font=self.font_small)
        
        # 标注大题分数
        essays = details.get('essays', {})
        if essays:
            start_y = 600
            for idx, (q_num, info) in enumerate(essays.items()):
                y = start_y + idx * 50
                score = round(info.get('score', 0), 1)
                max_score = info.get('max_score', 0)
                
                # 计算得分率显示颜色
                ratio = score / max_score if max_score > 0 else 0
                if ratio >= 0.8:
                    color = (40, 167, 69)
                elif ratio >= 0.6:
                    color = (255, 193, 7)
                else:
                    color = (220, 53, 69)
                
                draw.text((50, y), f"第{q_num}题: {score}/{max_score}分", fill=color, font=self.font_medium)
    
    def generate_score_report_image(self, score_data, student_info, output_path):
        """
        生成成绩报告图片（单独的图片，不是标注在原答题卡上）
        """
        # 创建新图片
        width, height = 800, 1000
        img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((width//2 - 150, 30), "成绩报告单", fill=(0, 0, 0), font=self.font_large)
        
        # 学生信息
        y = 100
        draw.text((50, y), f"姓名: {student_info.get('name', '')}", fill=(0, 0, 0), font=self.font_medium)
        y += 40
        draw.text((50, y), f"学号: {student_info.get('student_no', '')}", fill=(0, 0, 0), font=self.font_medium)
        y += 40
        draw.text((50, y), f"考试: {student_info.get('exam_name', '')}", fill=(0, 0, 0), font=self.font_medium)
        
        # 分隔线
        y += 60
        draw.line([(50, y), (width-50, y)], fill=(200, 200, 200), width=2)
        
        # 总分（大字体居中）
        y += 40
        total = score_data.get('total_score', 0)
        draw.text((width//2 - 80, y), f"总分: {total}", fill=(102, 126, 234), font=self.font_large)
        
        # 各题型得分
        y += 80
        draw.text((50, y), "各题型得分:", fill=(0, 0, 0), font=self.font_medium)
        y += 40
        
        choice = score_data.get('choice_score', 0)
        fill = score_data.get('fill_score', 0)
        essay = score_data.get('essay_score', 0)
        
        draw.text((100, y), f"选择题: {choice}分", fill=(0, 0, 0), font=self.font_small)
        y += 30
        draw.text((100, y), f"填空题: {fill}分", fill=(0, 0, 0), font=self.font_small)
        y += 30
        draw.text((100, y), f"解答题: {essay}分", fill=(0, 0, 0), font=self.font_small)
        
        # 保存
        img.save(output_path)
        return output_path


if __name__ == '__main__':
    # 测试
    annotator = ScoreAnnotator()
    
    test_data = {
        'total_score': 85,
        'choice_score': 28,
        'fill_score': 15,
        'essay_score': 42,
        'details': {
            'choices': {
                '1': {'score': 3, 'is_correct': True},
                '2': {'score': 3, 'is_correct': True},
                '3': {'score': 0, 'is_correct': False}
            },
            'fills': {
                '1': {'score': 5, 'similarity': 1.0},
                '2': {'score': 5, 'similarity': 0.9}
            },
            'essays': {
                '1': {'score': 14, 'max_score': 15}
            }
        }
    }
    
    # 生成报告图片
    output = r'C:\Users\X380\WorkBuddy\Claw\grading-system\data\test_score_report.png'
    annotator.generate_score_report_image(test_data, {'name': '张三', 'student_no': '2024001', 'exam_name': '期中考试'}, output)
    print(f'Report generated: {output}')