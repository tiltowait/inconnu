"""Character API routes."""

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated

import discord
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Response
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import StreamingResponse
from loguru import logger

import errors
from config import settings
from constants import ROUSE_FAIL_COLOR, Damage
from events import CharEventType, char_events
from inconnu.misc.aggheal import aggheal_update_message, heal_aggravated
from inconnu.misc.mend import mend_superficial, mend_update_message
from inconnu.misc.rouse import roll_rouse_checks, rouse_update_message
from models import VChar, VGuild
from models.vchar import Tracker
from models.vguild import VGuildSettings
from routes.auth import get_authenticated_user, verify_api_key
from routes.characters.edit import apply_edit, check_edit, edit_summary, summarize
from routes.characters.models import (
    CharData,
    CreationBody,
    CreationSuccess,
    DamageBody,
    EditBody,
    GuildChars,
    MendBody,
    MendResult,
    OwnerData,
    PublicCharacter,
    RouseBody,
    RouseResult,
    UserCharData,
    WizardSchema,
)
from routes.deps import get_bot
from services import char_mgr, guild_cache, send_update, wizard_cache
from services.guildcache import CachedGuild
from services.wizard import CharacterGuild
from utils.permissions import has_supporter_role, is_storyteller

if TYPE_CHECKING:
    from bot import InconnuBot

HEARTBEAT_SECONDS = 15.0

router = APIRouter()


# Getters


@router.get("/characters")
async def get_character_list(
    user_id: int = Depends(get_authenticated_user),
) -> UserCharData:
    """Get all of the user's characters and the guilds they belong to."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up")

    user_guilds = await guild_cache.fetchguilds(user_id)

    guilds = {}
    for guild in user_guilds:
        char_count = await char_mgr.countguild(guild.id)
        guilds[guild.id] = CharacterGuild.create(guild, char_count)

    chars = []
    for char in await char_mgr.fetchuser(user_id):
        if char.log.left is not None:
            continue
        if char.guild in guilds:
            guild = guilds[char.guild]
            authed = CharData(guild=guild, owner=None, character=char, spc=char.is_spc)
            chars.append(authed)

    return UserCharData(guilds=list(guilds.values()), characters=chars)


async def _fetch_guild_character(oid: PydanticObjectId, user_id: int) -> tuple[VChar, CachedGuild]:
    """Fetch a character and its cached guild, if the user is in that guild.
    Raises HTTPException if the bot is starting up, if the character or guild
    doesn't exist, or if the user isn't in the guild."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up")

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

    return char, guild


@router.get("/characters/{oid}")
async def get_character(
    oid: PydanticObjectId,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    user_id: int = Depends(get_authenticated_user),
) -> CharData:
    """Fetch a character.

    Args:
      oid (PydanticObjectId): The ObjectId identifying the character

    What is returned depends on the user_id. If that user is a Storyteller on
    the guild to which the character belongs, OR if the user is the character's
    owner, return the full character.

    Otherwise, return a PublicCharacter.

    The CharData also contains guild and owner information. If the
    character is an SPC, then owner information is not returned."""
    char, guild = await _fetch_guild_character(oid, user_id)

    # For the Storyteller check, need Discord member (has role data)
    discord_guild = bot.get_guild(char.guild)
    discord_member = discord_guild.get_member(user_id) if discord_guild else None

    # Permission check (requires Discord member for role checking)
    if user_id == char.user or await is_storyteller(discord_member):
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


async def _fetch_editable_character(
    oid: PydanticObjectId, user_id: int, bot: InconnuBot, players=True
) -> tuple[VChar, discord.Guild | None]:
    """Fetch a character the user may change, and its Discord guild, if the
    bot has it: the owner always may, and Storytellers may change SPCs, and
    players' characters if players is True. Raises 403 otherwise, and as
    _fetch_guild_character() does."""
    char, _ = await _fetch_guild_character(oid, user_id)

    discord_guild = bot.get_guild(char.guild)
    discord_member = discord_guild.get_member(user_id) if discord_guild else None
    if user_id != char.user:
        if not (players or char.is_spc):
            raise HTTPException(403, detail="Only the owner may do this")
        if not await is_storyteller(discord_member):
            raise HTTPException(
                403, detail="Only the owner or a Storyteller may change this character"
            )

    return char, discord_guild


