from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base

class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    userCode = Column(String, nullable=True)
    studentEmail = Column(String, nullable=True)
    type = Column(String, nullable=True)  # session, system, alert
    category = Column(String, nullable=True)
    title = Column(String, nullable=True)
    message = Column(String(2000), nullable=True)
    status = Column(String, nullable=True)  # APPROVED, REJECTED, PENDING, INFO
    bookingReference = Column(String, nullable=True)
    link = Column(String, nullable=True)
    linkText = Column(String, nullable=True)
    isRead = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.now)
