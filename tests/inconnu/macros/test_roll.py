"""Tests for inconnu/macros/roll.py's hunt and Slake menu."""

import importlib
from collections.abc import Iterator
from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord
import pytest

from ctx import AppCtx
from inconnu.macros.roll import _SlakeView, reroll_listener
from inconnu.macros.roll import roll as roll_macro
from inconnu.roll import Roll
from models import HiddenDicePerms, VChar
from models.vchardocs import VCharMacro
from services.haven import Haven
from tests.characters import gen_char

# inconnu.macros exports a roll() function, which shadows the module
HUNT_LISTENERS: dict = getattr(importlib.import_module("inconnu.macros.roll"), "__HUNT_LISTENERS")


@pytest.fixture(autouse=True)
def clear_hunt_listeners() -> Iterator[None]:
    """Keep listeners from leaking between tests."""
    yield
    HUNT_LISTENERS.clear()


@pytest.fixture(autouse=True)
def mock_hidden_dice_permissions() -> Iterator[AsyncMock]:
    """The server allows hidden dice by default."""
    with patch("services.settings.hidden_dice_permissions", new_callable=AsyncMock) as mock:
        mock.return_value = HiddenDicePerms.ENABLED
        yield mock


@pytest.fixture(autouse=True)
def mock_max_hunger() -> Iterator[AsyncMock]:
    """The server uses the standard max Hunger."""
    with patch("services.settings.max_hunger", new_callable=AsyncMock) as mock:
        mock.return_value = 5
        yield mock


@pytest.fixture
def owner() -> discord.Member:
    """The hunter's player."""
    member = MagicMock(spec=discord.Member)
    member.display_name = "tiltowait"
    member.guild_avatar = "https://example.com/avatar.png"
    return member


@pytest.fixture
def character() -> VChar:
    """A Hungry vampire."""
    char = gen_char("vampire")
    char.hunger = 3
    return char


@pytest.fixture
def outcome() -> Roll:
    """A successful hunt roll."""
    roll = Roll(1, 0, 1)
    roll.normal.dice = [6]
    return roll


@pytest.fixture
def ctx(owner: discord.Member) -> AppCtx:
    """The /vm invocation."""
    ctx = MagicMock(spec=AppCtx)
    ctx.user = owner
    ctx.respond = AsyncMock()  # A property on ApplicationContext, so the spec can't infer it
    return ctx


@pytest.fixture
def mock_haven(character: VChar) -> Iterator[MagicMock]:
    """Select the character, which has a hunting macro."""
    character.macros.append(
        VCharMacro(
            name="hunt",
            pool=["3"],
            hunger=False,
            difficulty=1,
            rouses=0,
            reroll_rouses=False,
            staining="show",
            hunt=True,
            comment=None,
        )
    )
    haven = MagicMock(spec=Haven)
    haven.fetch = AsyncMock(return_value=character)
    with patch("inconnu.macros.roll.Haven", return_value=haven) as mock:
        yield mock


@pytest.fixture
def mock_display_outcome() -> Iterator[AsyncMock]:
    """Capture the roll display's arguments."""
    with patch("inconnu.macros.roll.display_outcome", new_callable=AsyncMock) as mock:
        yield mock


async def hunt(ctx: AppCtx, die: int, hide_dice: bool):
    """Roll the hunting macro, with every die showing the given face."""
    with patch("inconnu.d10", side_effect=lambda count: [die] * count):
        await roll_macro(ctx, "hunt", hide_dice=hide_dice)


def make_interaction(owner: discord.Member) -> AsyncMock:
    """A button interaction from the owner."""
    inter = AsyncMock(spec=discord.Interaction)
    inter.user = owner
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    return inter


def show_menu(
    owner: discord.Member, character: VChar, outcome: Roll
) -> tuple[_SlakeView, AsyncMock]:
    """Show the Slake menu for a successful hunt and listen for rerolls."""
    view = _SlakeView(owner, character, outcome)
    menu = AsyncMock(spec=discord.WebhookMessage)
    view.message = menu
    HUNT_LISTENERS[outcome.id] = view
    return view, menu


