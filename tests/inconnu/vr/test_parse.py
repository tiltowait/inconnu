"""Tests for inconnu/vr/parse.py."""

from collections.abc import Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest

from ctx import AppCtx
from inconnu.vr.parse import hidden_dice_allowed, parse, perform_roll, stringify_mentions
from models import Impairment, ImpairmentCategory, VChar
from tests.characters import gen_char

MEMBER_ID = 280000000000000001
CHANNEL_ID = 280000000000000002
THREAD_ID = 280000000000000003
UNKNOWN_ID = 280000000000000100


def not_found() -> discord.NotFound:
    """A NotFound error, as raised by fetch_member()."""
    response = MagicMock(spec=aiohttp.ClientResponse)
    response.status = 404
    response.reason = "Not Found"
    return discord.NotFound(response, "Unknown Member")


def make_member(name: str) -> discord.Member:
    """A member with the given display name."""
    member = MagicMock(spec=discord.Member)
    member.display_name = name
    return member


@pytest.fixture
def member() -> discord.Member:
    """A guild member who is in the cache."""
    return make_member("Nadea")


@pytest.fixture
def channel() -> discord.TextChannel:
    """A guild channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "general"
    return channel


@pytest.fixture
def thread() -> discord.Thread:
    """A thread in the guild."""
    thread = MagicMock(spec=discord.Thread)
    thread.name = "scene-1"
    return thread


@pytest.fixture
def ctx(member: discord.Member, channel: discord.TextChannel, thread: discord.Thread) -> AppCtx:
    """A guild context whose caches contain one member, one channel, and one thread."""
    guild = MagicMock(spec=discord.Guild)
    guild.get_member.side_effect = lambda id: member if id == MEMBER_ID else None
    guild.fetch_member = AsyncMock(side_effect=not_found())
    guild.get_channel_or_thread.side_effect = {CHANNEL_ID: channel, THREAD_ID: thread}.get

    ctx = MagicMock(spec=AppCtx)
    ctx.guild = guild
    ctx.bot = MagicMock(spec=discord.Bot)
    return ctx


@pytest.fixture
def dm_ctx() -> AppCtx:
    """A DM context. The bot can see one user, whose global name differs from
    their server nickname."""
    user = MagicMock(spec=discord.User)
    user.display_name = "tiltowait"

    ctx = MagicMock(spec=AppCtx)
    ctx.guild = None
    ctx.bot = MagicMock(spec=discord.Bot)
    ctx.bot.get_user.side_effect = lambda id: user if id == MEMBER_ID else None
    return ctx


@pytest.mark.parametrize("sentence", [None, ""])
async def test_empty(ctx: AppCtx, sentence: str | None):
    """Empty comments become None."""
    assert await stringify_mentions(ctx, sentence) is None


async def test_no_mentions(ctx: AppCtx):
    """Comments without mentions only have their whitespace collapsed."""
    assert await stringify_mentions(ctx, "  a   comment \n here ") == "a comment here"


@pytest.mark.parametrize("mention", [f"<@{MEMBER_ID}>", f"<@!{MEMBER_ID}>"])
async def test_cached_member(ctx: AppCtx, mention: str):
    """Cached members are replaced with their display names."""
    assert await stringify_mentions(ctx, f"Biting {mention}") == "Biting @Nadea"


async def test_uncached_member_is_fetched(ctx: AppCtx):
    """Members missing from the cache are fetched."""
    guild = ctx.guild
    assert guild is not None
    fetch = AsyncMock(return_value=make_member("Ozzy"))
    guild.fetch_member = fetch

    assert await stringify_mentions(ctx, f"Biting <@{UNKNOWN_ID}>") == "Biting @Ozzy"
    fetch.assert_awaited_once_with(UNKNOWN_ID)


async def test_unknown_member_is_left_raw(ctx: AppCtx):
    """Members that can't be found are left as raw mentions."""
    sentence = f"Biting <@{UNKNOWN_ID}>"
    assert await stringify_mentions(ctx, sentence) == sentence


async def test_channel(ctx: AppCtx):
    """Channels are replaced with their names."""
    assert await stringify_mentions(ctx, f"Meet in <#{CHANNEL_ID}>") == "Meet in #general"


async def test_thread(ctx: AppCtx):
    """Threads are replaced with their names."""
    assert await stringify_mentions(ctx, f"Meet in <#{THREAD_ID}>") == "Meet in #scene-1"


