#!/usr/bin/env python3
import exifread
import os

image_path = 'images/IMG_20141231_164437.jpg'
print(f'检查照片: {image_path}')
print(f'文件大小: {os.path.getsize(image_path)} bytes')

try:
    # 'rb' (read binary) 模式打开文件
    with open(image_path, 'rb') as f:
        # 使用 exifread 处理文件
        tags = exifread.process_file(f)
        
        if not tags:
            print('没有找到EXIF数据')
        else:
            print('\n=== 所有 EXIF 数据 ===')
            # 打印所有找到的标签
            for tag, value in tags.items():
                # 排除缩略图数据，因为它太长了
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
                    print(f'{tag}: {value}')
            
            # 重点检查时间相关的EXIF字段
            print('\n=== 重点时间字段 ===')
            if 'EXIF DateTimeOriginal' in tags:
                print(f'原始拍摄时间: {tags["EXIF DateTimeOriginal"]}')
            if 'EXIF DateTimeDigitized' in tags:
                print(f'数字化时间: {tags["EXIF DateTimeDigitized"]}')
            if 'Image DateTime' in tags:
                print(f'文件修改时间: {tags["Image DateTime"]}')

except Exception as e:
    print(f'错误: {e}')