import os
import re
import smtplib
import base64
import html
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import urllib.parse
from app.config import settings
from app.models.subscription import CourseSubscription
from app.models.booking import IjazaBooking
from app.services.google_calendar import (
    generate_google_calendar_url,
    generate_ics_content,
)

logger = logging.getLogger(__name__)

def _send_smtp_message(to_address: str, subject: str, msg: MIMEMultipart) -> bool:
    if not settings.MAIL_PASSWORD or not settings.MAIL_USERNAME:
        logger.warning("SMTP credentials not set, skipping email dispatch.")
        return False
    try:
        msg["From"] = f"منصة مركز تحفيظ القرآن الكريم بأسريجه <{settings.MAIL_USERNAME}>"
        msg["To"] = to_address
        msg["Subject"] = subject

        with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT, timeout=15) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
        logger.info("Sent email to %s: %s", to_address, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_address, e)
        return False

def sanitize_phone(phone: str) -> str:
    if not phone:
        return ""
    clean = re.sub(r"[^0-9]", "", phone)
    if clean.startswith("0"):
        clean = clean[1:]
    return clean

def send_password_reset_email(to_email: str, student_name: str, new_password: str) -> bool:
    safe_name = html.escape(student_name or "طالب القرآن الكريم")
    safe_password = html.escape(new_password)
    subject = "🔐 استعادة كلمة المرور - منصة مركز تحفيظ القرآن الكريم بأسريجه"

    html_content = f"""
    <div dir='rtl' style='font-family: Arial, Tahoma, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 16px;'>
        <div style='text-align: center; border-bottom: 2px solid #059669; padding-bottom: 16px; margin-bottom: 20px;'>
            <h2 style='color: #065f46; margin: 0 0 6px 0; font-size: 22px;'>مركز تحفيظ القرآن الكريم بأسريجه</h2>
            <p style='color: #64748b; font-size: 14px; margin: 0;'>منصة تعليم وحفظ كتاب الله وتجويده</p>
        </div>

        <div style='background: #ffffff; border-radius: 12px; padding: 24px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>
            <h3 style='color: #0f172a; margin-top: 0; font-size: 18px;'>السلام عليكم ورحمة الله وبركاته، أهلاً بك يا {safe_name} 👋</h3>
            <p style='color: #334155; font-size: 14.5px; line-height: 1.7;'>
                لقد تلقينا طلباً لاستعادة كلمة المرور الخاصة بحسابك على منصة المركز. تم إنشاء كلمة مرور جديدة ومؤقتة لحسابك:
            </p>

            <div style='background: #ecfdf5; border: 2px dashed #059669; border-radius: 10px; padding: 18px; text-align: center; margin: 20px 0;'>
                <span style='font-size: 13px; color: #047857; display: block; margin-bottom: 6px; font-weight: bold;'>كلمة المرور الجديدة الخاصة بك:</span>
                <span style='font-size: 26px; font-weight: 900; color: #065f46; letter-spacing: 2px; font-family: monospace;'>{safe_password}</span>
            </div>

            <p style='color: #64748b; font-size: 13.5px; line-height: 1.6;'>
                💡 <strong>نصيحة أمنية:</strong> يمكنك الآن تسجيل الدخول باستخدام بريدك الإلكتروني وهذه الكلمة، ثم التوجه إلى صفحة تعديل الحساب لتغييرها إلى كلمة المرور المفضلة لديك.
            </p>

            <div style='text-align: center; margin-top: 24px;'>
                <a href='{settings.SERVER_BASE_URL}/index.html' target='_blank' style='display: inline-block; background: #059669; color: #ffffff; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: bold; font-size: 15px;'>
                    🚀 تسجيل الدخول إلى المنصة الآن
                </a>
            </div>
        </div>

        <div style='text-align: center; margin-top: 20px; font-size: 12px; color: #94a3b8;'>
            إذا لم تكن أنت من قام بهذا الطلب، يرجى التواصل مع إدارة المركز فوراً.
        </div>
    </div>
    """
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    return _send_smtp_message(to_email, subject, msg)

