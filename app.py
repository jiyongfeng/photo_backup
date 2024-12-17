#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-05-21 11:33:40
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-17 18:07:31
* @Description  : 实现自动将照片备份到指定目录并重新命名
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

from ast import pattern
import hashlib
from itertools import count
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler

import yaml
from PIL import Image
from PIL.ExifTags import TAGS
from setup_database import setup_database

# Set the working directory to the directory of the script
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

# Load configuration from YAML file
with open("configuration.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)
    sleep_time = config["task"]["sleep_time"]
    APP_VERSION = config["app"]["version"]

    # Copy rules
    destination_image_path_format = config["copy_rules"][
        "destination_image_path_format"
    ]
    destination_image_name_format = config["copy_rules"][
        "destination_image_name_format"
    ]
    destination_video_path_format = config["copy_rules"][
        "destination_video_path_format"
    ]
    destination_video_name_format = config["copy_rules"][
        "destination_video_name_format"
    ]
    overwrite_existing_rule = config["copy_rules"]["overwrite_existing_rule"]

    # Database configuration
    db_name = config["database"]["db_name"]

    # Source and destination directories
    source_image_dir = config["app"]["source_image_dir"]
    source_video_dir = config["app"]["source_video_dir"]
    destination_image_dir = config["app"]["destination_image_dir"]
    destination_video_dir = config["app"]["destination_video_dir"]

    # Define supported image file types from configuration
    SUPPORTED_IMAGE_TYPES = tuple(config["app"]["supported_image_types"])

    # Define supported video file types from configuration
    SUPPORTED_VIDEO_TYPES = tuple(config["app"]["supported_video_types"])

    # Logging configuration
    log_dir = config["logging"]["log_dir"]
    log_level = config["logging"]["log_level"]
    log_format = config["logging"]["log_format"]
    log_date_format = config["logging"]["log_date_format"]
    log_max_bytes = config["logging"]["log_max_bytes"]
    log_backup_count = config["logging"]["log_backup_count"]

# Ensure the logs directory exists
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(
    log_dir, f'app_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
)

handler = RotatingFileHandler(
    log_filename, maxBytes=log_max_bytes, backupCount=log_backup_count
)
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(log_level)  # Set the logging level
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())


def log_info(message):
    """
    Log an informational message.
    """
    logger.info(message)


def log_error(message):
    """
    Log an error message.
    """
    logger.error(message)


def log_warning(message):
    """
    Log a warning message.
    """
    logger.warning(message)


def log_debug(message):
    """
    Log a debug message.
    """
    logger.debug(message)


def log_critical(message):
    """
    Log a critical message.
    """
    logger.critical(message)


def validate_folder_path(folder_path):
    """
    check if the folder path is valid
    """
    if not os.path.isdir(folder_path):
        logger.error(f"{folder_path} is not a valid directory.")
        raise ValueError(f"{folder_path} is not a valid directory.")
    if not os.access(folder_path, os.W_OK):
        logger.error(f"Permission denied: {folder_path}")
        raise PermissionError(f"Permission denied: {folder_path}")
    return True


def generate_unique_filename(destination_path, base_name):
    """generate a unique filename"""
    unique_name = f"{base_name}"
    unique_path = os.path.join(destination_path, unique_name)
    if os.path.exists(unique_path):
        counter = 1
        while True:
            unique_name = (
                f"{base_name.split('.')[-2]}({counter}).{base_name.split('.')[-1]}"
            )
            unique_path = os.path.join(destination_path, unique_name)
            if not os.path.exists(unique_path):
                return unique_name
            counter += 1
    else:
        return unique_name


def get_md5(file_path):
    """计算文件的MD5哈希值"""
    with open(file_path, "rb") as file:
        md5_hash = hashlib.md5()
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def convert_to_iso_format(date_time_str):
    """Convert date time string from 'YYYY:MM:DD HH:MM:SS' to 'YYYY-MM-DDTHH:MM:SS'."""
    try:
        date_part, time_part = date_time_str.split(" ")
        date_part = date_part.replace(":", "-")  # Replace colons with dashes
        return f"{date_part}T{time_part}"  # Combine with 'T'
    except ValueError as e:
        logger.error(f"Error converting date time: {e}")
        return None


