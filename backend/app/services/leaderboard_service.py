from datetime import date, timedelta
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.memorization import MemorizationEntry
from app.models.leaderboard import WeeklyLeaderboardEntry
from app.schemas.leaderboard import WeeklyLeaderboardResponse, LeaderboardEntryResponse

POINTS_PER_PAGE = 5
MAX_LEADERBOARD_USERS = 10

def get_current_week_start() -> date:
    today = date.today()
    # Friday is weekday 4 in python (Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6)
    offset = (today.weekday() - 4) % 7
    return today - timedelta(days=offset)

def get_current_week_end() -> date:
    return get_current_week_start() + timedelta(days=6)

def refresh_current_week(db: Session):
    week_start = get_current_week_start()
    week_end = get_current_week_end()

    # Sum cumulative pages for each user
    sums = (
        db.query(MemorizationEntry.user_id, func.coalesce(func.sum(MemorizationEntry.pagesCount), 0.0))
        .group_by(MemorizationEntry.user_id)
        .all()
    )
    user_points_map = {row[0]: float(row[1]) for row in sums}

    all_users = db.query(User).all()
    ranked = []

    for user in all_users:
        pages = user_points_map.get(user.id, 0.0)
        pts = int(round(pages * POINTS_PER_PAGE))
        entry = WeeklyLeaderboardEntry(
            user_id=user.id,
            week_start=week_start,
            week_end=week_end,
            pagesCount=pages,
            points=pts,
            rank_position=1,
        )
        ranked.append(entry)

    # Sort descending by points, then pages, then user id
    ranked.sort(key=lambda e: (-e.points, -e.pagesCount, e.user_id))

    for idx, e in enumerate(ranked):
        e.rank_position = idx + 1

    db.query(WeeklyLeaderboardEntry).filter(WeeklyLeaderboardEntry.week_start == week_start).delete()
    db.flush()

    for e in ranked:
        db.add(e)
    db.commit()

def clear_leaderboard(db: Session):
    db.query(WeeklyLeaderboardEntry).delete()
    db.commit()

def get_current_week(db: Session) -> WeeklyLeaderboardResponse:
    week_start = get_current_week_start()
    week_end = get_current_week_end()

    try:
        refresh_current_week(db)
    except Exception as ex:
        db.rollback()

    stored = (
        db.query(WeeklyLeaderboardEntry)
        .filter(WeeklyLeaderboardEntry.week_start == week_start)
        .order_by(WeeklyLeaderboardEntry.rank_position.asc())
        .all()
    )

    active_entries = [e for e in stored if e.points > 0]
    total_users = len(active_entries)
    limited = active_entries[:MAX_LEADERBOARD_USERS]
    displayed_users = len(limited)

    entries = [
        LeaderboardEntryResponse(
            rankPosition=e.rank_position,
            fullName=e.user.fullName if e.user else "طالب قرآن",
            profileImage=e.user.profileImage if e.user else None,
            currentSurah=(e.user.currentSurah if e.user and e.user.currentSurah else "مسار الحفظ"),
            pagesCount=e.pagesCount,
            points=e.points,
        )
        for e in limited
    ]

    return WeeklyLeaderboardResponse(
        weekStart=week_start,
        weekEnd=week_end,
        pointsPerPage=POINTS_PER_PAGE,
        totalUsers=total_users,
        displayedUsers=displayed_users,
        entries=entries,
    )
