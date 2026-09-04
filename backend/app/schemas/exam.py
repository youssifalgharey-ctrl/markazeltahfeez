from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

class ExamResultRequest(BaseModel):
    resultCode: str = Field(..., min_length=1)
    studentName: str = Field(..., min_length=1)
    examName: str = Field(..., min_length=1)
    examDate: Optional[date] = None
    score: int
    maxScore: int
    passed: Optional[bool] = None
    notes: Optional[str] = None

class ExamResultItemResponse(BaseModel):
    examName: str
    examDate: Optional[date] = None
    score: int
    maxScore: int
    passed: bool
    notes: Optional[str] = None

class ExamResultLookupResponse(BaseModel):
    studentName: str
    results: List[ExamResultItemResponse]
