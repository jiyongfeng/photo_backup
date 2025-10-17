<!--
 * @Author       : JIYONGFENG jiyongfeng@163.com
 * @Date         : 2024-12-16 14:26:54
 * @LastEditors  : JIYONGFENG jiyongfeng@163.com
 * @LastEditTime : 2025-10-17 21:51:50
 * @Description  :
 * Copyright (c) 2024 by ZEZEDATA Technology CO, LTD, All Rights Reserved.
-->

# Photo Backup Application

## Description

This application automatically backs up photos to a specified directory and renames them based on their metadata.

## Installation

1. Clone the repository:ß

   ```bash
   git clone https://github.com/jiyongfeng/photo_backup.git
   ```

2. Navigate to the project directory:

   ```bash
   cd photo_backup
   ```

3. Install required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application using:

```bash
python app.py
```

## Configuration

The application uses a configuration file for settings. Key configurations include:

- `source_dir`: The directory where the photos are located.
- `destination_dir`: The directory where the photos will be backed up.
- Logging settings, including maximum file size and backup count.

## Logging

The application logs events to a file. The log file is rotated when it exceeds 10 MB, and a maximum of 2 backup files are kept.

## Contributing

Contributions are welcome! Please create a pull request or open an issue for discussion.

## License

This project is licensed under the MIT License.
