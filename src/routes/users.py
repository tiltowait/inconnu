"""User routing."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from routes.auth import get_authenticated_user, is_supporter
from routes.deps import get_bot

if TYPE_CHECKING:
    from bot import InconnuBot

router = APIRouter()


class PremiumStatus(BaseModel):
    """A user's premium status."""

    is_supporter: bool


@router.get("/users/check-premium")
async def check_premium(
    user_id: Annotated[int, Depends(get_authenticated_user)],
    bot: Annotated[InconnuBot, Depends(get_bot)],
) -> PremiumStatus:
    """Whether the requester is a supporter."""
    return PremiumStatus(is_supporter=await is_supporter(bot, user_id))
