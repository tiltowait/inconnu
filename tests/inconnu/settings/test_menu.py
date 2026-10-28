"""Tests for inconnu/settings/menu.py."""

from collections.abc import Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest
from discord.ui import Button, Select

from bot import InconnuBot
from ctx import AppCtx
from inconnu.settings.menu import OblivionOptions, SettingsIDs, SettingsMenu
from models import HiddenDicePerms, VGuild, VUser


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


def hidden_dice_select(menu: SettingsMenu) -> Select | None:
    """The hidden dice permissions select, if the menu has one."""
    return cast(Select | None, menu.get_item(SettingsIDs.HIDDEN_DICE))


@pytest.mark.parametrize("perms", list(HiddenDicePerms))
@pytest.mark.parametrize("admin", [True, False])
async def test_guild_menu_shows_hidden_dice(ctx: AppCtx, perms: HiddenDicePerms, admin: bool):
    """The server menu's select defaults to the setting, and only admins may use it."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.settings.hidden_dice_permissions = perms
    select = hidden_dice_select(SettingsMenu(ctx, vguild, admin=admin))

    assert select is not None
    assert [opt.value for opt in select.options if opt.default] == [perms]
    assert [opt.label for opt in select.options] == [p.description for p in HiddenDicePerms]
    assert select.disabled is not admin


async def test_user_menu_has_no_hidden_dice(ctx: AppCtx):
    """Hidden dice permission is a server setting, so users don't get it."""
    assert hidden_dice_select(SettingsMenu(ctx, VUser(user=1), admin=True)) is None


async def test_set_hidden_dice_permissions(ctx: AppCtx):
    """Choosing an option updates the setting and the select's default, and saves."""
    vguild = VGuild(guild=1, name="Test Guild")
    menu = SettingsMenu(ctx, vguild, admin=True)
    select = hidden_dice_select(menu)
    assert select is not None
    interaction = AsyncMock(spec=discord.Interaction)

    with (
        patch.object(Select, "values", new_callable=PropertyMock, return_value=["admin_only"]),
        patch.object(VGuild, "save", new_callable=AsyncMock) as mock_save,
    ):
        await menu.set_hidden_dice_permissions(interaction)

    assert vguild.settings.hidden_dice_permissions == HiddenDicePerms.ADMIN_ONLY
    assert [opt.value for opt in select.options if opt.default] == [HiddenDicePerms.ADMIN_ONLY]
    interaction.edit.assert_awaited_once_with(view=menu)
    mock_save.assert_awaited_once()


@pytest.mark.parametrize("option", list(OblivionOptions))
async def test_guild_menu_shows_oblivion_stains(ctx: AppCtx, option: OblivionOptions):
    """The menu opens with every saved Oblivion setting, including Never."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.settings.oblivion_stains = option.to_list()
    select = cast(Select, SettingsMenu(ctx, vguild, admin=True).get_item(SettingsIDs.OBLIVION))

    assert [opt.value for opt in select.options if opt.default] == [option]
