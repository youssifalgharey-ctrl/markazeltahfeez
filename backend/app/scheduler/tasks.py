import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import SessionLocal
from app.models.subscription import CourseSubscription
from app.services.email_service import send_expiration_warning_email
from app.services.leaderboard_service import refresh_current_week

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def check_expiring_and_expired_subscriptions():
    logger.info("Running scheduled check for expiring and expired subscriptions...")
    db = SessionLocal()
    try:
        now = datetime.now()
        three_days = now + timedelta(days=3)

        # 1. Expiring soon (within 3 days)
        expiring_soon = (
            db.query(CourseSubscription)
            .filter(
                CourseSubscription.status == "ACTIVATED",
                CourseSubscription.warningSent == False,
                CourseSubscription.expiresAt.isnot(None),
                CourseSubscription.expiresAt > now,
                CourseSubscription.expiresAt <= three_days,
            )
            .all()
        )

        for sub in expiring_soon:
            try:
                sent = send_expiration_warning_email(sub)
                if sent:
                    sub.warningSent = True
                    db.commit()
                    logger.info("Sent expiration warning for student %s (ends %s)", sub.studentName, sub.expiresAt)
            except Exception as e:
                logger.error("Failed to send expiration warning for %s: %s", sub.studentName, e)

        # 2. Expired subscriptions
        expired = (
            db.query(CourseSubscription)
            .filter(
                CourseSubscription.status == "ACTIVATED",
                CourseSubscription.expiresAt.isnot(None),
                CourseSubscription.expiresAt <= now,
            )
            .all()
        )

        for sub in expired:
            sub.status = "EXPIRED"
            logger.info("Marked subscription ID %s as EXPIRED for student %s", sub.id, sub.studentName)
        db.commit()

        # 3. Refresh leaderboard
        refresh_current_week(db)
    except Exception as e:
        logger.error("Error running scheduled background task: %s", e)
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(
        check_expiring_and_expired_subscriptions,
        "interval",
        hours=1,
        id="subscription_and_leaderboard_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started successfully.")
