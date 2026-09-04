from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Plan(Base):
    __tablename__ = "PLAN"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_plan_user"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("APP_USER.id", ondelete="CASCADE"), nullable=False, unique=True)
    memorizedPages = Column(Integer, nullable=False)
    minutesPerDay = Column(Integer, nullable=False)
    goal = Column(String, nullable=False)
    ability = Column(String, nullable=False)
    timing = Column(String, nullable=False)
    daysPerWeek = Column(Integer, nullable=True)
    followUp = Column(String, nullable=True)
    challenge = Column(String, nullable=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=False)
    pagesPerDay = Column(String, nullable=False)
    monthsToKhatm = Column(String, nullable=False)
    scheduleJson = Column(Text, nullable=False)
    tipsJson = Column(Text, nullable=False)
    aiGenerated = Column(Boolean, nullable=False, default=False)
    createdAt = Column(DateTime, default=datetime.now)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="plan")
