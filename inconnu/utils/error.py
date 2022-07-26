"""Simple error embed generator and presenter."""

import discord

import inconnu


async def error(ctx, err, *fields, **kwargs):
    """Show a nice-looking error message."""
    embed = ErrorEmbed(kwargs.pop("author", ctx.user), err, *fields, **kwargs)

    if (help_url := kwargs.get("help")) is not None:
        # If we have a help URL, we will add some links to the view
        view = kwargs.get("view") or inconnu.views.ReportingView()

        view.add_item(discord.ui.Button(label="Documentation", url=help_url, row=1))
        view.add_item(discord.ui.Button(label="Support", url=inconnu.constants.SUPPORT_URL, row=1))
        view.add_item(discord.ui.Button(label="Patreon", url=inconnu.constants.PATREON, row=1))
    else:
        view = kwargs.get("view", None)

    msg = await inconnu.respond(ctx)(
        embed=embed, view=view, ephemeral=kwargs.get("ephemeral", True)
    )

    if view is not None:
        view.message = msg

    return msg


class ErrorEmbed(discord.Embed):
    """A customizable error embed that accepts many optional parameters."""

    def __init__(self, author, err: str, *fields, **kwargs):
        super().__init__(
            title=kwargs.get("title", "Error"),
            description=str(err),
            color=kwargs.get("color", 0xFF0000),
        )

        # Get the data necessary for the author field
        avatar = inconnu.get_avatar(author)
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
            text=kwargs.get("footer", discord.Embed.Empty),
            icon_url=kwargs.get("footer_icon", discord.Embed.Empty),
        )
