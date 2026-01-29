"""Rolepost history route."""

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse

import bot
import inconnu
from inconnu.utils.text import diff as text_diff
from models import RPPost
from web import object_id, templates

router = APIRouter()


@router.get("/post/{oid}", response_class=HTMLResponse)
async def display_post_history(request: Request, oid: ObjectId = Depends(object_id), page: int = 0):
    """Display a Rolepost's history."""
    post = await RPPost.find_one({"_id": oid})
    if not post or post.id is None:
        raise HTTPException(404, detail="Post not found.")

    guild = bot.bot.get_guild(post.guild)
    channel = guild.get_channel(post.channel) if guild else None
    user = guild.get_member(post.user) if guild else None

    # Zip up the post history
    history = [(post.content, post.date_modified or post.date)]
    for event in post.history:
        history.append((event.content, event.date))

    if not 0 <= page <= len(history):
        raise HTTPException(404, detail="Page out of range.")

    content, date = history[page]

    try:
        previous = history[page + 1][0]
        diff = text_diff(previous, content, join=False, strip=True)
    except IndexError:
        diff = False

    return templates.TemplateResponse(
        request,
        "post.html.jinja",
        {
            "url": inconnu.post_url(post.id),
            "user": user,
            "channel": channel,
            "guild": guild,
            "header": post.header,
            "content": content,
            "link": post.url,
            "diff": diff,
            "date": date,
            "page": page,
            "dates": [event[1] for event in history],
            "pages": len(history),
            "deleted": post.deletion_date,
        },
    )
