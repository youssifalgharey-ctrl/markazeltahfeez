import os
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── إعدادات Rate Limiting ────────────────────────────────────────────
MAX_REQUESTS_PER_MINUTE = 10
TIME_WINDOW_SECONDS = 60.0

# عناوين IP الموثوقة لـ Reverse Proxy (مثل Nginx داخل الشبكة)
# أضف عنوان proxy الخاص بك هنا عند النشر
TRUSTED_PROXIES: set[str] = {
    "127.0.0.1",
    "::1",
}

# المسارات الخاضعة للـ Rate Limiting
RATE_LIMITED_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/profile/password",   # تغيير كلمة المرور
    "/api/payment/notify",          # إرسال إيصالات الدفع
    "/api/ijaza/book",              # حجز الجلسات
}

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_counts: dict[str, tuple[float, int]] = {}  # ip -> (window_start, count)

    def get_client_ip(self, request: Request) -> str:
        """
        استخراج IP العميل الحقيقي بأمان.
        - لا يثق في X-Forwarded-For إلا إذا جاء الطلب من proxy موثوق.
        - يمنع انتحال IP عبر تزوير هذا الهيدر.
        """
        client = request.client
        direct_ip = client.host if client else "unknown"

        if direct_ip in TRUSTED_PROXIES:
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                # أخذ أول IP في القائمة (IP العميل الحقيقي)
                real_ip = forwarded.split(",")[0].strip()
                if real_ip:
                    return real_ip

        # إذا لم يكن من proxy موثوق، استخدم الـ IP المباشر
        return direct_ip

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.lower()
        if path in RATE_LIMITED_PATHS:
            client_ip = self.get_client_ip(request)
            now = time.time()

            # تنظيف دوري للذاكرة
            if len(self.request_counts) > 5000:
                self.request_counts = {
                    ip: (w_start, cnt)
                    for ip, (w_start, cnt) in self.request_counts.items()
                    if now - w_start <= TIME_WINDOW_SECONDS
                }

            record = self.request_counts.get(client_ip)
            if not record or (now - record[0]) > TIME_WINDOW_SECONDS:
                self.request_counts[client_ip] = (now, 1)
            else:
                window_start, count = record
                count += 1
                self.request_counts[client_ip] = (window_start, count)
                if count > MAX_REQUESTS_PER_MINUTE:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "status": 429,
                            "error": "Too Many Requests",
                            "message": "تم تجاوز عدد المحاولات المسموح بها، يرجى الانتظار دقيقة ثم المحاولة مجدداً.",
                        },
                    )

        return await call_next(request)

