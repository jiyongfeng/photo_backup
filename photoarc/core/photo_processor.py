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
from datetime import datetime
from typing import Any

from photoarc.config import config
from photoarc.core.database import db
from photoarc.core.logger import logger
from photoarc.core.utils import (
    build_destination_path,
    generate_unique_filename_with_content_check,
    get_datetime_from_filename,
    get_file_modification_time,
    is_file_already_processed_by_path,
    is_same_file,
)

# Check PIL availability for image dimension extraction only
try:
    from PIL import Image
    pil_available = True
except ImportError:
    pil_available = False
    Image = None
    logger.warning("PIL not available, image dimensions will not be extracted")

# Check exifread availability for EXIF data extraction
exifread_available = False
exifread_module = None

try:
    import exifread as exifread_module
    exifread_available = True
except ImportError:
    logger.warning("exifread not available, EXIF data extraction will be disabled")


class PhotoProcessor:
    """
    Photo processing class that handles:
    - Photo file discovery and copying
    - EXIF data extraction
    - modification time determination
    - File naming and organization
    - Database recording
    - Resume capability for interrupted processing
    """

    def __init__(self):
        """Initialize the photo processor with configuration settings."""
        self.source_dir = config.image_source_dir
        self.dest_dir = config.image_destination_dir
        self.supported_types = config.supported_image_types
        self.exclude_dirs = config.exclude_directories  # 添加排除目录列表
        self.file_count = 0
        self.copy_count = 0
        self.skip_count = 0
        self.error_count = 0
        self.processed_files = set()  # Track processed files to support resume

    def _is_excluded_directory(self, dir_path: str) -> bool:
        """Check if a directory should be excluded from processing."""
        # Convert to relative path from source directory
        try:
            rel_path = os.path.relpath(dir_path, self.source_dir)
            # Handle the case where rel_path is '.' (source directory itself)
            if rel_path == ".":
                return False

            # Check if any exclude pattern matches
            for exclude_dir in self.exclude_dirs:
                # Normalize paths for comparison
                exclude_dir_normalized = os.path.normpath(exclude_dir)
                rel_path_normalized = os.path.normpath(rel_path)

                # Check for exact match or parent directory match
                if (
                    rel_path_normalized == exclude_dir_normalized
                    or rel_path_normalized.startswith(exclude_dir_normalized + os.sep)
                    or exclude_dir_normalized.startswith(rel_path_normalized + os.sep)
                ):
                    return True

            return False
        except ValueError:
            # This can happen on different drives on Windows
            return False

    def process_photos(self) -> None:
        """Process all photos in the source directory."""
        logger.info("Starting photo processing in directory: %s", self.source_dir)
        logger.info("Excluded directories: %s", self.exclude_dirs)
        self.file_count = 0
        self.skip_count = 0
        self.copy_count = 0
        self.error_count = 0

        # Load previously processed files for resume capability
        self._load_processed_files()

        # Process each subdirectory
        for root, dirs, files in os.walk(self.source_dir):
            # Check if current directory should be excluded
            if self._is_excluded_directory(root):
                logger.info("Skipping excluded directory: %s", root)
                dirs[:] = []  # Clear dirs to prevent walking into subdirectories
                continue

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
                        result = self._process_single_photo(root, file)
                        self.file_count += 1
                        if result == "skipped":
                            self.skip_count += 1
                        elif result == "copied":
                            self.copy_count += 1
                            # Add to processed files
                            self.processed_files.add(file_path)
                        else:
                            self.error_count += 1
                    except Exception as e:
                        self.error_count += 1
                        logger.error("Error processing file %s: %s", file, str(e))
            logger.info("Completed processing directory: %s", root)

        logger.info(
            "Image process completed. Total files: %d, Copied: %d, Skipped: %d, Errors: %d",
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
            logger.info(
                "Loaded %d previously processed files", len(self.processed_files)
            )
        except Exception as e:
            logger.error("Error loading processed files: %s", e)
            self.processed_files = set()

    def _process_single_photo(self, root: str, filename: str) -> str:
        """Process a single photo file."""
        file_path = os.path.join(root, filename)

        try:
            # Get photo modification time
            modification_time = self._get_photo_modification_time(file_path)
            if not modification_time:
                logger.error("Could not determine modification time for %s", file_path)
                return "error"

            # Build destination path
            dest_path, dest_filename = build_destination_path(
                modification_time,
                filename,
                config.image_destination_path_format,
                config.image_destination_filename_format,
            )
            full_dest_path = os.path.join(self.dest_dir, dest_path, dest_filename)

            # Check if file is already processed by checking if destination file exists
            # This is more reliable than checking database as it directly verifies file existence
            if is_file_already_processed_by_path(full_dest_path):
                # Check if it's the same file content
                if is_same_file(file_path, full_dest_path):
                    logger.info(
                        "File %s already exists with same content, skipping...",
                        full_dest_path,
                    )
                    return "skipped"
                else:
                    # Different content, need to generate unique filename
                    if not config.image_overwrite_existing_rule:
                        # Generate unique filename with content check
                        full_dest_path = generate_unique_filename_with_content_check(
                            self.dest_dir, dest_path, dest_filename, file_path
                        )
                        # After generating a new path, we need to check if this new path also exists
                        # with the same content to avoid unnecessary copies
                        if is_file_already_processed_by_path(full_dest_path):
                            if is_same_file(file_path, full_dest_path):
                                logger.info(
                                    "File %s already exists with same content, skipping...",
                                    full_dest_path,
                                )
                                return "skipped"
                    else:
                        # Overwrite existing file
                        logger.info(
                            "Overwriting existing file %s with different content",
                            full_dest_path,
                        )

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)

            # Copy file and record in database
            return self._copy_and_record_file(
                file_path, full_dest_path, modification_time
            )

        except (OSError, IOError) as e:
            logger.error("Error processing file %s: %s", file_path, e)
            return "error"

    def _get_photo_modification_time(self, file_path: str) -> str | None:
        """Get photo modification time, prioritizing EXIF data over filename and modification time."""
        if not exifread_available:
            # Fall back to filename/modification time if exifread is not available
            logger.info("exifread not available, using filename/modification time for %s", file_path)
            filename_time = get_datetime_from_filename(os.path.basename(file_path))
            mod_time = get_file_modification_time(file_path)
            return self._get_earliest_time(None, filename_time, mod_time)

        try:
            # Get EXIF data using exifread
            exif_data = self._get_exif_data(file_path)

            # Priority 1: Try to get EXIF time (永远优先从EXIF读取)
            if exif_data:
                exif_time = self._extract_exif_datetime(exif_data)
                if exif_time:
                    logger.info("Using EXIF time for %s: %s", file_path, exif_time)
                    return exif_time

            # Priority 2: Only if EXIF not available, use filename and modification time (最早时间)
            logger.info(
                "No EXIF time found for %s, falling back to filename/modification time",
                file_path,
            )
            filename_time = get_datetime_from_filename(os.path.basename(file_path))
            mod_time = get_file_modification_time(file_path)

            # Return the earliest time between filename and modification time
            return self._get_earliest_time(None, filename_time, mod_time)

        except Exception as e:
            logger.error("Error getting modification time for %s: %s", file_path, e)
            # Fall back to file modification time
            return get_file_modification_time(file_path)

    def _extract_exif_datetime(self, exif_data: dict[str, Any]) -> str | None:
        """Extract datetime from EXIF data, trying multiple fields in priority order."""
        # Priority order for EXIF datetime fields (using exifread tag names)
        exif_datetime_fields = [
            "EXIF DateTimeOriginal",  # 拍摄时间 (最优先)
            "EXIF DateTimeDigitized",  # 数字化时间
            "Image DateTime",  # 修改时间 (最后选择)
        ]

        for field in exif_datetime_fields:
            if field in exif_data:
                date_time = str(exif_data[field]).replace("\x00", "").strip()
                if date_time:
                    converted_time = self._convert_to_iso_format(date_time)
                    if converted_time:
                        logger.info(
                            "Found EXIF %s: %s -> %s", field, date_time, converted_time
                        )
                        return converted_time

        return None

    def _get_earliest_time(
        self, exif_time: str | None, filename_time: str | None, mod_time: str | None
    ) -> str | None:
        """Get the earliest time among EXIF, filename, and modification times."""
        times = [t for t in [exif_time, filename_time, mod_time] if t is not None]
        if not times:
            return None

        # Special case: if filename_time is midnight (00:00:00), it might be inaccurate
        # In this case, prefer EXIF time or modification time if available
        if filename_time and filename_time.endswith("T00:00:00"):
            logger.info(
                "Filename time is midnight, preferring EXIF or modification time"
            )
            non_filename_times = [t for t in [exif_time, mod_time] if t is not None]
            if non_filename_times:
                times = non_filename_times

        # Convert to datetime objects for comparison
        datetime_objects = []
        for time_str in times:
            try:
                datetime_objects.append(datetime.fromisoformat(time_str))
            except ValueError:
                logger.warning("Invalid time format: %s", time_str)

        if not datetime_objects:
            return None

        # Return the earliest time in ISO format
        earliest = min(datetime_objects)
        return earliest.isoformat()

    def _get_exif_data(self, file_path: str) -> dict[str, Any] | None:
        """Extract EXIF data from image file using exifread library."""
        if not exifread_available or exifread_module is None:
            logger.debug("exifread not available, cannot extract EXIF data")
            return None
            
        try:
            with open(file_path, 'rb') as f:
                tags = exifread_module.process_file(f)

                if not tags:
                    logger.info("图片没有EXIF数据")
                    return None

                # Convert exifread tags to a simple dictionary
                exif_dict = {}
                for tag, value in tags.items():
                    # Skip thumbnail data and maker notes as they are too large
                    if tag not in (
                        "JPEGThumbnail",
                        "TIFFThumbnail",
                        "Filename",
                        "EXIF MakerNote",
                    ):
                        exif_dict[tag] = str(value)

                logger.debug("=== 完整EXIF数据 ===")
                for key, value in exif_dict.items():
                    logger.debug("EXIF %s: %s", key, value)
                logger.debug("=== EXIF数据结束 ===")

                return exif_dict

        except Exception as e:
            logger.error("Error extracting EXIF data from %s: %s", file_path, e)
            return None

    def _convert_to_iso_format(self, date_time_str: str) -> str | None:
        """Convert date time string to ISO format."""
        try:
            date_part, time_part = date_time_str.split(" ")
            date_part = date_part.replace(":", "-")
            return f"{date_part}T{time_part}"
        except ValueError as e:
            logger.error("Error converting date time: %s", e)
            return None

    def _copy_and_record_file(
        self, source_path: str, dest_path: str, modification: str
    ) -> str:
        """Copy file and record in database."""
        try:
            exif_data = None
            file_size = None
            width = None
            height = None

            # Get file information
            try:
                file_size = os.path.getsize(source_path)
            except OSError:
                pass

            # Get image dimensions using PIL if available
            if pil_available and Image is not None:
                try:
                    with Image.open(source_path) as img:
                        width, height = img.size
                except Exception as e:
                    logger.warning("Failed to get image dimensions for %s: %s", source_path, e)
            
            # Get EXIF data using exifread
            exif_data = self._get_exif_data(source_path)

            shutil.copy2(source_path, dest_path)

            if db.insert_photo(
                str(uuid.uuid4()),
                os.path.basename(source_path),
                str(exif_data) if exif_data else None,
                modification,
                time.ctime(os.path.getmtime(source_path)),
                source_path,
                dest_path,
                os.path.splitext(source_path)[1].lower(),
                file_size,
                width,
                height,
                "image",
            ):
                logger.info("Copied %s to %s", source_path, dest_path)
                return "copied"

            return "error"

        except Exception as e:
            logger.error("Error copying file %s: %s", source_path, e)
            return "error"
