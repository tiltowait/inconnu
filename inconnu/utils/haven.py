"""Character selection tool."""

import functools
import uuid
from collections import OrderedDict

import discord

import inconnu
from logger import Logger


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
        owner: discord.Member = None,
        allow_lookups=False,
        character: str = None,
        tip: str = None,
        help: str = None,  # pylint: disable=redefined-builtin
        char_filter: callable = None,
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

    async def fetch(self):
        """Fetch the character(s)."""
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
            Logger.debug("HAVEN: Found explicit character: %s", character.name)

            if self.filter is not None:
                try:
                    self.filter(character)
                    self.match = character
                    Logger.debug("HAVEN: Explicit character %s matches filter", character.name)
                except inconnu.errors.InconnuError as err:
                    Logger.debug(
                        "HAVEN: Explicit character %s does not match filter", character.name
                    )
                    await inconnu.utils.error(self.ctx, err, author=self.owner, help=self.help)
                    raise inconnu.errors.HandledError() from err
            else:
                self.match = character

        except LookupError as err:
            await inconnu.utils.error(self.ctx, err)
            raise inconnu.errors.HandledError() from err

        except inconnu.errors.NoCharactersError as err:
            errmsg = _personalize_error(err, self.ctx, self.owner)
            await inconnu.utils.error(self.ctx, errmsg)
            raise inconnu.errors.HandledError() from err

        except inconnu.errors.CharacterNotFoundError as err:
            errmsg = _personalize_error(err, self.ctx, self.owner)
            await inconnu.utils.error(self.ctx, errmsg)
            raise inconnu.errors.HandledError() from err

        except inconnu.errors.UnspecifiedCharacterError as err:
            # Multiple possible characters. Fetch them all
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
                        Logger.debug("HAVEN: Character %s matches filter", char.name)
                        self.possibilities[self.uuid + char.id] = (char, False)
                        passed += 1
                    except inconnu.errors.InconnuError:
                        Logger.debug("HAVEN: Character %s does not match filter", char.name)
                        self.possibilities[self.uuid + char.id] = (char, True)

                Logger.debug("HAVEN: %s of %s character(s) match filter", passed, len(all_chars))

                if passed == 1:
                    # Only one character passed, so let's find it
                    for char, failed in self.possibilities.values():
                        if not failed:
                            self.match = char
                            Logger.debug("HAVEN: Sole match: %s", char.name)
                            break
                elif passed == 0:
                    await inconnu.utils.error(
                        self.ctx,
                        _personalize_error(self.errmsg, self.ctx, self.owner),
                        author=self.owner,
                        help=self.help,
                    )
                    raise inconnu.errors.HandledError()

            else:
                Logger.debug("HAVEN: Presenting %s character options", len(all_chars))
                self.possibilities = {self.uuid + char.id: (char, False) for char in all_chars}

            if self.match is None:
                await self._get_user_selection(err)
        return self.match

    async def _get_user_selection(self, err):
        """Present the player's character options."""
        err = _personalize_error(err, self.ctx, self.owner)

        view = self._create_view()
        if view is None:
            err = "There are too many characters to display! Please use the `character` parameter."

        await inconnu.utils.error(
            self.ctx,
            err,
            ("Proper syntax", self.tip),
            author=self.owner,
            help=self.help,
            view=view,
            footer="Characters that can't be clicked cannot perform the desired action.",
        )

        if view is None:
            raise inconnu.errors.HandledError("Too many characters.")

        await view.wait()

        if (key := view.selected_value) is not None:
            character, _ = self.possibilities[key]
            self.match = character
            Logger.debug("HAVEN: %s selected", character.name)
        else:
            Logger.debug("HAVEN: No character selected")
            raise inconnu.errors.HandledError("No character was selected.")

    def _create_view(self) -> inconnu.views.BasicSelector | None:
        """Create a character selector view."""
        if len(self.possibilities) > 100:
            Logger.debug("HAVEN: More than 100 characters; selection not possible")
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
            options = [(char.name, self.uuid + char.id) for char, _ in self.possibilities.values()]
            Logger.debug("HAVEN: %s characters are too many for buttons", len(options))

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

        Logger.debug("HAVEN: Created %s component(s)", len(components))
        view = inconnu.views.BasicSelector(*components)
        return view


def player_lookup(ctx, player: discord.Member, allow_lookups: bool):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player is None.

    Raises LookupError if the user doesn't have admin permissions.
    """
    if player is None:
        Logger.debug("HAVEN: No lookup issued")
        return ctx.user

    # Players are allowed to look up themselves
    if ctx.user != player:
        Logger.info(
            "HAVEN: %s#%s looked up %s#%s (%s)",
            ctx.user.name,
            ctx.user.discriminator,
            player.name,
            player.discriminator,
            ctx.guild.name,
        )
        if not (is_admin(ctx.user) or allow_lookups):
            Logger.info(
                "HAVEN: Invalid player lookup by %s#%s (%s)",
                ctx.user.name,
                ctx.user.discriminator,
                ctx.guild.name,
            )
            raise LookupError("You don't have lookup permissions.")

    return player


def is_admin(member: discord.Member):
    """Check if a user has admin permissions."""
    # We can't rely on ctx.channel.permissions_for, because sometimes we
    # receive a PartialMessageable
    privileged = member.top_role.permissions.administrator or member.guild_permissions.administrator
    if not privileged:
        Logger.debug("HAVEN: %s#%s is not an admin", member.name, member.discriminator)
    else:
        Logger.debug("HAVEN: %s#%s is an admin", member.name, member.discriminator)
    return privileged


def _personalize_error(err, ctx, member):
    """Replace "You have" with "{member} has" if ctx.user and member don't match."""
    if member != ctx.user:
        err = str(err).replace("You have", f"{member.mention} has")
        err = err.replace("your", f"{member.mention}'s")
    return err


def haven(url, char_filter=None, errmsg=None):
    """A decorator that handles character fetching duties."""

    def haven_decorator(func):
        """Inner decorator necessary due to argument passing."""

        @functools.wraps(func)
        async def wrapper(ctx, character, *args, **kwargs):
            """Fetch the character and pass it to the wrapped function."""
            haven_ = Haven(
                ctx,
                character=character,
                owner=kwargs.get("player"),
                char_filter=char_filter,
                errmsg=errmsg,
                help=url,
            )
            character = await haven_.fetch()
            return await func(ctx, character, *args, **kwargs)

        return wrapper

    return haven_decorator
