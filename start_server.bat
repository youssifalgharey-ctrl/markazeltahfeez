@echo off
chcp 65001 > nul
echo =========================================================
echo    تشغيل سيرفر منصة القرآن الكريم (Python FastAPI Backend)
echo =========================================================
echo.

cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    echo [خطأ] البيئة الافتراضية غير موجودة! جاري إنشاؤها وتثبيت المكتبات...
    "C:\Users\youss\AppData\Local\Programs\Python\Python312\python.exe" -m venv backend\venv
    call backend\venv\Scripts\pip.exe install -r backend\requirements.txt
)

echo [1/2] تفعيل السيرفر على المنفذ 8081...
echo [2/2] الرابط المباشر: http://localhost:8081
echo.
backend\venv\Scripts\python.exe backend\run.py

pause