async def press(view: _SlakeView, inter: AsyncMock, slake_amount: int):
    """Press the menu button that slakes the given amount."""
    custom_id = next(cid for cid, amount in view.buttons.items() if amount == slake_amount)
    inter.custom_id = custom_id
    await view.callback(inter)


@pytest.mark.parametrize("ephemeral", [False, True])
async def test_reroll_into_success_shows_menu(
    owner: discord.Member, character: VChar, outcome: Roll, ephemeral: bool
):
    """Rerolling a failed hunt into success shows the menu, privately for hidden rolls."""
    HUNT_LISTENERS[outcome.id] = None
    inter = make_interaction(owner)

    await reroll_listener(inter, character, outcome, ephemeral=ephemeral)

    inter.respond.assert_awaited_once_with(embed=ANY, view=ANY, ephemeral=ephemeral)
    assert outcome.id not in HUNT_LISTENERS


async def test_reroll_into_failure_deletes_menu(
    owner: discord.Member, character: VChar, outcome: Roll
):
    """Rerolling a successful hunt into failure deletes the unused menu and
    stops its view, so it doesn't time out and delete the menu again."""
    view, menu = show_menu(owner, character, outcome)
    outcome.normal.dice = [2]

    await reroll_listener(make_interaction(owner), character, outcome)

    menu.delete.assert_awaited_once()
    assert view.is_finished()
    assert outcome.id not in HUNT_LISTENERS


async def test_dont_slake_deletes_menu(owner: discord.Member, character: VChar, outcome: Roll):
    """Declining deletes the menu through the interaction, which works even
    when the menu is ephemeral."""
    view, _ = show_menu(owner, character, outcome)
    inter = make_interaction(owner)

    await press(view, inter, _SlakeView.CANCEL_SLAKE)

    inter.response.defer.assert_awaited_once()
    inter.delete_original_response.assert_awaited_once()
    assert outcome.id not in HUNT_LISTENERS


@patch("inconnu.reference.resonance", new_callable=AsyncMock)
@patch("inconnu.misc.slake", new_callable=AsyncMock)
async def test_slaking_keeps_result_after_failed_reroll(
    mock_slake: AsyncMock,
    _: AsyncMock,
    owner: discord.Member,
    character: VChar,
    outcome: Roll,
):
    """Once they've slaked, rerolling the hunt into failure leaves the result alone."""
    view, menu = show_menu(owner, character, outcome)
    inter = make_interaction(owner)

    await press(view, inter, 1)
    outcome.normal.dice = [2]
    await reroll_listener(inter, character, outcome)

    mock_slake.assert_awaited_once_with(inter, character, 1, edit_message=True)
    menu.delete.assert_not_awaited()


async def test_timeout_after_menu_deleted(owner: discord.Member, character: VChar, outcome: Roll):
    """A menu someone else deleted, such as a mod, doesn't break the timeout."""
    view, menu = show_menu(owner, character, outcome)
    menu.delete.side_effect = discord.NotFound(MagicMock(status=404), "Unknown Message")

    await view.on_timeout()

    menu.delete.assert_awaited_once()
    assert outcome.id not in HUNT_LISTENERS


async def test_timeout_deletes_interaction_menu(
    owner: discord.Member, character: VChar, outcome: Roll
):
    """A menu sent as the interaction's response is deleted through the interaction."""
    view = _SlakeView(owner, character, outcome)
    menu = AsyncMock(spec=discord.Interaction)
    view.message = menu

    await view.on_timeout()

    menu.delete_original_response.assert_awaited_once()


# Rolling the macro


