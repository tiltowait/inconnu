"""Custom Discord embed classes and error display utilities."""

import discord

import inconnu
import ui
from utils import cmd_replace, get_avatar
from utils.permissions import is_supporter


class VCharEmbed(discord.Embed):
    """A standardized VChar display."""

    def __init__(self, ctx, character, owner: discord.Member | None = None, link=False, **kwargs):
        owner = owner or ctx.user
        show_thumbnail = kwargs.pop("show_thumbnail", True)

        if link:
            kwargs["url"] = inconnu.profile_url(character.id)

        if "title" in kwargs:
            author_name = character.name
        else:
            author_name = owner.name
            kwargs["title"] = character.name

        if is_supporter(ctx, owner):
            # Premium color
            kwargs["color"] = 0x00A4FF

        super().__init__(**kwargs)

        self.set_author(name=author_name, icon_url=get_avatar(owner))

        if show_thumbnail:
            self.set_thumbnail(url=character.profile_image_url)


class ErrorEmbed(discord.Embed):
    """A customizable error embed that accepts many optional parameters."""

    def __init__(self, author, err: str, *fields, **kwargs):
        super().__init__(
            title=kwargs.get("title", "Error"),
            description=str(err),
            color=kwargs.get("color", 0xFF0000),
        )

        # Get the data necessary for the author field
        avatar = get_avatar(author)
        display_name = author.display_name

        if (character := kwargs.pop("character", None)) is not None:
            # If a character was supplied, we override display_name
            if isinstance(character, str):
                display_name = character
            else:
                display_name = character.name

        self.set_author(name=display_name, icon_url=avatar)

        for field in fields:
            name, value = field
            self.add_field(name=name, value=value, inline=False)

        self.set_footer(
            text=kwargs.get("footer", None),
            icon_url=kwargs.get("footer_icon", None),
        )


async def error(ctx, err, *fields, **kwargs):
    """Show a nice-looking error message."""
    embed = ErrorEmbed(kwargs.pop("author", ctx.user), err, *fields, **kwargs)

    if (help_url := kwargs.get("help")) is not None:
        # If we have a help URL, we will add some links to the view
        view = kwargs.get("view") or ui.views.ReportingView()

        view.add_item(discord.ui.Button(label="Documentation", url=help_url, row=4))
        view.add_item(discord.ui.Button(label="Support", url=inconnu.constants.SUPPORT_URL, row=4))
        view.add_item(discord.ui.Button(label="Patreon", url=inconnu.constants.PATREON, row=4))
    else:
        view = kwargs.get("view", None)

    msg = await cmd_replace(
        ctx,
        embed=embed,
        view=view,
        ephemeral=kwargs.get("ephemeral", True),
        allowed_mentions=discord.AllowedMentions.none(),
    )

    if view is not None:
        view.message = msg

    return msg