def send_payment_notification_email(sub: CourseSubscription, receipt_base64: str = None) -> bool:
    subject = f"🔔 إشعار دفع جديد: {sub.studentName} ({sub.studentPhone})"
    time_now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    activation_url = f"{settings.SERVER_BASE_URL}/api/payment/activate?token={sub.activationToken}"

    methods_ar = {
        "vodafone": "فودافون كاش / المحافظ الإلكترونية",
        "instapay": "إنستاباي InstaPay",
        "kuttab": "الدفع في الكُتّاب / المركز",
        "center": "الدفع في الكُتّاب / المركز",
        "fawry": "فوري Fawry Pay",
        "card": "بطاقة بنكية (فيزا / ماستركارد)",
    }
    payment_method_name = methods_ar.get(sub.paymentMethod, sub.paymentMethod or "غير محدد")
    clean_phone = sanitize_phone(sub.studentPhone)

    msg = MIMEMultipart("related")
    alt_part = MIMEMultipart("alternative")
    msg.attach(alt_part)

    html_content = f"""
    <div dir='rtl' style='font-family: Arial, Tahoma, sans-serif; background-color: #f0fdf4; padding: 24px; color: #1e293b; max-width: 650px; margin: auto; border: 2px solid #10b981; border-radius: 16px;'>
        <div style='text-align: center; border-bottom: 2px solid #10b981; padding-bottom: 16px; margin-bottom: 20px;'>
            <h2 style='color: #065f46; margin: 0 0 6px 0; font-size: 22px;'>مركز تحفيظ القرآن الكريم بأسريجه</h2>
            <h3 style='color: #059669; margin: 0; font-size: 18px;'>🔔 إشعار استلام دفع واشتراك دورة جديد</h3>
            <p style='color: #64748b; font-size: 13px; margin-top: 6px;'>تاريخ العملية: {time_now}</p>
        </div>

        <div style='background: #ecfdf5; border: 2px dashed #059669; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 24px;'>
            <p style='margin: 0 0 10px 0; font-size: 15px; font-weight: bold; color: #065f46;'>بعد التأكد من صورة الإيصال ورقم التحويل، اضغط الزر أدناه لتفعيل الاشتراك فورياً:</p>
            <a href='{activation_url}' target='_blank' style='display: inline-block; background-color: #059669; color: #ffffff; padding: 14px 32px; font-size: 17px; font-weight: 800; text-decoration: none; border-radius: 10px; box-shadow: 0 4px 14px rgba(5, 150, 105, 0.4);'>
                ⚡ اضغط هنا لتفعيل اشتراك الطالب فوراً
            </a>
            <p style='margin: 8px 0 0 0; font-size: 12px; color: #64748b;'>رابط التفعيل المباشر: <a href='{activation_url}' style='color: #059669;'>{activation_url}</a></p>
        </div>

        <h4 style='color: #065f46; margin-bottom: 8px; font-size: 16px;'>👤 بيانات الطالب ورقم الهاتف:</h4>
        <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1;'>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>اسم الطالب:</td><td style='padding: 10px 14px;'><strong>{sub.studentName}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>رقم الهاتف / الواتساب:</td><td style='padding: 10px 14px;'><a href='https://wa.me/2{clean_phone}' style='color: #059669; font-weight: 800;'>📱 {sub.studentPhone} (واتساب)</a></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>كود الطالب بالمركز:</td><td style='padding: 10px 14px;'>{sub.userCode or 'غير مدخل'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>البريد الإلكتروني:</td><td style='padding: 10px 14px;'>{sub.studentEmail or 'غير مسجل'}</td></tr>
        </table>

        <h4 style='color: #065f46; margin-bottom: 8px; font-size: 16px;'>💳 تفاصيل الدورة والتحويل:</h4>
        <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1;'>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>الدورة / الباقة:</td><td style='padding: 10px 14px;'><strong>{sub.courseTitle or '-'}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>تفاصيل الباقة:</td><td style='padding: 10px 14px;'>{sub.courseSubtitle or '-'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>مدة الاشتراك:</td><td style='padding: 10px 14px;'>{sub.durationDays or 90} يوم</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>المبلغ المطلوب:</td><td style='padding: 10px 14px; color: #059669; font-weight: bold;'>{sub.amount or '-'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>طريقة الدفع:</td><td style='padding: 10px 14px;'>{payment_method_name}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>بيانات التحويل / رقم المرسل:</td><td style='padding: 10px 14px;'><strong>{sub.senderDetails or 'لم يتم إدخالها'}</strong></td></tr>
        </table>
    """

    has_receipt = False
    receipt_bytes = None
    subtype = "jpeg"

    if receipt_base64 and "," in receipt_base64:
        try:
            header, b64data = receipt_base64.split(",", 1)
            if "image/png" in header:
                subtype = "png"
            elif "image/webp" in header:
                subtype = "webp"
            receipt_bytes = base64.b64decode(b64data)
            has_receipt = True
        except Exception as e:
            logger.error("Error decoding receipt base64: %s", e)

    if has_receipt and receipt_bytes:
        html_content += """
        <div style='margin-top: 20px; background: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #cbd5e1; text-align: center;'>
            <h4 style='color: #065f46; margin: 0 0 12px 0; font-size: 16px;'>📎 صورة إيصال التحويل (الاسكرين):</h4>
            <img src='cid:receiptImage' style='max-width: 100%; border-radius: 8px; border: 1px solid #94a3b8;' alt='إيصال التحويل' />
        </div>
        """
    else:
        html_content += """
        <div style='margin-top: 15px; padding: 12px; background: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; color: #92400e; font-size: 13px; text-align: center;'>
            ⚠️ لم يقم الطالب برفع صورة الإيصال.
        </div>
        """

    html_content += """
        <div style='text-align: center; margin-top: 24px; padding-top: 16px; border-top: 1px solid #cbd5e1; font-size: 12px; color: #64748b;'>
            منظومة إدارة مركز تحفيظ القرآن الكريم بأسريجه تلقائياً.
        </div>
    </div>
    """

    alt_part.attach(MIMEText(html_content, "html", "utf-8"))

    if has_receipt and receipt_bytes:
        img_part = MIMEImage(receipt_bytes, _subtype=subtype)
        img_part.add_header("Content-ID", "<receiptImage>")
        img_part.add_header("Content-Disposition", "inline", filename=f"receipt.{subtype}")
        msg.attach(img_part)

    return _send_smtp_message(settings.PAYMENT_ADMIN_EMAIL, subject, msg)

