"""Tests for the Haven character selector."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId
from discord.ui import Select

import errors
import services
from ctx import AppCtx
from models import VChar
from services.haven import Haven, _personalize_error, player_lookup
from tests.characters import gen_char
from ui.views.basicselector import BasicSelector

UI_ERROR = "ui.embeds.error"


def make_char(name: str) -> VChar:
    """Generate a PC with a unique ID and the given name."""
    char = gen_char("vampire")
    char.id = PydanticObjectId()
    char.guild = 1
    char.user = 1
    char.name = name

    return char


def make_view(selected_value: str | None) -> BasicSelector:
    """Create a finished BasicSelector with the given selection."""
    view = BasicSelector()
    view.selected_value = selected_value
    view.interaction = MagicMock(spec=discord.Interaction)
    view.stop()  # Make view.wait() return immediately

    return view


@pytest.fixture
def mock_ctx() -> AppCtx:
    """A mock AppCtx with a user and a guild."""
    ctx = MagicMock(spec=AppCtx)
    ctx.user = MagicMock(spec=discord.Member)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 1

    return ctx


def populate(haven: Haven, *chars: tuple[VChar, errors.InconnuError | None]):
    """Fill a Haven's possibilities as its fetch routine would."""
    for char, err in chars:
        haven.possibilities[haven.uuid + char.id_str] = (char, err)


# _create_view()


async def test_create_view_buttons(mock_ctx: AppCtx):
    """Five or fewer characters yield buttons, disabled if they failed the filter."""
    haven = Haven(mock_ctx)
    good = make_char("Alice")
    bad = make_char("Bob")
    populate(haven, (good, None), (bad, errors.InconnuError("Nope")))

    view = haven._create_view()

    assert view is not None
    buttons = [c for c in view.children if isinstance(c, discord.ui.Button)]
    assert len(buttons) == 2

    by_label = {button.label: button for button in buttons}
    assert not by_label[good.name].disabled
    assert by_label[bad.name].disabled
    assert by_label[good.name].custom_id == haven.uuid + good.id_str
    assert by_label[bad.name].custom_id == haven.uuid + bad.id_str


async def test_create_view_dropdown_marks_failed(mock_ctx: AppCtx):
    """Six or more characters yield a Select with failed characters marked."""
    haven = Haven(mock_ctx)
    chars = [make_char(f"Char{i}") for i in range(6)]
    failing = {chars[1].id_str, chars[4].id_str}
    populate(
        haven,
        *(
            (char, errors.InconnuError("Nope") if char.id_str in failing else None)
            for char in chars
        ),
    )

    view = haven._create_view()

    assert view is not None
    selects = [c for c in view.children if isinstance(c, Select)]
    assert len(selects) == 1
    assert len(selects[0].options) == 6

    for option in selects[0].options:
        failed = option.value.removeprefix(haven.uuid) in failing
        assert (option.emoji is not None) == failed


async def test_create_view_dropdown_chunking(mock_ctx: AppCtx):
    """More than 25 characters are split across multiple Selects."""
    haven = Haven(mock_ctx)
    chars = [make_char(f"Char{i:02}") for i in range(30)]
    populate(haven, *((char, None) for char in chars))

    view = haven._create_view()

    assert view is not None
    selects = [c for c in view.children if isinstance(c, Select)]
    assert len(selects) == 2
    assert len(selects[0].options) == 25
    assert len(selects[1].options) == 5

    # Each Select must contain its own chunk, in order
    keys = list(haven.possibilities)
    assert [o.value for o in selects[0].options] == keys[:25]
    assert [o.value for o in selects[1].options] == keys[25:]

    # With multiple menus, placeholders carry a name range
    for select in selects:
        assert "(" in (select.placeholder or "")


def test_create_view_too_many_characters(mock_ctx: AppCtx):
    """More than 100 characters can't be displayed at all."""
    haven = Haven(mock_ctx)
    populate(haven, *((make_char(f"Char{i:03}"), None) for i in range(101)))

    assert haven._create_view() is None


