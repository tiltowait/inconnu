"""AppCtx definitions."""

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord.interactions import InteractionChannel

    from bot import InconnuBot

    Channel = InteractionChannel | None
else:
    Channel = (
        discord.abc.GuildChannel
        | discord.abc.PrivateChannel
        | discord.Thread
        | discord.PartialMessageable
        | None
    )


class AppInteraction(discord.Interaction):
    @property
    def client(self) -> "InconnuBot":
        return super().client  # type: ignore[return-value]


class AppCtx(discord.ApplicationContext):
    bot: "InconnuBot"
    interaction: AppInteraction


AppInvocation = AppCtx | AppInteraction
