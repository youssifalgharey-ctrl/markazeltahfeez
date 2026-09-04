import html
import uuid
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.subscription import CourseSubscription
from app.schemas.payment import PaymentNotificationRequest
from app.security.deps import get_current_user_optional, require_admin
from app.services.email_service import send_payment_notification_email

router = APIRouter(prefix="/api/payment", tags=["payment"])

def determine_duration_days(course_key: str) -> int:
    ck = (course_key or "").lower()
    if ck == "course-foundation":
        return 60
    elif ck in ("course-tajweed", "pkg-mandatory", "pkg-flexible"):
        return 90
    elif ck in ("course-ijaza", "course-qiraat"):
        return 180
    elif ck == "course-month-1":
        return 30
    elif ck == "course-motun":
        return 60
    return 90

def render_result_html(success: bool, title: str, description: str, sub: Optional[CourseSubscription] = None) -> str:
    primary_color = "#059669" if success else "#dc2626"
    icon = "fa-circle-check" if success else "fa-triangle-exclamation"
    icon_bg = "#dcfce7" if success else "#fee2e2"

    safe_title = html.escape(title or "")
    safe_desc = html.escape(description or "")

    details_html = ""
    if sub:
        safe_student = html.escape(sub.studentName or "")
        safe_phone = html.escape(sub.studentPhone or "")
        safe_course = html.escape(sub.courseTitle or "-")
        safe_amount = html.escape(sub.amount or "-")
        expires_str = sub.expiresAt.strftime("%Y-%m-%d") if sub.expiresAt else ""

        details_html = f"""
        <div class='details-box'>
            <div class='details-row'><strong>اسم الطالب:</strong> <span>{safe_student}</span></div>
            <div class='details-row'><strong>رقم الهاتف:</strong> <span>{safe_phone}</span></div>
            <div class='details-row'><strong>الدورة:</strong> <span>{safe_course}</span></div>
            <div class='details-row'><strong>المبلغ:</strong> <span style='font-weight:bold; color: #059669;'>{safe_amount}</span></div>
            {"<div class='details-row'><strong>صالح حتى تاريخ:</strong> <span style='font-weight:bold; color: #059669;'>" + expires_str + "</span></div>" if expires_str else ""}
            <div class='details-row'><strong>حالة الاشتراك:</strong> <span style='color: #059669; font-weight: bold;'>مفعل بنجاح ✔</span></div>
        </div>
        """

    return f"""<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>{safe_title}</title>
<link href='https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap' rel='stylesheet'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<style>
body {{ font-family: 'Cairo', sans-serif; background: #f8fafc; color: #1e293b; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
.card {{ background: #ffffff; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; max-width: 540px; width: 100%; padding: 36px 28px; text-align: center; }}
.icon-circle {{ width: 76px; height: 76px; border-radius: 50%; background: {icon_bg}; color: {primary_color}; display: flex; align-items: center; justify-content: center; font-size: 36px; margin: 0 auto 20px; }}
h2 {{ color: {primary_color}; font-size: 22px; margin: 0 0 10px; font-weight: 800; }}
.desc {{ color: #64748b; font-size: 14.5px; line-height: 1.7; margin-bottom: 24px; }}
.details-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; text-align: right; margin-bottom: 24px; font-size: 14px; }}
.details-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #edf2f7; }}
.details-row:last-child {{ border-bottom: none; }}
.btn {{ display: inline-block; background: {primary_color}; color: #fff; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-weight: 700; font-size: 14px; transition: 0.2s; }}
.btn:hover {{ opacity: 0.9; }}
</style></head><body>
<div class='card'>
    <div class='icon-circle'><i class='fa-solid {icon}'></i></div>
    <h2>{safe_title}</h2>
    <p class='desc'>{safe_desc}</p>
    {details_html}
    <a href='/tajweed.html' class='btn'><i class='fa-solid fa-book-quran'></i> الانتقال لقسم الدورات والتجويد</a>
</div>
</body></html>"""

