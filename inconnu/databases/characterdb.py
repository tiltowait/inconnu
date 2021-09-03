"""Describes the UserDB class for managing characters across different guilds."""
# pylint: disable=too-many-arguments

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
                CharType  int    NOT NULL,
                CharName  text   NOT NULL,
                Humanity  text   NOT NULL,
                Heatlh    text   NOT NULL,
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

        if len(results) == 0:
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
        user_characters = self.characters(guildid, userid).keys()
        return char_name in user_characters


    #pylint: disable=invalid-name
    def add_character(
        self, guildid: int, userid: int, char_type: int, name: str, humanity: int, hp: str, wp: str
    ):
        """
        Adds a character to a guild.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The new character's name
        """
        query = "INSERT INTO Characters VALUES (%s, %s, %s, %s, %s, %s, %s);"
        self._execute(query, guildid, userid, char_type, name, humanity, hp, wp)


    def delete_character(self, guildid: int, userid: int, char_name: str) -> bool:
        """
        Removes a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The character's name
        Returns (bool): True if the character was successfully removed.
        """
        query = "DELETE FROM Characters WHERE GuildID=%s AND UserID=%s AND CharName=%s;"
        self._execute(query, guildid, userid, char_name)

        return self.cursor.statusmessage == "UPDATE 0"


    def rename_character(self, guildid: int, userid: int, old_name: str, new_name: str) -> bool:
        """
        Renames a given character.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            old_name (str): The character's current name
            new_name (str): The character's new name
        Returns (bool): True if the character was successfully renamed.
        """
        query = "UPDATE Characters SET CharName=%s WHERE GuildID=%s AND UserID=%s AND CharName=%s;"
        self._execute(query, new_name, guildid, userid, old_name)

        return self.cursor.statusmessage == "UPDATE 0"


    # Trait CRUD

    def trait_exists(self, guildid: int, userid: int, charid: int, trait_name: str) -> bool:
        """
        Determine whether a character already has a given trait.
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
            trait (str): The name of the trait to add
        Returns (bool): True if the trait exists already.
        """
        trait = trait_name + "%" # Wildcard matching

        query = """
            SELECT Trait
            FROM TRAITS
            WHERE
                GuildID=%s
                AND UserID=%s
                AND CharID=%s
                AND Trait ILIKE %s
            ;
        """
        self._execute(query, guildid, userid, charid, trait)
        results = self.cursor.fetchall()

        if len(results) == 0:
            return False

        if len(results) == 1:
            return True

        # More than one match
        matches = list(map(lambda row: row[0], results))
        raise AmbiguousTraitError(trait_name, matches)


    def add_trait(self, guildid: int, userid: int, char_name: str, trait: str, rating: int):
        """
        Adds or updates a trait on a given character
        Args:
            guildid (int): Discord ID of the guild
            userid (int): Discord ID of the user
            char_name (str): The name of the character
            trait (str): The name of the trait to add
            rating (int): The trait's rating

        Raises CharacterNotFound if the user does not have a character by that name.
        """
        charid = self.character_id(guildid, userid, char_name)

        if charid is not None:
            # Figure out if we're updating or adding a trait
            if self.trait_exists(guildid, userid, charid, trait):
                query = """
                    UPDATE Traits
                    SET Rating=%s
                    WHERE
                        GuildID=%s
                        AND UserID=%s
                        AND CharID=%s
                        AND Trait=%s
                    ;
                """
                self._execute(query, rating, guildid, userid, charid, trait)
            else:
                query = "INSERT INTO Traits VALUES (%s, %s, %s, %s, %s);"
                self._execute(query, guildid, userid, charid, trait, rating)

        else:
            # pylint: disable=raise-missing-from
            raise CharacterNotFoundError(f"You do not have a character named {char_name}.")


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
            ;
        """
        self._execute(query, guildid, userid, charid, fuzzy_trait)
        results = self.cursor.fetchall()

        if len(results) == 0:
            raise TraitNotFoundError(f"{trait} not found.")

        if len(results) == 1:
            rating = results[0][1]
            return rating

        # Ambiguous trait match
        matches = list(map(lambda row: row[0], results))
        raise AmbiguousTraitError(trait, matches)
