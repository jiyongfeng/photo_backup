#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 13:30:46
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-19 14:27:59
* @Description  : logger
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from photoarc.config import config


class Logger:
    _instance: "Logger | None" = None

    def __init__(self):
        # Initialize logger attribute with proper type annotation
        self.logger: logging.Logger = logging.getLogger()

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self) -> None:
        """Setup logging configuration."""
        if not os.path.exists(config.log_dir):
            os.makedirs(config.log_dir)

        log_filename = os.path.join(
            config.log_dir, f"app_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        )

        handler = RotatingFileHandler(
            log_filename,
            maxBytes=config.log_max_bytes,
            backupCount=config.log_backup_count,
        )
        formatter = logging.Formatter(config.log_format)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger()
        self.logger.setLevel(config.log_level)
        self.logger.addHandler(handler)
        self.logger.addHandler(logging.StreamHandler())

    def info(self, message: Any, *args: Any) -> None:
        self.logger.info(message, *args)

    def error(self, message: Any, *args: Any) -> None:
        self.logger.error(message, *args)

    def warning(self, message: Any, *args: Any) -> None:
        self.logger.warning(message, *args)

    def debug(self, message: Any, *args: Any) -> None:
        self.logger.debug(message, *args)

    def critical(self, message: Any, *args: Any) -> None:
        self.logger.critical(message, *args)


logger = Logger()
