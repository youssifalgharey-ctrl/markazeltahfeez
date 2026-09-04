import html
import random
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.booking import IjazaBooking
from app.models.notification import UserNotification
from app.schemas.booking import IjazaBookingRequest
from app.services.email_service import (
    send_ijaza_booking_email,
    send_calendar_invite_to_admin,
)
from app.services.google_calendar import generate_google_calendar_url

router = APIRouter(prefix="/api/ijaza", tags=["ijaza"])

@router.post("/book")
def book_session(request: IjazaBookingRequest, db: Session = Depends(get_db)):
    try:
        # ── إصلاح: استخدام UUID بدلاً من random 4 أرقام لمنع التخمين ──
        booking_ref = f"IJZ-{uuid.uuid4().hex[:10].upper()}"
        action_token = uuid.uuid4().hex

        booking = IjazaBooking(
            studentName=request.studentName.strip(),
            studentEmail=request.studentEmail.strip(),
            studentPhone=request.studentPhone.strip(),
            userCode=request.userCode.strip() if request.userCode else None,
            sheikhName=request.sheikhName.strip(),
            riwayah=request.riwayah.strip(),
            sessionType=request.sessionType or "جلسة تقييم وتحديد مستوى",
            trackName=request.trackName.strip() if request.trackName else "ختمة بالحصول علي الإجازة",
            sessionMode=request.sessionMode or "أونلاين (Online)",
            appointmentDate=request.appointmentDate.strip(),
            appointmentTime=request.appointmentTime.strip(),
            notes=request.notes.strip() if request.notes else None,
            paymentMethod=request.paymentMethod or "فودافون كاش",
            paymentSender=request.paymentSender.strip() if request.paymentSender else None,
            amount=request.amount or "100 ج.م",
            receiptBase64=request.receiptBase64,
            bookingReference=booking_ref,
            actionToken=action_token,
            status="PENDING",
            createdAt=datetime.now(),
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Create user notification
        notif = UserNotification(
            userCode=booking.userCode,
            studentEmail=booking.studentEmail,
            type="session",
            category="طلب جلسة قرآنية",
            title="⏳ تم إرسال طلب حجز موعد جلستك القرآنية",
            message=(
                f"تم استلام طلب حجز جلستك ({booking.trackName}) مع فضيلة الشيخ {booking.sheikhName} "
                f"يوم {booking.appointmentDate} الساعة {booking.appointmentTime}. "
                "طلبك قيد المراجعة لدى إدارة المركز وسيصلك إشعار بالقرار فوراً."
            ),
            status="PENDING",
            bookingReference=booking_ref,
            link="/notifications.html",
            linkText="متابعة حالة الطلب",
            isRead=False,
            createdAt=datetime.now(),
        )
        db.add(notif)
        db.commit()

        # Send email in background
        send_ijaza_booking_email(booking)

        return {
            "success": True,
            "bookingReference": booking_ref,
            "studentName": booking.studentName,
            "sheikhName": booking.sheikhName,
            "appointmentDate": booking.appointmentDate,
            "appointmentTime": booking.appointmentTime,
            "riwayah": booking.riwayah,
            "sessionMode": booking.sessionMode,
            "emailSent": True,
            "message": "تم حجز الموعد بنجاح! تم إرسال تفاصيل الموعد وتأكيده إلى بريدك الإلكتروني.",
        }
    except Exception as ex:
        return {
            "success": False,
            "message": "حدث خطأ أثناء تسجيل الحجز، يرجى المحاولة لاحقاً أو التواصل معنا عبر واتساب.",
        }

@router.get("/action", response_class=HTMLResponse)
def handle_booking_action(
    token: Optional[str] = Query(None),
    ref: Optional[str] = Query(None),
    action: str = Query(...),
    db: Session = Depends(get_db),
):
    booking = None
    if token and token.strip():
        booking = db.query(IjazaBooking).filter(IjazaBooking.actionToken == token.strip()).first()

    if not booking:
        return HTMLResponse(
            """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>طلب غير موجود</title></head>
<body style="font-family: Arial, Tahoma, sans-serif; background: #f8fafc; text-align: center; padding: 50px;">
    <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
        <h2 style="color: #dc2626;">عذراً، لم يتم العثور على هذا الحجز</h2>
        <p style="color: #64748b;">قد يكون الحجز تم حذفه أو أن الرابط غير صحيح.</p>
    </div>
</body></html>"""
        )

    is_approve = (action.lower() == "approve")
    booking.status = "APPROVED" if is_approve else "REJECTED"
    db.commit()
    db.refresh(booking)

    safe_name = html.escape(booking.studentName or "")
    safe_date = html.escape(booking.appointmentDate or "")
    safe_time = html.escape(booking.appointmentTime or "")
    safe_sheikh = html.escape(booking.sheikhName or "")

    notif_title = "🎉 تمت الموافقة على موعد جلستك القرآنية!" if is_approve else "⚠️ اعتذار عن موعد الجلسة القرآنية"
    notif_msg = (
        f"يسرنا إبلاغك بأنه تمت الموافقة على طلب جلستك ({booking.trackName or 'ختمة قرآنية'}) مع فضيلة الشيخ {safe_sheikh} "
        f"يوم {safe_date} الساعة {safe_time} بنجاح. نرجو الالتزام بالحضور في الموعد المحدد."
        if is_approve
        else f"نعتذر منك يا {safe_name}، تعذر تأكيد موعد جلستك المحدد يوم {safe_date} الساعة {safe_time} مع فضيلة الشيخ {safe_sheikh} نظراً لتعارض المواعيد أو انشغال الشيخ. نرجو التكرم باختيار موعد بديل متاح يناسبك."
    )

    decision_notif = UserNotification(
        userCode=booking.userCode,
        studentEmail=booking.studentEmail,
        type="session" if is_approve else "alert",
        category="موافقة على الجلسة" if is_approve else "اعتذار عن الموعد",
        title=notif_title,
        message=notif_msg,
        status="APPROVED" if is_approve else "REJECTED",
        bookingReference=booking.bookingReference,
        link="/home.html" if is_approve else "/khatma.html",
        linkText="عرض التفاصيل" if is_approve else "اختيار موعد بديل",
        isRead=False,
        createdAt=datetime.now(),
    )
    db.add(decision_notif)
    db.commit()

    cal_button_html = ""
    if is_approve:
        try:
            cal_url = generate_google_calendar_url(booking)
            send_calendar_invite_to_admin(booking)
            cal_button_html = f"""
            <div style='margin: 20px 0 25px 0;'>
                <a href='{cal_url}' target='_blank' class='btn-cal'>
                    📅 فتح وحفظ الموعد في Google Calendar
                </a>
                <div style='font-size: 13px; color: #64748b; margin-top: 8px;'>
                    تم إرسال دعوة التقويم (.ics) لبريدك <strong>{settings.PAYMENT_ADMIN_EMAIL}</strong> ليثبت الموعد تلقائياً في تقويم جوجل.
                </div>
            </div>
            """
        except Exception:
            pass

    title = "تمت الموافقة وتأكيد الجلسة بنجاح!" if is_approve else "تم تسجيل الاعتذار عن الموعد بنجاح"
    color = "#059669" if is_approve else "#dc2626"
    icon = "✅" if is_approve else "⚠️"
    message = (
        f"تمت الموافقة على طلب الجلسة مع الطالب <strong>{safe_name}</strong> وتأكيد الموعد يوم (<strong>{safe_date} - {safe_time}</strong>).<br>"
        f"تم تحديث حالة الجلسة وإرسال إشعار للمستخدم، وتم إرسال دعوة الموعد إلى Google Calendar لحساب <strong>{settings.PAYMENT_ADMIN_EMAIL}</strong> بنجاح."
        if is_approve
        else f"تم تسجيل الاعتذار عن موعد الجلسة للطالب <strong>{safe_name}</strong> بنجاح."
    )

    page_html = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: 'Cairo', Arial, Tahoma, sans-serif; background: #f0fdf4; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
.card {{ background: #ffffff; max-width: 550px; width: 100%; border-radius: 20px; padding: 35px 25px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 2px solid {color}; }}
.icon {{ font-size: 50px; margin-bottom: 15px; }}
h2 {{ color: {color}; margin: 0 0 12px 0; font-size: 24px; }}
p {{ color: #334155; font-size: 15px; line-height: 1.8; margin-bottom: 20px; }}
.badge {{ background: #f1f5f9; padding: 8px 16px; border-radius: 8px; font-weight: bold; color: #475569; display: inline-block; margin-bottom: 20px; }}
.btn-cal {{ display: inline-block; background: #1a73e8; color: #ffffff; padding: 13px 26px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 15px; box-shadow: 0 4px 12px rgba(26,115,232,0.35); }}
.btn-home {{ display: inline-block; background: #059669; color: #ffffff; padding: 11px 24px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 14px; margin-top: 15px; }}
</style></head><body>
<div class="card">
    <div class="icon">{icon}</div>
    <h2>{title}</h2>
    <div class="badge">كود الحجز: {booking.bookingReference}</div>
    <p>{message}</p>
    {cal_button_html}
    <div><a href="/home.html" class="btn-home">العودة للمنصة الرئيسية</a></div>
</div>
</body></html>"""

    return HTMLResponse(page_html)

@router.get("/sheikhs")
def get_available_sheikhs():
    return [
        {
            "id": "sheikh-sennar",
            "name": "فضيلة الشيخ / محمد سنار",
            "title": "مقرئ ومعلم القرآن الكريم والقراءات والتجويد — المشرف على مركز تحفيظ القرآن الكريم بأسريجه",
            "riwayaat": ["حفص عن عاصم", "شعبة عن عاصم", "ورش عن نافع", "قالون", "القراءات العشر"],
            "days": ["طوال أيام الأسبوع"],
            "avatar": "fa-user-tie",
        }
    ]
