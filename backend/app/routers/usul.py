from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.progress import UsulProgressResponse, UsulToggleRequest, UsulSyncRequest
from app.security.deps import get_current_user
from app.services import usul_service

router = APIRouter(prefix="/api/usul-progress", tags=["usul-progress"])

@router.get("", response_model=UsulProgressResponse)
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return usul_service.get_progress(current_user, db)

@router.post("/toggle", response_model=UsulProgressResponse)
def toggle_lesson(
    request: UsulToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return usul_service.toggle_lesson(current_user, request.science, request.lessonId, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sync", response_model=UsulProgressResponse)
def sync_progress(
    request: UsulSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return usul_service.sync_progress(current_user, request, db)
