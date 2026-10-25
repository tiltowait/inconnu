"""Tests for inconnu/settings/menu.py."""

from collections.abc import Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ui import Button

from bot import InconnuBot
from ctx import AppCtx
from inconnu.settings.menu import SettingsIDs, SettingsMenu
from models import VGuild, VUser


@pytest.fixture
def ctx() -> AppCtx:
    """A mock AppCtx."""
    ctx = MagicMock(spec=AppCtx)
    ctx.bot = MagicMock(spec=InconnuBot)
    ctx.bot.cmd_mention.return_value = "/resonance"
    return ctx


@pytest.fixture
def mock_save() -> Iterator[AsyncMock]:
    """Prevent VUser saves."""
    with patch.object(VUser, "save", new_callable=AsyncMock) as mock:
        yield mock


def auto_impairment_button(menu: SettingsMenu) -> Button | None:
    """The auto-impairment toggle, if the menu has one."""
    return cast(Button | None, menu.get_item(SettingsIDs.AUTO_IMPAIRMENT))


@pytest.mark.parametrize(
    "enabled,label,style",
    [(True, "Yes", discord.ButtonStyle.primary), (False, "No", discord.ButtonStyle.secondary)],
)
async def test_user_menu_shows_auto_impairment(
    ctx: AppCtx, enabled: bool, label: str, style: discord.ButtonStyle
):
    """The user menu's toggle reflects the current setting."""
    vuser = VUser(user=1)
    vuser.settings.auto_impairment = enabled
    button = auto_impairment_button(SettingsMenu(ctx, vuser, admin=False))

    assert button is not None
    assert button.label == label
    assert button.style == style
    assert not button.disabled


async def test_guild_menu_has_no_auto_impairment(ctx: AppCtx):
    """Auto-impairment is a personal setting, so servers don't get it."""
    vguild = VGuild(guild=1, name="Test Guild")
    assert auto_impairment_button(SettingsMenu(ctx, vguild, admin=True)) is None


async def test_toggle_auto_impairment(ctx: AppCtx, mock_save: AsyncMock):
    """Toggling flips the setting, updates the button, and saves."""
    vuser = VUser(user=1)
    menu = SettingsMenu(ctx, vuser, admin=False)
    interaction = AsyncMock(spec=discord.Interaction)

    await menu.toggle_auto_impairment(interaction)

    assert not vuser.settings.auto_impairment
    button = auto_impairment_button(menu)
    assert button is not None
    assert button.label == "No"
    assert button.style == discord.ButtonStyle.secondary
    interaction.edit.assert_awaited_once_with(view=menu)
    mock_save.assert_awaited_once()

    await menu.toggle_auto_impairment(interaction)
    assert vuser.settings.auto_impairment
