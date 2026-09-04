from typing import List, Optional
from datetime import date
from pydantic import BaseModel

class LeaderboardEntryResponse(BaseModel):
    rankPosition: int
    fullName: str
    profileImage: Optional[str] = None
    currentSurah: Optional[str] = "مسار الحفظ"
    pagesCount: float
    points: int

class WeeklyLeaderboardResponse(BaseModel):
    weekStart: date
    weekEnd: date
    pointsPerPage: int
    totalUsers: int
    displayedUsers: int
    entries: List[LeaderboardEntryResponse]
