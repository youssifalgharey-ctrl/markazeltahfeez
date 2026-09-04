from typing import List
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.progress import TajweedProgressResponse, TajweedToggleRequest
from app.security.deps import get_current_user
from app.services import tajweed_service

router = APIRouter(prefix="/api/tajweed-progress", tags=["tajweed-progress"])

@router.get("", response_model=TajweedProgressResponse)
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tajweed_service.get_progress(current_user, db)

@router.post("/toggle", response_model=TajweedProgressResponse)
def toggle_topic(
    request: TajweedToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tajweed_service.toggle_topic(current_user, request.topicKey, db)

@router.post("/sync", response_model=TajweedProgressResponse)
def sync_progress(
    completed_topics: List[str] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tajweed_service.sync_progress(current_user, completed_topics, db)
