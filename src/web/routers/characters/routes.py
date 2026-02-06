"""Character API routes."""

import discord
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import errors
import inconnu
from config import API_KEY
from constants import Damage
from models import VChar
from services import char_mgr, wizard_cache
from services.wizard import CharacterGuild
from web.routers.characters.models import (
    AuthorizedCharacter,
    AuthorizedCharacterList,
    BaseProfile,
    CreationBody,
    CreationSuccess,
    OwnerData,
    ProfileWithOwner,
    WizardSchema,
)

DISCORD_HEADER = "X-Discord-User-ID"

router = APIRouter()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> HTTPAuthorizationCredentials:
    """Validates the API bearer token."""
    if credentials.credentials != API_KEY:
        raise HTTPException(401, detail="Invalid authentication token")
    return credentials


async def get_authenticated_user(
    request: Request,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> int:
    """Get the authenticated user ID from headers after verifying API key."""
    user_id = request.headers.get(DISCORD_HEADER)
    if user_id is None:
        raise HTTPException(400, detail="Missing user ID")
    return int(user_id)


# Getters


@router.get("/characters")
async def get_character_list(
    user_id: int = Depends(get_authenticated_user),
) -> AuthorizedCharacterList:
    """Get all of the user's characters and the guilds they belong to."""
    guilds = []
    guild_ids = set()
    for guild in inconnu.bot.guilds:
        if guild.get_member(user_id) is not None:
            guilds.append(CharacterGuild.create(guild))
            guild_ids.add(guild.id)

    chars = []
    for char in await char_mgr.fetchuser(user_id):
        if char.stat_log.get("left") is not None:
            continue
        if char.guild in guild_ids:
            chars.append(char)

    return AuthorizedCharacterList(guilds=guilds, characters=chars)


@router.get("/characters/{oid}")
async def get_full_character(
    oid: PydanticObjectId,
    user_id: int = Depends(get_authenticated_user),
) -> AuthorizedCharacter:
    """Returns a given character if it belongs to the authed user. This
    endpoint requires authorization checks, as it returns the entire character
    object!"""
    char = await char_mgr.fetchid(oid)

    if char is None:
        raise HTTPException(404, detail="Character not found")
    if int(user_id) != char.user:
        raise HTTPException(403, detail="User does not own character")

    guild = await CharacterGuild.fetch(char.guild)

    return AuthorizedCharacter(
        guild=guild,
        character=char,
    )


@router.get("/characters/guild/{guild_id}")
async def get_guild_characters(
    guild_id: int,
    user_id: int = Depends(get_authenticated_user),
) -> list[ProfileWithOwner]:
    """Get all character base profiles belonging to the guild. Excludes
    characters whose owners have left the server."""
    guild = await inconnu.bot.get_or_fetch_guild(guild_id)
    if guild is None:
        raise HTTPException(404, detail="Guild not found")
    member = await guild.get_or_fetch(discord.Member, user_id)
    if member is None:
        raise HTTPException(400, detail="User does not belong to guild")

    char_guild = CharacterGuild.create(guild)
    profiles = []
    for char in await char_mgr.fetchguild(guild_id):
        if char.stat_log.get("left") is not None:
            continue

        if char.is_spc:
            owner_data = None
        else:
            owner_data = await OwnerData.create(char.guild, char.user)
            if owner_data is None:
                # We couldn't find them; maybe Discord is throwing a fit.
                # Without owner data, however, we won't return this character.
                continue

        base_profile = await BaseProfile.create(char, char_guild)
        guild_profile = ProfileWithOwner(character=base_profile, owner_data=owner_data)
        profiles.append(guild_profile)

    return profiles


@router.get("/characters/profile/{oid}")
async def get_character_profile(
    oid: PydanticObjectId,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> BaseProfile:
    """Fetch a character profile. This endpoint returns a non-sensitive character
    model with only name, ownership data, and public profile data."""
    char = await char_mgr.fetchid(oid)
    if char is None:
        raise HTTPException(404, detail="Character not found.")

    return await BaseProfile.create(char)


# Wizard


@router.get("/characters/wizard/{token}")
async def get_wizard(
    token: str,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> WizardSchema:
    """Get the character wizard schema."""
    wizard = wizard_cache.get(token)
    if wizard is None:
        raise HTTPException(404, detail="Unknown token. It may have expired.")

    return WizardSchema(
        spc=wizard.spc,
        guild=wizard.guild,
    )


@router.post("/characters/wizard/{token}", status_code=201)
async def create_character(
    token: str,
    data: CreationBody,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> CreationSuccess:
    """Create the character and insert it into the database."""
    wizard = wizard_cache.pop(token)
    if wizard is None:
        raise HTTPException(404, detail="Unknown token. It may have expired.")

    # We need to sort the traits before setting them
    traits = sorted(data.traits, key=lambda t: t.name.casefold())
    owner_id = wizard.user if not wizard.spc else VChar.SPC_OWNER

    character = VChar(
        guild=wizard.guild.id,
        user=owner_id,
        name=data.name,
        splat=data.splat,
        humanity=data.humanity,
        health=data.health * Damage.NONE,
        willpower=data.willpower * Damage.NONE,
        potency=data.blood_potency,
        traits=traits,
    )
    character.profile.biography = data.biography
    character.profile.description = data.description
    character.convictions = data.convictions

    try:
        await char_mgr.register(character)
    except errors.DuplicateCharacterError as err:
        raise HTTPException(422, detail=str(err)) from err

    return CreationSuccess(
        guild=wizard.guild,
        character_id=character.id_str,
        character_name=character.name,
    )
