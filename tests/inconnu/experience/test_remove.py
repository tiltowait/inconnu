"""Tests for inconnu/experience/remove.py helper functions."""

from inconnu.experience.remove import _entry_scope


# Test basic functionality


def test_entry_scope_unspent():
    """Test extracting 'unspent' scope from event."""
    entry = {"event": "xp_unspent"}
    result = _entry_scope(entry)
    assert result == "Unspent"


def test_entry_scope_lifetime():
    """Test extracting 'lifetime' scope from event."""
    entry = {"event": "xp_lifetime"}
    result = _entry_scope(entry)
    assert result == "Lifetime"


def test_entry_scope_total():
    """Test extracting 'total' scope from event."""
    entry = {"event": "xp_total"}
    result = _entry_scope(entry)
    assert result == "Total"


# Test capitalization


def test_entry_scope_capitalizes():
    """Test that the scope is capitalized."""
    entry = {"event": "xp_something"}
    result = _entry_scope(entry)
    assert result == "Something"
    assert result[0].isupper()


def test_entry_scope_capitalizes_lowercase_input():
    """Test capitalization even if input is lowercase."""
    entry = {"event": "prefix_lowercase"}
    result = _entry_scope(entry)
    assert result == "Lowercase"


# Test with different prefixes


def test_entry_scope_different_prefix():
    """Test that it works with any prefix before underscore."""
    entry = {"event": "prefix_scope"}
    result = _entry_scope(entry)
    assert result == "Scope"


def test_entry_scope_long_prefix():
    """Test with longer prefix."""
    entry = {"event": "very_long_prefix_value"}
    result = _entry_scope(entry)
    assert result == "Value"


# Test edge cases


def test_entry_scope_single_word():
    """Test with single word (no underscore)."""
    entry = {"event": "single"}
    result = _entry_scope(entry)
    assert result == "Single"


def test_entry_scope_multiple_underscores():
    """Test with multiple underscores - should take last segment."""
    entry = {"event": "one_two_three_four"}
    result = _entry_scope(entry)
    assert result == "Four"


def test_entry_scope_empty_after_underscore():
    """Test with empty string after final underscore."""
    entry = {"event": "prefix_"}
    result = _entry_scope(entry)
    assert result == ""


def test_entry_scope_uppercase_input():
    """Test that uppercase input is capitalized (first upper, rest as-is)."""
    entry = {"event": "prefix_UPPERCASE"}
    result = _entry_scope(entry)
    # capitalize() makes first char upper, rest lower
    assert result == "Uppercase"


def test_entry_scope_mixed_case_input():
    """Test mixed case input."""
    entry = {"event": "prefix_MiXeD"}
    result = _entry_scope(entry)
    assert result == "Mixed"


# Test with realistic data


def test_entry_scope_realistic_xp_unspent():
    """Test with realistic XP unspent event."""
    entry = {"event": "award_unspent", "amount": 5, "reason": "Session play"}
    result = _entry_scope(entry)
    assert result == "Unspent"


def test_entry_scope_realistic_xp_lifetime():
    """Test with realistic XP lifetime event."""
    entry = {"event": "award_lifetime", "amount": 5, "reason": "Session play"}
    result = _entry_scope(entry)
    assert result == "Lifetime"


# Test that it only uses the 'event' key


def test_entry_scope_ignores_other_keys():
    """Test that only the 'event' key is used."""
    entry = {
        "event": "xp_unspent",
        "amount": 10,
        "reason": "Test",
        "other_scope": "should_be_ignored",
    }
    result = _entry_scope(entry)
    assert result == "Unspent"


# Test with numbers in scope


def test_entry_scope_with_numbers():
    """Test scope with numbers."""
    entry = {"event": "prefix_scope123"}
    result = _entry_scope(entry)
    assert result == "Scope123"


def test_entry_scope_numbers_only():
    """Test scope that's only numbers."""
    entry = {"event": "prefix_123"}
    result = _entry_scope(entry)
    assert result == "123"
