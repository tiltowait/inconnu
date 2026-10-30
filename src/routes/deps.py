"""Shared route dependencies."""

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from bot import InconnuBot


def get_bot(request: Request) -> "InconnuBot":
    """The bot instance serving this API."""
    return request.app.state.bot
