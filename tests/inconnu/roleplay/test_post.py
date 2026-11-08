"""Tests for inconnu/roleplay/post.py PostModal helper methods."""

import asyncio
import inspect
from collections.abc import Generator
from functools import partial
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest
from beanie import PydanticObjectId

import errors
import services
from bot import InconnuBot
from ctx import AppCtx
from inconnu.roleplay.post import PostModal, create_post, edit_post
from models import HeaderSubdoc, RPPost, VChar
from services.webhooks import UNKNOWN_WEBHOOK, ChannelWebhook
from tests.characters import gen_char
from tests.inconnu.roleplay.conftest import USER_ID, MockCtx, PostFactory

type MockChangelog = AsyncMock
type MockGet = AsyncMock
type MockInteraction = AsyncMock
type MockPostModal = MagicMock
type MockWebhook = AsyncMock

CHANGELOG_ID = 7000
MESSAGE_ID = 8000


@pytest.fixture
def mock_post_modal() -> MockPostModal:
    """Create a mock PostModal instance with children structure."""
    modal = MagicMock(spec=PostModal)
    # PostModal has children: [message_field, ..., title_field, tags_field]
    # We care about the last one (index -1) for tags
    modal.children = [MagicMock(spec=discord.ui.InputText) for _ in range(3)]
    return modal


@pytest.fixture
def webhook() -> MockWebhook:
    """A webhook whose messages have sequential IDs, starting at 1."""
    mock = AsyncMock(spec=discord.Webhook)
    mock.send.side_effect = [MagicMock(spec=discord.WebhookMessage, id=i) for i in range(1, 6)]
    return mock


@pytest.fixture
def interaction() -> MockInteraction:
    """The modal's interaction."""
    mock = AsyncMock(spec=discord.Interaction)
    mock.response = AsyncMock(spec=discord.InteractionResponse)
    mock.user = MagicMock(spec=discord.Member, id=USER_ID)
    mock.user.mention = f"<@{USER_ID}>"
    mock.guild = MagicMock(spec=discord.Guild)
    mock.guild.name = "Test Guild"
    return mock


@pytest.fixture
def posting_modal(mock_post_modal: MockPostModal, webhook: MockWebhook) -> MockPostModal:
    """A modal ready to make a two-page post with no header or mentions."""
    mock_post_modal.bot = MagicMock(spec=InconnuBot)
    mock_post_modal.bot.prep_webhook = AsyncMock(return_value=ChannelWebhook(webhook))
    mock_post_modal.bot.webhook_send = partial(InconnuBot.webhook_send, mock_post_modal.bot)
    mock_post_modal.character = MagicMock(spec=VChar)
    mock_post_modal.character.name = "Nadea"
    mock_post_modal.character.profile_image_url = None
    mock_post_modal.header = MagicMock(spec=HeaderSubdoc)
    mock_post_modal.show_header = False
    mock_post_modal.mentions = ""
    mock_post_modal._clean_post_content.return_value = ["First page", "Second page"]
    mock_post_modal._clean_tags.return_value = ["tag"]
    mock_post_modal._clean_title.return_value = "A title"
    mock_post_modal._send_rp_post = partial(PostModal._send_rp_post, mock_post_modal)
    return mock_post_modal


@pytest.fixture
def new_post() -> Generator[MagicMock]:
    """RPPost.new(), which makes a post whose save does nothing."""
    with patch.object(RPPost, "new", side_effect=lambda **_: AsyncMock(spec=RPPost)) as mock:
        yield mock


