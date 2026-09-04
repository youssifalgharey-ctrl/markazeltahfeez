import json
import logging
import math
import httpx
from typing import Optional, List
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.models.plan import Plan
from app.schemas.plan import PlanRequest, PlanResponse, PlanScheduleItem

logger = logging.getLogger(__name__)

def build_prompt(req: PlanRequest) -> str:
    return (
        "أنت مساعد متخصص في تصميم خطط حفظ القرآن الكريم الشخصية بمركز تحفيظ القرآن الكريم بأسريجه.\n"
        "بيانات الطالب:\n"
        f"- عدد الصفحات المحفوظة حالياً: {req.memorizedPages} من أصل 604\n"
        f"- الوقت المتاح للحفظ يومياً: {req.minutesPerDay} دقيقة\n"
        f"- الهدف: {req.goal} (khatm=ختم كامل، part=حفظ جزء مميز، review=مراجعة وتثبيت، tajweed=تحسين التلاوة)\n"
        f"- مستوى القدرة على الحفظ: {req.ability} (excellent=ممتاز، good=جيد، slow=بطيء، help=محتاج مساعدة)\n"
        f"- الوقت المفضل للحفظ: {req.timing} (fajr=بعد الفجر، noon=بين الظهر والعصر، evening=بعد العصر، night=بعد العشاء)\n"
        f"- عدد الأيام اللي يقدر يلتزم بيها في الأسبوع: {req.daysPerWeek} من أصل 7\n"
        f"- طريقة الحفظ: {req.followUp} (alone=بمفرده، teacher=مع معلم، group=مع مجموعة أو حلقة، family=مع الأسرة)\n"
        f"- أهم تحدياته: {req.challenge} (forgetting=النسيان السريع، time=ضيق الوقت، motivation=قلة التحفيز، tajweed_hard=صعوبة التجويد)\n\n"
        "مسارات المنصة المتاحة للترشيح:\n"
        "1. مسار قصار السور للمبتدئين (للمبتدئين ومن يحفظ من الصفر أو لديه صعوبة أو وقته قليل)\n"
        "2. مسار إتقان التجويد والترتيل (لمن هدفه التجويد أو يواجه صعوبة في أحكام التلاوة ومخارج الحروف)\n"
        "3. مسار أصول الدين (للتأصيل العقدي ومصاحبة الحفظ بفهم العقيدة وأصول الإيمان)\n"
        "4. مسار الفقه (لتعلم فقه العبادات والطهارة والصلاة مع الحفظ)\n"
        "5. مسار المتون (لمن حفظ قدراً طيباً ويريد ضبط متون التجويد كتحفة الأطفال والجزرية)\n"
        "6. مسار الدورة الصيفية للحفظ المكثف (لمن وقته كبير 60+ دقيقة ويريد إنجازاً مكثفاً)\n\n"
        "المطلوب: خطة حفظ أسبوعية واقعية ومحفزة، مكتوبة بالعربية الفصحى المبسطة، تراعي كل البيانات.\n"
        "يجب أن تتضمن قائمة النصائح (tips) كأول نصيحة: ترشيح مسار محدد ومناسب جداً من مسارات المنصة الـ 6 المذكورة أعلاه مع بيان واضح لسبب الترشيح.\n"
        "رجّع النتيجة بصيغة JSON فقط وبالضبط بهذا الشكل، بدون أي نص إضافي قبله أو بعده:\n"
        "{\n"
        '  "title": "عنوان قصير للخطة",\n'
        '  "subtitle": "جملة قصيرة توضح أساس الخطة",\n'
        '  "pagesPerDay": "عدد الصفحات الجديدة يومياً كنص، مثال: 1 أو ½ أو ¼",\n'
        '  "monthsToKhatm": "عدد الشهور المتوقعة للختم كنص، أو -- لو غير منطبق",\n'
        '  "schedule": [ { "icon": "fa-solid fa-book-open", "title": "عنوان بند الجدول", "desc": "وصف قصير للبند" } ],\n'
        '  "tips": [ "نرشح لك مسار (اسم المسار)؛ مع سبب الترشيح وكيف يفيدك", "نصيحة عملية 1", "نصيحة عملية 2" ]\n'
        "}\n"
        'اجعل "schedule" من 2 إلى 5 بنود تناسب الهدف وعدد أيام الالتزام والوقت المتاح، و"tips" من 3 إلى 4 نصائح فقط.'
    )

