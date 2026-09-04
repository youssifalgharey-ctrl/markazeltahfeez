from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base

class QuizScore(Base):
    __tablename__ = "quiz_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_code = Column(String, nullable=True)
    student_email = Column(String, nullable=True)
    student_name = Column(String, nullable=True)
    surah_name = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Integer, nullable=False)
    passed = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    @property
    def userCode(self):
        return self.user_code

    @userCode.setter
    def userCode(self, val):
        self.user_code = val

    @property
    def studentEmail(self):
        return self.student_email

    @studentEmail.setter
    def studentEmail(self, val):
        self.student_email = val

    @property
    def studentName(self):
        return self.student_name

    @studentName.setter
    def studentName(self, val):
        self.student_name = val

    @property
    def surahName(self):
        return self.surah_name

    @surahName.setter
    def surahName(self, val):
        self.surah_name = val

    @property
    def totalQuestions(self):
        return self.total_questions

    @totalQuestions.setter
    def totalQuestions(self, val):
        self.total_questions = val

    @property
    def createdAt(self):
        return self.created_at

    @createdAt.setter
    def createdAt(self, val):
        self.created_at = val
