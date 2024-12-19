#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 13:41:57
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-19 16:42:12
* @Description  : utils
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import os
import re
import hashlib
from datetime import datetime
from typing import Optional, Tuple

from core.logger import logger


def get_file_md5(file_path: str) -> Optional[str]:
    """
    Calculate MD5 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        str: MD5 hash of the file, or None if error occurs
    """
    try:
        with open(file_path, "rb") as f:
            md5_hash = hashlib.md5()
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except IOError as e:
        logger.error("Error calculating MD5 for %s: %s", file_path, e)
        return None


def is_same_file(source_path: str, dest_path: str) -> bool:
    """
    Check if two files have the same content using MD5.

    Args:
        source_path: Path to source file
        dest_path: Path to destination file

    Returns:
        bool: True if files have same content, False otherwise
    """
    source_md5 = get_file_md5(source_path)
    dest_md5 = get_file_md5(dest_path)
    return source_md5 and dest_md5 and source_md5 == dest_md5


def get_date_from_filename(filename: str) -> Optional[str]:
    """
    Extract date from filename using various patterns.

    Args:
        filename: Name of the file

    Returns:
        str: ISO format date string, or None if no date found
    """
    patterns = [
        r"(19\d{2}|20\d{2})([ ._-]*)(0[1-9]|1[0-2])([ ._-]*)(0[1-9]|[12][0-9]|3[01])([ ._-]*)(20|21|22|23|[0-1]\d)([ ._-]*)([0-5]\d)([ ._-]*)([0-5]\d)",  # 20241230 183045
        r"(19\d{2}|20\d{2})([ ._-]*)(0[1-9]|1[0-2])([ ._-]*)(0[1-9]|[12][0-9]|3[01])",  # 20241230
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            if len(match.groups()) == 11:
                year = match.group(1)
                month = match.group(3)
                day = match.group(5)
                hour = match.group(7)
                minute = match.group(9)
                second = match.group(11)
                filename_time = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
                logger.debug(
                    f"Found date and time in filename {filename}: {filename_time}"
                )
                return filename_time
            elif len(match.groups()) == 6:
                year = match.group(1)
                month = match.group(3)
                day = match.group(5)
                filename_time = f"{year}-{month}-{day}T00:00:00"
                logger.debug(f"Found date in filename {filename}: {filename_time}")
                return filename_time
            else:
                logger.error("Unexpected number of groups in match: %s", match.groups())
                return None
        else:
            logger.info("No date or datetime found in filename: %s", filename)
            return None


def get_file_creation_time(file_path: str) -> Optional[str]:
    """
    Get file creation time from metadata.

    Args:
        file_path: Path to the file

    Returns:
        str: ISO format date string, or None if error occurs
    """
    try:
        creation_time = datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
        logger.info(f"Getting file creation time for {file_path}: {creation_time}")
        return creation_time
    except Exception as e:
        logger.error("Error getting file creation time for %s: %s", file_path, e)
        return None


def build_destination_path(
    created_time: str, original_filename: str, path_format: str, filename_format: str
) -> Tuple[str, str]:
    """
    Build destination path and filename based on creation time.

    Args:
        created_time: ISO format date string
        original_filename: Original file name
        path_format: Format string for path
        filename_format: Format string for filename

    Returns:
        tuple: (destination_path, destination_filename)
    """
    dt = datetime.fromisoformat(created_time)

    # Format path
    path = path_format.format(
        year=str(dt.year),
        month=str(dt.month).zfill(2),
        day=str(dt.day).zfill(2),
    )

    # Format filename
    name, ext = os.path.splitext(original_filename)
    filename = filename_format.format(
        originalfile=name,
        year=str(dt.year),
        month=str(dt.month).zfill(2),
        day=str(dt.day).zfill(2),
        hour=str(dt.hour).zfill(2),
        minute=str(dt.minute).zfill(2),
        second=str(dt.second).zfill(2),
        extension=ext[1:],
    )

    return path, filename


def generate_unique_filename(base_dir: str, dest_path: str, filename: str) -> str:
    """
    Generate a unique filename by adding a counter.

    Args:
        base_dir: Base directory
        dest_path: Destination path
        filename: Original filename

    Returns:
        str: Full path to unique filename
    """
    base_name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_name = f"{base_name}({counter}){ext}"
        full_path = os.path.join(base_dir, dest_path, new_name)
        if not os.path.exists(full_path):
            return full_path
        counter += 1


def validate_directory(dir_path: str, dir_type: str) -> bool:
    """
    Validate directory existence and permissions.

    Args:
        dir_path: Path to directory
        dir_type: Type of directory (for logging)

    Returns:
        bool: True if directory is valid, False otherwise
    """
    if not os.path.exists(dir_path):
        logger.error("%s path does not exist: %s", dir_type, dir_path)
        return False

    if not os.path.isdir(dir_path):
        logger.error("%s path is not a directory: %s", dir_type, dir_path)
        return False

    return True


def create_directory(dir_path: str) -> bool:
    """
    Create directory if it doesn't exist.

    Args:
        dir_path: Path to directory

    Returns:
        bool: True if directory exists or was created, False on error
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            logger.info("Directory created: %s", dir_path)
            return True
        except OSError as e:
            logger.error("Failed to create directory: %s", e)
            return False
    return True