@pytest.fixture
def get_post() -> Generator[MockGet]:
    """RPPost.get(), which reloads the post being edited."""
    with patch.object(RPPost, "get", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def editing_modal(
    mock_post_modal: MockPostModal,
    webhook: MockWebhook,
    make_post: PostFactory,
    get_post: MockGet,
) -> Generator[MockPostModal]:
    """A modal ready to edit a real post, with unchanged content, whose saves do
    nothing. Reloading the post finds it unchanged."""
    mock_post_modal.bot = MagicMock(spec=InconnuBot)
    mock_post_modal.bot.prep_webhook = AsyncMock(return_value=ChannelWebhook(webhook))
    mock_post_modal.character = MagicMock(spec=VChar)
    mock_post_modal.character.profile_image_url = None
    mock_post_modal.message = MagicMock(spec=discord.Message, id=MESSAGE_ID)
    mock_post_modal.post_to_edit = make_post("Original", id=PydanticObjectId())
    get_post.return_value = mock_post_modal.post_to_edit
    mock_post_modal._clean_post_content.return_value = "Original"
    mock_post_modal._clean_tags.return_value = []
    mock_post_modal._clean_title.return_value = ""
    with patch.object(RPPost, "save", new_callable=AsyncMock):
        yield mock_post_modal


@pytest.fixture
def changelog(interaction: MockInteraction) -> Generator[MockChangelog]:
    """The guild's Rolepost changelog channel."""
    channel = AsyncMock(spec=discord.PartialMessageable)
    interaction.client = MagicMock(spec=InconnuBot)
    interaction.client.get_partial_messageable.return_value = channel
    with patch.object(services.settings, "changelog_channel", AsyncMock(return_value=CHANGELOG_ID)):
        yield channel


def http_error[E: discord.HTTPException](cls: type[E]) -> E:
    """A Discord failure of the given type."""
    return cls(MagicMock(spec=aiohttp.ClientResponse, status=500, reason="Error"), "Failed")


# Test _clean_tags


def test_clean_tags_basic(mock_post_modal: MockPostModal):
    """Test basic tag cleaning and splitting."""
    mock_post_modal.children[-1].value = "tag1; tag2; tag3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_comma_separator(mock_post_modal: MockPostModal):
    """Test that commas are converted to semicolons."""
    mock_post_modal.children[-1].value = "tag1, tag2, tag3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_mixed_separators(mock_post_modal: MockPostModal):
    """Test mixing commas and semicolons."""
    mock_post_modal.children[-1].value = "tag1, tag2; tag3, tag4"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3", "tag4"]


def test_clean_tags_lowercase_conversion(mock_post_modal: MockPostModal):
    """Test that tags are converted to lowercase."""
    mock_post_modal.children[-1].value = "TAG1; Tag2; tAg3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_removes_special_characters(mock_post_modal: MockPostModal):
    """Test that special characters are removed (except parens and allowed chars)."""
    mock_post_modal.children[-1].value = "tag1!@#; tag2$%^; tag3&*"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_preserves_parentheses(mock_post_modal: MockPostModal):
    """Test that parentheses are preserved in tags."""
    mock_post_modal.children[-1].value = "tag (with parens); another (test)"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["another (test)", "tag (with parens)"]  # sorted


def test_clean_tags_extra_whitespace(mock_post_modal: MockPostModal):
    """Test that extra whitespace is cleaned."""
    mock_post_modal.children[-1].value = "  tag1  ;  tag2  ;  tag3  "

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_empty_tags_removed(mock_post_modal: MockPostModal):
    """Test that empty tags are removed."""
    mock_post_modal.children[-1].value = "tag1;; tag2;;; tag3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_duplicates_removed(mock_post_modal: MockPostModal):
    """Test that duplicate tags are removed."""
    mock_post_modal.children[-1].value = "tag1; tag2; tag1; tag3; tag2"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_sorted_output(mock_post_modal: MockPostModal):
    """Test that tags are sorted alphabetically."""
    mock_post_modal.children[-1].value = "zebra; alpha; beta; charlie"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["alpha", "beta", "charlie", "zebra"]


def test_clean_tags_single_tag(mock_post_modal: MockPostModal):
    """Test cleaning a single tag."""
    mock_post_modal.children[-1].value = "  Single Tag  "

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["single tag"]


def test_clean_tags_empty_string(mock_post_modal: MockPostModal):
    """Test that empty string returns empty list."""
    mock_post_modal.children[-1].value = ""

    result = PostModal._clean_tags(mock_post_modal)

    assert result == []


def test_clean_tags_only_whitespace(mock_post_modal: MockPostModal):
    """Test that whitespace-only input returns empty list."""
    mock_post_modal.children[-1].value = "   ;  ;  "

    result = PostModal._clean_tags(mock_post_modal)

    assert result == []


def test_clean_tags_only_special_chars(mock_post_modal: MockPostModal):
    """Test that special-char-only tags are removed."""
    mock_post_modal.children[-1].value = "!!!; @@@; ###"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == []


def test_clean_tags_numbers_preserved(mock_post_modal: MockPostModal):
    """Test that numbers in tags are preserved."""
    mock_post_modal.children[-1].value = "tag1; tag2; 123"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["123", "tag1", "tag2"]


def test_clean_tags_underscores_preserved(mock_post_modal: MockPostModal):
    """Test that underscores are preserved (part of \\w)."""
    mock_post_modal.children[-1].value = "tag_one; tag_two"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag_one", "tag_two"]


def test_clean_tags_complex_case(mock_post_modal: MockPostModal):
    """Test complex real-world scenario."""
    mock_post_modal.children[-1].value = "Combat (violent), Magic!!, combat (violent); TEST; test"

    result = PostModal._clean_tags(mock_post_modal)

    # lowercase, remove special chars, dedupe, sort
    assert result == ["combat (violent)", "magic", "test"]


def test_clean_tags_unicode_characters_removed(mock_post_modal: MockPostModal):
    """Test that unicode special characters are removed."""
    mock_post_modal.children[-1].value = "tag1™; tag2®; tag3©"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_hyphens_removed(mock_post_modal: MockPostModal):
    """Test that hyphens are removed (not in regex pattern)."""
    mock_post_modal.children[-1].value = "tag-one; tag-two"

    result = PostModal._clean_tags(mock_post_modal)

    # Hyphens removed, words merged
    assert result == ["tagone", "tagtwo"]


def test_clean_tags_multiple_spaces_collapsed(mock_post_modal: MockPostModal):
    """Test that multiple spaces within tags are collapsed."""
    mock_post_modal.children[-1].value = "tag   with   spaces"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag with spaces"]


def test_clean_tags_truncates_long_tags(mock_post_modal: MockPostModal):
    """Tags are cut to the length a select option can hold."""
    mock_post_modal.children[-1].value = "a" * 128

    assert PostModal._clean_tags(mock_post_modal) == ["a" * RPPost.MAX_TAG_LEN]


def test_clean_tags_strips_truncated_tags(mock_post_modal: MockPostModal):
    """Truncating a tag doesn't leave a trailing space."""
    mock_post_modal.children[-1].value = "a" * 99 + " bc"

    assert PostModal._clean_tags(mock_post_modal) == ["a" * 99]


# Test _clean_post_content


@pytest.mark.parametrize("length", [1997, 1998, 1999, 2000])
def test_clean_post_content_keeps_full_edit(mock_post_modal: MockPostModal, length: int):
    """An edit that fits the modal keeps all its text, however it's split into lines."""
    text = "\n".join(["x" * 99] * 19)
    text += "\n" + "y" * (length - len(text) - 1)
    mock_post_modal.post_to_edit = MagicMock(spec=RPPost)
    mock_post_modal.children[0].value = text

    assert PostModal._clean_post_content(mock_post_modal) == text


def test_clean_post_content_strips_edit(mock_post_modal: MockPostModal):
    """An edit loses its surrounding whitespace, but not its paragraphs."""
    mock_post_modal.post_to_edit = MagicMock(spec=RPPost)
    mock_post_modal.children[0].value = "  First\n\nSecond\n"

    assert PostModal._clean_post_content(mock_post_modal) == "First\n\nSecond"


# Test _new_rp_post


async def test_empty_post_rejected(mock_post_modal: MockPostModal):
    """A post with no content shows an error and posts nothing."""
    mock_post_modal.bot = MagicMock(spec=InconnuBot)
    mock_post_modal._clean_post_content.return_value = []
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    with patch("ui.embeds.error", new_callable=AsyncMock) as show_error:
        await PostModal._new_rp_post(mock_post_modal, interaction)

    show_error.assert_awaited_once()
    interaction.response.send_message.assert_not_awaited()
    mock_post_modal.bot.prep_webhook.assert_not_called()


async def test_new_post_overlaps_ack_with_sending(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """The post starts sending without waiting for the acknowledgment."""
    sending = asyncio.Event()

    async def prep_webhook(_: Any) -> ChannelWebhook:
        """Signal that sending has started."""
        sending.set()
        return ChannelWebhook(webhook)

    async def defer():
        """Finish only once sending has started."""
        await asyncio.wait_for(sending.wait(), timeout=1)

    posting_modal.bot.prep_webhook.side_effect = prep_webhook
    interaction.response.defer.side_effect = defer

    await PostModal._new_rp_post(posting_modal, interaction)

    interaction.response.defer.assert_awaited_once()
    assert webhook.send.await_count == 2


async def test_new_post_error_waits_for_ack(
    posting_modal: MockPostModal, interaction: MockInteraction
):
    """A failed post doesn't reach the reporter until the interaction is answered."""
    acknowledged = asyncio.Event()

    async def defer():
        """Hold the acknowledgment until the test releases it."""
        await acknowledged.wait()

    posting_modal.bot.prep_webhook.side_effect = errors.WebhookError("No permission")
    interaction.response.defer.side_effect = defer

    post = asyncio.create_task(PostModal._new_rp_post(posting_modal, interaction))
    await asyncio.sleep(0.01)

    posting_modal.bot.prep_webhook.assert_awaited_once()
    assert not post.done()

    acknowledged.set()
    with pytest.raises(errors.WebhookError):
        await post


async def test_new_post_only_pings_users(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """Every message in a post may ping users, but not roles or @everyone."""
    posting_modal.mentions = "<@1> <@&2>"

    await PostModal._new_rp_post(posting_modal, interaction)

    assert webhook.send.await_count == 3
    for call in webhook.send.await_args_list:
        allowed = call.kwargs["allowed_mentions"]
        assert allowed.users is True
        assert allowed.roles is False
        assert allowed.everyone is False


async def test_new_post_sends_as_character(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """Each page is sent under the character's name and image, in order."""
    posting_modal.character.profile_image_url = "https://example.com/char.png"

    await PostModal._new_rp_post(posting_modal, interaction)

    calls = webhook.send.await_args_list
    assert [call.kwargs["content"] for call in calls] == ["First page", "Second page"]
    for call in calls:
        assert call.kwargs["username"] == "Nadea"
        assert call.kwargs["avatar_url"] == "https://example.com/char.png"


async def test_new_post_falls_back_to_user_avatar(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """A character with no image posts with the user's avatar."""
    await PostModal._new_rp_post(posting_modal, interaction)

    assert webhook.send.await_args_list[0].kwargs["avatar_url"] == "https://example.com/avatar.png"


async def test_new_post_records_each_page(
    posting_modal: MockPostModal,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """Each page gets a saved record, but only the first has the title and tags."""
    await PostModal._new_rp_post(posting_modal, interaction)

    first, second = [call.kwargs for call in new_post.call_args_list]
    assert (first["content"], first["message"].id) == ("First page", 1)
    assert (second["content"], second["message"].id) == ("Second page", 2)
    assert (first["title"], first["tags"]) == ("A title", ["tag"])
    assert (second["title"], second["tags"]) == (None, [])


async def test_new_post_replaces_deleted_webhook(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """If the channel's webhook was deleted, the whole post goes through its
    replacement."""
    stale = AsyncMock(spec=discord.Webhook)
    response = MagicMock(spec=aiohttp.ClientResponse, status=404, reason="Not Found")
    stale.send.side_effect = discord.NotFound(response, {"code": UNKNOWN_WEBHOOK, "message": ""})
    posting_modal.bot.prep_webhook.side_effect = [ChannelWebhook(stale), ChannelWebhook(webhook)]

    await PostModal._new_rp_post(posting_modal, interaction)

    posting_modal.bot.webhook_cache.forget.assert_called_once_with(stale)
    assert [call.kwargs["content"] for call in webhook.send.await_args_list] == [
        "First page",
        "Second page",
    ]
    assert [call.kwargs["message"].id for call in new_post.call_args_list] == [1, 2]


async def test_new_post_in_thread(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    new_post: MagicMock,
):
    """Every message of a thread post goes to the thread."""
    thread = MagicMock(spec=discord.Thread)
    posting_modal.bot.prep_webhook.return_value = ChannelWebhook(webhook, thread)
    posting_modal.show_header = True
    posting_modal.mentions = "<@10>"

    with (
        patch("inconnu.header.embed", return_value=discord.Embed(description="Header")),
        patch("inconnu.header.register", new_callable=AsyncMock),
    ):
        await PostModal._new_rp_post(posting_modal, interaction)

    assert webhook.send.await_count == 4  # Header, two pages, mentions
    assert all(call.kwargs["thread"] is thread for call in webhook.send.await_args_list)


async def test_new_post_saves_records(
    posting_modal: MockPostModal,
    interaction: MockInteraction,
):
    """All of a post's records are saved, with the whole ID chain."""
    record = AsyncMock(spec=RPPost)

    with patch.object(RPPost, "new", return_value=record):
        await PostModal._new_rp_post(posting_modal, interaction)

    assert record.save.await_count == 2
    assert record.id_chain == [1, 2]


async def test_new_post_chain_covers_header_and_mentions(
    posting_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
):
    """The ID chain runs from the header to the mentions, which are extracted as
    user IDs only."""
    posting_modal.show_header = True
    posting_modal.mentions = "<@10> <@!11> <@&12> <#13>"
    record = AsyncMock(spec=RPPost)

    with (
        patch("inconnu.header.embed", return_value=discord.Embed(description="Header")),
        patch("inconnu.header.register", new_callable=AsyncMock) as register,
        patch.object(RPPost, "new", return_value=record) as new,
    ):
        await PostModal._new_rp_post(posting_modal, interaction)

    assert record.id_chain == [1, 2, 3, 4]
    assert new.call_args.kwargs["mentions"] == [10, 11]

    header_embed = webhook.send.await_args_list[0].kwargs["embed"]
    assert f"*Author: <@{USER_ID}>*" in header_embed.description
    assert webhook.send.await_args_list[-1].kwargs["content"] == posting_modal.mentions
    assert register.call_args.args[1].id == 1


# Test _edit_rp_post


async def test_empty_edit_rejected(mock_post_modal: MockPostModal):
    """An edit with no content points to Post: Delete and changes nothing."""
    post = AsyncMock(spec=RPPost)
    mock_post_modal.post_to_edit = post
    mock_post_modal.bot = MagicMock(spec=InconnuBot)
    mock_post_modal.children[0].value = " \n "
    mock_post_modal._clean_post_content.side_effect = lambda: PostModal._clean_post_content(
        mock_post_modal
    )
    interaction = AsyncMock(spec=discord.Interaction)

    with patch("ui.embeds.error", new_callable=AsyncMock) as show_error:
        await PostModal._edit_rp_post(mock_post_modal, interaction)

    show_error.assert_awaited_once()
    assert "`Post: Delete`" in show_error.call_args.args[1]
    mock_post_modal.bot.prep_webhook.assert_not_called()
    post.edit_post.assert_not_called()
    post.save.assert_not_awaited()


async def test_edit_updates_message_and_history(
    editing_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
):
    """New content goes to the message and the record, keeping the old content."""
    editing_modal._clean_post_content.return_value = "Changed"

    await PostModal._edit_rp_post(editing_modal, interaction)

    post = editing_modal.post_to_edit
    webhook.edit_message.assert_awaited_once_with(MESSAGE_ID, content="Changed")
    assert post.content == "Changed"
    assert post.history[0].content == "Original"
    post.save.assert_awaited_once()
    editing_modal._post_to_changelog.assert_awaited_once()
    assert interaction.response.send_message.await_args.args[0] == "Post updated!"


async def test_edit_without_content_change(
    editing_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
):
    """Changing only the title and tags leaves the message and changelog alone."""
    editing_modal._clean_title.return_value = "A title"
    editing_modal._clean_tags.return_value = ["tag"]

    await PostModal._edit_rp_post(editing_modal, interaction)

    post = editing_modal.post_to_edit
    assert post.title == "A title"
    assert post.tags == ["tag"]
    assert post.history == []
    post.save.assert_awaited_once()
    webhook.edit_message.assert_not_awaited()
    editing_modal._post_to_changelog.assert_not_awaited()


async def test_edit_can_clear_title(editing_modal: MockPostModal, interaction: MockInteraction):
    """Emptying the title field removes the bookmark."""
    editing_modal.post_to_edit.title = "A title"

    await PostModal._edit_rp_post(editing_modal, interaction)

    assert editing_modal.post_to_edit.title is None


async def test_edit_of_missing_message(
    editing_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    show_error: AsyncMock,
):
    """If the message is gone, the user is told and the record isn't changed."""
    editing_modal._clean_post_content.return_value = "Changed"
    webhook.edit_message.side_effect = http_error(discord.NotFound)

    await PostModal._edit_rp_post(editing_modal, interaction)

    post = editing_modal.post_to_edit
    assert show_error.call_args.kwargs["title"] == "Unable to edit message"
    assert post.content == "Original"
    post.save.assert_not_awaited()
    editing_modal._post_to_changelog.assert_not_awaited()


@pytest.mark.parametrize("content", ["Original", "Changed"])
@pytest.mark.parametrize("found", [True, False])
async def test_edit_of_post_deleted_while_editing(
    editing_modal: MockPostModal,
    webhook: MockWebhook,
    interaction: MockInteraction,
    get_post: MockGet,
    show_error: AsyncMock,
    content: str,
    found: bool,
):
    """A post deleted while the modal was open stays deleted, whether or not
    the content changed."""
    post = editing_modal.post_to_edit
    if found:
        post.deleted = True
    else:
        get_post.return_value = None
    editing_modal._clean_post_content.return_value = content
    editing_modal._clean_title.return_value = "A title"

    await PostModal._edit_rp_post(editing_modal, interaction)

    get_post.assert_awaited_once_with(post.id)
    assert show_error.call_args.kwargs["title"] == "Unable to edit post"
    webhook.edit_message.assert_not_awaited()
    post.save.assert_not_awaited()
    interaction.response.send_message.assert_not_awaited()


async def test_edit_keeps_edits_made_elsewhere(
    editing_modal: MockPostModal,
    interaction: MockInteraction,
    get_post: MockGet,
    make_post: PostFactory,
):
    """An edit made in another modal stays in the history."""
    current = make_post("Original", id=editing_modal.post_to_edit.id)
    current.edit_post("Edited elsewhere")
    get_post.return_value = current
    editing_modal._clean_post_content.return_value = "Changed"

    await PostModal._edit_rp_post(editing_modal, interaction)

    assert editing_modal.post_to_edit is current
    assert current.content == "Changed"
    assert [entry.content for entry in current.history] == ["Edited elsewhere", "Original"]
    cast(AsyncMock, current.save).assert_awaited_once()  # Patched by editing_modal


# Test _post_to_changelog


async def test_changelog_shows_diff(
    editing_modal: MockPostModal,
    interaction: MockInteraction,
    changelog: MockChangelog,
):
    """The changelog says who edited the post and shows what changed."""
    post = editing_modal.post_to_edit
    post.id = PydanticObjectId()
    post.edit_post("Changed")

    await PostModal._post_to_changelog(editing_modal, interaction)

    interaction.client.get_partial_messageable.assert_called_once_with(CHANGELOG_ID)
    embed = changelog.send.await_args.kwargs["embed"]
    assert f"<@{USER_ID}> edited a post in <#{post.channel}>" in embed.description
    assert "- Original" in embed.description
    assert "+ Changed" in embed.description
    assert str(post.id) in embed.url
    assert embed.fields[0].value == str(post.url)


async def test_changelog_names_thread(
    editing_modal: MockPostModal,
    interaction: MockInteraction,
    changelog: MockChangelog,
):
    """A thread post's changelog names the thread, not its parent."""
    post = editing_modal.post_to_edit
    post.thread = 9000
    post.edit_post("Changed")

    await PostModal._post_to_changelog(editing_modal, interaction)

    assert "edited a post in <#9000>" in changelog.send.await_args.kwargs["embed"].description


async def test_changelog_fits_embed(
    editing_modal: MockPostModal,
    interaction: MockInteraction,
    changelog: MockChangelog,
):
    """A long diff is cut to fit the embed, and its code block stays closed."""
    post = editing_modal.post_to_edit
    post.id = PydanticObjectId()
    post.content = "a\n" * 1000
    post.edit_post("b\n" * 1000)

    await PostModal._post_to_changelog(editing_modal, interaction)

    description = changelog.send.await_args.kwargs["embed"].description
    assert len(description) <= 4096
    assert description.endswith("```")


async def test_changelog_not_set(editing_modal: MockPostModal, interaction: MockInteraction):
    """Nothing is sent without a changelog channel."""
    interaction.client = MagicMock(spec=InconnuBot)

    with patch.object(services.settings, "changelog_channel", AsyncMock(return_value=None)):
        await PostModal._post_to_changelog(editing_modal, interaction)

    interaction.client.get_partial_messageable.assert_not_called()


@pytest.mark.parametrize("error", [discord.Forbidden, discord.HTTPException])
async def test_changelog_failure_is_ignored(
    editing_modal: MockPostModal,
    interaction: MockInteraction,
    changelog: MockChangelog,
    error: type[discord.HTTPException],
):
    """A broken changelog channel doesn't turn a good edit into an error."""
    post = editing_modal.post_to_edit
    post.id = PydanticObjectId()
    post.edit_post("Changed")
    changelog.send.side_effect = http_error(error)

    await PostModal._post_to_changelog(editing_modal, interaction)

    changelog.send.assert_awaited_once()


# Test PostModal.__init__


def saved_vampire() -> VChar:
    """A saved vampire."""
    vamp = gen_char("vampire")
    vamp.id = PydanticObjectId()
    return vamp


async def test_new_modal_fields():
    """A new post has two message boxes, up to 4,000 characters, and a fresh header."""
    vamp = saved_vampire()
    options: dict[str, Any] = {"location": "Elysium", "mentions": "Hi <@1>", "show_header": False}

    modal = PostModal(vamp, MagicMock(spec=InconnuBot), title="Post", **options)

    assert len(modal.children) == 4
    assert modal.children[0].max_length == 4000
    assert modal.children[1].required is False
    assert modal.header.location == "Elysium"
    assert modal.mentions == "<@1>"
    assert modal.show_header is False


async def test_edit_modal_fields(make_post: PostFactory):
    """An edit has one message box, up to 2,000 characters, filled from the post."""
    post = make_post("The content", title="A title", tags=["one", "two"])
    message = MagicMock(spec=discord.Message)

    modal = PostModal(
        saved_vampire(),
        MagicMock(spec=InconnuBot),
        title="Edit",
        rp_post=post,
        message=message,
    )

    assert len(modal.children) == 3
    assert modal.children[0].max_length == 2000
    assert modal.children[0].value == "The content"
    assert modal.children[1].value == "A title"
    assert modal.children[2].value == "one; two"
    assert modal.header is post.header


# Test create_post


async def test_create_post_opens_modal(rp_ctx: MockCtx):
    """A channel that allows webhooks gets the post modal."""
    rp_ctx.bot.can_webhook.return_value = True
    vamp = saved_vampire()
    options: dict[str, Any] = {"mentions": "<@1>"}

    await inspect.unwrap(create_post)(rp_ctx, vamp, **options)

    modal = rp_ctx.send_modal.await_args.args[0]
    assert isinstance(modal, PostModal)
    assert modal.title == f"{vamp.name}'s Post"
    assert modal.mentions == "<@1>"


@pytest.mark.parametrize(
    "channel,message",
    [
        (MagicMock(spec=discord.Thread, locked=True), "locked"),
        (MagicMock(spec=discord.Thread, locked=False), "`Manage Webhooks`"),
        (MagicMock(spec=discord.TextChannel), "`Manage Webhooks`"),
    ],
)
async def test_create_post_without_webhooks(
    rp_ctx: MockCtx,
    show_error: AsyncMock,
    channel: MagicMock,
    message: str,
):
    """A channel that can't use webhooks gets an error saying why."""
    rp_ctx.bot.can_webhook.return_value = False
    rp_ctx.channel = channel

    await inspect.unwrap(create_post)(rp_ctx, saved_vampire())

    assert message in show_error.call_args.args[1]
    rp_ctx.send_modal.assert_not_awaited()


# Test edit_post


async def test_edit_post_opens_modal(rp_ctx: MockCtx, make_post: PostFactory):
    """A user's own post opens the edit modal for its character."""
    post = make_post()
    message = MagicMock(spec=discord.Message, id=MESSAGE_ID)

    with (
        patch.object(RPPost, "find_one", AsyncMock(return_value=post)) as find_one,
        patch.object(
            services.char_mgr, "fetchone", AsyncMock(return_value=saved_vampire())
        ) as fetchone,
    ):
        await edit_post(rp_ctx, message)

    assert find_one.call_args.args[0] == {"message_id": MESSAGE_ID}
    assert fetchone.call_args.args[2] == str(post.header.charid)
    modal = rp_ctx.send_modal.await_args.args[0]
    assert modal.post_to_edit is post
    assert modal.message is message


async def test_edit_post_not_a_rolepost(rp_ctx: MockCtx, show_error: AsyncMock):
    """Only Roleposts can be edited."""
    with patch.object(RPPost, "find_one", AsyncMock(return_value=None)):
        await edit_post(rp_ctx, MagicMock(spec=discord.Message))

    assert show_error.call_args.args[1] == "This isn't a Rolepost!"
    rp_ctx.send_modal.assert_not_awaited()


async def test_edit_post_of_another_user(
    rp_ctx: MockCtx, make_post: PostFactory, show_error: AsyncMock
):
    """Users can only edit their own posts."""
    post = make_post(user=USER_ID + 1)

    with patch.object(RPPost, "find_one", AsyncMock(return_value=post)):
        await edit_post(rp_ctx, MagicMock(spec=discord.Message))

    assert show_error.call_args.args[1] == "You can only edit your own posts!"
    rp_ctx.send_modal.assert_not_awaited()


async def test_edit_post_of_deleted_character(
    rp_ctx: MockCtx, make_post: PostFactory, show_error: AsyncMock
):
    """A deleted character's posts can't be edited."""
    with (
        patch.object(RPPost, "find_one", AsyncMock(return_value=make_post())),
        patch.object(
            services.char_mgr,
            "fetchone",
            AsyncMock(side_effect=errors.CharacterNotFoundError("Gone")),
        ),
    ):
        await edit_post(rp_ctx, MagicMock(spec=discord.Message))

    assert "deleted character" in show_error.call_args.args[1]
    rp_ctx.send_modal.assert_not_awaited()


@pytest.mark.parametrize("error", [errors.WrongGuild, errors.WrongOwner])
async def test_edit_post_of_transferred_character(error: type[errors.CharacterError]):
    """Editing a post after its character changed hands shows the reason."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.user = MagicMock(spec=discord.Member, id=1)
    rp_post = MagicMock(spec=RPPost, user=1)

    with (
        patch.object(RPPost, "find_one", AsyncMock(return_value=rp_post)),
        patch.object(services.char_mgr, "fetchone", AsyncMock(side_effect=error("Not yours"))),
        patch("ui.embeds.error", new_callable=AsyncMock) as show_error,
    ):
        await edit_post(ctx, MagicMock(spec=discord.Message))

    show_error.assert_awaited_once()
    assert str(show_error.call_args.args[1]) == "Not yours"
