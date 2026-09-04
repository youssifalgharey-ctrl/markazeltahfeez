from typing import List, Optional
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of sender: 'user' or 'assistant' or 'system'")
    content: str = Field(..., description="Message text")

class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The user's input message")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Conversation history")

class AIChatResponse(BaseModel):
    reply: str
    suggestions: Optional[List[str]] = Field(default_factory=list)
    source: str = Field(default="gemini", description="'gemini' or 'knowledge_base'")

class SuggestionResponse(BaseModel):
    suggestions: List[str]
    welcomeMessage: str
