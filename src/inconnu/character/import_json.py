"""Import characters exported by other tools."""

import discord
from pydantic import ValidationError

import errors
import services
import ui
from constants import Damage
from ctx import AppCtx
from models import VChar
from routes.characters.models import CreationBody

MAX_IMPORT_SIZE = 1_000_000


async def import_progeny(ctx: AppCtx, attachment: discord.Attachment):
    """Import a Progeny JSON export for the invoking user."""
    if attachment.size > MAX_IMPORT_SIZE:
        await ui.embeds.error(ctx, "The JSON file must be smaller than 1 MB.")
        return

    try:
        data = CreationBody.model_validate_json(await attachment.read())
    except ValidationError as err:
        issue = err.errors()[0]
        location = ".".join(str(part) for part in issue["loc"]) or "document"
        await ui.embeds.error(
            ctx,
            f"Invalid Progeny JSON at `{location}`: {issue['msg']}.",
        )
        return

    character = VChar(
        guild=ctx.guild.id,
        user=ctx.user.id,
        name=data.name,
        splat=data.splat,
        humanity=data.humanity,
        health=data.health * Damage.NONE,
        willpower=data.willpower * Damage.NONE,
        potency=data.blood_potency,
        traits=sorted(data.traits, key=lambda trait: trait.name.casefold()),
    )
    character.profile.biography = data.biography
    character.profile.description = data.description
    character.convictions = data.convictions

    try:
        await services.char_mgr.register(character)
    except errors.DuplicateCharacterError as err:
        await ui.embeds.error(ctx, err)
        return

    await ctx.respond(f"Imported **{character.raw_name}** from Progeny.", ephemeral=True)
