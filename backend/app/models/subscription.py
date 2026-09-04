from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.database import Base

class CourseSubscription(Base):
    __tablename__ = "COURSE_SUBSCRIPTION"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    studentName = Column(String, nullable=False)
    studentPhone = Column(String, nullable=False)
    userCode = Column(String, nullable=True)
    studentEmail = Column(String, nullable=True)
    courseKey = Column(String, nullable=False)
    courseTitle = Column(String, nullable=True)
    courseSubtitle = Column(String, nullable=True)
    amount = Column(String, nullable=True)
    paymentMethod = Column(String, nullable=True)  # vodafone, instapay, fawry, card
    senderDetails = Column(String, nullable=True)
    receiptImage = Column(Text, nullable=True)  # Base64 screenshot
    activationToken = Column(String(64), unique=True, index=True, nullable=True)
    status = Column(String, nullable=False, default="PENDING")  # PENDING, ACTIVATED, EXPIRED
    durationDays = Column(Integer, nullable=True)
    createdAt = Column(DateTime, default=datetime.now)
    activatedAt = Column(DateTime, nullable=True)
    expiresAt = Column(DateTime, nullable=True)
    warningSent = Column(Boolean, default=False)

    def is_expired(self) -> bool:
        if self.expiresAt is None:
            return False
        return datetime.now() > self.expiresAt
