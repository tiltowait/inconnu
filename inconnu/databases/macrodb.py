"""databases/macrodp.py - Character macro database."""

import os
import ssl
import asyncio

import asyncpg

from .exceptions import MacroAlreadyExistsError, MacroNotFoundError

class MacroDB(): # Auditing asyncpg, so we aren't inheriting Database
    """A class for managing character macros."""

    def __init__(self):
        self.conn = None

        # Prepared statements
        self._check_exists = None
        self._create = None
        self._list = None
        self._fetch_macro = None
        self._delete = None


    async def _prepare(self):
        """Establish database connection."""
        if self.conn is not None:
            return

        # Equivalent to sslmode="require"
        sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        sslctx.check_hostname = False
        sslctx.verify_mode = ssl.CERT_NONE

        self.conn = await asyncpg.connect(
            os.environ["DATABASE_URL"],
            database="inconnu",
            ssl=sslctx
        )

        # Create the database
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Macros(
                MacroID int    GENERATED ALWAYS AS IDENTITY,
                CharID  int    NOT NULL,
                Name    text   NOT NULL,
                Pool    text[] NOT NULL,
                Diff    int    DEFAULT 0,
                Comment text   DEFAULT NULL,
                PRIMARY KEY (MacroID),

                CONSTRAINT fk_character
                    FOREIGN KEY(CharID)
                        REFERENCES Characters(CharID)
                        ON DELETE CASCADE
            );
            """
        )
        self.conn.add_termination_listener(self.__connection_closed)

        # Prepare some statements
        check_exists = "SELECT COUNT(*) FROM Macros WHERE CharID = $1 AND Name ILIKE $2"
        self._check_exists = await self.conn.prepare(check_exists)

        create = """
            INSERT INTO Macros(CharID, Name, Pool, Diff, Comment)
            VALUES($1, $2, $3, $4, $5)
        """
        self._create = await self.conn.prepare(create)

        list_all = "SELECT Name, Pool, Diff, Comment FROM Macros WHERE CharID = $1"
        self._list = await self.conn.prepare(list_all)

        fetch = "SELECT Name, Pool, Diff, Comment FROM Macros WHERE CharID = $1 AND Name ILIKE $2"
        self._fetch_macro = await self.conn.prepare(fetch)

        delete = "DELETE FROM Macros WHERE CharID = $1 AND Name ILIKE $2"
        self._delete = await self.conn.prepare(delete)


    async def __connection_closed(self, _):
        """A listener for connection closures."""
        self.conn = None


    async def macro_exists(self, char_id: int, macro_name: str) -> bool:
        """
        Determine whether a macro exists.
        Args:
            char_id (int): The character's ID
            macro_name (str): The new macro's name
        Returns (bool): True if the user has that macro already.
        """
        await self._prepare()
        count = await self._check_exists.fetchval(char_id, macro_name)
        return count > 0


    async def create_macro(
        self, char_id: int, macro_name: str, pool: list, diff: int, comment: str
    ):
        """
        Create a a macro.
        Args:
            char_id (int): The character's ID
            macro_name (str): The new macro's name
            pool (list): The macro's pool
            diff (int): The macro's default difficulty
            comment (str): The macro's comment

        Raises MacroAlreadyExistsError if the macro already exists.

        Macros do not have predefined Hunger, because of the fluid nature of that stat.
        """
        await self._prepare()
        if await self.macro_exists(char_id, macro_name):
            raise MacroAlreadyExistsError(f"Macro `{macro_name}` already exists.")

        await self._create.executemany(((char_id, macro_name, pool, diff, comment),))


    async def char_macros(self, char_id: int):
        """Fetch all the macros owned by the character."""
        await self._prepare()
        return await self._list.fetch(char_id)


    async def fetch_macro(self, char_id: int, macro_name: str):
        """
        Fetch a macro.
        Args:
            char_id (int): The character's ID
            macro_name (str): The macro's name

        Raises MacroNotFoundError if the macro doesn't exist.
        """
        await self._prepare()
        fetched = await self._fetch_macro.fetchrow(char_id, macro_name)
        if fetched is None:
            raise MacroNotFoundError(f"That character has no macro named '{macro_name}'.")

        return fetched


    async def delete_macro(self, char_id: int, macro_name: str):
        """
        Delete a a macro.
        Args:
            char_id (int): The character's ID
            macro_name (str): The new macro's name

        Raises MacroNotFoundError if the macro doesn't exist.
        """
        await self._prepare()
        if not await self.macro_exists(char_id, macro_name):
            raise MacroNotFoundError(f"That character has no macro named '{macro_name}.")

        await self._delete.executemany(((char_id, macro_name),))
