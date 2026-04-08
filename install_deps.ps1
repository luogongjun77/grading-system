$env:Path = "C:\Program Files\Python312;C:\Program Files\Python312\Scripts;" + $env:Path
cd "C:\Users\X380\WorkBuddy\Claw\grading-system\backend"
pip install flask flask-cors pillow pytesseract pandas openpyxl numpy -q
Write-Host "Dependencies installed"