"""Defines the base database class using postgres and autocommit."""
# pylint: disable=no-member

import os
import ssl

import asyncpg


class Database:
    """Base database class."""
    # pylint: disable=too-few-public-methods

    def __init__(self):
        self.conn = None

    async def _prepare(self):
        """Prepare the database in case of connection loss."""
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
        self.conn.add_termination_listener(self.__connection_closed)


    async def __connection_closed(self, _):
        """A listener for connection closures."""
        self.conn = None
