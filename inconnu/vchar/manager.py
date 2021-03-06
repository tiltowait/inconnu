"""vchar/manager.py - Character cache/in-memory database."""

import datetime

import inconnu


class CharacterManager:
    """A class for maintaining a local copy of characters."""

    def __init__(self):
        self.all_fetched = {}  # [user_id: bool]
        self.user_cache = {}  # [guild: [user: [VChar]]]
        self.id_cache = {}  # [char_id: VChar]

        # Set after construction. Used to check whether a user is an admin
        self.bot = None

    @property
    def collection(self):
        """Get the database's characters collection."""
        return inconnu.db.characters

    async def fetchone(self, guild: int, user: int, name: str):
        """
        Fetch a single character.
        Args:
            guild: The Discord ID of the guild the bot was invoked in
            user: The user's Discord ID
            name (optional): The character's name or ID

        If the name isn't given, return the user's sole character, if applicable.
        """
        if isinstance(name, inconnu.VChar):
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
                if char.name.lower() == name.lower():
                    self._validate(guild, user, char)
                    return char

            # The given name doesn't match any character ID or name
            raise inconnu.errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        # No character name given. If the user only has one character, then we
        # can just return it. Otherwise, send an error message.

        user_chars = await self.fetchall(guild, user)

        if (count := len(user_chars)) == 0:
            raise inconnu.errors.NoCharactersError("You have no characters.")
        if count == 1:
            return user_chars[0]

        # Two or more characters
        errmsg = f"You have {count} characters. Please specify which to use."
        raise inconnu.errors.UnspecifiedCharacterError(errmsg)

    async def fetchall(self, guild: int, user: int):
        """
        Fetch all of a user's characters in a given guild. Adds them to the
        cache if necessary.
        """
        guild, user, key = self._get_ids(guild, user)

        if self.all_fetched.get(key, False):
            return self.user_cache.get(key, [])

        # Need to build the cache
        cursor = self.collection.find({"guild": guild, "user": user})
        cursor.collation({"locale": "en", "strength": 2}).sort("name")

        characters = []
        async for char_params in cursor:
            character = inconnu.VChar(char_params)

            if character.id not in self.id_cache:
                characters.append(character)
                self.id_cache[character.id] = character
            else:
                # Use the already cached character. This will probably never
                # happen, but we'll put it here just in case
                characters.append(self.id_cache[character.id])

        self.user_cache[key] = characters
        self.all_fetched[key] = True

        return characters

    async def exists(self, guild: int, user: int, name: str, is_spc: bool) -> bool:
        """Determine whether a user already has a named character."""
        if is_spc:
            owner_id = inconnu.constants.INCONNU_ID
            name += " (SPC)"
        else:
            owner_id = user
        user_chars = await self.fetchall(guild, owner_id)

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

        key = self._user_key(character)
        self.user_cache[key] = user_chars

        await self.collection.insert_one(character.raw)

    async def remove(self, character):
        """Remove a character from the database and the cache."""
        deletion = await self.collection.delete_one(character.find_query)

        if deletion.deleted_count == 1:
            user_chars = await self.fetchall(character.guild, character.user)
            if character in user_chars:
                user_chars.remove(character)

            key = self._user_key(character)
            self.user_cache[key] = user_chars

            if character.id in self.id_cache:
                del self.id_cache[character.id]

            return True

        return False

    async def transfer(self, character, current_owner, new_owner):
        """Transfer one character to another."""
        # Remove it from the owner's cache
        current_chars = await self.fetchall(character.guild, current_owner)
        current_key = self._user_key(character)
        current_chars.remove(character)
        self.user_cache[current_key] = current_chars

        # Make the transfer
        await character.set_user(new_owner)

        # Only add it to the new owner's cache if they've already loaded
        new_key = self._user_key(character)
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
            {"guild": player.guild.id, "user": player.id},
            {"$set": {"log.left": datetime.datetime.utcnow()}},
        )

    async def mark_active(self, player):
        """
        When a player returns to the guild, we mark their characters as active
        so long as they haven't already been culled.
        """
        await self.collection.update_many(
            {"guild": player.guild.id, "user": player.id}, {"$unset": {"log.left": 1}}
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
    def _get_ids(guild, user):
        """Get the guild and user IDs."""
        if guild and not isinstance(guild, int):
            guild = guild.id
        if user and not isinstance(user, int):
            user = user.id

        key = f"{guild} {user}"

        return guild, user, key

    @staticmethod
    def _user_key(character):
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
