"""Admin endpointlari: ijaralarni boshqarish.

Router darajasida `require_admin` dependency'si ulangan, shuning uchun
bu yerdagi HAMMA endpoint faqat admin uchun ochiq:
tokensiz so'rov -> 401, customer -> 403.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Rental
from app.schemas import RentalOut

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/rentals/active", response_model=list[RentalOut])
def list_active_rentals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Barcha faol (hali qaytarilmagan) ijaralar.

    Muddati o'tgan, lekin hali qaytarilmagan ijaralar ham shu ro'yxatda
    bo'ladi: ular faol ijaralarning bir qismi hisoblanadi.
    """
    stmt = (
        select(Rental)
        .where(Rental.returned_at.is_(None))
        .order_by(Rental.due_at, Rental.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


@router.get("/rentals/overdue", response_model=list[RentalOut])
def list_overdue_rentals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Muddati o'tgan ijaralar.

    Overdue sharti: returned_at IS NULL AND due_at < hozirgi vaqt (UTC).
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(Rental)
        .where(Rental.returned_at.is_(None), Rental.due_at < now)
        .order_by(Rental.due_at, Rental.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


@router.post("/rentals/{rental_id}/return", response_model=RentalOut)
def confirm_return(rental_id: int, db: Session = Depends(get_db)):
    """Jihoz qaytarilganini tasdiqlash (faqat admin, faqat bir marta).

    Qatorni FOR UPDATE bilan qulflaymiz: ikkita admin bir vaqtda bosib
    yuborsa ham, ikkinchisi birinchisini kutadi va qaytarilganini ko'rib 409 oladi.
    """
    rental = db.get(Rental, rental_id, with_for_update=True)
    if rental is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ijara topilmadi"
        )

    if rental.returned_at is not None:
        db.rollback()  # qulfni bo'shatish
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu ijara allaqachon qaytarilgan deb tasdiqlangan",
        )

    rental.returned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rental)
    return rental