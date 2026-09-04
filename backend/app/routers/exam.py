from typing import Optional
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
from app.security.deps import require_admin
from app.services import exam_service

router = APIRouter(prefix="/api/results", tags=["results"])

@router.get("/{code}", response_model=ExamResultLookupResponse)
def get_by_code(code: str, db: Session = Depends(get_db)):
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
