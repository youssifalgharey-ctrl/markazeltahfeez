from typing import Optional
from pydantic import BaseModel, Field

class PaymentNotificationRequest(BaseModel):
    fullName: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    userCode: Optional[str] = None
    email: Optional[str] = None
    courseKey: Optional[str] = "pkg-mandatory"
    courseTitle: Optional[str] = "دورة تجويد"
    courseSubtitle: Optional[str] = None
    amount: Optional[str] = None
    paymentMethod: Optional[str] = None
    senderDetails: Optional[str] = None
    receiptBase64: Optional[str] = None
