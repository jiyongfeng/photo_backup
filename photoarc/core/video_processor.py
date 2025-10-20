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
import sqlite3
import time
import uuid
from typing import Optional

from core.database import db
from core.logger import logger

from config import config
from core.utils import (
    build_destination_path,
    get_date_from_filename,
    get_file_creation_time,
    is_same_file,
)


class VideoProcessor:
    """
    Video processing class that handles:
    - Video file discovery and copying
    - Creation time determination from filename or file metadata
    - File naming and organization
    - Database recording
    - Resume capability for interrupted processing
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
        self.processed_files = set()  # Track processed files to support resume

    def process_videos(self) -> None:
        """Process all videos in the source directory."""
        logger.info("Starting video processing in directory: %s", self.source_dir)
        self.file_count = 0
        self.copy_count = 0
        self.skip_count = 0
        self.error_count = 0

        # Load previously processed files for resume capability
        self._load_processed_files()

        # Process each subdirectory
        for root, dirs, files in os.walk(self.source_dir):
            logger.info("Processing directory: %s", root)
            for file in files:
                if file.lower().endswith(self.supported_types):
                    file_path = os.path.join(root, file)

                    # Skip if already processed (for resume capability)
                    if file_path in self.processed_files:
                        logger.debug("Skipping already processed file: %s", file_path)
                        self.skip_count += 1
                        self.file_count += 1
                        continue

                    try:
                        result = self._process_single_video(root, file)
                        self.file_count += 1
                        if result == "skipped":
                            self.skip_count += 1
                        elif result == "copied":
                            self.copy_count += 1
                            # Add to processed files
                            self.processed_files.add(file_path)
                        else:
                            self.error_count += 1
                    except (OSError, IOError, sqlite3.Error) as e:
                        self.error_count += 1
                        logger.error("Error processing video %s: %s", file, str(e))
            logger.info("Completed processing directory: %s", root)

        logger.info(
            "Video process completed. Total videos: %d, Copied: %d, Skipped: %d, Errors: %d",
            self.file_count,
            self.copy_count,
            self.skip_count,
            self.error_count,
        )

    def _load_processed_files(self) -> None:
        """Load list of already processed files from database."""
        try:
            processed = db.get_processed_files(self.source_dir)
            self.processed_files = {row[0] for row in processed}  # source_file_path
            logger.info("Loaded %d previously processed files", len(self.processed_files))
        except Exception as e:
            logger.error("Error loading processed files: %s", e)
            self.processed_files = set()

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
                if is_same_file(file_path, full_dest_path):
                    logger.info(
                        "File %s already exists with same content, skipping...",
                        full_dest_path,
                    )
                    return "skipped"

                if not config.video_overwrite_existing_rule:
                    # Generate unique filename with counter format
                    base_name, ext = os.path.splitext(dest_filename)
                    counter = 1
                    while os.path.exists(full_dest_path):
                        new_filename = f"{base_name}_{counter:03d}{ext}"
                        full_dest_path = os.path.join(self.dest_dir, dest_path, new_filename)
                        counter += 1

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)

            # Copy file and record in database
            return self._copy_and_record_file(file_path, full_dest_path, created_time)

        except (OSError, IOError, sqlite3.Error) as e:
            logger.error("Error processing file %s: %s", file_path, e)
            return "error"

    def _get_video_creation_time(self, file_path: str) -> Optional[str]:
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
            # Get file information
            file_size = None
            try:
                file_size = os.path.getsize(source_path)
            except OSError:
                pass

            shutil.copy2(source_path, dest_path)

            if db.insert_photo(  # 使用相同的数据库表
                str(uuid.uuid4()),
                os.path.basename(source_path),
                None,  # 视频没有 EXIF 数据
                created_time,
                time.ctime(os.path.getmtime(source_path)),
                source_path,
                dest_path,
                os.path.splitext(source_path)[1].lower(),
                file_size,
                None,  # width
                None,  # height
                "video"
            ):
                logger.info("Copied %s to %s", source_path, dest_path)
                return "copied"

            return "error"

        except (OSError, IOError, sqlite3.Error) as e:
            logger.error("Error copying file %s: %s", source_path, e)
            return "error"