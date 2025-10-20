#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Photo Archive Tool - A tool for archiving photos and videos
"""

import argparse
import os
import sys
from datetime import datetime

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import logger
from core.video_processor import VideoProcessor

from config import config
from core.photo_processor import PhotoProcessor
from core.utils import create_directory, validate_directory


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Photo Archive Tool")

    # File type selection
    parser.add_argument("--all", action="store_true", help="Process both images and videos")
    parser.add_argument("--video", action="store_true", help="Process only videos")
    parser.add_argument("--image", action="store_true", help="Process only images")

    # Source directories
    parser.add_argument("--image_source", help="Image source directory")
    parser.add_argument("--video_source", help="Video source directory")

    # Archive directories
    parser.add_argument("--image_archive", help="Image archive directory")
    parser.add_argument("--video_archive", help="Video archive directory")

    # Overwrite option
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")

    # Resume option for interrupted processing
    parser.add_argument("--resume", action="store_true", help="Resume from last interrupted processing")

    return parser.parse_args()


def set_default_values(args):
    """Set default values for directories."""
    # Get current directory (excluding logs directory)
    current_dir = os.getcwd()

    # Set source directories
    if args.image_source is None:
        args.image_source = current_dir
    if args.video_source is None:
        args.video_source = current_dir

    # Set archive directories
    if args.image_archive is None:
        args.image_archive = os.path.join(current_dir, "archive", "image")
    if args.video_archive is None:
        args.video_archive = os.path.join(current_dir, "archive", "video")

    # Set file types to process
    if not args.all and not args.video and not args.image:
        args.all = True  # Default to processing all if none specified


def update_config_with_args(args):
    """Update configuration with command line arguments."""
    # Update source directories
    config.image_source_dir = args.image_source
    config.video_source_dir = args.video_source

    # Update archive directories
    config.image_destination_dir = args.image_archive
    config.video_destination_dir = args.video_archive

    # Update overwrite settings
    config.image_overwrite_existing_rule = args.overwrite
    config.video_overwrite_existing_rule = args.overwrite


def main():
    """Main execution function."""
    # Parse arguments
    args = parse_arguments()

    # Set default values
    set_default_values(args)

    # Update configuration with arguments
    update_config_with_args(args)

    logger.info(
        "Photo Archive Tool Version: %s - Run Timestamp: %s",
        config.app_version,
        datetime.now().isoformat(),
    )

    logger.info("Processing options: all=%s, video=%s, image=%s", args.all, args.video, args.image)
    logger.info("Image source: %s", args.image_source)
    logger.info("Video source: %s", args.video_source)
    logger.info("Image archive: %s", args.image_archive)
    logger.info("Video archive: %s", args.video_archive)
    logger.info("Overwrite: %s", args.overwrite)
    logger.info("Resume: %s", args.resume)

    # Validate source directories
    if (args.all or args.image) and not validate_directory(config.image_source_dir, "Image source"):
        logger.error("Image source directory validation failed")
        return False

    if (args.all or args.video) and not validate_directory(config.video_source_dir, "Video source"):
        logger.error("Video source directory validation failed")
        return False

    # Create destination directories if needed
    if (args.all or args.image) and not create_directory(config.image_destination_dir):
        logger.error("Failed to create image archive directory")
        return False

    if (args.all or args.video) and not create_directory(config.video_destination_dir):
        logger.error("Failed to create video archive directory")
        return False

    # Process files based on arguments
    if args.all or args.image:
        logger.info("Starting image processing...")
        photo_processor = PhotoProcessor()
        photo_processor.process_photos()

    if args.all or args.video:
        logger.info("Starting video processing...")
        video_processor = VideoProcessor()
        video_processor.process_videos()

    logger.info("Photo Archive Tool execution completed.")


if __name__ == "__main__":
    main()