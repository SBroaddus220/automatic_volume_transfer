#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration file for `automatic_volume_transfer`
"""

import logging
from pathlib import Path

# **********
# Sets up logger
logger = logging.getLogger(__name__)

# **********
#: Dictionary of volume names and their corresponding source/destination directories
# NOTE: Do not include volume letters in the source_dir for Windows
# NOTE: Upon running the script, the `source_dir` will be searched for in every volume. Please ensure that the `source_dir` is unique across all volumes unless otherwise desired.
VOLUMES = {
    "GENREC": {
        # "windows": {
        #     "source_dir": "example_dir",
        #     "destination_dir": "C:\\example_dir"
        # },
        "windows": {
            "source_dir": "testdir",
            "destination_dir": "D:\\testdir02"
        },
        # "linux": {
        #     "source_dir": "path_on_linux",
        #     "destination_dir": "destination_on_linux"
        # }
    }
}

# **********
# Custom logging configuration
PROGRAM_LOG_FILE_PATH = Path(__file__).resolve().parent / "program_log.txt"

# Separates stdout and stderr for more flexibility
class StderrFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.ERROR

class StdoutFilter(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.ERROR


LOGGER_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Doesn't disable other loggers that might be active
    "formatters": {
        "default": {
            "format": "[%(levelname)s][%(funcName)s] | %(asctime)s | %(message)s",
        },
        "simple": {
            "format": "[%(levelname)s][%(funcName)s] | %(message)s",
        },
    },
    
    "filters": {
        "stderr_only": {
            "()": StderrFilter,
        },
        "stdout_only": {
            "()": StdoutFilter,
        }
    },
        
    "handlers": {
        "logfile": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "level": "INFO",
            "filename": PROGRAM_LOG_FILE_PATH.as_posix(),
            "mode": "a",
            "encoding": "utf-8",
        },
        "console_stdout": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
            "filters": ["stdout_only"],  # Using our filter
        },
        "console_stderr": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "ERROR",
            "stream": "ext://sys.stderr",
            "filters": ["stderr_only"],  # Using our filter
        },
    },
    "root": {  # Simple program, so root logger uses all handlers
        "level": "DEBUG",
        "handlers": [
            "logfile",
            "console_stdout",
            "console_stderr",
        ]
    }
}

# **********
if __name__ == "__main__":
    pass