def build_fallback_plan(req: PlanRequest) -> PlanResponse:
    memorized = req.memorizedPages or 0
    minutes_day = req.minutesPerDay or 30
    goal = req.goal or "khatm"
    ability = req.ability or "good"
    timing = req.timing or "fajr"
    days_week = req.daysPerWeek or 6
    challenge = req.challenge or "forgetting"
    follow_up = req.followUp or "alone"

    if minutes_day <= 15:
        base_pages = 0.5
    elif minutes_day <= 30:
        base_pages = 1.0
    elif minutes_day <= 60:
        base_pages = 2.0
    else:
        base_pages = 3.0

    ability_factor = {
        "excellent": 1.5,
        "good": 1.0,
        "slow": 0.6,
        "help": 0.4,
    }
    base_pages = max(0.25, base_pages * ability_factor.get(ability, 1.0))

    review_pages = 0
    if goal == "review":
        review_pages = int(round(base_pages * 2))
        base_pages = round(base_pages * 0.5)

    if base_pages < 0.5:
        pages_rounded = "¼"
    elif base_pages < 1.0:
        pages_rounded = "½"
    else:
        pages_rounded = str(int(round(base_pages)))

    remaining = 604 - memorized
    effective_per_week = (base_pages if base_pages != 0 else 0.5) * days_week
    weeks_to_finish = remaining / (effective_per_week if effective_per_week != 0 else 0.5)
    months_to_finish = math.ceil(weeks_to_finish / 4.345)

    timing_labels = {
        "fajr": "بعد صلاة الفجر",
        "noon": "بين الظهر والعصر",
        "evening": "بعد صلاة العصر",
        "night": "بعد صلاة العشاء",
    }

    schedule = []
    if goal != "review":
        schedule.append(PlanScheduleItem(
            icon="fa-solid fa-book-open",
            title=f"حفظ جديد — {timing_labels.get(timing, '')}",
            desc=f"احفظ {pages_rounded} صفحة يومياً في وقت صفاء الذهن",
        ))

    if memorized > 0 or goal == "review":
        rev_desc = f"راجع {review_pages} صفحات من حفظك السابق يومياً" if review_pages > 0 else "خصص 10 دقائق لمراجعة آخر ما حفظته"
        schedule.append(PlanScheduleItem(
            icon="fa-solid fa-rotate",
            title="مراجعة — " + ("بعد صلاة العشاء" if timing == "fajr" else "بعد صلاة الفجر"),
            desc=rev_desc,
        ))

    if minutes_day >= 60:
        schedule.append(PlanScheduleItem(
            icon="fa-solid fa-headphones",
            title="استماع مكثف — في أي وقت",
            desc="استمع لتلاوة ما تحفظه ليتثبت في ذاكرتك",
        ))

    schedule.append(PlanScheduleItem(
        icon="fa-solid fa-calendar-week",
        title="يوم المراجعة الأسبوعي — الجمعة",
        desc="يوم مراجعة شامل لما حفظته طوال الأسبوع",
    ))

    tips = []
    if goal == "tajweed" or challenge == "tajweed_hard":
        tips.append("🌟 نرشح لك مسار «إتقان التجويد والترتيل» بالمنصة لضبط مخارج الحروف وأحكام التلاوة النظرية والتطبيقية.")
    elif memorized == 0 or ability in ("help", "slow") or goal == "part":
        tips.append("🌟 نرشح لك مسار «قصار السور للمبتدئين» بالمنصة لبدء رحلة الحفظ الممنهجة خطوة بخطوة وبناء عادة يومية متينة.")
    elif minutes_day >= 60 and (goal == "khatm" or ability == "excellent"):
        tips.append("🌟 نرشح لك مسار «الدورة الصيفية للحفظ المكثف» بالمنصة لاستثمار وقتك في إنجاز خطة حفظ سريعة ومنضبطة.")
    elif memorized >= 300:
        tips.append("🌟 نرشح لك مسار «المتون التجويدية» بالمنصة لضبط منظومات التجويد كتحفة الأطفال والجزرية وتأهيلك للإجازة.")
    else:
        tips.append("🌟 نرشح لك مسار «أصول الدين» بالمنصة لمصاحبة حفظك لكتاب الله بتأصيل عقدي راسخ وفهم أركان الإيمان.")

    if ability in ("slow", "help"):
        tips.append("ابدأ بسور قصيرة وسهلة مثل سور جزء عمّ — الثقة أهم من السرعة.")
        tips.append("كرر الآية الواحدة من 20 إلى 30 مرة بصوت عالٍ قبل الانتقال للتالية.")
    if goal == "khatm":
        tips.append("الانتظام يومياً أهم من الكثرة — يوم واحد بلا حفظ يضيّع أسبوعاً من التثبيت.")
    if timing == "fajr":
        tips.append("وقت الفجر من أفضل أوقات الحفظ — الذاكرة في أوج نشاطها بعد النوم.")
    if timing == "night":
        tips.append("الحفظ قبل النوم يثبت في الذاكرة طويلة الأمد بشكل أفضل.")

    goal_titles = {
        "khatm": "خطة ختم القرآن الكريم",
        "part": "خطة حفظ جزء مميز",
        "review": "خطة المراجعة والتثبيت",
        "tajweed": "خطة تحسين التلاوة والتجويد",
    }

    return PlanResponse(
        hasPlan=True,
        title=goal_titles.get(goal, "خطة الحفظ الشخصية"),
        subtitle="صُممت بناءً على إجاباتك لتناسب جدولك اليومي",
        pagesPerDay=pages_rounded,
        minutesPerDay=minutes_day,
        monthsToKhatm=str(months_to_finish) if goal == "khatm" else ("3-6" if goal == "part" else "—"),
        schedule=schedule,
        tips=tips[:4],
        aiGenerated=False,
    )

