"""Parolni xeshlash va JWT token bilan ishlash."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Parolni bcrypt bilan xeshlaydi."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiritilgan parol xeshga mos kelishini tekshiradi."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    """JWT access token yaratadi. `sub` ichida foydalanuvchi id si saqlanadi."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """Tokenni tekshiradi va foydalanuvchi id sini qaytaradi.

    Token yaroqsiz, muddati tugagan yoki `sub` noto'g'ri bo'lsa, None qaytadi.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject = payload.get("sub")
        if subject is None:
            return None
        return int(subject)
    except (JWTError, ValueError):
        return None