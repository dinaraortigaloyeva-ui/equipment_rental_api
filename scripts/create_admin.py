"""Birinchi admin foydalanuvchini yaratish skripti.

Ishga tushirish (loyihaning asosiy papkasidan):
    python -m scripts.create_admin
"""

import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User, UserRole
from app.oauth2 import hash_password


def main() -> None:
    raw_email = input("Admin email: ").strip().lower()
    try:
        email = TypeAdapter(EmailStr).validate_python(raw_email)
    except ValidationError:
        print("Xato: email formati noto'g'ri.")
        sys.exit(1)

    password = getpass.getpass("Parol (kamida 8 belgi): ")
    if len(password) < 8 or len(password) > 72:
        print("Xato: parol 8 dan 72 belgigacha bo'lishi kerak.")
        sys.exit(1)

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            print("Xato: bu email bilan foydalanuvchi allaqachon mavjud.")
            sys.exit(1)

        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        db.commit()

    print(f"Admin yaratildi: {email}")


if __name__ == "__main__":
    main()