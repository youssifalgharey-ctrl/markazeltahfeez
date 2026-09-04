import json
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.progress import TajweedProgress
from app.schemas.progress import TajweedProgressResponse

def get_or_create(user: User, db: Session) -> TajweedProgress:
    progress = db.query(TajweedProgress).filter(TajweedProgress.user_id == user.id).first()
    if not progress:
        progress = TajweedProgress(user_id=user.id, completedTopics="[]", completedCount=0)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress

def get_progress(user: User, db: Session) -> TajweedProgressResponse:
    progress = get_or_create(user, db)
    topics = json.loads(progress.completedTopics) if progress.completedTopics else []
    return TajweedProgressResponse(completedTopics=topics, updatedAt=progress.updatedAt)

def toggle_topic(user: User, topic_key: str, db: Session) -> TajweedProgressResponse:
    progress = get_or_create(user, db)
    topics = json.loads(progress.completedTopics) if progress.completedTopics else []

    key = topic_key.strip()
    if key in topics:
        topics.remove(key)
    else:
        topics.append(key)

    progress.completedTopics = json.dumps(topics, ensure_ascii=False)
    progress.completedCount = len(topics)
    db.commit()
    db.refresh(progress)

    return TajweedProgressResponse(completedTopics=topics, updatedAt=progress.updatedAt)

def sync_progress(user: User, completed_topics: List[str], db: Session) -> TajweedProgressResponse:
    progress = get_or_create(user, db)
    topics = completed_topics or []
    progress.completedTopics = json.dumps(topics, ensure_ascii=False)
    progress.completedCount = len(topics)
    db.commit()
    db.refresh(progress)

    return TajweedProgressResponse(completedTopics=topics, updatedAt=progress.updatedAt)
