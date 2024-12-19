#!/usr/bin/env python
# coding=utf-8

"""
* @Author       : JIYONGFENG jiyongfeng@163.com
* @Date         : 2024-12-19 13:30:41
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2024-12-19 14:31:01
* @Description  :
* @Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
"""

import os
import sys
import yaml


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "configuration.yaml",
            )
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file)

            # 将配置项设置为实例属性
            self.sleep_time = config["task"]["sleep_time"]
            self.app_version = config["app"]["version"]
            # image settings
            self.supported_image_types = tuple(config["app"]["supported_image_types"])
            self.image_source_dir = config["app"]["image_source_dir"]
            self.image_destination_dir = config["app"]["image_destination_dir"]
            self.image_overwrite_existing_rule = config["app"][
                "image_overwrite_existing_rule"
            ]
            self.image_destination_path_format = config["app"][
                "image_destination_path_format"
            ]
            self.image_destination_filename_format = config["app"][
                "image_destination_filename_format"
            ]

            # video settings
            self.supported_video_types = tuple(config["app"]["supported_video_types"])
            self.video_source_dir = config["app"]["video_source_dir"]
            self.video_destination_dir = config["app"]["video_destination_dir"]
            self.video_overwrite_existing_rule = config["app"][
                "video_overwrite_existing_rule"
            ]
            self.video_destination_path_format = config["app"][
                "video_destination_path_format"
            ]
            self.video_destination_filename_format = config["app"][
                "video_destination_filename_format"
            ]

            self.db_name = config["database"]["db_name"]

            # 日志配置
            self.log_dir = config["logging"]["log_dir"]
            self.log_level = config["logging"]["log_level"]
            self.log_format = config["logging"]["log_format"]
            self.log_date_format = config["logging"]["log_date_format"]
            self.log_max_bytes = config["logging"]["log_max_bytes"]
            self.log_backup_count = config["logging"]["log_backup_count"]

        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)


config = Config()
