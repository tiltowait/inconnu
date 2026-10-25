"""Loading the Markdown docs from the docs/ directory."""

import hashlib
import posixpath
import re
from pathlib import Path

import yaml

from routes.docs.models import DocPage, DocsBundle, NavItem, NavSection

DOCS_DIR = Path(__file__).parents[3] / "docs"
SUMMARY = "SUMMARY.md"

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n+", re.DOTALL)
NAV_ENTRY = re.compile(r"^( *)\* \[(.+?)\]\((.+?)\)$")


def page_path(file: str) -> str:
    """The URL path for a docs file. READMEs stand for their directory."""
    if file == "README.md":
        return ""
    if file.endswith("/README.md"):
        return file.removesuffix("/README.md")
    return file.removesuffix(".md")


def parse_page(file: str, text: str) -> DocPage:
    """Parse a docs page. Its title is its first H1, outside of code blocks."""
    description = None
    if match := FRONTMATTER.match(text):
        frontmatter = yaml.safe_load(match.group(1)) or {}
        description = frontmatter.get("description")
        text = text[match.end() :]

    title = None
    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and line.startswith("# "):
            title = line.removeprefix("# ").strip()
            break
    if title is None:
        raise ValueError(f"{file} has no title")

    return DocPage(
        path=page_path(file),
        file=file,
        title=title,
        description=description,
        markdown=text,
    )


def parse_summary(text: str, files: set[str]) -> list[NavSection]:
    """Parse SUMMARY.md into sidebar sections. "## " headings start titled
    sections and "***" starts an untitled one. Entries nest by two spaces."""
    sections: list[NavSection] = []
    parents: list[NavItem] = []  # The most recent item at each depth

    for line in text.splitlines():
        if line.startswith("## "):
            sections.append(NavSection(title=line.removeprefix("## ").strip()))
            parents = []
        elif line.strip() == "***":
            sections.append(NavSection(title=None))
            parents = []
        elif match := NAV_ENTRY.match(line):
            indent, title, link = match.groups()
            item = NavItem(title=title)
            if link.startswith(("http://", "https://")):
                item.url = link
            else:
                file = posixpath.normpath(link)
                if file not in files:
                    raise ValueError(f"{SUMMARY} links to a missing page: {link}")
                item.path = page_path(file)

            depth = len(indent) // 2
            if depth == 0:
                if not sections:
                    sections.append(NavSection(title=None))
                sections[-1].items.append(item)
            else:
                parents[depth - 1].children.append(item)
            parents[depth:] = [item]

    return sections


def load(directory: Path) -> DocsBundle:
    """Load every docs page and the sidebar from a docs directory."""
    pages = []
    for source in sorted(directory.rglob("*.md")):
        file = source.relative_to(directory).as_posix()
        if file != SUMMARY:
            pages.append(parse_page(file, source.read_text()))

    files = {page.file for page in pages}
    nav = parse_summary((directory / SUMMARY).read_text(), files)

    content = DocsBundle(version="", nav=nav, pages=pages).model_dump_json()
    version = hashlib.sha256(content.encode()).hexdigest()[:16]

    return DocsBundle(version=version, nav=nav, pages=pages)


def assets(directory: Path) -> dict[str, Path]:
    """The docs' asset files, by name."""
    asset_dir = directory / "assets"
    return {path.name: path for path in asset_dir.iterdir() if path.is_file()}
