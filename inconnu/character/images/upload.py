"""Character image uploading."""

import os
from pathlib import Path

import aiohttp
import async_timeout
import discord
from bson.objectid import ObjectId
from PIL import Image

import inconnu
import s3
from logger import Logger

__HELP_URL = "https://www.inconnu.app"
VALID_EXTENSIONS = [".png", ".webp", ".jpg", ".jpeg"]


async def upload_image(ctx: discord.ApplicationContext, image: discord.Attachment, character: str):
    """Upload an image. Only premium users can use this feature."""
    if not valid_url(image.url):
        embed = inconnu.utils.ErrorEmbed(
            ctx.user,
            "This is not a valid image file!",
            ("Allowed extensions", ", ".join(VALID_EXTENSIONS)),
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/character image upload` `character:CHARACTER`",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    if not ctx.interaction.response.is_done():
        # If we responded already, there's no chance of timeout; also we can't
        # defer if we've responded, so ...
        await ctx.defer(ephemeral=True)

    original = await download_file(image.url)
    Logger.debug(
        "IMAGES: Downloaded image for %s, size=%s", character.name, os.stat(original).st_size
    )
    webp = convert_to_webp(original)

    destination = f"profiles/{character.id}/{webp}"
    await s3.upload_file(webp, destination)
    aws_url = s3.get_url(destination)

    if aws_url in character.profile.images:
        Logger.info("IMAGES: %s: Ignoring duplicate image: %s", character.name, aws_url)
    else:
        Logger.info("IMAGES: %s: Adding image URL: %s", character.name, aws_url)
        character.profile.images.append(aws_url)
    delete_file(webp)

    embed = inconnu.utils.VCharEmbed(
        ctx,
        character,
        title="Image uploaded!",
        character_author=True,
        show_thumbnail=False,
    )
    embed.set_image(url=aws_url)
    embed.set_footer(text="View your images with /character images.")

    await ctx.respond(embed=embed, ephemeral=True)
    await character.commit()

    # We maintain a log of all image uploads to protect ourself against
    # potential legal claims if someone uploads something illegal
    await inconnu.db.upload_log.insert_one(
        {
            "user": ctx.user.id,
            "charid": character.pk,
            "url": aws_url,
            "deleted": False,
            "timestamp": discord.utils.utcnow(),
        }
    )


def valid_url(url: str) -> bool:
    """Check whether a URL is a valid image URL."""
    url = url.lower()
    Logger.debug("IMAGES: Checking validity of %s", url)

    for extension in VALID_EXTENSIONS:
        if url.endswith(extension):
            return True
    return False


async def download_file(url: str) -> Path:
    """Download a file."""
    filename = Path(str(ObjectId()))
    Logger.debug("IMAGES: Downloading %s to %s", url, filename)

    async with async_timeout.timeout(120):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                with open(filename, "wb") as file:
                    async for data in response.content.iter_chunked(1024):
                        file.write(data)

    return filename


def convert_to_webp(source: str, quality=99) -> Path:
    """Convert an image file to WebP."""
    destination = source.with_suffix(".webp")
    image = Image.open(source)
    image.save(destination, format="webp", quality=quality)
    Logger.debug(
        "IMAGES: Converted %s to WebP with quality=%s, size=%s",
        source,
        quality,
        os.stat(destination).st_size,
    )
    delete_file(source)
    return destination


def delete_file(file: str):
    """Delete a file."""
    if os.path.exists(file):
        Logger.debug("IMAGES: Deleting temporary image file %s", file)
        os.remove(file)
    else:
        Logger.error("IMAGES: Attempted to delete file that doesn't exist: %s", file)
