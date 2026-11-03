"""Experience command tests."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import inconnu.experience.award_deduct as award_deduct_module
from ctx import AppCtx
from inconnu.experience.award_deduct import award_or_deduct
from inconnu.experience.remove import remove_entry
from models.vchar import VChar
from models.vchardocs import VCharExperienceEntry


@pytest.fixture
def mock_error() -> Iterator[AsyncMock]:
    """Patch the error embed."""
    with patch.object(award_deduct_module.ui.embeds, "error", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def allow_all() -> Iterator[None]:
    """Let the user adjust both scopes of XP."""
    unspent_patch, lifetime_patch = _permissions(True, True)
    with unspent_patch, lifetime_patch:
        yield


def _permissions(unspent: bool, lifetime: bool):
    """Patch the server's XP permissions."""
    settings = award_deduct_module.services.settings
    return (
        patch.object(
            settings, "can_adjust_current_xp", new_callable=AsyncMock, return_value=unspent
        ),
        patch.object(
            settings, "can_adjust_lifetime_xp", new_callable=AsyncMock, return_value=lifetime
        ),
    )


def _sent_embed(mock_respond: AsyncMock) -> discord.Embed:
    """The embed of the command's response."""
    assert mock_respond.await_args is not None
    return mock_respond.await_args.kwargs["embed"]


@pytest.mark.parametrize(
    "scope,unspent_ok,lifetime_ok,allowed",
    [
        ("Unspent", True, False, True),
        ("Unspent", False, True, False),
        ("Lifetime", False, True, True),
        ("Lifetime", True, False, False),
    ],
)
@pytest.mark.usefixtures("mock_respond", "mock_char_save")
async def test_award_respects_permissions(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_error: AsyncMock,
    scope: str,
    unspent_ok: bool,
    lifetime_ok: bool,
    allowed: bool,
):
    """Players can award XP only in the scopes the server allows."""
    unspent_patch, lifetime_patch = _permissions(unspent_ok, lifetime_ok)
    with unspent_patch, lifetime_patch:
        await award_or_deduct(ctx, vamp, 5, scope, "Test", player=user)

    if allowed:
        assert vamp.experience.unspent == 5
        assert len(vamp.experience.log) == 1
        mock_error.assert_not_awaited()
    else:
        assert vamp.experience.unspent == 0
        assert vamp.experience.lifetime == 0
        assert not vamp.experience.log
        mock_error.assert_awaited_once()


@pytest.mark.parametrize(
    "scope,amount,expected_unspent,expected_lifetime",
    [
        ("Unspent", 5, 10, 20),
        ("Unspent", -5, 0, 20),  # Spending everything is fine
        ("Lifetime", 5, 10, 25),
        ("Lifetime", -20, -15, 0),  # Unspent may go negative
    ],
)
@pytest.mark.usefixtures("allow_all")
async def test_award_or_deduct(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
    mock_error: AsyncMock,
    scope: str,
    amount: int,
    expected_unspent: int,
    expected_lifetime: int,
):
    """XP changes are applied, logged, saved, and confirmed."""
    vamp.experience.unspent = 5
    vamp.experience.lifetime = 20

    await award_or_deduct(ctx, vamp, amount, scope, "Test", player=user)

    assert vamp.experience.unspent == expected_unspent
    assert vamp.experience.lifetime == expected_lifetime
    entry = vamp.experience.log[-1]
    assert entry.amount == amount
    assert entry.event.endswith(scope.lower())
    assert entry.admin == ctx.author.id
    mock_char_save.assert_awaited_once()
    mock_error.assert_not_awaited()

    verb = "Awarded" if amount > 0 else "Deducted"
    assert _sent_embed(mock_respond).title == f"{verb} {abs(amount)} {scope} XP"


