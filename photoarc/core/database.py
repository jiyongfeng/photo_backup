#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 13:30:51
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-19 14:28:32
* @Description  : database handler
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import sqlite3

from photoarc.config import config
from photoarc.core.logger import logger


class Database:
    def __init__(self):
        self.db_name = config.db_name
        self.setup_database()

    def setup_database(self) -> None:
        """Setup the database and create necessary tables."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # Enhanced photos table with better indexing and additional fields
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS photos (
                        id INTEGER PRIMARY KEY,
                        uuid TEXT UNIQUE,
                        filename TEXT,
                        file_extension TEXT,
                        exif_data TEXT,
                        created_time TEXT,
                        modified_time TEXT,
                        file_size INTEGER,
                        width INTEGER,
                        height INTEGER,
                        source_file_path TEXT,
                        destination_file_path TEXT,
                        media_type TEXT,  -- 'image' or 'video'
                        processing_timestamp TEXT
                    )
                """)

                # Create indexes for better query performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_time
                    ON photos(created_time)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_media_type
                    ON photos(media_type)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_source_path
                    ON photos(source_file_path)
                """)

                conn.commit()
        except sqlite3.Error as e:
            logger.error("Error setting up database: %s", e)

    def insert_photo(
        self,
        uuid: str,
        filename: str,
        exif_data: str | None,
        created_time: str,
        modified_time: str,
        source_path: str,
        dest_path: str,
        file_extension: str | None = None,
        file_size: int | None = None,
        width: int | None = None,
        height: int | None = None,
        media_type: str = "image"
    ) -> bool:
        """Insert a new photo/video record into the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO photos (
                        uuid, filename, file_extension, exif_data, created_time, modified_time,
                        file_size, width, height, source_file_path, destination_file_path,
                        media_type, processing_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                    (
                        uuid,
                        filename,
                        file_extension,
                        exif_data,
                        created_time,
                        modified_time,
                        file_size,
                        width,
                        height,
                        source_path,
                        dest_path,
                        media_type
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error("Error inserting photo record: %s", e)
            return False

    def insert_video(
        self,
        uuid: str,
        filename: str,
        exif_data: str | None,
        created_time: str,
        modified_time: str,
        source_path: str,
        dest_path: str,
        file_extension: str | None = None,
        file_size: int | None = None,
        width: int | None = None,
        height: int | None = None
    ) -> bool:
        """Insert a new video record into the database."""
        return self.insert_photo(
            uuid, filename, exif_data, created_time, modified_time,
            source_path, dest_path, file_extension, file_size, width, height, "video"
        )

    def get_processed_files(self, source_dir: str) -> list[tuple[str, str]]:
        """Get list of already processed files from a source directory."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT source_file_path, destination_file_path FROM photos WHERE source_file_path LIKE ?",
                    (f"{source_dir}%",)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error("Error retrieving processed files: %s", e)
            return []

    def is_file_processed(self, source_path: str) -> bool:
        """Check if a file has already been processed."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM photos WHERE source_file_path = ?",
                    (source_path,)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error as e:
            logger.error("Error checking if file is processed: %s", e)
            return False


db = Database()