def get_exif_data(image):
    """Extracts detailed EXIF data from an image."""
    exif_data = image._getexif()
    if exif_data is not None:
        exif_info = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)  # Get the tag name or use the tag number
            exif_info[tag_name] = value  # Store the value in the dictionary
        return exif_info  # Return the complete EXIF information
    return None


def get_date_from_filename(filename):
    """Extracts the date from the file name and returns it in ISO format."""
    pattern1 = r"(\D*)(\d{4})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(\D*)"  # 20220101
    pattern2 = r"(\D*)(\d{4})-(0[1-9]|1[0-9])(0[1-9]|[12][0-9]|3[01])_([012][0-9])-([012345][0-9])-([012345][0-9])(\D*)"  # 2022-01-01_12-34-56
    pattern3 = r"(\D*)(\d{4})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])_(\d{6})(\D*)"  # 2022-01-01_123456
    pattern4 = r"(\D*)(\d{4})-(0[1-9]|1[0-9])-(0[1-9]|[12][0-9]|3[01])-(\d{2})-(\d{2})-(\d{2})(\D*)"  # 2022-01-01-12-34-56
    pattern5 = r"(\D*)(\d{8})_(\d{6})(\D*)"  # 20231122_123456
    pattern6 = (
        r"(\D*)(\d{4})-(0[1-9]|1[0-9])-(0[1-9]|[12][0-9]|3[01])(\D*)"  # 1982-11-22
    )
    pattern7 = r"(\D*)(\d{4})-(0[1-9]|1[0-9])-(0[1-9]|[12][0-9]|3[01])_(\d{6})(\D*)"  # 1982-11-22_121314

    match1 = re.search(pattern1, filename)
    match2 = re.search(pattern2, filename)
    match3 = re.search(pattern3, filename)
    match4 = re.search(pattern4, filename)
    match5 = re.search(pattern5, filename)
    match6 = re.search(pattern6, filename)
    match7 = re.search(pattern7, filename)

    log_debug(f"{filename}: {match1}")
    log_debug(f"{filename}: {match2}")
    log_debug(f"{filename}: {match3}")
    log_debug(f"{filename}: {match4}")
    log_debug(f"{filename}: {match5}")
    log_debug(f"{filename}: {match6}")
    log_debug(f"{filename}: {match7}")

    if match5:
        year = match5.group(2)[:4]
        month = match5.group(2)[4:6]
        day = match5.group(2)[6:8]
        hour = match5.group(3)[:2]
        minute = match5.group(3)[2:4]
        second = match5.group(3)[4:6]
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    elif match4:
        year = match4.group(2)
        month = match4.group(3)
        day = match4.group(4)
        hour = match4.group(5)
        minute = match4.group(6)
        second = match4.group(7)
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    elif match3:
        year = match3.group(2)
        month = match3.group(3)
        day = match3.group(4)
        hour = match3.group(5)[:2]
        minute = match3.group(5)[2:4]
        second = match3.group(5)[4:6]
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    elif match2:
        year = match2.group(2)
        month = match2.group(3)
        day = match2.group(4)
        return f"{year}-{month}-{day}T00:00:00"
    elif match1:
        year = match1.group(2)
        month = match1.group(3)
        day = match1.group(4)
        return f"{year}-{month}-{day}T00:00:00"
    log_debug(f"No match found for {filename}")
    return None


