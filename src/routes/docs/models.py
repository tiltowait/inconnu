"""Pydantic models for the docs API."""

from pydantic import BaseModel, Field


class NavItem(BaseModel):
    """A sidebar entry. Links either to a docs page (path) or elsewhere (url)."""

    title: str
    path: str | None = None
    url: str | None = None
    children: list["NavItem"] = Field(default_factory=list)


class NavSection(BaseModel):
    """A group of sidebar entries. Untitled sections are separated by a divider."""

    title: str | None
    items: list[NavItem] = Field(default_factory=list)


class DocPage(BaseModel):
    """A docs page.

    path is the page's URL path (guides/quickstart), and file is its source
    file (guides/quickstart/README.md), which relative links resolve against."""

    path: str
    file: str
    title: str
    description: str | None
    markdown: str


class DocsBundle(BaseModel):
    """Every docs page plus the sidebar. version changes whenever they do."""

    version: str
    nav: list[NavSection]
    pages: list[DocPage]
