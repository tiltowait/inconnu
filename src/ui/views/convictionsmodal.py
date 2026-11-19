"""views/convictionsmodal.py - Allow users to enter their Convictions."""

import asyncio
from collections.abc import Awaitable
from typing import cast

import discord
from discord.ui import InputText, Modal

import services
from constants import MAX_CONVICTION_LENGTH
from ctx import AppInteraction
from models import VChar


class ConvictionsModal(Modal):
    """A modal that lets the user set their characters' Convictions."""

    def __init__(self, character: VChar, report=True):
        super().__init__(title="Convictions")
        self.character = character
        self.report = report

        convictions = character.convictions.copy()

        self.add_item(_conviction_input("First", _pop_first(convictions)))
        self.add_item(_conviction_input("Second", _pop_first(convictions)))
        self.add_item(_conviction_input("Third", _pop_first(convictions)))

    async def callback(self, interaction: discord.Interaction):
        """Set the character's Convictions."""
        first = self.children[0].value
        second = self.children[1].value
        third = self.children[2].value

        # Add punctuation
        if first and first[-1].isalpha():
            first += "."
        if second and second[-1].isalpha():
            second += "."
        if third and third[-1].isalpha():
            third += "."

        old_convictions = self.character.convictions.copy()
        old_convictions = "\n".join(old_convictions) if old_convictions else "*None*"

        new_convictions = [v for v in [first, second, third] if v]
        new_convictions_str = "\n".join(new_convictions) if new_convictions else "*None*"

        assert interaction.user is not None
        user = interaction.user
        update_message = f"__{user.mention} changed **{self.character.name}'s** Convictions__"
        update_message += f"\n\n***Old***\n{old_convictions}\n\n***New***\n{new_convictions_str}"

        self.character.convictions = new_convictions

        tasks: list[Awaitable[object]] = [self.character.save_changes()]
        if self.report:
            tasks.append(
                interaction.response.send_message(
                    f"Changed **{self.character.name}'s** Convictions!", ephemeral=True
                )
            )
            tasks.append(
                services.post_update(
                    ctx=cast(AppInteraction, interaction),
                    character=self.character,
                    title="Changed Convictions",
                    message=update_message,
                )
            )
        else:
            tasks.append(interaction.response.send_message("Convictions set!", ephemeral=True))

        await asyncio.gather(*tasks)


def _conviction_input(ordinal: str, value: str) -> InputText:
    """A Conviction's text input. A period may be added to the entry, so it
    leaves room for one. Older Convictions may be longer, and the modal can't
    open with a value over its limit."""
    return InputText(
        label=f"{ordinal} Conviction",
        placeholder=f"{ordinal} Conviction",
        value=value,
        required=False,
        max_length=max(MAX_CONVICTION_LENGTH - 1, len(value)),
    )


def _pop_first(convictions_list: list[str]) -> str:
    """Pop the first item in the list, returning an empty string if out of bounds."""
    try:
        return convictions_list.pop(0)
    except IndexError:
        return ""