async def _save(char: VChar):
    """Save the character, undoing its changes if the save fails, since the
    character manager holds this same object."""
    try:
        await char.save_changes()
    except Exception:
        char.rollback()
        raise


async def _post_update(
    discord_guild: discord.Guild | None,
    char: VChar,
    user_id: int,
    *,
    title: str,
    description: str,
    color: int | None = None,
):
    """Post a web change to the guild's update channel. The guild cache,
    unlike the gateway's, is sure to have the user: it vouched for them. The
    change is already saved, so a failed post is only logged."""
    editor = await guild_cache.fetchmember(char.guild, user_id)
    if discord_guild is None or editor is None:
        return

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name=char.name, icon_url=editor.icon)
    try:
        await send_update(discord_guild, embed)
    except discord.HTTPException as err:
        logger.warning("Couldn't post {}'s web update: {}", char.name, err)


@router.patch("/characters/{oid}", status_code=204)
async def edit_character(
    oid: PydanticObjectId,
    body: EditBody,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    user_id: int = Depends(get_authenticated_user),
) -> Response:
    """Save the web app's edits: every editable field, at once. Only the
    owner and Storytellers may edit. Edits are corrections, so they don't
    touch the Chronicle log or experience, but they are posted to the
    update channel. Other tabs refresh through the "changed" event."""
    char, discord_guild = await _fetch_editable_character(oid, user_id, bot)
    await check_edit(char, body)

    old = char.model_copy(deep=True)
    apply_edit(char, body)
    await _save(char)

    if char.raw_name != old.raw_name:
        # After the save, so a failed one can't leave the list misordered
        await char_mgr.sort_chars()

    if changes := summarize(old, char):
        await _post_update(
            discord_guild,
            char,
            user_id,
            title="Character Updated",
            description=edit_summary(char, user_id, changes),
        )

    return Response(status_code=204)


@router.post("/characters/{oid}/rouse")
async def rouse_character(
    oid: PydanticObjectId,
    body: RouseBody,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    user_id: int = Depends(get_authenticated_user),
) -> RouseResult:
    """Make Rouse checks, as /rouse does: Hunger rises on failures, the
    checks are logged, and Oblivion Stains are applied if asked for. Ghouls take one Aggravated Health damage instead, and
    mortals can't Rouse. As in Discord, only the owner may Rouse, though
    Storytellers may Rouse SPCs."""
    char, discord_guild = await _fetch_editable_character(oid, user_id, bot, players=False)

    if char.is_ghoul:
        char.set_aggravated_hp(char.aggravated_hp + 1)
        await _save(char)
        return RouseResult(
            successes=0, failures=0, hunger=0, frenzy=False, aggravated=1, stains=0, degeneration=0
        )

    if not char.is_vampire:
        raise RequestValidationError(
            [{"loc": ("body",), "msg": f"{char.name} is a mortal.", "type": "value_error"}]
        )

    if body.oblivion_stains:
        # By ID, so it works without the gateway's guild
        vguild = await VGuild.find_one(VGuild.guild == char.guild)
        faces = (vguild.settings if vguild else VGuildSettings()).oblivion_stains
    else:
        faces = []

    outcome = roll_rouse_checks(char, body.count, body.reroll, faces)
    degeneration = char.add_stains(outcome.stains, log=True) if outcome.stains else 0
    await _save(char)
    await _post_update(
        discord_guild,
        char,
        user_id,
        title="Rouse Check",
        description=rouse_update_message(char, outcome),
        color=ROUSE_FAIL_COLOR if char.hunger >= 4 else None,
    )

    return RouseResult(
        successes=outcome.successes,
        failures=outcome.failures,
        hunger=char.hunger,
        frenzy=outcome.frenzy,
        aggravated=0,
        stains=outcome.stains,
        degeneration=degeneration,
    )