async def test_unknown_channel_is_left_raw(ctx: AppCtx):
    """Channels that can't be found are left as raw mentions."""
    sentence = f"Meet in <#{UNKNOWN_ID}>"
    assert await stringify_mentions(ctx, sentence) == sentence


async def test_repeated_mention(ctx: AppCtx):
    """Repeated mentions are looked up once and all replaced."""
    guild = ctx.guild
    assert guild is not None
    result = await stringify_mentions(ctx, f"<@{MEMBER_ID}> and <@{MEMBER_ID}>")

    assert result == "@Nadea and @Nadea"
    cast(MagicMock, guild.get_member).assert_called_once_with(MEMBER_ID)


async def test_lookups_stop_after_three_failures(ctx: AppCtx):
    """After three failed lookups, the rest of the mentions are left alone."""
    guild = ctx.guild
    assert guild is not None
    fetch = AsyncMock(side_effect=not_found())
    guild.fetch_member = fetch
    sentence = " ".join(f"<@{UNKNOWN_ID + n}>" for n in range(5))

    assert await stringify_mentions(ctx, sentence) == sentence
    assert fetch.await_count == 3


async def test_dm_user(dm_ctx: AppCtx):
    """In DMs, users are shown by their global display name."""
    assert await stringify_mentions(dm_ctx, f"Hi <@{MEMBER_ID}>") == "Hi @tiltowait"


async def test_dm_channel_is_left_raw(dm_ctx: AppCtx):
    """In DMs, there's no guild to find channels in."""
    sentence = f"Meet in <#{CHANNEL_ID}>"
    assert await stringify_mentions(dm_ctx, sentence) == sentence


# Impairment penalty


@pytest.fixture
def mock_auto_impairment() -> Iterator[AsyncMock]:
    """The invoking user's auto-impairment setting, on by default."""
    with patch("services.settings.auto_impairment", new_callable=AsyncMock) as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def vampire() -> VChar:
    """A vampire with physical and mental traits and no impairment."""
    char = gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 2, "Wits": 2, "Awareness": 2})
    return char


PHYSICALLY_IMPAIRED = "//////"
MENTALLY_IMPAIRED = "/////"


async def test_penalty_applied_once(ctx: AppCtx, vampire: VChar, mock_auto_impairment: AsyncMock):
    """The penalty comes off the dice once, and the user's text is untouched."""
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(ctx, vampire, "strength+brawl 0 0")

    assert roll.pool == 3
    assert roll.base_pool == 5
    assert roll.impairment_penalty == Impairment.PHYSICAL
    assert roll.pool_str == "Strength + Brawl"
    assert roll.syntax == "strength+brawl 0 0"
    mock_auto_impairment.assert_awaited_once_with(ctx)


@pytest.mark.usefixtures("mock_auto_impairment")
async def test_penalty_records_impairment_state(ctx: AppCtx, vampire: VChar):
    """The recorded penalty is the character's impairment, not the roll's category."""
    vampire.health = PHYSICALLY_IMPAIRED
    vampire.willpower = MENTALLY_IMPAIRED
    roll = await perform_roll(ctx, vampire, "strength+brawl 0 0")

    assert roll.pool == 3
    assert roll.impairment_penalty == Impairment.TOTAL


@pytest.mark.usefixtures("mock_auto_impairment")
async def test_penalty_removes_normal_dice_first(ctx: AppCtx, vampire: VChar):
    """Hunger dice are kept; the penalty comes out of the normal dice."""
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(ctx, vampire, "strength+brawl 2 0")

    assert roll.normal.count == 1
    assert roll.hunger.count == 2


@pytest.mark.usefixtures("mock_auto_impairment")
async def test_penalty_survives_reroll(ctx: AppCtx, vampire: VChar):
    """Rerolls change the dice, not the pool, so the penalty isn't reapplied."""
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(ctx, vampire, "strength+brawl 0 0")

    with patch("inconnu.d10", return_value=10):
        roll.reroll("reroll_failures")

    assert roll.pool == 3
    assert roll.impairment_penalty == Impairment.PHYSICAL