def copy_photos_with_exif(source_dir, destination_dir):
    """Copy photos from source directory to destination directory."""
    try:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith(SUPPORTED_IMAGE_TYPES):
                    file_path = os.path.join(root, file)

                    try:
                        with Image.open(file_path) as img:
                            exif_info = get_exif_data(img)
                            date_time_original = (
                                exif_info.get("DateTimeOriginal") if exif_info else None
                            )
                            if date_time_original:
                                # Sanitize the date string by removing null bytes
                                date_time_original = date_time_original.replace(
                                    "\x00", ""
                                )
                                created_time = convert_to_iso_format(date_time_original)
                            else:
                                created_time = get_date_from_filename(file)
                            if created_time is None:
                                datetime_from_fileinfo = os.path.getctime(file_path)
                                log_debug(
                                    f"datetime_from_fileinfo: {datetime_from_fileinfo}"
                                )
                                if datetime_from_fileinfo is None:
                                    log_error(
                                        f"Failed to get created time for {file_path}"
                                    )
                                    continue
                                created_time = datetime.fromtimestamp(
                                    datetime_from_fileinfo
                                ).isoformat()
                                # Parse the ISO date string
                            dt = datetime.fromisoformat(created_time)

                            year = str(dt.year)
                            month = str(dt.month).zfill(2)
                            day = str(dt.day).zfill(2)
                            hour = str(dt.hour).zfill(2)
                            minute = str(dt.minute).zfill(2)
                            second = str(dt.second).zfill(2)

                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        continue

                    # Prepare the destination path based on the configuration if not set, default to f"{year}/{month}/{day}
                    destination_path = (
                        destination_image_path_format.replace("{year}", year)
                        .replace("{month}", month)
                        .replace("{day}", day)
                        if destination_image_path_format
                        else f"{year}/{month}/{day}"
                    )

                    # Prepare the destination filename
                    originalfile, ext = os.path.splitext(file)
                    extension = ext[1:]
                    destination_filename = (
                        destination_image_name_format.replace(
                            "{originalfile}", originalfile
                        )
                        .replace("{year}", year)
                        .replace("{month}", month)
                        .replace("{day}", day)
                        .replace("{hour}", hour)
                        .replace("{minute}", minute)
                        .replace("{second}", second)
                        .replace("{extension}", extension)
                        if destination_image_name_format
                        else f"IMG_{year}{month}{day}_{originalfile}.{extension}"
                    )

                    # Construct the full destination path
                    full_destination_path = os.path.join(
                        destination_dir, destination_path, destination_filename
                    )

                    # check if file exists, due to the rule to overwrite or ignore
                    if os.path.exists(full_destination_path):
                        # Check if the MD5 hashes are the same
                        if get_md5(file_path) == get_md5(full_destination_path):
                            log_info(
                                f"File {full_destination_path} already exists with the same content, skipping..."
                            )
                            continue

                        # Generate a new filename if the content is different
                        base_name, extension = os.path.splitext(destination_filename)
                        new_full_destination_path = full_destination_path
                        counter = 1

                        # If overwrite rule is false, generate a new unique filename
                        while os.path.exists(new_full_destination_path):
                            if overwrite_existing_rule:
                                log_info(
                                    f"File {full_destination_path} already exists, overwriting..."
                                )
                                os.remove(full_destination_path)
                                break
                            else:
                                new_full_destination_path = os.path.join(
                                    destination_dir,
                                    destination_path,
                                    f"{base_name}({counter}){extension}",
                                )
                                counter += 1

                        full_destination_path = new_full_destination_path

                    # Ensure the destination directory exists
                    destination_dir_path = os.path.join(
                        destination_dir, destination_path
                    )
                    if not os.path.exists(destination_dir_path):
                        os.makedirs(destination_dir_path)

                    # Now proceed to copy the file
                    try:
                        shutil.copy2(file_path, full_destination_path)
                        # add to database
                        conn = sqlite3.connect(db_name)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO photos (uuid, filename, exif_data, created_time, modified_time, source_file_path, destination_file_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                str(uuid.uuid4()),
                                file,
                                str(img._getexif()),
                                created_time,
                                time.ctime(os.path.getmtime(file_path)),
                                file_path,
                                full_destination_path,
                            ),
                        )
                        conn.commit()
                        log_info(f"Copied {file_path} to {full_destination_path}")
                    except Exception as e:
                        log_error(f"Error copying file {file_path}: {str(e)}")
                    #  close connection
                    finally:
                        conn.close()
    except Exception as e:
        log_error(f"Error during copy process: {str(e)}")
        log_error(f"Traceback: {traceback.format_exc()}")


