"""Guild/Member caching for cold start recovery."""

import asyncio
import functools

import aiosqlite
import discord
from loguru import logger
from pydantic import BaseModel, Field

from config import settings
from utils.discord_helpers import get_avatar

# Seconds to wait for a single guild's member chunk before giving up. py-cord's
# chunk requests have no timeout of their own and can otherwise wait forever.
CHUNK_TIMEOUT = 60.0


class CachedMember(BaseModel):
    """A cached member object with minimal values. For use with web routes."""

    id: int
    name: str
    icon: str
    guild: "CachedGuild"


class CachedGuild(BaseModel):
    """A cached guild object with minimal values. For use with web routes."""

    id: int
    name: str
    icon: str | None
    members: list[CachedMember] = Field(default_factory=list)

    def get_member(self, id: int) -> CachedMember | None:
        """Get a member, if it exists."""
        try:
            return next(m for m in self.members if m.id == id)
        except StopIteration:
            return None


def validate(func):
    """Decorator for asserting that the GuildCache is ready."""

    @functools.wraps(func)
    async def wrapper(gc: "GuildCache", *args, **kwargs):
        if not gc.initialized:
            raise RuntimeError("Guild cache has not been initialized.")
        return await func(gc, *args, **kwargs)

    return wrapper


class GuildCache:
    """SQLite-backed cache of Guilds and Members."""

    def __init__(self, loc: str):
        self.location = loc
        self._initialized = False
        self._refreshed = False

    @property
    def initialized(self) -> bool:
        """Whether the cache has been initialized."""
        return self._initialized

    async def ready(self) -> bool:
        """Check if the cache is populated."""
        if not self.initialized:
            return False
        if self._refreshed:
            return True
        async with self.db.execute("SELECT COUNT(*) AS count FROM members") as cur:
            row = await cur.fetchone()
            if row is None:
                return False

            # The bot is always on at least one guild, so if there are no
            # members, then the cache is definitely not initialized.
            return row["count"] > 0

    async def initialize(self):
        """Initialize the database and create tables if necessary."""
        if self.initialized:
            logger.warning("Guild cache already initialized! ({})", self.location)
            return

        self.db = await aiosqlite.connect(self.location)
        self.db.row_factory = aiosqlite.Row

        await self.db.execute("PRAGMA foreign_keys = ON")
        await self.db.execute(
            """
                CREATE TABLE IF NOT EXISTS guilds (
                    id INTEGER,
                    name TEXT,
                    icon TEXT
                )
            """
        )
        await self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guild_id ON guilds (id)")
        await self.db.execute(
            """
                CREATE TABLE IF NOT EXISTS members (
                    guild INTEGER,
                    id INTEGER,
                    name TEXT,
                    icon TEXT,
                    FOREIGN KEY (guild) REFERENCES guilds (id) ON DELETE CASCADE
                )
            """
        )
        await self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_member_id ON members (guild, id)"
        )

        await self.db.commit()
        self._initialized = True
        logger.info("Guild cache initialized at {}", self.location)

    async def close(self):
        """Close the database."""
        await self.db.close()
        self._initialized = False
        self._refreshed = False
        logger.info("Guild cache closed ({})", self.location)

    @validate
    async def upsert_guilds(self, guilds: discord.Guild | list[discord.Guild]):
        """Upsert a Discord guild."""
        if isinstance(guilds, discord.Guild):
            guilds = [guilds]

        await self._chunk(guilds)
        await self._write_guilds(guilds)
        await self.db.commit()

    async def _chunk(self, guilds: list[discord.Guild]):
        """Ensure the guilds' member caches are populated. Guilds that time out
        are logged and left with whatever members are already cached."""
        for guild in guilds:
            if guild.chunked:
                continue
            try:
                await asyncio.wait_for(guild.chunk(), timeout=CHUNK_TIMEOUT)
            except TimeoutError:
                logger.warning(
                    "Guild cache: timed out chunking {} ({}); caching {}/{} members",
                    guild.name,
                    guild.id,
                    len(guild.members),
                    guild.member_count,
                )

    async def _write_guilds(self, guilds: list[discord.Guild]):
        """Write guilds and their members without committing."""
        data = [(g.id, g.name, g.icon.url if g.icon else None) for g in guilds]
        await self.db.executemany(
            """
                INSERT INTO guilds VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET 
                name = excluded.name,
                icon = excluded.icon
            """,
            data,
        )
        await self._write_members([m for g in guilds for m in g.members])

    @validate
    async def delete_guild(self, guild: discord.Guild):
        """Delete a guild."""
        await self.db.execute("DELETE FROM guilds WHERE id=?", (guild.id,))
        await self.db.commit()

    @validate
    async def fetchguild(self, guild_id: int, members=True) -> CachedGuild | None:
        """Fetch a guild."""
        async with self.db.execute("SELECT * FROM guilds WHERE id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if row is None:
                return None

            guild = CachedGuild.model_validate(dict(row))
            if members:
                guild.members = await self.fetchmembers(guild.id)
            return guild

    @validate
    async def fetchguilds(self, user_id: int) -> list[CachedGuild]:
        """Fetch the guilds a specific user belongs to, with members populated."""
        guilds: dict[int, CachedGuild] = {}

        query = (
            "SELECT "
            "g.id AS guild_id, g.name AS guild_name, g.icon AS guild_icon, "
            "m.id AS member_id, m.name AS member_name, m.icon AS member_icon "
            "FROM guilds g "
            "JOIN members m ON g.id = m.guild "
            "WHERE g.id IN (SELECT guild FROM members WHERE id = ?)"
        )
        async with self.db.execute(query, (user_id,)) as cur:
            async for row in cur:
                gid = row["guild_id"]
                if gid not in guilds:
                    guilds[gid] = CachedGuild(
                        id=gid, name=row["guild_name"], icon=row["guild_icon"]
                    )
                guild = guilds[gid]
                member = CachedMember(
                    id=row["member_id"],
                    name=row["member_name"],
                    icon=row["member_icon"],
                    guild=guild,
                )
                guild.members.append(member)

        return list(guilds.values())

    @validate
    async def upsert_members(self, members: discord.Member | list[discord.Member]):
        """Upsert guild members."""
        if isinstance(members, discord.Member):
            members = [members]
        if not members:
            return

        await self._write_members(members)
        await self.db.commit()

    async def _write_members(self, members: list[discord.Member]):
        """Write members without committing."""
        data = [(m.guild.id, m.id, m.display_name, get_avatar(m).url) for m in members]
        await self.db.executemany(
            """
                INSERT INTO members VALUES (?, ?, ?, ?)
                ON CONFLICT (guild, id) DO UPDATE SET
                name = excluded.name,
                icon = excluded.icon
            """,
            data,
        )

    @validate
    async def delete_member(self, member: discord.Member):
        """Delete a member if it exists."""
        await self.db.execute(
            "DELETE FROM members WHERE guild=? AND id=?", (member.guild.id, member.id)
        )
        await self.db.commit()

    @validate
    async def fetchmember(self, guild_id: int, member_id: int) -> CachedMember | None:
        """Fetch a cached member."""
        cguild = await self.fetchguild(guild_id)
        if cguild is None:
            return None

        async with self.db.execute(
            "SELECT * FROM members WHERE guild=? AND id=?", (guild_id, member_id)
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                return None

            data = dict(row)
            data["guild"] = cguild
            return CachedMember.model_validate(data)

    @validate
    async def fetchmembers(self, guild: int | CachedGuild | discord.Guild) -> list[CachedMember]:
        """Fetch a cached member."""
        guild_id = guild if isinstance(guild, int) else guild.id
        if isinstance(guild, CachedGuild):
            cguild = guild
        else:
            cguild = await self.fetchguild(guild_id, members=False)
            if cguild is None:
                return []

        async with self.db.execute("SELECT * FROM members WHERE guild=?", (guild_id,)) as cur:
            members = []
            async for row in cur:
                data = dict(row)
                data["guild"] = cguild
                members.append(CachedMember.model_validate(data))

            return members

    @validate
    async def refresh(self, guilds: list[discord.Guild]):
        """Clear all data and insert new guilds. For use in bot on_ready()."""
        # Chunk before touching the database, so the wipe and rewrite happen
        # in one short transaction and the old data stays readable meanwhile.
        await self._chunk(guilds)
        try:
            await self.db.execute("DELETE FROM guilds")
            await self._write_guilds(guilds)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        logger.info("Guild cache {} refreshed!", self.location)
        self._refreshed = True


guild_cache = GuildCache(settings.guild_cache_loc)
