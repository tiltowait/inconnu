"""misc/slake.py - Slake 1 or more Hunger."""

import asyncio

import inconnu

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#slaking-hunger"


async def slake(ctx, amount, character=None, **kwargs):
    """Slake a character's Hunger."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip=f"`/slake` `amount:{amount}` `character:CHARACTER`",
        char_filter=_can_slake,
        errmsg="None of your characters have Hunger to slake.",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    if not character.is_vampire:
        await ctx.respond("Only vampires need to slake Hunger!", ephemeral=True)
        return

    slaked = min(amount, character.hunger)

    if slaked == 0:
        await ctx.respond(f"**{character.name}** has no Hunger!", ephemeral=True)
    else:
        old_hunger = character.hunger
        character.hunger -= slaked
        character.log("slake", slaked)

        if old_hunger >= 4:
            view = inconnu.views.FrenzyView(character, 3)
        else:
            view = None

        update = f"**{character.name}** slaked `{slaked}` Hunger (now at `{character.hunger}`)."

        inter = await inconnu.character.display(
            ctx,
            character,
            title=f"Slaked {slaked} Hunger",
            fields=[("New Hunger", inconnu.character.DisplayField.HUNGER)],
            view=view,
            **kwargs,
        )
        msg = await inconnu.get_message(inter)
        await asyncio.gather(
            character.commit(),
            inconnu.common.report_update(
                ctx=ctx,
                msg=msg,
                character=character,
                title="Hunger Slaked",
                message=update,
            ),
        )


def _can_slake(character):
    """Raises an exception if the character isn't a vampire or is at Hunger 0."""
    if not character.is_vampire:
        raise inconnu.errors.CharacterError(f"{character.name} isn't a vampire!")
    if character.hunger == 0:
        raise inconnu.errors.CharacterError(f"{character.name} has no Hunger!")