def safe_increment_filename(base_name, extension):
    counter = 1
    new_name = f"{base_name}({counter}){extension}"
    while os.path.exists(new_name):
        counter += 1
        new_name = f"{base_name}({counter}){extension}"
    return new_name


def extract_creation_time_from_filename(filename):
    pattern4 = r"(\D*)(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])_([012][0-9])-([012345][0-9])-([012345][0-9])(\D*)"  # 2022-01-01_12-34-56
    pattern3 = r"(\D*)(\d{4})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])_(\d{6})(\D*)"  # 2022-01-01_123456
    pattern2 = r"(\D*)(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])(\s+.*)"  # 2022-01-01 hello world
    pattern1 = r"(\D*)(\d{4})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(\D*)"  # 2022-01-01

    match4 = re.search(pattern4, filename)
    match3 = re.search(pattern3, filename)
    match2 = re.search(pattern2, filename)
    match1 = re.search(pattern1, filename)

    if match4:
        year = match4.group(2)
        month = match4.group(3)
        day = match4.group(4)
        hour = match4.group(5)
        minute = match4.group(6)
        second = match4.group(7)
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    elif match3:
        year = match3.group(2) + match3.group(3)
        month = match3.group(4)
        day = match3.group(5)
        hour = match3.group(6)[:2]
        minute = match3.group(6)[2:4]
        second = match3.group(6)[4:6]
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    elif match2:
        year = match2.group(2)
        month = match2.group(3)
        day = match2.group(4)
        return f"{year}-{month}-{day}T00:00:00"
    elif match1:
        year = match1.group(2)
        month = match1.group(3)
        day = match1.group(4)
        return f"{year}-{month}-{day}T00:00:00"
    return None


def copy_videos_with_md5(source_dir, destination_dir, overwrite_rule):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(SUPPORTED_VIDEO_TYPES):
                file_path = os.path.join(root, file)
                try:
                    create_time = get_date_from_filename(file)
                    if create_time is None:
                        datetime_from_fileinfo = os.path.getctime(file_path)
                        log_debug(f"datetime_from_fileinfo: {datetime_from_fileinfo}")
                        if datetime_from_fileinfo is None:
                            log_error(f"Failed to get created time for {file_path}")
                            continue
                        create_time = datetime.fromtimestamp(
                            datetime_from_fileinfo
                        ).isoformat()
                        # Parse the ISO date string
                    dt = datetime.fromisoformat(create_time)

                    year = str(dt.year)
                    month = str(dt.month).zfill(2)
                    day = str(dt.day).zfill(2)
                    hour = str(dt.hour).zfill(2)
                    minute = str(dt.minute).zfill(2)
                    second = str(dt.second).zfill(2)

                except Exception as e:
                    log_error(f"Error processing {file_path}: {e}")
                    continue

                # Prepare the destination path based on the configuration if not set, default to f"{year}/{month}/{day}
                destination_path = (
                    destination_video_path_format.replace("{year}", year)
                    .replace("{month}", month)
                    .replace("{day}", day)
                    if destination_video_path_format
                    else f"{year}/{month}/{day}"
                )

                # Prepare the destination filename
                originalfile, ext = os.path.splitext(file)
                extension = ext[1:]
                destination_filename = (
                    destination_video_name_format.replace(
                        "{originalfile}", originalfile
                    )
                    .replace("{year}", year)
                    .replace("{month}", month)
                    .replace("{day}", day)
                    .replace("{hour}", hour)
                    .replace("{minute}", minute)
                    .replace("{second}", second)
                    .replace("{extension}", extension)
                    if destination_video_name_format
                    else f"VID_{year}{month}{day}_{originalfile}.{extension}"
                )

                # Construct the full destination path
                full_destination_path = os.path.join(
                    destination_dir, destination_path, destination_filename
                )
                # Check if the destination file already exists
                if os.path.exists(full_destination_path):
                    if get_md5(file_path) == get_md5(full_destination_path):
                        log_info(
                            f"File {full_destination_path} already exists with the same content, skipping..."
                        )
                        continue  # Skip if MD5 is the same

                    base_name, extension = os.path.splitext(file)
                    full_destination_path = safe_increment_filename(
                        base_name, extension
                    )
                    counter = 1

                    while os.path.exists(full_destination_path):
                        if overwrite_existing_rule:
                            log_info(
                                f"File {full_destination_path} already exists, overwriting..."
                            )
                            os.remove(full_destination_path)
                            break
                        else:
                            new_full_destination_path = os.path.join(
                                destination_dir,
                                destination_path,
                                f"{base_name}({counter}){extension}",
                            )
                            counter += 1
                    full_destination_path = new_full_destination_path

                # Ensure the destination directory exists
                destination_dir_path = os.path.join(destination_dir, destination_path)
                if not os.path.exists(destination_dir_path):
                    os.makedirs(destination_dir_path)
                # Proceed with copying the file
                try:
                    shutil.copy2(file_path, full_destination_path)
                    log_info(f"Copied {file_path} to {full_destination_path}")
                    # Add to database
                    conn = sqlite3.connect(db_name)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO videos (uuid, filename, md5_hash, created_time, modified_time, source_file_path, destination_file_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            str(uuid.uuid4()),
                            file,
                            get_md5(file_path),
                            time.ctime(os.path.getmtime(file_path)),
                            time.ctime(os.path.getmtime(file_path)),
                            file_path,
                            full_destination_path,
                        ),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    log_error(f"Error copying file {file_path}: {str(e)}")


