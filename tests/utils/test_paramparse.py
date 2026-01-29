"""Tests for utils.paramparse module."""

import pytest
from collections import OrderedDict

from utils.paramparse import parse_parameters


# Basic parsing tests


def test_basic_key_value():
    """Test basic key=value parsing."""
    result = parse_parameters("name=John", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John")])


def test_multiple_parameters():
    """Test parsing multiple key=value pairs."""
    result = parse_parameters("name=John age=30 city=Boston", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John"), ("age", "30"), ("city", "Boston")])


def test_multi_word_values():
    """Test parsing values with multiple words."""
    result = parse_parameters("name=John Doe title=Senior Developer", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John Doe"), ("title", "Senior Developer")])


def test_colon_separator():
    """Test that colons are converted to equals signs."""
    result = parse_parameters("name:John age:30", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John"), ("age", "30")])


def test_mixed_separators():
    """Test mixing = and : separators."""
    result = parse_parameters("name=John age:30", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John"), ("age", "30")])


# Plus/minus operator tests


def test_plus_equals_operator():
    """Test += operator parsing."""
    result = parse_parameters("health+=5", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "+5")])


def test_minus_equals_operator():
    """Test -= operator parsing."""
    result = parse_parameters("health-=3", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "-3")])


def test_plus_equals_with_spaces():
    """Test += operator with various spacing."""
    result = parse_parameters("health + = 5", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "+5")])

    result = parse_parameters("health= +5", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "+5")])

    result = parse_parameters("health =+ 5", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "+5")])


def test_negative_values():
    """Test negative number values."""
    result = parse_parameters("health=-10", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "-10")])


# rewrite_plus_minus flag tests


def test_rewrite_plus_minus_enabled():
    """Test that key+value becomes key+=value when rewrite_plus_minus=True."""
    result = parse_parameters("health+5", rewrite_plus_minus=True)
    assert result == OrderedDict([("health", "+5")])

    result = parse_parameters("health-3", rewrite_plus_minus=True)
    assert result == OrderedDict([("health", "-3")])


def test_rewrite_plus_minus_with_spaces():
    """Test rewrite_plus_minus with various spacing."""
    result = parse_parameters("health + 5", rewrite_plus_minus=True)
    assert result == OrderedDict([("health", "+5")])

    result = parse_parameters("health- 3", rewrite_plus_minus=True)
    assert result == OrderedDict([("health", "-3")])


def test_rewrite_plus_minus_disabled():
    """Test that + and - in values are preserved when rewrite_plus_minus=False."""
    # When disabled, key+value without = should fail or preserve the + in value
    # Let's test that it doesn't get converted
    result = parse_parameters("name=John+Doe", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John+Doe")])


def test_rewrite_plus_minus_complex():
    """Test rewrite_plus_minus with multiple parameters."""
    result = parse_parameters("health+5 willpower-2 name=John", rewrite_plus_minus=True)
    assert result == OrderedDict([("health", "+5"), ("willpower", "-2"), ("name", "John")])


# Whitespace handling


def test_extra_whitespace():
    """Test handling of extra whitespace in values."""
    result = parse_parameters("name=John   Doe age=30", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John   Doe"), ("age", "30")])


def test_value_with_leading_trailing_spaces():
    """Test that values are stripped of leading/trailing spaces."""
    result = parse_parameters("name=  John  ", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "John")])


# Underscore in keys


def test_underscore_in_keys():
    """Test that underscores are allowed in keys."""
    result = parse_parameters("sup_hp=5 agg_wp=2", rewrite_plus_minus=False)
    assert result == OrderedDict([("sup_hp", "5"), ("agg_wp", "2")])


# Error cases


def test_duplicate_keys_error():
    """Test that duplicate keys raise ValueError."""
    with pytest.raises(ValueError, match="You cannot use `name` more than once"):
        parse_parameters("name=John name=Jane", rewrite_plus_minus=False)


def test_invalid_syntax_no_equals():
    """Test that invalid syntax raises SyntaxError."""
    with pytest.raises(SyntaxError, match="Invalid syntax"):
        parse_parameters("invalid syntax here", rewrite_plus_minus=False)


def test_invalid_syntax_number_start():
    """Test that keys starting with numbers are invalid."""
    # Keys must start with letter or underscore
    with pytest.raises(SyntaxError, match="Invalid syntax"):
        parse_parameters("123key=value", rewrite_plus_minus=False)


# Edge cases


def test_empty_string():
    """Test parsing empty string."""
    result = parse_parameters("", rewrite_plus_minus=False)
    assert result == OrderedDict()


def test_single_character_values():
    """Test single character values."""
    result = parse_parameters("a=b c=d", rewrite_plus_minus=False)
    assert result == OrderedDict([("a", "b"), ("c", "d")])


def test_numeric_values():
    """Test numeric values."""
    result = parse_parameters("health=100 damage=25", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "100"), ("damage", "25")])


def test_empty_value():
    """Test empty value (key= with nothing after)."""
    result = parse_parameters("name=", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "")])


def test_ordered_dict_preservation():
    """Test that OrderedDict preserves insertion order."""
    result = parse_parameters("z=1 y=2 x=3 w=4", rewrite_plus_minus=False)
    keys = list(result.keys())
    assert keys == ["z", "y", "x", "w"]


# Real-world usage examples from the codebase


def test_character_update_syntax():
    """Test parsing character update parameters."""
    result = parse_parameters("health=10 willpower=8 humanity=7", rewrite_plus_minus=False)
    assert result == OrderedDict([("health", "10"), ("willpower", "8"), ("humanity", "7")])


def test_tracker_adjustment_syntax():
    """Test parsing tracker adjustments with +/-."""
    result = parse_parameters("sh=+2 ah=-1 stains=+3", rewrite_plus_minus=False)
    assert result == OrderedDict([("sh", "+2"), ("ah", "-1"), ("stains", "+3")])


def test_mixed_update_syntax():
    """Test mixing absolute values and adjustments."""
    result = parse_parameters("name=New Name health+=5 hunger-=1", rewrite_plus_minus=False)
    assert result == OrderedDict([("name", "New Name"), ("health", "+5"), ("hunger", "-1")])
