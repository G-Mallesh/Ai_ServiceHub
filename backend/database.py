import mysql.connector
from mysql.connector import Error

from backend.config import Config


def get_db_connection():
    """
    Create a MySQL connection using Render environment variables.
    """

    if not Config.MYSQL_HOST:
        raise RuntimeError("DB_HOST environment variable is missing")

    if not Config.MYSQL_USER:
        raise RuntimeError("DB_USER environment variable is missing")

    if not Config.MYSQL_PASSWORD:
        raise RuntimeError("DB_PASSWORD environment variable is missing")

    if not Config.MYSQL_DATABASE:
        raise RuntimeError("DB_NAME environment variable is missing")

    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        ssl_disabled=False,
        connection_timeout=15
    )


def query(
    sql,
    params=None,
    fetch=False,
    fetchone=False
):
    """
    Execute a MySQL query.
    """

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            sql,
            params or ()
        )

        if fetchone:

            result = cursor.fetchone()

        elif fetch:

            result = cursor.fetchall()

        else:

            connection.commit()

            result = cursor.lastrowid

        return result

    except Error:

        if connection:
            connection.rollback()

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()