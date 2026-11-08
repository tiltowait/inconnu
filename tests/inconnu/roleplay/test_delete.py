"""Tests for inconnu/roleplay/delete.py."""

from collections.abc import Generator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest
from beanie import PydanticObjectId
from pymongo.asynchronous.collection import AsyncCollection

import db
from inconnu.roleplay.delete import DeletionModal, delete_message_chain, deletion_embed
from models import RPPost
from services.webhooks import ChannelWebhook
from tests.inconnu.roleplay.conftest import USER_ID, MockCtx, PostFactory
from utils.urls import post_url

type MockFindOne = AsyncMock
type MockHeaders = AsyncMock
type MockInteraction = AsyncMock
type MockMessage = MagicMock
type MockWebhook = AsyncMock

WEBHOOK_ID = 5000
MESSAGE_ID = 6000


@pytest.fixture
def webhook(rp_ctx: MockCtx) -> MockWebhook:
    """The channel's webhook."""
    mock = AsyncMock(spec=discord.Webhook)
    mock.id = WEBHOOK_ID
    rp_ctx.bot.prep_webhook = AsyncMock(return_value=ChannelWebhook(mock))
    return mock


@pytest.fixture
def message() -> MockMessage:
    """A message from the channel's webhook."""
    mock = MagicMock(spec=discord.Message, id=MESSAGE_ID)
    mock.author = MagicMock(spec=discord.User, id=WEBHOOK_ID, bot=True)
    return mock


@pytest.fixture
def find_one() -> Generator[MockFindOne]:
    """RPPost.find_one(), which finds nothing unless told otherwise."""
    with patch.object(RPPost, "find_one", AsyncMock(return_value=None)) as mock:
        yield mock


@pytest.fixture
def headers() -> Generator[MockHeaders]:
    """The header collection, which finds nothing unless told otherwise."""
    collection = AsyncMock(spec=AsyncCollection)
    collection.find_one.return_value = None
    with patch.object(db, "headers", collection):
        yield collection


@pytest.fixture
def interaction() -> MockInteraction:
    """The modal's interaction."""
    mock = AsyncMock(spec=discord.Interaction)
    mock.response = AsyncMock(spec=discord.InteractionResponse)
    return mock


def http_error[E: discord.HTTPException](cls: type[E]) -> E:
    """A Discord failure of the given type."""
    return cls(MagicMock(spec=aiohttp.ClientResponse, status=500, reason="Error"), "Failed")


# Test delete_message_chain


async def test_own_post_opens_modal(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    find_one: MockFindOne,
    make_post: PostFactory,
):
    """A user's own Rolepost, found by any message in its chain, opens the modal."""
    post = make_post(id_chain=[MESSAGE_ID, MESSAGE_ID + 1])
    find_one.return_value = post

    await delete_message_chain(rp_ctx, message)

    assert find_one.call_args.args[0] == {"id_chain": MESSAGE_ID}
    modal = rp_ctx.send_modal.await_args.args[0]
    assert isinstance(modal, DeletionModal)
    assert modal.rp_post is post
    assert modal.webhook == ChannelWebhook(webhook)


async def test_user_message_rejected(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    show_error: AsyncMock,
):
    """A regular user's message can't be deleted."""
    message.author.bot = False

    await delete_message_chain(rp_ctx, message)

    assert "user's post" in str(show_error.call_args.args[1])
    rp_ctx.send_modal.assert_not_awaited()


async def test_bot_message_rejected(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    show_error: AsyncMock,
):
    """Inconnu's own messages aren't Roleposts."""
    rp_ctx.bot.user = message.author

    await delete_message_chain(rp_ctx, message)

    assert "isn't a Rolepost" in str(show_error.call_args.args[1])
    rp_ctx.send_modal.assert_not_awaited()


async def test_other_webhook_rejected(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    show_error: AsyncMock,
):
    """A message from a different webhook can't be deleted."""
    message.author.id = WEBHOOK_ID + 1

    await delete_message_chain(rp_ctx, message)

    assert "webhook was deleted" in str(show_error.call_args.args[1])
    rp_ctx.send_modal.assert_not_awaited()


async def test_header_points_to_header_delete(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    find_one: MockFindOne,
    headers: MockHeaders,
    show_error: AsyncMock,
):
    """A standalone header is deleted with a different command."""
    headers.find_one.return_value = {"message": MESSAGE_ID}

    await delete_message_chain(rp_ctx, message)

    assert "`Header: Delete`" in str(show_error.call_args.args[1])
    rp_ctx.send_modal.assert_not_awaited()


