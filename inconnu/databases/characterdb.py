"""Describes the UserDB class for managing characters across different guilds."""
# pylint: disable=too-many-arguments

from collections import OrderedDict

from .base import Database
from .exceptions import CharacterNotFoundError, AmbiguousTraitError, TraitNotFoundError

class CharacterDB(Database):
    """Class for managing characters owned by users across different guilds."""

    def __init__(self):
        super().__init__()

        # Prep the prep! This is to stop pylint from complaining
        self._characters = None
        self._character_fetch = None
        self._char_count = None
        self._char_exists = None
        self._add_char = None
        self._delete = None
        self._rename = None
        self._trait_exists = None
        self._update_trait = None
        self._add_trait = None
        self._trait_rating = None
        self._get_all_traits = None
        self._delete_trait = None


    async def _prepare(self):
        """Prepare the database and prep statements in case of connection loss."""
        if self.conn is not None:
            return

        await super()._prepare()

        # Create the basic character table
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Characters(
                GuildID   bigint NOT NULL,
                UserID    bigint NOT NULL,
                Splat     int    NOT NULL,
                CharName  text   NOT NULL,
                Hunger    int    DEFAULT 1,
                Humanity  int    DEFAULT 7,
                Stains    int    DEFAULT 0,
                Health    text   NOT NULL,
                Willpower text   NOT NULL,
                CurrentXP int    DEFAULT 0,
                TotalXP   int    DEFAULT 0,
                CharID    int    GENERATED ALWAYS AS IDENTITY,
                PRIMARY KEY (CharID)
            );
            """
        )

        # Create the character traits table
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Traits(
                CharID  int    NOT NULL,
                Trait   text   NOT NULL,
                Rating  int    DEFAULT 0,

                CONSTRAINT fk_character
                    FOREIGN KEY(CharID)
                        REFERENCES Characters(CharID)
                        ON DELETE CASCADE
            );
            """
        )

        # Prepared statements
        all_chars = "SELECT CharName, CharID FROM Characters WHERE GuildID=$1 AND UserID=$2"
        self._characters = await self.conn.prepare(all_chars)

        character_fetch = """
            SELECT CharName, CharID
            FROM Characters
            WHERE GuildID=$1 AND UserID=$2 AND CharName ILIKE $3
        """
        self._character_fetch = await self.conn.prepare(character_fetch)

        char_count = "SELECT COUNT(*) FROM Characters WHERE GuildID=$1 AND UserID=$2"
        self._char_count = await self.conn.prepare(char_count)

        exists = "SELECT 1 FROM Characters WHERE GuildID=$1 AND UserID=$2 AND CharName ILIKE $3"
        self._char_exists = await self.conn.prepare(exists)

        add_char = """
        INSERT INTO Characters(
            GuildID, UserID, Splat, CharName, Humanity, Stains, Health, Willpower
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        self._add_char = await self.conn.prepare(add_char)

        delete = "DELETE FROM Characters WHERE CharID=$1"
        self._delete = await self.conn.prepare(delete)

        rename = "UPDATE Characters SET CharName=$1 WHERE CharID=$2"
        self._rename = await self.conn.prepare(rename)

        trait_exists = """
            SELECT Trait
            FROM Traits
            WHERE
                CharID=$1
                AND Trait ILIKE $2
        """
        self._trait_exists = await self.conn.prepare(trait_exists)

        update_trait = """
            UPDATE Traits
            SET Rating=$1
            WHERE
                CharID=$2
                AND Trait ILIKE $3
        """
        self._update_trait = await self.conn.prepare(update_trait)

        add_trait = "INSERT INTO Traits VALUES ($1, $2, $3)"
        self._add_trait = await self.conn.prepare(add_trait)

        trait_rating = """
            SELECT Trait, Rating
            FROM Traits
            WHERE
                CharID=$1
                AND Trait ILIKE $2
            ORDER BY Trait
        """
        self._trait_rating = await self.conn.prepare(trait_rating)

        get_all_traits = """
            SELECT Trait, Rating
            FROM Traits
            WHERE CharID=$1
            ORDER BY Trait
        """
        self._get_all_traits = await self.conn.prepare(get_all_traits)

        delete_trait = """
            DELETE FROM Traits
            WHERE CharID=$1
                AND Trait ILIKE $2
        """
        self._delete_trait = await self.conn.prepare(delete_trait)


    # Character CRUD

    async def characters(self, guildid: int, userid: int) -> dict:
        """
        Retrieve the characters the user has in a given guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
        Returns (list): A list of characters held by the user.
        """
        await self._prepare()
        results = await self._characters.fetch(guildid, userid)

        # For the sake of convenience, we will put the users into a dictionary of [str: int]. The
        # reason for this is due to the fact that users will refer to their characters by name only,
        # and this provides an easy way to look up the character ID when checking attributes.
        return {result["charname"]: result["charid"] for result in results}


    async def character(self, guildid: int, userid: int, char_name: str) -> tuple:
        """
        Retrieve the name and ID for a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
        Returns (tuple): The character's name and ID.

        Character names are case-insensitive, which is why the name is also returned.
        Raises CharacterNotFoundError if the character isn't found.
        """
        await self._prepare()
        char = await self._character_fetch.fetchrow(guildid, userid, char_name)
        if char is None:
            raise CharacterNotFoundError(f"You do not have a character named `{char_name}`.")

        return (char["charname"], char["charid"])


    async def character_count(self, guildid: int, userid: int) -> int:
        """
        Retrieve the number of characters the user has in the guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
        Returns (int): The number of characters.
        """
        await self._prepare()
        return await self._char_count.fetchval(guildid, userid)


    async def character_exists(self, guildid: int, userid: int, char_name: str) -> bool:
        """
        Determine whether a user has a character of a given name in the guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
        Returns (bool): True if the character exists.
        """
        await self._prepare()
        char = await self._char_exists.fetchrow(guildid, userid, char_name)
        return char is not None


    #pylint: disable=invalid-name
    async def add_character(self,
        guildid: int, userid: int, char_type: int,
        name: str, humanity: int, stains: int, hp: str, wp: str
    ):
        """
        Add a character to a guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The new character's name
        """
        await self._prepare()
        await self._add_char.fetch(guildid, userid, char_type, name, humanity, stains, hp, wp)

        _, char_id = await self.character(guildid, userid, name)
        return char_id


    async def delete_character(self, char_id: int) -> bool:
        """
        Removes a given character.
        Args:
            char_id (int): The character's ID
        Returns (bool): True if the character was successfully removed.
        """
        await self._prepare()
        await self._delete.fetch(char_id)

        return self._delete.get_statusmsg() != "UPDATE 0"


    async def rename_character(self, char_id: int, new_name: str):
        """
        Rename a given character.
        Args:
            char_id (int): The character's database ID
            new_name (str): The character's new name
        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self._rename.fetch(new_name, char_id)

        if self._rename.get_statusmsg() == "UPDATE 0":
            raise CharacterNotFoundError("Character does not exist.")


    async def get_hunger(self, charid: int) -> int:
        """
        Retrieve the character's hunger.
        Args:
            char_id (int): The character's database ID
        Returns (str): The character's hunger.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "Hunger")


    async def set_hunger(self, charid: int, new_hunger: str) -> int:
        """
        Update the character's hunger.
        Args:
            char_id (int): The character's database ID
            new_hunger (int): The character's new hunger

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self.__set_attribute(charid, "Hunger", new_hunger)


    async def get_health(self, charid: int) -> str:
        """
        Retrieve the given character health string.
        Args:
            char_id (int): The character's database ID
        Returns (str): The character's health string.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "Health")


    async def set_health(self, charid: int, new_health: str) -> str:
        """
        Update the given character health string.
        Args:
            char_id (int): The character's database ID
            new_health (str): The character's new health string

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self.__set_attribute(charid, "Health", new_health)


    async def get_willpower(self, charid: int) -> str:
        """
        Retrieve the given character willpower string.
        Args:
            char_id (int): The character's database ID
        Returns (str): The character's willpower string.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "Willpower")


    async def set_willpower(self, charid: int, new_willpower: str) -> str:
        """
        Update the given character willpower string.
        Args:
            char_id (int): The character's database ID
            new_willpower (str): The character's new willpower string

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self.__set_attribute(charid, "Willpower", new_willpower)


    async def get_humanity(self, charid: int) -> str:
        """
        Retrieve the given character humanity string.
        Args:
            char_id (int): The character's database ID
        Returns (int): The character's humanity string.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "Humanity")


    async def set_humanity(self, charid: int, new_humanity: int) -> str:
        """
        Set the given character humanity string.
        Args:
            char_id (int): The character's database ID
            new_humanity (int): The character's new humanity string

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self.__set_attribute(charid, "Humanity", new_humanity)
        await self.set_stains(charid, 0)


    async def get_stains(self, charid: int) -> str:
        """
        Retrieve the character's stains.
        Args:
            char_id (int): The character's database ID
        Returns (str): The number of stains.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "Stains")


    async def set_stains(self, charid: int, new_stains: int) -> str:
        """
        Set the character's stains.
        Args:
            char_id (int): The character's database ID
            new_stains (int): The new number of stains

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self.__set_attribute(charid, "Stains", new_stains)



    async def get_splat(self, charid: int) -> str:
        """
        Retrieve the given character splat.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's splat.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "Splat")


    async def set_splat(self, charid: int, new_splat: str) -> str:
        """
        Set the given character splat.
        Args:
            char_id (int): The character's database ID
            new_splat (str): The character's new splat

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        await self.__set_attribute(charid, "Splat", new_splat)


    async def get_current_xp(self, charid: int) -> str:
        """
        Retrieve the character's current XP.
        Args:
            char_id (int): The character's database ID
        Returns (str): The character's current XP.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "CurrentXP")


    async def set_current_xp(self, charid: int, new_cur_xp: int) -> str:
        """
        Set the character's current XP.
        Args:
            char_id (int): The character's database ID
            new_cur_xp (str): The character's new current XP

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()

        total_xp = await self.get_total_xp(charid)
        if new_cur_xp > total_xp:
            raise ValueError(f"Current XP cannot exceed total XP! (`{new_cur_xp}` > `{total_xp}`)")

        await self.__set_attribute(charid, "CurrentXP", new_cur_xp)


    async def get_total_xp(self, charid: int) -> str:
        """
        Retrieve the character's total XP.
        Args:
            char_id (int): The character's database ID
        Returns (str): The character's total XP.

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()
        return await self.__get_attribute(charid, "TotalXP")


    async def set_total_xp(self, charid: int, new_tot_xp: int) -> str:
        """
        Set the character's total XP and modify the character's current XP by the same delta.
        Args:
            char_id (int): The character's database ID
            new_cur_xp (str): The character's new total XP

        Raises CharacterNotFoundError if the character does not exist.
        """
        await self._prepare()

        delta = new_tot_xp - await self.get_total_xp(charid)
        new_cur_xp = await self.get_current_xp(charid) + delta

        if new_cur_xp < 0:
            new_cur_xp = 0 # No negatives allowed

        await self.__set_attribute(charid, "TotalXP", new_tot_xp)
        await self.set_current_xp(charid, new_cur_xp)


    async def __get_attribute(self, charid: int, attribute: str):
        """
        Retrieve the given character attribute.
        Args:
            char_id (int): The character's database ID
            attribute (str): The column name of an attribute
        Returns: The value contained in the column.

        Raises CharacterNotFoundError if the character does not exist.
        This method does no checking for column validity!
        """
        await self._prepare()

        # This is a hack
        query = f"""
            SELECT {attribute.lower()}
            FROM Characters
            WHERE CharID=$1
        """
        results = await self.conn.fetchrow(query, charid)

        if results is None:
            raise CharacterNotFoundError("Character not found.")

        return results[0]


    async def __set_attribute(self, charid: int, attribute: str, new_value):
        """
        Update the given character attribute.
        Args:
            char_id (int): The character's database ID
            attribute (str): The column name of an attribute
            new_value: The column's new attribute

        Raises CharacterNotFoundError if the character does not exist.
        This method does no checking for column validity!
        """
        await self._prepare()

        # This is a hack
        query = f"""
            UPDATE Characters
            SET {attribute.lower()}=$1
            WHERE CharID=$2;
        """
        status = await self.conn.execute(query, new_value, charid)

        if status == "UPDATE 0":
            raise CharacterNotFoundError("Character not found.")


    # Trait CRUD

    async def trait_exists(self, charid: int, trait: str) -> bool:
        """
        Determine whether a character already has a given trait.
        Args:
            char_name (str): The name of the character
            trait (str): The name of the trait to add
        Returns (bool): True if the trait exists already.
        """
        await self._prepare()
        return await self._trait_exists.fetchrow(charid, trait) is not None


    async def add_trait(self, char_id: int, trait: str, rating: int):
        """
        Adds or updates a trait on a given character
        Args:
            char_id (int): The name of the character
            trait (str): The name of the trait to add
            rating (int): The trait's rating
        """
        # Figure out if we're updating or adding a trait
        await self._prepare()

        if await self.trait_exists(char_id, trait):
            await self._update_trait.fetch(rating, char_id, trait)
        else:
            await self._add_trait.fetch(char_id, trait, rating)


    async def add_multiple_traits(self, charid: int, traits: dict):
        """
        Adds or updates a trait on a given character
        Args:
            char_id (int): The name of the character
            traits (dict): The str: int trait pairs
        """
        async with self.conn.transaction():
            for trait, rating in traits.items():
                await self._add_trait.fetch(charid, trait, rating)


    async def trait_rating(self, charid: int, trait: str) -> int:
        """
        Fetch a trait name and rating based off a fuzzy match.
        Args:
            charid (int): The character's database ID
            trait (str): The name of the trait to add
        Returns (tuple): The name and rating for the trait.

        Raises TraitNotFoundError if the trait does not exist.
        """
        await self._prepare()

        # First, see if we have an exact match
        exact_match = await self._trait_rating.fetchrow(charid, trait)

        if exact_match is not None:
            return (exact_match["trait"], exact_match["rating"])

        # Exact match not found; see if it's got ambiguous matches
        fuzzy_trait = trait + "%"
        results = await self._trait_rating.fetch(charid, fuzzy_trait)

        if len(results) == 0:
            raise TraitNotFoundError(f"`{trait}` not found.")

        if len(results) == 1:
            match = results[0]
            return (match["trait"], match["rating"])

        # Ambiguous trait match
        matches = list(map(lambda row: row[0], results))
        raise AmbiguousTraitError(trait, matches)


    async def get_all_traits(self, charid: int):
        """
        Retrieve all of a character's traits.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            charid (int): The character's database ID
        Returns (dict): All of the character's traits, plus their ratings.
        """
        await self._prepare()

        results = await self._get_all_traits.fetch(charid)
        return OrderedDict(map(lambda res: (res["trait"], res["rating"]), results))


    async def delete_trait(self, charid: int, trait: str):
        """
        Fetch the rating for a given character's trait.
        Args:
            charid (int): The character's database ID
            trait (str): The name of the trait to add
        """
        await self._prepare()
        await self._delete_trait.fetch(charid, trait)
