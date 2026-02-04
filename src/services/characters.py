"""vchar/manager.py - Character cache/in-memory database."""

import asyncio
import bisect
from datetime import UTC, datetime

import discord
from beanie import PydanticObjectId
from cachetools import TTLCache
from loguru import logger

import db
import errors
from bot import InconnuBot
from models.vchar import VChar
from utils.text import pluralize


class CharacterManager2:
    """A class for maintaining a local copy of characters."""

    def __init__(self):
        self._characters: list[VChar] = []
        self._id_cache: dict[str, VChar] = {}
        self.bot: InconnuBot | None = None
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Whether the bot has been initialized."""
        return self._initialized

    def _check_initialized(self):
        """Raises an exception if the manager hasn't been initialized or the
        bot is not set."""
        if not self.initialized:
            raise RuntimeError("The character manager has not been initialized!")
        if self.bot is None:
            raise RuntimeError("The character manager needs a bot instance to run.")

    async def initialize(self):
        """Load the characters from the database."""
        self._characters = await VChar.find_all().to_list()
        self._id_cache = {char.id_str: char for char in self._characters}
        self._initialized = True

        logger.info("Initialized with {} characters", len(self._characters))

    async def fetchall(self, guild: discord.Guild | int, user: discord.Member | int) -> list[VChar]:
        """Fetch all characters. Parameters given act as a filter."""
        self._check_initialized()

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
        self._check_initialized()

        if isinstance(name, VChar):
            # Short-circuit if we already have a VChar
            return name
        if name:
            # See if we have a character ID
            if char := self._id_cache.get(name):
                self._validate(guild, user, char)
                return char

        user_chars = await self.fetchall(guild, user)
        if not user_chars:
            raise errors.CharacterNotFoundError("You have no characters.")
        if len(user_chars) == 1:
            return user_chars[0]

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
            raise errors.UnspecifiedCharacterError(f"You have no character named `{name}`.")

    async def id_fetch(self, oid: PydanticObjectId | str) -> VChar | None:
        """Fetch the character by ID, if it exists."""
        self._check_initialized()

        return self._id_cache.get(str(oid))

    async def character_count(self, guild: discord.Guild | int, user: discord.Member | int) -> int:
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
        self._check_initialized()

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

        logger.info("Registered {} to {} on {}", character.name, character.user, character.guild)

    async def remove(self, character: VChar) -> bool:
        """Delete the character from the database and the cache."""
        self._check_initialized()

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
        self._check_initialized()

        character.user = new_owner.id
        await character.save()

        logger.info(
            "Transferred '{}' from {} to {} on {}",
            character.name,
            current_owner.name,
            new_owner.name,
            character.guild,
        )

    async def mark_inactive(self, player: discord.Member):
        """
        When a player leaves a guild, mark their characters as inactive. They
        will then be culled after 30 days if they haven't returned before then.
        """
        self._check_initialized()

        tasks = []
        for char in self._characters:
            if char.user == player.id:
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
        self._check_initialized()

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

    # No-ops for compatibility testing
    def sort_user(self, *_):
        pass

    def clear_caches(self):
        pass

    def _validate(self, guild: discord.Guild, user: discord.Member, char: VChar):
        """Validate character ownership."""
        if guild.id != char.guild:
            raise LookupError(f"**{char.name}** doesn't belong to this server!")
        if char.user != user:
            if not self._is_admin(user):
                raise LookupError(f"**{char.name}** doesn't belong to this user!")

    @staticmethod
    def _is_admin(user: discord.Member) -> bool:
        """Determine whether the user is an administrator."""
        return user.top_role.permissions.administrator or user.guild_permissions.administrator


class CharacterManager:
    """A class for maintaining a local copy of characters."""

    def __init__(self):
        logger.info("CHARACTER MANAGER: Initialized")
        max_size = 200
        ttl = 7200
        self.all_fetched: TTLCache[str, bool] = TTLCache(maxsize=max_size, ttl=ttl)
        self.user_cache: TTLCache[str, list[VChar]] = TTLCache(
            maxsize=max_size,
            ttl=ttl,
        )
        self.id_cache: TTLCache[str, VChar] = TTLCache(
            maxsize=max_size,
            ttl=ttl,
        )

        # Set after construction. Used to check whether a user is an admin
        self.bot = None
        self.collection = db.characters

    async def fetchone(
        self,
        guild: discord.Guild | int,
        user: discord.Member | int,
        name: str | VChar | None,
    ):
        """
        Fetch a single character.
        Args:
            guild: The Discord ID of the guild the bot was invoked in
            user: The user's Discord ID
            name (optional): The character's name or ID

        If the name isn't given, return the user's sole character, if applicable.
        """
        if isinstance(name, VChar):
            return name

        guild, user, _ = self._get_ids(guild, user)

        if name is not None:
            if char := self.id_cache.get(name[:24]):
                self._validate(guild, user, char)
                return char

            # Retrieve all of the user's characters on the guild, which also
            # populates the ID cache
            user_chars = await self.fetchall(guild, user)

            # We could check the ID cache again, but this is only a tiny bit
            # slower, so let's avoid code duplication
            for char in user_chars:
                # Post editing sends an ObjectId, so we need to check that, too
                if char.name.lower() == name.lower() or char.id_str == name:
                    self._validate(guild, user, char)
                    return char

            # The given name doesn't match any character ID or name
            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        # No character name given. If the user only has one character, then we
        # can just return it. Otherwise, send an error message.

        user_chars = await self.fetchall(guild, user)

        if (count := len(user_chars)) == 0:
            raise errors.NoCharactersError(
                "You have no characters. Create one with `/character create`."
            )
        if count == 1:
            return user_chars[0]

        # Two or more characters
        errmsg = f"You have {count} characters. Please specify which to use."
        raise errors.UnspecifiedCharacterError(errmsg)

    async def fetchall(self, guild: int, user: int):
        """
        Fetch all of a user's characters in a given guild. Adds them to the
        cache if necessary.
        """
        guild, user, key = self._get_ids(guild, user)

        if self.all_fetched.get(key, False):
            return self.user_cache.get(key, [])

        logger.info("CHARACTER MANAGER: Fetching {}'s characters on {} from the db", user, guild)

        characters = []
        async for character in VChar.find({"guild": guild, "user": user}):
            if character.id_str not in self.id_cache:
                bisect.insort(characters, character)
                self.id_cache[character.id_str] = character
            else:
                # Use the already cached character. This will probably never
                # happen, but we'll put it here just in case
                bisect.insort(characters, self.id_cache[character.id_str])

        self.user_cache[key] = characters
        self.all_fetched[key] = True

        logger.debug(
            "CHARACTER MANAGER: Found {} characters ({} on {})",
            len(characters),
            user,
            guild,
        )

        return characters

    async def id_fetch(self, oid: PydanticObjectId | str) -> VChar | None:
        """Fetch the character by ID, if it exists."""
        if str(oid) in self.id_cache:
            return self.id_cache[str(oid)]

        char = await VChar.get(str(oid))
        if char is not None:
            self.id_cache[str(oid)] = char
        return char

    async def character_count(self, guild: int, user: int) -> int:
        """Get a count of the user's characters in the server."""
        chars = await self.fetchall(guild, user)
        return len(chars)

    async def exists(self, guild: int, user: int, name: str, is_spc: bool) -> bool:
        """Determine whether a user already has a named character."""
        if self.bot is None:
            raise ValueError("Bot is not set!")

        if is_spc:
            owner_id = self.bot.user.id
            name += " (SPC)"
        else:
            owner_id = user
        user_chars = await self.fetchall(guild, owner_id)

        for character in user_chars:
            if character.name.lower() == name.lower():
                return True

        return False

    def clear_caches(self, player: discord.Member):
        """Clear the caches for the player + guild."""
        _, _, key = self._get_ids(player.guild, player)
        char_ids = {c.id_str for c in self.user_cache.get(key, [])}
        for char_id in char_ids:
            if char_id in self.id_cache:
                del self.id_cache[char_id]
        if key in self.user_cache:
            del self.user_cache[key]

        logger.debug("{}: Cleared {}'s caches", player.guild.name, player.name)

    async def register(self, character: VChar):
        """Add the character to the database and the cache."""
        # Check for duplicate character (same name, guild, and user)
        user_chars = await self.fetchall(character.guild, character.user)
        for existing_char in user_chars:
            if existing_char.name.casefold() == character.name.casefold():
                raise errors.DuplicateCharacterError(
                    f"Character '{character.name}' already exists for this user in this guild."
                )

        await character.save()
        self.id_cache[character.id_str] = character

        inserted = False

        # Keep the list sorted
        for index, char in enumerate(user_chars):
            if character.name.lower() < char.name.lower():
                user_chars.insert(index, character)
                inserted = True
                break

        if not inserted:
            user_chars.append(character)

        key = self._user_key(character)
        self.user_cache[key] = user_chars

        logger.info("Registered {} to {} on {}", character.name, character.user, character.guild)

    async def remove(self, character: VChar):
        """Remove a character from the database and the cache."""
        deletion = await character.delete()

        if deletion.deleted_count == 1:
            user_chars = await self.fetchall(character.guild, character.user)
            if character in user_chars:
                user_chars.remove(character)

            key = self._user_key(character)
            self.user_cache[key] = user_chars

            if character.id_str in self.id_cache:
                del self.id_cache[character.id_str]

            logger.info("CHARACTER MANAGER: Removed {}", character.name)

            return True

        logger.warning("CHARACTER MANAGER: Unable to remove {}", character.name)
        return False

    async def transfer(self, character, current_owner, new_owner):
        """Transfer one character to another."""
        # Remove it from the owner's cache
        current_chars = await self.fetchall(character.guild, current_owner)
        current_key = self._user_key(character)
        current_chars.remove(character)
        self.user_cache[current_key] = current_chars

        # Make the transfer
        character.user = new_owner.id
        await character.save()

        # Only add it to the new owner's cache if they've already loaded
        new_key = self._user_key(character)
        if (new_chars := self.user_cache.get(new_key)) is not None:
            inserted = False

            for index, char in enumerate(new_chars):
                if char > character:
                    new_chars.insert(index, character)
                    inserted = True
                    break

            if not inserted:
                new_chars.append(character)

            self.user_cache[new_key] = new_chars

        logger.info(
            "CHARACTER MANAGER: Transferred '{}' from {} to {}",
            character.name,
            current_owner.name,
            new_owner.name,
        )

    async def mark_inactive(self, player: discord.Member):
        """
        When a player leaves a guild, mark their characters as inactive. They
        will then be culled after 30 days if they haven't returned before then.
        """
        self.clear_caches(player)

        res = await self.collection.update_many(
            {"guild": player.guild.id, "user": player.id},
            {"$set": {"log.left": datetime.now(UTC)}},
        )
        if res.modified_count > 0:
            logger.info(
                "{}: {} left. Marked {} {} inactive.",
                player.guild.name,
                player.name,
                res.modified_count,
                pluralize(res.modified_count, "character"),
            )

    async def mark_active(self, player: discord.Member):
        """
        When a player returns to the guild, we mark their characters as active
        so long as they haven't already been culled.
        """
        # We don't need to clear the caches, since we already did that when we
        # marked them inactive.
        res = await self.collection.update_many(
            {"guild": player.guild.id, "user": player.id}, {"$unset": {"log.left": 1}}
        )
        if res.modified_count > 0:
            logger.info(
                "{}: {} re-joined. Cleared {} deletion {}.",
                player.guild.name,
                player.name,
                res.modified_count,
                pluralize(res.modified_count, "countdown"),
            )

    def sort_user(self, guild: int, user: int):
        """Sorts the user's characters alphabetically."""
        guild, user, key = self._get_ids(guild, user)

        if not (user_chars := self.user_cache.get(key)):
            # Characters are automatically sorted when fetched
            return

        user_chars.sort()
        self.user_cache[key] = user_chars

    # Private Methods

    @staticmethod
    def _get_ids(guild: discord.Guild | int, user: discord.Member | int):
        """Get the guild and user IDs."""
        if guild and not isinstance(guild, int):
            guild = guild.id
        if user and not isinstance(user, int):
            user = user.id

        key = f"{guild} {user}"

        return guild, user, key

    @staticmethod
    def _user_key(character: VChar):
        """Generate a key for the user cache."""
        return f"{character.guild} {character.user}"

    def _is_admin(self, guild: int, user: int):
        """Determine whether the user is an administrator."""
        if not self.bot:
            return False

        if isinstance(guild, int):
            guild = self.bot.get_guild(guild)
        if isinstance(user, int):
            user = guild.get_member(user)

        return user.top_role.permissions.administrator or user.guild_permissions.administrator

    def _validate(self, guild, user, char):
        """Validate that a character belongs to the user."""
        if guild and char.guild != guild:
            raise LookupError(f"**{char.name}** doesn't belong to this server!")
        if user and char.user != user:
            if not self._is_admin(guild, user):
                raise LookupError(f"**{char.name}** doesn't belong to this user!")


char_mgr = CharacterManager()
