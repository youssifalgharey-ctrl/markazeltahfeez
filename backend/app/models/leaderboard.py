from datetime import datetime, date
from sqlalchemy import Column, Integer, DateTime, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class WeeklyLeaderboardEntry(Base):
    __tablename__ = "WEEKLY_LEADERBOARD"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uk_leaderboard_user_week"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("APP_USER.id", ondelete="CASCADE"), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    pagesCount = Column(Float, nullable=False, default=0.0)
    points = Column(Integer, nullable=False, default=0)
    rank_position = Column(Integer, nullable=False, default=1)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="leaderboard_entries")

    @property
    def weekStart(self):
        return self.week_start

    @weekStart.setter
    def weekStart(self, val):
        self.week_start = val

    @property
    def weekEnd(self):
        return self.week_end

    @weekEnd.setter
    def weekEnd(self, val):
        self.week_end = val

    @property
    def rankPosition(self):
        return self.rank_position

    @rankPosition.setter
    def rankPosition(self, val):
        self.rank_position = val
