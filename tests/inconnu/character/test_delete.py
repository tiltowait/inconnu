"""Tests for inconnu/character/delete.py."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord

import errors
from ctx import AppCtx
from inconnu.character.delete import delete
from utils.urls import docs_url


async def test_missing_character_links_help():
    """The error for a missing character links to the docs."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.user = MagicMock(spec=discord.Member)

    with (
        patch(
            "services.char_mgr.fetchone",
            new_callable=AsyncMock,
            side_effect=errors.CharacterNotFoundError("Nope"),
        ),
        patch("ui.embeds.error", new_callable=AsyncMock) as mock_error,
    ):
        await delete(ctx, "Nobody")

    mock_error.assert_awaited_once_with(
        ctx, ANY, help=docs_url("command-reference/characters#character-delete")
    )
