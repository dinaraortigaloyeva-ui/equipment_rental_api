
"""Ijara (Rental) endpointlari: mijoz uchun."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Equipment, Rental, User, UserRole
from app.schemas import RentalCreate, RentalOut

router = APIRouter(prefix="/rentals", tags=["Rentals"])

# PostgreSQL xato kodlari
PG_UNIQUE_VIOLATION = "23505"
PG_FOREIGN_KEY_VIOLATION = "23503"

# Bitta jihozda faqat bitta faol ijara bo'lishini ta'minlovchi index
ACTIVE_RENTAL_CONSTRAINT = "uq_rentals_one_active_per_equipment"


@router.post(
    "",
    response_model=RentalOut,
    status_code=status.HTTP_201_CREATED,
)
def create_rental(
    payload: RentalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bo'sh jihozni kunlar sonini ko'rsatib ijaraga olish."""

    # Jihoz mavjudligini tekshirish
    equipment = db.get(Equipment, payload.equipment_id)

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jihoz topilmadi",
        )

    # Ijara boshlanish vaqtini UTC bo'yicha belgilash
    start_at = datetime.now(timezone.utc)

    # Yangi ijara obyektini yaratish
    rental = Rental(
        user_id=current_user.id,
        equipment_id=equipment.id,
        start_at=start_at,
        due_at=start_at + timedelta(days=payload.days),
        days=payload.days,
        daily_rate=equipment.daily_rate,
        total_price=equipment.daily_rate * payload.days,
    )

    db.add(rental)

    try:
        db.commit()

    except IntegrityError as exc:
        # Xatodan keyin sessionni tiklash
        db.rollback()

        orig = exc.orig

        # Psycopg va boshqa PostgreSQL drayverlari uchun
        pgcode = (
            getattr(orig, "pgcode", None)
            or getattr(orig, "sqlstate", None)
        )

        # Constraint nomini olish
        diag = getattr(orig, "diag", None)
        constraint_name = getattr(
            diag,
            "constraint_name",
            None,
        )

        # Jihoz allaqachon faol ijarada
        if (
            pgcode == PG_UNIQUE_VIOLATION
            or constraint_name == ACTIVE_RENTAL_CONSTRAINT
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Bu jihoz hozir ijarada, "
                    "qaytarilgandan keyin olish mumkin"
                ),
            ) from exc

        # Jihoz yozuvi boshqa so'rov vaqtida o'chirilgan
        if pgcode == PG_FOREIGN_KEY_VIOLATION:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jihoz topilmadi",
            ) from exc

        # Boshqa kutilmagan xatolarni yashirmaslik
        raise

    # Saqlangan ijara ma'lumotlarini yangilash
    db.refresh(rental)

    return rental


# DIQQAT: /my endpointi /{rental_id} dan oldin turishi kerak.
@router.get(
    "/my",
    response_model=list[RentalOut],
)
def list_my_rentals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Foydalanuvchining o'z ijaralari ro'yxati."""

    stmt = (
        select(Rental)
        .where(Rental.user_id == current_user.id)
        .order_by(Rental.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


@router.get(
    "/{rental_id}",
    response_model=RentalOut,
)
def get_rental(
    rental_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ijara tafsilotlarini ko'rish."""

    rental = db.get(Rental, rental_id)

    # Ijara mavjud bo'lmasa yoki foydalanuvchiga tegishli bo'lmasa
    if rental is None or (
        rental.user_id != current_user.id
        and current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ijara topilmadi",
        )

    return rental
