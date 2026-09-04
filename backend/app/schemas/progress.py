from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TajweedToggleRequest(BaseModel):
    topicKey: str = Field(..., min_length=1)

class TajweedProgressResponse(BaseModel):
    completedTopics: List[str]
    updatedAt: Optional[datetime] = None

class UsulToggleRequest(BaseModel):
    science: str = Field(..., min_length=1)
    lessonId: str = Field(..., min_length=1)

class UsulSyncRequest(BaseModel):
    tawheed: Optional[List[str]] = None
    hadeeth: Optional[List[str]] = None
    seerah: Optional[List[str]] = None
    tafseer: Optional[List[str]] = None

class UsulProgressResponse(BaseModel):
    tawheed: List[str]
    hadeeth: List[str]
    seerah: List[str]
    tafseer: List[str]
    updatedAt: Optional[datetime] = None
