"""Web package."""

from bson import ObjectId
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader("./web/templates"),
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=["jinja_markdown.MarkdownExtension"],
)

templates = Jinja2Templates(env=env)


def object_id(oid: str) -> ObjectId:
    """Converts a string to an ObjectId or raises an HTTP exception."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(400, detail="Invalid ID.")
    return ObjectId(oid)
