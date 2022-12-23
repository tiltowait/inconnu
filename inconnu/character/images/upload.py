"""Character image uploading."""

import os

import aiohttp
import async_timeout
import discord

import inconnu
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/guides/premium/character-images"
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

    try:
        aws_image_url = await process_file(character.id, image.url)
        Logger.info("IMAGES: %s: Uploaded new image to %s", character.name, aws_image_url)

        character.profile.images.append(aws_image_url)

        embed = inconnu.utils.VCharEmbed(
            ctx,
            character,
            title="Image uploaded!",
            show_thumbnail=False,
        )
        embed.set_image(url=aws_image_url)
        embed.set_footer(text="View your images with /character images.")

        await ctx.respond(embed=embed, ephemeral=True)
        await character.commit()

        # We maintain a log of all image uploads to protect ourself against
        # potential legal claims if someone uploads something illegal
        await inconnu.db.upload_log.insert_one(
            {
                "guild": ctx.guild.id,
                "user": ctx.user.id,
                "charid": character.pk,
                "url": aws_image_url,
                "deleted": False,
                "timestamp": discord.utils.utcnow(),
            }
        )

    except (aiohttp.ClientResponseError, aiohttp.ClientConnectorError):
        await inconnu.utils.error(ctx, "Unable to process image. Please try again later.")


def valid_url(url: str) -> bool:
    """Check whether a URL is a valid image URL."""
    url = url.lower()
    Logger.debug("IMAGES: Checking validity of %s", url)

    for extension in VALID_EXTENSIONS:
        if url.endswith(extension):
            return True
    return False


async def process_file(charid: str, image_url: str) -> str:
    """Send the file URL to the API for processing."""
    url = "https://api.inconnu.app/upload-fc"
    token = os.environ["INCONNU_API_TOKEN"]
    header = {"Authorization": f"token {token}"}
    payload = {"charid": charid, "image_url": image_url}

    async with async_timeout.timeout(60):
        async with aiohttp.ClientSession(headers=header, raise_for_status=True) as session:
            async with session.post(url, json=payload) as response:
                response_json = await response.json()
                return response_json["url"]  # The image's new bucket URL
