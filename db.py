import sqlite3
import os


class SqliteConnector():
    def open_db(self):
        application_path = os.path.dirname(os.path.realpath(__file__))
        return sqlite3.connect(
            application_path
            + os.path.sep
            + "db"
            + os.path.sep
            + self.db_name
        )

    def close_db(self):
        self.con.close()

    def search_address(self, first_name: str, last_name: str) -> list:
        cur = self.con.cursor()
        result = cur.execute(
            """
            select
                *
            from
                addresses
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
    
    def enter_address(self, row: tuple) -> None:
        cur = self.con.cursor()
        cur.execute(
            """
            insert or ignore into 
                addresses 
            values
                (?,?,?,?,?,?)
            """,
            row
        )
        self.con.commit()

    def remove_address(self, row: tuple) -> None:
        cur = self.con.cursor()
        cur.execute("select count(*) from addresses")
        row_count_pre = cur.fetchone()[0]

        cur.execute(
            """
            delete from
                addresses
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

        cur.execute("select count(*) from addresses")
        row_count_post = cur.fetchone()[0]

        return False if row_count_pre == row_count_post else True

    def __init__(self, db_name):
        self.db_name = db_name
        self.con = self.open_db()
        self.con.row_factory = sqlite3.Row