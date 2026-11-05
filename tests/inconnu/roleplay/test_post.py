"""Tests for inconnu/roleplay/post.py PostModal helper methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import errors
import services
from ctx import AppCtx
from inconnu.roleplay.post import PostModal, edit_post
from models import RPPost

type MockPostModal = MagicMock


@pytest.fixture
def mock_post_modal() -> MockPostModal:
    """Create a mock PostModal instance with children structure."""
    modal = MagicMock(spec=PostModal)
    # PostModal has children: [message_field, ..., title_field, tags_field]
    # We care about the last one (index -1) for tags
    modal.children = [MagicMock(), MagicMock(), MagicMock()]
    return modal


# Test _clean_tags


def test_clean_tags_basic(mock_post_modal: MockPostModal):
    """Test basic tag cleaning and splitting."""
    mock_post_modal.children[-1].value = "tag1; tag2; tag3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_comma_separator(mock_post_modal: MockPostModal):
    """Test that commas are converted to semicolons."""
    mock_post_modal.children[-1].value = "tag1, tag2, tag3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_mixed_separators(mock_post_modal: MockPostModal):
    """Test mixing commas and semicolons."""
    mock_post_modal.children[-1].value = "tag1, tag2; tag3, tag4"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3", "tag4"]


def test_clean_tags_lowercase_conversion(mock_post_modal: MockPostModal):
    """Test that tags are converted to lowercase."""
    mock_post_modal.children[-1].value = "TAG1; Tag2; tAg3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_removes_special_characters(mock_post_modal: MockPostModal):
    """Test that special characters are removed (except parens and allowed chars)."""
    mock_post_modal.children[-1].value = "tag1!@#; tag2$%^; tag3&*"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_preserves_parentheses(mock_post_modal: MockPostModal):
    """Test that parentheses are preserved in tags."""
    mock_post_modal.children[-1].value = "tag (with parens); another (test)"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["another (test)", "tag (with parens)"]  # sorted


def test_clean_tags_extra_whitespace(mock_post_modal: MockPostModal):
    """Test that extra whitespace is cleaned."""
    mock_post_modal.children[-1].value = "  tag1  ;  tag2  ;  tag3  "

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_empty_tags_removed(mock_post_modal: MockPostModal):
    """Test that empty tags are removed."""
    mock_post_modal.children[-1].value = "tag1;; tag2;;; tag3"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_duplicates_removed(mock_post_modal: MockPostModal):
    """Test that duplicate tags are removed."""
    mock_post_modal.children[-1].value = "tag1; tag2; tag1; tag3; tag2"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_sorted_output(mock_post_modal: MockPostModal):
    """Test that tags are sorted alphabetically."""
    mock_post_modal.children[-1].value = "zebra; alpha; beta; charlie"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["alpha", "beta", "charlie", "zebra"]


def test_clean_tags_single_tag(mock_post_modal: MockPostModal):
    """Test cleaning a single tag."""
    mock_post_modal.children[-1].value = "  Single Tag  "

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["single tag"]


def test_clean_tags_empty_string(mock_post_modal: MockPostModal):
    """Test that empty string returns empty list."""
    mock_post_modal.children[-1].value = ""

    result = PostModal._clean_tags(mock_post_modal)

    assert result == []


def test_clean_tags_only_whitespace(mock_post_modal: MockPostModal):
    """Test that whitespace-only input returns empty list."""
    mock_post_modal.children[-1].value = "   ;  ;  "

    result = PostModal._clean_tags(mock_post_modal)

    assert result == []


def test_clean_tags_only_special_chars(mock_post_modal: MockPostModal):
    """Test that special-char-only tags are removed."""
    mock_post_modal.children[-1].value = "!!!; @@@; ###"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == []


def test_clean_tags_numbers_preserved(mock_post_modal: MockPostModal):
    """Test that numbers in tags are preserved."""
    mock_post_modal.children[-1].value = "tag1; tag2; 123"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["123", "tag1", "tag2"]


def test_clean_tags_underscores_preserved(mock_post_modal: MockPostModal):
    """Test that underscores are preserved (part of \\w)."""
    mock_post_modal.children[-1].value = "tag_one; tag_two"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag_one", "tag_two"]


def test_clean_tags_complex_case(mock_post_modal: MockPostModal):
    """Test complex real-world scenario."""
    mock_post_modal.children[-1].value = "Combat (violent), Magic!!, combat (violent); TEST; test"

    result = PostModal._clean_tags(mock_post_modal)

    # lowercase, remove special chars, dedupe, sort
    assert result == ["combat (violent)", "magic", "test"]


def test_clean_tags_unicode_characters_removed(mock_post_modal: MockPostModal):
    """Test that unicode special characters are removed."""
    mock_post_modal.children[-1].value = "tag1™; tag2®; tag3©"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag1", "tag2", "tag3"]


def test_clean_tags_hyphens_removed(mock_post_modal: MockPostModal):
    """Test that hyphens are removed (not in regex pattern)."""
    mock_post_modal.children[-1].value = "tag-one; tag-two"

    result = PostModal._clean_tags(mock_post_modal)

    # Hyphens removed, words merged
    assert result == ["tagone", "tagtwo"]


def test_clean_tags_multiple_spaces_collapsed(mock_post_modal: MockPostModal):
    """Test that multiple spaces within tags are collapsed."""
    mock_post_modal.children[-1].value = "tag   with   spaces"

    result = PostModal._clean_tags(mock_post_modal)

    assert result == ["tag with spaces"]


# Test edit_post


@pytest.mark.parametrize("error", [errors.WrongGuild, errors.WrongOwner])
async def test_edit_post_of_transferred_character(error: type[errors.CharacterError]):
    """Editing a post after its character changed hands shows the reason."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.user = MagicMock(spec=discord.Member, id=1)
    rp_post = MagicMock(spec=RPPost, user=1)

    with (
        patch.object(RPPost, "find_one", AsyncMock(return_value=rp_post)),
        patch.object(services.char_mgr, "fetchone", AsyncMock(side_effect=error("Not yours"))),
        patch("ui.embeds.error", new_callable=AsyncMock) as show_error,
    ):
        await edit_post(ctx, MagicMock(spec=discord.Message))

    show_error.assert_awaited_once()
    assert str(show_error.call_args.args[1]) == "Not yours"
