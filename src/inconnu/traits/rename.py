"""traits/rename.py - Rename a character's trait."""

from loguru import logger

import errors
import services
import ui
from ctx import AppCtx
from inconnu.stats import trait_renamed
from inconnu.traits import traitcommon
from services.haven import Haven
from utils.text import straighten_apostrophes
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/traits#traits-rename")


async def rename(ctx: AppCtx, char_name: str | None, trait: str, new_name: str):
    """Rename a trait, keeping its rating and specialties. Only characters with
    the trait are offered for selection."""
    trait = _clean(trait)
    new_name = _clean(new_name)
    try:
        traitcommon.validate_trait_names(new_name)
    except (ValueError, SyntaxError) as err:
        await ui.embeds.error(ctx, err, character=char_name, help=__HELP_URL)
        return

    haven = Haven(
        ctx,
        character=char_name,
        char_filter=traitcommon.any_trait_filter(trait),
        errmsg=traitcommon.missing_traits_message(trait),
        help=__HELP_URL,
    )
    character = await haven.fetch()
    if haven.new_interaction is not None:
        ctx.interaction = haven.new_interaction

    try:
        old_name = character.rename_trait(trait, new_name)
    except errors.TraitError as err:
        await ui.embeds.error(ctx, err, character=character, help=__HELP_URL)
        return

    # Save first, so a failed response can't hide the change
    await character.save_changes()
    try:
        await trait_renamed(character.id, old_name, new_name)
    except Exception:
        # The rename is saved; only its trait statistics are at stake
        logger.exception("Couldn't rename {} in {}'s rolls", old_name, character.name)

    change = f"`{old_name}` → `{new_name}`"
    embed = ui.embeds.VCharEmbed(ctx, character, title="Trait Renamed", description=change)
    embed.set_footer(text="Macros using it were updated, too.")
    view = ui.views.TraitsView(character, ctx.user)
    await ctx.respond(embed=embed, view=view, ephemeral=True)

    await services.post_update(
        ctx=ctx,
        character=character,
        title="Trait Renamed",
        message=f"__{ctx.user.mention} renamed {character.name}'s trait:__\n{change}",
        color=0xFF9400,
    )


def _clean(name: str) -> str:
    """Collapse whitespace and straighten apostrophes in a trait name."""
    return " ".join(straighten_apostrophes(name).split())
