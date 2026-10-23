"""Pydantic v2 schemalari (kirish va chiqish modellari)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    model_validator,
)

from app.models import UserRole


# ---------------------------------------------------------------------------
# Auth / User
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    """Ro'yxatdan o'tish uchun ma'lumotlar.

    extra="forbid": body ichida `role` kabi ortiqcha maydon yuborilsa, 422 qaytadi.
    Shu tarzda foydalanuvchi o'ziga admin rolini bera olmaydi.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    """Foydalanuvchi haqida javob (parol xeshi hech qachon qaytarilmaydi)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------
class EquipmentCreate(BaseModel):
    """Yangi jihoz qo'shish uchun ma'lumotlar (admin)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    category: str = Field(min_length=1, max_length=100)
    inventory_code: str = Field(min_length=1, max_length=50)
    # Kunlik narx noldan katta bo'lishi shart; pul uchun Decimal ishlatiladi
    daily_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class EquipmentUpdate(BaseModel):
    """Jihozni qisman tahrirlash: faqat yuborilgan maydonlar o'zgaradi."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    inventory_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    daily_rate: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )

    @model_validator(mode="after")
    def _tekshirish(self):
        if not self.model_fields_set:
            raise ValueError("Kamida bitta maydon yuborilishi kerak")
        # description null bo'lishi mumkin, qolganlari esa yo'q
        for maydon in ("name", "category", "inventory_code", "daily_rate"):
            if maydon in self.model_fields_set and getattr(self, maydon) is None:
                raise ValueError(f"{maydon} qiymati null bo'lishi mumkin emas")
        return self


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    category: str
    inventory_code: str
    daily_rate: Decimal
    created_at: datetime



# ---------------------------------------------------------------------------
# Rental
# ---------------------------------------------------------------------------
class RentalCreate(BaseModel):
    """Jihozni ijaraga olish uchun ma'lumotlar.

    extra="forbid": start_at, user_id, daily_rate, total_price kabi maydonlarni
    klient yubora olmaydi, ularni faqat server belgilaydi.
    """

    model_config = ConfigDict(extra="forbid")

    equipment_id: int = Field(gt=0)
    # Ijara muddati musbat butun son. 365 kun yuqori chegara: juda katta
    # qiymatlar sana hisoblashda xatoga olib kelmasligi uchun.
    days: int = Field(gt=0, le=365)


class RentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    equipment_id: int
    start_at: datetime
    due_at: datetime
    days: int
    daily_rate: Decimal
    total_price: Decimal
    returned_at: Optional[datetime]

    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Overdue sharti: returned_at IS NULL AND due_at < hozirgi vaqt."""
        return self.returned_at is None and self.due_at < datetime.now(timezone.utc)