@pytest.mark.parametrize("hide_dice", [False, True])
@pytest.mark.usefixtures("mock_haven")
async def test_successful_hunt_shows_menu(
    ctx: AppCtx, mock_display_outcome: AsyncMock, hide_dice: bool
):
    """A successful hunt shows the menu, privately for hidden rolls."""
    await hunt(ctx, 6, hide_dice)

    assert mock_display_outcome.await_args is not None
    assert mock_display_outcome.await_args.kwargs["hide_dice"] is hide_dice
    respond = cast(AsyncMock, ctx.respond)
    respond.assert_awaited_once_with(embed=ANY, view=ANY, ephemeral=hide_dice)


@pytest.mark.usefixtures("mock_haven")
async def test_failed_hunt_waits_for_reroll(ctx: AppCtx, mock_display_outcome: AsyncMock):
    """A failed hunt shows no menu, but listens for a reroll."""
    await hunt(ctx, 2, False)

    assert mock_display_outcome.await_args is not None
    outcome = mock_display_outcome.await_args.args[3]
    cast(AsyncMock, ctx.respond).assert_not_awaited()
    assert HUNT_LISTENERS == {outcome.id: None}


@pytest.mark.parametrize("hide_dice", [False, True])
@pytest.mark.usefixtures("mock_haven")
async def test_failed_hunt_reroll_listener(
    ctx: AppCtx,
    owner: discord.Member,
    character: VChar,
    mock_display_outcome: AsyncMock,
    hide_dice: bool,
):
    """The roll display's reroll listener shows the menu privately for hidden rolls."""
    await hunt(ctx, 2, hide_dice)
    assert mock_display_outcome.await_args is not None
    outcome = mock_display_outcome.await_args.args[3]
    listener = mock_display_outcome.await_args.args[5]

    outcome.normal.dice = [6, 6, 6]
    inter = make_interaction(owner)
    await listener(inter, character, outcome)

    inter.respond.assert_awaited_once_with(embed=ANY, view=ANY, ephemeral=hide_dice)


async def test_hidden_hunt_disallowed(
    ctx: AppCtx,
    mock_haven: MagicMock,
    mock_display_outcome: AsyncMock,
    mock_hidden_dice_permissions: AsyncMock,
):
    """If the server disallows hidden dice, nothing is rolled or looked up."""
    mock_hidden_dice_permissions.return_value = HiddenDicePerms.DISABLED

    with patch("inconnu.macros.roll.rouse", new_callable=AsyncMock) as mock_rouse:
        await hunt(ctx, 6, True)

    mock_haven.assert_not_called()
    mock_rouse.assert_not_awaited()
    mock_display_outcome.assert_not_awaited()
    respond = cast(AsyncMock, ctx.respond)
    assert respond.await_args is not None
    assert respond.await_args.kwargs["ephemeral"] is True
    assert (
        respond.await_args.kwargs["embed"].description == "This server doesn't allow hidden dice."
    )


# Macro modifiers


@pytest.fixture
def mock_punch(character: VChar) -> Iterator[MagicMock]:
    """Select the character, which has a Hungry Strength macro."""
    character.assign_traits({"Strength": 3, "Brawl": 1})
    character.macros.append(
        VCharMacro(
            name="punch",
            pool=["Strength"],
            hunger=True,
            difficulty=2,
            rouses=0,
            reroll_rouses=False,
            staining="show",
            hunt=False,
            comment=None,
        )
    )
    haven = MagicMock(spec=Haven)
    haven.fetch = AsyncMock(return_value=character)
    with patch("inconnu.macros.roll.Haven", return_value=haven) as mock:
        yield mock


