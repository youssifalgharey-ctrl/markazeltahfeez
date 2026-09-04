from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.memorization import MemorizationEntry
from app.schemas.memorization import (
    MemorizationEntryRequest,
    MemorizationEntryResponse,
    MemorizationStatsResponse,
)
from app.services.leaderboard_service import refresh_current_week

MAX_PAGES_UNDER_16 = 5
MAX_PAGES_16_AND_ABOVE = 10

def enforce_daily_pages_limit(user: User, pages_count: Optional[float]):
    if pages_count is None:
        return
    max_pages = MAX_PAGES_UNDER_16 if (user.age and user.age < 16) else MAX_PAGES_16_AND_ABOVE
    if pages_count > max_pages:
        raise ValueError("حصلت مشكلة في حفظ التسجيل، من فضلك راجع البيانات وحاول تاني")

def to_response(entry: MemorizationEntry) -> MemorizationEntryResponse:
    return MemorizationEntryResponse(
        id=entry.id,
        entryDate=entry.entryDate,
        content=entry.content,
        pagesCount=entry.pagesCount,
        edited=entry.edited,
        createdAt=entry.createdAt,
        updatedAt=entry.updatedAt,
    )

def log_today(user: User, request: MemorizationEntryRequest, db: Session) -> MemorizationEntryResponse:
    today = date.today()
    existing = (
        db.query(MemorizationEntry)
        .filter(MemorizationEntry.user_id == user.id, MemorizationEntry.entry_date == today)
        .first()
    )
    if existing:
        raise ValueError("تم تسجيل حفظ اليوم بالفعل، ولا يمكن التعديل عليه")

    enforce_daily_pages_limit(user, request.pagesCount)

    entry = MemorizationEntry(
        user_id=user.id,
        user_code=user.userCode,
        student_name=user.fullName,
        entry_date=today,
        content=request.content.strip(),
        pagesCount=request.pagesCount,
        edited=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    try:
        refresh_current_week(db)
    except Exception:
        pass

    return to_response(entry)

def update_today(user: User, request: MemorizationEntryRequest, db: Session) -> MemorizationEntryResponse:
    today = date.today()
    entry = (
        db.query(MemorizationEntry)
        .filter(MemorizationEntry.user_id == user.id, MemorizationEntry.entry_date == today)
        .first()
    )
    if not entry:
        raise ValueError("لسه معملتش تسجيل حفظ النهاردة عشان تقدر تعدله")

    if entry.edited:
        raise ValueError("تم استخدام فرصة تعديل تسجيل اليوم بالفعل، ولا يمكن التعديل مرة أخرى")

    enforce_daily_pages_limit(user, request.pagesCount)

    entry.content = request.content.strip()
    entry.pagesCount = request.pagesCount
    entry.user_code = user.userCode
    entry.student_name = user.fullName
    entry.edited = True

    db.commit()
    db.refresh(entry)

    try:
        refresh_current_week(db)
    except Exception:
        pass

    return to_response(entry)

def get_history(user: User, db: Session) -> List[MemorizationEntryResponse]:
    entries = (
        db.query(MemorizationEntry)
        .filter(MemorizationEntry.user_id == user.id)
        .order_by(MemorizationEntry.entry_date.desc())
        .all()
    )
    return [to_response(e) for e in entries]

def compute_current_streak(entries_desc: List[MemorizationEntry]) -> int:
    if not entries_desc:
        return 0

    expected = date.today()
    if entries_desc[0].entryDate != expected:
        expected = expected - timedelta(days=1)
        if entries_desc[0].entryDate != expected:
            return 0

    streak = 0
    for entry in entries_desc:
        if entry.entryDate == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif entry.entryDate < expected:
            break
    return streak

def compute_longest_streak(entries_desc: List[MemorizationEntry]) -> int:
    if not entries_desc:
        return 0
    longest = 1
    current = 1
    for i in range(1, len(entries_desc)):
        prev_day = entries_desc[i - 1].entryDate
        day = entries_desc[i].entryDate
        if prev_day - timedelta(days=1) == day:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    return longest

def get_stats(user: User, db: Session) -> MemorizationStatsResponse:
    entries = (
        db.query(MemorizationEntry)
        .filter(MemorizationEntry.user_id == user.id)
        .order_by(MemorizationEntry.entry_date.desc())
        .all()
    )
    total_days = len(entries)
    total_pages = sum(e.pagesCount for e in entries if e.pagesCount is not None)
    last_date = entries[0].entryDate if entries else None
    logged_today = (last_date == date.today()) if last_date else False

    current_streak = compute_current_streak(entries)
    longest_streak = compute_longest_streak(entries)

    return MemorizationStatsResponse(
        totalDays=total_days,
        currentStreak=current_streak,
        longestStreak=longest_streak,
        totalPages=total_pages,
        lastEntryDate=last_date,
        loggedToday=logged_today,
    )
