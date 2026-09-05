from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.user import User
from app.models.notification import UserNotification
from app.security.deps import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

def is_owner(notif: UserNotification, user: User) -> bool:
    if user.role == "ADMIN":
        return True
    if not notif.userCode and not notif.studentEmail:
        return False
    match_code = bool(user.userCode and notif.userCode and user.userCode.lower() == notif.userCode.lower())
    match_email = bool(user.email and notif.studentEmail and user.email.lower() == notif.studentEmail.lower())
    return match_code or match_email

@router.get("/unread-count")
def get_unread_count(
    userCode: Optional[str] = None,
    email: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    clean_code = current_user.userCode if current_user else (userCode.strip() if userCode else None)
    clean_email = current_user.email if current_user else (email.strip() if email else None)

    if not clean_code and not clean_email:
        return {"unread": 0}

    count = db.query(UserNotification).filter(
        or_(
            UserNotification.userCode == clean_code,
            UserNotification.studentEmail == clean_email,
            (UserNotification.userCode.is_(None) & UserNotification.studentEmail.is_(None))
        ),
        UserNotification.isRead == False
    ).count()

    return {"unread": count}

@router.get("/my")
def get_my_notifications(
    userCode: Optional[str] = None,
    email: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    clean_code = current_user.userCode if current_user else (userCode.strip() if userCode else None)
    clean_email = current_user.email if current_user else (email.strip() if email else None)

    if not clean_code and not clean_email:
        return []

    query = db.query(UserNotification).filter(
        or_(
            UserNotification.userCode == clean_code,
            UserNotification.studentEmail == clean_email,
            (UserNotification.userCode.is_(None) & UserNotification.studentEmail.is_(None))
        )
    ).order_by(UserNotification.createdAt.desc())

    notifications = query.all()

    if not notifications:
        welcome_notif = UserNotification(
            userCode=clean_code,
            studentEmail=clean_email,
            type="system",
            category="ترحيب وشكر",
            title="أهلاً ومرحباً بك في منصة القرآن الكريم! 🎉",
            message=(
                "نشكرك على تسجيلك وانضمامك إلى منصة مركز تحفيظ القرآن الكريم بأسريجه. "
                "نسأل الله العظيم أن يبارك في همتك، وأن يجعل القرآن ربيع قلبك ونور صدرك، "
                "ويسرنا مرافقتك في رحلتك المباركة لتعلم وحفظ وتلاوة كتاب الله."
            ),
            status="INFO",
            link="/courses.html",
            linkText="ابدأ رحلتك واستكشف البرامج",
            isRead=False,
            createdAt=datetime.now(),
        )
        db.add(welcome_notif)
        db.commit()
        db.refresh(welcome_notif)
        notifications = [welcome_notif]

    return [
        {
            "id": n.id,
            "userCode": n.userCode,
            "studentEmail": n.studentEmail,
            "type": n.type,
            "category": n.category,
            "title": n.title,
            "message": n.message,
            "status": n.status,
            "bookingReference": n.bookingReference,
            "link": n.link,
            "linkText": n.linkText,
            "isRead": n.isRead,
            "createdAt": n.createdAt.isoformat() if n.createdAt else "",
        }
        for n in notifications
    ]

@router.post("/{id}/read")
def mark_as_read(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(UserNotification).filter(UserNotification.id == id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not is_owner(notif, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح لك بتعديل هذا الإشعار")

    notif.isRead = True
    db.commit()
    return {"success": True, "message": "تم تحديد الإشعار كمقروء"}

@router.post("/mark-all-read")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(UserNotification).filter(
        or_(
            UserNotification.userCode == current_user.userCode,
            UserNotification.studentEmail == current_user.email,
            (UserNotification.userCode.is_(None) & UserNotification.studentEmail.is_(None))
        )
    )
    for notif in query.all():
        if not notif.isRead:
            notif.isRead = True
    db.commit()
    return {"success": True, "message": "تم تحديد جميع الإشعارات كمقروءة"}

@router.delete("/{id}")
def delete_notification(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(UserNotification).filter(UserNotification.id == id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not is_owner(notif, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح لك بحذف هذا الإشعار")

    db.delete(notif)
    db.commit()
    return {"success": True, "message": "تم حذف الإشعار بنجاح"}
