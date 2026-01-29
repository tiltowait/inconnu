"""macros/update.py - Macro update commands."""

import errors
import inconnu
from ctx import AppCtx
from inconnu.macros import macro_common
from models import VChar
from inconnu.utils import strtobool
from services import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/macros/updating"
__VALID_KEYS = {
    "name": "The macro's name (letters and underscores only)",
    "pool": "The macro's pool",
    "hunger": "Whether to add Hunger to the roll",
    "difficulty": "The macro's default difficulty",
    "rouses": "The number of Rouse checks to make",
    "reroll_rouses": "Whether to re-roll the Rouse checks",
    "staining": "Whether the Rouse checks can stain (Yes/No)",
    "hunt": "Provide an option to slake Hunger if the roll is successful",
    "comment": "The macro's comment",
}


@haven(__HELP_URL)
async def update(ctx: AppCtx, character: VChar, macro: str, syntax: str):
    """Update a macro."""
    try:
        syntax = " ".join(syntax.split())

        parameters = inconnu.utils.parse_parameters(syntax, False)
        macro_update = __validate_parameters(character, parameters)

        macro_name = character.update_macro(macro, macro_update)
        await ctx.respond(f"Updated **{character.name}'s** `{macro_name}` macro.")
        await character.save()

    except (
        errors.AmbiguousTraitError,
        errors.HungerInPool,
        errors.MacroNotFoundError,
        errors.TraitNotFound,
        SyntaxError,
        ValueError,
    ) as err:
        if isinstance(err, (SyntaxError, ValueError)):
            await inconnu.log.log_event(
                "macro_update_error", user=ctx.user.id, charid=character.id, syntax=syntax
            )

        keys = [f"`{key}`: {value}" for key, value in __VALID_KEYS.items()]
        instructions = [
            ("Instructions", "Update the macro with one or more KEY=VALUE pairs."),
            ("Valid Keys", "\n".join(keys)),
        ]

        await inconnu.embeds.error(
            ctx, err, *instructions, help=__HELP_URL, character=character.name
        )


def __validate_parameters(character: "VChar", parameters: dict):
    """Parse the update parameters."""
    macro_update = {}

    for key, value in parameters.items():
        # Each parameter should be part of a key=value pair
        if key in macro_update:
            raise SyntaxError(f"Duplicate key: `{key}`.")

        # Valid keys:
        #   name
        #   pool
        #   hunger
        #   difficulty
        #   comment
        #   rouses/rouse
        #   reroll_rouses/reroll
        #   stains/stain/staining
        #   hunt
        if key == "name":
            if not macro_common.is_macro_name_valid(value):
                raise ValueError(f"`{value}` is not a valid macro name.")
            macro_update[key] = value

        elif key == "pool":
            pool = inconnu.vr.RollParser(
                character, value, expand_only=True, power_bonus=False
            ).pool_stack
            macro_update[key] = pool

        elif key == "hunger":
            try:
                value = bool(strtobool(value))
                macro_update[key] = value
            except ValueError:
                raise ValueError("`hunger` requires yes/no or true/false.") from ValueError

        elif key in ["diff", "difficulty"]:
            if not value.isdigit() or int(value) < 0:
                raise ValueError("`difficulty` must be a number greater than 0.")
            macro_update["difficulty"] = int(value)

        elif key == "comment":
            macro_update[key] = value

        elif key in ["rouses", "rouse"]:
            if not value.isdigit() or not 0 <= int(value) <= 3:
                raise ValueError("`rouses` must be a number between 0 and 3.")
            macro_update["rouses"] = int(value)

        elif key in ["reroll_rouses", "reroll", "rerolls", "reroll_rouse"]:
            try:
                value = bool(strtobool(value))
                macro_update["reroll_rouses"] = value
            except ValueError:
                raise ValueError("`reroll_rouses` requires yes/no or true/false.") from ValueError

        elif key in ["stain", "stains", "staining"]:
            if value.lower() == "yes":
                macro_update["staining"] = "apply"
            elif value.lower() == "no":
                macro_update["staining"] = "no"
            else:
                raise ValueError("`stains` must be `YES` or `NO`.")

        elif key == "hunt":
            try:
                value = bool(strtobool(value))
                macro_update["hunt"] = value
            except ValueError:
                raise ValueError("`hunt` requires yes/now or true/false.") from ValueError

        else:
            raise ValueError(f"Unknown key `{key}`.")

    # Validated the update
    return macro_update
