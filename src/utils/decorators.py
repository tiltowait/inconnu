"""Command decorators."""

from collections.abc import Awaitable, Callable
from pathlib import PurePath
from typing import Any, cast

import discord
from discord.ext import commands
from loguru import logger

import errors
from ctx import AppCtx
from utils.permissions import get_or_fetch_supporter


def _app_check(predicate: Callable[[AppCtx], bool | Awaitable[bool]]):
    """commands.check() for slash commands. py-cord types its predicate as taking a
    prefix-command Context, though slash commands pass an ApplicationContext."""
    return commands.check(cast(Any, predicate))


def not_on_lockdown():
    """A decorator that checks if the bot is on lockdown."""

    def predicate(ctx):
        if ctx.bot.lockdown is not None:
            logger.info("BOT: {} ({}) attempted locked-down command", ctx.user.name, ctx.guild.name)
            raise errors.LockdownError()
        logger.debug("BOT: Not on lockdown")
        return True

    return commands.check(predicate)


async def _check_supporter(ctx: AppCtx, user: discord.Member | None = None):
    """Wraps is_supporter() to raise on failure."""
    if not await get_or_fetch_supporter(ctx, user):
        raise errors.NotPremium

    return True


def premium():
    """A decorator for commands that only work for supporters."""
    return _app_check(_check_supporter)


def attachment(*, extensions: list[str] | None = None, filesize: int | None = None):
    """A decorator restricting the command's attachments to the given extensions
    and maximum file size (in bytes)."""
    allowed = {ext.lower().lstrip(".") for ext in extensions or []}

    def predicate(ctx: AppCtx):
        resolved = (ctx.interaction.data or {}).get("resolved", {})
        for file in resolved.get("attachments", {}).values():
            suffix = PurePath(file["filename"]).suffix.lower().lstrip(".")
            if allowed and suffix not in allowed:
                types = ", ".join(f"`.{ext}`" for ext in sorted(allowed))
                raise errors.InvalidAttachment(f"Allowed file types: {types}.")
            if filesize is not None and file["size"] > filesize:
                raise errors.InvalidAttachment(
                    f"The file must be no larger than {_format_size(filesize)}."
                )
        return True

    return _app_check(predicate)


def _format_size(size: int) -> str:
    """Format a byte count as a human-readable, base-2 size."""
    for unit, scale in (("MB", 1024**2), ("KB", 1024)):
        if size >= scale:
            return f"{size / scale:g} {unit}"
    return f"{size} bytes"
