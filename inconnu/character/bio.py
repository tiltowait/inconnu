"""character/bio.py - Create/edit/view character bios."""

import discord

import inconnu

__HELP_URL = "https://www.inconnu-bot.com"


async def edit_biography(ctx, character):
    """Edit a character bio."""
    character = inconnu.vchar.VChar.fetch(ctx.guild.id, ctx.user.id, character)
    modal = _CharacterBio(character, title=f"Edit Biography: {character.name}")

    await ctx.interaction.response.send_modal(modal)


async def show_biography(ctx, character, player):
    """Display a character's biography."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player, requires_admin=False)
        tip = "`/character bio show character:CHARACTER player:PLAYER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        embed = discord.Embed(title=f"Biography: {character.name}")
        embed.add_field(
            name="Biography",
            value=character.biography or "*Not set.*",
            inline=False
        )
        embed.add_field(
            name="Description",
            value=character.description or "*Not set.*",
            inline=False
        )

        await ctx.respond(embed=embed)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


class _CharacterBio(discord.ui.Modal):
    """A character biography modal."""

    def __init__(self, character, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character

        self.add_item(discord.ui.InputText(
            label="Biography",
            placeholder="Character biography and history.",
            value=character.biography,
            style=discord.InputTextStyle.long
        ))
        self.add_item(discord.ui.InputText(
            label="Description & Personality",
            placeholder="The character's physical description.",
            value=character.description,
            style=discord.InputTextStyle.long
        ))


    async def callback(self, interaction: discord.Interaction):
        """Finalize the modal."""
        biography = self.children[0].value
        description = self.children[1].value

        self.character.biography = biography
        self.character.description = description

        await interaction.response.send_message(
            f"Edited {self.character.name}'s bio!",
            ephemeral=True
        )
