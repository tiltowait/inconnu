"""Tests for models/rppost.py."""

from unittest.mock import MagicMock

import discord
import pytest
from beanie import PydanticObjectId

from models import BlushState, RPPost, VChar
from models.rpheader import DamageSubdoc, HeaderSubdoc

type MockChannel = MagicMock
type MockInteraction = MagicMock

GUILD_ID = 1
CHANNEL_ID = 2
THREAD_ID = 3


def header() -> HeaderSubdoc:
    """A Rolepost header."""
    damage = DamageSubdoc(superficial=0, aggravated=0)
    return HeaderSubdoc(
        charid=PydanticObjectId(),
        char_name="Nadea",
        blush=BlushState.NA,
        hunger=1,
        location="",
        merits="",
        flaws="",
        temp="",
        health=damage,
        willpower=damage,
    )


def new_post(channel: MockChannel) -> RPPost:
    """A new Rolepost made in the given channel."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.channel = channel
    interaction.channel_id = channel.id
    interaction.user = MagicMock(spec=discord.Member, id=4)
    character = MagicMock(spec=VChar, guild=GUILD_ID)
    message = MagicMock(spec=discord.WebhookMessage, id=5)
    message.jump_url = f"https://discord.com/channels/{GUILD_ID}/{channel.id}/5"

    return RPPost.new(
        interaction=interaction,
        character=character,
        header=header(),
        content="Content",
        message=message,
        mentions=[],
        title=None,
        tags=[],
    )


def thread(*, private: bool) -> MockChannel:
    """A thread in CHANNEL_ID."""
    mock = MagicMock(spec=discord.Thread, id=THREAD_ID, parent_id=CHANNEL_ID)
    mock.is_private.return_value = private
    return mock


def test_new_post_in_channel():
    """A channel post has no thread."""
    post = new_post(MagicMock(spec=discord.TextChannel, id=CHANNEL_ID))

    assert (post.channel, post.thread, post.private_channel) == (CHANNEL_ID, None, None)
    assert post.location == CHANNEL_ID


@pytest.mark.parametrize("private,private_channel", [(False, None), (True, CHANNEL_ID)])
def test_new_post_in_thread(private: bool, private_channel: int | None):
    """A thread post records its parent as the channel, and private threads
    mark the post private."""
    post = new_post(thread(private=private))

    assert (post.channel, post.thread) == (CHANNEL_ID, THREAD_ID)
    assert post.private_channel == private_channel
    assert post.location == THREAD_ID
