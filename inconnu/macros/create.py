"""macros/create.py - Creating user macros."""
# pylint: disable=too-many-arguments

import inconnu

from . import macro_common

__HELP_URL = "https://www.inconnu.app/#/macros?id=creation"


async def create(
    ctx,
    name: str,
    pool: str,
    hunger: bool,
    diff: int,
    rouses: int,
    reroll_rouses: bool,
    staining: str,
    hunt: bool,
    comment: str,
    character: str,
):
    """Create a macro if the syntax is valid."""
    try:
        haven = inconnu.utils.Haven(
            ctx,
            character=character,
            tip="`/macro create` `name:NAME` `pool:POOL` `character:CHARACTER`",
            help=__HELP_URL,
        )
        character = await haven.fetch()

        # Make sure fields aren't too long
        if (length := len(name)) > macro_common.NAME_LEN:
            raise SyntaxError(f"Macro names can't be longer than 50 characters. (Yours: {length})")
        if comment is not None and (length := len(comment)) > macro_common.COMMENT_LEN:
            raise SyntaxError(f"Comments can't be longer than 300 characters. (Yours: {length})")

        if not macro_common.is_macro_name_valid(name):
            await inconnu.common.present_error(
                ctx,
                "Macro names can only contain letters and underscores.",
                character=character.name,
                help_url=__HELP_URL,
            )
            return

        if pool != "0":
            pool = inconnu.vr.RollParser(character, pool).pool_stack
        else:
            pool = []

        await character.add_macro(
            name, pool, hunger, diff, rouses, reroll_rouses, staining, hunt, comment
        )
        await ctx.respond(f"**{character.name}:** Created macro `{name}`.", ephemeral=True)

    except (
        SyntaxError,
        inconnu.errors.AmbiguousTraitError,
        inconnu.errors.TraitNotFoundError,
        inconnu.errors.MacroAlreadyExistsError,
    ) as err:
        await inconnu.utils.error(ctx, err, help=__HELP_URL, character=character.name)
