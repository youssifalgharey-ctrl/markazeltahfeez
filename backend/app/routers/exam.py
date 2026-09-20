from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.schemas.exam import (
    ExamResultRequest,
    ExamResultItemResponse,
    ExamResultLookupResponse,
)
from app.models.user import User
from app.security.deps import require_admin, get_current_user_optional
from app.services import exam_service

router = APIRouter(prefix="/api/results", tags=["results"])

@router.get("/{code}", response_model=ExamResultLookupResponse)
def get_by_code(
    code: str,
    x_sync_secret: Optional[str] = Header(None, alias="X-Sync-Secret"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # Allow bypass if valid sync webhook secret is provided
    is_sync = bool(x_sync_secret and x_sync_secret == settings.SYNC_WEBHOOK_SECRET)

    if not is_sync:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="يجب تسجيل الدخول أولاً للاستعلام عن النتيجة.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Admins (role ADMIN, or specific admin accounts 0001 and 0002) can look up any student's result
        is_admin = (
            current_user.role == "ADMIN"
            or current_user.userCode in ("0001", "0002")
            or (current_user.email and current_user.email.lower() in (
                "markazeltafeez@gmail.com",
                "youssifalgharey@gmail.com",
                "admin@asseriga-quran.com"
            ))
        )
        if not is_admin:
            user_code = (current_user.userCode or "").strip()
            user_variants = set(exam_service.get_code_variants(user_code)) if user_code else set()
            req_variants = set(exam_service.get_code_variants(code.strip()))

            if not user_variants or not user_variants.intersection(req_variants):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="غير مصرح لك بالاطلاع على نتيجة طالب آخر، يمكنك الاستعلام عن نتيجتك فقط."
                )

    try:
        return exam_service.lookup(code, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("", response_model=ExamResultItemResponse)
def create_result(
    request: ExamResultRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return exam_service.create_or_update(request, db)

@router.post("/sync", response_model=ExamResultItemResponse)
def sync_from_sheet(
    request: ExamResultRequest,
    x_sync_secret: Optional[str] = Header(None, alias="X-Sync-Secret"),
    db: Session = Depends(get_db),
):
    if not x_sync_secret or x_sync_secret != settings.SYNC_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "رمز التحقق السري لمزامنة النتائج غير صحيح أو مفقود"}
        )
    return exam_service.create_or_update(request, db)

@router.post("/batch")
def sync_batch(
    requests: List[ExamResultRequest],
    x_sync_secret: Optional[str] = Header(None, alias="X-Sync-Secret"),
    db: Session = Depends(get_db),
):
    if not x_sync_secret or x_sync_secret != settings.SYNC_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "رمز التحقق السري لمزامنة النتائج غير صحيح أو مفقود"}
        )
    return exam_service.batch_create_or_update(requests, db)

@router.delete("/{code}")
def delete_result(
    code: str,
    exam_name: Optional[str] = None,
    x_sync_secret: Optional[str] = Header(None, alias="X-Sync-Secret"),
    db: Session = Depends(get_db),
):
    if not x_sync_secret or x_sync_secret != settings.SYNC_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "رمز التحقق السري لمزامنة النتائج غير صحيح أو مفقود"}
        )
    return exam_service.delete_result(code, exam_name, db)

