from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.plan import PlanRequest, PlanResponse
from app.security.deps import get_current_user
from app.services import gemini_service

router = APIRouter(prefix="/api/plan", tags=["plan"])

@router.post("/generate", response_model=PlanResponse)
async def generate_plan(
    request: PlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await gemini_service.generate_and_save(current_user, request, db)

@router.get("/mine", response_model=PlanResponse)
def get_mine(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return gemini_service.get_my_plan(current_user, db)

@router.delete("/mine", status_code=status.HTTP_204_NO_CONTENT)
def delete_mine(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gemini_service.delete_plan(current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
