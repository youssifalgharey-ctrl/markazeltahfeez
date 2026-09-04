from typing import List, Optional
from pydantic import BaseModel

class PlanRequest(BaseModel):
    memorizedPages: Optional[int] = 0
    minutesPerDay: Optional[int] = 30
    goal: Optional[str] = "khatm"
    ability: Optional[str] = "good"
    timing: Optional[str] = "fajr"
    daysPerWeek: Optional[int] = 6
    followUp: Optional[str] = "alone"
    challenge: Optional[str] = "forgetting"

class PlanScheduleItem(BaseModel):
    icon: str
    title: str
    desc: str

class PlanResponse(BaseModel):
    hasPlan: Optional[bool] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    pagesPerDay: Optional[str] = None
    minutesPerDay: Optional[int] = None
    monthsToKhatm: Optional[str] = None
    schedule: Optional[List[PlanScheduleItem]] = None
    tips: Optional[List[str]] = None
    aiGenerated: Optional[bool] = False
    createdAt: Optional[str] = None

class BeginnerPlanRequest(BaseModel):
    ageGroup: str
    priorMemorization: str
    ability: str
    minutesPerDay: int
    followUp: str

class BeginnerPlanItem(BaseModel):
    order: int
    surahName: str
    description: str
    icon: str
    completed: Optional[bool] = False
    completedAt: Optional[str] = None

class BeginnerPlanResponse(BaseModel):
    hasPlan: Optional[bool] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    totalItems: Optional[int] = 0
    currentIndex: Optional[int] = 0
    completedCount: Optional[int] = 0
    schedule: Optional[List[BeginnerPlanItem]] = None
    tips: Optional[List[str]] = None
    aiGenerated: Optional[bool] = False
    createdAt: Optional[str] = None

class BeginnerPlanCompleteRequest(BaseModel):
    order: int
