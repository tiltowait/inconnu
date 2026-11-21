"""character/display/trackmoji.py - A tool for converting a stress track to emoji."""

import services
from constants import Theme


def emojify_track(theme: Theme, track: str) -> str:
    """Convert a stress track into an emoji string."""
    emoji_track = []
    for box in track:
        emoji_track.append(__emojify_stressbox(theme, box))

    gaps = int((len(emoji_track) - 1) / 5)  # Minus 1 so we don't put a dot at multiples of 5
    for pos in range(gaps * 5, 0, -5):
        emoji_track.insert(pos, "∙")

    return " ".join(emoji_track)


def emojify_hunger(theme: Theme, level: int) -> str:
    """Create a hunger emoji track."""
    filled = level
    unfilled = 5 - level

    hunger = __hungermoji(theme, True, filled)
    unfilled = __hungermoji(theme, False, unfilled)
    hunger.extend(unfilled)

    return " ".join(hunger)


def emojify_blood_potency(theme: Theme, level: int) -> str:
    """Create a Blood Potency track."""
    if level > 0:
        potency = services.emojis.get(theme, "bp_filled", level)
        return " ".join(potency)

    return services.emojis.emoji(theme, "bp_unfilled")


def emojify_humanity(theme: Theme, humanity: int, stains: int) -> str:
    """Create a humanity emoji track."""

    # Humanity fills from the right, to a max of 10. Stains fill from the right
    # and can overlap filled boxes

    # Need: Filled, Overlapped, Empty, Stained

    unfilled = 10 - humanity - stains
    if unfilled < 0:
        overlapped = abs(unfilled)
        stains -= overlapped
        unfilled = 0  # So we don't accidentally add to filled boxes
    else:
        overlapped = 0
    filled = 10 - unfilled - stains - overlapped

    filled = __humanitymoji(theme, True, filled)
    overlapped = __degenerationmoji(theme, overlapped)
    unfilled = __humanitymoji(theme, False, unfilled)
    stain_emojis = __stainmoji(theme, stains)

    track = filled
    track.extend(overlapped)
    track.extend(unfilled)
    track.extend(stain_emojis)

    return " ".join(track)


# Helper Methods


def __emojify_stressbox(theme: Theme, box: str) -> str:
    """Convert a stress box value to an emoji."""
    if not box:
        raise ValueError("Invalid stress box")  # Should never happen

    return services.emojis.emoji(theme, box)


def __hungermoji(theme: Theme, hungry: bool, count: int) -> list[str]:
    """Return a filled or unfilled hunger emoji."""
    hunger = "hunger" if hungry else "no_hunger"
    return services.emojis.get(theme, hunger, count)


def __humanitymoji(theme: Theme, filled: bool, count: int) -> list[str]:
    """Return a filled or unfilled humanity emoji."""
    humanity = "hu_filled" if filled else "hu_unfilled"
    return services.emojis.get(theme, humanity, count)


def __stainmoji(theme: Theme, count: int) -> list[str]:
    """Return a stain emoji."""
    return services.emojis.get(theme, "stain", count)


def __degenerationmoji(theme: Theme, count: int) -> list[str]:
    """Return a degeneration emoji."""
    return services.emojis.get(theme, "degen", count)
