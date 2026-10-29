"""parse.py - Handles parsing and execution of roll commands."""

# When a user rolls, they have two options:
#    * Roll straight numbers (7 3 2 == pool 7, hunger 3, diff 2)
#    * Roll using traits (str+dex 3 2)

# In the latter case, we need to figure out which character they are rolling for.
# If they only have one character, then we will allow them to omit the character
# name; however, if they have more than one, they _MUST_ supply a name. Complicating
# this is the fact they could theoretically supply a name despite not using a
# trait-based roll, so we need to check for the character in either case.

import re
from functools import partial

import discord
from loguru import logger

import errors
import services
import ui
from ctx import AppCtx
from inconnu.roll import Roll
from inconnu.vr.rolldisplay import RerollListener, RollDisplay, TimeoutHandler
from inconnu.vr.rollparser import RollParser
from models import (
    IMPAIRMENT_DICE,
    HiddenDicePerms,
    Impairment,
    ImpairmentCategory,
    RollCategory,
    VChar,
)
from models.vchardocs import VCharTrait
from services.haven import Haven
from utils.permissions import is_admin
from utils.urls import docs_url

__HELP_URL = docs_url("guides/quickstart/rolling-with-traits")


async def parse(
    ctx: AppCtx,
    raw_syntax: str,
    comment: str | None,
    char_name: str | None,
    player: discord.Member | None,
    *,
    impairment_category: ImpairmentCategory | None = None,
    hide_dice=False,
) -> VChar | None:
    """Parse the user's arguments and attempt to roll the dice."""
    if not await hidden_dice_allowed(ctx, hide_dice):
        return

    raw_syntax = " ".join(raw_syntax.split())
    syntax = raw_syntax  # Save the raw in case we get a character error
    owner = ctx.user

    # Comments appear after the first # in a command
    if "#" in syntax:
        syntax, comment = syntax.split("#", 1)

    if RollParser.has_invalid_characters(syntax):
        if RollParser.possible_spec_use(syntax):
            fields = [("Trying to roll a specialty?", "Use `skill.spec`, not `skill (spec)`.")]
        else:
            fields = []
        await ui.embeds.error(ctx, f"Invalid syntax: `{syntax}`.", *fields, ephemeral=False)
        return

    comment = await stringify_mentions(ctx, comment)
    if comment is not None and (comment_len := len(comment)) > 300:
        logger.debug("VR: Comment is too long")
        await ui.embeds.error(ctx, f"Comment is too long by {comment_len - 300} characters.")
        return

    if ctx.guild is None and needs_character(syntax):
        await ui.embeds.error(ctx, "You cannot roll traits in DMs!", help=__HELP_URL)
        return

    # Determine the character being used, if any. Only guilds have characters,
    # so in DMs, we ignore the character parameter if the user gave it.
    character: VChar | None = None
    if ctx.guild is not None:
        try:
            if char_name is not None or needs_character(syntax):
                haven = Haven(
                    ctx,
                    owner=player,
                    character=char_name,
                    char_filter=partial(validate_roll, syntax=syntax),
                    tip=f"`/vr` `syntax:{raw_syntax}` `character:CHARACTER`",
                    help=__HELP_URL,
                    errmsg=f"None of your characters can roll `{syntax}`.",
                )
                character = await haven.fetch()
                owner = haven.owner

        except (SyntaxError, LookupError) as err:
            await ui.embeds.error(ctx, err, help=__HELP_URL)
            return
        except errors.HandledError:
            return

    # Attempt to parse the user's roll syntax
    try:
        max_hunger = await services.settings.max_hunger(ctx.guild)
        outcome = await perform_roll(
            ctx, character, syntax, max_hunger, impairment_category=impairment_category
        )
        await display_outcome(
            ctx,
            owner,
            character,
            outcome,
            comment,
            impairment_category=impairment_category,
            hide_dice=hide_dice,
        )

    except (SyntaxError, ValueError, errors.TraitError, errors.RollError) as err:
        if isinstance(err, errors.TraitError):
            view = ui.views.TraitsView(character, ctx.user)
            ephemeral = True
        else:
            view = discord.MISSING
            ephemeral = False

        await ui.embeds.error(
            ctx,
            err,
            ("Your Input", f"/vr syntax:`{raw_syntax}`"),
            author=owner,
            character=character,
            help=__HELP_URL,
            view=view,
            ephemeral=ephemeral,
        )

    return character


