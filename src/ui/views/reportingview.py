"""Base Inconnu View."""

import discord


class ReportingView(discord.ui.View):
    """A View whose errors reach the error reporter. discord.ui.View already
    dispatches them to ErrorListener, so this only marks the intent."""
