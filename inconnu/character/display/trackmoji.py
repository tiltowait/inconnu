"""character/display/trackmoji.py - A tool for converting a stress track to emoji."""

from ...constants import DAMAGE

__EMOJIS = {
    DAMAGE.none: "<:no_dmg:883516968777449472>",
    DAMAGE.superficial: "<:sup_dmg:890694337212579930>",
    DAMAGE.aggravated: "<:agg_dmg:883516968727089202>",
    "hunger": "<:hunger:883527494832119858>",
    "no_hunger": "<:no_hunger:883527495394164776>",
    "hu_filled": "<:hu_filled:883532393946972160>",
    "hu_unfilled": "<:hu_unfilled:883532394051809290>",
    "degen": "<:degen:893638753304850452>",
    "stain": "<:stain:883536498950025258>",
    "bp_filled": ":red_circle:",
    "bp_unfilled": ":o:",
}


# Public Methods

def emojify_track(track: str) -> str:
    """Convert a stress track into an emoji string."""
    emoji_track = []
    for box in track:
        emoji_track.append(__emojify_stressbox(box))

    gaps = int((len(emoji_track) - 1) / 5) # Minus 1 so we don't put a dot at multiples of 5
    for pos in range(gaps * 5, 0, -5):
        emoji_track.insert(pos, "∙")

    return " ".join(emoji_track)


def emojify_hunger(level: int) -> str:
    """Create a hunger emoji track."""
    filled = level
    unfilled = 5 - level

    hunger = [__hungermoji(True) for _ in range(filled)]
    unfilled = [__hungermoji(False) for _ in range(unfilled)]
    hunger.extend(unfilled)

    return " ".join(hunger)


def emojify_blood_potency(level: int) -> str:
    """Create a Blood Potency track."""
    if level > 0:
        potency = [__EMOJIS["bp_filled"] for _ in range(level)]
        return " ".join(potency)

    return __EMOJIS["bp_unfilled"]


def emojify_humanity(humanity: int, stains: int) -> str:
    """Create a humanity emoji track."""

    # Humanity fills from the right, to a max of 10. Stains fill from the right
    # and can overlap filled boxes

    # Need: Filled, Overlapped, Empty, Stained

    unfilled = 10 - humanity - stains
    if unfilled < 0:
        overlapped = abs(unfilled)
        stains -= overlapped
        unfilled = 0 # So we don't accidentally add to filled boxes
    else:
        overlapped = 0
    filled = 10 - unfilled - stains - overlapped

    filled = [__humanitymoji(True) for _ in range(filled)]
    overlapped = [__degenerationmoji() for _ in range(overlapped)]
    unfilled = [__humanitymoji(False) for _ in range(unfilled)]
    stains = [__stainmoji() for _ in range(stains)]

    track = filled
    track.extend(overlapped)
    track.extend(unfilled)
    track.extend(stains)

    return " ".join(track)


# Helper Methods

def __emojify_stressbox(box: str):
    """Convert a stress box value to an emoji."""
    if len(box) == 0:
        raise ValueError("Invalid stress box") # Should never happen

    return __EMOJIS[box]


def __hungermoji(hungry: bool) -> str:
    """Return a filled or unfilled hunger emoji."""
    hunger = "hunger" if hungry else "no_hunger"
    return __EMOJIS[hunger]


def __humanitymoji(filled) -> str:
    """Return a filled or unfilled humanity emoji."""
    humanity = "hu_filled" if filled else "hu_unfilled"
    return __EMOJIS[humanity]


def __stainmoji() -> str:
    """Return a stain emoji."""
    return __EMOJIS["stain"]


def __degenerationmoji() -> str:
    """Return a degeneration emoji."""
    return __EMOJIS["degen"]
