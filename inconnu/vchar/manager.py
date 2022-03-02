"""vchar/manager.py - Character cache/in-memory database."""

import os

import motor.motor_asyncio

from . import errors
from .vchar import VChar


class CharacterManager:
    """A class for maintaining a local copy of characters."""

    def __init__(self):
        self.all_fetched = {} # [user_id: bool]
        self.user_cache = {} # [guild: [user: [VChar]]]
        self.id_cache = {} # [char_id: VChar]


    @property
    def collection(self):
        """Get the database's characters collection."""
        client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URL"))
        return client.inconnu.characters


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


    async def fetch_character(self, guild: int, user: int, name: str):
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
            if (char := self.id_cache.get(name)) is not None:
                if guild and char.guild != guild:
                    raise ValueError(f"**{char.name}** doesn't belong to this server!")
                if user and char.user != user:
                    raise ValueError(f"**{char.name}** doesn't belong to this user!")

                return char

            user_chars = await self.all_characters(guild, user)
            for char in user_chars:
                if char.name.lower() == name.lower():
                    return char

            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        # No character name given. If the user only has one character, then we
        # can just return it. Otherwise, send an error message.

        user_chars = await self.all_characters(guild, user)

        if (count := len(user_chars)) == 0:
            raise errors.NoCharactersError("You have no characters.")
        if count == 1:
            return user_chars[0]

        # Two or more characters
        errmsg = f"You have {count} characters. Please specify which you want."
        raise errors.UnspecifiedCharacterError(errmsg)


    async def all_characters(self, guild: int, user: int):
        """
        Fetch all of a user's characters in a given guild. Adds them to the
        cache if necessary.
        """
        guild, user = self.get_ids(guild, user)
        key = f"{guild} {user}"

        if self.all_fetched.get(key, False):
            print("All characters cache HIT")
            return self.user_cache.get(key, [])

        print("All characters cache MISS")
        # Need to build the cache
        cursor = self.collection.find({ "guild": guild, "user": user })
        cursor.collation({ "locale": "en", "strength": 2 }).sort("name")

        characters = []
        async for char_params in cursor:
            characters.append(VChar(char_params))

        self.user_cache[key] = characters
        self.all_fetched[key] = True

        return characters


    async def add_to_cache(self, character):
        """Add the character to the cache."""
        self.id_cache[character.id] = character

        user_chars = await self.all_characters(character.guild, character.user)
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


    async def remove(self, character):
        """Remove a character from the database and the cache."""
        del self.id_cache[character.id]

        user_chars = await self.all_characters(character.guild, character.user)
        user_chars.remove(character)

        key = self.user_key(character)
        self.user_cache[key] = user_chars

        await self.collection.delete_one(character.find_query)
