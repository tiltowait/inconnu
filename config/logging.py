"""Logging configuration."""
# pylint: disable=invalid-name

import os
from distutils.util import strtobool

from dotenv import load_dotenv

load_dotenv()

upload_to_aws = bool(strtobool(os.getenv("AWS_UPLOAD_LOGS", "0")))
log_level = os.getenv("LOG_LEVEL", "info")
log_enable = int(os.getenv("LOG_ENABLE", "1"))
log_to_file = bool(strtobool(os.getenv("LOG_TO_FILE", "1")))
log_dir = os.getenv("LOG_DIR", "logs")
log_name = "inconnu_%Y-%m-%d_%H.%M_%_.txt"
log_maxfiles = 10
