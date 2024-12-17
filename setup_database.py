import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_database(db_name):
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY,
                uuid TEXT,
                filename TEXT,
                exif_data TEXT,
                created_time TEXT,
                modified_time TEXT,
                source_file_path TEXT,
                destination_file_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY,
                uuid TEXT,
                filename TEXT,
                md5_hash TEXT,
                created_time TEXT,
                modified_time TEXT,
                source_file_path TEXT,
                destination_file_path TEXT
            )
        """)
        conn.commit()
        logger.info(f"Database {db_name} setup completed.")
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
    finally:
        conn.close()
