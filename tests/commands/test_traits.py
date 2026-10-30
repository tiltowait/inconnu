"""Tests for /traits update and /traits delete character filtering."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId

import errors
import services
import tests.characters
from ctx import AppCtx
from inconnu.traits import delete, update
from models import VChar


def make_char(name: str, traits: dict[str, int]) -> VChar:
    """Generate a vampire with a unique ID, the given name, and traits."""
    char = tests.characters.gen_char("vampire")
    char.id = PydanticObjectId()
    char.name = name
    char.assign_traits(traits)

    return char


@pytest.fixture
def alice() -> VChar:
    """A character with Foo."""
    return make_char("Alice", {"Foo": 1, "Strength": 2})


@pytest.fixture
def bob() -> VChar:
    """A character with Bar."""
    return make_char("Bob", {"Bar": 1, "Strength": 2})


@pytest.fixture(autouse=True)
def mock_chars(alice: VChar, bob: VChar) -> Generator[AsyncMock]:
    """Give the user both characters without specifying one."""
    with (
        patch.object(
            services.char_mgr,
            "fetchone",
            AsyncMock(side_effect=errors.UnspecifiedCharacterError("Which?")),
        ) as fetchone,
        patch.object(services.char_mgr, "fetchall", AsyncMock(return_value=[alice, bob])),
    ):
        yield fetchone


@pytest.fixture
def mock_selection() -> Generator[AsyncMock]:
    """Stand in for the character selector, ending the command when it's shown."""
    with patch(
        "services.haven.Haven._get_user_selection",
        AsyncMock(side_effect=errors.HandledError()),
    ) as mock:
        yield mock


@pytest.fixture
def mock_error() -> Generator[AsyncMock]:
    """Capture error embeds."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock:
        yield mock


async def test_update_selects_sole_owner(
    ctx: AppCtx, alice: VChar, bob: VChar, mock_respond: AsyncMock, mock_char_save: AsyncMock
):
    """Only Alice has Foo, so she's updated without a selector."""
    await update(ctx, None, "Foo=3")

    assert alice.find_trait("Foo").rating == 3
    assert not bob.has_trait("Foo")
    mock_respond.assert_awaited_once()


async def test_update_matches_any_trait(
    ctx: AppCtx, alice: VChar, mock_respond: AsyncMock, mock_char_save: AsyncMock
):
    """A character needs only one of the traits to be chosen."""
    await update(ctx, None, "Foo=3 Baz=2")

    assert alice.find_trait("Foo").rating == 3


async def test_update_shows_selector_for_multiple_owners(
    ctx: AppCtx, mock_selection: AsyncMock, mock_char_save: AsyncMock
):
    """Both characters have Strength, so the user must choose."""
    with pytest.raises(errors.HandledError):
        await update(ctx, None, "Strength=3")

    mock_selection.assert_awaited_once()
    mock_char_save.assert_not_awaited()


async def test_update_no_owners(ctx: AppCtx, mock_error: AsyncMock, mock_char_save: AsyncMock):
    """No character has the trait, so the user is told so."""
    with pytest.raises(errors.HandledError):
        await update(ctx, None, "Baz=3")

    assert mock_error.await_args is not None
    assert mock_error.await_args.args[1] == "None of your characters have a trait named `Baz`."
    mock_char_save.assert_not_awaited()


async def test_update_syntax_error_before_lookup(
    ctx: AppCtx, mock_chars: AsyncMock, mock_error: AsyncMock
):
    """Bad input is rejected before any character is fetched."""
    await update(ctx, None, "Foo=9")

    mock_error.assert_awaited_once()
    mock_chars.assert_not_awaited()


async def test_delete_selects_sole_owner(
    ctx: AppCtx, alice: VChar, bob: VChar, mock_respond: AsyncMock, mock_char_save: AsyncMock
):
    """Only Bob has Bar, so it's deleted from him without a selector."""
    await delete(ctx, None, "Bar Baz")

    assert not bob.has_trait("Bar")
    assert alice.has_trait("Foo")
    mock_char_save.assert_awaited_once()


async def test_delete_core_trait_shows_selector(
    ctx: AppCtx, mock_selection: AsyncMock, mock_char_save: AsyncMock
):
    """Every character can zero a core trait, so none are filtered out."""
    with pytest.raises(errors.HandledError):
        await delete(ctx, None, "Foo Wits")

    mock_selection.assert_awaited_once()
    mock_char_save.assert_not_awaited()


async def test_delete_no_owners(ctx: AppCtx, mock_error: AsyncMock, mock_char_save: AsyncMock):
    """No character has the traits, so the user is told so."""
    with pytest.raises(errors.HandledError):
        await delete(ctx, None, "Baz Qux")

    assert mock_error.await_args is not None
    assert (
        mock_error.await_args.args[1]
        == "None of your characters have any of these traits: `Baz`, `Qux`."
    )
    mock_char_save.assert_not_awaited()
