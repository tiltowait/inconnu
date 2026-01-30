"""character/display/trackmoji.py - A tool for converting a stress track to emoji."""

import services


def emojify_track(track: str) -> str:
    """Convert a stress track into an emoji string."""
    emoji_track = []
    for box in track:
        emoji_track.append(__emojify_stressbox(box))

    gaps = int((len(emoji_track) - 1) / 5)  # Minus 1 so we don't put a dot at multiples of 5
    for pos in range(gaps * 5, 0, -5):
        emoji_track.insert(pos, "∙")

    return " ".join(emoji_track)


def emojify_hunger(level: int) -> str:
    """Create a hunger emoji track."""
    filled = level
    unfilled = 5 - level

    hunger = __hungermoji(True, filled)
    unfilled = __hungermoji(False, unfilled)
    hunger.extend(unfilled)

    return " ".join(hunger)


def emojify_blood_potency(level: int) -> str:
    """Create a Blood Potency track."""
    if level > 0:
        potency = services.emojis.get("bp_filled", level)
        return " ".join(potency)

    return services.emojis["bp_unfilled"]


def emojify_humanity(humanity: int, stains: int) -> str:
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

    filled = __humanitymoji(True, filled)
    overlapped = __degenerationmoji(overlapped)
    unfilled = __humanitymoji(False, unfilled)
    stains = __stainmoji(stains)

    track = filled
    track.extend(overlapped)
    track.extend(unfilled)
    track.extend(stains)

    return " ".join(track)


# Helper Methods


def __emojify_stressbox(box: str):
    """Convert a stress box value to an emoji."""
    if not box:
        raise ValueError("Invalid stress box")  # Should never happen

    return services.emojis[box]


def __hungermoji(hungry: bool, count: int) -> str:
    """Return a filled or unfilled hunger emoji."""
    hunger = "hunger" if hungry else "no_hunger"
    return services.emojis.get(hunger, count)


def __humanitymoji(filled, count) -> str:
    """Return a filled or unfilled humanity emoji."""
    humanity = "hu_filled" if filled else "hu_unfilled"
    return services.emojis.get(humanity, count)


def __stainmoji(count: int) -> str:
    """Return a stain emoji."""
    return services.emojis.get("stain", count)


def __degenerationmoji(count: int) -> str:
    """Return a degeneration emoji."""
    return services.emojis.get("degen", count)
