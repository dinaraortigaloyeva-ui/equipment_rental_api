
"""Foydalanuvchi profiliga oid endpointlar."""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    """JWT token orqali joriy foydalanuvchi profilini qaytaradi."""
    return current_user
