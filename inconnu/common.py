"""common.py - Commonly used functions."""

import re
from types import SimpleNamespace
from uuid import uuid4

import discord
from discord.ui import Button, View

import inconnu


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun."""
    nouns = {"success": "successes", "die": "dice"}

    pluralized = f"{value} {noun}"
    if value != 1:
        if noun in nouns:
            pluralized = f"{value} {nouns[noun]}"
        else:
            pluralized += "s"

    return pluralized


async def present_error(
    ctx,
    error,
    *fields,
    author=None,
    character: str = None,
    footer: str = None,
    help_url: str = None,
    view=None,
    ephemeral=True,
):
    """
    Display an error in a nice embed.
    Args:
        ctx: The Discord context for sending the response.
        error: The error message to display.
        fields (list): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        author (discord.Member): The member the message is attributed to, if not the same as ctx
        character (str): The character the message is attributed to
        footer (str): Footer text to display.
        help_url (str): The documentation URL for the error.
        components (list): Buttons or selection menus to add to the message.
    """
    if await inconnu.settings.accessible(ctx):
        content = __error_text(error, *fields, footer=footer)
        msg_contents = {"content": content}
    else:
        embed = __error_embed(
            ctx,
            error,
            *fields,
            author=author,
            character=character,
            footer=footer,
        )
        msg_contents = {"embed": embed}

    # Finish preparing the response
    msg_contents["ephemeral"] = ephemeral
    msg_contents["allowed_mentions"] = discord.AllowedMentions.none()

    if help_url is not None:
        # If we have a help URL, we will add some links to the view
        view = view or View()

        view.add_item(Button(label="Documentation", url=help_url, row=1))
        view.add_item(Button(label="Support", url=inconnu.constants.SUPPORT_URL, row=1))

    if view is not None:
        msg_contents["view"] = view

    msg = await inconnu.respond(ctx)(**msg_contents)

    if isinstance(view, inconnu.views.DisablingView):
        # So it can automatically disable its buttons
        view.message = msg

    return msg


def __error_embed(
    ctx,
    error,
    *fields,
    author=None,
    character: str = None,
    footer: str = None,
):
    # Figure out the author
    if author is None:
        avatar = inconnu.get_avatar(ctx.user)
        display_name = ctx.user.display_name
    else:
        avatar = inconnu.get_avatar(author)
        display_name = author.display_name

    if character is not None:
        if isinstance(character, str):
            display_name = character
        else:
            display_name = character.name

    embed = discord.Embed(title="Error", description=str(error), color=0xFF0000)
    embed.set_author(name=display_name, icon_url=avatar)

    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=False)

    if footer is not None:
        embed.set_footer(text=footer)

    return embed


def __error_text(
    error,
    *fields,
    footer: str = None,
):
    """Display the error as plaintext."""
    contents = ["**Error**", str(error) + "\n"]

    for field in fields:
        contents.append(f"{field[0]}: {field[1]}")

    if footer is not None:
        contents.append(f"```{footer}```")

    return "\n".join(contents)


async def report_update(*, ctx, character, title, message, **kwargs):
    """Display character updates in the update channel."""
    if update_channel := await inconnu.settings.update_channel(ctx.guild):
        msg = kwargs.pop("msg", discord.Embed.Empty)
        if msg:
            msg = msg.jump_url

        embed = discord.Embed(
            title=title,
            description=message,
            url=msg,
            color=kwargs.pop("color", discord.Embed.Empty),
        )
        embed.set_author(name=character.name, icon_url=inconnu.get_avatar(ctx.user))

        mentions = discord.AllowedMentions(users=False)

        await update_channel.send(embed=embed, allowed_mentions=mentions)


async def select_character(ctx, err, help_url, tip, player=None):
    """
    A prompt for the user to select a character from a list.
    Args:
        ctx: Discord context
        err: An error message to display
        help_url: A URL pointing to the documentation
        tip (tuple): A name and value for an embed field
        player: (Optional) A Discord member to query instead
    """
    if ctx.user != player:
        user = player
        err = str(err).replace("You have", f"{user.display_name} has")
    else:
        user = ctx.user

    options = await character_options(ctx.guild.id, user.id)
    msg = await present_error(
        ctx, err, (tip[0], tip[1]), author=user, help_url=help_url, view=options.view
    )

    options.view.message = msg
    await options.view.wait()

    if (character_id := options.view.selected_value) is not None:
        # These button IDs follow the format "character_id UUID", so we need
        # to remove the UUID to get just the character ID
        character_id = character_id.split()[0]

    return character_id


async def character_options(guild: int, user: int):
    """
    Generate a dictionary of characters keyed by ID plus components for selecting them.
    Under 6 characters: Buttons
    Six or more characters: Selections
    """
    characters = await inconnu.char_mgr.fetchall(guild, user)
    chardict = {char.id: char for char in characters}

    # We have to use an ugly hack for this. If we just use the character's ID
    # as the button's identifier, then multiple displays of these buttons will
    # work incorrectly: click on one, and the other instances stop responding.
    # Therefore, we tack a UUID to the end. Later, we will split the custom ID
    # so we can pull just the character ID.

    if len(characters) < 6:
        components = [
            Button(
                label=char.name, custom_id=f"{char.id} {uuid4()}", style=discord.ButtonStyle.primary
            )
            for char in characters
        ]
    else:
        options = [(char.name, char.id) for char in characters]
        components = [inconnu.views.Dropdown("Select a character", *options)]

    view = inconnu.views.BasicSelector(*components)
    return SimpleNamespace(characters=chardict, view=view)


async def player_lookup(ctx, player: discord.Member):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player_str is None.

    Raises PermissionError if the user doesn't have admin permissions.
    Raises ValueError if player is not a valid player name.
    """
    if player is None:
        return ctx.user

    # Players are allowed to look up themselves
    if (not ctx.user.guild_permissions.administrator) and ctx.user != player:
        raise LookupError("You don't have lookup permissions.")

    return player


