
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Sanika@123",
    "database": "studymate_db",
    "port": 33006
}


def get_db_connection():
    """
    Creates and returns a MySQL database connection.
    Returns None if the connection fails.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            print("MySQL database connected successfully!")
            return connection

    except Error as error:
        print(f"MySQL connection error: {error}")

    return None
