"""Tests for command decorators."""

from typing import Any
from unittest.mock import MagicMock

import discord
import pytest

import errors
from ctx import AppCtx
from utils.decorators import _format_size, attachment


def make_ctx(*files: tuple[str, int]) -> AppCtx:
    """Make a context whose interaction carries the given (filename, size) attachments."""
    data: dict[str, Any] = {
        "resolved": {
            "attachments": {
                str(i): {"filename": name, "size": size} for i, (name, size) in enumerate(files)
            }
        }
    }
    inter = MagicMock(spec=discord.Interaction)
    inter.data = data
    ctx = MagicMock(spec=AppCtx)
    ctx.interaction = inter
    return ctx


async def check(ctx: AppCtx, **kwargs: Any) -> bool:
    """Run the attachment check's predicate."""
    return await attachment(**kwargs).predicate(ctx)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "filename,extensions",
    [
        ("image.png", [".png", ".jpg"]),
        ("IMAGE.PNG", [".png"]),
        ("image.jpg", ["JPG"]),
        ("anything.exe", None),
    ],
)
async def test_allowed_extension(filename: str, extensions: list[str] | None):
    assert await check(make_ctx((filename, 100)), extensions=extensions)


@pytest.mark.parametrize("filename", ["image.gif", "image", "png", "image.png.exe"])
async def test_rejected_extension(filename: str):
    with pytest.raises(errors.InvalidAttachment, match=r"`\.jpg`, `\.png`"):
        await check(make_ctx((filename, 100)), extensions=[".png", ".jpg"])


@pytest.mark.parametrize("size,allowed", [(1023, True), (1024, True), (1025, False)])
async def test_filesize(size: int, allowed: bool):
    ctx = make_ctx(("file.json", size))
    if allowed:
        assert await check(ctx, filesize=1024)
    else:
        with pytest.raises(errors.InvalidAttachment, match="1 KB"):
            await check(ctx, filesize=1024)


async def test_every_attachment_checked():
    ctx = make_ctx(("a.png", 100), ("b.gif", 100))
    with pytest.raises(errors.InvalidAttachment):
        await check(ctx, extensions=[".png"])


async def test_no_attachments():
    inter = MagicMock(spec=discord.Interaction)
    inter.data = {}
    ctx = MagicMock(spec=AppCtx)
    ctx.interaction = inter
    assert await check(ctx, extensions=[".png"], filesize=1)


@pytest.mark.parametrize(
    "size,expected",
    [(1023, "1023 bytes"), (1024, "1 KB"), (1536, "1.5 KB"), (5 * 1024**2, "5 MB")],
)
def test_format_size(size: int, expected: str):
    assert _format_size(size) == expected
