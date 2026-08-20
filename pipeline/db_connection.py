# Database connection module providing safe MySQL connections and transaction management
# Uses pymysql with dictionary cursor support for structured query execution

import pymysql
import os
from contextlib import contextmanager

# Database configuration settings with environment variable fallbacks
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "consultbae_db"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False
}

# Context manager providing safe database connection lifecycle and automatic rollback on failure
@contextmanager
def get_db_connection():
    # Establish connection with the configured MySQL instance
    connection = pymysql.connect(**DB_CONFIG)
    try:
        # Yield the active connection to the calling context
        yield connection
        # Commit transaction on successful block completion
        connection.commit()
    except Exception as error:
        # Roll back transaction if any error occurs during execution
        connection.rollback()
        raise error
    finally:
        # Close connection to avoid connection leaks in pool
        connection.close()
