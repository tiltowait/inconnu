"""Basic config vars."""
# pylint: disable=invalid-name

import os

from dotenv import load_dotenv

load_dotenv()

supporter_server = int(os.environ["SUPPORTER_SERVER"])
supporter_role = int(os.environ["SUPPORTER_ROLE"])
