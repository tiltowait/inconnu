"""macros/create.py - Creating user macros."""

import errors
import inconnu
import ui
from ctx import AppCtx
from inconnu.macros import macro_common
from models import VChar
from services.haven import haven
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/macros#macro-create")


@haven(__HELP_URL)
async def create(
    ctx: AppCtx,
    character: VChar,
    name: str,
    pool: str,
    hunger: bool,
    diff: int,
    rouses: int,
    reroll_rouses: bool,
    staining: str,
    hunt: bool,
    comment: str | None,
):
    """Create a macro if the syntax is valid."""
    try:
        # Make sure fields aren't too long
        if (length := len(name)) > macro_common.NAME_LEN:
            raise SyntaxError(f"Macro names can't be longer than 50 characters. (Yours: {length})")
        if comment is not None and (length := len(comment)) > macro_common.COMMENT_LEN:
            raise SyntaxError(f"Comments can't be longer than 300 characters. (Yours: {length})")

        if not macro_common.is_macro_name_valid(name):
            await ui.embeds.error(
                ctx,
                "Macro names can only contain letters and underscores.",
                character=character.name,
                help=__HELP_URL,
            )
            return

        if pool != "0":
            pool_stack = inconnu.vr.RollParser(
                character, pool, expand_only=True, power_bonus=False
            ).pool_stack
        else:
            pool_stack = []
        macro_common.check_has_action(pool_stack, rouses)

        character.add_macro(
            name=name,
            pool=pool_stack,
            hunger=hunger,
            difficulty=diff,
            rouses=rouses,
            reroll_rouses=reroll_rouses,
            staining=staining,
            hunt=hunt,
            comment=comment,
        )
        await ctx.respond(f"**{character.name}:** Created macro `{name}`.", ephemeral=True)
        await character.save()

    except (
        SyntaxError,
        errors.AmbiguousTraitError,
        errors.MacroError,
        errors.RollError,
        errors.TraitNotFound,
    ) as err:
        await ui.embeds.error(ctx, err, help=__HELP_URL, character=character.name)
