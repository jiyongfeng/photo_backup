#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 13:40:50
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-19 16:34:15
* @Description  : video processor
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import os
import shutil
import time
import uuid
import sqlite3

from config import config
from core.logger import logger
from core.database import db
from core.utils import (
    is_same_file,
    get_date_from_filename,
    get_file_creation_time,
    build_destination_path,
    generate_unique_filename,
)


class VideoProcessor:
    """
    Video processing class that handles:
    - Video file discovery and copying
    - Creation time determination from filename or file metadata
    - File naming and organization
    - Database recording
    """

    def __init__(self):
        """Initialize the video processor with configuration settings."""
        self.source_dir = config.video_source_dir
        self.dest_dir = config.video_destination_dir
        self.supported_types = config.supported_video_types
        self.file_count = 0
        self.copy_count = 0
        self.skip_count = 0
        self.error_count = 0

    def process_videos(self):
        """Process all videos in the source directory."""

        self.file_count = 0
        self.copy_count = 0
        self.skip_count = 0
        self.error_count = 0
        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if file.lower().endswith(self.supported_types):
                    try:
                        result = self._process_single_video(root, file)
                        self.file_count += 1
                        if result == "skipped":
                            self.skip_count += 1
                        elif result == "copied":
                            self.copy_count += 1
                        else:
                            self.error_count += 1
                    except (OSError, IOError, sqlite3.Error) as e:
                        self.error_count += 1
                        logger.error("Error processing video %s: %s", file, str(e))

        logger.info(
            "Video process completed. Total videos: %d, Copyed: %d, Skipped: %d, Errors: %d",
            self.file_count,
            self.copy_count,
            self.skip_count,
            self.error_count,
        )

    def _process_single_video(self, root: str, filename: str) -> str:
        """Process a single video file."""
        file_path = os.path.join(root, filename)

        try:
            # Get video creation time
            created_time = self._get_video_creation_time(file_path)
            if not created_time:
                logger.error("Could not determine creation time for %s", file_path)
                return "error"

            # Build destination path
            dest_path, dest_filename = build_destination_path(
                created_time,
                filename,
                config.video_destination_path_format,
                config.video_destination_filename_format,
            )
            full_dest_path = os.path.join(self.dest_dir, dest_path, dest_filename)

            # Check for existing file
            if os.path.exists(full_dest_path):
                base, ext = os.path.splitext(full_dest_path)
                counter = 1
                while os.path.exists(full_dest_path):
                    if is_same_file(file_path, full_dest_path):
                        logger.info(
                            "File %s already exists with same content, skipping...",
                            full_dest_path,
                        )
                        return "skipped"
                    full_dest_path = f"{base}({counter}){ext}"
                    counter += 1

                if not config.overwrite_existing_rule:
                    full_dest_path = generate_unique_filename(
                        self.dest_dir, dest_path, dest_filename
                    )

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)

            # Copy file and record in database
            return self._copy_and_record_file(file_path, full_dest_path, created_time)

        except (OSError, IOError, sqlite3.Error) as e:
            logger.error("Error processing file %s: %s", file_path, e)
            return "error"

    def _get_video_creation_time(self, file_path: str) -> str:
        """Get video creation time from filename or file metadata."""
        # Try to get date from filename first
        created_time = get_date_from_filename(os.path.basename(file_path))
        if created_time:
            return created_time

        # Fall back to file creation time
        return get_file_creation_time(file_path)

    def _copy_and_record_file(
        self, source_path: str, dest_path: str, created_time: str
    ) -> str:
        """Copy file and record in database."""
        try:
            shutil.copy2(source_path, dest_path)

            if db.insert_photo(  # 使用相同的数据库表
                str(uuid.uuid4()),
                os.path.basename(source_path),
                None,  # 视频没有EXIF数据
                created_time,
                time.ctime(os.path.getmtime(source_path)),
                source_path,
                dest_path,
            ):
                logger.info("Copied %s to %s", source_path, dest_path)
                return "copied"

            return "error"

        except (OSError, IOError, sqlite3.Error) as e:
            logger.error("Error copying file %s: %s", source_path, e)
            return "error"