def validate_roll(character: VChar, syntax: str):
    """Raise an exception if the character can't roll the syntax. Used to
    filter characters, so errors that the character choice can't fix stop the
    search with a SyntaxError."""
    try:
        _ = RollParser(character, syntax)
    except (errors.AmbiguousTraitError, errors.HungerInPool):
        # It's possible there's no ambiguity on another character. We pass on
        # HungerInPool so we can show the correct error message. Otherwise, we
        # get "None of your characters can roll x + hunger".
        pass
    except (errors.HungerIsntHunger, errors.InvalidDifficulty) as err:
        # A misused trait fails the same way for every character, so asking
        # which character to use would be pointless. SyntaxErrors aren't
        # handled by Haven, so this shows the error immediately.
        raise SyntaxError(str(err)) from err
    except errors.TooManyParameters as err:
        # Vampires take the most parameters, so we always want to show the
        # error message if it's too many for a vampire. Mortals, however, have
        # a Hunger 0 inserted, so their parameter count is always one higher.
        if character.is_vampire:
            raise SyntaxError(str(err)) from err

        # We can't use the auto-generated error message for mortals, because
        # the user might have a mortal and a vampire, and the auto-generated
        # message might be confusing given it says Hunger 0.

        msg = (
            f"**Got {err.count - 3} too many parameters!**\n"
            "*If you're adding traits together, don't forget `+` and `-`!*\n"
            f"**Raw:** `{syntax}`"
        )

        if err.count == 4:
            # We don't want to abort early if it's just a case of Hunger being
            # added to a mortal roll, or it won't roll for vampires. This means
            # a user with only mortals will get the most generic error message,
            # but that can't be helped for now.
            msg += "\n\nRemember: Mortals only need `POOL` and `DIFFICULTY`."
            raise errors.TooManyParameters(4, msg) from err

        # There are too many parameters even for a vampire, so we'll just fail.
        # This works, because SyntaxErrors aren't handled by Haven.
        msg += "\n\n**Vampires:** `POOL` `HUNGER` `DIFFICULTY`\n**Mortals:** `POOL` `DIFFICULTY`"
        raise SyntaxError(msg) from err


async def hidden_dice_allowed(ctx: AppCtx, hide_dice: bool) -> bool:
    """Whether the roll may go ahead. If the user may not hide their dice, they're
    told why. Check before rolling anything, Rouse checks included."""
    if not hide_dice:
        return True
    if ctx.guild is None:
        await ui.embeds.error(ctx, "Hidden dice are not available in DMs.")
        return False

    match await services.settings.hidden_dice_permissions(ctx.guild):
        case HiddenDicePerms.ENABLED:
            return True
        case HiddenDicePerms.ADMIN_ONLY if is_admin(ctx):
            return True
        case HiddenDicePerms.ADMIN_ONLY:
            err = "Only admins can hide their dice on this server."
        case HiddenDicePerms.DISABLED:
            err = "This server doesn't allow hidden dice."

    await ui.embeds.error(ctx, err)
    return False


async def display_outcome(
    ctx: AppCtx,
    player: discord.Member | discord.User,
    character: VChar | None,
    results: Roll,
    comment: str | None,
    listener: RerollListener | None = None,
    timeout: TimeoutHandler | None = None,
    *,
    impairment_category: ImpairmentCategory | None = None,
    hide_dice=False,
):
    """Display the roll results."""
    roll_display = RollDisplay(
        ctx,
        results,
        comment,
        character,
        player,
        listener,
        timeout,
        impairment_category=impairment_category,
        hide_dice=hide_dice,
    )

    await roll_display.display()


