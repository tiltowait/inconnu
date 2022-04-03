"""experience/remove.py - Remove an XP log entry."""

import discord

import inconnu

from ..views import DisablingView

__HELP_URL = "https://www.inconnu-bot.com"


async def remove_entry(ctx, player, character, index):
    """Award or deduct XP from a character."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/experience remove player:PLAYER character:CHARACTER index:INDEX`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        try:
            log = character.experience_log
            entry_to_delete = log[-index]  # Log entries are presented to the user in reverse
            await character.remove_experience_log_entry(entry_to_delete)

            if await inconnu.settings.accessible(ctx.user):
                msg = {"content": _get_text(character, entry_to_delete)}
            else:
                msg = {"embed": _get_embed(owner, character, entry_to_delete)}

            msg["view"] = _ExperienceView(character, entry_to_delete)

            await inconnu.respond(ctx)(**msg)

        except IndexError:
            err = f"{character.name} has no experience log entry at index `{index}`."
            await inconnu.common.present_error(ctx, err)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


def _get_embed(player, character, entry):
    """Generate an embed for displaying the deletion message."""
    embed = discord.Embed(title="Deleted Experience Log Entry", description=_format_entry(entry))
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
    embed.set_footer(text="Be sure to adjust unspent/lifetime XP accordingly!")

    experience = f"```{character.current_xp} / {character.total_xp}```"
    embed.add_field(name="Experience", value=experience)

    return embed


def _get_text(character, entry):
    """Generate text version of deletion message."""
    msg = f"**{character.name}**\n"
    msg += "```Deleted Experience Log Entry```"
    msg += "\n" + _format_entry(entry)
    msg += "\n\n*Be sure to adjust unspent/lifetime XP accordingly!"

    return msg


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
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only an admin can do this.", ephemeral=True)
            return False

        return True
