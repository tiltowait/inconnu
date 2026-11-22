"""User routing."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from routes.auth import get_authenticated_user
from services.premium import is_supporter

router = APIRouter()


class PremiumStatus(BaseModel):
    """A user's premium status."""

    is_supporter: bool


@router.get("/users/check-premium")
async def check_premium(
    user_id: Annotated[int, Depends(get_authenticated_user)],
) -> PremiumStatus:
    """Whether the requester is a supporter."""
    return PremiumStatus(is_supporter=is_supporter(user_id))
