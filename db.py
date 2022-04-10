import sqlite3
from sqlite3 import Row
import os
from typing import Tuple, List


class SqliteConnector():
    """
    Class managing a connection to the SQLite instance.

    Attributes:
        db_name -- the name of the SQLite database file to connect to.
        con -- the sqlite3 object representing the connection to the database.
    
    Methods:
        __init__
        open_db
        close_db
        search_address
        enter_address
        remove_address
    """

    def __init__(self, db_name):
        """
        Initialise a new instance of SqliteConnector.
        """
        self.db_name = db_name
        self.con = self.open_db()
        self.con.row_factory = Row

    def open_db(self):
        """
        Opens a connection to the SQLite3 database file pointed to by
        the db_name attribute.
        """
        application_path = os.path.dirname(os.path.realpath(__file__))
        return sqlite3.connect(
            application_path
            + os.path.sep
            + "db"
            + os.path.sep
            + self.db_name
        )

    def close_db(self):
        """
        Closes the connection to the SQLite3 database opened when the object
        of this class was instantiated.
        """
        self.con.close()

    def search_address(self, first_name: str, last_name: str) -> List[Row]:
        """
        Returns a list of sqlite3 Row objects containing information on each
        row in the 'address' table with a matching first_name and last_name field.

        Arguments:
            first_name -- the first name of the client whose address to search for.
            last_name -- the last name of the client whose address to search for.
        """
        cur = self.con.cursor()
        result = cur.execute(
            """
            select
                *
            from
                address
            where
                first_name=?
                and last_name=?
            """,
            (
                first_name,
                last_name
            )
        )
        return list(result)
    
    def enter_address(self, row: Tuple[str]) -> None:
        """
        Enters a new row into the address table.
        
        Arguments:
            row -- a tuple containing the data that will fill the new row.
        """
        cur = self.con.cursor()
        cur.execute(
            """
            insert or ignore into 
                address
            values
                (?,?,?,?,?,?)
            """,
            row
        )
        self.con.commit()

    def remove_address(self, row: Tuple[str]) -> None:
        """
        Removes a row from the address table, returns a dict containing the success
        state of the operation.

        Arguments:
            row -- the row of data to remove.
        """
        cur = self.con.cursor()
        cur.execute("select count(*) from address")
        row_count_pre = cur.fetchone()[0]

        cur.execute(
            """
            delete from
                address
            where
                first_name=?
                and last_name=?
                and address_line_1=?
                and address_line_2=?
                and city=?
                and post_code=?
            """,
            row
        )
        self.con.commit()

        cur.execute("select count(*) from address")
        row_count_post = cur.fetchone()[0]

        return not (row_count_pre == row_count_post)