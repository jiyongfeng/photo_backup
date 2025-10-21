# Photo Archive Application

## Description

This application automatically archives photos and videos to specified directories and renames them based on their metadata. It supports resuming interrupted operations and provides comprehensive logging.

## Features

- Archives both photos and videos
- Extracts creation time from EXIF data, filename, or file metadata
- Organizes files in a structured directory hierarchy (year/month/day)
- Renames files with timestamp-based names
- Avoids duplicates by checking file content
- Supports resume capability for interrupted operations
- Excludes specified directories from processing
- Stores metadata in SQLite database for future querying
- Comprehensive logging with rotation

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/jiyongfeng/photo_backup.git
   ```

2. Navigate to the project directory:

   ```bash
   cd photo_backup
   ```

3. Create a virtual environment and install dependencies:

   ```bash
   uv sync
   ```

## Usage

### As a Module (Recommended)

Run the application using the module syntax:

```bash
uv run -m photoarc [--all] [--video] [--image] [--image_source PATH] [--video_source PATH] [--image_archive PATH] [--video_archive PATH] [--overwrite] [--resume] [--exclude DIR [DIR ...]]
```

Options:

- `--all`: Process both images and videos (default)
- `--video`: Process only videos
- `--image`: Process only images
- `--image_source`: Image source directory (default: current directory)
- `--video_source`: Video source directory (default: current directory)
- `--image_archive`: Image archive directory (default: ./archive/image)
- `--video_archive`: Video archive directory (default: ./archive/video)
- `--overwrite`: Overwrite existing files
- `--resume`: Resume from last interrupted processing
- `--exclude DIR [DIR ...]`: Exclude specified directories from processing

### Examples

Process all media in the current directory:

```bash
uv run -m photoarc
```

Process only images from a specific directory:

```bash
uv run -m photoarc --image --image_source /path/to/photos
```

Process videos and save to a custom archive directory:

```bash
uv run -m photoarc --video --video_archive /path/to/my/videos
```

Resume interrupted processing:

```bash
uv run -m photoarc --resume
```

Exclude specific directories from processing:

```bash
uv run -m photoarc --exclude temp unwanted_folder
```

Exclude nested directories:

```bash
uv run -m photoarc --exclude folder1/subfolder folder2/subfolder/deep
```

### Synology NAS Usage

1. 通过套件管理器安装 python3.13

1. ssh 连接到 NAS，创建目录，并 git clone code
1. 创建虚拟环境并安装 uv

   ```bash
   python3.13 -m venv .venv
   pip install uv
   ```

1. 运行包

   ```bash
   # 参考Examples
   # 为了确保拷贝不会涉及权限问题，建议sudo运行
   sudo uv run -m photoarc --video --video_source /volume2/downloads/backup/homevideo --video_archive /volume1/video
   ```

## Configuration

The application uses a configuration file (`configuration.yaml`) for settings. Key configurations include:

- Source directories for images and videos
- Archive directories for images and videos
- Supported file types
- File naming and path formats
- Database configuration
- Logging settings

## Database

The application stores metadata in an SQLite database (`media.db`) with the following information:

- File UUID
- Original filename
- File extension
- EXIF data (for images)
- Creation time
- File size
- Dimensions (for images)
- Source and destination paths
- Media type (image/video)

## Logging

The application logs events to files in the `logs` directory. The log file is rotated when it exceeds 10 MB, and a maximum of 5 backup files are kept.

## Contributing

Contributions are welcome! Please create a pull request or open an issue for discussion.

## License

This project is licensed under the MIT License.
