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
    """A discord.Interaction with client and bot typed to InconnuBot, and user typed
    as non-None."""

    # py-cord types Interaction.user as optional, but every interaction we handle
    # (commands, components, autocomplete, modals) has a user
    user: discord.Member | discord.User  # pyright: ignore[reportIncompatibleVariableOverride]

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

    @property
    def client(self) -> "InconnuBot":
        """Alias for .bot."""
        return self.bot


type AppInvocation = AppCtx | AppInteraction
