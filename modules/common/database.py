
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "studymate_db"),
    "port": int(os.getenv("DB_PORT", "33006")),
}

# Enable certificate verification for TiDB Cloud
if DB_CONFIG["host"] != "localhost":
    DB_CONFIG.update({
        "ssl_ca": os.getenv("DB_SSL_CA", "/etc/secrets/tidb-ca.pem"),
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
        "use_pure": True,
    })


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
