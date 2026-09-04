import json
import logging
from datetime import datetime
from typing import List, Tuple, Any, Dict
import httpx
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.models.beginner_plan import BeginnerPlan
from app.schemas.plan import BeginnerPlanRequest, BeginnerPlanResponse, BeginnerPlanItem

logger = logging.getLogger(__name__)

SURAH_POOL = [
    # Stage 1: Short surahs
    ("الفاتحة", "fa-solid fa-book-quran"),
    ("الناس", "fa-solid fa-mosque"),
    ("الفلق", "fa-solid fa-mosque"),
    ("الإخلاص", "fa-solid fa-mosque"),
    ("المسد", "fa-solid fa-mosque"),
    ("النصر", "fa-solid fa-mosque"),
    ("الكافرون", "fa-solid fa-mosque"),
    ("الكوثر", "fa-solid fa-mosque"),
    ("الماعون", "fa-solid fa-mosque"),
    ("قريش", "fa-solid fa-mosque"),
    ("الفيل", "fa-solid fa-mosque"),
    ("الهمزة", "fa-solid fa-mosque"),
    ("العصر", "fa-solid fa-mosque"),
    ("التكاثر", "fa-solid fa-mosque"),
    ("القارعة", "fa-solid fa-mosque"),
    ("العاديات", "fa-solid fa-mosque"),
    ("الزلزلة", "fa-solid fa-mosque"),
    ("البينة", "fa-solid fa-mosque"),
    ("القدر", "fa-solid fa-mosque"),
    ("العلق", "fa-solid fa-mosque"),
    ("التين", "fa-solid fa-mosque"),
    ("الشرح", "fa-solid fa-mosque"),
    ("الضحى", "fa-solid fa-mosque"),
    # Stage 2: Medium Juz Amma
    ("الليل", "fa-solid fa-mosque"),
    ("الشمس", "fa-solid fa-mosque"),
    ("البلد", "fa-solid fa-mosque"),
    ("الفجر", "fa-solid fa-mosque"),
    ("الغاشية", "fa-solid fa-mosque"),
    ("الأعلى", "fa-solid fa-mosque"),
    ("الطارق", "fa-solid fa-mosque"),
    ("البروج", "fa-solid fa-mosque"),
    ("الانشقاق", "fa-solid fa-mosque"),
    # Stage 3: Long Juz Amma
    ("المطففين", "fa-solid fa-book-quran"),
    ("الانفطار", "fa-solid fa-book-quran"),
    ("التكوير", "fa-solid fa-book-quran"),
    ("عبس", "fa-solid fa-book-quran"),
    ("النازعات", "fa-solid fa-book-quran"),
    ("النبأ", "fa-solid fa-book-quran"),
    # Stage 4: Juz Tabarak
    ("المرسلات", "fa-solid fa-star-and-crescent"),
    ("الإنسان", "fa-solid fa-star-and-crescent"),
    ("القيامة", "fa-solid fa-star-and-crescent"),
    ("المدثر", "fa-solid fa-star-and-crescent"),
    ("المزمل", "fa-solid fa-star-and-crescent"),
    ("الجن", "fa-solid fa-star-and-crescent"),
    ("نوح", "fa-solid fa-star-and-crescent"),
    ("المعارج", "fa-solid fa-star-and-crescent"),
    ("الحاقة", "fa-solid fa-star-and-crescent"),
    ("القلم", "fa-solid fa-star-and-crescent"),
    ("الملك", "fa-solid fa-star-and-crescent"),
]

def build_fallback_plan(req: BeginnerPlanRequest) -> Tuple[str, str, List[BeginnerPlanItem], List[str]]:
    prior = req.priorMemorization
    start_idx = 0
    if prior == "juz_amma_half":
        start_idx = 17
    elif prior == "juz_amma_full":
        start_idx = 38
    elif prior == "few_surahs":
        start_idx = 7

    count = 10 if req.minutesPerDay >= 30 else 7
    schedule = []
    order = 0
    for i in range(start_idx, min(start_idx + count, len(SURAH_POOL))):
        name, icon = SURAH_POOL[i]
        schedule.append(BeginnerPlanItem(
            order=order,
            surahName=name,
            description=f"احفظ سورة {name} جيداً ثم سمّعها للشيخ قبل الانتقال للتالية",
            icon=icon,
            completed=False
        ))
        order += 1

    title = "خطة قصار السور للمبتدئين"
    subtitle = "صُممت خصيصاً لمستوى حفظك لتبدأ بالتدرج السلس"
    tips = [
        "استمع لتلاوة السورة بصوت الشيخ الحصري أو المنشاوي 3 مرات قبل البدء في الحفظ.",
        "احفظ آية آية، ولا تنتقل لآية جديدة حتى تكرر السابقة 10 مرات غيباً.",
        "سمّع السورة كاملة للشيخ في حلقتك قبل الانتقال للسورة التالية.",
    ]
    return title, subtitle, schedule, tips