@router.post("/characters/{oid}/damage", status_code=204)
async def damage_character(
    oid: PydanticObjectId,
    body: DamageBody,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    user_id: int = Depends(get_authenticated_user),
) -> Response:
    """Deal Superficial, then Aggravated, damage to a track, as /character
    update does: Superficial damage past the track's end wraps into
    Aggravated. The damage is logged. As in Discord, Storytellers may damage
    players' characters."""
    char, discord_guild = await _fetch_editable_character(oid, user_id, bot)
    track_name = body.track.title()

    lines: list[str] = []
    if body.superficial:
        aggravated = getattr(char, body.track).count(Damage.AGGRAVATED)
        char.apply_damage(body.track, Damage.SUPERFICIAL, body.superficial)
        line = f"`+{body.superficial}` Superficial {track_name} damage."
        if wrapped := getattr(char, body.track).count(Damage.AGGRAVATED) - aggravated:
            line += f" `{wrapped}` wrapped to Aggravated."
        lines.append(line)
    if body.aggravated:
        char.apply_damage(body.track, Damage.AGGRAVATED, body.aggravated)
        lines.append(f"`+{body.aggravated}` Aggravated {track_name} damage.")

    await _save(char)
    summary = "\n".join(f"* {line}" for line in lines)
    await _post_update(
        discord_guild,
        char,
        user_id,
        title="Damage Taken",
        description=f"__<@{user_id}> damaged {char.name} on the web:__\n{summary}",
    )

    return Response(status_code=204)


def _heal_willpower(char: VChar, severity: Damage) -> int:
    """Heal Superficial Willpower (as much as /awaken would) or one
    Aggravated, returning the amount healed."""
    if severity == Damage.SUPERFICIAL:
        healed = min(char.superficial_wp, char.willpower_recovery)
    else:
        healed = 1
    char.apply_damage(Tracker.WILLPOWER, severity, -healed)
    return healed


@router.post("/characters/{oid}/mend")
async def mend_character(
    oid: PydanticObjectId,
    body: MendBody,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    user_id: int = Depends(get_authenticated_user),
) -> MendResult:
    """Heal damage. Health heals as /mend (Superficial) and /aggheal
    (Aggravated) do, Rouse Checks and logging included. Willpower recovers
    what /awaken would (Superficial) or one Aggravated, with no Rouse Checks
    or logging. As in Discord, only the owner may heal, though Storytellers
    may heal SPCs."""
    char, discord_guild = await _fetch_editable_character(oid, user_id, bot, players=False)

    severity = Damage.SUPERFICIAL if body.type == "superficial" else Damage.AGGRAVATED
    track: str = getattr(char, body.track)
    if severity not in track:
        message = f"{char.name} has no {body.type.title()} {body.track.title()} damage to heal."
        raise RequestValidationError(
            [{"loc": ("body", "type"), "msg": message, "type": "value_error"}]
        )

    if body.track == Tracker.WILLPOWER:
        healed = _heal_willpower(char, severity)
        await _save(char)
        remaining = char.willpower.count(severity)
        await _post_update(
            discord_guild,
            char,
            user_id,
            title="Willpower Recovered",
            description=(
                f"Recovered `{healed}` {body.type.title()} Willpower damage.\n"
                f"`{remaining}` remaining."
            ),
        )
        return MendResult(
            track=char.willpower, dice=[], hunger=char.hunger, frenzy=False, torpor=False
        )

    if severity == Damage.SUPERFICIAL:
        mended = mend_superficial(char)
        await _save(char)
        await _post_update(
            discord_guild,
            char,
            user_id,
            title="Damage Mended",
            description=mend_update_message(char, mended),
        )
        dice, frenzy, torpor = mended.dice, mended.frenzy, False
    else:
        healed = heal_aggravated(char)
        await _save(char)
        await _post_update(
            discord_guild,
            char,
            user_id,
            title="Aggravated Damage Healed",
            description=aggheal_update_message(char, healed),
        )
        dice, frenzy, torpor = healed.dice, False, healed.torpor

    return MendResult(
        track=getattr(char, body.track),
        dice=dice,
        hunger=char.hunger,
        frenzy=frenzy,
        torpor=torpor,
    )


