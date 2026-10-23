"""Jihozlar (Equipment) endpointlari."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Equipment, Rental, User
from app.schemas import EquipmentCreate, EquipmentOut, EquipmentUpdate

router = APIRouter(prefix="/equipment", tags=["Equipment"])


class EquipmentFilters:
    """Ro'yxat uchun umumiy qidiruv, filtr va sahifalash parametrlari."""

    def __init__(
        self,
        search: Optional[str] = Query(
            None, min_length=1, max_length=100, description="Jihoz nomi bo'yicha qidirish"
        ),
        category: Optional[str] = Query(
            None, min_length=1, max_length=100, description="Kategoriya bo'yicha filtr"
        ),
        min_price: Optional[Decimal] = Query(
            None, ge=0, description="Minimal kunlik narx"
        ),
        max_price: Optional[Decimal] = Query(
            None, ge=0, description="Maksimal kunlik narx"
        ),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
    ):
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="min_price max_price dan katta bo'lishi mumkin emas",
            )
        self.search = search
        self.category = category
        self.min_price = min_price
        self.max_price = max_price
        self.skip = skip
        self.limit = limit


def _list_equipment(
    db: Session, filters: EquipmentFilters, only_available: bool = False
) -> list[Equipment]:
    """Filtrlar bo'yicha jihozlar ro'yxatini qaytaradi."""
    stmt = select(Equipment)

    if filters.search:
        # LIKE maxsus belgilari (%, _) oddiy matn sifatida qidiriladi
        escaped = (
            filters.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        stmt = stmt.where(Equipment.name.ilike(f"%{escaped}%", escape="\\"))
    if filters.category:
        stmt = stmt.where(func.lower(Equipment.category) == filters.category.lower())
    if filters.min_price is not None:
        stmt = stmt.where(Equipment.daily_rate >= filters.min_price)
    if filters.max_price is not None:
        stmt = stmt.where(Equipment.daily_rate <= filters.max_price)
    if only_available:
        # Qaytarilmagan (faol yoki muddati o'tgan) ijarasi yo'q jihozlar
        active_rental = (
            select(Rental.id)
            .where(Rental.equipment_id == Equipment.id, Rental.returned_at.is_(None))
            .exists()
        )
        stmt = stmt.where(~active_rental)

    stmt = stmt.order_by(Equipment.id).offset(filters.skip).limit(filters.limit)
    return list(db.scalars(stmt).all())


def _get_equipment_or_404(
    db: Session, equipment_id: int, for_update: bool = False
) -> Equipment:
    equipment = db.get(Equipment, equipment_id, with_for_update=for_update)
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jihoz topilmadi"
        )
    return equipment


def _commit_or_409(db: Session) -> None:
    """Commit qiladi; inventory_code takrorlansa 409 qaytaradi."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu inventar kodi bilan jihoz allaqachon mavjud",
        )


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Yangi jihoz qo'shish (faqat admin)."""
    equipment = Equipment(**payload.model_dump())
    db.add(equipment)
    _commit_or_409(db)
    db.refresh(equipment)
    return equipment


@router.get("", response_model=list[EquipmentOut])
def list_equipment(
    filters: EquipmentFilters = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Barcha jihozlar: nom bo'yicha qidirish, kategoriya va narx bo'yicha filtr."""
    return _list_equipment(db, filters)


# DIQQAT: bu endpoint "/{equipment_id}" dan OLDIN turishi shart,
# aks holda "available" so'zi jihoz id si deb o'qilib, 422 xatosi chiqadi.
@router.get("/available", response_model=list[EquipmentOut])
def list_available_equipment(
    filters: EquipmentFilters = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Hozir ijaraga olinmagan jihozlar (xuddi shu filtrlar bilan)."""
    return _list_equipment(db, filters, only_available=True)


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Bitta jihoz tafsilotlari."""
    return _get_equipment_or_404(db, equipment_id)


@router.patch("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Jihozni tahrirlash (faqat admin).

    Kunlik narx o'zgarsa, eski ijaralarning narxi o'zgarmaydi: ular
    ijara boshlangan paytdagi narx nusxasini o'zida saqlaydi.
    """
    equipment = _get_equipment_or_404(db, equipment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(equipment, field, value)
    _commit_or_409(db)
    db.refresh(equipment)
    return equipment


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Jihozni o'chirish (faqat admin). Faol ijarasi bo'lsa, 409 qaytadi."""
    # Qatorni qulflaymiz (FOR UPDATE): tekshiruv bilan o'chirish orasida
    # boshqa mijoz shu jihozni ijaraga olib ulgurmasligi uchun.
    equipment = _get_equipment_or_404(db, equipment_id, for_update=True)

    active_rental_id = db.scalar(
        select(Rental.id)
        .where(Rental.equipment_id == equipment.id, Rental.returned_at.is_(None))
        .limit(1)
    )
    if active_rental_id is not None:
        db.rollback()  # qulfni bo'shatish
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faol ijarasi bor jihozni o'chirib bo'lmaydi",
        )

    db.delete(equipment)
    db.commit()