def send_ijaza_booking_email(booking: IjazaBooking) -> bool:
    track = booking.trackName or "ختمة القرآن الكريم"
    subject = f"🔔 طلب حجز [{track}]: {booking.studentName} ({booking.appointmentDate} | {booking.appointmentTime})"
    action_tok = booking.actionToken or ""
    approve_url = f"{settings.SERVER_BASE_URL}/api/ijaza/action?token={action_tok}&action=approve"
    reject_url = f"{settings.SERVER_BASE_URL}/api/ijaza/action?token={action_tok}&action=reject"
    clean_phone = sanitize_phone(booking.studentPhone)

    msg = MIMEMultipart("related")
    alt_part = MIMEMultipart("alternative")
    msg.attach(alt_part)

    wa_text = urllib.parse.quote(f"السلام عليكم يا {booking.studentName}، بخصوص طلب موعد جلستك يوم {booking.appointmentDate} الساعة {booking.appointmentTime} مع فضيلة الشيخ محمد سنار")

    html_content = f"""
    <div dir='rtl' style='font-family: Arial, Tahoma, sans-serif; background-color: #f0fdf4; padding: 24px; color: #1e293b; max-width: 650px; margin: auto; border: 2px solid #059669; border-radius: 16px;'>
        <div style='text-align: center; border-bottom: 2px solid #059669; padding-bottom: 16px; margin-bottom: 20px;'>
            <h2 style='color: #065f46; margin: 0 0 6px 0; font-size: 22px;'>مركز تحفيظ القرآن الكريم بأسريجه</h2>
            <h3 style='color: #059669; margin: 0; font-size: 19px;'>🔔 طلب حجز موعد جلسة جديدة</h3>
            <div style='margin-top: 10px;'><span style='background: #065f46; color: #ffffff; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 15px;'>📌 المسار: {track}</span></div>
            <p style='color: #64748b; font-size: 13px; margin: 8px 0 0 0;'>كود الحجز: <strong>{booking.bookingReference}</strong></p>
        </div>

        <div style='background: #ffffff; border: 2px solid #10b981; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;'>
            <p style='margin: 0 0 16px 0; font-size: 16px; font-weight: 800; color: #065f46;'>فضيلة الشيخ / إدارة المركز، يرجى اختيار الإجراء المطلوب لهذا الموعد:</p>
            <div style='margin-bottom: 12px;'>
                <a href='{approve_url}' target='_blank' style='display: inline-block; background-color: #059669; color: #ffffff; padding: 12px 28px; font-size: 16px; font-weight: 800; text-decoration: none; border-radius: 8px; margin: 6px;'>
                    ✅ الموافقة وتأكيد الجلسة
                </a>
                <a href='{reject_url}' target='_blank' style='display: inline-block; background-color: #dc2626; color: #ffffff; padding: 12px 28px; font-size: 16px; font-weight: 800; text-decoration: none; border-radius: 8px; margin: 6px;'>
                    ❌ الاعتذار / رفض الموعد
                </a>
            </div>
            <p style='margin: 0; font-size: 12.5px; color: #64748b;'>عند الضغط على أي زر سيتم تحديث وتثبيت حالة الجلسة في النظام فورياً.</p>
        </div>

        <h4 style='color: #065f46; margin-bottom: 8px; font-size: 16px;'>📋 تفاصيل طلب الجلسة والطالب:</h4>
        <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1;'>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>🌟 المسار المطلوب:</td><td style='padding: 10px 14px;'><strong>{track}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>اسم الطالب:</td><td style='padding: 10px 14px;'><strong>{booking.studentName}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>كود الطالب:</td><td style='padding: 10px 14px;'>{booking.userCode or 'غير مسجل'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>رقم الهاتف / الواتساب:</td><td style='padding: 10px 14px;'><a href='https://wa.me/2{clean_phone}' style='color: #059669; font-weight: 800;'>📱 {booking.studentPhone}</a></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>الشيخ المعلم:</td><td style='padding: 10px 14px;'><strong>{booking.sheikhName}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>💳 رسوم الجلسة المسددة:</td><td style='padding: 10px 14px;'>{booking.amount or '100 ج.م'} ({booking.paymentMethod or 'فودافون كاش'})</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>رقم التحويل / مرسل الدفع:</td><td style='padding: 10px 14px;'><strong>{booking.paymentSender or 'لم يتم إدخالها'}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>تاريخ الجلسة:</td><td style='padding: 10px 14px;'><strong>{booking.appointmentDate}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>توقيت الجلسة:</td><td style='padding: 10px 14px;'><strong>{booking.appointmentTime}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>نوع الجلسة المرادة:</td><td style='padding: 10px 14px;'>{booking.sessionType or '-'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>الرواية المقروء بها:</td><td style='padding: 10px 14px;'>{booking.riwayah or '-'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>نظام الحضور:</td><td style='padding: 10px 14px;'>{booking.sessionMode or 'أونلاين'}</td></tr>
        </table>
    """

    has_receipt = False
    receipt_bytes = None
    subtype = "jpeg"

    if booking.receiptBase64 and "," in booking.receiptBase64:
        try:
            header, b64data = booking.receiptBase64.split(",", 1)
            if "image/png" in header:
                subtype = "png"
            elif "image/webp" in header:
                subtype = "webp"
            receipt_bytes = base64.b64decode(b64data)
            has_receipt = True
        except Exception as e:
            logger.error("Error decoding booking receipt base64: %s", e)

    if has_receipt and receipt_bytes:
        html_content += """
        <div style='margin-top: 20px; background: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #cbd5e1; text-align: center;'>
            <h4 style='color: #065f46; margin: 0 0 12px 0; font-size: 16px;'>📎 صورة إيصال التحويل:</h4>
            <img src='cid:bookingReceiptImg' style='max-width: 100%; max-height: 450px; border-radius: 8px;' alt='إيصال التحويل' />
        </div>
        """

    html_content += f"""
        <div style='text-align: center; margin: 20px 0;'>
            <a href='https://wa.me/2{clean_phone}?text={wa_text}' target='_blank' style='background-color: #25d366; color: #ffffff; padding: 12px 26px; font-size: 15px; font-weight: bold; text-decoration: none; border-radius: 8px; display: inline-block;'>
                📱 مراسلة الطالب عبر واتساب مباشرة
            </a>
        </div>
    </div>
    """

    alt_part.attach(MIMEText(html_content, "html", "utf-8"))

    if has_receipt and receipt_bytes:
        img_part = MIMEImage(receipt_bytes, _subtype=subtype)
        img_part.add_header("Content-ID", "<bookingReceiptImg>")
        img_part.add_header("Content-Disposition", "inline", filename=f"booking_receipt.{subtype}")
        msg.attach(img_part)

    return _send_smtp_message(settings.PAYMENT_ADMIN_EMAIL, subject, msg)

