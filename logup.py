"""Uploads logs before redeployment."""

import asyncio

import api

if __name__ == "__main__":
    asyncio.run(api.upload_logs())
