from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.security.jwt_handler import decode_access_token

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:].strip()
    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    token_version = payload.get("version", 1)
    if not username:
        return None

    user = (
        db.query(User).filter(User.email == username).first()
        or db.query(User).filter(User.phone == username).first()
        or db.query(User).filter(User.userCode == username).first()
    )

    if not user:
        return None

    current_version = user.token_version if user.token_version is not None else 1
    if token_version != current_version:
        return None

    return user

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    user = get_current_user_optional(authorization=authorization, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز الدخول غير صالح أو انتهت صلاحيته",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مصرح لك بالوصول، هذه الصفحة مخصصة للإدارة فقط"
        )
    return current_user
