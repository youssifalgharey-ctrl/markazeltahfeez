import re
import urllib.parse
import logging
from datetime import datetime, date, time, timedelta
from app.config import settings
from app.models.booking import IjazaBooking

logger = logging.getLogger(__name__)

def parse_session_date_time(booking: IjazaBooking):
    d = date.today()
    start_time = time(18, 0)  # Default 6:00 PM

    if booking.appointmentDate:
        raw_date = booking.appointmentDate.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_date):
            try:
                d = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except Exception:
                pass
        elif re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", raw_date):
            try:
                parts = raw_date.split("/")
                d = date(int(parts[2]), int(parts[1]), int(parts[0]))
            except Exception:
                pass

    if booking.appointmentTime:
        raw_time = booking.appointmentTime.strip()
        m = re.search(r"(\d{1,2}):(\d{2})", raw_time)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))
            if ("مساء" in raw_time or "PM" in raw_time.upper()) and hour < 12:
                hour += 12
            elif ("صباح" in raw_time or "AM" in raw_time.upper()) and hour == 12:
                hour = 0
            start_time = time(hour, minute)

    start_dt = datetime.combine(d, start_time)
    end_dt = start_dt + timedelta(hours=1)
    return start_dt, end_dt

def generate_google_calendar_url(booking: IjazaBooking) -> str:
    try:
        start_dt, end_dt = parse_session_date_time(booking)
        dates_param = f"{start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}"

        track = booking.trackName or "جلسة قرآنية"
        title = f"جلسة قرآنية: {booking.studentName} ({track})"
        location = booking.sessionMode or "أونلاين عبر Google Meet / Zoom"

        desc = (
            "مركز تحفيظ القرآن الكريم بأسريجه\n"
            f"• الطالب: {booking.studentName}\n"
        )
        if booking.userCode:
            desc += f"• كود الطالب: {booking.userCode}\n"
        desc += (
            f"• هاتف/واتساب: {booking.studentPhone}\n"
            f"• الشيخ المحفّظ: {booking.sheikhName}\n"
            f"• المسار: {track}\n"
        )
        if booking.riwayah:
            desc += f"• الرواية: {booking.riwayah}\n"
        desc += f"• كود الحجز: {booking.bookingReference}\n"

        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": dates_param,
            "details": desc,
            "location": location,
            "add": settings.PAYMENT_ADMIN_EMAIL,
        }
        return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"
    except Exception as ex:
        logger.error("Error creating Google Calendar URL: %s", ex)
        return "https://calendar.google.com/"

def generate_ics_content(booking: IjazaBooking) -> str:
    start_dt, end_dt = parse_session_date_time(booking)
    start_str = start_dt.strftime("%Y%m%dT%H%M%S")
    end_str = end_dt.strftime("%Y%m%dT%H%M%S")
    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    track = booking.trackName or "جلسة قرآنية"
    title = f"جلسة قرآنية: {booking.studentName} ({track})"
    location = booking.sessionMode or "Google Meet / Zoom"

    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Markaz El Tafeez//Quran Booking//AR\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:REQUEST\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{booking.bookingReference}@markazeltafeez.com\r\n"
        f"DTSTAMP:{now_str}\r\n"
        f"DTSTART:{start_str}\r\n"
        f"DTEND:{end_str}\r\n"
        f"SUMMARY:{title}\r\n"
        f"DESCRIPTION:جلسة قرآنية مع فضيلة الشيخ {booking.sheikhName} - الطالب: {booking.studentName} ({booking.studentPhone})\r\n"
        f"LOCATION:{location}\r\n"
        f"ORGANIZER;CN=مركز تحفيظ القرآن الكريم:mailto:{settings.PAYMENT_ADMIN_EMAIL}\r\n"
        f"ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN=إدارة المركز:mailto:{settings.PAYMENT_ADMIN_EMAIL}\r\n"
        "STATUS:CONFIRMED\r\n"
        "TRANSP:OPAQUE\r\n"
        "SEQUENCE:0\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
