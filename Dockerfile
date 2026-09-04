# =======================================================
# بيئة تشغيل منصة تحفيظ القرآن الكريم (Python 3.12 - FastAPI)
# =======================================================
FROM python:3.12-slim

WORKDIR /app

# منع إنشاء ملفات pyc وتفعيل إخراج فوري للسجلات
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8081

# تثبيت الاعتماديات
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# نسخ ملفات المشروع والواجهة الأمامية
COPY backend ./backend
COPY frontend ./frontend
COPY data ./data

WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8081}"]
