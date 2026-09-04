from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.quiz import QuizScore
from app.models.notification import UserNotification
from app.security.deps import get_current_user_optional

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

@router.post("/submit")
def submit_score(
    body: Dict[str, Any] = Body(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    try:
        user_code = current_user.userCode if current_user else body.get("userCode")
        student_email = current_user.email if current_user else body.get("studentEmail")
        student_name = current_user.fullName if current_user else body.get("studentName")
        surah_name = body.get("surahName")
        score = int(body.get("score", 0))
        total = int(body.get("totalQuestions", 5))

        percentage = int(round((score / total) * 100)) if total > 0 else 0
        passed = (percentage >= 60)

        quiz_score = QuizScore(
            user_code=user_code.strip() if user_code and user_code.strip() else None,
            student_email=student_email.strip() if student_email and student_email.strip() else None,
            student_name=student_name.strip() if student_name and student_name.strip() else "طالب قرآن",
            surah_name=surah_name.strip() if surah_name and surah_name.strip() else "سورة قرآنية",
            score=score,
            total_questions=total,
            percentage=percentage,
            passed=passed,
            created_at=datetime.now(),
        )
        db.add(quiz_score)
        db.commit()
        db.refresh(quiz_score)

        if passed and (user_code or student_email):
            try:
                badge_msg = "درجة كاملة وامتياز 🌟" if percentage == 100 else "أداء رائع ومميز 👏"
                notif = UserNotification(
                    userCode=user_code,
                    studentEmail=student_email,
                    type="session",
                    category="نتيجة اختبار",
                    title=f"تهنئة: نتيجتك في اختبار {quiz_score.surahName} ({percentage}%) 🎉",
                    message=f"أحسنت يا {quiz_score.studentName}! لقد اجتزت اختبار {quiz_score.surahName} بنجاح وحققت {score} من {total} أسئلة. {badge_msg}",
                    status="INFO",
                    link="/quiz.html",
                    linkText="خوض اختبار جديد",
                    isRead=False,
                    createdAt=datetime.now(),
                )
                db.add(notif)
                db.commit()
            except Exception:
                pass

        return {
            "success": True,
            "id": quiz_score.id,
            "score": score,
            "total": total,
            "percentage": percentage,
            "passed": passed,
            "message": "بارك الله فيك! اجتزت الاختبار بنجاح." if passed else "حاول مرة أخرى لتحسين نتيجتك وتثبيت حفظك.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={"success": False, "message": "حدث خطأ أثناء حفظ النتيجة."})

@router.get("/my-scores")
def get_my_scores(
    userCode: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    clean_code = current_user.userCode if current_user else (userCode.strip() if userCode else None)
    clean_email = current_user.email if current_user else (email.strip() if email else None)

    query = db.query(QuizScore)
    conditions = []
    if clean_code:
        conditions.append(QuizScore.user_code == clean_code)
    if clean_email:
        conditions.append(QuizScore.student_email == clean_email)

    if conditions:
        from sqlalchemy import or_
        scores = query.filter(or_(*conditions)).order_by(QuizScore.created_at.desc()).all()
    else:
        scores = []

    return [
        {
            "id": s.id,
            "userCode": s.userCode,
            "studentEmail": s.studentEmail,
            "studentName": s.studentName,
            "surahName": s.surahName,
            "score": s.score,
            "totalQuestions": s.totalQuestions,
            "percentage": s.percentage,
            "passed": s.passed,
            "createdAt": s.createdAt.isoformat() if s.createdAt else "",
        }
        for s in scores
    ]
