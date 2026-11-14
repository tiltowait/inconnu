"""Rolepost models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

import discord
from beanie import Document
from pydantic import AnyUrl, BaseModel, Field
from pymongo import ASCENDING, TEXT, IndexModel

from models.rpheader import HeaderSubdoc

if TYPE_CHECKING:
    from models import VChar

# Every player-facing query starts with a player's live posts in a guild
_OWNER = [("deleted", ASCENDING), ("guild", ASCENDING), ("user", ASCENDING)]

# /search with search text. This is the form MongoDB stores a text index in,
# rather than the usual ("content", TEXT). Beanie drops and rebuilds any index
# that doesn't match its declaration, and it compares against the stored form.
_TEXT_INDEX = IndexModel(
    [*_OWNER, ("_fts", TEXT), ("_ftsx", ASCENDING), ("date", ASCENDING)],
    name="deleted_1_guild_1_user_1_content_text_date_1",
    weights={"content": 1},
    default_language="english",
    language_override="language",
    textIndexVersion=3,
)


class PostHistoryEntry(BaseModel):
    """Represents historic post content and a date of modification."""

    date: datetime
    content: str


class RPPost(Document):
    """Represents a Rolepost with the ability to maintain deltas."""

    MAX_TAG_LEN: ClassVar[int] = 100  # Tags must fit a Discord select option

    # Metadata
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    date_modified: datetime | None = None
    guild: int
    channel: int  # A thread's parent, so posts share its visibility and fate
    thread: int | None = None
    # The parent's ID for posts in private threads. Searches by other players
    # match it against the channels where they can manage threads.
    private_channel: int | None = None
    user: int
    message_id: int
    url: AnyUrl | None
    deleted: bool = False
    deletion_date: datetime | None = None
    id_chain: list[int] = Field(default_factory=list)

    # Content
    header: HeaderSubdoc
    content: str
    mentions: list[int] = Field(default_factory=list)
    history: list[PostHistoryEntry] = Field(default_factory=list)

    # Custom
    title: str | None = None
    tags: list[str] = Field(default_factory=list)

    @property
    def location(self) -> int:
        """The ID of the thread or channel the post is in."""
        return self.thread or self.channel

    @property
    def utc_date(self) -> datetime:
        """The UTC-aware post date."""
        return self.date.replace(tzinfo=UTC)

    class Settings:
        name = "rp_posts"
        use_state_management = True
        validate_on_save = True
        indexes = [
            IndexModel("message_id", unique=True),
            "id_chain",  # Replies to any message of a post
            "channel",
            "thread",
            # /search without search text, newest or oldest first
            [*_OWNER, ("date", ASCENDING)],
            _TEXT_INDEX,
            [*_OWNER, ("tags", ASCENDING)],
            [*_OWNER, ("title", ASCENDING)],  # Bookmarks
        ]

    @classmethod
    def new(
        cls,
        *,
        interaction: discord.Interaction,
        character: VChar,
        header: HeaderSubdoc,
        content: str,
        message: discord.Message,
        mentions: list[int],
        title: str | None,
        tags: list[str],
    ):
        """Create a Rolepost."""
        if interaction.channel_id is None:
            raise ValueError("Interaction channel has no ID")
        if interaction.user is None:
            raise ValueError("Interaction user does not exist")

        channel = interaction.channel_id
        thread = None
        private_channel = None
        if isinstance(interaction.channel, discord.Thread):
            channel = interaction.channel.parent_id
            thread = interaction.channel.id
            if interaction.channel.is_private():
                private_channel = channel

        return cls(
            guild=character.guild,
            channel=channel,
            thread=thread,
            private_channel=private_channel,
            user=interaction.user.id,
            message_id=message.id,
            header=header,
            content=content,
            url=AnyUrl(message.jump_url),
            mentions=mentions,
            title=title,
            tags=tags,
        )

    def edit_post(self, new_post: str):
        """Update the post content, if necessary."""
        if new_post != self.content:
            # We only bother with this if the post was actually changed
            entry = PostHistoryEntry(
                date=self.date_modified or self.date,
                content=self.content,
            )
            self.history.insert(0, entry)
            self.content = new_post
            self.date_modified = datetime.now(UTC)
