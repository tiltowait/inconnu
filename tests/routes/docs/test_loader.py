"""Tests for loading the Markdown docs."""

from pathlib import Path

import pytest

from routes.docs import loader

SUMMARY = """# Table of contents

* [Inconnu](README.md)
  * [Basic Features](inconnu/basic-features.md)
* [Discord FAQ](https://support.discord.com)

## Guides

* [Quickstart](guides/quickstart/README.md)
  * [Specialties](guides/quickstart/specialties.md)
    * [Deep](guides/quickstart/deep.md)
  * [Trackers](guides/quickstart/trackers.md)

***

* [Contact](contact.md)
"""

FILES = {
    "README.md",
    "inconnu/basic-features.md",
    "guides/quickstart/README.md",
    "guides/quickstart/specialties.md",
    "guides/quickstart/deep.md",
    "guides/quickstart/trackers.md",
    "contact.md",
}


def write_docs(directory: Path, pages: dict[str, str]):
    """Write a docs directory: the given pages, a SUMMARY linking each, and an asset."""
    for file, text in pages.items():
        path = directory / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    summary = "".join(f"* [{file}]({file})\n" for file in pages)
    (directory / "SUMMARY.md").write_text(summary)
    (directory / "assets").mkdir()
    (directory / "assets" / "image.png").write_bytes(b"png")


def test_real_docs_load():
    """The repo's docs parse, and every page has a title. Loading also checks
    that every sidebar link points to a page."""
    bundle = loader.load(loader.DOCS_DIR)

    assert bundle.pages
    assert all(page.title for page in bundle.pages)
    assert "SUMMARY.md" not in {page.file for page in bundle.pages}


@pytest.mark.parametrize(
    "file,expected",
    [
        ("README.md", ""),
        ("contact.md", "contact"),
        ("guides/quickstart/README.md", "guides/quickstart"),
        ("guides/quickstart/specialties.md", "guides/quickstart/specialties"),
    ],
)
def test_page_path(file: str, expected: str):
    """READMEs stand for their directory; other pages drop .md."""
    assert loader.page_path(file) == expected


def test_parse_page_frontmatter():
    """Frontmatter supplies the description and is removed from the Markdown."""
    text = "---\ndescription: >-\n  Folded\n  text.\n---\n\n# 💡 Title\n\nBody\n"
    page = loader.parse_page("guides/basics.md", text)

    assert page.path == "guides/basics"
    assert page.file == "guides/basics.md"
    assert page.title == "💡 Title"
    assert page.description == "Folded text."
    assert page.markdown == "# 💡 Title\n\nBody\n"


def test_parse_page_without_frontmatter():
    """Pages without frontmatter have no description."""
    page = loader.parse_page("contact.md", "# Contact\n\nBody\n")

    assert page.description is None
    assert page.markdown == "# Contact\n\nBody\n"


def test_parse_page_ignores_code_headings():
    """A "# " line in a code block isn't the title."""
    text = "Intro\n\n```\n# comment\n```\n\n# Real title\n"
    assert loader.parse_page("page.md", text).title == "Real title"


def test_parse_page_requires_title():
    """A page without an H1 is an error."""
    with pytest.raises(ValueError, match="page.md has no title"):
        loader.parse_page("page.md", "## Not a title\n")


def test_parse_summary_sections():
    """Headings start titled sections, and *** starts an untitled one. Items
    before any heading go in an untitled section."""
    sections = loader.parse_summary(SUMMARY, FILES)

    assert [section.title for section in sections] == [None, "Guides", None]
    assert [item.title for item in sections[2].items] == ["Contact"]


def test_parse_summary_links():
    """Docs links become page paths; external links stay URLs."""
    sections = loader.parse_summary(SUMMARY, FILES)
    home, faq = sections[0].items

    assert home.path == ""
    assert home.url is None
    assert faq.path is None
    assert faq.url == "https://support.discord.com"


def test_parse_summary_nesting():
    """Entries nest by two spaces, and a shallower entry returns to its level."""
    quickstart = loader.parse_summary(SUMMARY, FILES)[1].items[0]

    assert quickstart.path == "guides/quickstart"
    assert [child.title for child in quickstart.children] == ["Specialties", "Trackers"]
    assert [child.title for child in quickstart.children[0].children] == ["Deep"]


def test_parse_summary_missing_page():
    """A sidebar link to a page that doesn't exist is an error."""
    with pytest.raises(ValueError, match="missing page: contact.md"):
        loader.parse_summary(SUMMARY, FILES - {"contact.md"})


def test_load(tmp_path: Path):
    """Loading reads every page except SUMMARY.md, with the sidebar."""
    write_docs(tmp_path, {"README.md": "# Home\n", "guides/a.md": "# A\n"})
    bundle = loader.load(tmp_path)

    assert [page.file for page in bundle.pages] == ["README.md", "guides/a.md"]
    assert [item.path for item in bundle.nav[0].items] == ["", "guides/a"]


def test_load_version_tracks_content(tmp_path: Path):
    """The version is stable for the same docs and changes when a page does."""
    write_docs(tmp_path, {"README.md": "# Home\n"})
    first = loader.load(tmp_path).version

    assert loader.load(tmp_path).version == first

    (tmp_path / "README.md").write_text("# Home\n\nNew text\n")
    assert loader.load(tmp_path).version != first


def test_assets(tmp_path: Path):
    """Assets are listed by name."""
    write_docs(tmp_path, {"README.md": "# Home\n"})
    assert loader.assets(tmp_path) == {"image.png": tmp_path / "assets" / "image.png"}
