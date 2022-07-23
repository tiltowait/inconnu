"""AWS config vars."""
# pylint: disable=invalid-name

import os

from dotenv import load_dotenv

load_dotenv()

access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region_name = "us-west-1"
