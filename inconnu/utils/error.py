"""Simple error embed generator."""

import discord
import inconnu


async def error(ctx, err, *fields, **kwargs):
    """Show an error message."""
    embed = ErrorEmbed(kwargs.pop("author", ctx.user), err, *fields, **kwargs)

    if (help := kwargs.get("help")) is not None:
        # If we have a help URL, we will add some links to the view
        view = kwargs.get("view", discord.ui.View())

        view.add_item(discord.ui.Button(label="Documentation", url=help, row=1))
        view.add_item(discord.ui.Button(label="Support", url=inconnu.constants.SUPPORT_URL, row=1))
    else:
        view = kwargs.get("view", discord.MISSING)

    msg = await inconnu.respond(ctx)(
        embed=embed, view=view, ephemeral=kwargs.get("ephemeral", True)
    )
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
            self.add_field(name=name, value=value)

        self.set_footer(
            text=kwargs.get("footer", discord.Embed.Empty),
            icon_url=kwargs.get("footer_icon", discord.Embed.Empty),
        )
