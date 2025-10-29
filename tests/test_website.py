"""Run tests against the website."""

import pytest
from bson import ObjectId
from httpx import AsyncClient

from inconnu import db
from server import app


@pytest.mark.parametrize(
    "charid,expected_status",
    [
        ("6140d7d811c1853b3d42c1e9", 200),
        ("613d3e4bba8a6a8dc0ee2a09", 200),
        ("Invalid", 400),
        ("613d3e4bba8a6a8dc0ee2a06", 404),
    ],
)
@pytest.mark.asyncio
async def test_profile_page(charid: str, expected_status: int):
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get(f"/profile/{charid}")
        assert r.status_code == expected_status

        if expected_status != 200:
            res = r.json()
            if expected_status == 400:
                assert res["detail"] == "Invalid ID."
            elif expected_status == 404:
                assert res["detail"] == "Character not found."
            else:
                pytest.fail(msg=f"Unexpected response code: {r.status_code}")
        else:
            char = await db.characters.find_one(
                {"_id": ObjectId(charid)}, {"images": "$profile.images"}
            )
            assert r.text.count("carousel-item") == len(char["images"])


@pytest.mark.parametrize(
    "postid,expected_status,deleted,num_posts",
    [
        ("6404dfafa9b47c1a4dd13294", 200, False, 7),
        ("6404dfafa9b47c1a4dd13294", 200, True, 7),
        ("6367ee5eaa29004c72953016", 404, False, 0),
        ("Invalid", 400, False, 0),
    ],
)
@pytest.mark.asyncio
async def test_posts_page(postid: str, expected_status: int, deleted: bool, num_posts: int):
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get(f"/post/{postid}")
        assert r.status_code == expected_status

        if expected_status != 200:
            res = r.json()
            if expected_status == 400:
                assert res["detail"] == "Invalid ID."
            elif expected_status == 404:
                assert res["detail"] == "Post not found."
            else:
                pytest.fail(msg=f"Unexpected response code: {r.status_code}")
        else:
            if deleted:
                assert "Deleted" in r.text
            if num_posts == 1:
                assert r.text.count("dropdown-item") == 0
            else:
                assert r.text.count("dropdown-item") == num_posts
