from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class TajweedProgress(Base):
    __tablename__ = "TAJWEED_PROGRESS"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_tajweed_progress_user"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("APP_USER.id", ondelete="CASCADE"), nullable=False, unique=True)
    completedTopics = Column(Text, nullable=True, default="[]")
    completedCount = Column(Integer, nullable=False, default=0)
    createdAt = Column(DateTime, default=datetime.now)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="tajweed_progress")


class UsulProgress(Base):
    __tablename__ = "USUL_PROGRESS"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_usul_progress_user"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("APP_USER.id", ondelete="CASCADE"), nullable=False, unique=True)
    tawheedLessons = Column(Text, nullable=True, default="[]")
    hadeethLessons = Column(Text, nullable=True, default="[]")
    seerahLessons = Column(Text, nullable=True, default="[]")
    tafseerLessons = Column(Text, nullable=True, default="[]")
    createdAt = Column(DateTime, default=datetime.now)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="usul_progress")
