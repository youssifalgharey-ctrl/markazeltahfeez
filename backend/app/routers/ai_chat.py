import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security.deps import get_current_user_optional
from app.schemas.ai_chat import AIChatRequest, AIChatResponse, SuggestionResponse
from app.services import ai_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-chat", tags=["AI Chat Assistant"])

@router.post("/send", response_model=AIChatResponse)
async def send_chat_message(
    request: AIChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """إرسال رسالة إلى المساعد الذكي والحصول على الرد والمقترحات."""
    user_name = current_user.fullName if current_user else None
    return await ai_chat_service.call_gemini_chat(request, user_name=user_name)

@router.get("/suggestions", response_model=SuggestionResponse)
async def get_initial_suggestions(
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """الحصول على الأسئلة المقترحة الافتتاحية ورسالة الترحيب."""
    name_str = f" يا {current_user.fullName}" if current_user and current_user.fullName else ""
    welcome = (
        f"السلام عليكم ورحمة الله وبركاته{name_str} 🌸\n"
        "أهلاً بك في منصة مركز تحفيظ القرآن الكريم بأسريجه! أنا مرشدك الذكي، كيف يمكنني مساعدتك اليوم؟"
    )
    return SuggestionResponse(
        suggestions=ai_chat_service.DEFAULT_SUGGESTIONS,
        welcomeMessage=welcome
    )
