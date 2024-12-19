#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 17:20:07
* @LastEditors  : JIYONGFENG jiyongfeng@163.com
* @LastEditTime : 2024-12-19 17:41:21
* @Description  : main function
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import os
import subprocess
from datetime import datetime

from config import config
from core.logger import logger
from core.photo_processor import PhotoProcessor
from core.utils import create_directory, validate_directory
from core.video_processor import VideoProcessor


def main():
    """Main execution flow."""

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    logger.info(
        "App Version: %s - Run Timestamp: %s",
        config.app_version,
        datetime.now().isoformat(),
    )

    # Validate source directories
    if not all(
        [
            validate_directory(config.image_source_dir, "Image source"),
            validate_directory(config.video_source_dir, "Video source"),
        ]
    ):
        return False

    # Create destination directories if needed
    if not all(
        [
            create_directory(config.image_destination_dir),
            create_directory(config.video_destination_dir),
        ]
    ):
        return False

    # Initialize processors
    photo_processor = PhotoProcessor()
    video_processor = VideoProcessor()

    while True:
        try:
            # Process images
            photo_processor.process_photos()
            # Process videos
            video_processor.process_videos()
        except Exception as e:
            logger.error("Error during processing: %s", e)
        finally:
            logger.info("Processing cycle completed.")

        try:
            subprocess.run(["sleep", str(config.sleep_time)], check=True)
        except subprocess.CalledProcessError as e:
            logger.error("Sleep command failed: %s", e)


if __name__ == "__main__":
    main()
