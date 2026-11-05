"""Tests for inconnu/settings/menu.py."""

from collections.abc import Iterator
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest
from discord.ui import Button, Select

from bot import InconnuBot
from ctx import AppCtx
from inconnu.settings.menu import OblivionOptions, SettingsIDs, SettingsMenu
from models import HiddenDicePerms, VGuild, VUser

ST_ROLE = 1234
MAX_COMPONENTS = 40  # Discord's limit per message, nested components included


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

    assert vguild.settings.hidden_dice_permissions == HiddenDicePerms.STORYTELLER_ONLY
    assert [opt.value for opt in select.options if opt.default] == [
        HiddenDicePerms.STORYTELLER_ONLY
    ]
    interaction.edit.assert_awaited_once_with(view=menu)
    mock_save.assert_awaited_once()


@pytest.mark.parametrize("option", list(OblivionOptions))
async def test_guild_menu_shows_oblivion_stains(ctx: AppCtx, option: OblivionOptions):
    """The menu opens with every saved Oblivion setting, including Never."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.settings.oblivion_stains = option.to_list()
    select = cast(Select, SettingsMenu(ctx, vguild, admin=True).get_item(SettingsIDs.OBLIVION))

    assert [opt.value for opt in select.options if opt.default] == [option]


def storyteller_role_select(menu: SettingsMenu) -> Select | None:
    """The Storyteller role select, if the menu has one."""
    return cast(Select | None, menu.get_item(SettingsIDs.STORYTELLER_ROLE))


@pytest.mark.parametrize("role_id", [ST_ROLE, None])
@pytest.mark.parametrize("admin", [True, False])
async def test_guild_menu_shows_storyteller_role(ctx: AppCtx, role_id: int | None, admin: bool):
    """The server menu's role select defaults to the role, can be cleared, and
    only admins may use it."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.settings.storyteller_role = role_id
    select = storyteller_role_select(SettingsMenu(ctx, vguild, admin=admin))

    assert select is not None
    assert select.type == discord.ComponentType.role_select
    assert select.min_values == 0
    assert [dv.id for dv in select.default_values] == ([] if role_id is None else [role_id])
    assert select.disabled is not admin


async def test_user_menu_has_no_storyteller_role(ctx: AppCtx):
    """The Storyteller role is a server setting, so users don't get it."""
    assert storyteller_role_select(SettingsMenu(ctx, VUser(user=1), admin=True)) is None


def mock_role(role_id: int) -> discord.Role:
    """A role with the given ID."""
    role = MagicMock(spec=discord.Role)
    role.id = role_id
    role.name = "Storyteller"
    return role


@pytest.mark.parametrize(
    "before,chosen", [(None, ST_ROLE), (ST_ROLE, ST_ROLE + 1), (ST_ROLE, None)]
)
async def test_set_storyteller_role(ctx: AppCtx, before: int | None, chosen: int | None):
    """Choosing a role sets it, and clearing the select removes it. Either way,
    the select's default follows, and the server saves."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.settings.storyteller_role = before
    menu = SettingsMenu(ctx, vguild, admin=True)
    select = storyteller_role_select(menu)
    assert select is not None
    interaction = AsyncMock(spec=discord.Interaction)
    values = [] if chosen is None else [mock_role(chosen)]

    with (
        patch.object(Select, "values", new_callable=PropertyMock, return_value=values),
        patch.object(VGuild, "save", new_callable=AsyncMock) as mock_save,
    ):
        await menu.set_storyteller_role(interaction)

    assert vguild.settings.storyteller_role == chosen
    assert [dv.id for dv in select.default_values] == ([] if chosen is None else [chosen])
    interaction.edit.assert_awaited_once_with(view=menu)
    mock_save.assert_awaited_once()


def count_components(component: dict[str, Any]) -> int:
    """Count a component and everything nested in it."""
    nested = list(component.get("components", []))
    if accessory := component.get("accessory"):
        nested.append(accessory)
    return 1 + sum(count_components(child) for child in nested)


@pytest.mark.parametrize("guild", [True, False])
async def test_menu_within_component_limit(ctx: AppCtx, guild: bool):
    """Discord rejects messages with more than 40 components, counting nested
    ones, so both menus must stay within it."""
    scope = VGuild(guild=1, name="Test Guild") if guild else VUser(user=1)
    menu = SettingsMenu(ctx, scope, admin=True)
    total = sum(count_components(component) for component in menu.to_components())
    assert total <= MAX_COMPONENTS
