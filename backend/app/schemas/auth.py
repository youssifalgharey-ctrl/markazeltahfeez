import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ── نمط رقم الهاتف المصري ────────────────────────────────────────────
# يقبل: 01xxxxxxxxx (11 رقم) أو +201xxxxxxxxx
_PHONE_PATTERN = re.compile(r"^(\+?2)?01[0-2,5]\d{8}$")

class RegisterRequest(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=11, max_length=15)
    age: int = Field(..., ge=4, le=120)
    email: Optional[str] = Field(None, max_length=254)
    inviteCode: Optional[str] = Field(None, max_length=10)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not _PHONE_PATTERN.match(cleaned):
            raise ValueError("رقم الهاتف غير صحيح، يرجى إدخال رقم مصري صحيح (مثال: 01xxxxxxxxx)")
        return cleaned

    @field_validator("fullName")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("الاسم لا يمكن أن يكون فارغاً")
        return stripped

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=254)  # Can be email, phone, or userCode
    password: str = Field(..., min_length=1, max_length=128)

class AuthResponse(BaseModel):
    token: Optional[str] = None
    fullName: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    userCode: Optional[str] = None
    role: Optional[str] = None
    message: Optional[str] = None
    profileImage: Optional[str] = None

class ProfileResponse(BaseModel):
    fullName: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    userCode: Optional[str] = None
    address: Optional[str] = None
    currentSurah: Optional[str] = None
    profileImage: Optional[str] = None
    role: Optional[str] = None
    token: Optional[str] = None  # يُرسَل فقط لو تغيّرت بيانات التحقق

class ProfileUpdateRequest(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=11, max_length=15)
    age: int = Field(..., ge=4, le=120)
    email: Optional[str] = Field(None, max_length=254)
    address: Optional[str] = Field(None, max_length=300)
    currentSurah: Optional[str] = Field(None, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not _PHONE_PATTERN.match(cleaned):
            raise ValueError("رقم الهاتف غير صحيح، يرجى إدخال رقم مصري صحيح (مثال: 01xxxxxxxxx)")
        return cleaned

class AvatarUpdateRequest(BaseModel):
    image: str = Field(..., max_length=3_000_000)  # ~2 MB base64

class ChangePasswordRequest(BaseModel):
    oldPassword: str = Field(..., min_length=1, max_length=128)
    newPassword: str = Field(..., min_length=6, max_length=128)
    confirmPassword: str = Field(..., min_length=1, max_length=128)

