from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.memorization import (
    MemorizationEntryRequest,
    MemorizationEntryResponse,
    MemorizationStatsResponse,
)
from app.security.deps import get_current_user
from app.services import memorization_service

router = APIRouter(prefix="/api/progress", tags=["progress"])

@router.post("/log", response_model=MemorizationEntryResponse)
def log_today(
    request: MemorizationEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return memorization_service.log_today(current_user, request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/log", response_model=MemorizationEntryResponse)
def update_today(
    request: MemorizationEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return memorization_service.update_today(current_user, request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=List[MemorizationEntryResponse])
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return memorization_service.get_history(current_user, db)

@router.get("/stats", response_model=MemorizationStatsResponse)
def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return memorization_service.get_stats(current_user, db)
