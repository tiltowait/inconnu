"""Custom Discord embed classes."""

import discord

import inconnu
from inconnu.utils.permissions import is_supporter


class VCharEmbed(discord.Embed):
    """A standardized VChar display."""

    def __init__(self, ctx, character, owner: discord.Member | None = None, link=False, **kwargs):
        owner = owner or ctx.user
        show_thumbnail = kwargs.pop("show_thumbnail", True)

        if link:
            kwargs["url"] = inconnu.profile_url(character.pk)

        if "title" in kwargs:
            author_name = character.name
        else:
            author_name = owner.name
            kwargs["title"] = character.name

        if is_supporter(ctx, owner):
            # Premium color
            kwargs["color"] = 0x00A4FF

        super().__init__(**kwargs)

        self.set_author(name=author_name, icon_url=inconnu.get_avatar(owner))

        if show_thumbnail:
            self.set_thumbnail(url=character.profile_image_url)
