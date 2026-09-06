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

def get_code_variants(code: str) -> list[str]:
    clean = code.strip().lower()
    variants = {clean}
    if clean.isdigit():
        stripped = clean.lstrip('0')
        if stripped:
            variants.add(stripped)
        variants.add(clean.zfill(4))
    return [v for v in variants if v]

def is_same_exam(existing_name: str, incoming_name: str) -> bool:
    if not existing_name or not incoming_name:
        return False
    if existing_name.strip().lower() == incoming_name.strip().lower():
        return True
    norm_a = normalize_arabic(existing_name)
    norm_b = normalize_arabic(incoming_name)
    if norm_a == norm_b:
        return True
    # Substring matching (e.g., "الاختبار الشفوي لنهاية" in "الاختبار الشفوي لنهاية للدورة الصيفية")
    if (norm_a in norm_b or norm_b in norm_a) and min(len(norm_a), len(norm_b)) >= 6:
        return True
    # Both are oral exams ("شفوي")
    if "شفوي" in norm_a and "شفوي" in norm_b:
        return True
    # Both are written exams ("تحريري")
    if "تحريري" in norm_a and "تحريري" in norm_b:
        return True
    # High word overlap (>= 60%)
    words_a = set(norm_a.split())
    words_b = set(norm_b.split())
    if words_a and words_b:
        intersection = words_a.intersection(words_b)
        smaller = min(len(words_a), len(words_b))
        if smaller > 0 and len(intersection) / smaller >= 0.6:
            return True
    return False

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
    variants = get_code_variants(clean_code)
    entries = (
        db.query(ExamResult)
        .filter(func.lower(ExamResult.result_code).in_(variants))
        .order_by(ExamResult.examDate.desc(), ExamResult.id.desc())
        .all()
    )

    if not entries:
        raise ValueError("مفيش نتيجة مسجلة بهذا الكود")

    student_name = entries[0].studentName

    # Deduplicate results by exam category so frontend never shows duplicate cards
    deduped_results = []
    seen_keys = set()
    for e in entries:
        norm = normalize_arabic(e.examName)
        if "شفوي" in norm:
            key = "oral"
        elif "تحريري" in norm:
            key = "written"
        else:
            key = norm
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_results.append(to_item_response(e))

    return ExamResultLookupResponse(studentName=student_name, results=deduped_results)

def find_matching_entry(existing_entries: List[ExamResult], incoming_exam: str) -> Optional[ExamResult]:
    for e in existing_entries:
        if is_same_exam(e.examName, incoming_exam):
            return e
    # If student has only 1 existing record and incoming is not in conflict, update that record
    if len(existing_entries) == 1:
        norm_existing = normalize_arabic(existing_entries[0].examName)
        norm_new = normalize_arabic(incoming_exam)
        conflict = ("شفوي" in norm_existing and "تحريري" in norm_new) or ("تحريري" in norm_existing and "شفوي" in norm_new)
        if not conflict:
            return existing_entries[0]
    return None

def create_or_update(request: ExamResultRequest, db: Session) -> ExamResultItemResponse:
    code = request.resultCode.strip()
    exam = request.examName.strip()
    clean_student_name = request.studentName.strip()
    variants = get_code_variants(code)

    # Find existing entries for this student code (with or without leading zeros)
    existing_entries = (
        db.query(ExamResult)
        .filter(func.lower(ExamResult.result_code).in_(variants))
        .all()
    )

    entry = find_matching_entry(existing_entries, exam)

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
        clean_student_name = req.studentName.strip()
        variants = get_code_variants(code)

        existing_entries = (
            db.query(ExamResult)
            .filter(func.lower(ExamResult.result_code).in_(variants))
            .all()
        )

        entry = find_matching_entry(existing_entries, exam)

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
    variants = get_code_variants(clean_code)
    q = db.query(ExamResult).filter(func.lower(ExamResult.result_code).in_(variants))
    if exam_name:
        clean_exam = exam_name.strip()
        entries = q.all()
        deleted = 0
        for e in entries:
            if is_same_exam(e.examName, clean_exam):
                db.delete(e)
                deleted += 1
        db.commit()
        return {"success": True, "deleted": deleted}
    count = q.delete(synchronize_session=False)
    db.commit()
    return {"success": True, "deleted": count}

