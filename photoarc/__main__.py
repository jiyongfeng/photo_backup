#!/usr/bin/env python
# coding=utf-8

'''
Author       : JIYONGFENG jiyongfeng@163.com
Date         : 2025-10-20 10:05:35
LastEditors  : JIYONGFENG jiyongfeng@163.com
LastEditTime : 2025-10-20 11:25:41
FilePath     : /photo_backup/photoarc/__main__.py
Description  :  Photo Archive Tool
Copyright (c) 2025 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
'''



import argparse
import os
from datetime import datetime

from photoarc.config import config
from photoarc.core.logger import logger
from photoarc.core.photo_processor import PhotoProcessor
from photoarc.core.utils import create_directory, validate_directory
from photoarc.core.video_processor import VideoProcessor


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Photo Archive Tool - Organizes photos and videos by date",
        epilog="""
Configuration file support:
If command line arguments are not provided, default values will be loaded from configuration.yaml:
  - image_source_dir: Source directory for images
  - video_source_dir: Source directory for videos  
  - image_destination_dir: Archive directory for images
  - video_destination_dir: Archive directory for videos

Examples:
  python -m photoarc --image                           # Use config file defaults for images
  python -m photoarc --all                             # Process all using config defaults
  python -m photoarc --image --image_source ./photos   # Override image source
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # File type selection
    parser.add_argument(
        "--all", action="store_true", help="Process both images and videos"
    )
    parser.add_argument("--video", action="store_true", help="Process only videos")
    parser.add_argument("--image", action="store_true", help="Process only images")

    # Source directories
    parser.add_argument("--image_source", help="Image source directory (overrides config file)")
    parser.add_argument("--video_source", help="Video source directory (overrides config file)")

    # Archive directories
    parser.add_argument("--image_archive", help="Image archive directory (overrides config file)")
    parser.add_argument("--video_archive", help="Video archive directory (overrides config file)")

    # Overwrite option
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files"
    )

    # Resume option for interrupted processing
    parser.add_argument(
        "--resume", action="store_true", help="Resume from last interrupted processing"
    )

    # Exclude directories
    parser.add_argument(
        "--exclude", nargs="*", default=[], help="Directories to exclude from processing"
    )

    return parser.parse_args()


def set_default_values(args):
    """Set default values for directories using configuration file values."""
    # Get current directory for relative path resolution
    current_dir = os.getcwd()
    
    # Convert relative paths from config to absolute paths
    def resolve_path(path):
        if not path:
            return current_dir
        if os.path.isabs(path):
            return path
        # Normalize path to remove redundant separators and up-level references
        return os.path.normpath(os.path.join(current_dir, path))

    # Set source directories from config if not provided via command line
    if args.image_source is None:
        args.image_source = resolve_path(config.image_source_dir)
    if args.video_source is None:
        args.video_source = resolve_path(config.video_source_dir)

    # Set archive directories from config if not provided via command line
    if args.image_archive is None:
        args.image_archive = resolve_path(config.image_destination_dir)
    if args.video_archive is None:
        args.video_archive = resolve_path(config.video_destination_dir)

    # Set file types to process
    if not args.all and not args.video and not args.image:
        args.all = True  # Default to processing all if none specified


def update_config_with_args(args):
    """Update configuration with command line arguments temporarily."""
    # Store original values for restoration later if needed
    # For now, we'll update config directly but this could be improved
    # by passing args to processors instead
    
    # Update source directories
    config.image_source_dir = args.image_source
    config.video_source_dir = args.video_source

    # Update archive directories  
    config.image_destination_dir = args.image_archive
    config.video_destination_dir = args.video_archive

    # Update overwrite settings
    config.image_overwrite_existing_rule = args.overwrite
    config.video_overwrite_existing_rule = args.overwrite

    # Store exclude directories in config
    config.exclude_directories = args.exclude


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

    logger.info(
        "Processing options: all=%s, video=%s, image=%s",
        args.all,
        args.video,
        args.image,
    )
    logger.info("Processing configuration:")
    logger.info("Image source: %s", args.image_source)
    logger.info("Video source: %s", args.video_source)
    logger.info("Image archive: %s", args.image_archive)
    logger.info("Video archive: %s", args.video_archive)
    logger.info("Overwrite: %s", args.overwrite)
    logger.info("Resume: %s", args.resume)
    logger.info("Exclude directories: %s", config.exclude_directories)

    # Display directory contents before processing
    if args.all or args.image:
        logger.info("Image source directory contents:")
        try:
            if os.path.exists(config.image_source_dir):
                contents = os.listdir(config.image_source_dir)
                logger.info("  Found %d items in %s", len(contents), config.image_source_dir)
                for item in contents[:10]:  # Show first 10 items
                    item_path = os.path.join(config.image_source_dir, item)
                    item_type = "DIR" if os.path.isdir(item_path) else "FILE"
                    logger.info("    [%s] %s", item_type, item)
                if len(contents) > 10:
                    logger.info("    ... and %d more items", len(contents) - 10)
            else:
                logger.warning("  Directory does not exist: %s", config.image_source_dir)
        except Exception as e:
            logger.warning("  Cannot list directory contents: %s", e)

    # Validate source directories
    if (args.all or args.image) and not validate_directory(
        config.image_source_dir, "Image source"
    ):
        logger.error("Image source directory validation failed")
        return False

    if (args.all or args.video) and not validate_directory(
        config.video_source_dir, "Video source"
    ):
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
