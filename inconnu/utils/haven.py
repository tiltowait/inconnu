"""Character selection tool."""

import functools
import uuid
from collections import OrderedDict
from typing import Awaitable, Callable, Concatenate, ParamSpec, TypeVar, cast

import discord
from loguru import logger

import inconnu
from inconnu.models import VChar
from inconnu.utils.permissions import is_admin
from inconnu.views.basicselector import BasicSelector

P = ParamSpec("P")
T = TypeVar("T")


class Haven:  # pylint: disable=too-few-public-methods
    """
    A class for fetching a desired character.

    If the user has only one character, then it will be returned automatically.
    Automatic return will also happen if the optional `character` parameter is
    supplied.

    If the user has multiple characters and has not manually specified one,
    then we generate a list of available characters and filter them based on
    an optional filter function. This function must be failable and raise a
    VCharError or one of its subclasses.

    If only one character satisfies the filter, then that character is returned
    just as if the user had explicitly supplied it.

    If multiple characters satisfy the filter, or if no filter is supplied, we
    present a selection list. Characters that do not satisfy the filter are
    disabled. This is done (rather than omitting them completely) to prevent
    users from worrying that their character was somehow deleted.
    """

    def __init__(
        self,
        ctx,
        *,
        owner: discord.Member | None = None,
        allow_lookups=False,
        character: str | None = None,
        tip: str | None = None,
        help: str | None = None,  # pylint: disable=redefined-builtin
        char_filter: Callable | None = None,
        errmsg: str = "None of your characters can perform this action.",
    ):
        self.uuid = uuid.uuid4().hex  # For ensuring button uniqueness
        self.ctx = ctx
        self._given_owner = owner
        self.owner = None
        self.allow_lookups = allow_lookups
        self.tip = tip
        self.help = help
        self.errmsg = errmsg

        self.match = character
        self.filter = char_filter
        self.possibilities = OrderedDict()

        # When the view's button is clicked, the view doesn't make use of the
        # interaction. Instead, we'll store it so that the function calling
        # Haven can make use of it. This speeds up response times (one fewer
        # API call).
        self.new_interaction = None

    async def fetch(self):
        """Fetch the sole-matching character or raise a CharacterError."""
        try:
            # Confirm ownership. We weren't able to do so in a sync context,
            # but now that we're async, we can do so and send an error message
            # if it's invalid.
            self.owner = player_lookup(self.ctx, self._given_owner, self.allow_lookups)

            # If the owner only has one character, or selected one, then we
            # can skip the rest of the fetch and filter routine
            character = await inconnu.char_mgr.fetchone(
                self.ctx.guild.id,
                self.owner.id,
                self.match,
            )
            logger.debug("HAVEN: Found explicit character: {}", character.name)

            if self.filter is not None:
                try:
                    self.filter(character)
                    self.match = character
                    logger.debug("HAVEN: Explicit character {} matches filter", character.name)
                except inconnu.errors.InconnuError as err:
                    logger.debug(
                        "HAVEN: Explicit character {} does not match filter", character.name
                    )
                    await inconnu.embeds.error(self.ctx, err, author=self.owner, help=self.help)
                    raise inconnu.errors.HandledError() from err
            else:
                self.match = character

        except LookupError as err:
            await inconnu.embeds.error(self.ctx, err)
            raise inconnu.errors.HandledError() from err

        except inconnu.errors.NoCharactersError as err:
            errmsg = _personalize_error(err, self.ctx, self.owner)
            await inconnu.embeds.error(self.ctx, errmsg)
            raise inconnu.errors.HandledError() from err

        except inconnu.errors.CharacterNotFoundError as err:
            errmsg = _personalize_error(err, self.ctx, self.owner)
            await inconnu.embeds.error(self.ctx, errmsg)
            raise inconnu.errors.HandledError() from err

        except inconnu.errors.UnspecifiedCharacterError as err:
            # Multiple possible characters. Fetch them all
            assert self.owner is not None
            all_chars = await inconnu.char_mgr.fetchall(self.ctx.guild.id, self.owner.id)
            if self.filter is not None:
                # If we were given a filter, then we can only add those
                # characters that match the filter and potentially go down
                # to a single valid character
                self.possibilities.clear()
                passed = 0

                for char in all_chars:
                    try:
                        self.filter(char)
                        logger.debug("HAVEN: Character {} matches filter", char.name)
                        self.possibilities[self.uuid + char.id_str] = (char, False)
                        passed += 1
                    except inconnu.errors.InconnuError:
                        logger.debug("HAVEN: Character {} does not match filter", char.name)
                        self.possibilities[self.uuid + char.id_str] = (char, True)

                logger.debug("HAVEN: {} of {} character(s) match filter", passed, len(all_chars))

                if passed == 1:
                    # Only one character passed, so let's find it
                    for char, failed in self.possibilities.values():
                        if not failed:
                            self.match = char
                            logger.debug("HAVEN: Sole match: {}", char.name)
                            break
                elif passed == 0:
                    await inconnu.embeds.error(
                        self.ctx,
                        _personalize_error(self.errmsg, self.ctx, self.owner),
                        author=self.owner,
                        help=self.help,
                    )
                    raise inconnu.errors.HandledError()

            else:
                logger.debug("HAVEN: Presenting {} character options", len(all_chars))
                self.possibilities = {self.uuid + char.id_str: (char, False) for char in all_chars}

            if self.match is None:
                await self._get_user_selection(err)

        return cast(inconnu.models.VChar, self.match)

    async def _get_user_selection(self, err):
        """Present the player's character options."""
        err = _personalize_error(err, self.ctx, self.owner)

        view = self._create_view()
        if view is None:
            err = "There are too many characters to display! Please use the `character` parameter."

        await inconnu.embeds.error(
            self.ctx,
            err,
            # ("Proper syntax", self.tip),
            author=self.owner,
            help=self.help,
            view=view,
            footer="Characters that can't be clicked cannot perform the desired action.",
        )

        if view is None:
            raise inconnu.errors.HandledError("Too many characters.")

        await view.wait()
        self.new_interaction = view.interaction
        await self.ctx.delete()

        if (key := view.selected_value) is not None:
            character, _ = self.possibilities[key]
            self.match = character
            logger.debug("HAVEN: {} selected", character.name)
        else:
            logger.debug("HAVEN: No character selected")
            raise inconnu.errors.HandledError("No character was selected.")

    def _create_view(self) -> BasicSelector | None:
        """Create a character selector view."""
        if len(self.possibilities) > 100:
            logger.debug("HAVEN: More than 100 characters; selection not possible")
            return None

        components = []
        if len(self.possibilities) < 6:
            for key, value in self.possibilities.items():
                char, disabled = value
                components.append(
                    discord.ui.Button(
                        label=char.name,
                        custom_id=key,
                        style=discord.ButtonStyle.primary,
                        disabled=disabled,
                    )
                )
        else:
            options = [
                (char.name, self.uuid + char.id_str) for char, _ in self.possibilities.values()
            ]
            logger.debug("HAVEN: {} characters are too many for buttons", len(options))

            # A very small number of users have more than 25 characters, so we
            # might need to display multiple select menus
            components = []
            show_name_range = len(options) > 25

            while options:
                selection = options[:25]
                begin_letter = selection[0][0][0]
                end_letter = selection[-1][0][0]

                placeholder = "Select a character"
                if show_name_range:
                    # For example: "Select a character (A-S)"
                    if begin_letter == end_letter:
                        name_range = f" ({begin_letter})"
                    else:
                        name_range = f" ({begin_letter}-{end_letter})"
                    placeholder += name_range

                components.append(inconnu.views.Dropdown(placeholder, *selection))
                options = options[25:]

        logger.debug("HAVEN: Created {} component(s)", len(components))
        view = BasicSelector(*components)
        return view


