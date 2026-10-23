"""Ma'lumotlar bazasi bilan ulanish.

- engine: PostgreSQL bilan ulanish
- SessionLocal: sessiyalar fabrikasi
- Base: barcha modellar uchun asosiy klass
- get_db: har bir so'rov uchun sessiya beruvchi dependency
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# pool_pre_ping=True: uzilib qolgan ulanishlarni avtomatik aniqlaydi.
# timezone=utc: baza sessiyasi UTC vaqt bilan ishlaydi, shunda vaqtlar izchil bo'ladi.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"options": "-c timezone=utc"},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Barcha SQLAlchemy modellari shu klassdan meros oladi."""


def get_db():
    """Har bir so'rov uchun alohida sessiya ochadi va oxirida yopadi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()