# _get_user_selection()


async def test_selection_valid(mock_ctx: AppCtx):
    """Selecting a valid character sets the match and captures the interaction."""
    haven = Haven(mock_ctx)
    haven.owner = mock_ctx.user
    char = make_char("Alice")
    populate(haven, (char, None))
    view = make_view(haven.uuid + char.id_str)

    with (
        patch.object(Haven, "_create_view", return_value=view),
        patch(UI_ERROR, new_callable=AsyncMock) as mock_error,
    ):
        await haven._get_user_selection("Which character?")

    assert haven.match is char
    assert haven.new_interaction is view.interaction
    mock_error.assert_awaited_once()
    cast(AsyncMock, mock_ctx.delete).assert_awaited_once()


async def test_selection_of_filtered_character_is_rejected(mock_ctx: AppCtx):
    """Choosing a filter-failing character shows its stored error and aborts."""
    haven = Haven(mock_ctx)
    haven.owner = mock_ctx.user
    good = make_char("Alice")
    bad = make_char("Bob")
    filter_err = errors.InconnuError("Bob cannot do that")
    populate(haven, (good, None), (bad, filter_err))
    view = make_view(haven.uuid + bad.id_str)

    with (
        patch.object(Haven, "_create_view", return_value=view),
        patch(UI_ERROR, new_callable=AsyncMock) as mock_error,
    ):
        with pytest.raises(errors.HandledError):
            await haven._get_user_selection("Which character?")

    assert haven.match is None

    # The rejection is the second error message, sent via the click's interaction
    assert mock_error.await_count == 2
    rejection = mock_error.await_args_list[-1]
    assert rejection.args[0] is view.interaction
    assert "Bob cannot do that" in str(rejection.args[1])


async def test_selection_timeout(mock_ctx: AppCtx):
    """A view that finishes without a selection aborts."""
    haven = Haven(mock_ctx)
    haven.owner = mock_ctx.user
    populate(haven, (make_char("Alice"), None))
    view = make_view(None)

    with (
        patch.object(Haven, "_create_view", return_value=view),
        patch(UI_ERROR, new_callable=AsyncMock),
    ):
        with pytest.raises(errors.HandledError):
            await haven._get_user_selection("Which character?")

    assert haven.match is None


async def test_selection_unpresentable(mock_ctx: AppCtx):
    """When no view can be constructed, the user is informed and we abort."""
    haven = Haven(mock_ctx)
    haven.owner = mock_ctx.user

    with (
        patch.object(Haven, "_create_view", return_value=None),
        patch(UI_ERROR, new_callable=AsyncMock) as mock_error,
    ):
        with pytest.raises(errors.HandledError):
            await haven._get_user_selection("Which character?")

    assert "too many characters" in str(mock_error.await_args_list[-1].args[1]).lower()


# fetch()


async def test_fetch_explicit_character_passing_filter(mock_ctx: AppCtx):
    """An explicitly given character that passes the filter is returned."""
    char = make_char("Alice")
    haven = Haven(mock_ctx, character=char.name, char_filter=lambda c: None)

    with patch.object(services.char_mgr, "fetchone", AsyncMock(return_value=char)):
        assert await haven.fetch() is char


async def test_fetch_explicit_character_failing_filter(mock_ctx: AppCtx):
    """An explicitly given character that fails the filter aborts with an error."""

    def char_filter(character: VChar):
        """Reject everyone."""
        raise errors.InconnuError("No dice")

    char = make_char("Alice")
    haven = Haven(mock_ctx, character=char.name, char_filter=char_filter)

    with (
        patch.object(services.char_mgr, "fetchone", AsyncMock(return_value=char)),
        patch(UI_ERROR, new_callable=AsyncMock) as mock_error,
    ):
        with pytest.raises(errors.HandledError):
            await haven.fetch()

    assert "No dice" in str(mock_error.await_args_list[-1].args[1])


