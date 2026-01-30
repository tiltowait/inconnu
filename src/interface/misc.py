"""interface/misc.py - Miscellaneous commands."""

import asyncio
from typing import TYPE_CHECKING

import discord
from discord import option
from discord.commands import slash_command
from discord.ext import commands

import constants
import errors
import inconnu
import services
import ui
from inconnu.options import char_option

if TYPE_CHECKING:
    from bot import InconnuBot


class MiscCommands(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: "InconnuBot"):
        self.bot = bot

    @slash_command()
    @option(
        "hidden",
        description="Make the changelog only visible to you (default true).",
        default=True,
    )
    async def changelog(self, ctx, hidden: bool):
        """Show Inconnu's most recent changelog."""
        await inconnu.misc.show_changelog(ctx, hidden)

    @slash_command()
    async def coinflip(self, ctx):
        """Flip a coin."""
        await inconnu.misc.coinflip(ctx)

    @slash_command()
    async def invite(self, ctx):
        """Display Inconnu's invite link."""
        embed = discord.Embed(
            title="Invite Inconnu to your server",
            url=ctx.bot.invite_url,
            description="Click the link above to invite Inconnu to your server!",
        )
        embed.set_author(name=ctx.bot.user.display_name)
        embed.set_thumbnail(url=ctx.bot.user.display_avatar)
        site = discord.ui.Button(label="Website", url="https://www.inconnu.app")
        support = discord.ui.Button(label="Support", url=constants.SUPPORT_URL)

        await ctx.respond(embed=embed, view=ui.views.ReportingView(site, support))

    @slash_command()
    @option("ceiling", description="The roll's highest possible value", min_value=2, default=100)
    async def random(
        self,
        ctx: discord.ApplicationContext,
        ceiling: int,
    ):
        """Roll between 1 and a given ceiling (default 100)."""
        await inconnu.misc.percentile(ctx, ceiling)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @commands.has_permissions(administrator=True)
    @option("current_owner", description="The character's owner (admin only)")
    @char_option("The character to transfer", required=True)
    @option("new_owner", description="The character's new owner")
    async def transfer(
        self,
        ctx: discord.ApplicationContext,
        current_owner: discord.Member,
        character: str,
        new_owner: discord.Member,
    ):
        """Reassign a character from one player to another."""
        if current_owner.id == new_owner.id:
            await ui.embeds.error(ctx, "`current_owner` and `new_owner` can't be the same.")
            return

        try:
            xfer = await services.char_mgr.fetchone(ctx.guild, current_owner.id, character)

            if ctx.guild.id == xfer.guild and current_owner.id == xfer.user:
                current_mention = current_owner.mention
                new_mention = new_owner.mention

                msg = f"Transferred **{xfer.name}** from {current_mention} to {new_mention}."
                await asyncio.gather(
                    services.char_mgr.transfer(xfer, current_owner, new_owner), ctx.respond(msg)
                )
                await self.bot.transfer_premium(new_owner, xfer)

            else:
                await ui.embeds.error(ctx, f"{current_owner.display_name} doesn't own {xfer.name}!")

        except errors.CharacterNotFoundError:
            await ui.embeds.error(ctx, "Character not found.")
        except (LookupError, ValueError) as err:
            await ui.embeds.error(ctx, err)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(MiscCommands(bot))
