from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.exam_result import ExamResult
from app.schemas.exam import (
    ExamResultRequest,
    ExamResultItemResponse,
    ExamResultLookupResponse,
)

PASS_THRESHOLD = 0.5

def to_item_response(entry: ExamResult) -> ExamResultItemResponse:
    if entry.passed is not None:
        passed = entry.passed
    else:
        passed = (
            entry.maxScore > 0 and (entry.score / entry.maxScore) >= PASS_THRESHOLD
            if entry.maxScore else False
        )
    return ExamResultItemResponse(
        examName=entry.examName,
        examDate=entry.examDate,
        score=entry.score,
        maxScore=entry.maxScore,
        passed=passed,
        notes=entry.notes,
    )

def lookup(result_code: str, db: Session) -> ExamResultLookupResponse:
    clean_code = result_code.strip()
    entries = (
        db.query(ExamResult)
        .filter(func.lower(ExamResult.result_code) == clean_code.lower())
        .order_by(ExamResult.examDate.desc())
        .all()
    )

    if not entries:
        raise ValueError("مفيش نتيجة مسجلة بهذا الكود")

    student_name = entries[0].studentName
    results = [to_item_response(e) for e in entries]
    return ExamResultLookupResponse(studentName=student_name, results=results)

def create_or_update(request: ExamResultRequest, db: Session) -> ExamResultItemResponse:
    code = request.resultCode.strip()
    exam = request.examName.strip()

    entry = (
        db.query(ExamResult)
        .filter(
            func.lower(ExamResult.result_code) == code.lower(),
            func.lower(ExamResult.examName) == exam.lower(),
        )
        .first()
    )

    if not entry:
        entry = ExamResult()
        db.add(entry)

    entry.result_code = code
    entry.studentName = request.studentName.strip()
    entry.examName = exam
    entry.examDate = request.examDate
    entry.score = request.score
    entry.maxScore = request.maxScore
    entry.passed = request.passed
    entry.notes = request.notes

    db.commit()
    db.refresh(entry)
    return to_item_response(entry)
