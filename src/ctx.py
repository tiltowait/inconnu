"""AppCtx definitions."""

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot import InconnuBot


class AppCtx(discord.ApplicationContext):
    bot: "InconnuBot"
