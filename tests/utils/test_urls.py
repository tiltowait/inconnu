"""Tests for URL generation, including that the bot's docs links resolve."""

import ast
import re
from pathlib import Path

import pytest

from routes.docs import loader
from utils.urls import docs_url

SRC = Path(__file__).parents[2] / "src"


def heading_anchors(markdown: str) -> set[str]:
    """The anchors for a page's headings, using GitHub's rules: lowercase, drop
    punctuation and emoji, spaces become hyphens, and repeats get -1, -2, ..."""
    anchors = set()
    counts: dict[str, int] = {}
    in_code = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not (match := re.match(r"#{1,6} (.+)", line)):
            continue
        slug = re.sub(r"[^\w\- ]", "", match.group(1).strip().lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def docs_url_calls() -> list[tuple[str, int, str | None]]:
    """Every docs_url() call in src: file, line, and its page argument, or None
    if the argument isn't a single string literal."""
    calls = []
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "docs_url"
            ):
                continue
            page = None
            if len(node.args) == 1 and not node.keywords:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    page = arg.value
            calls.append((path.relative_to(SRC).as_posix(), node.lineno, page))
    return calls


def test_docs_url():
    """Docs URLs point at the docs site, keeping any anchor."""
    assert docs_url("guides/quickstart") == "https://docs.inconnu.app/guides/quickstart"
    assert (
        docs_url("guides/gameplay-shortcuts#rouse-checks")
        == "https://docs.inconnu.app/guides/gameplay-shortcuts#rouse-checks"
    )


@pytest.mark.parametrize(
    "markdown,expected",
    [
        ("# 🥇 Specialties", {"-specialties"}),  # The space after the emoji remains
        ("### You aren't able to upload images", {"you-arent-able-to-upload-images"}),
        ("### `experience_permissions`", {"experience_permissions"}),
        ("### Use emojis (server)", {"use-emojis-server"}),
        ("## Notes\n## Notes\n## Notes", {"notes", "notes-1", "notes-2"}),
        ("```\n# comment\n```\n## Real", {"real"}),
    ],
)
def test_heading_anchors(markdown: str, expected: set[str]):
    """Anchors follow GitHub's rules, and code blocks aren't headings."""
    assert heading_anchors(markdown) == expected


def test_docs_links_resolve():
    """Every docs_url() call names a real docs page, and any anchor names a
    heading on that page."""
    pages = {page.path: page for page in loader.load(loader.DOCS_DIR).pages}
    calls = docs_url_calls()
    assert len(calls) > 40, "The call scan found too few docs_url() calls"

    problems = []
    for file, line, page in calls:
        where = f"{file}:{line}"
        if page is None:
            problems.append(f"{where}: argument must be a string literal")
            continue
        path, _, anchor = page.partition("#")
        if path not in pages:
            problems.append(f"{where}: no docs page '{path}'")
        elif anchor and anchor not in heading_anchors(pages[path].markdown):
            problems.append(f"{where}: no heading '#{anchor}' on '{path}'")

    assert not problems, "\n".join(problems)


def test_no_hardcoded_docs_urls():
    """Docs links go through docs_url(), so the test above can check them."""
    hardcoded = [
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if path != SRC / "utils" / "urls.py" and "docs.inconnu.app" in path.read_text()
    ]
    assert not hardcoded
