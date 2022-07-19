"""Character selection tool."""

import uuid
from collections import OrderedDict

import discord

import inconnu


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
        character: str = None,
        tip: str = None,
        help: str = None,  # pylint: disable=redefined-builtin
        char_filter: callable = None,
        errmsg: str = "None of your characters can perform this action.",
    ):
        self.uuid = uuid.uuid4().hex  # For ensuring button uniqueness
        self.ctx = ctx
        self.owner = player_lookup(ctx, owner)
        self.tip = tip
        self.help = help
        self.errmsg = errmsg

        self.match = character
        self.filter = char_filter
        self.possibilities = OrderedDict()

    async def fetch(self):
        """Fetch the character(s)."""
        try:
            # If the owner only has one character, or selected one, then we
            # can skip the rest of the fetch and filter routine
            self.match = await inconnu.char_mgr.fetchone(
                self.ctx.guild.id,
                self.owner.id,
                self.match,
            )

        except inconnu.vchar.errors.NoCharactersError as err:
            await inconnu.utils.error(self.ctx, err)
            raise inconnu.common.FetchError() from err

        except inconnu.vchar.errors.UnspecifiedCharacterError as err:
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
                        self.possibilities[self.uuid + char.id] = (char, False)
                        passed += 1
                    except Exception:  # TODO: Proper exception type
                        self.possibilities[self.uuid + char.id] = (char, True)

                if passed == 1:
                    # Only one character passed, so let's find it
                    for char, failed in self.possibilities.values():
                        if not failed:
                            self.match = char
                            break
                elif passed == 0:
                    await inconnu.utils.error(
                        self.ctx,
                        self.errmsg,
                        author=self.owner,
                        help=self.help,
                    )
                    raise inconnu.common.FetchError()

            else:
                self.possibilities = all_chars

            if self.match is None:
                await self._get_user_selection(err)
        return self.match

    async def _get_user_selection(self, err):
        """Present the player's character options."""
        if self.ctx.user != self.owner:
            # We did a lookup, so change the ownership string
            err = str(err).replace("You have", f"{self.owner.display_name} has")

        view = self._create_view()
        await inconnu.utils.error(
            self.ctx,
            err,
            ("Proper syntax", self.tip),
            author=self.owner,
            help=self.help,
            view=view,
            footer="Characters that can't be clicked cannot perform the desired action.",
        )
        await view.wait()

        if (key := view.selected_value) is not None:
            character, _ = self.possibilities[key]
            self.match = character
        else:
            raise inconnu.common.FetchError("No character was selected.")

    def _create_view(self):
        """Create a character selector view."""
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
            options = [(char.name, char.id) for char in self.possibilities.values()]
            components = [inconnu.views.Dropdown("Select a character", *options)]

        view = inconnu.views.BasicSelector(*components)
        return view


def player_lookup(ctx, player: discord.Member):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player is None.

    Raises LookupError if the user doesn't have admin permissions.
    """
    if player is None:
        return ctx.user

    # Players are allowed to look up themselves
    if ctx.user != player:
        if not (
            ctx.user.guild_permissions.administrator or ctx.user.top_role.permissions.administrator
        ):
            raise LookupError("You don't have lookup permissions.")

    return player
