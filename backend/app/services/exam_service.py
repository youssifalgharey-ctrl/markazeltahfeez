import re
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.exam_result import ExamResult
from app.schemas.exam import (
    ExamResultRequest,
    ExamResultItemResponse,
    ExamResultLookupResponse,
)

PASS_THRESHOLD = 0.5

def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    # remove diacritics / tashkeel
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    # normalize alef
    text = re.sub(r"[إأآاٱ]", "ا", text)
    # normalize teh marbuta / heh
    text = re.sub(r"ة", "ه", text)
    # normalize yaa / alef maksura
    text = re.sub(r"[ىي]", "ي", text)
    # normalize spaces
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

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
        .order_by(ExamResult.examDate.desc(), ExamResult.id.desc())
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
    norm_exam = normalize_arabic(exam)
    clean_student_name = request.studentName.strip()

    # Find existing entries for this student
    existing_entries = (
        db.query(ExamResult)
        .filter(func.lower(ExamResult.result_code) == code.lower())
        .all()
    )

    entry = None
    for e in existing_entries:
        if e.examName.lower() == exam.lower() or normalize_arabic(e.examName) == norm_exam:
            entry = e
            break

    if not entry:
        entry = ExamResult()
        db.add(entry)

    entry.result_code = code
    entry.studentName = clean_student_name
    entry.examName = exam
    entry.examDate = request.examDate
    entry.score = float(request.score)
    entry.maxScore = float(request.maxScore)
    entry.passed = request.passed
    entry.notes = request.notes

    # Keep studentName uniform across all results for this code
    for other in existing_entries:
        if other != entry:
            other.studentName = clean_student_name

    db.commit()
    db.refresh(entry)
    return to_item_response(entry)

def batch_create_or_update(requests: List[ExamResultRequest], db: Session) -> dict:
    saved = 0
    for req in requests:
        code = req.resultCode.strip()
        exam = req.examName.strip()
        norm_exam = normalize_arabic(exam)
        clean_student_name = req.studentName.strip()

        existing_entries = (
            db.query(ExamResult)
            .filter(func.lower(ExamResult.result_code) == code.lower())
            .all()
        )

        entry = None
        for e in existing_entries:
            if e.examName.lower() == exam.lower() or normalize_arabic(e.examName) == norm_exam:
                entry = e
                break

        if not entry:
            entry = ExamResult()
            db.add(entry)

        entry.result_code = code
        entry.studentName = clean_student_name
        entry.examName = exam
        entry.examDate = req.examDate
        entry.score = float(req.score)
        entry.maxScore = float(req.maxScore)
        entry.passed = req.passed if req.passed is not None else (
            entry.maxScore > 0 and (entry.score / entry.maxScore) >= PASS_THRESHOLD
        )
        entry.notes = req.notes

        # Keep studentName uniform across all results for this code
        for other in existing_entries:
            if other != entry:
                other.studentName = clean_student_name

        saved += 1

    db.commit()
    return {"success": True, "count": saved}

def delete_result(code: str, exam_name: Optional[str], db: Session) -> dict:
    clean_code = code.strip()
    q = db.query(ExamResult).filter(func.lower(ExamResult.result_code) == clean_code.lower())
    if exam_name:
        clean_exam = exam_name.strip()
        norm_exam = normalize_arabic(clean_exam)
        entries = q.all()
        deleted = 0
        for e in entries:
            if e.examName.lower() == clean_exam.lower() or normalize_arabic(e.examName) == norm_exam:
                db.delete(e)
                deleted += 1
        db.commit()
        return {"success": True, "deleted": deleted}
    count = q.delete(synchronize_session=False)
    db.commit()
    return {"success": True, "deleted": count}