@router.post("/notify")
def notify_payment(request: PaymentNotificationRequest, db: Session = Depends(get_db)):
    # ── إصلاح: حد أقصى لحجم صورة الإيصال ──
    _MAX_RECEIPT_B64 = 5 * 1024 * 1024 * 4 // 3  # ~5 MB
    if request.receiptBase64 and len(request.receiptBase64) > _MAX_RECEIPT_B64:
        raise HTTPException(status_code=413, detail="حجم صورة الإيصال كبير جداً، الحد الأقصى 5 ميجابايت")

    token = uuid.uuid4().hex
    duration_days = determine_duration_days(request.courseKey)

    sub = CourseSubscription(
        studentName=request.fullName.strip(),
        studentPhone=request.phone.strip(),
        userCode=request.userCode.strip() if request.userCode else None,
        studentEmail=request.email.strip() if request.email else None,
        courseKey=request.courseKey or "pkg-mandatory",
        courseTitle=request.courseTitle or "دورة تجويد",
        courseSubtitle=request.courseSubtitle,
        amount=request.amount,
        paymentMethod=request.paymentMethod,
        senderDetails=request.senderDetails,
        receiptImage=request.receiptBase64,
        activationToken=token,
        status="PENDING",
        durationDays=duration_days,
        createdAt=datetime.now(),
        warningSent=False,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Send email notification
    send_payment_notification_email(sub, request.receiptBase64)

    return {
        "success": True,
        "subscriptionId": sub.id,
        "status": sub.status,
        "message": "تم استلام وتأكيد بيانات عملية الدفع وإرسال الإشعار للإدارة بنجاح.",
    }

@router.get("/activate", response_class=HTMLResponse)
def activate_subscription(token: str = Query(...), db: Session = Depends(get_db)):
    sub = db.query(CourseSubscription).filter(CourseSubscription.activationToken == token).first()
    if not sub:
        return HTMLResponse(
            status_code=400,
            content=render_result_html(
                False,
                "رابط تفعيل غير صالح أو منتهي الصلاحية",
                "لم يتم العثور على أي اشتراك مرتبط بهذا الرابط.",
            ),
        )

    # ── إصلاح: التحقق من صلاحية رابط التفعيل (أقصى 7 أيام من تاريخ الإنشاء) ──
    TOKEN_EXPIRY_DAYS = 7
    now = datetime.now()
    if sub.createdAt and (now - sub.createdAt).days >= TOKEN_EXPIRY_DAYS and sub.status != "ACTIVATED":
        return HTMLResponse(
            status_code=400,
            content=render_result_html(
                False,
                "رابط التفعيل منتهي الصلاحية",
                f"انتهت صلاحية رابط التفعيل بعد {TOKEN_EXPIRY_DAYS} أيام من تاريخ الطلب. يرجى مراجعة إدارة المركز.",
            ),
        )

    if sub.status == "ACTIVATED" and sub.expiresAt and sub.expiresAt > now:
        return HTMLResponse(
            content=render_result_html(
                True,
                "الاشتراك مفعل بالفعل مسبقاً!",
                f"تم تفعيل هذا الاشتراك في وقت سابق حتى تاريخ: {sub.expiresAt.strftime('%Y-%m-%d %I:%M %p')}",
                sub,
            )
        )

    duration = sub.durationDays or 90
    sub.status = "ACTIVATED"
    sub.activatedAt = now
    sub.expiresAt = now + timedelta(days=duration)
    sub.warningSent = False
    db.commit()
    db.refresh(sub)

    return HTMLResponse(
        content=render_result_html(
            True,
            "تم تفعيل اشتراك الطالب بنجاح! 🎉",
            f"أصبح حساب الطالب مفعلاً حتى تاريخ ({sub.expiresAt.strftime('%Y-%m-%d')}) ومتاحاً له الوصول لكافة محاضرات وتدريبات الدورة على المنصة.",
            sub,
        )
    )

@router.get("/my-subscriptions")
def get_my_subscriptions(
    phone: Optional[str] = Query(None),
    userCode: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    target_phone = phone
    target_code = userCode
    target_email = email

    is_admin = current_user is not None and current_user.role == "ADMIN"
    if not is_admin:
        admin_check = None
        if target_code:
            admin_check = db.query(User).filter(User.userCode == target_code.strip(), User.role == "ADMIN").first()
        if not admin_check and target_email:
            admin_check = db.query(User).filter(User.email == target_email.strip(), User.role == "ADMIN").first()
        if not admin_check and target_phone:
            admin_check = db.query(User).filter(User.phone == target_phone.strip(), User.role == "ADMIN").first()
        if admin_check:
            is_admin = True

    # إذا كان الحساب مسؤول المنصة (Admin)، تكون كافة الكورسات مفتوحة له بالكامل
    if is_admin:
        all_courses = [
            "course-foundation",
            "course-tajweed",
            "course-ijaza",
            "course-qiraat",
            "pkg-mandatory",
            "pkg-flexible",
            "course-month-1",
            "course-motun",
            "free-intro",
        ]
        return {
            "activeCourseKeys": all_courses,
            "subscriptions": [
                {
                    "id": 0,
                    "courseKey": c,
                    "courseTitle": "وصول كامل بحساب الإدارة",
                    "amount": "0 ج.م",
                    "status": "ACTIVATED",
                    "activatedAt": datetime.now().isoformat(),
                    "expiresAt": None,
                }
                for c in all_courses
            ],
            "isAdmin": True,
        }

    if current_user and not is_admin:
        target_phone = current_user.phone
        target_code = current_user.userCode
        target_email = current_user.email
    elif current_user:
        if not target_phone:
            target_phone = current_user.phone
        if not target_code:
            target_code = current_user.userCode
        if not target_email:
            target_email = current_user.email

    now = datetime.now()

    # Query active subscriptions
    query = db.query(CourseSubscription).filter(
        CourseSubscription.status == "ACTIVATED",
        (CourseSubscription.expiresAt.is_(None) | (CourseSubscription.expiresAt > now)),
    )

    conditions = []
    if target_phone and target_phone.strip():
        conditions.append(CourseSubscription.studentPhone == target_phone.strip())
    if target_code and target_code.strip():
        conditions.append(CourseSubscription.userCode == target_code.strip())
    if target_email and target_email.strip():
        conditions.append(CourseSubscription.studentEmail == target_email.strip())

    if conditions:
        from sqlalchemy import or_
        query = query.filter(or_(*conditions))
    else:
        # No identifiers provided, return empty
        return {"activeCourseKeys": [], "subscriptions": []}

    active_subs = query.all()

    active_keys = list({s.courseKey for s in active_subs if s.courseKey})
    sub_list = [
        {
            "id": s.id,
            "courseKey": s.courseKey,
            "courseTitle": s.courseTitle,
            "amount": s.amount,
            "status": s.status,
            "activatedAt": s.activatedAt.isoformat() if s.activatedAt else "",
            "expiresAt": s.expiresAt.isoformat() if s.expiresAt else "",
        }
        for s in active_subs
    ]

    return {"activeCourseKeys": active_keys, "subscriptions": sub_list}

@router.get("/check-subscription")
def check_subscription(
    courseKey: str = Query(...),
    phone: Optional[str] = Query(None),
    userCode: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    target_phone = phone
    target_code = userCode
    target_email = email

    is_admin = current_user is not None and current_user.role == "ADMIN"
    if not is_admin:
        admin_check = None
        if target_code:
            admin_check = db.query(User).filter(User.userCode == target_code.strip(), User.role == "ADMIN").first()
        if not admin_check and target_email:
            admin_check = db.query(User).filter(User.email == target_email.strip(), User.role == "ADMIN").first()
        if not admin_check and target_phone:
            admin_check = db.query(User).filter(User.phone == target_phone.strip(), User.role == "ADMIN").first()
        if admin_check:
            is_admin = True

    # إذا كان مسؤول المنصة، الكورس مفتوح له فوراً
    if is_admin:
        return {"isSubscribed": True, "courseKey": courseKey, "isAdmin": True}

    if current_user and not is_admin:
        target_phone = current_user.phone
        target_code = current_user.userCode
        target_email = current_user.email
    elif current_user:
        if not target_phone:
            target_phone = current_user.phone
        if not target_code:
            target_code = current_user.userCode
        if not target_email:
            target_email = current_user.email

    now = datetime.now()
    query = db.query(CourseSubscription).filter(
        CourseSubscription.status == "ACTIVATED",
        CourseSubscription.courseKey == courseKey,
        (CourseSubscription.expiresAt.is_(None) | (CourseSubscription.expiresAt > now)),
    )

    conditions = []
    if target_phone and target_phone.strip():
        conditions.append(CourseSubscription.studentPhone == target_phone.strip())
    if target_code and target_code.strip():
        conditions.append(CourseSubscription.userCode == target_code.strip())
    if target_email and target_email.strip():
        conditions.append(CourseSubscription.studentEmail == target_email.strip())

    if conditions:
        from sqlalchemy import or_
        query = query.filter(or_(*conditions))
        is_sub = (query.first() is not None)
    else:
        is_sub = False

    return {"isSubscribed": is_sub, "courseKey": courseKey}

@router.get("/all-subscriptions")
def get_all_subscriptions(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(CourseSubscription).order_by(CourseSubscription.createdAt.desc()).all()

@router.get("/admin/stats")
def get_admin_stats(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    subs = db.query(CourseSubscription).all()
    now = datetime.now()

    total = len(subs)
    activated = sum(1 for s in subs if s.status == "ACTIVATED" and (not s.expiresAt or s.expiresAt > now))
    pending = sum(1 for s in subs if s.status == "PENDING")
    expired = sum(1 for s in subs if s.status == "EXPIRED" or (s.expiresAt and s.expiresAt <= now))

    total_revenue = 0.0
    for s in subs:
        if s.status == "ACTIVATED" and s.amount:
            try:
                num = re.sub(r"[^0-9.]", "", s.amount)
                if num:
                    total_revenue += float(num)
            except Exception:
                pass

    return {
        "total": total,
        "activated": activated,
        "pending": pending,
        "expired": expired,
        "totalRevenue": total_revenue,
    }

@router.post("/admin/activate/{id}")
def manual_activate(id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    sub = db.query(CourseSubscription).filter(CourseSubscription.id == id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    duration = sub.durationDays or 90
    now = datetime.now()
    sub.status = "ACTIVATED"
    sub.activatedAt = now
    sub.expiresAt = now + timedelta(days=duration)
    sub.warningSent = False
    db.commit()
    db.refresh(sub)

    return {
        "success": True,
        "message": f"تم تفعيل اشتراك الطالب بنجاح حتى تاريخ: {sub.expiresAt}",
        "subscription": sub,
    }

@router.post("/admin/deactivate/{id}")
def manual_deactivate(id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    sub = db.query(CourseSubscription).filter(CourseSubscription.id == id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.status = "PENDING"
    sub.activatedAt = None
    sub.expiresAt = None
    db.commit()
    db.refresh(sub)

    return {
        "success": True,
        "message": "تم تعليق الاشتراك وإعادته لحالة قيد المراجعة",
        "subscription": sub,
    }

@router.delete("/admin/delete/{id}")
def delete_subscription(id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    sub = db.query(CourseSubscription).filter(CourseSubscription.id == id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    db.delete(sub)
    db.commit()
    return {"success": True, "message": "تم حذف سجل الاشتراك بنجاح"}