def send_expiration_warning_email(sub: CourseSubscription) -> bool:
    subject = f"⚠️ تنبيه اقتراب انتهاء اشتراك: {sub.studentName} (متبقي 3 أيام)"
    clean_phone = sanitize_phone(sub.studentPhone)
    expiry_str = sub.expiresAt.strftime("%Y-%m-%d %I:%M %p") if sub.expiresAt else "خلال 3 أيام"

    wa_text = urllib.parse.quote("السلام عليكم ورحمة الله وبركاته، نحيطكم علماً بقرب انتهاء اشتراككم في دورة التجويد خلال 3 أيام، لتجديد الاشتراك ومواصلة الحضور يرجى التواصل معنا.")

    html_content = f"""
    <div dir='rtl' style='font-family: Arial, Tahoma, sans-serif; background-color: #fffbeb; padding: 24px; color: #1e293b; max-width: 650px; margin: auto; border: 2px solid #f59e0b; border-radius: 16px;'>
        <div style='text-align: center; border-bottom: 2px solid #f59e0b; padding-bottom: 16px; margin-bottom: 20px;'>
            <h2 style='color: #92400e; margin: 0 0 6px 0; font-size: 22px;'>مركز تحفيظ القرآن الكريم بأسريجه</h2>
            <h3 style='color: #d97706; margin: 0; font-size: 18px;'>⚠️ تنبيه: اقتراب انتهاء مدة اشتراك طالب (متبقي 3 أيام)</h3>
        </div>
        <p style='font-size: 15px; line-height: 1.8; color: #78350f;'>نحيطكم علماً بأن اشتراك الطالب التالي أوشك على الانتهاء، وسيتم إغلاق المحاضرات عنه تلقائياً بعد 3 أيام إذا لم يقم بالتجديد:</p>
        <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #fed7aa;'>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>اسم الطالب:</td><td style='padding: 10px 14px;'><strong>{sub.studentName}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>رقم الهاتف:</td><td style='padding: 10px 14px;'><a href='https://wa.me/2{clean_phone}' style='color: #d97706; font-weight: 800;'>📱 {sub.studentPhone}</a></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>كود الطالب:</td><td style='padding: 10px 14px;'>{sub.userCode or 'غير مسجل'}</td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>الدورة:</td><td style='padding: 10px 14px;'><strong>{sub.courseTitle or sub.courseKey}</strong></td></tr>
            <tr style='border-bottom: 1px solid #e2e8f0;'><td style='padding: 10px 14px; font-weight: bold; width: 35%; background: #f8fafc;'>تاريخ الانتهاء:</td><td style='padding: 10px 14px; color: #dc2626; font-weight: bold;'>{expiry_str}</td></tr>
        </table>
        <div style='text-align: center; margin: 24px 0;'>
            <a href='https://wa.me/2{clean_phone}?text={wa_text}' target='_blank' style='background-color: #25d366; color: #ffffff; padding: 12px 28px; font-size: 16px; font-weight: bold; text-decoration: none; border-radius: 8px; display: inline-block;'>
                مراسلة الطالب عبر واتساب للتجديد
            </a>
        </div>
    </div>
    """
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    return _send_smtp_message(settings.PAYMENT_ADMIN_EMAIL, subject, msg)

