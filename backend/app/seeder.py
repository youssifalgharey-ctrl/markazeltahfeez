import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import User
from app.security.passwords import hash_password

logger = logging.getLogger(__name__)

def seed_admin_accounts(db: Session):
    admins = [
        {
            "fullName": "مدير المنصة الأول (الإدارة العامة)",
            "userCode": "0001",
            "email": "markazeltafeez@gmail.com",
            "phone": "01000000001",
            "password": "admin1234",
            "currentSurah": "إدارة المنصة",
            "title": "الإدارة العامة للمركز",
        },
        {
            "fullName": "مدير المنصة الثاني (المشرف العام)",
            "userCode": "0002",
            "email": "admin@asseriga-quran.com",
            "phone": "01000000002",
            "password": "admin1234",
            "currentSurah": "المشرف العام",
            "title": "المشرف العام",
        },
    ]

    for adm in admins:
        try:
            user = (
                db.query(User).filter(User.userCode == adm["userCode"]).first()
                or db.query(User).filter(User.email == adm["email"]).first()
            )
            if not user:
                user = User(
                    fullName=adm["fullName"],
                    userCode=adm["userCode"],
                    email=adm["email"],
                    phone=adm["phone"],
                    age=35,
                    password=hash_password(adm["password"]),
                    role="ADMIN",
                    token_version=1,
                    currentSurah=adm["currentSurah"],
                    createdAt=datetime.now(),
                )
                db.add(user)
                db.commit()
                logger.info("👑 [ADMIN CREATED] تم إنشاء حساب المسؤول بنجاح: %s | كود: %s | إيميل: %s", adm["title"], adm["userCode"], adm["email"])
            else:
                user.role = "ADMIN"
                user.userCode = adm["userCode"]
                # لا نغير كلمة المرور إذا كانت موجودة بالفعل، حتى لا تُلغى كلمة المرور التي غيرها المسؤول بنفسه
                if not user.password:
                    user.password = hash_password(adm["password"])
                if user.token_version is None:
                    user.token_version = 1
                db.commit()
                logger.info("👑 [ADMIN VERIFIED] تم التحقق من حساب المسؤول وتثبيت الرتبة: %s (%s)", adm["title"], adm["userCode"])
        except Exception as ex:
            logger.error("خطأ أثناء تهيئة حساب المسؤول %s: %s", adm["title"], ex)
            db.rollback()
