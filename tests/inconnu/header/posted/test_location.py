"""Tests for inconnu.header.posted.location."""

from collections.abc import AsyncGenerator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from inconnu.header.posted.location import LocationChangeModal, _resolve_webhook, edit_location
from services.webhooks import ChannelWebhook, WebhookCache

_RESOLVE_WEBHOOK = "inconnu.header.posted.location._resolve_webhook"


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
async def no_webhook() -> AsyncGenerator[AsyncMock]:
    """Patch _resolve_webhook to return None (no webhook found)."""
    with patch(_RESOLVE_WEBHOOK, new_callable=AsyncMock, return_value=None) as mock:
        yield mock


@pytest.fixture
async def mock_webhook(webhook: discord.Webhook) -> AsyncGenerator[AsyncMock]:
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

    await edit_location(ctx, message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "isn't an RP header" in args[0]
    assert kwargs["ephemeral"] is True


async def test_no_db_record(ctx: AsyncMock, no_webhook: AsyncMock, message: discord.Message):
    """Bot message with no header record in the database is rejected."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=None):
        await edit_location(ctx, message)

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
        await edit_location(ctx, message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "isn't your RP header" in args[0]
    assert kwargs["ephemeral"] is True


async def test_owner_gets_modal(
    ctx: AsyncMock, no_webhook: AsyncMock, message: discord.Message, header_record: dict
):
    """The header owner receives the edit modal."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record):
        await edit_location(ctx, message)

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
        await edit_location(ctx, webhook_message)

    ctx.respond.assert_not_awaited()
    ctx.send_modal.assert_awaited_once()


async def test_webhook_message_no_record(
    ctx: AsyncMock, mock_webhook: AsyncMock, webhook_message: discord.Message
):
    """A webhook-authored message with no db record is rejected."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=None):
        await edit_location(ctx, webhook_message)

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


async def test_get_location_title_blushed_in_location_name():
    """Title with a location containing 'Blushed' as a substring."""
    msg = _make_header_message(title="Nadea • The Blushed Rose")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == "The Blushed Rose"


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


async def test_get_location_without_heading(webhook: discord.Webhook):
    """A header missing its author has no location to show."""
    msg = _make_header_message()
    modal = LocationChangeModal(msg, webhook=ChannelWebhook(webhook), title="Edit")
    assert modal._get_location() == ""


@pytest.mark.parametrize("heading", ["Blushed", "Not Blushed"])
async def test_get_location_author_blush_only(heading: str):
    """Author mode: a lone Blush isn't a location."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(author_name=heading)
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    assert modal._get_location() == ""


async def test_callback_author_keeps_lone_blush(interaction: discord.Interaction):
    """Author mode: adding a location keeps a lone Blush."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="Not Blushed")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    assert msg.embeds[0].author.name == "The Rack • Not Blushed"


@pytest.mark.parametrize("location", ["•", " • • "])
async def test_callback_rejects_blank_location(location: str, interaction: discord.Interaction):
    """A location of only bullets gets no response, which keeps the modal open."""
    msg = _make_header_message(title="Nadea • Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = location
    modal.children[1].value = ""

    await modal.callback(interaction)

    cast(AsyncMock, interaction.response.send_message).assert_not_awaited()
    msg.edit.assert_not_awaited()
    assert msg.embeds[0].title == "Nadea • Blushed"


async def test_get_location_extra_bullets():
    """Title mode: a location with bullets in it is shown whole."""
    msg = _make_header_message(title="Nadea • Elysium • Roof • Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    assert modal._get_location() == "Elysium • Roof"


async def test_get_location_author_extra_bullets():
    """Author mode: a location with bullets in it is shown whole."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="Elysium • Roof • Blushed")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    assert modal._get_location() == "Elysium • Roof"


async def test_callback_replaces_location_with_bullets(interaction: discord.Interaction):
    """Title mode: the whole old location is replaced, and nothing else."""
    msg = _make_header_message(title="Nadea • Elysium • Roof • Blushed")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    assert msg.embeds[0].title == "Nadea • The Rack • Blushed"


async def test_callback_author_replaces_location_with_bullets(interaction: discord.Interaction):
    """Author mode: the whole old location is replaced, and nothing else."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message(author_name="Elysium • Roof • Blushed")
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    assert msg.embeds[0].author.name == "The Rack • Blushed"


async def test_callback_author_without_heading(interaction: discord.Interaction):
    """Author mode: a missing heading becomes just the location."""
    wh = AsyncMock(spec=discord.Webhook)
    msg = _make_header_message()
    modal = LocationChangeModal(msg, webhook=wh, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    assert msg.embeds[0].author.name == "The Rack"


async def test_callback_title_with_empty_element(interaction: discord.Interaction):
    """Title mode: an empty trailing element doesn't survive the edit."""
    msg = _make_header_message(title="Nadea • ")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "The Rack"
    modal.children[1].value = ""

    await modal.callback(interaction)

    assert msg.embeds[0].title == "Nadea • The Rack"


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


async def test_callback_strips_bullet_from_location(interaction: discord.Interaction):
    """Bullet character in location input is stripped to prevent parsing issues."""
    msg = _make_header_message(title="Nadea")
    modal = LocationChangeModal(msg, webhook=None, title="Edit")
    modal.children[0].value = "Bar • VIP Lounge"
    modal.children[1].value = ""

    await modal.callback(interaction)

    embed = msg.embeds[0]
    assert embed.title == "Nadea • Bar VIP Lounge"


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


# _resolve_webhook


def thread_in(parent: MagicMock | None) -> MagicMock:
    """A thread in the given channel."""
    thread = MagicMock(spec=discord.Thread)
    thread.parent = parent  # Mock() treats parent= as its own argument
    return thread


@pytest.fixture
def resolving_bot() -> MagicMock:
    """A bot whose cache finds a matching webhook."""
    bot = MagicMock(spec=InconnuBot)
    bot.webhook_cache = AsyncMock(spec=WebhookCache)
    bot.webhook_cache.matching_webhook.return_value = AsyncMock(spec=discord.Webhook)
    return bot


async def test_resolve_webhook_in_thread(
    resolving_bot: MagicMock, webhook_message: discord.Message
):
    """A thread's header is matched against its parent's webhook, bound to the
    thread."""
    parent = MagicMock(spec=discord.ForumChannel)
    thread = thread_in(parent)

    result = await _resolve_webhook(resolving_bot, thread, webhook_message)

    resolving_bot.webhook_cache.matching_webhook.assert_awaited_once_with(parent, 888)
    webhook = resolving_bot.webhook_cache.matching_webhook.return_value
    assert result == ChannelWebhook(webhook, thread)


async def test_resolve_webhook_without_match(
    resolving_bot: MagicMock, webhook_message: discord.Message
):
    """No matching webhook means no webhook."""
    resolving_bot.webhook_cache.matching_webhook.return_value = None
    channel = MagicMock(spec=discord.TextChannel)

    assert await _resolve_webhook(resolving_bot, channel, webhook_message) is None


async def test_resolve_webhook_without_parent(
    resolving_bot: MagicMock, webhook_message: discord.Message
):
    """A thread whose parent is unknown has no webhook."""
    assert await _resolve_webhook(resolving_bot, thread_in(None), webhook_message) is None
    resolving_bot.webhook_cache.matching_webhook.assert_not_awaited()
