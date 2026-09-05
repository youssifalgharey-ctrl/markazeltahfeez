import random
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.notification import UserNotification
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    AvatarUpdateRequest,
    ChangePasswordRequest,
)
from app.security.passwords import hash_password, verify_password
from app.security.jwt_handler import create_access_token, decode_access_token
from app.security.deps import get_current_user
from app.services.google_sheets import sync_user_to_sheet
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

def normalize_arabic_digits(text: str) -> str:
    if not text:
        return ""
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, ch in enumerate(arabic_digits):
        text = text.replace(ch, str(i))
    return text.strip()

def generate_unique_code(db: Session) -> str:
    while True:
        code = str(random.randint(1000, 9999))
        if not db.query(User).filter(User.userCode == code).first():
            return code

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    phone = request.phone.strip()
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="رقم الهاتف مسجل بالفعل!")

    email = request.email.strip() if request.email and request.email.strip() else None
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل بالفعل!")

    if request.inviteCode and request.inviteCode.strip():
        assigned_code = request.inviteCode.strip()
        if db.query(User).filter(User.userCode == assigned_code).first():
            raise HTTPException(status_code=400, detail="هذا الكود مستخدم بالفعل من قبل شخص آخر!")
        reg_type = "كود مسبق (يدوي)"
    else:
        assigned_code = generate_unique_code(db)
        reg_type = "توليد تلقائي"

    is_admin = (
        email is not None
        and settings.PAYMENT_ADMIN_EMAIL
        and email.lower() == settings.PAYMENT_ADMIN_EMAIL.lower()
    )

    user = User(
        fullName=request.fullName.strip(),
        phone=phone,
        age=request.age,
        email=email,
        password=hash_password(request.password),
        userCode=assigned_code,
        inviteCode=request.inviteCode.strip() if request.inviteCode else None,
        role="ADMIN" if is_admin else "USER",
        token_version=1,
        createdAt=datetime.now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Sync to Google Sheets
    sync_user_to_sheet(user, reg_type)

    # Welcome notification
    welcome_notif = UserNotification(
        userCode=user.userCode,
        studentEmail=user.email,
        type="system",
        category="ترحيب بالمنصة",
        title="أهلاً ومرحباً بك في منصة القرآن الكريم! 🎉",
        message=(
            f"نشكرك جزيل الشكر يا {user.fullName} على تسجيلك وانضمامك إلى منصة مركز تحفيظ القرآن الكريم بأسريجه. "
            "نسأل الله العظيم أن يبارك في همتك، وأن يجعل القرآن ربيع قلبك ونور صدرك، ويسرنا مرافقتك في رحلتك المباركة لتعلم وحفظ وتلاوة كتاب الله."
        ),
        status="INFO",
        link="/courses.html",
        linkText="ابدأ رحلتك واستكشف البرامج",
        isRead=False,
        createdAt=datetime.now(),
    )
    db.add(welcome_notif)
    db.commit()

    return AuthResponse(
        fullName=user.fullName,
        phone=user.phone,
        email=user.email,
        userCode=user.userCode,
        message=f"الكود الخاص بك هو: {user.userCode}",
    )

@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    raw_ident = request.email.strip() if request.email else ""
    clean_ident = normalize_arabic_digits(raw_ident)

    if not raw_ident:
        raise HTTPException(status_code=400, detail="بيانات الدخول غير صحيحة!")

    from sqlalchemy import or_
    filters = []
    if clean_ident:
        filters.append(User.userCode == clean_ident)
        filters.append(User.phone == clean_ident)
    if raw_ident:
        filters.append(User.email == raw_ident)

    user = db.query(User).filter(or_(*filters)).first()

    if not user:
        raise HTTPException(status_code=400, detail="بيانات الدخول غير صحيحة!")

    is_admin = (user.role == "ADMIN")
    password_matches = verify_password(request.password.strip(), user.password, is_admin=is_admin)

    if not password_matches:
        raise HTTPException(status_code=400, detail="بيانات الدخول غير صحيحة!")

    # If it was an admin fallback password, rehash with standard admin1234
    if is_admin and request.password.strip().lower() in ("admin1234", "admin@asseriga2026!", "!admin@asseriga2026", "admin@markaz2026!", "!admin@markaz2026"):
        user.password = hash_password("admin1234")
        db.commit()

    # ── فحص الجلسة النشطة: منع فتح الحساب على أكثر من جهاز في نفس الوقت ──
    # مدة صلاحية الجلسة بدون نشاط (120 ثانية = دقيقتان)
    SESSION_INACTIVITY_TIMEOUT = 120
    if user.active_session_id and user.last_active_at:
        seconds_since_last_active = (datetime.now() - user.last_active_at).total_seconds()
        if seconds_since_last_active < SESSION_INACTIVITY_TIMEOUT:
            raise HTTPException(
                status_code=400,
                detail="هذا الحساب مفتوح حالياً على جهاز آخر. يجب تسجيل الخروج من الجهاز الآخر أولاً لتتمكن من الدخول."
            )

    new_session_id = uuid.uuid4().hex
    user.active_session_id = new_session_id
    user.last_active_at = datetime.now()
    user.token_version = (user.token_version or 1) + 1
    db.commit()
    db.refresh(user)

    lookup_key = user.email or user.phone or user.userCode
    token = create_access_token(lookup_key, user.token_version, session_id=new_session_id)

    return AuthResponse(
        token=token,
        fullName=user.fullName,
        phone=user.phone,
        email=user.email,
        userCode=user.userCode,
        role=user.role,
        profileImage=user.profileImage,
    )

@router.post("/logout")
def logout_endpoint(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """تحرير الجلسة النشطة فوراً حتى يتمكن أي جهاز آخر من تسجيل الدخول"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        if payload:
            username = payload.get("sub")
            if username:
                user = (
                    db.query(User).filter(User.email == username).first()
                    or db.query(User).filter(User.phone == username).first()
                    or db.query(User).filter(User.userCode == username).first()
                )
                if user:
                    user.active_session_id = None
                    user.last_active_at = None
                    user.token_version = (user.token_version or 1) + 1
                    db.commit()
    return {"success": True, "message": "تم تسجيل الخروج بنجاح وتحرير الحساب"}

@router.post("/heartbeat")
def heartbeat_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """إرسال نبضات النشاط من المتصفح للحفاظ على حجز الجلسة طالما التبويب مفتوح"""
    current_user.last_active_at = datetime.now()
    try:
        db.commit()
    except Exception:
        db.rollback()
    return {"status": "alive"}

@router.post("/forgot-password")
def forgot_password(body: Dict[str, str], db: Session = Depends(get_db)):
    email = body.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="يرجى إدخال البريد الإلكتروني")

    # ── إصلاح User Enumeration: دائماً اعرض نفس الرسالة بغض النظر عن وجود الإيميل ──
    # هذا يمنع المهاجم من معرفة أي إيميل مسجل في المنصة
    GENERIC_RESET_MSG = "إذا كان هذا البريد الإلكتروني مسجلاً لدينا، ستصلك رسالة تحتوي على كلمة المرور الجديدة. يرجى فحص صندوق الوارد والبريد الجانبي (Spam)."

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # لا نكشف أن الإيميل غير موجود — نعيد نفس الرسالة
        return {"success": True, "message": GENERIC_RESET_MSG}

    temp_password = f"Qr{random.randint(100000, 999999)}"
    user.password = hash_password(temp_password)
    user.token_version = (user.token_version or 1) + 1
    db.commit()

    send_password_reset_email(user.email, user.fullName, temp_password)

    return {"success": True, "message": GENERIC_RESET_MSG}

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return f"You are authenticated as: {current_user.email or current_user.phone or current_user.userCode}"

@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return ProfileResponse(
        fullName=current_user.fullName,
        phone=current_user.phone,
        age=current_user.age,
        email=current_user.email,
        userCode=current_user.userCode,
        address=current_user.address,
        currentSurah=current_user.currentSurah,
        profileImage=current_user.profileImage,
        role=current_user.role,
    )

@router.get("/public-avatar")
def get_public_avatar(
    userCode: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    user = None
    if userCode and userCode.strip():
        user = db.query(User).filter(User.userCode == userCode.strip()).first()
    if not user and phone and phone.strip():
        user = db.query(User).filter(User.phone == phone.strip()).first()
    if not user and email and email.strip():
        user = db.query(User).filter(User.email == email.strip()).first()

    avatar = user.profileImage if user else ""
    return {"profileImage": avatar or ""}

@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_phone = request.phone.strip()
    if new_phone != current_user.phone:
        if db.query(User).filter(User.phone == new_phone).first():
            raise HTTPException(status_code=400, detail="رقم الهاتف مسجل بالفعل!")

    new_email = request.email.strip() if request.email and request.email.strip() else None
    if new_email and new_email != current_user.email:
        if db.query(User).filter(User.email == new_email).first():
            raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل بالفعل!")

    # ── إصلاح: إبطال التوكن فقط لو تغييرت بيانات التحقق فعلاً (لو الإيميل أو الهاتف تغيّرا إلى قيمة جديدة) ──
    # مقارنة آمنة: (None == None) = True, ("إيميل" == "إيميل") = True, (None == "إيميل") = False
    old_email = (current_user.email or "").strip().lower()
    cur_email = (new_email or "").strip().lower()
    email_changed = bool(new_email) and cur_email != old_email

    old_phone = (current_user.phone or "").strip()
    phone_changed = new_phone.strip() != old_phone

    if email_changed or phone_changed:
        current_user.token_version = (current_user.token_version or 1) + 1

    current_user.fullName = request.fullName.strip()
    current_user.phone = new_phone
    current_user.age = request.age
    current_user.email = new_email
    current_user.address = request.address.strip() if request.address else None
    current_user.currentSurah = request.currentSurah.strip() if request.currentSurah else None

    db.commit()
    db.refresh(current_user)

    # ── إصلاح UX: لو تغيّرت بيانات التحقق (إيميل/هاتف)، أرجع توكن جديد للمستخدم ──
    new_token: Optional[str] = None
    if email_changed or phone_changed:
        lookup_key = current_user.email or current_user.phone or current_user.userCode
        new_token = create_access_token(lookup_key, current_user.token_version)

    return ProfileResponse(
        fullName=current_user.fullName,
        phone=current_user.phone,
        age=current_user.age,
        email=current_user.email,
        userCode=current_user.userCode,
        address=current_user.address,
        currentSurah=current_user.currentSurah,
        profileImage=current_user.profileImage,
        role=current_user.role,
        token=new_token,
    )

# الحد الأقصى لحجم صورة الملف الشخصي: 2 ميجابايت بترميز Base64
_MAX_AVATAR_B64_CHARS = 2 * 1024 * 1024 * 4 // 3  # ~2.7M حرف

@router.put("/profile/avatar", response_model=ProfileResponse)
def update_avatar(
    request: AvatarUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── إصلاح: التحقق من حجم الصورة (دون تقييد نوع MIME عشان تدعم جميع متصفحات/مكتبات صور بشكل مختلف) ──
    if not request.image:
        raise HTTPException(status_code=400, detail="الصورة مطلوبة")
    if len(request.image) > _MAX_AVATAR_B64_CHARS:
        raise HTTPException(status_code=413, detail="حجم الصورة كبير جداً، الحد الأقصى 2 ميجابايت")
    # قبول أي صورة Data URL أو base64 عادي (Canvas toDataURL بيطلع JPEG تلقائياً)
    if not (request.image.startswith("data:image/") or request.image.startswith("/9j/") or request.image.startswith("iVBOR")):
        raise HTTPException(status_code=400, detail="صيغة الصورة غير صحيحة")

    current_user.profileImage = request.image
    db.commit()
    db.refresh(current_user)
    return ProfileResponse(
        fullName=current_user.fullName,
        phone=current_user.phone,
        age=current_user.age,
        email=current_user.email,
        userCode=current_user.userCode,
        address=current_user.address,
        currentSurah=current_user.currentSurah,
        profileImage=current_user.profileImage,
        role=current_user.role,
    )

@router.delete("/profile/avatar", response_model=ProfileResponse)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.profileImage = None
    db.commit()
    db.refresh(current_user)
    return ProfileResponse(
        fullName=current_user.fullName,
        phone=current_user.phone,
        age=current_user.age,
        email=current_user.email,
        userCode=current_user.userCode,
        address=current_user.address,
        currentSurah=current_user.currentSurah,
        profileImage=current_user.profileImage,
        role=current_user.role,
    )

@router.put("/profile/password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.oldPassword, current_user.password, is_admin=(current_user.role == "ADMIN")):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة!")

    if request.newPassword != request.confirmPassword:
        raise HTTPException(status_code=400, detail="كلمة المرور الجديدة وتأكيدها غير متطابقين!")

    if verify_password(request.newPassword, current_user.password, is_admin=False):
        raise HTTPException(status_code=400, detail="كلمة المرور الجديدة يجب أن تختلف عن الحالية!")

    current_user.password = hash_password(request.newPassword)
    current_user.token_version = (current_user.token_version or 1) + 1
    db.commit()

    # ── إصلاح UX: إرجاع توكن جديد حتى يفضل المستخدم مسجّل دخول بدون انقطاع ──
    lookup_key = current_user.email or current_user.phone or current_user.userCode
    new_token = create_access_token(lookup_key, current_user.token_version)

    return {
        "message": "تم تغيير كلمة المرور بنجاح",
        "token": new_token,
    }
