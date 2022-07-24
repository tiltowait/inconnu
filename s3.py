"""S3 uploads."""
# pylint: disable=invalid-name

import glob
import os
import urllib

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError
from dotenv import load_dotenv

from config import aws
from logger import Logger

load_dotenv()

s3_client = None
BUCKET = "inconnu"
BASE_URL = f"https://{BUCKET}.s3.amazonaws.com/"

if aws.access_key_id is None:
    Logger.warning("S3: AWS is not configured")
else:
    Logger.info("S3: Establishing AWS connection")
    s3_client = boto3.client("s3")


def get_url(object_name: str):
    """Get the URL of a given S3 object."""
    url = f"""https://{BASE_URL}{urllib.parse.quote(object_name, safe="~()*!.'")}"""
    return url


def upload_file(file_name, object_name: str = None) -> bool:
    """Upload a file to an S3 bucket. Returns True if successful."""
    if s3_client is None:
        Logger.error("S3: Cannot upload %s; client not configured", file_name)
        return False

    # We might have been given a Path object
    if not isinstance(file_name, str):
        file_name = str(file_name)

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    try:
        s3_client.upload_file(file_name, BUCKET, object_name)
        Logger.info("S3: Uploaded %s to %s/%s", file_name, BUCKET, object_name)
        return True
    except ClientError as err:
        Logger.error("S3: %s", err, exc_info=True)
        return False


def upload_logs() -> bool:
    """Upload the contents of the log directory."""
    Logger.info("S3: Uploading logs")
    successful = True
    try:
        logs = glob.glob("./logs/*.txt")
        if logs:
            for file in logs:
                base = os.path.basename(file)
                if not upload_file(file, f"logs/{base}"):
                    successful = False
        else:
            Logger.error("S3: No log files found")
            return False
    except (ParamValidationError, NoCredentialsError) as error:
        Logger.exception("S3: %s", error)
        successful = False
    return successful
