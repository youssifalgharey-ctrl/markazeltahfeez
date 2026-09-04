from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class MemorizationEntry(Base):
    __tablename__ = "MEMORIZATION_ENTRY"
    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", name="uk_user_entry_date"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("APP_USER.id", ondelete="CASCADE"), nullable=False)
    entry_date = Column(Date, nullable=False, default=date.today)
    content = Column(Text, nullable=False)
    pagesCount = Column(Float, nullable=True)
    user_code = Column(String, nullable=True)
    student_name = Column(String, nullable=True)
    edited = Column(Boolean, default=False, nullable=False)
    createdAt = Column(DateTime, default=datetime.now)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="memorization_entries")

    @property
    def entryDate(self):
        return self.entry_date

    @entryDate.setter
    def entryDate(self, val):
        self.entry_date = val

    @property
    def userCode(self):
        return self.user_code

    @userCode.setter
    def userCode(self, val):
        self.user_code = val

    @property
    def studentName(self):
        return self.student_name

    @studentName.setter
    def studentName(self, val):
        self.student_name = val
