"""FastAPI server."""

from fastapi import FastAPI

from routes import characters, constraints, docs, roleposts, users

app = FastAPI(openapi_url=None)
app.include_router(characters.router)
app.include_router(constraints.router)
app.include_router(docs.router)
app.include_router(roleposts.router)
app.include_router(users.router)
