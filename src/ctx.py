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
    """A discord.Interaction with client and bot typed to InconnuBot."""

    @property
    def client(self) -> "InconnuBot":
        return super().client  # type: ignore[return-value]

    @property
    def bot(self) -> "InconnuBot":
        """The bot instance."""
        return super().client  # type: ignore[return-value]


class AppCtx(discord.ApplicationContext):
    """A discord.ApplicationContext with bot typed to InconnuBot and interaction
    typed to AppInteraction."""

    bot: "InconnuBot"
    interaction: AppInteraction


type AppInvocation = AppCtx | AppInteraction