async def test_unknown_message_rejected(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    find_one: MockFindOne,
    headers: MockHeaders,
    show_error: AsyncMock,
):
    """An unrecorded webhook message needs a moderator."""
    await delete_message_chain(rp_ctx, message)

    assert "moderator" in str(show_error.call_args.args[1])
    rp_ctx.send_modal.assert_not_awaited()


async def test_other_users_post_rejected(
    rp_ctx: MockCtx,
    webhook: MockWebhook,
    message: MockMessage,
    find_one: MockFindOne,
    make_post: PostFactory,
    show_error: AsyncMock,
):
    """Users can only delete their own Roleposts."""
    find_one.return_value = make_post(user=USER_ID + 1)

    await delete_message_chain(rp_ctx, message)

    assert "isn't your Rolepost" in str(show_error.call_args.args[1])
    rp_ctx.send_modal.assert_not_awaited()


# Test deletion_embed


def test_deletion_embed_shows_post(make_post: PostFactory):
    """A notice has the post's author, channel, contents, date, and history link."""
    post = make_post("The post content", user=1, channel=2)
    post.id = PydanticObjectId()

    embed = deletion_embed(post)

    description = cast(str, embed.description)
    assert "**Poster:** <@1>" in description
    assert "**Channel:** <#2>" in description
    assert description.endswith("The post content")
    assert embed.url == post_url(post.id)
    assert embed.timestamp == post.utc_date


def test_deletion_embed_shows_thread(make_post: PostFactory):
    """A thread post's notice names the thread, not its parent."""
    post = make_post(channel=2, thread=3)
    post.id = PydanticObjectId()

    description = cast(str, deletion_embed(post).description)

    assert "**Channel:** <#3>" in description


# Test DeletionModal


@pytest.mark.parametrize("confirmation", ["DELETE", "delete", "Delete"])
async def test_confirmation_deletes_chain(
    webhook: MockWebhook,
    interaction: MockInteraction,
    make_post: PostFactory,
    confirmation: str,
):
    """Confirming deletes every message in the chain."""
    modal = DeletionModal(webhook, make_post(id_chain=[1, 2, 3]))
    modal.children[0].value = confirmation

    await modal.callback(interaction)

    deleted = [call.args[0] for call in webhook.delete_message.await_args_list]
    assert deleted == [1, 2, 3]
    assert interaction.respond.await_args.args[0] == "Rolepost deleted!"


async def test_confirmation_deletes_chain_in_thread(
    webhook: MockWebhook, interaction: MockInteraction, make_post: PostFactory
):
    """A thread post's messages are deleted from the thread."""
    thread = MagicMock(spec=discord.Thread, id=7000)
    modal = DeletionModal(ChannelWebhook(webhook, thread), make_post(id_chain=[1, 2]))
    modal.children[0].value = "DELETE"

    await modal.callback(interaction)

    assert [call.kwargs for call in webhook.delete_message.await_args_list] == [
        {"thread_id": 7000},
        {"thread_id": 7000},
    ]


async def test_missing_message_counts_as_deleted(
    webhook: MockWebhook, interaction: MockInteraction, make_post: PostFactory
):
    """A message that's already gone isn't a failure."""
    webhook.delete_message.side_effect = [http_error(discord.NotFound), None]
    modal = DeletionModal(webhook, make_post(id_chain=[1, 2]))
    modal.children[0].value = "DELETE"

    await modal.callback(interaction)

    assert webhook.delete_message.await_count == 2
    assert interaction.respond.await_args.args[0] == "Rolepost deleted!"


@pytest.mark.parametrize("error", [discord.Forbidden, discord.HTTPException])
async def test_failed_deletion_is_reported(
    webhook: MockWebhook,
    interaction: MockInteraction,
    make_post: PostFactory,
    show_error: AsyncMock,
    error: type[discord.HTTPException],
):
    """A message that can't be deleted doesn't stop the rest, and the user is told."""
    webhook.delete_message.side_effect = [http_error(error), None]
    modal = DeletionModal(webhook, make_post(id_chain=[1, 2]))
    modal.children[0].value = "DELETE"

    await modal.callback(interaction)

    assert webhook.delete_message.await_count == 2
    assert show_error.call_args.kwargs["title"] == "Unable to delete post"
    interaction.respond.assert_not_awaited()


async def test_wrong_confirmation_deletes_nothing(
    webhook: MockWebhook,
    interaction: MockInteraction,
    make_post: PostFactory,
    show_error: AsyncMock,
):
    """Anything but DELETE leaves the post alone."""
    modal = DeletionModal(webhook, make_post(id_chain=[1]))
    modal.children[0].value = "nope"

    await modal.callback(interaction)

    webhook.delete_message.assert_not_awaited()
    assert show_error.call_args.kwargs["title"] == "Invalid response"
