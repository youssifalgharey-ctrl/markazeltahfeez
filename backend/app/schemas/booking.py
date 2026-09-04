from typing import Optional
from pydantic import BaseModel, Field

class IjazaBookingRequest(BaseModel):
    studentName: str = Field(..., min_length=1)
    studentEmail: str = Field(..., min_length=1)
    studentPhone: str = Field(..., min_length=1)
    userCode: Optional[str] = None
    sheikhName: str = Field(..., min_length=1)
    riwayah: str = Field(..., min_length=1)
    sessionType: Optional[str] = "جلسة تقييم وتحديد مستوى"
    trackName: Optional[str] = "ختمة بالحصول علي الإجازة"
    sessionMode: Optional[str] = "أونلاين (Online)"
    appointmentDate: str = Field(..., min_length=1)
    appointmentTime: str = Field(..., min_length=1)
    notes: Optional[str] = None
    paymentMethod: Optional[str] = "فودافون كاش"
    paymentSender: Optional[str] = None
    amount: Optional[str] = "100 ج.م"
    receiptBase64: Optional[str] = None