def player_lookup(ctx, player: discord.Member | None, allow_lookups: bool):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player is None.

    Raises LookupError if the user doesn't have admin permissions.
    """
    if player is None:
        logger.debug("HAVEN: No lookup issued")
        return ctx.user

    # Players are allowed to look up themselves
    if ctx.user != player:
        logger.info("HAVEN: {} looked up {} ({})", ctx.user.name, player.name, ctx.guild.name)
        if not (is_admin(ctx) or allow_lookups):
            logger.info("HAVEN: Invalid player lookup by {} ({})", ctx.user.name, ctx.guild.name)
            raise LookupError("You don't have lookup permissions.")

    return player


def _personalize_error(err, ctx, member):
    """Replace "You have" with "{member} has" if ctx.user and member don't match."""
    if member != ctx.user:
        err = str(err).replace("You have", f"{member.mention} has")
        err = err.replace("your", f"{member.mention}'s")
    return err


def haven(
    url: str,
    char_filter: Callable[[VChar], None] | None = None,
    errmsg: str = "",
    allow_lookups: bool = False,
) -> Callable[
    [Callable[Concatenate[discord.ApplicationContext, VChar, P], Awaitable[T]]],
    Callable[Concatenate[discord.ApplicationContext, str | None, P], Awaitable[T]],
]:
    """A decorator that handles character fetching duties.

    Transforms functions that accept VChar into functions that accept str | None.
    The decorator handles character lookup and validation automatically.
    """

    def haven_decorator(
        func: Callable[Concatenate[discord.ApplicationContext, VChar, P], Awaitable[T]],
    ) -> Callable[Concatenate[discord.ApplicationContext, str | None, P], Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(
            ctx: discord.ApplicationContext,
            character: str | None,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> T:
            logger.debug("@HAVEN: Using @haven")
            player: discord.Member | None
            if "player" in kwargs:
                # Capture the player lookup
                logger.debug("@HAVEN: Found 'player' in kwargs")
                player = kwargs["player"]  # type: ignore[assignment]
                player_kwargs = True
            else:
                player = None
                player_kwargs = False

            # Actual character fetching
            haven_ = Haven(
                ctx,
                character=character,
                owner=player,
                char_filter=char_filter,
                errmsg=errmsg,
                allow_lookups=allow_lookups,
                help=url,
            )
            fetched_character = await haven_.fetch()

            if player_kwargs:
                logger.debug("@HAVEN: Replacing 'player' in kwargs")
                kwargs["player"] = haven_.owner  # type: ignore[typeddict-item]

            if haven_.new_interaction is not None:
                logger.debug("@HAVEN: Replacing the interaction with a new one")
                ctx.interaction = haven_.new_interaction

            return await func(ctx, fetched_character, *args, **kwargs)

        return wrapper

    return haven_decorator
