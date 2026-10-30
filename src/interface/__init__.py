"""Miscellaneous shared interface functions."""

from typing import ClassVar

from discord.ext import commands


class CommandCog(commands.Cog):
    """A cog of user-facing commands. Each gets a /help page, which links to its docs."""

    # Link labels and docs URLs, in the order the help page shows them
    docs: ClassVar[dict[str, str]] = {}
