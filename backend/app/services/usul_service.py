import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.progress import UsulProgress
from app.schemas.progress import UsulProgressResponse, UsulSyncRequest

def get_or_create(user: User, db: Session) -> UsulProgress:
    progress = db.query(UsulProgress).filter(UsulProgress.user_id == user.id).first()
    if not progress:
        progress = UsulProgress(
            user_id=user.id,
            tawheedLessons="[]",
            hadeethLessons="[]",
            seerahLessons="[]",
            tafseerLessons="[]"
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress

def to_response(p: UsulProgress) -> UsulProgressResponse:
    tawheed = json.loads(p.tawheedLessons) if p.tawheedLessons else []
    hadeeth = json.loads(p.hadeethLessons) if p.hadeethLessons else []
    seerah = json.loads(p.seerahLessons) if p.seerahLessons else []
    tafseer = json.loads(p.tafseerLessons) if p.tafseerLessons else []
    return UsulProgressResponse(
        tawheed=tawheed,
        hadeeth=hadeeth,
        seerah=seerah,
        tafseer=tafseer,
        updatedAt=p.updatedAt,
    )

def get_progress(user: User, db: Session) -> UsulProgressResponse:
    progress = get_or_create(user, db)
    return to_response(progress)

def toggle_lesson(user: User, science: str, lesson_id: str, db: Session) -> UsulProgressResponse:
    progress = get_or_create(user, db)
    s = science.strip().lower()
    lid = lesson_id.strip()

    if s == "tawheed":
        list_ = json.loads(progress.tawheedLessons) if progress.tawheedLessons else []
        if lid in list_:
            list_.remove(lid)
        else:
            list_.append(lid)
        progress.tawheedLessons = json.dumps(list_, ensure_ascii=False)
    elif s == "hadeeth":
        list_ = json.loads(progress.hadeethLessons) if progress.hadeethLessons else []
        if lid in list_:
            list_.remove(lid)
        else:
            list_.append(lid)
        progress.hadeethLessons = json.dumps(list_, ensure_ascii=False)
    elif s == "seerah":
        list_ = json.loads(progress.seerahLessons) if progress.seerahLessons else []
        if lid in list_:
            list_.remove(lid)
        else:
            list_.append(lid)
        progress.seerahLessons = json.dumps(list_, ensure_ascii=False)
    elif s == "tafseer":
        list_ = json.loads(progress.tafseerLessons) if progress.tafseerLessons else []
        if lid in list_:
            list_.remove(lid)
        else:
            list_.append(lid)
        progress.tafseerLessons = json.dumps(list_, ensure_ascii=False)
    else:
        raise ValueError("المسار غير معروف: " + science)

    db.commit()
    db.refresh(progress)
    return to_response(progress)

def sync_progress(user: User, req: UsulSyncRequest, db: Session) -> UsulProgressResponse:
    progress = get_or_create(user, db)

    if req.tawheed is not None:
        progress.tawheedLessons = json.dumps(req.tawheed, ensure_ascii=False)
    if req.hadeeth is not None:
        progress.hadeethLessons = json.dumps(req.hadeeth, ensure_ascii=False)
    if req.seerah is not None:
        progress.seerahLessons = json.dumps(req.seerah, ensure_ascii=False)
    if req.tafseer is not None:
        progress.tafseerLessons = json.dumps(req.tafseer, ensure_ascii=False)

    db.commit()
    db.refresh(progress)
    return to_response(progress)
