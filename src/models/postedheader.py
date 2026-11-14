"""Posted RP header records."""

from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel
from pymongo import IndexModel


class HeaderOwner(BaseModel):
    """The character a posted header belongs to."""

    guild: int
    user: int
    charid: PydanticObjectId
    spc: bool | None = None  # Unknown: headers before December 2023 lack it


class PostedHeader(Document):
    """A header posted to a channel, tracked so it can be edited or deleted. A
    thread's header also records the thread's parent, since deleting the parent
    deletes the thread without a thread deletion event."""

    character: HeaderOwner
    channel: int
    message: int
    parent: int | None = None
    timestamp: datetime

    class Settings:
        name = "headers"
        indexes = [
            IndexModel("message", unique=True),
            # Deleting a channel deletes its headers and its threads' headers
            "channel",
            "parent",
        ]
