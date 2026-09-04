from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "APP_USER"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fullName = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True, index=True)
    age = Column(Integer, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password = Column(String, nullable=False)
    userCode = Column(String(4), unique=True, index=True, nullable=True)
    inviteCode = Column(String, nullable=True)
    role = Column(String, nullable=False, default="USER")
    token_version = Column(BigInteger, default=1, nullable=False)
    address = Column(String, nullable=True)
    currentSurah = Column(String, nullable=True)
    profileImage = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.now)

    # Relationships
    memorization_entries = relationship("MemorizationEntry", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("WeeklyLeaderboardEntry", back_populates="user", cascade="all, delete-orphan")
    plan = relationship("Plan", back_populates="user", uselist=False, cascade="all, delete-orphan")
    beginner_plan = relationship("BeginnerPlan", back_populates="user", uselist=False, cascade="all, delete-orphan")
    tajweed_progress = relationship("TajweedProgress", back_populates="user", uselist=False, cascade="all, delete-orphan")
    usul_progress = relationship("UsulProgress", back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def tokenVersion(self):
        return self.token_version

    @tokenVersion.setter
    def tokenVersion(self, val):
        self.token_version = val