# Main execution flow
if __name__ == "__main__":
    # Log the application version and current timestamp
    log_info(
        f"App Version: {APP_VERSION} - Run Timestamp: {datetime.now().isoformat()}"
    )

    # Check if source image path exists and is a directory
    if not os.path.exists(source_image_dir):
        log_error(f"Source path does not exist: {source_image_dir}")
        exit(1)
    elif not os.path.isdir(source_image_dir):
        log_error(f"Source path is not a directory: {source_image_dir}")
        exit(1)

    # Check if destination image path exists, and is a directory, if not create it
    if not os.path.exists(destination_image_dir):
        try:
            os.makedirs(destination_image_dir)
            log_info(f"Destination directory created: {destination_image_dir}")
        except OSError as e:
            log_error(f"Failed to create destination directory: {e}")
            exit(1)
    elif not os.path.isdir(destination_image_dir):
        log_error(f"Destination path is not a directory: {destination_image_dir}")
        exit(1)

    # Check if source video path exists and is a directory
    if not os.path.exists(source_video_dir):
        log_error(f"Source path does not exist: {source_video_dir}")
        exit(1)
    elif not os.path.isdir(source_video_dir):
        log_error(f"Source path is not a directory: {source_video_dir}")
        exit(1)

    # Check if destination video path exists, and is a directory, if not create it
    if not os.path.exists(destination_video_dir):
        try:
            os.makedirs(destination_video_dir)
            log_info(f"Destination directory created: {destination_video_dir}")
        except OSError as e:
            log_error(f"Failed to create destination directory: {e}")
            exit(1)
    elif not os.path.isdir(destination_video_dir):
        log_error(f"Destination path is not a directory: {destination_video_dir}")
        exit(1)

    # Initialize database
    if not os.path.exists(db_name):
        setup_database(db_name)
        log_info(f"Database {db_name} created.")
    else:
        log_info(f"Database {db_name} already exists.")

    while True:
        # Check if the copy process is running
        try:
            log_info("Starting copy process...")
            copy_photos_with_exif(source_image_dir, destination_image_dir)
            copy_videos_with_md5(
                source_video_dir, destination_video_dir, overwrite_existing_rule
            )
        except Exception as e:
            log_error(f"Error during copy process: {str(e)}")
        finally:
            log_info("Copy process completed.")

        subprocess.run(["sleep", str(sleep_time)])  # Wait for the specified sleep time
