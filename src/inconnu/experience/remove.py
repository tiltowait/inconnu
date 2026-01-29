"""experience/remove.py - Remove an XP log entry."""

import discord

import inconnu
from ctx import AppCtx
from inconnu.utils import is_admin
from models import VChar
from services import haven
from ui.views import DisablingView

__HELP_URL = "https://docs.inconnu.app/advanced/administration/experience-management"


@haven(__HELP_URL)
async def remove_entry(
    ctx: AppCtx,
    character: VChar,
    index: int,
    *,
    player: discord.Member,
):
    """Award or deduct XP from a character."""
    try:
        # Log entries are presented to the user in reverse, so we need the
        # negative index
        entry_to_delete = character.experience.log.pop(-index)

        embed = _get_embed(player, character, entry_to_delete)
        view = _ExperienceView(character, entry_to_delete)

        view.message = await ctx.respond(embed=embed, view=view)
        await character.save()

    except IndexError:
        err = f"{character.name} has no experience log entry at index `{index}`."
        await inconnu.embeds.error(ctx, err)


def _get_embed(player, character, entry):
    """Generate an embed for displaying the deletion message."""
    embed = discord.Embed(title="Deleted Experience Log Entry", description=_format_entry(entry))
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
    embed.set_footer(text="Be sure to adjust unspent/lifetime XP accordingly!")

    experience = f"```{character.experience.unspent} / {character.experience.lifetime}```"
    embed.add_field(name="Experience", value=experience)

    return embed


def _format_entry(entry):
    """Format the deleted entry for display."""
    date = entry["date"].strftime("%b %d, %Y")
    scope = _entry_scope(entry)

    return f"**{entry['amount']:+} {scope} XP: {entry['reason']}** *({date})*"


def _entry_scope(entry):
    """Get the log entry scope."""
    return entry["event"].split("_")[-1].capitalize()


class _ExperienceView(DisablingView):
    """A View that adds or deducts the proper XP from a character when pressed."""

    def __init__(self, character, entry):
        super().__init__()

        self.character = character
        self.scope = _entry_scope(entry)
        self.amount = entry["amount"] * -1

        if self.amount < 0:
            title = f"Remove {abs(self.amount)} {self.scope} XP"
        else:
            title = f"Add {abs(self.amount)} {self.scope} XP"

        button = discord.ui.Button(label=title, style=discord.ButtonStyle.primary)
        button.callback = self.apply_xp
        self.add_item(button)

    async def apply_xp(self, interaction):
        """Apply the XP to the character."""
        if self.scope == "Unspent":
            syntax = f"uxp{self.amount:+}"
        else:
            syntax = f"lxp{self.amount:+}"

        await interaction.response.edit_message(view=None)

        field = inconnu.character.DisplayField.EXPERIENCE
        await inconnu.character.update(
            interaction, syntax, character=self.character, fields=[(field.value, field)]
        )
        self.stop()

    async def interaction_check(self, interaction) -> bool:
        """Check whether the user is an admin."""
        if not is_admin(interaction):
            await interaction.response.send_message("Only an admin can do this.", ephemeral=True)
            return False

        return True
