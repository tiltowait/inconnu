"""Tests for errors.py."""

import errors


def test_ambiguous_trait_lists_matches():
    """A short list of matches is shown in full."""
    err = errors.AmbiguousTraitError("s", (name for name in ["Stamina", "Strength"]))

    assert str(err) == "`s` is ambiguous. Do you mean: `Stamina`, `Strength`?"
    assert err.matches == ["Stamina", "Strength"]  # Kept, though given a generator


def test_ambiguous_trait_truncates_matches():
    """Long lists show the first few and count the rest, so the message stays
    short enough to send."""
    matches = [f"Brawl.Spec{i}" for i in range(errors.AmbiguousTraitError.MAX_SHOWN + 5)]
    err = errors.AmbiguousTraitError("b.", matches)

    shown = ", ".join(f"`{match}`" for match in matches[: errors.AmbiguousTraitError.MAX_SHOWN])
    assert str(err) == f"`b.` is ambiguous. Do you mean: {shown}, and 5 more?"
    assert err.matches == matches
