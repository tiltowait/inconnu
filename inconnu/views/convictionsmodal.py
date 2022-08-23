"""views/convictionsmodal.py - Allow users to enter their Convictions."""

import asyncio

from discord.ui import InputText, Modal

import inconnu


class ConvictionsModal(Modal):
    """A modal that lets the user set their characters' Convictions."""

    def __init__(self, character, report=True):
        super().__init__(title="Convictions")
        self.character = character
        self.report = report

        convictions = character.convictions

        self.add_item(
            InputText(
                label="First Conviction",
                placeholder="First Conviction",
                value=_pop_first(convictions),
                required=False,
            )
        )
        self.add_item(
            InputText(
                label="Second Conviction",
                placeholder="Second Conviction",
                value=_pop_first(convictions),
                required=False,
            )
        )
        self.add_item(
            InputText(
                label="Third Conviction",
                placeholder="Third Conviction",
                value=_pop_first(convictions),
                required=False,
            )
        )

    async def callback(self, interaction):
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

        old_convictions = self.character.convictions
        old_convictions = "\n".join(old_convictions) if old_convictions else "*None*"

        new_convictions = [first, second, third]
        new_convictions_str = "\n".join(new_convictions) if new_convictions else "*None*"

        user = interaction.user
        update_message = f"__{user.mention} changed **{self.character.name}'s** Convictions__"
        update_message += f"\n\n***Old***\n{old_convictions}\n\n***New***\n{new_convictions_str}"

        self.character.convictions = new_convictions

        tasks = [self.character.commit()]
        if self.report:
            tasks.append(
                interaction.response.send_message(
                    f"Changed **{self.character.name}'s** Convictions!", ephemeral=True
                )
            )
            tasks.append(
                inconnu.common.report_update(
                    ctx=interaction,
                    character=self.character,
                    title="Changed Convictions",
                    message=update_message,
                )
            )
        else:
            tasks.append(interaction.response.send_message("Convictions set!", ephemeral=True))

        await asyncio.gather(*tasks)


def _pop_first(convictions_list) -> str:
    """Pop the first item in the list, returning an empty string if out of bounds."""
    try:
        return convictions_list.pop(0)
    except IndexError:
        return ""
