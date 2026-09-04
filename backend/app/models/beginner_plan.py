from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class BeginnerPlan(Base):
    __tablename__ = "BEGINNER_PLAN"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_beginner_plan_user"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("APP_USER.id", ondelete="CASCADE"), nullable=False, unique=True)
    ageGroup = Column(String, nullable=False)
    priorMemorization = Column(String, nullable=False)
    ability = Column(String, nullable=False)
    minutesPerDay = Column(Integer, nullable=False)
    followUp = Column(String, nullable=False)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=False)
    scheduleJson = Column(Text, nullable=False)
    tipsJson = Column(Text, nullable=False)
    totalItems = Column(Integer, nullable=False)
    currentIndex = Column(Integer, nullable=False, default=0)
    completedJson = Column(Text, nullable=True)
    aiGenerated = Column(Boolean, nullable=False, default=False)
    createdAt = Column(DateTime, default=datetime.now)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="beginner_plan")
