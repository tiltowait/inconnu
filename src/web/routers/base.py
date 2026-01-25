"""The base web route."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status

from config import SHOW_TEST_ROUTES
from web import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Debug page or (if live) redirect to the documentation site."""
    if SHOW_TEST_ROUTES:
        return templates.TemplateResponse(request, "test.html.jinja")
    return RedirectResponse("https://docs.inconnu.app", status_code=status.HTTP_303_SEE_OTHER)
