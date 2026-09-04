from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.leaderboard import WeeklyLeaderboardResponse
from app.security.deps import require_admin
from app.services import leaderboard_service

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

@router.get("/weekly", response_model=WeeklyLeaderboardResponse)
def get_weekly(db: Session = Depends(get_db)):
    return leaderboard_service.get_current_week(db)

@router.post("/reset")
def reset_leaderboard(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    leaderboard_service.clear_leaderboard(db)
    return "تم تفريغ لوحة الشرف بنجاح حتى موعد التجديد الأسبوعي القادم"

@router.post("/refresh", response_model=WeeklyLeaderboardResponse)
def force_refresh(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    leaderboard_service.refresh_current_week(db)
    return leaderboard_service.get_current_week(db)
