import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.subscription import CourseSubscription
from app.models.booking import IjazaBooking
from app.models.notification import UserNotification
from app.security.deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

def parse_amount(amount_str: Optional[str]) -> int:
    if not amount_str:
        return 0
    clean = re.sub(r"[^0-9]", "", amount_str)
    return int(clean) if clean else 0

@router.get("/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    all_subs = db.query(CourseSubscription).all()
    all_bookings = db.query(IjazaBooking).all()

    active_subs = sum(1 for s in all_subs if s.status == "ACTIVATED")
    pending_subs = sum(1 for s in all_subs if s.status in ("PENDING", "PENDING_REVIEW"))

    confirmed_bookings = sum(1 for b in all_bookings if b.status in ("APPROVED", "CONFIRMED"))
    pending_bookings = sum(1 for b in all_bookings if b.status == "PENDING")

    subscription_revenue = sum(parse_amount(s.amount) for s in all_subs if s.status == "ACTIVATED")
    booking_revenue = sum(parse_amount(b.amount) for b in all_bookings if b.status in ("APPROVED", "COMPLETED"))

    return {
        "totalUsers": total_users,
        "totalSubscriptions": len(all_subs),
        "activeSubscriptions": active_subs,
        "pendingSubscriptions": pending_subs,
        "totalBookings": len(all_bookings),
        "confirmedBookings": confirmed_bookings,
        "pendingBookings": pending_bookings,
        "subscriptionRevenue": subscription_revenue,
        "bookingRevenue": booking_revenue,
        "totalRevenue": subscription_revenue + booking_revenue,
    }

@router.get("/users")
def get_all_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    q = search.strip().lower() if search and search.strip() else None

    result = []
    for u in users:
        if role and role.upper() != "ALL" and u.role != role.upper():
            continue

        if q:
            match_name = bool(u.fullName and q in u.fullName.lower())
            match_phone = bool(u.phone and q in u.phone)
            match_code = bool(u.userCode and q in u.userCode.lower())
            match_email = bool(u.email and q in u.email.lower())
            if not (match_name or match_phone or match_code or match_email):
                continue

        result.append({
            "id": u.id,
            "fullName": u.fullName,
            "phone": u.phone,
            "email": u.email,
            "userCode": u.userCode,
            "age": u.age,
            "role": u.role,
            "currentSurah": u.currentSurah,
            "profileImage": u.profileImage,
            "createdAt": u.createdAt.isoformat() if u.createdAt else None,
        })

    result.sort(key=lambda x: x["createdAt"] or "", reverse=True)
    return result

@router.post("/users/{id}/toggle-role")
def toggle_user_role(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.userCode in ("0001", "0002") or (user.email and user.email.lower() in ("markazeltafeez@gmail.com", "youssifalgharey@gmail.com", "admin@asseriga-quran.com")):
        return {"success": False, "message": "لا يمكن تغيير رتبة حسابات الإدارة والمشرفين الرئيسية."}

    new_role = "USER" if user.role == "ADMIN" else "ADMIN"
    user.role = new_role
    user.token_version = (user.token_version or 1) + 1
    db.commit()

    return {
        "success": True,
        "newRole": new_role,
        "message": f"تم تغيير رتبة المستخدم بنجاح إلى: {new_role}",
    }

@router.get("/bookings")
def get_all_bookings(db: Session = Depends(get_db)):
    bookings = db.query(IjazaBooking).order_by(IjazaBooking.createdAt.desc()).all()
    return bookings

@router.post("/bookings/{id}/status")
def update_booking_status(
    id: int,
    body: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
):
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="الحالة مطلوبة")

    booking = db.query(IjazaBooking).filter(IjazaBooking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    status_clean = new_status.upper().strip()
    booking.status = status_clean
    db.commit()

    is_approved = (status_clean == "APPROVED")
    is_rejected = (status_clean == "REJECTED")

    title = (
        "🎉 تمت الموافقة على طلب جلستك القرآنية!"
        if is_approved
        else ("⚠️ اعتذار عن موعد الجلسة القرآنية" if is_rejected else "تحديث في حالة حجز جلستك")
    )
    msg = (
        f"يسرنا إبلاغك بأنه تمت مراجعة إيصالك وتأكيد موعد جلستك ({booking.trackName}) مع فضيلة الشيخ {booking.sheikhName} "
        f"يوم {booking.appointmentDate} الساعة {booking.appointmentTime}."
        if is_approved
        else f"نعتذر منك يا {booking.studentName}، تعذر تأكيد طلب حجز الجلسة المحدد. يرجى مراجعة إدارة المركز أو اختيار موعد بديل."
    )

    notif = UserNotification(
        userCode=booking.userCode,
        studentEmail=booking.studentEmail,
        type="session" if is_approved else "alert",
        category="جلسة قرآنية",
        title=title,
        message=msg,
        status=status_clean,
        bookingReference=booking.bookingReference,
        link="/notifications.html",
        linkText="عرض الإشعارات",
        isRead=False,
        createdAt=datetime.now(),
    )
    db.add(notif)
    db.commit()

    return {
        "success": True,
        "status": status_clean,
        "message": "تم تحديث حالة الحجز بنجاح وإشعار الطالب.",
    }

@router.delete("/bookings/{id}")
def delete_booking(id: int, db: Session = Depends(get_db)):
    booking = db.query(IjazaBooking).filter(IjazaBooking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.delete(booking)
    db.commit()
    return {"success": True, "message": "تم حذف الحجز بنجاح"}

@router.delete("/users/{id}")
def delete_user(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    if user.role == "ADMIN" or user.userCode in ("0001", "0002") or (user.email and user.email.lower() in ("markazeltafeez@gmail.com", "youssifalgharey@gmail.com", "admin@asseriga-quran.com")):
        raise HTTPException(status_code=400, detail="محظور: لا يمكن حذف حسابات الإدارة والمشرفين (Admin) من السيستم.")

    user_code = user.userCode
    user_email = user.email

    try:
        from app.models.subscription import CourseSubscription
        from app.models.booking import IjazaBooking
        from app.models.notification import UserNotification
        from app.models.quiz import QuizScore
        from sqlalchemy import or_

        if user_code or user_email:
            conds_sub = []
            conds_book = []
            conds_notif = []
            conds_quiz = []
            if user_code:
                conds_sub.append(CourseSubscription.userCode == user_code)
                conds_book.append(IjazaBooking.userCode == user_code)
                conds_notif.append(UserNotification.userCode == user_code)
                conds_quiz.append(QuizScore.user_code == user_code)
            if user_email:
                conds_sub.append(CourseSubscription.studentEmail == user_email)
                conds_book.append(IjazaBooking.studentEmail == user_email)
                conds_notif.append(UserNotification.studentEmail == user_email)
                conds_quiz.append(QuizScore.student_email == user_email)

            if conds_sub:
                db.query(CourseSubscription).filter(or_(*conds_sub)).delete(synchronize_session=False)
            if conds_book:
                db.query(IjazaBooking).filter(or_(*conds_book)).delete(synchronize_session=False)
            if conds_notif:
                db.query(UserNotification).filter(or_(*conds_notif)).delete(synchronize_session=False)
            if conds_quiz:
                db.query(QuizScore).filter(or_(*conds_quiz)).delete(synchronize_session=False)

        db.delete(user)
        db.commit()
        return {"success": True, "message": "تم حذف المستخدم وكافة بياناته بنجاح"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء حذف المستخدم: {str(e)}")

