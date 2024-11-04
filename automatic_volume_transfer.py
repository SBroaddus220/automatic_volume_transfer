#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to detect volumes upon instantiation and copy files from the volumes to the destination directory.
"""

import os
import shutil
import logging
import hashlib
import subprocess
from tqdm import tqdm
from datetime import datetime, timedelta

# Add root project directory to path
import sys
from pathlib import Path
sys.path.append((Path(__file__).parent.parent.resolve()).as_posix())

from config import VOLUMES

# **********
# Sets up logger
logger = logging.getLogger(__name__)

# **********
def get_unique_filename(target_path: Path) -> Path:
    """Return a unique path by appending (1), (2), etc. if the path already exists.

    Args:
        target_path (Path): Path to file to be made unique.

    Returns:
        Path: Unique path for file.
    """
    if not target_path.exists():
        return target_path

    base_name = target_path.stem
    ext = target_path.suffix
    parent = target_path.parent

    counter = 1
    while True:
        new_name = f"{base_name} ({counter}){ext}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1

def convert_wav_to_flac(input_file_path: Path, output_file_path: Path = None, exists_ok: bool = False) -> subprocess.CompletedProcess:
    logger.info(f"Converting {input_file_path} to flac")
    # Ensure FFmpeg is installed and on path
    if not shutil.which("ffmpeg"):
        raise EnvironmentError("FFmpeg not found on path. Please install FFmpeg.")
    
    # Get audio file name and extension for processing
    file_name = input_file_path.stem
    ext = input_file_path.suffix
    
    # Get output file name and extension
    if not output_file_path:
        output_file_path = Path.cwd() / f"{file_name}.flac"
    if output_file_path.exists():
        if exists_ok:
            logger.warning(f"Output file already exists: {output_file_path}")
            output_file_path = get_unique_filename(output_file_path)
        else:
            logger.error(f"Output file already exists: {output_file_path}")
            raise FileExistsError(f"Output file already exists: {output_file_path}")
    logger.info(f"Output file path: {output_file_path}")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert audio file
    process = subprocess.run(["ffmpeg", "-i", input_file_path.as_posix(), "-map_metadata", "0", "-compression_level", "8", output_file_path.as_posix()])
    
    return process

def is_valid_timestamp(timestamp: str, date_format: str = "%y%m%d_%H%M", duration: int = 30) -> bool:
    """Check if a timestamp is within {duration} days (+/-) of the current date.

    Args:
        timestamp (str): Timestamp to check.
        date_format (str, optional): Format of the timestamp. Defaults to "%y%m%d_%H%M".
        duration (int, optional): Duration in days for timestamp to fall within. Defaults to 30.

    Returns:
        bool: Whether the timestamp is valid.
    """
    try:
        # Convert timestamp to datetime object
        timestamp_date = datetime.strptime(timestamp, date_format)
        # Get the current date
        current_date = datetime.now()
        # Check if the timestamp is within {duration} days (+/-) of the current date
        min_date = current_date - timedelta(days=duration)
        max_date = current_date + timedelta(days=duration)
        return min_date <= timestamp_date <= max_date
    except ValueError:
        # If there's an error parsing the timestamp, it's invalid
        return False


def get_drives_windows():
    return [f"{d}:" for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{d}:\\")]

def get_drives_linux():
    drives = []
    mounts = ["/media", "/mnt"]
    for mount_point in mounts:
        if os.path.exists(mount_point):
            drives.extend([os.path.join(mount_point, d) for d in os.listdir(mount_point)])
    return drives

def get_drives_macos():
    return [os.path.join("/Volumes", d) for d in os.listdir("/Volumes")]


def get_available_drives():
    if sys.platform.startswith('win'):
        return get_drives_windows()
    elif sys.platform.startswith('linux'):
        return get_drives_linux()
    elif sys.platform.startswith('darwin'):
        return get_drives_macos()
    else:
        logger.error("Unsupported OS")
        return []


def copy_files_from_drive(volume_name: str):
    logger.debug(f"OS: {sys.platform}")
    os_type = 'windows' if sys.platform.startswith('win') else 'linux' if sys.platform.startswith('linux') else None
    if not os_type:
        logger.error("Unsupported OS")
        raise NotImplementedError("Unsupported OS: {sys.platform}}")
    
    source_dir = VOLUMES[volume_name][os_type]["source_dir"]
    destination_dir = VOLUMES[volume_name][os_type]["destination_dir"]

    drives = get_available_drives()

    matched_drives = []
    for drive in drives:
        logger.debug(f"Checking drive {drive}")
        try:
            if sys.platform.startswith('win'):
                volume_info = os.popen(f'vol {drive}').read()
                volume_condition = volume_name in volume_info
            elif sys.platform.startswith('linux'):
                volume_condition = volume_name in drive
            else:
                continue
            
            if volume_condition:
                logger.info(f"Found drive {drive}")
                source_path = os.path.join(f"{drive}\\", source_dir)
                if os.path.exists(source_path):
                    
                    # Iterate through files in directory and copy to destination
                    for item in os.listdir(source_path):
                        logger.info(f"Processing item {item}")
                        item_path = os.path.join(source_path, item)
                        item_name = os.path.basename(item_path)
                        
                        # Extract timestamp from filename and validate
                        timestamp = item_name.split(".")[0]  # Assumes filename is in the filename without extension
                        if not is_valid_timestamp(timestamp):
                            logger.warning(f"Invalid timestamp {timestamp} for file {item}")
                        
                        if os.path.isfile(item_path):
                            destination = os.path.join(destination_dir, item_name)
                            # Copy file to destination
                            try:
                                copy_with_progress(item_path, destination)
                            except FileExistsError as e:
                                logger.warning(e)
                                continue
                                
                            logger.info(f"File {item} copied to {destination}")
                            # Delete file from drive
                            os.remove(item_path)
                            logger.info(f"File {item} deleted from {source_path}")
                            
                            # Converts wav files to flac
                            extension = os.path.splitext(item_name)[1].lower()
                            if extension == ".wav":
                                basename_without_ext = os.path.splitext(destination)[0]
                                logger.info(f"Convert {destination} to {basename_without_ext}.flac")
                                try:
                                    convert_wav_to_flac(Path(destination), Path(f"{basename_without_ext}.flac", exists_ok=False))
                                except FileExistsError as e:
                                    logger.warning(e)
                                    logger.info(f"Deleting {destination}")
                                    os.remove(destination)  # WAV already exists in destination as FLAC, so delete the WAV
                                    continue
                                logger.info(f"Deleting {destination}")
                                os.remove(destination)
                            
                    matched_drives.append(drive)
                    
        except Exception as e:
            logger.error(f"Error processing drive {drive}: {e}")
            raise

    if not matched_drives:
        logger.warning("No matching drives found")


def calculate_sha256(file_path, show_progress=False):
    """Return the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    file_size = os.path.getsize(file_path)

    with open(file_path, 'rb') as f:
        if show_progress:
            with tqdm(total=file_size, unit='B', unit_scale=True, desc=f'Hashing {file_path}') as pbar:
                for block in iter(lambda: f.read(65536), b''):  # Reading in 64k chunks
                    sha256.update(block)
                    pbar.update(len(block))
        else:
            for block in iter(lambda: f.read(65536), b''):  # Reading in 64k chunks without progress
                sha256.update(block)

    return sha256.hexdigest()