@pytest.mark.parametrize(
    "scope,unspent,lifetime,amount,error",
    [
        ("Unspent", 3, 20, -5, "only has `3` unspent XP!"),
        ("Unspent", 0, 20, -1, "has no unspent XP!"),
        ("Lifetime", 3, 4, -5, "only has `4` lifetime XP!"),
        ("Lifetime", 0, 0, -1, "has no lifetime XP!"),
    ],
)
@pytest.mark.usefixtures("allow_all", "mock_respond")
async def test_deduct_too_much(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_char_save: AsyncMock,
    mock_error: AsyncMock,
    scope: str,
    unspent: int,
    lifetime: int,
    amount: int,
    error: str,
):
    """Deductions can't exceed the XP in their scope."""
    vamp.experience.unspent = unspent
    vamp.experience.lifetime = lifetime

    await award_or_deduct(ctx, vamp, amount, scope, "Test", player=user)

    assert vamp.experience.unspent == unspent
    assert vamp.experience.lifetime == lifetime
    assert not vamp.experience.log
    mock_char_save.assert_not_awaited()
    assert mock_error.await_args is not None
    assert mock_error.await_args.args[1].endswith(error)


@pytest.mark.parametrize(
    "reason,shown",
    [
        ("Session 3", "Session 3."),
        ("Session 3.", "Session 3."),
        ("Great session!", "Great session!"),
        ("Who knows?", "Who knows?"),
    ],
)
@pytest.mark.usefixtures("allow_all", "mock_char_save")
async def test_award_reason_punctuation(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_respond: AsyncMock,
    reason: str,
    shown: str,
):
    """The confirmation ends the reason with punctuation; the log keeps it as given."""
    await award_or_deduct(ctx, vamp, 1, "Lifetime", reason, player=user)

    fields = {field.name: field.value for field in _sent_embed(mock_respond).fields}
    assert fields["Reason"] == shown
    assert vamp.experience.log[-1].reason == reason


@pytest.mark.usefixtures("allow_all")
async def test_award_saves_before_responding(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
):
    """A failed response can't leave an unsaved change behind."""
    order = MagicMock()
    order.attach_mock(mock_char_save, "save")
    order.attach_mock(mock_respond, "respond")

    await award_or_deduct(ctx, vamp, 1, "Lifetime", "Test", player=user)

    assert [call[0] for call in order.mock_calls] == ["save", "respond"]


def _log(character: VChar, *reasons: str):
    """Give the character log entries, oldest first."""
    character.experience.log = [
        VCharExperienceEntry(event="award_lifetime", amount=1, reason=reason, admin=1)
        for reason in reasons
    ]


@pytest.mark.parametrize("index,removed", [(1, "Newest"), (2, "Middle"), (3, "Oldest")])
async def test_remove_entry(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
    mock_error: AsyncMock,
    index: int,
    removed: str,
):
    """Entries are numbered newest first, as /experience log shows them."""
    _log(vamp, "Oldest", "Middle", "Newest")

    await remove_entry(ctx, vamp, index, player=user)

    remaining = [entry.reason for entry in vamp.experience.log]
    assert removed not in remaining
    assert len(remaining) == 2
    mock_char_save.assert_awaited_once()
    mock_error.assert_not_awaited()
    assert removed in (_sent_embed(mock_respond).description or "")


async def test_remove_entry_out_of_range(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
    mock_error: AsyncMock,
):
    """A missing entry is an error, and nothing changes."""
    _log(vamp, "Only")

    await remove_entry(ctx, vamp, 2, player=user)

    assert len(vamp.experience.log) == 1
    mock_char_save.assert_not_awaited()
    mock_respond.assert_not_awaited()
    mock_error.assert_awaited_once()


async def test_remove_entry_saves_before_responding(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
):
    """A failed response can't leave an unsaved change behind."""
    _log(vamp, "Only")
    order = MagicMock()
    order.attach_mock(mock_char_save, "save")
    order.attach_mock(mock_respond, "respond")

    await remove_entry(ctx, vamp, 1, player=user)

    assert [call[0] for call in order.mock_calls] == ["save", "respond"]