async def test_fetch_sole_filter_survivor(mock_ctx: AppCtx):
    """When exactly one character passes the filter, it's returned without a view."""
    alice = make_char("Alice")
    bob = make_char("Bob")

    def char_filter(character: VChar):
        """Only Alice may pass."""
        if character is not alice:
            raise errors.InconnuError("Nope")

    haven = Haven(mock_ctx, char_filter=char_filter)

    with (
        patch.object(
            services.char_mgr,
            "fetchone",
            AsyncMock(side_effect=errors.UnspecifiedCharacterError("Which?")),
        ),
        patch.object(services.char_mgr, "fetchall", AsyncMock(return_value=[alice, bob])),
        patch.object(Haven, "_get_user_selection", new_callable=AsyncMock) as mock_selection,
    ):
        assert await haven.fetch() is alice

    mock_selection.assert_not_awaited()


async def test_fetch_multiple_survivors_presents_selection(mock_ctx: AppCtx):
    """Multiple filter survivors trigger the selection view.

    Regression test: a partial filter failure must not unbind the caught
    UnspecifiedCharacterError before it's passed to _get_user_selection."""
    alice = make_char("Alice")
    bob = make_char("Bob")
    eve = make_char("Eve")

    def char_filter(character: VChar):
        """Eve may not pass."""
        if character is eve:
            raise errors.InconnuError("Nope")

    haven = Haven(mock_ctx, char_filter=char_filter)

    with (
        patch.object(
            services.char_mgr,
            "fetchone",
            AsyncMock(side_effect=errors.UnspecifiedCharacterError("Which?")),
        ),
        patch.object(services.char_mgr, "fetchall", AsyncMock(return_value=[alice, bob, eve])),
        patch.object(Haven, "_get_user_selection", new_callable=AsyncMock) as mock_selection,
    ):
        await haven.fetch()

    mock_selection.assert_awaited_once()
    assert isinstance(mock_selection.await_args_list[-1].args[0], errors.UnspecifiedCharacterError)

    _, stored_err = haven.possibilities[haven.uuid + eve.id_str]
    assert isinstance(stored_err, errors.InconnuError)


async def test_fetch_no_filter_survivors(mock_ctx: AppCtx):
    """If no character passes the filter, the errmsg is shown and we abort."""

    def char_filter(character: VChar):
        """Reject everyone."""
        raise errors.InconnuError("Nope")

    haven = Haven(mock_ctx, char_filter=char_filter, errmsg="You have no worthy characters.")
    chars = [make_char("Alice"), make_char("Bob")]

    with (
        patch.object(
            services.char_mgr,
            "fetchone",
            AsyncMock(side_effect=errors.UnspecifiedCharacterError("Which?")),
        ),
        patch.object(services.char_mgr, "fetchall", AsyncMock(return_value=chars)),
        patch(UI_ERROR, new_callable=AsyncMock) as mock_error,
    ):
        with pytest.raises(errors.HandledError):
            await haven.fetch()

    assert "no worthy characters" in str(mock_error.await_args_list[-1].args[1])


# Helper functions


def test_player_lookup_defaults_to_author(mock_ctx: AppCtx):
    """With no player given, the command author is returned."""
    assert player_lookup(mock_ctx, None, False) is mock_ctx.user


def test_player_lookup_permissions(mock_ctx: AppCtx):
    """Looking up another player requires admin status or allow_lookups."""
    player = MagicMock(spec=discord.Member)

    with patch("services.haven.is_admin", return_value=False):
        with pytest.raises(LookupError):
            player_lookup(mock_ctx, player, False)
        assert player_lookup(mock_ctx, player, True) is player

    with patch("services.haven.is_admin", return_value=True):
        assert player_lookup(mock_ctx, player, False) is player


def test_personalize_error(mock_ctx: AppCtx):
    """Errors are personalized only when the owner isn't the invoking user."""
    same = _personalize_error("You have no characters.", mock_ctx, mock_ctx.user)
    assert same == "You have no characters."

    other = MagicMock(spec=discord.Member)
    other.mention = "@Other"
    personalized = _personalize_error("You have no characters.", mock_ctx, other)
    assert personalized == "@Other has no characters."
