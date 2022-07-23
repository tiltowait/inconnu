"""Logging configuration."""
# pylint: disable=invalid-name

import os

from dotenv import load_dotenv

load_dotenv()

log_level = os.getenv("LOG_LEVEL", "debug")
log_enable = int(os.getenv("LOG_ENABLE", "1"))
log_dir = os.getenv("LOG_DIR", "logs")
log_name = "inconnu_%Y-%m-%d_%H.%M_%_.txt"
log_maxfiles = 10
