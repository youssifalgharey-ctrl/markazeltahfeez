from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

class IjazaBooking(Base):
    __tablename__ = "IJAZA_BOOKING"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    studentName = Column(String, nullable=False)
    studentEmail = Column(String, nullable=False)
    studentPhone = Column(String, nullable=False)
    userCode = Column(String, nullable=True)
    sheikhName = Column(String, nullable=False)
    riwayah = Column(String, nullable=False)
    sessionType = Column(String, nullable=True)
    trackName = Column(String, nullable=True)
    sessionMode = Column(String, nullable=True)
    appointmentDate = Column(String, nullable=False)
    appointmentTime = Column(String, nullable=False)
    notes = Column(String(1000), nullable=True)
    bookingReference = Column(String(32), unique=True, index=True, nullable=True)
    actionToken = Column(String(64), unique=True, index=True, nullable=True)
    status = Column(String, nullable=True, default="PENDING")  # CONFIRMED, PENDING, COMPLETED, CANCELLED
    paymentMethod = Column(String, nullable=True)
    paymentSender = Column(String, nullable=True)
    amount = Column(String, nullable=True)
    receiptBase64 = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.now)
