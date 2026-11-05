"""Character import command tests."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from ctx import AppCtx
from inconnu.character.import_json import import_progeny

type MockAttachment = MagicMock


def progeny_export(**overrides: Any) -> dict[str, Any]:
    """Build a valid Progeny export payload."""
    data = {
        "name": "Test Vampire",
        "splat": "vampire",
        "health": 5,
        "willpower": 4,
        "humanity": 7,
        "blood_potency": 1,
        "convictions": ["Protect the innocent"],
        "biography": "A short biography.",
        "description": "A short description.",
        "traits": [
            {"name": "Strength", "rating": 3, "type": "attribute", "subtraits": []},
            {"name": "Brawl", "rating": 2, "type": "skill", "subtraits": ["Grappling"]},
        ],
    }
    data.update(overrides)
    return data


def json_attachment(data: dict[str, Any]) -> MockAttachment:
    """Build a Discord attachment containing JSON."""
    attachment = MagicMock(spec=discord.Attachment)
    attachment.size = 1_000
    attachment.read = AsyncMock(return_value=json.dumps(data).encode())
    return attachment


async def test_import_progeny_registers_character(
    ctx: AppCtx, guild: discord.Guild, mock_respond: AsyncMock
):
    attachment = json_attachment(progeny_export())

    with patch("services.char_mgr.register", new_callable=AsyncMock) as register:
        await import_progeny(ctx, attachment)

    character = register.call_args.args[0]
    assert character.guild == guild.id
    assert character.user == ctx.user.id
    assert character.raw_name == "Test Vampire"
    assert character.health == "....."
    assert character.willpower == "...."
    assert character.potency == 1
    assert character.convictions == ["Protect the innocent"]
    assert character.profile.biography == "A short biography."
    assert [trait.name for trait in character.traits] == ["Brawl", "Strength"]
    mock_respond.assert_awaited_once_with("Imported **Test Vampire** from Progeny.", ephemeral=True)


async def test_import_progeny_rejects_invalid_json(ctx: AppCtx):
    attachment = json_attachment({"name": "Incomplete"})

    with (
        patch("services.char_mgr.register", new_callable=AsyncMock) as register,
        patch("ui.embeds.error", new_callable=AsyncMock) as show_error,
    ):
        await import_progeny(ctx, attachment)

    register.assert_not_awaited()
    show_error.assert_awaited_once()
    assert "Invalid Progeny JSON" in show_error.call_args.args[1]