@pytest.mark.parametrize(
    "health,willpower,syntax,expected_pool",
    [
        ("......", ".....", "strength+brawl 0 0", 5),  # Not impaired
        (PHYSICALLY_IMPAIRED, ".....", "wits+awareness 0 0", 4),  # Wrong category
        (PHYSICALLY_IMPAIRED, MENTALLY_IMPAIRED, "5 0 0", 5),  # No category
    ],
)
async def test_no_penalty(
    ctx: AppCtx,
    vampire: VChar,
    mock_auto_impairment: AsyncMock,
    health: str,
    willpower: str,
    syntax: str,
    expected_pool: int,
):
    """Rolls the impairment doesn't penalize keep their full pool, without a
    settings lookup."""
    vampire.health = health
    vampire.willpower = willpower
    roll = await perform_roll(ctx, vampire, syntax)

    assert roll.pool == expected_pool
    assert roll.impairment_penalty == Impairment.NONE
    mock_auto_impairment.assert_not_awaited()


async def test_no_penalty_when_ignored(
    ctx: AppCtx, vampire: VChar, mock_auto_impairment: AsyncMock
):
    """Ignoring Impairment skips the penalty without a settings lookup."""
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(
        ctx, vampire, "strength+brawl 0 0", impairment_category=ImpairmentCategory.IGNORE
    )

    assert roll.pool == 5
    assert roll.impairment_penalty == Impairment.NONE
    mock_auto_impairment.assert_not_awaited()


async def test_no_penalty_when_setting_off(
    ctx: AppCtx, vampire: VChar, mock_auto_impairment: AsyncMock
):
    """Users who turned off auto-impairment get their full pool."""
    mock_auto_impairment.return_value = False
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(ctx, vampire, "strength+brawl 0 0")

    assert roll.pool == 5
    assert roll.impairment_penalty == Impairment.NONE


async def test_no_penalty_without_character(ctx: AppCtx, mock_auto_impairment: AsyncMock):
    """Character-less rolls are never penalized."""
    roll = await perform_roll(ctx, None, "5 0 0")

    assert roll.pool == 5
    assert roll.impairment_penalty == Impairment.NONE
    mock_auto_impairment.assert_not_awaited()


@pytest.mark.parametrize("setting", [True, False])
async def test_category_override_applies_penalty(
    ctx: AppCtx, vampire: VChar, mock_auto_impairment: AsyncMock, setting: bool
):
    """Choosing a category the character is impaired in applies the penalty, even
    with auto-impairment turned off."""
    mock_auto_impairment.return_value = setting
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(
        ctx, vampire, "wits+awareness 0 0", impairment_category=ImpairmentCategory.PHYSICAL
    )

    assert roll.pool == 2
    assert roll.impairment_penalty == Impairment.PHYSICAL
    mock_auto_impairment.assert_not_awaited()


async def test_category_override_removes_penalty(
    ctx: AppCtx, vampire: VChar, mock_auto_impairment: AsyncMock
):
    """Choosing a category the character isn't impaired in removes the penalty."""
    vampire.health = PHYSICALLY_IMPAIRED
    roll = await perform_roll(
        ctx, vampire, "strength+brawl 0 0", impairment_category=ImpairmentCategory.MENTAL
    )

    assert roll.pool == 5
    assert roll.impairment_penalty == Impairment.NONE
    mock_auto_impairment.assert_not_awaited()


# Hidden dice permission


@pytest.mark.parametrize(
    "hide_dice,allowed,expected",
    [(False, False, True), (True, True, True), (True, False, False)],
)
async def test_hidden_dice_allowed(hide_dice: bool, allowed: bool, expected: bool):
    """Only hiding dice where the server disallows it is refused, with an error."""
    ctx = MagicMock(spec=AppCtx)
    with (
        patch("services.settings.allow_hidden_dice", new_callable=AsyncMock, return_value=allowed),
        patch("ui.embeds.error", new_callable=AsyncMock) as mock_error,
    ):
        result = await hidden_dice_allowed(ctx, hide_dice)

    assert result is expected
    if expected:
        mock_error.assert_not_awaited()
    else:
        mock_error.assert_awaited_once_with(ctx, "This server doesn't allow hidden dice.")


async def test_parse_disallowed_hidden_dice():
    """If the server disallows hidden dice, nothing is rolled."""
    ctx = MagicMock(spec=AppCtx)
    with (
        patch("services.settings.allow_hidden_dice", new_callable=AsyncMock, return_value=False),
        patch("ui.embeds.error", new_callable=AsyncMock),
        patch("services.settings.max_hunger", new_callable=AsyncMock, return_value=5),
        patch("inconnu.vr.parse.display_outcome", new_callable=AsyncMock),
        patch("inconnu.vr.parse.perform_roll", new_callable=AsyncMock) as mock_roll,
    ):
        await parse(ctx, "5 0 0", None, None, None, hide_dice=True)

    mock_roll.assert_not_awaited()
