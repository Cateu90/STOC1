from contextlib import contextmanager
import mysql.connector
from typing import Generator
from data.db import get_db

@contextmanager
def get_db_connection(user_email: str = None) -> Generator[mysql.connector.MySQLConnection, None, None]:
    db = None
    try:
        db = get_db(user_email=user_email)
        yield db
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

@contextmanager
def get_db_cursor(user_email: str = None, dictionary: bool = True) -> Generator:
    with get_db_connection(user_email) as db:
        cursor = db.cursor(dictionary=dictionary)
        try:
            yield cursor, db
        finally:
            cursor.close()


