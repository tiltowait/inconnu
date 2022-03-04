"""vchar/manager.py - Character cache/in-memory database."""

import datetime
import re

from bson.objectid import ObjectId

import inconnu
from . import errors
from .vchar import VChar
from ..constants import INCONNU_ID


class CharacterManager:
    """A class for maintaining a local copy of characters."""

    def __init__(self):
        self.all_fetched = {} # [user_id: bool]
        self.user_cache = {} # [guild: [user: [VChar]]]
        self.id_cache = {} # [char_id: VChar]


    @property
    def collection(self):
        """Get the database's characters collection."""
        return inconnu.db.characters


    @staticmethod
    def get_ids(guild, user):
        """Get the guild and user IDs."""
        if guild and not isinstance(guild, int):
            guild = guild.id
        if user and not isinstance(user, int):
            user = user.id

        return guild, user


    @staticmethod
    def user_key(character):
        """Generate a key for the user cache."""
        return f"{character.guild} {character.user}"


    @staticmethod
    def _validate(guild, user, char):
        """Validate that a character belongs to the user."""
        if guild and char.guild != guild:
            raise ValueError(f"**{char.name}** doesn't belong to this server!")
        if user and char.user != user:
            raise ValueError(f"**{char.name}** doesn't belong to this user!")


    async def _id_fetch(self, charid):
        """Attempt to fetch a character by ID."""
        if re.search(r"\d", charid):
            if (char_params := await self.collection.find_one({ "_id": ObjectId(charid) })):
                return VChar(char_params)

            # Character names can't contain numbers
            raise errors.CharacterNotFoundError(f"`{charid}` is not a valid character name.")

        return None


    async def fetchone(self, guild: int, user: int, name: str):
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

        guild, user = self.get_ids(guild, user)

        if name is not None:
            if (char := self.id_cache.get(name)):
                self._validate(guild, user, char)
                return char

            # Attempt to pull from the user cache
            user_chars = await self.fetchall(guild, user)
            for char in user_chars:
                if char.name.lower() == name.lower():
                    return char

            # Attempt to pull from the database
            if (char := await self._id_fetch(name)):
                self.id_cache[char.id] = char
                self._validate(guild, user, char)
                return char

            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        # No character name given. If the user only has one character, then we
        # can just return it. Otherwise, send an error message.

        user_chars = await self.fetchall(guild, user)

        if (count := len(user_chars)) == 0:
            raise errors.NoCharactersError("You have no characters.")
        if count == 1:
            return user_chars[0]

        # Two or more characters
        errmsg = f"You have {count} characters. Please specify which you want."
        raise errors.UnspecifiedCharacterError(errmsg)


    async def fetchall(self, guild: int, user: int):
        """
        Fetch all of a user's characters in a given guild. Adds them to the
        cache if necessary.
        """
        guild, user = self.get_ids(guild, user)
        key = f"{guild} {user}"

        if self.all_fetched.get(key, False):
            return self.user_cache.get(key, [])

        # Need to build the cache
        cursor = self.collection.find({ "guild": guild, "user": user })
        cursor.collation({ "locale": "en", "strength": 2 }).sort("name")

        characters = []
        async for char_params in cursor:
            character = VChar(char_params)
            characters.append(character)

            if character.id not in self.id_cache:
                self.id_cache[character.id] = character

        self.user_cache[key] = characters
        self.all_fetched[key] = True

        return characters


    async def exists(self, guild: int, user: int, name: str, is_spc: bool) -> bool:
        """Determine whether a user already has a named character."""
        user_chars = await self.fetchall(guild, user if not is_spc else INCONNU_ID)

        for character in user_chars:
            if character.name.lower() == name.lower():
                return True

        return False


    async def register(self, character):
        """Add the character to the database and the cache."""
        self.id_cache[character.id] = character

        user_chars = await self.fetchall(character.guild, character.user)
        inserted = False

        # Keep the list sorted
        for index, char in enumerate(user_chars):
            if character.name.lower() < char.name.lower():
                user_chars.insert(index, character)
                inserted = True
                break

        if not inserted:
            user_chars.append(character)

        key = self.user_key(character)
        self.user_cache[key] = user_chars

        await self.collection.insert_one(character.raw)


    async def remove(self, character):
        """Remove a character from the database and the cache."""
        deletion = await self.collection.delete_one(character.find_query)

        if deletion.deleted_count == 1:
            user_chars = await self.fetchall(character.guild, character.user)
            if character in user_chars:
                user_chars.remove(character)

            key = self.user_key(character)
            self.user_cache[key] = user_chars

            if character.id in self.id_cache:
                del self.id_cache[character.id]

            return True

        return False


    async def transfer(self, character, current_owner, new_owner):
        """Transfer one character to another."""
        # Remove it from the owner's cache
        current_chars = await self.fetchall(character.guild, current_owner)
        current_key = self.user_key(character)
        current_chars.remove(character)
        self.user_cache[current_key] = current_chars

        # Make the transfer
        await character.set_user(new_owner)

        # Only add it to the new owner's cache if they've already loaded
        new_key = self.user_key(character)
        if (new_chars := self.user_cache.get(new_key)) is not None:
            inserted = False

            for (index, char) in enumerate(new_chars):
                if char > character:
                    new_chars.insert(index, character)
                    inserted = True
                    break

            if not inserted:
                new_chars.append(character)

            self.user_cache[new_key] = new_chars


    async def mark_inactive(self, player):
        """
        When a player leaves a guild, mark their characters as inactive. They
        will then be culled after 30 days if they haven't returned before then.
        """
        await self.collection.update_many(
            { "guild": player.guild.id, "user": player.id },
            { "$set": { "log.left": datetime.datetime.utcnow() } }
        )


    async def mark_active(self, player):
        """
        When a player returns to the guild, we mark their characters as active
        so long as they haven't already been culled.
        """
        await self.collection.update_many(
            { "guild": player.guild.id, "user": player.id },
            { "$unset": { "log.left": 1 } }
        )


    def sort_user(self, guild: int, user: int):
        """Sorts the user's characters alphabetically."""
        guild, user = self.get_ids(guild, user)
        key = f"{guild} {user}"

        if not (user_chars := self.user_cache.get(key)):
            # Characters are automatically sorted when fetched
            return

        user_chars.sort()
        self.user_cache[key] = user_chars
