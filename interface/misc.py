"""interface/misc.py - Miscellaneous commands."""

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


class MiscCommands(commands.Cog):
    """Miscellaneous commands."""

    @slash_command()
    async def coinflip(self, ctx):
        """Flip a coin."""
        await inconnu.misc.coinflip(ctx)


    @slash_command()
    async def invite(self, ctx):
        """Display Inconnu's invite link."""
        embed = discord.Embed(
            title="Invite Inconnu to your server",
            url="https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147747840&scope=applications.commands%20bot",
            description="Click the link above to invite Inconnu to your server!"
        )
        embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar)
        embed.set_thumbnail(url=ctx.bot.user.display_avatar)
        site = discord.ui.Button(label="Website", url="https://www.inconnu-bot.com")
        support = discord.ui.Button(label="Support", url="https://discord.gg/CPmsdWHUcZ")

        await ctx.respond(embed=embed, view=discord.ui.View(site, support))


    @slash_command()
    async def probability(
        self,
        ctx: discord.ApplicationContext,
        roll: Option(str, "The pool, hunger, and difficulty"),
        reroll: Option(str, "The re-roll strategy to use",
            choices=[
                OptionChoice("Re-Roll Failures", "reroll_failures"),
                OptionChoice("Maximize Crits", "maximize_criticals"),
                OptionChoice("Avoid Messy", "avoid_messy"),
                OptionChoice("Risky Avoid Messy", "risky")
            ],
            required=False
        ),
        character: inconnu.options.character("The character (if using traits)")
    ):
        """Calculate outcome probabilities for a given roll."""
        await inconnu.misc.probability(ctx, roll, reroll, character)


    @slash_command()
    async def random(
        self,
        ctx: discord.ApplicationContext,
        ceiling: Option(int, "The roll's highest possible value", min_value=2, default=100)
    ):
        """Roll between 1 and a given ceiling (default 100)."""
        await inconnu.misc.percentile(ctx, ceiling)


    @slash_command()
    @commands.guild_only()
    async def statistics(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(str, "(Optional) A trait to look for", required=False),
        date: Option(str, "(Optional) YYYYMMDD date to count from", default="19700101")
    ):
        """View roll statistics for your characters."""
        await inconnu.misc.statistics(ctx, trait, date)


    @slash_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def transfer(
        self,
        ctx: discord.ApplicationContext,
        current_owner: Option(discord.Member, "The character's current owner"),
        character: inconnu.options.character("The character to transfer", required=True),
        new_owner: Option(discord.Member, "The character's new owner"),
    ):
        """Reassign a character from one player to another."""
        try:
            character = inconnu.vchar.VChar.fetch(None, None, character)

            if ctx.guild.id == character.guild and current_owner.id == character.user:
                character.user = new_owner.id
                current_mention = current_owner.mention
                new_mention = new_owner.mention

                msg = f"Transferred **{character.name}** from {current_mention} to {new_mention}."
                await ctx.respond(msg)

            else:
                await inconnu.common.present_error(
                    ctx,
                    f"{current_owner.display_name} doesn't own {character.name}!"
                )

        except inconnu.vchar.errors.CharacterNotFoundError:
            await inconnu.common.present_error(ctx, "Character not found.")


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(MiscCommands(bot))
