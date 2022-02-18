"""Set up the package interface."""

import os

import discord

from . import character
from .cull import Culler as culler
from . import experience
from . import macros
from . import misc
from . import options
from .roll import Roll
from .settings import Settings as settings
from . import traits
from .vchar import VChar
from . import views


def respond(ctx):
    """Get the proper response callable."""
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            return ctx.followup.send
        return ctx.response.send_message
    return ctx.respond
