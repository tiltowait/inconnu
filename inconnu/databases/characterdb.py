"""Describes the UserDB class for managing characters across different guilds."""
# pylint: disable=too-many-arguments

from collections import OrderedDict

from psycopg2.sql import SQL, Identifier

from .base import Database
from .exceptions import CharacterNotFoundError, AmbiguousTraitError, TraitNotFoundError

class CharacterDB(Database):
    """Class for managing characters owned by users across different guilds."""

    def __init__(self):
        super().__init__()

        # Create the basic character table
        self.cursor.execute(
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
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Traits(
                GuildID bigint NOT NULL,
                UserID  bigint NOT NULL,
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


    # Character CRUD

    def characters(self, guildid: int, userid: int) -> dict:
        """
        Retrieve the characters the user has in a given guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
        Returns (list): A list of characters held by the user.
        """
        query = "SELECT CharName, CharID FROM Characters WHERE GuildID=%s AND UserID=%s;"
        self._execute(query, guildid, userid)
        results = self.cursor.fetchall()

        # For the sake of convenience, we will put the users into a dictionary of [str: int]. The
        # reason for this is due to the fact that users will refer to their characters by name only,
        # and this provides an easy way to look up the character ID when checking attributes.
        char_dict = dict(results)
        return char_dict


    def character(self, guildid: int, userid: int, char_name: str) -> tuple:
        """
        Retrieve the name and ID for a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
        Returns (int): The character's ID.

        Character names are case-insensitive, which is why the name is also returned.
        Raises CharacterNotFoundError if the character isn't found.
        """
        query = """
            SELECT CharName, CharID
            FROM Characters
            WHERE GuildID=%s AND UserID=%s AND CharName ILIKE %s;
        """
        self._execute(query, guildid, userid, char_name)
        results = self.cursor.fetchone()

        if results is None:
            raise CharacterNotFoundError(f"You do not have a character named `{char_name}`.")

        return results


    def character_count(self, guildid: int, userid: int) -> int:
        """
        Retrieve the number of characters the user has in the guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
        Returns (int): The number of characters.
        """
        query = "SELECT COUNT(*) FROM Characters WHERE GuildID=%s AND UserID=%s;"
        self._execute(query, guildid, userid)
        results = self.cursor.fetchone()

        return results[0]


    def character_id(self, guildid: int, userid: int, char_name: str) -> int:
        """
        Retrieve the ID for a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
        Returns (int): The character's ID.

        Character names are case-insensitive.
        Raises CharacterNotFoundError if the character isn't found.
        """
        query = "SELECT CharID FROM Characters WHERE GuildID=%s AND UserID=%s AND CharName ILIKE %s;"
        self._execute(query, guildid, userid, char_name)
        results = self.cursor.fetchone()

        if results is None:
            raise CharacterNotFoundError(f"You do not have a character named {char_name}.")

        return results[0]


    def character_exists(self, guildid: int, userid: int, char_name: str) -> bool:
        """
        Determine whether a user has a character of a given name in the guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
        Returns (bool): True if the character exists.
        """
        query = "SELECT 1 FROM Characters WHERE GuildID=%s AND UserID=%s AND CharName ILIKE %s;"
        self._execute(query, guildid, userid, char_name)
        results = self.cursor.fetchone()

        return results is not None


    #pylint: disable=invalid-name
    def add_character(self,
        guildid: int, userid: int, char_type: int,
        name: str, humanity: int, stains: int, hp: str, wp: str
    ):
        """
        Adds a character to a guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The new character's name
        """
        query = """
        INSERT INTO Characters(
            GuildID, UserID, Splat, CharName, Humanity, Stains, Health, Willpower
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        self._execute(query, guildid, userid, char_type, name, humanity, stains, hp, wp)


    def delete_character(self, guildid: int, userid: int, char_id: int) -> bool:
        """
        Removes a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's ID
        Returns (bool): True if the character was successfully removed.
        """
        query = "DELETE FROM Characters WHERE GuildID=%s AND UserID=%s AND CharID=%s;"
        self._execute(query, guildid, userid, char_id)

        return self.cursor.statusmessage != "UPDATE 0"


    def rename_character(self, guildid: int, userid: int, char_id: int, new_name: str):
        """
        Rename a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_name (str): The character's new name
        Raises CharacterNotFoundError if the character does not exist.
        """
        query = "UPDATE Characters SET CharName=%s WHERE GuildID=%s AND UserID=%s AND CharID=%s;"
        self._execute(query, new_name, guildid, userid, char_id)

        if self.cursor.statusmessage == "UPDATE 0":
            raise CharacterNotFoundError("Character does not exist.")


    def get_hunger(self, guildid: int, userid: int, charid: int) -> int:
        """
        Retrieve the character's hunger.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's hunger.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "Hunger")


    def set_hunger(self, guildid: int, userid: int, charid: int, new_hunger: str) -> int:
        """
        Update the character's hunger.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_hunger (int): The character's new hunger

        Raises CharacterNotFoundError if the character does not exist.
        """
        self.__set_attribute(guildid, userid, charid, "Hunger", new_hunger)


    def get_health(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the given character health string.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's health string.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "Health")


    def set_health(self, guildid: int, userid: int, charid: int, new_health: str) -> str:
        """
        Update the given character health string.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_health (str): The character's new health string

        Raises CharacterNotFoundError if the character does not exist.
        """
        self.__set_attribute(guildid, userid, charid, "Health", new_health)


    def get_willpower(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the given character willpower string.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's willpower string.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "Willpower")


    def set_willpower(self, guildid: int, userid: int, charid: int, new_willpower: str) -> str:
        """
        Update the given character willpower string.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_willpower (str): The character's new willpower string

        Raises CharacterNotFoundError if the character does not exist.
        """
        self.__set_attribute(guildid, userid, charid, "Willpower", new_willpower)


    def get_humanity(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the given character humanity string.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (int): The character's humanity string.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "Humanity")


    def set_humanity(self, guildid: int, userid: int, charid: int, new_humanity: int) -> str:
        """
        Set the given character humanity string.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_humanity (int): The character's new humanity string

        Raises CharacterNotFoundError if the character does not exist.
        """
        self.__set_attribute(guildid, userid, charid, "Humanity", new_humanity)
        self.set_stains(guildid, userid, charid, 0)


    def get_stains(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the character's stains.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The number of stains.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "Stains")


    def set_stains(self, guildid: int, userid: int, charid: int, new_stains: int) -> str:
        """
        Set the character's stains.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_stains (int): The new number of stains

        Raises CharacterNotFoundError if the character does not exist.
        """
        self.__set_attribute(guildid, userid, charid, "Stains", new_stains)



    def get_splat(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the given character splat.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's splat.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "Splat")


    def set_splat(self, guildid: int, userid: int, charid: int, new_splat: str) -> str:
        """
        Set the given character splat.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_splat (str): The character's new splat

        Raises CharacterNotFoundError if the character does not exist.
        """
        self.__set_attribute(guildid, userid, charid, "Splat", new_splat)


    def get_current_xp(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the character's current XP.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's current XP.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "CurrentXP")


    def set_current_xp(self, guildid: int, userid: int, charid: int, new_cur_xp: int) -> str:
        """
        Set the character's current XP.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_cur_xp (str): The character's new current XP

        Raises CharacterNotFoundError if the character does not exist.
        """
        total_xp = self.get_total_xp(guildid, userid, charid)
        if new_cur_xp > total_xp:
            raise ValueError(f"Current XP cannot exceed total XP! (`{new_cur_xp}` > `{total_xp}`)")

        self.__set_attribute(guildid, userid, charid, "CurrentXP", new_cur_xp)


    def get_total_xp(self, guildid: int, userid: int, charid: int) -> str:
        """
        Retrieve the character's total XP.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
        Returns (str): The character's total XP.

        Raises CharacterNotFoundError if the character does not exist.
        """
        return self.__get_attribute(guildid, userid, charid, "TotalXP")


    def set_total_xp(self, guildid: int, userid: int, charid: int, new_tot_xp: int) -> str:
        """
        Set the character's total XP and modify the character's current XP by the same delta.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            new_cur_xp (str): The character's new total XP

        Raises CharacterNotFoundError if the character does not exist.
        """
        delta = new_tot_xp - self.get_total_xp(guildid, userid, charid)
        new_cur_xp = self.get_current_xp(guildid, userid, charid) + delta

        if new_cur_xp < 0:
            new_cur_xp = 0 # No negatives allowed

        self.__set_attribute(guildid, userid, charid, "TotalXP", new_tot_xp)
        self.set_current_xp(guildid, userid, charid, new_cur_xp)


    def __get_attribute(self, guildid: int, userid: int, charid: int, attribute: str):
        """
        Retrieve the given character attribute.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            attribute (str): The column name of an attribute
        Returns: The value contained in the column.

        Raises CharacterNotFoundError if the character does not exist.
        This method does no checking for column validity!
        """
        attribute = attribute.lower()
        query = SQL("""
            SELECT {key}
            FROM Characters
            WHERE GuildID=%s AND UserID=%s AND CharID=%s;
            """
        ).format(key=Identifier(attribute))

        self._execute(query, guildid, userid, charid)
        results = self.cursor.fetchone()

        if len(results) == 0:
            raise CharacterNotFoundError("Character not found.")

        return results[0]


    def __set_attribute(self, guildid: int, userid: int, charid: int, attribute: str, new_value):
        """
        Update the given character attribute.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The character's database ID
            attribute (str): The column name of an attribute
            new_value: The column's new attribute

        Raises CharacterNotFoundError if the character does not exist.
        This method does no checking for column validity!
        """
        attribute = attribute.lower()
        query = SQL("""
            UPDATE Characters
            SET {key}=%s
            WHERE GuildID=%s AND UserID=%s AND CharID=%s;
            """
        ).format(key=Identifier(attribute))

        self._execute(query, new_value, guildid, userid, charid)

        if self.cursor.statusmessage == "UPDATE 0":
            raise CharacterNotFoundError("Character not found.")


    # Trait CRUD

    def trait_exists(self, guildid: int, userid: int, charid: int, trait: str) -> bool:
        """
        Determine whether a character already has a given trait.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
            trait (str): The name of the trait to add
        Returns (bool): True if the trait exists already.
        """
        query = """
            SELECT Trait
            FROM Traits
            WHERE
                GuildID=%s
                AND UserID=%s
                AND CharID=%s
                AND Trait ILIKE %s
            ;
        """
        self._execute(query, guildid, userid, charid, trait)
        results = self.cursor.fetchone()

        return results is not None


    def add_trait(self, guildid: int, userid: int, char_id: int, trait: str, rating: int):
        """
        Adds or updates a trait on a given character
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_id (int): The name of the character
            trait (str): The name of the trait to add
            rating (int): The trait's rating

        Raises CharacterNotFound if the user does not have a character by that name.
        """
        # Figure out if we're updating or adding a trait
        if self.trait_exists(guildid, userid, char_id, trait):
            query = """
                UPDATE Traits
                SET Rating=%s
                WHERE
                    GuildID=%s
                    AND UserID=%s
                    AND CharID=%s
                    AND Trait ILIKE %s
                ;
            """
            self._execute(query, rating, guildid, userid, char_id, trait)
        else:
            query = "INSERT INTO Traits VALUES (%s, %s, %s, %s, %s);"
            self._execute(query, guildid, userid, char_id, trait, rating)


    def trait_rating(self, guildid: int, userid: int, charid: int, trait: str) -> int:
        """
        Fetch the rating for a given character's trait.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            charid (int): The character's database ID
            trait (str): The name of the trait to add
        Returns (int): The rating for the trait.

        Raises TraitNotFoundError if the trait does not exist.
        """
        fuzzy_trait = trait + "%"

        query = """
            SELECT Trait, Rating
            FROM Traits
            WHERE
                GuildID=%s
                AND UserID=%s
                AND CharID=%s
                AND Trait ILIKE %s
            ORDER BY Trait
            ;
        """
        # First, see if we have an exact match
        self._execute(query, guildid, userid, charid, trait)
        exact_match_results = self.cursor.fetchone()

        if exact_match_results is not None:
            return exact_match_results[1]

        # Exact match not found; see if it's got ambiguous matches
        self._execute(query, guildid, userid, charid, fuzzy_trait)
        results = self.cursor.fetchall()

        if len(results) == 0:
            raise TraitNotFoundError(f"`{trait}` not found.")

        if len(results) == 1:
            return results[0][1]

        # Ambiguous trait match
        matches = list(map(lambda row: row[0], results))
        raise AmbiguousTraitError(trait, matches)


    def get_all_traits(self, guildid: int, userid: int, charid: int):
        """
        Retrieve all of a character's traits.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            charid (int): The character's database ID
        Returns (dict): All of the character's traits, plus their ratings.
        """
        query = """
            SELECT Trait, Rating
            FROM Traits
            WHERE GuildID=%s AND UserID=%s AND CharID=%s
            ORDER BY Trait;
        """
        self._execute(query, guildid, userid, charid)
        results = self.cursor.fetchall()

        return OrderedDict(results)


    def delete_trait(self, guildid: int, userid: int, charid: int, trait: str):
        """
        Fetch the rating for a given character's trait.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            charid (int): The character's database ID
            trait (str): The name of the trait to add
        Returns (int): The rating for the trait.
        """
        query = """
            DELETE FROM Traits
            WHERE GuildID=%s
                AND UserID=%s
                AND CharID=%s
                AND Trait ILIKE %s;
        """
        self._execute(query, guildid, userid, charid, trait)
