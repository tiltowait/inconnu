"""misc/slake.py - Slake 1 or more Hunger."""

from discord_ui.components import Button

from .. import common
from .. import character as char
from ..listeners import FrenzyListener

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=slaking-hunger"


async def slake(ctx, amount, character=None):
    """Slake a character's Hunger."""
    try:
        tip = f"`/slake` `amount:{amount}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        slaked = min(amount, character.hunger)

        if slaked == 0:
            await ctx.respond(f"**{character.name}** has no Hunger!", ephemeral=True)
        else:
            old_hunger = character.hunger
            character.hunger -= slaked
            character.log("slake", slaked)

            if old_hunger >= 4:
                components = [Button("Hunger Frenzy (DC 3)", color="red")]
            else:
                components = None

            msg = await char.display(ctx, character,
                title=f"Slaked {slaked} Hunger",
                fields=[("New Hunger", char.HUNGER)],
                components=components
            )

            if old_hunger >= 4:
                FrenzyListener(character, 3).attach_me_to(msg)


    except common.FetchError:
        pass