async def perform_roll(
    ctx: AppCtx,
    character: VChar | None,
    syntax: str | list[str],
    max_hunger=5,
    *,
    impairment_category: ImpairmentCategory | None = None,
    default_hunger="0",
    default_difficulty="0",
) -> Roll:
    """Parse the syntax and roll the dice, applying any impairment penalty.
    The defaults fill in Hunger and Difficulty if the syntax omits them.

    The pool string and syntax are left as the user wrote them; the penalty is
    recorded on the Roll."""
    parser = RollParser(
        character, syntax, default_hunger=default_hunger, default_difficulty=default_difficulty
    )
    penalty = await impairment_penalty(ctx, character, parser.pool_str, impairment_category)
    pool = parser.pool - IMPAIRMENT_DICE if penalty else parser.pool

    return Roll(
        pool,
        parser.hunger,
        parser.difficulty,
        max_hunger,
        parser.pool_str,
        syntax,
        impairment_penalty=penalty,
        base_pool=parser.pool,
    )


async def impairment_penalty(
    ctx: AppCtx,
    character: VChar | None,
    pool_str: str | None,
    override: ImpairmentCategory | None = None,
) -> Impairment:
    """The Impairment that penalizes the roll, or Impairment.NONE if no penalty
    applies. An override replaces the category detected from the pool and applies
    even if the user turned off auto-impairment."""
    if character is None:
        return Impairment.NONE

    category = override.roll_category if override else RollCategory.from_pool(pool_str)
    impairment = character.impairment_state
    if not impairment.penalizes(category):
        return Impairment.NONE

    # Checked last, so we only look up the setting when it matters
    if override is None and not await services.settings.auto_impairment(ctx):
        return Impairment.NONE

    return impairment


def needs_character(syntax: str) -> bool:
    """Determines whether a roll needs a character."""
    if not syntax:
        return False

    return any(c.isalpha() or c in {"_", VCharTrait.DELIMITER} for c in syntax)


async def stringify_mentions(ctx: AppCtx, sentence: str | None) -> str | None:
    """Replace all raw mentions and channels with their plaintext names."""
    if not sentence:
        return None

    # Use a set to avoid redundant lookups
    if matches := set(re.findall(r"<[@#]!?\d+>", sentence)):
        replacements = {}
        failed_lookups = 0

        for match in matches:
            if (name := await _mention_name(ctx, match)) is not None:
                replacements[match] = name
            else:
                # Realistically, there should be no failed lookups. If there are,
                # the user is probably trying to lock up the bot. Give them three
                # tries in case there's something weird going on before bailing.
                failed_lookups += 1
                if failed_lookups == 3:
                    break

        # Replace the items in the original string
        for match, replacement in replacements.items():
            sentence = sentence.replace(match, replacement)

    return " ".join(sentence.split())


async def _mention_name(ctx: AppCtx, mention: str) -> str | None:
    """The plaintext name for a raw user or channel mention, or None if not found."""
    snowflake = int(re.sub(r"\D", "", mention))

    if mention.startswith("<#"):
        if ctx.guild is None:
            # Channels can only be looked up in guilds
            return None
        channel = ctx.guild.get_channel_or_thread(snowflake)
        return f"#{channel.name}" if channel is not None else None

    if ctx.guild is None:
        # DMs have no members, but we can still find the user
        user = ctx.bot.get_user(snowflake)
        return f"@{user.display_name}" if user is not None else None

    member = ctx.guild.get_member(snowflake)
    if member is None:
        try:
            member = await ctx.guild.fetch_member(snowflake)
        except discord.HTTPException:
            return None
    return f"@{member.display_name}"
