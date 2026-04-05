"""Tests for inconnu.header.fix.location."""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from inconnu.header.fix.location import LocationChangeModal, fix_header_location

_RESOLVE_WEBHOOK = "inconnu.header.fix.location._resolve_webhook"


@pytest.fixture
def bot_user() -> discord.User:
    """The bot's user identity."""
    user = MagicMock(spec=discord.User)
    user.id = 999
    return user


@pytest.fixture
def owner_user() -> discord.Member:
    """The header owner."""
    user = MagicMock(spec=discord.Member)
    user.id = 100
    user.name = "owner"
    return user


@pytest.fixture
def other_user() -> discord.Member:
    """A non-owner user."""
    user = MagicMock(spec=discord.Member)
    user.id = 200
    user.name = "intruder"
    return user


@pytest.fixture
def webhook() -> discord.Webhook:
    """A resolved webhook."""
    return MagicMock(spec=discord.Webhook)


@pytest.fixture
def header_record(owner_user: discord.Member) -> dict:
    """A database header record."""
    return {"character": {"user": owner_user.id}}


@pytest.fixture
def message(bot_user: discord.User) -> discord.Message:
    """A Discord message authored by the bot (non-webhook header)."""
    msg = MagicMock(spec=discord.Message)
    msg.id = 12345
    msg.author = bot_user
    return msg


@pytest.fixture
def webhook_message() -> discord.Message:
    """A Discord message authored by a webhook."""
    msg = MagicMock(spec=discord.Message)
    msg.id = 67890
    msg.author = MagicMock(spec=discord.User)
    msg.author.id = 888
    return msg


@pytest.fixture
def ctx(owner_user: discord.Member, bot_user: discord.User) -> AsyncMock:
    """A minimal AppCtx mock."""
    ctx = AsyncMock()
    ctx.user = owner_user
    ctx.bot = MagicMock()
    ctx.bot.user = bot_user
    ctx.channel = MagicMock(spec=discord.TextChannel)
    return ctx


@pytest.fixture
async def no_webhook() -> AsyncGenerator[AsyncMock, None]:
    """Patch _resolve_webhook to return None (no webhook found)."""
    with patch(_RESOLVE_WEBHOOK, new_callable=AsyncMock, return_value=None) as mock:
        yield mock


@pytest.fixture
async def mock_webhook(webhook: discord.Webhook) -> AsyncGenerator[AsyncMock, None]:
    """Patch _resolve_webhook to return a webhook."""
    with patch(_RESOLVE_WEBHOOK, new_callable=AsyncMock, return_value=webhook) as mock:
        yield mock


