from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, Index
from app.database import Base

class ExamResult(Base):
    __tablename__ = "EXAM_RESULT"
    __table_args__ = (
        Index("idx_exam_result_code", "result_code"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    result_code = Column(String(50), nullable=False)
    studentName = Column(String, nullable=False)
    examName = Column(String, nullable=False)
    examDate = Column(Date, nullable=True)
    score = Column(Integer, nullable=False)
    maxScore = Column(Integer, nullable=False)
    passed = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.now)

    @property
    def resultCode(self):
        return self.result_code

    @resultCode.setter
    def resultCode(self, val):
        self.result_code = val