class FetchError(Exception):
    """An error for when we are unable to fetch a character."""


async def fetch_character(ctx, character, tip, help_url, owner=None):
    """
    Attempt to fetch a character, presenting a selection dialogue if necessary.
    Args:
        ctx: The Discord context for displaying messages and retrieving guild info
        character (str): The name of the character to fetch. Optional.
        tip (str): The proper syntax for the command
        help_url (str): The URL of the button to display on any error messages
        userid (int): The ID of the user who owns the character, if different from the ctx author
    """
    if isinstance(character, inconnu.VChar):
        return character

    try:
        owner = owner or ctx.user
        return await inconnu.char_mgr.fetchone(ctx.guild.id, owner.id, character)

    except inconnu.vchar.errors.UnspecifiedCharacterError as err:
        character = await select_character(ctx, err, help_url, ("Proper syntax", tip), player=owner)

        if character is None:
            raise FetchError("No character was selected.") from err

        return await inconnu.char_mgr.fetchone(ctx.guild.id, owner.id, character)

    except inconnu.vchar.errors.CharacterError as err:
        await present_error(ctx, err, help_url=help_url, author=owner)
        raise FetchError(str(err)) from err


def paginate(page_size: int, *contents) -> list:
    """Break the contents into pages to fit a Discord message."""
    contents = list(contents)
    pages = []

    if isinstance(contents[0], str):
        page = contents.pop(0)
        for item in contents:
            if len(page) >= page_size:
                pages.append(page)
                page = item
            else:
                page += "\n" + item

    else:
        # [[(header, contents), (header, contents), (header, contents)]]
        page = [contents.pop(0)]
        page_len = len(page[0].name) + len(page[0].value)
        for item in contents:
            if page_len >= page_size:
                pages.append(page)
                page = [item]
                page_len = len(item.name) + len(item.value)
            else:
                page_len += len(item.name) + len(item.value)
                page.append(item)

    pages.append(page)
    return pages


def contains_digit(string: str):
    """Determine whether a string contains a digit."""
    if string is None:
        return False
    return bool(re.search(r"\d", string))  # Much faster than using any()
