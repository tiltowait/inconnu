"""vchar/manager.py - Character cache/in-memory database."""

import asyncio
import bisect
from datetime import UTC, datetime

import discord
from beanie import PydanticObjectId
from bson import ObjectId
from loguru import logger

import errors
from models.vchar import VChar
from utils.text import pluralize


class CharacterManager:
    """A class for maintaining a local copy of characters."""

    def __init__(self):
        self._characters: list[VChar] = []
        self._id_cache: dict[str, VChar] = {}
        self._initialized = False
        self._lock = asyncio.Lock()

    @property
    def initialized(self) -> bool:
        """Whether the bot has been initialized."""
        return self._initialized

    async def initialize(self):
        """Load the characters from the database."""
        if not self._initialized:
            self._characters = await VChar.find_all().to_list()
            self._characters.sort()
            self._id_cache = {char.id_str: char for char in self._characters}
            self._initialized = True

            logger.info("Initialized with {} characters", len(self._characters))

    async def fetchall(self, guild: discord.Guild | int, user: discord.Member | int) -> list[VChar]:
        """Fetch all characters. Parameters given act as a filter."""
        await self.initialize()

        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        user_id = user.id if isinstance(user, discord.Member) else user

        return [
            char for char in self._characters if char.guild == guild_id and char.user == user_id
        ]

    async def fetchone(
        self,
        guild: discord.Guild,
        user: discord.Member,
        name: str | VChar | None,
    ) -> VChar:
        """Attempt to return a single character.

        Args:
            guild: The guild to which the character belongs.
            user: The character's owner.
            name (optional): The character's name, or a VChar object.

        Returns a single character, if a single match is found.

        Raises:
            CharacterNotFoundError if no character matches the name.
            UnspecifiedCharacterError if more than one match is found.
        """
        await self.initialize()

        if isinstance(name, VChar):
            # Short-circuit if we already have a VChar
            return name
        if isinstance(name, str):
            name = name.strip()

        if name and ObjectId.is_valid(name):
            if char := self._id_cache.get(name):
                self._validate(guild, user, char)
                return char

        user_chars = await self.fetchall(guild, user)
        if not user_chars:
            raise errors.CharacterNotFoundError("You have no characters.")
        if len(user_chars) == 1:
            if not name:
                return user_chars[0]
            if user_chars[0].name.casefold() == name.casefold():
                return user_chars[0]
            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        # More than one found. Attempt to filter down.
        if name is None:
            raise errors.UnspecifiedCharacterError(
                f"You have {len(user_chars)} characters. Please specify which to use."
            )

        try:
            char = next(char for char in user_chars if char.name.casefold() == name.casefold())
            self._validate(guild, user, char)
            return char
        except StopIteration:
            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

    async def id_fetch(self, oid: PydanticObjectId | str) -> VChar | None:
        """Fetch the character by ID, if it exists."""
        await self.initialize()
        return self._id_cache.get(str(oid))

    async def character_count(self, guild: discord.Guild, user: discord.Member) -> int:
        """Get a count of the user's characters in the server."""
        chars = await self.fetchall(guild, user)
        return len(chars)

    async def exists(
        self,
        guild: discord.Guild,
        user: discord.Member,
        name: str,
        is_spc: bool,
    ) -> bool:
        """Determine whether a user already has a named character."""
        await self.initialize()

        if is_spc:
            owner_id = VChar.SPC_OWNER
        else:
            owner_id = user.id

        for character in await self.fetchall(guild, owner_id):
            if character.name.casefold() == name.casefold():
                return True

        return False

    async def register(self, character: VChar):
        """Insert the character into the database and the cache."""
        await self.initialize()

        # Acquire global lock to prevent race conditions on shared data structures
        async with self._lock:
            try:
                duplicate = next(
                    char
                    for char in self._characters
                    if char.user == character.user
                    and char.guild == character.guild
                    and char.name.casefold() == character.name.casefold()
                )
                raise errors.DuplicateCharacterError(
                    f"Character '{duplicate.name}' already exists for this user in this guild."
                )
            except StopIteration:
                # No duplicate found
                pass

            await character.save()
            self._id_cache[character.id_str] = character
            bisect.insort(self._characters, character)

            logger.info(
                "Registered {} to {} on {}", character.name, character.user, character.guild
            )

    async def remove(self, character: VChar) -> bool:
        """Delete the character from the database and the cache."""
        await self.initialize()

        # Acquire global lock to prevent race conditions on shared data structures
        async with self._lock:
            deletion = await character.delete()

            if deletion.deleted_count == 1:
                self._characters.remove(character)
                del self._id_cache[character.id_str]

                logger.info("Removed {} from {}", character.name, character.guild)
                return True

            logger.warning("Unable to remove {} from {}", character.name, character.guild)
            return False

    async def transfer(
        self, character: VChar, current_owner: discord.Member, new_owner: discord.Member
    ):
        """Transfer character ownership."""
        await self.initialize()

        if character.user != current_owner.id:
            raise errors.WrongOwner(f"{current_owner.display_name} does not own {character.name}!")
        if character.guild != new_owner.guild.id:
            raise errors.WrongGuild(
                f"{new_owner.display_name} is not in the same server as {character.name}!"
            )

        character.user = new_owner.id
        await character.save()

        logger.info(
            "Transferred '{}' from {} to {} on {}",
            character.name,
            current_owner.name,
            new_owner.name,
            new_owner.guild.name,
        )

    async def mark_inactive(self, player: discord.Member):
        """
        When a player leaves a guild, mark their characters as inactive. They
        will then be culled after 30 days if they haven't returned before then.
        """
        await self.initialize()

        tasks = []
        for char in self._characters:
            if char.user == player.id and char.guild == player.guild.id:
                char.stat_log["left"] = datetime.now(UTC)
                tasks.append(char.save())

        if tasks:
            logger.info(
                "{}: {} left. Marked {} {} inactive.",
                player.guild.name,
                player.name,
                len(tasks),
                pluralize(len(tasks), "character"),
            )
            await asyncio.gather(*tasks)

    async def mark_active(self, player: discord.Member):
        """
        When a player returns to the guild, we mark their characters as active
        so long as they haven't already been culled.
        """
        await self.initialize()

        tasks = []
        for char in self._characters:
            if char.user == player.id and "left" in char.stat_log:
                del char.stat_log["left"]
                tasks.append(char.save())

        if tasks:
            logger.info(
                "{}: {} left. Marked {} {} active.",
                player.guild.name,
                player.name,
                len(tasks),
                pluralize(len(tasks), "character"),
            )
            await asyncio.gather(*tasks)

    async def sort_chars(self):
        """Sort characters after a rename."""
        async with self._lock:
            self._characters.sort()

    def _validate(self, guild: discord.Guild, user: discord.Member, char: VChar):
        """Validate character ownership."""
        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        user_id = user.id if isinstance(user, discord.Member) else user

        if guild_id != char.guild:
            raise LookupError(f"**{char.name}** doesn't belong to this server!")
        if char.user != user_id:
            if not self._is_admin(user):
                raise LookupError(f"**{char.name}** doesn't belong to this user!")

    @staticmethod
    def _is_admin(user: discord.Member) -> bool:
        """Determine whether the user is an administrator."""
        return user.top_role.permissions.administrator or user.guild_permissions.administrator


char_mgr = CharacterManager()