async def call_gemini(req: BeginnerPlanRequest) -> Tuple[str, str, List[BeginnerPlanItem], List[str]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    prompt = (
        "أنت معلم قرآن متخصص في مسار قصار السور للمبتدئين بمركز تحفيظ القرآن الكريم بأسريجه.\n"
        f"بيانات الطالب: الفئة العمرية ({req.ageGroup})، مقدار الحفظ السابق ({req.priorMemorization})، "
        f"مستوى القدرة ({req.ability})، الوقت المتاح يومياً ({req.minutesPerDay} دقيقة)، طريقة المتابعة ({req.followUp}).\n"
        "صمم خطة متدرجة من 7 إلى 10 سور مناسبة تماماً لمستواه من قصار السور.\n"
        "رجع النتيجة بصيغة JSON فقط بهذا الشكل:\n"
        "{\n"
        '  "title": "عنوان الخطة",\n'
        '  "subtitle": "وصف فرعي",\n'
        '  "schedule": [ {"order": 0, "surahName": "الفاتحة", "description": "وصف التسميع", "icon": "fa-solid fa-book-quran"} ],\n'
        '  "tips": [ "نصيحة 1", "نصيحة 2" ]\n'
        "}"
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    plan_json = json.loads(text)

    schedule = [
        BeginnerPlanItem(
            order=idx,
            surahName=item.get("surahName", ""),
            description=item.get("description", ""),
            icon=item.get("icon", "fa-solid fa-mosque"),
            completed=False
        )
        for idx, item in enumerate(plan_json.get("schedule", []))
    ]
    tips = [str(t) for t in plan_json.get("tips", [])]
    return plan_json.get("title", "خطة قصار السور للمبتدئين"), plan_json.get("subtitle", "خطة مخصصة لتثبيت الحفظ"), schedule, tips

def to_response(plan: BeginnerPlan) -> BeginnerPlanResponse:
    schedule_data = json.loads(plan.scheduleJson) if plan.scheduleJson else []
    tips_data = json.loads(plan.tipsJson) if plan.tipsJson else []
    completed_data = json.loads(plan.completedJson) if plan.completedJson else []

    completed_map = {item.get("order"): item.get("completedAt") for item in completed_data}

    schedule = []
    for item in schedule_data:
        order = item.get("order", 0)
        is_completed = order in completed_map
        schedule.append(BeginnerPlanItem(
            order=order,
            surahName=item.get("surahName", ""),
            description=item.get("description", ""),
            icon=item.get("icon", "fa-solid fa-mosque"),
            completed=is_completed,
            completedAt=completed_map.get(order)
        ))

    return BeginnerPlanResponse(
        hasPlan=True,
        title=plan.title,
        subtitle=plan.subtitle,
        totalItems=plan.totalItems,
        currentIndex=plan.currentIndex,
        completedCount=len(completed_map),
        schedule=schedule,
        tips=tips_data,
        aiGenerated=plan.aiGenerated,
        createdAt=plan.createdAt.isoformat() if plan.createdAt else None,
    )

async def generate_and_save(user: User, req: BeginnerPlanRequest, db: Session) -> BeginnerPlanResponse:
    ai_generated = False
    if settings.GEMINI_API_KEY and "ضع_هنا" not in settings.GEMINI_API_KEY:
        try:
            title, subtitle, schedule, tips = await call_gemini(req)
            ai_generated = True
        except Exception as e:
            logger.error("Beginner plan Gemini failed: %s", e)
            title, subtitle, schedule, tips = build_fallback_plan(req)
    else:
        title, subtitle, schedule, tips = build_fallback_plan(req)

    plan = db.query(BeginnerPlan).filter(BeginnerPlan.user_id == user.id).first()
    if not plan:
        plan = BeginnerPlan(user_id=user.id)
        db.add(plan)

    plan.ageGroup = req.ageGroup
    plan.priorMemorization = req.priorMemorization
    plan.ability = req.ability
    plan.minutesPerDay = req.minutesPerDay
    plan.followUp = req.followUp
    plan.title = title
    plan.subtitle = subtitle
    plan.totalItems = len(schedule)
    plan.currentIndex = 0
    plan.completedJson = "[]"
    plan.aiGenerated = ai_generated
    plan.scheduleJson = json.dumps([item.dict() for item in schedule], ensure_ascii=False)
    plan.tipsJson = json.dumps(tips, ensure_ascii=False)

    db.commit()
    db.refresh(plan)
    return to_response(plan)

def get_my_plan(user: User, db: Session) -> BeginnerPlanResponse:
    plan = db.query(BeginnerPlan).filter(BeginnerPlan.user_id == user.id).first()
    if not plan:
        return BeginnerPlanResponse(hasPlan=False)
    return to_response(plan)

def mark_complete(user: User, order: int, db: Session) -> BeginnerPlanResponse:
    plan = db.query(BeginnerPlan).filter(BeginnerPlan.user_id == user.id).first()
    if not plan:
        raise ValueError("لسه معملتش خطة حفظ، ابدأ بالإجابة على الأسئلة أولاً")

    if order != plan.currentIndex:
        raise ValueError("لازم تكمل عناصر الخطة بترتيبها، ابدأ بالعنصر الحالي أولاً")

    if order >= plan.totalItems:
        raise ValueError("خلّصت كل عناصر الخطة بالفعل، مبروك!")

    completed_list = json.loads(plan.completedJson) if plan.completedJson else []
    completed_list.append({
        "order": order,
        "completedAt": datetime.now().isoformat()
    })

    plan.completedJson = json.dumps(completed_list, ensure_ascii=False)
    plan.currentIndex = order + 1
    db.commit()
    db.refresh(plan)
    return to_response(plan)

def advance_to_next_stage(user: User, db: Session) -> BeginnerPlanResponse:
    plan = db.query(BeginnerPlan).filter(BeginnerPlan.user_id == user.id).first()
    if not plan:
        raise ValueError("لا توجد خطة سابقة للانتقال منها، ابدأ بتوليد خطة أولاً")

    old_schedule = json.loads(plan.scheduleJson) if plan.scheduleJson else []
    completed_names = [item.get("surahName") for item in old_schedule if item.get("surahName")]

    last_idx = -1
    for name in completed_names:
        for idx, (s_name, _) in enumerate(SURAH_POOL):
            if s_name in name:
                last_idx = max(last_idx, idx)

    next_start = (last_idx + 1) if last_idx >= 0 else 23
    if next_start >= len(SURAH_POOL):
        next_start = 0

    schedule = []
    order = 0
    for i in range(next_start, min(next_start + 10, len(SURAH_POOL))):
        s_name, icon = SURAH_POOL[i]
        schedule.append(BeginnerPlanItem(
            order=order,
            surahName=s_name,
            description=f"احفظ سورة {s_name} جيداً ثم سمّعها للشيخ قبل الانتقال للتالية",
            icon=icon,
            completed=False
        ))
        order += 1

    stage_title = (
        "خطة جزء تبارك" if next_start >= 38
        else ("خطة طوال جزء عمّ" if next_start >= 32
        else ("خطة متوسطات جزء عمّ" if next_start >= 23 else "خطة قصار السور"))
    )

    plan.title = stage_title
    plan.subtitle = "مرحلة جديدة مرتبة تصاعدياً لمواصلة الحفظ خطوة بخطوة مع الشيخ"
    plan.totalItems = len(schedule)
    plan.currentIndex = 0
    plan.completedJson = "[]"
    plan.aiGenerated = False
    plan.scheduleJson = json.dumps([item.dict() for item in schedule], ensure_ascii=False)

    db.commit()
    db.refresh(plan)
    return to_response(plan)
