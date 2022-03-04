"""misc/slake.py - Slake 1 or more Hunger."""

import asyncio

import inconnu

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=slaking-hunger"


async def slake(ctx, amount, character=None):
    """Slake a character's Hunger."""
    try:
        tip = f"`/slake` `amount:{amount}` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)
        slaked = min(amount, character.hunger)

        if slaked == 0:
            await ctx.respond(f"**{character.name}** has no Hunger!", ephemeral=True)
        else:
            old_hunger = character.hunger
            await character.set_hunger(old_hunger - slaked)

            if old_hunger >= 4:
                view = inconnu.views.FrenzyView(character, 3)
            else:
                view = None

            await asyncio.gather(
                character.log("slake", slaked),
                inconnu.character.display(ctx, character,
                    title=f"Slaked {slaked} Hunger",
                    fields=[("New Hunger", inconnu.character.DisplayField.HUNGER)],
                    view=view
                )
            )

    except inconnu.common.FetchError:
        pass
