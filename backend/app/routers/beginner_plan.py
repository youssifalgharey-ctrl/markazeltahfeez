from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.plan import (
    BeginnerPlanRequest,
    BeginnerPlanResponse,
    BeginnerPlanCompleteRequest,
)
from app.security.deps import get_current_user
from app.services import beginner_plan_service

router = APIRouter(prefix="/api/beginner-plan", tags=["beginner-plan"])

@router.post("/generate", response_model=BeginnerPlanResponse)
async def generate_plan(
    request: BeginnerPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await beginner_plan_service.generate_and_save(current_user, request, db)

@router.get("/mine", response_model=BeginnerPlanResponse)
def get_mine(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return beginner_plan_service.get_my_plan(current_user, db)

@router.post("/complete", response_model=BeginnerPlanResponse)
def complete_step(
    request: BeginnerPlanCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return beginner_plan_service.mark_complete(current_user, request.order, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/next-stage", response_model=BeginnerPlanResponse)
def next_stage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return beginner_plan_service.advance_to_next_stage(current_user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
