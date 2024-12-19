#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 13:31:35
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-19 16:31:13
* @Description  : photo processor
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import os
import shutil
import time
import uuid

from PIL import Image
from PIL.ExifTags import TAGS

from config import config
from core.database import db
from core.logger import logger
from core.utils import (
    build_destination_path,
    generate_unique_filename,
    get_date_from_filename,
    get_file_creation_time,
    is_same_file,
)


class PhotoProcessor:
    """
    Photo processing class that handles:
    - Photo file discovery and copying
    - EXIF data extraction
    - Creation time determination
    - File naming and organization
    - Database recording
    """

    def __init__(self):
        """Initialize the photo processor with configuration settings."""
        self.source_dir = config.image_source_dir
        self.dest_dir = config.image_destination_dir
        self.supported_types = config.supported_image_types
        self.file_count = 0
        self.copy_count = 0
        self.skip_count = 0
        self.error_count = 0

    def process_photos(self):
        """Process all photos in the source directory."""
        self.file_count = 0
        self.skip_count = 0
        self.copy_count = 0
        self.error_count = 0
        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if file.lower().endswith(self.supported_types):
                    try:
                        result = self._process_single_photo(root, file)
                        self.file_count += 1
                        if result == "skipped":
                            self.skip_count += 1
                        elif result == "copied":
                            self.copy_count += 1
                        else:
                            self.error_count += 1
                    except Exception as e:
                        self.error_count += 1
                        logger.error("Error processing file %s: %s", file, str(e))

        logger.info(
            "Image process completed. Total files: %d, Copied: %d, Skipped: %d, Errors: %d",
            self.file_count,
            self.copy_count,
            self.skip_count,
            self.error_count,
        )

    def _process_single_photo(self, root: str, filename: str) -> str:
        """Process a single photo file."""
        file_path = os.path.join(root, filename)

        try:
            # Get photo creation time
            created_time = self._get_photo_creation_time(file_path)
            if not created_time:
                logger.error("Could not determine creation time for %s", file_path)
                return "error"

            # Build destination path
            dest_path, dest_filename = build_destination_path(
                created_time,
                filename,
                config.image_destination_path_format,
                config.image_destination_filename_format,
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

                if not config.image_overwrite_existing_rule:
                    full_dest_path = generate_unique_filename(
                        self.dest_dir, dest_path, dest_filename
                    )

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)

            # Copy file and record in database
            return self._copy_and_record_file(file_path, full_dest_path, created_time)

        except (OSError, IOError) as e:
            logger.error("Error processing file %s: %s", file_path, e)
            return "error"

    def _get_photo_creation_time(self, file_path: str) -> str:
        """Get photo creation time from EXIF data or filename."""
        try:
            with Image.open(file_path) as img:
                exif_data = self._get_exif_data(img)
                if exif_data and "DateTimeOriginal" in exif_data:
                    date_time = exif_data["DateTimeOriginal"].replace("\x00", "")
                    return self._convert_to_iso_format(date_time)

            # Try to get date from filename
            created_time = get_date_from_filename(os.path.basename(file_path))
            if created_time:
                return created_time

            # Fall back to file creation time
            return get_file_creation_time(file_path)

        except Exception as e:
            logger.error("Error getting creation time for %s: %s", file_path, e)
            return None

    def _get_exif_data(self, image) -> dict:
        """Extract EXIF data from image."""
        try:
            exif_data = image.getexif()
            if exif_data:
                return {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            return None
        except Exception as e:
            logger.error("Error extracting EXIF data: %s", e)
            return None

    def _convert_to_iso_format(self, date_time_str: str) -> str:
        """Convert date time string to ISO format."""
        try:
            date_part, time_part = date_time_str.split(" ")
            date_part = date_part.replace(":", "-")
            return f"{date_part}T{time_part}"
        except ValueError as e:
            logger.error("Error converting date time: %s", e)
            return None

    def _copy_and_record_file(
        self, source_path: str, dest_path: str, created_time: str
    ) -> str:
        """Copy file and record in database."""
        try:
            with Image.open(source_path) as img:
                exif_data = self._get_exif_data(img)
                shutil.copy2(source_path, dest_path)

                if db.insert_photo(
                    str(uuid.uuid4()),
                    os.path.basename(source_path),
                    str(exif_data),
                    created_time,
                    time.ctime(os.path.getmtime(source_path)),
                    source_path,
                    dest_path,
                ):
                    logger.info("Copied %s to %s", source_path, dest_path)
                    return "copied"

            return "error"

        except Exception as e:
            logger.error("Error copying file %s: %s", source_path, e)
            return "error"
