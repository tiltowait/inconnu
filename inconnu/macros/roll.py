"""macros/roll.py - Rolling character macros."""

import re
from uuid import uuid4

import discord
from discord.ui import Button, View

import inconnu

from .. import common
from ..misc import rouse
from ..vchar import errors
from ..vr import display_outcome, perform_roll
from . import macro_common

__HUNT_LISTENERS = {}
__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=rolling"


async def roll(ctx, syntax: str, character=None):
    """Roll a macro."""
    try:
        tip = f"`/vm` `syntax:{syntax}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        macro_stack, hunger, difficulty = __normalize_syntax(
            syntax
        )  # pylint: disable=unbalanced-tuple-unpacking

        if not macro_common.is_macro_name_valid(macro_stack[0]):
            raise ValueError("Macro names may only contain letters and underscores.")

        macro = character.find_macro(macro_stack.pop(0))
        parameters = macro.pool
        parameters.extend(macro_stack)

        # Macros can contain hunger by default, but the user can override
        if hunger is None:
            hunger = "hunger" if macro.hunger else "0"

        parameters.append(hunger)
        parameters.append(difficulty or macro.difficulty)

        outcome = perform_roll(character, parameters)

        # We show the rouse check first, because display_outcome() is blocking
        await __rouse(ctx, character, macro)
        await display_outcome(
            ctx, ctx.user, character, outcome, macro.comment, reroll_listener, remove_hunt_listener
        )

        if macro.hunt:
            if outcome.is_successful:
                await __slake(ctx, character, outcome)
            else:
                __HUNT_LISTENERS[outcome.id] = None

    except (ValueError, errors.MacroNotFoundError) as err:
        await common.present_error(ctx, err, character=character.name, help_url=__HELP_URL)
    except SyntaxError:
        err = f"**Unknown syntax:** `{syntax}`"
        err += "\n**Usage:** `/vm <macro_name> [hunger] [difficulty]`"
        err += "\n\nYou may add simple math after `macro_name`."
        err += "\n `hunger` and `difficulty` are optional."
        await common.present_error(ctx, err, help_url=__HELP_URL)
        return
    except common.FetchError:
        pass


async def __rouse(ctx, character, macro):
    """Perform a rouse check."""
    if macro.comment is not None:
        purpose = macro.comment
    else:
        purpose = f"{macro.name} macro"
    msg = "Hunger gained does not apply to the roll."

    if macro.rouses > 0:
        await rouse(
            ctx,
            macro.rouses,
            character.name,
            purpose,
            macro.reroll_rouses,
            oblivion=macro.staining,
            message=msg,
        )


async def reroll_listener(ctx, character, outcome):
    """Listens to roll events."""
    if outcome.id in __HUNT_LISTENERS:
        old_inter = __HUNT_LISTENERS[outcome.id]
        if old_inter is None and outcome.is_successful:
            # They re-rolled into success
            await __slake(ctx, character, None)
        elif old_inter is not None and not outcome.is_successful:
            # They re-rolled into failure
            await old_inter.delete()

        await remove_hunt_listener(outcome)


async def remove_hunt_listener(outcome):
    """Stop listening for reroll events."""
    if outcome is not None and outcome.id in __HUNT_LISTENERS:
        del __HUNT_LISTENERS[outcome.id]


async def __slake(ctx, character, outcome):
    """Present a menu to slake Hunger."""
    if character.hunger > 0:
        # Show nothing if Hunger is 0
        embed = discord.Embed(
            title="Slake Hunger",
            description="Click a button below to slake Hunger.",
        )
        embed.set_author(
            name=ctx.user.display_name,
            icon_url=inconnu.get_avatar(ctx.user),
        )
        embed.set_footer(
            text="Red indicates harmful drinks (p.212). Slaking to 0 Hunger kills the victim."
        )

        view = _SlakeView(ctx.user, character, outcome)
        view.message = await inconnu.respond(ctx)(embed=embed, view=view)

        if outcome is not None:
            __HUNT_LISTENERS[outcome.id] = view.message


def __normalize_syntax(syntax: str):
    syntax = re.sub(r"([+-])", r" \g<1> ", syntax)
    stack = syntax.split()
    params = []

    while len(stack) > 1 and stack[-2] not in ["+", "-"]:
        params.insert(0, stack.pop())

    params.insert(0, stack)

    if len(params) == 1:
        params.append(None)

    if len(params) == 2:
        params.append(None)

    # At this point, the stack contains the following items
    # 0: Pool (list that will be parsed by the standard roll parser)
    # 1: Hunger ("0" or the user's input)
    # 2: Difficulty (None or the user's input)

    # We validate the pool stack later, but we will validate hunger and difficulty
    # here. We don't modify anything; the roll parser will do that for us. Instead,
    # we simply check for validity.

    if params[1] is not None and params[1].lower() != "hunger":  # "hunger" is a valid option here
        if not 0 <= int(params[1]) <= 5:
            raise ValueError("Hunger must be between 0 and 5.")

    difficulty = params[2]
    if difficulty is not None:
        difficulty = int(difficulty)
        if difficulty < 0:
            raise ValueError("Difficulty cannot be less than 0.")

    return params


class _SlakeView(View):
    """A View that allows the user to slake Hunger."""

    CANCEL_SLAKE = -1

    def __init__(self, owner, character, outcome):
        super().__init__(timeout=600)
        self.owner = owner
        self.character = character
        self.buttons = {}
        self.message = None
        self.outcome = outcome

        for hunger in range(1, character.hunger + 1):
            # Red buttons denote harmful drinks (or full drain)
            if hunger == character.hunger:
                label = "Drain"
                button_style = discord.ButtonStyle.danger
            elif hunger > 2:
                label = str(hunger)
                button_style = discord.ButtonStyle.danger
            else:
                label = str(hunger)
                button_style = discord.ButtonStyle.primary

            custom_id = str(uuid4())
            self.buttons[custom_id] = hunger

            button = Button(label=label, style=button_style, custom_id=custom_id, row=0)
            button.callback = self.callback
            self.add_item(button)

        custom_id = str(uuid4())
        self.buttons[custom_id] = _SlakeView.CANCEL_SLAKE

        cancel = Button(
            label="Don't Slake", style=discord.ButtonStyle.secondary, custom_id=custom_id, row=1
        )
        cancel.callback = self.callback
        self.add_item(cancel)

    async def callback(self, inter):
        """Slake Hunger or cancel."""
        if inter.user != self.owner:
            await inter.response.send_message("This button doesn't belong to you!", ephemeral=True)
            return

        self.stop()
        custom_id = inter.data["custom_id"]
        slake_amount = self.buttons[custom_id]

        if slake_amount == _SlakeView.CANCEL_SLAKE:
            await inter.message.delete()
            await remove_hunt_listener(self.outcome)
        else:
            await inter.message.delete()
            await inconnu.misc.slake(inter, slake_amount, self.character)
            await inconnu.reference.resonance(inter, character=self.character.name)

    async def on_timeout(self):
        """Delete the message."""
        self.stop()
        await self.message.delete()
        await remove_hunt_listener(self.outcome)
