# -*- coding: utf-8 -*-
"""
AI辅助评分模块
支持填空题和大题的智能化评分
"""
import re
import json

class AIGrading:
    """AI评分器"""
    
    def __init__(self):
        # 数学关键词库
        self.math_keywords = {
            '几何': ['平行', '垂直', '相似', '全等', '勾股定理', '三角函数', '圆', '角'],
            '代数': ['方程', '函数', '不等式', '因式分解', '配方', '求根公式'],
            '计算': ['化简', '计算', '求值', '解'],
            '证明': ['证明', '求证', '因为', '所以', '∵', '∴']
        }
        
        # 英语评分标准
        self.english_criteria = {
            'grammar': ['时态', '语态', '从句', '主谓一致', '词性'],
            'vocabulary': ['词汇', '短语', '搭配'],
            'coherence': ['连贯', '逻辑', '连接词']
        }
    
    def grade_fill_blank(self, student_answer, standard_answer, full_score):
        """
        填空题AI评分
        支持数值、表达式、文字答案的模糊匹配
        """
        if not student_answer or not standard_answer:
            return {'score': 0, 'similarity': 0, 'feedback': '未作答'}
        
        student_ans = str(student_answer).strip()
        standard_ans = str(standard_answer).strip()
        
        # 1. 精确匹配
        if student_ans == standard_ans:
            return {
                'score': full_score,
                'similarity': 1.0,
                'feedback': '完全正确',
                'method': 'exact_match'
            }
        
        # 2. 数值等价判断（数学）
        try:
            student_val = float(student_ans.replace(' ', ''))
            standard_val = float(standard_ans.replace(' ', ''))
            if abs(student_val - standard_val) < 0.01:
                return {
                    'score': full_score,
                    'similarity': 1.0,
                    'feedback': '数值正确',
                    'method': 'numeric_equivalent'
                }
        except:
            pass
        
        # 3. 表达式等价判断
        expr_sim = self._compare_expression(student_ans, standard_ans)
        if expr_sim > 0.9:
            return {
                'score': full_score * expr_sim,
                'similarity': expr_sim,
                'feedback': '表达式等价',
                'method': 'expression_equivalent'
            }
        
        # 4. 文本相似度
        text_sim = self._text_similarity(student_ans, standard_ans)
        
        # 5. 关键词匹配
        keyword_sim = self._keyword_match(student_ans, standard_ans)
        
        # 综合评分
        final_sim = max(text_sim, keyword_sim, expr_sim)
        
        if final_sim > 0.8:
            feedback = '答案基本正确，略有差异'
        elif final_sim > 0.6:
            feedback = '部分正确，需要完善'
        elif final_sim > 0.3:
            feedback = '答案不完整或有错误'
        else:
            feedback = '答案错误或未理解题意'
        
        return {
            'score': round(full_score * final_sim, 2),
            'similarity': round(final_sim, 2),
            'feedback': feedback,
            'method': 'ai_similarity',
            'details': {
                'text_similarity': round(text_sim, 2),
                'keyword_match': round(keyword_sim, 2),
                'expression_match': round(expr_sim, 2)
            }
        }
    
    def grade_essay(self, student_text, standard_answer, full_score, subject='math'):
        """
        大题AI辅助评分
        分析解题步骤、关键步骤、最终答案
        """
        if not student_text:
            return {
                'score': 0,
                'feedback': '未作答',
                'breakdown': {}
            }
        
        result = {
            'score': 0,
            'max_score': full_score,
            'feedback': '',
            'breakdown': {},
            'suggestions': []
        }
        
        if subject == 'math':
            result = self._grade_math_essay(student_text, standard_answer, full_score)
        elif subject == 'english':
            result = self._grade_english_essay(student_text, standard_answer, full_score)
        else:
            result = self._grade_generic_essay(student_text, standard_answer, full_score)
        
        return result
    
    def _grade_math_essay(self, student_text, standard_answer, full_score):
        """数学大题评分"""
        breakdown = {}
        total_score = 0
        suggestions = []
        
        # 1. 检查是否有解题步骤
        has_steps = len(student_text) > 20 and ('=' in student_text or '∵' in student_text or '因为' in student_text)
        if has_steps:
            breakdown['有步骤'] = full_score * 0.1
            total_score += full_score * 0.1
        else:
            suggestions.append('建议写出详细解题步骤')
        
        # 2. 检查关键公式/定理使用
        key_formulas_found = []
        for category, keywords in self.math_keywords.items():
            for keyword in keywords:
                if keyword in student_text:
                    key_formulas_found.append(keyword)
        
        if key_formulas_found:
            formula_score = min(full_score * 0.3, len(key_formulas_found) * 2)
            breakdown['关键公式/定理'] = formula_score
            total_score += formula_score
        else:
            suggestions.append('未使用明显的数学公式或定理')
        
        # 3. 检查计算过程
        calculations = re.findall(r'[=＝]([^=\n]+)', student_text)
        if len(calculations) >= 2:
            breakdown['计算过程'] = full_score * 0.3
            total_score += full_score * 0.3
        elif len(calculations) == 1:
            breakdown['计算过程'] = full_score * 0.15
            total_score += full_score * 0.15
            suggestions.append('计算步骤可以更加详细')
        else:
            suggestions.append('缺少计算过程')
        
        # 4. 最终答案检查
        answer_sim = self._extract_and_compare_answer(student_text, standard_answer)
        if answer_sim > 0.9:
            breakdown['最终答案'] = full_score * 0.3
            total_score += full_score * 0.3
        elif answer_sim > 0.6:
            breakdown['最终答案'] = full_score * 0.15
            total_score += full_score * 0.15
            suggestions.append('最终答案有偏差，请检查计算')
        else:
            suggestions.append('最终答案错误或缺失')
        
        # 生成反馈
        if total_score >= full_score * 0.9:
            feedback = '解答完整，思路清晰，答案正确'
        elif total_score >= full_score * 0.7:
            feedback = '解答基本正确，部分步骤可完善'
        elif total_score >= full_score * 0.5:
            feedback = '解答部分正确，需要补充关键步骤'
        else:
            feedback = '解答有较大问题，建议重新审题'
        
        return {
            'score': round(min(total_score, full_score), 2),
            'max_score': full_score,
            'feedback': feedback,
            'breakdown': breakdown,
            'suggestions': suggestions,
            'key_points_found': key_formulas_found[:5]  # 最多显示5个
        }
    
    def _grade_english_essay(self, student_text, standard_answer, full_score):
        """英语作文/大题评分"""
        breakdown = {}
        suggestions = []
        
        # 1. 字数检查
        word_count = len(student_text.split())
        if word_count > 100:
            breakdown['字数充足'] = full_score * 0.1
        elif word_count > 50:
            breakdown['字数'] = full_score * 0.05
            suggestions.append('字数偏少，可适当扩充')
        else:
            suggestions.append('字数不足，需要补充内容')
        
        # 2. 句子结构多样性
        sentences = re.split(r'[.!?。！？]', student_text)
        complex_patterns = ['which', 'that', 'who', 'when', 'where', 'because', 'although', 'if']
        complex_count = sum(1 for s in sentences for p in complex_patterns if p in s.lower())
        
        if complex_count >= 3:
            breakdown['句式多样'] = full_score * 0.2
        elif complex_count >= 1:
            breakdown['句式'] = full_score * 0.1
            suggestions.append('可尝试使用更多复合句')
        
        # 3. 词汇丰富度
        unique_words = set(student_text.lower().split())
        vocab_score = min(full_score * 0.2, len(unique_words) * 0.5)
        breakdown['词汇'] = vocab_score
        
        total_score = sum(breakdown.values())
        
        return {
            'score': round(min(total_score, full_score), 2),
            'max_score': full_score,
            'feedback': '英语评分参考（需人工复核）',
            'breakdown': breakdown,
            'suggestions': suggestions,
            'word_count': word_count
        }
    
    def _grade_generic_essay(self, student_text, standard_answer, full_score):
        """通用大题评分"""
        text_sim = self._text_similarity(student_text, standard_answer)
        
        return {
            'score': round(full_score * text_sim, 2),
            'max_score': full_score,
            'feedback': '基于文本相似度的参考评分',
            'similarity': round(text_sim, 2),
            'note': '建议人工复核'
        }
    
    def _text_similarity(self, s1, s2):
        """计算两段文本的相似度（简化版编辑距离）"""
        if not s1 or not s2:
            return 0
        
        # 预处理
        s1 = re.sub(r'\s+', '', str(s1).lower())
        s2 = re.sub(r'\s+', '', str(s2).lower())
        
        if s1 == s2:
            return 1.0
        
        # 最长公共子序列近似
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0
        
        # 使用集合计算字符重叠度
        set1, set2 = set(s1), set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0
    
    def _keyword_match(self, student, standard):
        """关键词匹配度"""
        student_words = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', str(student)))
        standard_words = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', str(standard)))
        
        if not standard_words:
            return 0
        
        match = len(student_words & standard_words)
        return match / len(standard_words)
    
    def _compare_expression(self, expr1, expr2):
        """比较两个数学表达式是否等价（简化版）"""
        # 标准化表达式
        def normalize(expr):
            expr = str(expr).replace(' ', '').replace('×', '*').replace('÷', '/')
            expr = expr.replace('（', '(').replace('）', ')')
            return expr
        
        e1, e2 = normalize(expr1), normalize(expr2)
        
        if e1 == e2:
            return 1.0
        
        # 尝试数值计算比较
        try:
            # 替换数学符号
            def eval_expr(expr):
                expr = expr.replace('^', '**')
                expr = expr.replace('√', 'math.sqrt')
                # 安全计算（简化版）
                return eval(expr, {'__builtins__': {}}, {'math': __import__('math')})
            
            v1, v2 = eval_expr(e1), eval_expr(e2)
            if abs(v1 - v2) < 0.001:
                return 1.0
        except:
            pass
        
        return self._text_similarity(e1, e2)
    
    def _extract_and_compare_answer(self, text, standard):
        """提取并比较最终答案"""
        # 尝试提取数值答案
        numbers = re.findall(r'[=＝]\s*([+-]?\d+\.?\d*)', text)
        if numbers:
            student_answer = numbers[-1]  # 取最后一个等号后的值
            return self._text_similarity(student_answer, str(standard))
        
        # 尝试提取中文答案
        chinese_pattern = r'(?:答案|结果为|得)[:：]?\s*([^，。\n]+)'
        matches = re.findall(chinese_pattern, text)
        if matches:
            return self._text_similarity(matches[-1], str(standard))
        
        return 0.5  # 无法确定时给中等分数


# 全局AI评分器实例
ai_grader = AIGrading()

if __name__ == '__main__':
    # 测试
    result = ai_grader.grade_fill_blank('x=3', 'x=3', 5)
    print('填空题评分:', result)
    
    math_solution = '''
    解：∵ ABCD是矩形
    ∴ ∠A = 90°
    由勾股定理：BD² = AB² + AD² = 100 + 36 = 136
    ∴ BD = √136 = 2√34
    '''
    result2 = ai_grader.grade_essay(math_solution, '2√34', 10, 'math')
    print('大题评分:', result2)