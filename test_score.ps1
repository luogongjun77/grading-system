$env:Path = "C:\Program Files\Python312;C:\Program Files\Python312\Scripts;" + $env:Path
cd "C:\Users\X380\WorkBuddy\Claw\grading-system\backend"
python -c "
from answer_sheet_generator import AnswerSheetGenerator
gen = AnswerSheetGenerator()
output = r'C:\Users\X380\WorkBuddy\Claw\grading-system\data\答题卡_分数版.pdf'
gen.generate_template(output, 'math')
print('Generated')
"