def copy_with_progress(src, dst, show_progress=False):
    """Copy code credit to https://stackoverflow.com/questions/274493/how-to-copy-a-file-in-python-with-a-progress-bar
    """
    
    dst_dir = os.path.dirname(dst)
    
    # If dst is a directory, append the filename from src
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    
    if not os.path.exists(dst_dir):
        error_message = f"The directory {dst_dir} does not exist!"
        logger.error(error_message)
        raise FileNotFoundError(error_message)
    elif not os.access(dst_dir, os.W_OK):
        error_message = f"You do not have write permissions for {dst_dir}!"
        logger.error(error_message)
        raise PermissionError(error_message)
    
    if os.path.exists(dst):
        error_message = f"The file {dst} already exists!"
        logger.error(error_message)
        raise FileExistsError(error_message)
    
    size = os.path.getsize(src)
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        if show_progress:
            with tqdm(total=size, unit='B', unit_scale=True, desc=f'Copying {src} to {dst}') as pbar:
                while True:
                    chunk = fsrc.read(4096)
                    if not chunk:
                        break
                    fdst.write(chunk)
                    pbar.update(len(chunk))
        else:
            while True:
                chunk = fsrc.read(4096)
                if not chunk:
                    break
                fdst.write(chunk)
                    
                    
    # Simple size check
    src_size = os.path.getsize(src)
    dst_size = os.path.getsize(dst)
    if src_size != dst_size:
        error_message = f"Size mismatch: {src} ({src_size} bytes) != {dst} ({dst_size} bytes)"
        logger.error(error_message)
        raise IOError(error_message)

    # SHA256 integrity check
    logger.info(f"Calculating SHA256 hash for {src}")
    src_hash = calculate_sha256(src, show_progress=show_progress)
    logger.info(f"Calculating SHA256 hash for {dst}")
    dst_hash = calculate_sha256(dst, show_progress=show_progress)
    if src_hash != dst_hash:
        error_message = f"Hash mismatch: {src} ({src_hash}) != {dst} ({dst_hash})"
        logger.error(error_message)
        raise IOError(error_message)

    logger.info(f"File {src} copied to {dst} successfully!")


# **********
def main():
    from config import LOGGER_CONFIG
    
    import logging.config
    logging.disable(logging.DEBUG)
    logging.config.dictConfig(LOGGER_CONFIG)
    
    
    # ****
    for volume_name in VOLUMES.keys():
        copy_files_from_drive(volume_name)
    

# **********
if __name__ == "__main__":
    main()
    
