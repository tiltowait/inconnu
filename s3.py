"""S3 uploads."""
# pylint: disable=invalid-name

import asyncio
import concurrent.futures
import functools
import glob
import os
import urllib

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError
from dotenv import load_dotenv

from config import aws
from logger import Logger

load_dotenv()

executor = concurrent.futures.ThreadPoolExecutor()
s3_client = None
BUCKET = "inconnu"
BASE_URL = f"https://{BUCKET}.s3.amazonaws.com/"

if aws.access_key_id is None:
    Logger.warning("S3: AWS is not configured")
else:
    Logger.info("S3: Establishing AWS connection")
    s3_client = boto3.client("s3")


def aio(func):
    """AsyncIO decorator for AWS."""

    async def aio_wrapper(*args, **kwargs):
        """Wraps an AWS function into an async one."""
        f_bound = functools.partial(func, *args, **kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, f_bound)

    return aio_wrapper


def get_url(object_name: str):
    """Get the URL of a given S3 object."""
    url = f"""{BASE_URL}{urllib.parse.quote(object_name, safe="/~()*!.'")}"""
    return url


def is_managed_url(url: str) -> bool:
    """Check whether a URL is managed by the bot."""
    return url.startswith(BASE_URL)


def get_s3_object(url: str) -> str | None:
    """Get the base object of an S3 URL. Returns None if it isn't a managed URL."""
    if is_managed_url(url):
        return url.replace(BASE_URL, "")
    return None


async def upload_file(file_name, object_name: str = None) -> bool:
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
        upload_object = aio(s3_client.upload_file)
        await upload_object(file_name, BUCKET, object_name)
        Logger.info("S3: Uploaded %s to %s%s", file_name, BASE_URL, object_name)
        return True
    except ClientError as err:
        Logger.error("S3: %s", err, exc_info=True)
        return False


async def delete_file(resource: str):
    """Delete a file from S3."""
    if s3_client is None:
        Logger.error("S3: Cannot delete %s; client not configured", resource)
        return

    if not resource.startswith(BASE_URL):
        raise ValueError(f"{resource} is not a managed resource.!")

    key = resource.replace(BASE_URL, "")
    delete_object = aio(s3_client.delete_object)
    await delete_object(Bucket=BUCKET, Key=key)
    Logger.info("S3: Deleted %s", key)


async def delete_character_images(character: "VChar"):
    """Delete all of a character's images."""
    if character.image_urls:
        deletions = [delete_file(image) for image in character.image_urls]
        await asyncio.gather(*deletions)
        await delete_file(get_url(f"profiles/{character.id}"))  # Delete the directory
        Logger.info("S3: Deleted %s's images", character.name)
    else:
        Logger.info("S3: %s had no images to delete", character.name)


async def upload_logs() -> bool:
    """Upload the contents of the log directory."""
    Logger.info("S3: Uploading logs")
    successful = True
    try:
        logs = sorted(glob.glob("./logs/*.txt"))
        if logs:
            for file in logs:
                base = os.path.basename(file)
                if not await upload_file(file, f"logs/{base}"):
                    successful = False

            if successful and len(logs) > 1:
                # We want to remove all but the most recent log so we don't
                # waste PutObject requests
                for log in logs[:-1]:
                    Logger.info("S3: Deleting old log: %s", log)
                    os.unlink(log)
        else:
            Logger.error("S3: No log files found")
            return False
    except (ParamValidationError, NoCredentialsError) as error:
        Logger.exception("S3: %s", error)
        successful = False
    return successful


async def main():
    """On dokku release, we want to upload the logs as they currently stand."""
    await upload_logs()


if __name__ == "__main__":
    asyncio.run(main())