@router.get("/characters/{oid}/events")
async def get_character_events(
    oid: PydanticObjectId,
    user_id: int = Depends(get_authenticated_user),
) -> StreamingResponse:
    """Stream Server-Sent Events whenever the character changes. Events carry
    no data beyond "changed" or "deleted", so membership in the character's
    guild is enough; the app refetches the character, which checks access."""
    char, _ = await _fetch_guild_character(oid, user_id)
    return StreamingResponse(
        char_event_stream(char.id_str),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


async def char_event_stream(oid: str, heartbeat=HEARTBEAT_SECONDS) -> AsyncGenerator[str]:
    """Yield a character's events as SSE messages, until it's deleted. Pings
    during quiet spells, because a dead connection only shows up when a write
    fails. At shutdown, the stream ends without a message, and the client
    reconnects once the bot is back."""
    async with char_events.subscribe(oid) as queue:
        yield "retry: 5000\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), heartbeat)
            except TimeoutError:
                yield ": ping\n\n"
                continue
            if event == CharEventType.CLOSED:
                return
            yield f"data: {event}\n\n"
            if event == CharEventType.DELETED:
                return


@router.get("/characters/guild/{guild_id}")
async def get_guild_characters(
    guild_id: int,
    user_id: int = Depends(get_authenticated_user),
) -> GuildChars:
    """Get all character base profiles belonging to the guild. Excludes
    characters whose owners have left the server."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up")

    guild = await guild_cache.fetchguild(guild_id)
    if guild is None:
        raise HTTPException(404, detail="Guild not found")

    member = await guild_cache.fetchmember(guild_id, user_id)
    if member is None:
        raise HTTPException(403, detail="User does not belong to guild")

    chars = [c for c in await char_mgr.fetchguild(guild_id) if c.log.left is None]
    owner_ids = {c.user for c in chars if not c.is_spc}
    owners = {m.id: m for m in await guild_cache.fetchmembers(guild, ids=owner_ids)}

    char_guild = CharacterGuild.create(guild)
    profiles: list[CharData] = []
    for char in chars:
        if char.is_spc:
            owner_data = None
        else:
            owner = owners.get(char.user)
            if owner is None:
                # We couldn't find them; maybe Discord is throwing a fit.
                # Without owner data, however, we won't return this character.
                continue
            owner_data = OwnerData.from_user(owner)

        base_profile = PublicCharacter.create(char)
        guild_profile = CharData(
            guild=char_guild,
            owner=owner_data,
            character=base_profile,
            spc=char.is_spc,
        )
        profiles.append(guild_profile)

    return GuildChars(guild=char_guild, characters=profiles)


@router.get("/characters/profile/{oid}", dependencies=[Depends(verify_api_key)])
async def get_character_profile(oid: PydanticObjectId) -> CharData:
    """Fetch a character profile. This endpoint returns a non-sensitive character
    model with only name, ownership data, and public profile data."""
    if not await guild_cache.ready():
        raise HTTPException(503, detail="Bot is still starting up")

    char = await char_mgr.fetchid(oid)
    if char is None:
        raise HTTPException(404, detail="Character not found")

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


@router.get("/characters/wizard/{token}", dependencies=[Depends(verify_api_key)])
async def get_wizard(token: str) -> WizardSchema:
    """Get the character wizard schema."""
    wizard = wizard_cache.get(token)
    if wizard is None:
        raise HTTPException(404, detail="Unknown token. It may have expired.")

    return WizardSchema(
        spc=wizard.spc,
        guild=wizard.guild,
    )


@router.post("/characters/wizard/{token}", status_code=201, dependencies=[Depends(verify_api_key)])
async def create_character(
    token: str, data: CreationBody, bot: Annotated[InconnuBot, Depends(get_bot)]
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

    # Figure out if the user has premium
    has_premium = False
    guild = await bot.get_or_fetch_guild(settings.supporter_guild)
    if guild is not None:
        user = await guild.get_or_fetch(discord.Member, wizard.user)
        has_premium = user is not None and has_supporter_role(user)
    else:
        logger.warning("Supporter guild not found")

    return CreationSuccess(
        guild=wizard.guild,
        character_id=character.id_str,
        character_name=character.name,
        has_premium=has_premium,
    )
