"""Character API routes."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import errors
import inconnu
from config import API_KEY
from constants import Damage
from models import VChar
from services import char_mgr, guild_cache, wizard_cache
from services.wizard import CharacterGuild
from web.routers.characters.models import (
    CharData,
    CreationBody,
    CreationSuccess,
    GuildChars,
    OwnerData,
    PublicCharacter,
    UserCharData,
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
) -> UserCharData:
    """Get all of the user's characters and the guilds they belong to."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up.")

    guilds = {}
    for guild in await guild_cache.fetchguilds():
        if guild.id in guilds:
            # Shouldn't be possible
            continue
        if guild.get_member(user_id) is not None:
            guilds[guild.id] = CharacterGuild.create(guild)

    chars = []
    for char in await char_mgr.fetchuser(user_id):
        if char.stat_log.get("left") is not None:
            continue
        if char.guild in guilds:
            guild = guilds[char.guild]
            authed = CharData(guild=guild, owner=None, character=char, spc=char.is_spc)
            chars.append(authed)

    return UserCharData(guilds=list(guilds.values()), characters=chars)


@router.get("/characters/{oid}")
async def get_character(
    oid: PydanticObjectId,
    user_id: int = Depends(get_authenticated_user),
) -> CharData:
    """Fetch a character.

    Args:
      oid (PydanticObjectId): The ObjectId identifying the character

    What is returned depends on the user_id. If that user is identified as an
    admin on the guild to which the character belongs, OR if the user is the
    character's owner, return the full character.

    Otherwise, return a PublicCharacter.

    The CharData also contains guild and owner information. If the
    character is an SPC, then owner information is not returned."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up.")

    char = await char_mgr.fetchid(oid)
    if char is None:
        raise HTTPException(404, detail="Character not found")

    # Get cached guild (primary data source for web routes)
    guild = await guild_cache.fetchguild(char.guild)
    if guild is None:
        raise HTTPException(404, detail="Guild not found")

    # Verify user is a member
    cached_user = await guild_cache.fetchmember(char.guild, user_id)
    if cached_user is None:
        raise HTTPException(404, detail="User not in character's guild")

    # For admin check, need Discord member (has role data)
    discord_guild = inconnu.bot.get_guild(char.guild)
    discord_member = discord_guild.get_member(user_id) if discord_guild else None

    # Permission check (requires Discord member for role checking)
    if user_id == char.user or (discord_member and char_mgr.is_admin(discord_member)):
        character = char
    else:
        character = PublicCharacter.create(char)

    if char.is_spc:
        owner_data = None
    else:
        owner_data = await OwnerData.fetch(char.guild, char.user)

    return CharData(
        guild=CharacterGuild.create(guild),
        owner=owner_data,
        character=character,
        spc=char.is_spc,
    )


@router.get("/characters/guild/{guild_id}")
async def get_guild_characters(
    guild_id: int,
    user_id: int = Depends(get_authenticated_user),
) -> GuildChars:
    """Get all character base profiles belonging to the guild. Excludes
    characters whose owners have left the server."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up.")

    guild = await guild_cache.fetchguild(guild_id)
    if guild is None:
        raise HTTPException(404, detail="Guild not found")

    member = await guild_cache.fetchmember(guild_id, user_id)
    if member is None:
        raise HTTPException(403, detail="User does not belong to guild")

    char_guild = CharacterGuild.create(guild)
    profiles: list[CharData] = []
    for char in await char_mgr.fetchguild(guild_id):
        if char.stat_log.get("left") is not None:
            continue

        if char.is_spc:
            owner_data = None
        else:
            owner_data = await OwnerData.fetch(char.guild, char.user)
            if owner_data is None:
                # We couldn't find them; maybe Discord is throwing a fit.
                # Without owner data, however, we won't return this character.
                continue

        base_profile = PublicCharacter.create(char)
        guild_profile = CharData(
            guild=char_guild,
            owner=owner_data,
            character=base_profile,
            spc=char.is_spc,
        )
        profiles.append(guild_profile)

    return GuildChars(guild=char_guild, characters=profiles)


@router.get("/characters/profile/{oid}")
async def get_character_profile(
    oid: PydanticObjectId,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> CharData:
    """Fetch a character profile. This endpoint returns a non-sensitive character
    model with only name, ownership data, and public profile data."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up.")

    char = await char_mgr.fetchid(oid)
    if char is None:
        raise HTTPException(404, detail="Character not found.")

    guild = await CharacterGuild.fetch(char.guild)
    if char.is_spc:
        owner = None
    else:
        owner = await OwnerData.fetch(char.guild, char.user)

    return CharData(
        guild=guild,
        owner=owner,
        character=PublicCharacter.create(char),
        spc=char.is_spc,
    )


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
    wizard = wizard_cache.get(token)
    if wizard is None:
        raise HTTPException(404, detail="Unknown token. It may have expired.")
    # We need to sort the traits before setting them
    traits = sorted(data.traits, key=lambda t: t.name.casefold())
    owner_id = wizard.user if not wizard.spc else VChar.SPC_OWNER

    character = VChar(
        guild=int(wizard.guild.id),
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

    wizard_cache.delete(token)

    return CreationSuccess(
        guild=wizard.guild,
        character_id=character.id_str,
        character_name=character.name,
    )