def send_calendar_invite_to_admin(booking: IjazaBooking) -> bool:
    track = booking.trackName or "جلسة قرآنية"
    subject = f"📅 تم تثبيت الموعد في Google Calendar: {booking.studentName} ({booking.appointmentDate} | {booking.appointmentTime})"
    cal_url = generate_google_calendar_url(booking)

    body_html = f"""
    <div dir='rtl' style='font-family: Arial, Tahoma, sans-serif; background-color: #f0fdf4; padding: 24px; color: #1e293b; max-width: 600px; margin: auto; border: 2px solid #059669; border-radius: 16px;'>
        <div style='text-align: center; border-bottom: 2px solid #059669; padding-bottom: 16px; margin-bottom: 20px;'>
            <h2 style='color: #065f46; margin: 0 0 6px 0;'>مركز تحفيظ القرآن الكريم بأسريجه</h2>
            <h3 style='color: #059669; margin: 0;'>📅 تأكيد وحفظ موعد الجلسة في Google Calendar</h3>
        </div>
        <p style='font-size: 15px; line-height: 1.7;'>تمت الموافقة بنجاح على موعد الجلسة وتأكيد حجزها في النظام:</p>
        <div style='background: #ffffff; padding: 16px; border-radius: 12px; border: 1px solid #cbd5e1; margin-bottom: 20px;'>
            <p style='margin: 6px 0;'><strong>• الطالب:</strong> {booking.studentName} (كود: {booking.userCode or '-'})</p>
            <p style='margin: 6px 0;'><strong>• الشيخ:</strong> {booking.sheikhName}</p>
            <p style='margin: 6px 0;'><strong>• التاريخ:</strong> {booking.appointmentDate}</p>
            <p style='margin: 6px 0;'><strong>• التوقيت:</strong> {booking.appointmentTime}</p>
            <p style='margin: 6px 0;'><strong>• المسار:</strong> {track}</p>
        </div>
        <div style='text-align: center; margin: 25px 0;'>
            <a href='{cal_url}' target='_blank' style='display: inline-block; background: #059669; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 16px;'>
                📅 فتح الموعد مباشرة في Google Calendar
            </a>
        </div>
        <p style='font-size: 13px; color: #64748b; text-align: center;'>مرفق بالرسالة ملف التقويم (.ics) ليتم تثبيت الموعد تلقائياً في تقويم جوجل لحسابك.</p>
    </div>
    """

    msg = MIMEMultipart("mixed")
    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(alt_part)

    ics_content = generate_ics_content(booking)
    ics_part = MIMEBase("text", "calendar", method="REQUEST", charset="UTF-8")
    ics_part.set_payload(ics_content.encode("utf-8"))
    encoders.encode_base64(ics_part)
    ics_part.add_header("Content-Disposition", "attachment", filename=f"quran_session_{booking.bookingReference}.ics")
    msg.attach(ics_part)

    return _send_smtp_message(settings.PAYMENT_ADMIN_EMAIL, subject, msg)
