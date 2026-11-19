from modules.common.database import get_db_connection

connection = get_db_connection()

if connection:
    print("Database connection test successful!")
    connection.close()
else:
    print("Database connection failed.")