async def call_gemini(req: PlanRequest) -> PlanResponse:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    prompt = build_prompt(req)

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4,
        },
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    plan_json = json.loads(text)

    schedule = [
        PlanScheduleItem(
            icon=item.get("icon", "fa-solid fa-book-open"),
            title=item.get("title", ""),
            desc=item.get("desc", ""),
        )
        for item in plan_json.get("schedule", [])
    ]

    tips = [str(tip) for tip in plan_json.get("tips", [])]

    return PlanResponse(
        hasPlan=True,
        title=plan_json.get("title", "خطة الحفظ الشخصية"),
        subtitle=plan_json.get("subtitle", "صُممت بناءً على إجاباتك لتناسب جدولك اليومي"),
        pagesPerDay=str(plan_json.get("pagesPerDay", "1")),
        minutesPerDay=req.minutesPerDay,
        monthsToKhatm=str(plan_json.get("monthsToKhatm", "—")),
        schedule=schedule,
        tips=tips,
        aiGenerated=True,
    )

async def generate_plan(req: PlanRequest) -> PlanResponse:
    if settings.GEMINI_API_KEY and "ضع_هنا" not in settings.GEMINI_API_KEY:
        try:
            return await call_gemini(req)
        except Exception as e:
            logger.error("Gemini API call failed, using fallback plan: %s", e)
    return build_fallback_plan(req)

async def generate_and_save(user: User, req: PlanRequest, db: Session) -> PlanResponse:
    generated = await generate_plan(req)

    plan = db.query(Plan).filter(Plan.user_id == user.id).first()
    if not plan:
        plan = Plan(user_id=user.id)
        db.add(plan)

    plan.memorizedPages = req.memorizedPages or 0
    plan.minutesPerDay = req.minutesPerDay or 30
    plan.goal = req.goal or "khatm"
    plan.ability = req.ability or "good"
    plan.timing = req.timing or "fajr"
    plan.daysPerWeek = req.daysPerWeek
    plan.followUp = req.followUp
    plan.challenge = req.challenge
    plan.title = generated.title
    plan.subtitle = generated.subtitle
    plan.pagesPerDay = generated.pagesPerDay
    plan.monthsToKhatm = generated.monthsToKhatm
    plan.scheduleJson = json.dumps([item.dict() for item in generated.schedule], ensure_ascii=False)
    plan.tipsJson = json.dumps(generated.tips, ensure_ascii=False)
    plan.aiGenerated = generated.aiGenerated

    db.commit()
    db.refresh(plan)
    generated.createdAt = plan.createdAt.isoformat() if plan.createdAt else None
    return generated

def get_my_plan(user: User, db: Session) -> PlanResponse:
    plan = db.query(Plan).filter(Plan.user_id == user.id).first()
    if not plan:
        return PlanResponse(hasPlan=False)

    schedule_data = json.loads(plan.scheduleJson) if plan.scheduleJson else []
    tips_data = json.loads(plan.tipsJson) if plan.tipsJson else []

    schedule = [PlanScheduleItem(**item) for item in schedule_data]

    return PlanResponse(
        hasPlan=True,
        title=plan.title,
        subtitle=plan.subtitle,
        pagesPerDay=plan.pagesPerDay,
        minutesPerDay=plan.minutesPerDay,
        monthsToKhatm=plan.monthsToKhatm,
        schedule=schedule,
        tips=tips_data,
        aiGenerated=plan.aiGenerated,
        createdAt=plan.createdAt.isoformat() if plan.createdAt else None,
    )

def delete_plan(user: User, db: Session):
    plan = db.query(Plan).filter(Plan.user_id == user.id).first()
    if plan:
        db.delete(plan)
        db.commit()
