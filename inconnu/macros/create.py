"""macros/create.py - Creating user macros."""
# pylint: disable=too-many-arguments

from . import macro_common
from .. import common
from ..vchar import errors

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=creation"


async def create(
    ctx,
    name: str,
    pool: str,
    hunger: bool,
    difficulty: int,
    rouses: int,
    reroll_rouses: bool,
    comment: str,
    character: str
):
    """Create a macro if the syntax is valid."""
    if difficulty < 0:
        await common.present_error(ctx, "`Difficulty` cannot be less than 0.", help_url=__HELP_URL)
        return

    try:
        tip = "`/macro create` `name:NAME` `pool:POOL` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        # Make sure fields aren't too long
        if len(name) > macro_common.NAME_LEN:
            length = len(name)
            raise SyntaxError(f"Macro names can't be longer than 50 characters. (Yours: {length})")
        if comment is not None and len(comment) > macro_common.COMMENT_LEN:
            length = len(comment)
            raise SyntaxError(f"Comments can't be longer than 300 characters. (Yours: {length})")

        if not macro_common.is_macro_name_valid(name):
            await common.present_error(
                ctx,
                "Macro names can only contain letters and underscores.",
                character=character.name,
                help_url=__HELP_URL
            )
            return

        pool = macro_common.expand_syntax(character, pool)
        character.add_macro(name, pool, hunger, rouses, reroll_rouses, difficulty, comment)
        await ctx.respond(f"**{character.name}:** Created macro `{name}`.", hidden=True)

    except (
        SyntaxError, errors.AmbiguousTraitError, errors.TraitNotFoundError,
        errors.MacroAlreadyExistsError
    ) as err:
        await common.present_error(ctx, err, help_url=__HELP_URL, character=character.name)
    except common.FetchError:
        pass
