"""Defines the base database class using postgres and autocommit."""
# pylint: disable=no-member

import os
from typing import Union

import psycopg2.sql


class Database:
    """Base database class."""
    # pylint: disable=too-few-public-methods

    def __init__(self):
        # Set up the database
        self.conn = psycopg2.connect(
            os.environ["DATABASE_URL"],
            dbname="inconnu",
            sslmode="require"
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()


    def __del__(self):
        self.conn.close()


    def _execute(self, query: Union[str, psycopg2.sql.SQL], *args):
        """
        Execute the specified query. Tries to reconnect to the database if there's an error.
        Args:
            query (Union[str, psycopg2.sql.SQL]): The SQL query to execute
            *args: The values associated with the query
            **kwargs: Used for determining if this is a second execution attempt
        """
        try:
            # Check first if the database connection is still valid
            self.cursor.execute("SELECT 1")
        except psycopg2.Error:
            # Though we are going to attempt to reconnect to the database,
            # technically this will catch other errors as well, such as bad
            # SQL syntax. We will trust that our syntax is correct, given it is
            # programmatically generated.
            self.conn = psycopg2.connect(
                os.environ["DATABASE_URL"],
                dbname="inconnu",
                sslmode="require"
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
        finally:
            self.cursor.execute(query, args)
