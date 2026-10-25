"""Docs routing.

The docs are read once, on first request, and served from memory. Changing
them requires a restart, which deploying does anyway."""

from functools import cache
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse

from routes.auth import verify_api_key
from routes.docs import loader

router = APIRouter()

ASSET_CACHE = "public, max-age=86400"


@cache
def _docs() -> tuple[bytes, str]:
    """The docs bundle's JSON and ETag."""
    bundle = loader.load(loader.DOCS_DIR)
    return bundle.model_dump_json().encode(), f'"{bundle.version}"'


@cache
def _assets() -> dict[str, Path]:
    """The docs' asset files, by name."""
    return loader.assets(loader.DOCS_DIR)


@router.get("/docs", dependencies=[Depends(verify_api_key)])
async def get_docs(request: Request) -> Response:
    """Fetch every docs page plus the sidebar. Honors If-None-Match."""
    body, etag = _docs()
    headers = {"ETag": etag}
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)


@router.get("/docs/assets/{name}", dependencies=[Depends(verify_api_key)])
async def get_asset(name: str) -> FileResponse:
    """Fetch a docs image. Only files in docs/assets are served."""
    path = _assets().get(name)
    if path is None:
        raise HTTPException(404, detail="Asset not found")
    return FileResponse(path, headers={"Cache-Control": ASSET_CACHE})
