from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

class MemorizationEntryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    pagesCount: Optional[float] = None

class MemorizationEntryResponse(BaseModel):
    id: int
    entryDate: date
    content: str
    pagesCount: Optional[float] = None
    edited: bool = False
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

class MemorizationStatsResponse(BaseModel):
    totalDays: int
    currentStreak: int
    longestStreak: int
    totalPages: float
    lastEntryDate: Optional[date] = None
    loggedToday: bool = False