@pytest.mark.parametrize(
    "syntax,pool_str,pool,hunger,difficulty",
    [
        ("punch", "Strength", 3, 3, 2),
        ("punch 1", "Strength", 3, 1, 2),
        ("punch 1 4", "Strength", 3, 1, 4),
        ("punch + brawl", "Strength + Brawl", 4, 3, 2),
        ("punch + brawl 1", "Strength + Brawl", 4, 1, 2),
        ("punch + br - 1 1 0", "Strength + Brawl - 1", 3, 1, 0),
        ("punch hun", "Strength", 3, 3, 2),
        ("punch hunger - 1", "Strength", 3, 2, 2),
    ],
)
@pytest.mark.usefixtures("mock_punch")
async def test_macro_modifiers(
    ctx: AppCtx,
    mock_display_outcome: AsyncMock,
    syntax: str,
    pool_str: str,
    pool: int,
    hunger: int,
    difficulty: int,
):
    """Modifiers, Hunger, and Difficulty follow the macro name, as in /vr."""
    await roll_macro(ctx, syntax)

    assert mock_display_outcome.await_args is not None
    outcome = mock_display_outcome.await_args.args[3]
    assert outcome.pool_str == pool_str
    assert outcome.pool == pool
    assert outcome.hunger.count == hunger
    assert outcome.difficulty == difficulty


@pytest.mark.parametrize("syntax", ["punch surge", "punch 1 res", "punch 1 2 3"])
@pytest.mark.usefixtures("mock_punch")
async def test_macro_roll_errors_are_shown(ctx: AppCtx, syntax: str):
    """Invalid Hunger, Difficulty, and extra parameters are shown, not raised."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock_error:
        await roll_macro(ctx, syntax)

    mock_error.assert_awaited_once()


async def roll_error(ctx: AppCtx, syntax: str) -> str:
    """Roll the macro and return the error message shown."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock_error:
        await roll_macro(ctx, syntax)

    mock_error.assert_awaited_once()
    assert mock_error.await_args is not None
    return str(mock_error.await_args.args[1])


@pytest.mark.usefixtures("mock_punch")
async def test_macro_deleted_trait(ctx: AppCtx, character: VChar):
    """A trait missing from the macro's own pool was probably deleted."""
    character.macros[-1].pool = ["Strength", "+", "Dominate"]
    message = await roll_error(ctx, "punch")
    assert "`Dominate`" in message
    assert "Perhaps you deleted it?" in message


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("punch + lung", "has no trait named `lung`"),
        ("punch + s", "`s` is ambiguous"),  # Strength or Surge
    ],
)
@pytest.mark.usefixtures("mock_punch")
async def test_macro_modifier_trait_errors(ctx: AppCtx, syntax: str, expected: str):
    """Trait errors in the player's modifiers are shown as-is."""
    message = await roll_error(ctx, syntax)
    assert expected in message
    assert "deleted" not in message


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("punch 6", "Hunger must be between 0 and 5"),
        ("punch + 100", "Pool cannot exceed 100"),
    ],
)
@pytest.mark.usefixtures("mock_punch")
async def test_macro_range_errors_are_shown(ctx: AppCtx, syntax: str, expected: str):
    """Out-of-range Hunger, Difficulty, and pools show why, not "Unknown syntax"."""
    message = await roll_error(ctx, syntax)
    assert expected in message
    assert "Unknown syntax" not in message


@pytest.mark.usefixtures("mock_punch")
async def test_macro_uses_server_max_hunger(
    ctx: AppCtx, mock_display_outcome: AsyncMock, mock_max_hunger: AsyncMock
):
    """Macros allow Hunger up to the server's max, as /vr does."""
    mock_max_hunger.return_value = 10
    await roll_macro(ctx, "punch + 5 7")

    assert mock_display_outcome.await_args is not None
    outcome = mock_display_outcome.await_args.args[3]
    assert outcome.hunger.count == 7


async def test_invalid_macro_name(ctx: AppCtx):
    """An invalid macro name says why, rather than "Unknown syntax"."""
    message = await roll_error(ctx, "punch2")
    assert message == "Macro names may only contain letters and underscores."


@pytest.mark.usefixtures("mock_punch")
async def test_macro_roll_error_shows_input(ctx: AppCtx):
    """Roll errors show the player's input, since they describe the macro's
    pool rather than its name."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock_error:
        await roll_macro(ctx, "punch 1 2 3")

    assert mock_error.await_args is not None
    assert "Strength" in str(mock_error.await_args.args[1])
    assert mock_error.await_args.args[2] == ("Your Input", "/vm syntax:`punch 1 2 3`")
