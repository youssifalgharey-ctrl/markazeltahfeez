import asyncio
import logging
import threading
import httpx
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

async def _post_sheet(payload: dict):
    if not settings.GOOGLE_SHEETS_WEBHOOK_URL or "ضع_هنا" in settings.GOOGLE_SHEETS_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(settings.GOOGLE_SHEETS_WEBHOOK_URL, json=payload)
            logger.info("Synced user to Google Sheet, status: %s", resp.status_code)
    except Exception as e:
        logger.error("Failed to sync user to Google Sheets: %s", e)

def _send_sync_thread(payload: dict):
    try:
        asyncio.run(_post_sheet(payload))
    except Exception as e:
        logger.error("Background sync error: %s", e)

def sync_user_to_sheet(user: User, registration_type: str = "توليد تلقائي"):
    payload = {
        "id": user.userCode or "",
        "fullName": user.fullName or "",
        "phone": user.phone or "",
        "age": str(user.age) if user.age is not None else "",
        "email": user.email or "",
        "userCode": user.id if user.id is not None else "",
        "registrationType": registration_type or "توليد تلقائي",
        "createdAt": user.createdAt.isoformat() if user.createdAt else "",
    }
    # إرسال البيانات في خيط منفصل تماماً (Non-blocking) لضمان ظهور الكود للمستخدم فوراً بدون أي تأخير
    threading.Thread(target=_send_sync_thread, args=(payload,), daemon=True).start()

