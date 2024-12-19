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

from config import config
from core.logger import logger


class Database:
    def __init__(self):
        self.db_name = config.db_name
        self.setup_database()

    def setup_database(self):
        """Setup the database and create necessary tables."""
        try:
            with sqlite3.connect(self.db_name) as conn:
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
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Error setting up database: %s", e)

    def insert_photo(
        self,
        uuid,
        filename,
        exif_data,
        created_time,
        modified_time,
        source_path,
        dest_path,
    ):
        """Insert a new photo record into the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO photos (
                        uuid, filename, exif_data, created_time, modified_time,
                        source_file_path, destination_file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        uuid,
                        filename,
                        exif_data,
                        created_time,
                        modified_time,
                        source_path,
                        dest_path,
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error("Error inserting photo record: %s", e)
            return False

    def insert_video(
        self,
        uuid,
        filename,
        exif_data,
        created_time,
        modified_time,
        source_path,
        dest_path,
    ):
        """Insert a new video record into the database."""
        return self.insert_photo(
            uuid, filename, "", created_time, modified_time, source_path, dest_path
        )


db = Database()