async def test_not_bot_message_and_no_webhook(
    ctx: AsyncMock, no_webhook: AsyncMock, other_user: discord.Member
):
    """Non-bot, non-webhook message is rejected."""
    message = MagicMock(spec=discord.Message)
    message.id = 1
    message.author = other_user

    await fix_header_location(ctx, message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "isn't an RP header" in args[0]
    assert kwargs["ephemeral"] is True


async def test_no_db_record(ctx: AsyncMock, no_webhook: AsyncMock, message: discord.Message):
    """Bot message with no header record in the database is rejected."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=None):
        await fix_header_location(ctx, message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "isn't an RP header" in args[0]
    assert kwargs["ephemeral"] is True


async def test_non_owner_rejected(
    ctx: AsyncMock,
    no_webhook: AsyncMock,
    message: discord.Message,
    other_user: discord.Member,
    header_record: dict,
):
    """A user who doesn't own the header is rejected."""
    ctx.user = other_user

    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record):
        await fix_header_location(ctx, message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "isn't your RP header" in args[0]
    assert kwargs["ephemeral"] is True


async def test_owner_gets_modal(
    ctx: AsyncMock, no_webhook: AsyncMock, message: discord.Message, header_record: dict
):
    """The header owner receives the edit modal."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record):
        await fix_header_location(ctx, message)

    ctx.respond.assert_not_awaited()
    ctx.send_modal.assert_awaited_once()


async def test_webhook_message_with_record(
    ctx: AsyncMock,
    mock_webhook: AsyncMock,
    webhook_message: discord.Message,
    header_record: dict,
):
    """A webhook-authored message with a valid record opens the modal."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record):
        await fix_header_location(ctx, webhook_message)

    ctx.respond.assert_not_awaited()
    ctx.send_modal.assert_awaited_once()


async def test_webhook_message_no_record(
    ctx: AsyncMock, mock_webhook: AsyncMock, webhook_message: discord.Message
):
    """A webhook-authored message with no db record is rejected."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=None):
        await fix_header_location(ctx, webhook_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "isn't an RP header" in args[0]
    assert kwargs["ephemeral"] is True


# --- LocationChangeModal tests ---


def _make_header_message(
    *,
    title: str | None = None,
    author_name: str | None = None,
    author_url: str = "https://example.com/profile",
    author_icon_url: str = "https://example.com/icon.png",
    footer_text: str = "",
) -> AsyncMock:
    """Build a mock message with a real embed for modal testing."""
    embed = discord.Embed(title=title)
    if author_name is not None:
        embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
    if footer_text:
        embed.set_footer(text=footer_text)

    msg = AsyncMock(spec=discord.Message)
    msg.id = 11111
    msg.embeds = [embed]
    return msg


@pytest.fixture
def interaction() -> discord.Interaction:
    """A mock interaction for modal callbacks."""
    inter = AsyncMock(spec=discord.Interaction)
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    return inter


# --- _get_location tests (title mode) ---


async def test_get_location_title_name_only():
    """Title with just character name → empty location."""
    msg = _make_header_message(title="Nadea")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == ""


async def test_get_location_title_name_and_location():
    """Title with name and location → extracts location."""
    msg = _make_header_message(title="Nadea • The Elysium")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == "The Elysium"


async def test_get_location_title_name_and_blushed():
    """Title with name and 'Blushed' → empty (not a location)."""
    msg = _make_header_message(title="Nadea • Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == ""


async def test_get_location_title_name_and_not_blushed():
    """Title with name and 'Not Blushed' → empty."""
    msg = _make_header_message(title="Nadea • Not Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == ""


async def test_get_location_title_all_three():
    """Title with name, location, and blush → extracts location."""
    msg = _make_header_message(title="Nadea • The Elysium • Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == "The Elysium"


# --- _get_location tests (author mode) ---


async def test_get_location_author_location_only():
    """Author with just location → returns it."""
    wh = MagicMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="The Elysium")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    assert modal._get_location() == "The Elysium"


async def test_get_location_author_location_and_blush():
    """Author with location and blush → extracts location."""
    wh = MagicMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="The Elysium • Blushed")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    assert modal._get_location() == "The Elysium"


# --- callback tests (title mode, no webhook) ---


async def test_callback_title_insert_location(interaction: discord.Interaction):
    """Title mode: inserting a location where none existed."""
    msg = _make_header_message(title="Nadea")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.title == "Nadea • The Rack"
    msg.edit.assert_awaited_once_with(embed=embed)


async def test_callback_title_replace_location(interaction: discord.Interaction):
    """Title mode: replacing an existing location."""
    msg = _make_header_message(title="Nadea • The Elysium • Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.title == "Nadea • The Rack • Blushed"
    msg.edit.assert_awaited_once_with(embed=embed)


async def test_callback_title_sets_footer(interaction: discord.Interaction):
    """Title mode: temp effects written to footer."""
    msg = _make_header_message(title="Nadea • The Elysium")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "The Elysium"
    modal.children[1].value = "Obfuscate active"

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.footer.text == "Obfuscate active"


async def test_callback_title_whitespace_normalization(interaction: discord.Interaction):
    """Whitespace in location and temp effects is collapsed."""
    msg = _make_header_message(title="Nadea")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "  The   Rack  "
    modal.children[1].value = "  Obfuscate   active  "

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.title == "Nadea • The Rack"
    assert embed.footer.text == "Obfuscate active"


# --- callback tests (author mode, with webhook) ---


async def test_callback_author_replace_location(interaction: discord.Interaction):
    """Author mode: replacing an existing location."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="The Elysium • Blushed")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.author.name == "The Rack • Blushed"
    wh.edit_message.assert_awaited_once_with(msg.id, embed=embed)


async def test_callback_author_preserves_url_and_icon(interaction: discord.Interaction):
    """Author mode: url and icon_url are preserved after editing."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(
        author_name="The Elysium • Blushed",
        author_url="https://example.com/profile",
        author_icon_url="https://example.com/icon.png",
    )
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.author.url == "https://example.com/profile"
    assert embed.author.icon_url == "https://example.com/icon.png"


async def test_callback_uses_message_edit_without_webhook(interaction: discord.Interaction):
    """Without a webhook, callback edits via message.edit()."""
    msg = _make_header_message(title="Nadea • The Elysium")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    msg.edit.assert_awaited_once()


async def test_callback_uses_webhook_edit_with_webhook(interaction: discord.Interaction):
    """With a webhook, callback edits via webhook.edit_message()."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="The Elysium • Blushed")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    wh.edit_message.assert_awaited_once()
    msg.edit.assert_not_awaited()
