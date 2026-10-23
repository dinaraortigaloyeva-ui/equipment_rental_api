"""SQLAlchemy ORM modellari: User, Equipment, Rental.

Muhim qoidalar:
- Pul qiymatlari Numeric (Decimal) bilan saqlanadi, float ishlatilmaydi.
- Barcha vaqtlar timezone-aware (DateTime(timezone=True)).
- Bitta jihozda faqat bitta faol ijara bo'lishi PostgreSQL partial unique index
  orqali ta'minlanadi (returned_at IS NULL bo'lgan yozuvlar uchun).
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """Foydalanuvchi rollari."""

    ADMIN = "admin"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,  # PostgreSQL ENUM turi emas, VARCHAR + CHECK
            create_constraint=True,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.CUSTOMER,
        server_default=UserRole.CUSTOMER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    rentals: Mapped[list["Rental"]] = relationship(back_populates="user")


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint("daily_rate > 0", name="ck_equipment_daily_rate_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    inventory_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    rentals: Mapped[list["Rental"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Rental(Base):
    __tablename__ = "rentals"
    __table_args__ = (
        CheckConstraint("days > 0", name="ck_rentals_days_positive"),
        CheckConstraint("daily_rate > 0", name="ck_rentals_daily_rate_positive"),
        CheckConstraint(
            "total_price = daily_rate * days", name="ck_rentals_total_price_matches"
        ),
        CheckConstraint("due_at > start_at", name="ck_rentals_due_after_start"),
        # Bitta jihozda faqat bitta faol (qaytarilmagan) ijara bo'lishi mumkin.
        # Parallel so'rovlarda ham bazaning o'zi buni kafolatlaydi.
        Index(
            "uq_rentals_one_active_per_equipment",
            "equipment_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE")
    )
    # start_at server tomonidan belgilanadi (klient yubora olmaydi)
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    days: Mapped[int] = mapped_column(Integer)
    # Ijara boshlangan paytdagi narx nusxasi: Equipment narxi keyin o'zgarsa ham
    # eski ijaraning narxi o'zgarmaydi.
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    returned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="rentals")
    equipment: Mapped["Equipment"] = relationship(back_populates="rentals")