from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from app.config import settings

def create_access_token(subject: str, token_version: int = 1, session_id: Optional[str] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(milliseconds=settings.JWT_EXPIRATION_MS)
    payload = {
        "sub": subject,
        "version": token_version,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        return None
