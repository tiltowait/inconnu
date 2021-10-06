"""character/update/paramupdate.py - Functions for updating a character's non-trait parameters."""

import re

from ...constants import DAMAGE
from ...vchar import VChar

VALID_SPLATS = ["vampire", "ghoul", "mortal"]


def update_name(character: VChar, new_name: str) -> str:
    """Update the character's name."""
    if not re.match(r"[A-z_]+", new_name):
        raise ValueError("Names may only contain letters and underscores.")
    if len(new_name) > 30:
        raise ValueError(f"`{new_name}` is too long by {len(new_name) - 30} characters.")

    character.name = new_name
    return f"Set name to `{new_name}`."


def update_splat(character: VChar, new_splat: str) -> str:
    """Update the character's splat."""
    if new_splat not in VALID_SPLATS:
        splats = map(lambda splat: f"`{splat}`", VALID_SPLATS)
        splats = ", ".join(splats)
        raise ValueError(f"The `splat` must be one of: {splats}.")

    character.splat = new_splat
    return f"Set splat to `{new_splat}`."


def update_hunger(character: VChar, delta: str) -> str:
    """Update the character's Hunger."""
    return __update_hunger_potency(character, delta, "hunger", 5)


def update_potency(character: VChar, delta: str) -> str:
    """Update the character's Blood Potency."""
    return __update_hunger_potency(character, delta, "potency", 10)


def __update_hunger_potency(character: VChar, delta: str, key: str, maximum: int) -> str:
    """Update the character's hunger if they are a vampire."""
    if character.splat != "vampire": # Not a vampire
        raise ValueError(f"Mortals and ghouls do not have {key.title()}.")

    setting = not delta[0] in ["+", "-"]
    try:
        delta = int(delta)
    except ValueError:
        raise ValueError(f"{key.title()} must be a number.") # pylint: disable=raise-missing-from

    new_value = delta if setting else getattr(character, key) + delta
    if not 0 <= new_value <= maximum:
        raise ValueError(f"{key.title()} {new_value} is not between 0 and {maximum}.")

    if key == "hunger":
        character.hunger = new_value
        return f"Set Hunger to `{new_value}`."

    character.potency = new_value
    return f"Set Blood Potency to `{new_value}`."


def update_health(character: VChar, new_max: str) -> str:
    """Update the character's maximum HP. If decreasing, this truncates from the right."""
    return __update_track(character, "health", new_max)


def update_willpower(character: VChar, new_max: str) -> str:
    """Update the character's maximum WP. If decreasing, this truncates from the right."""
    return __update_track(character, "willpower", new_max)


def update_humanity(character: VChar, delta: str) -> str:
    """Update the character's humanity rating. If decreasing, this truncates from the right."""
    __update_humanity(character, "stains", "0")
    return __update_humanity(character, "humanity", delta)


def update_stains(character: VChar, delta: str) -> str:
    """Apply or remove superficial health damage."""
    return __update_humanity(character, "stains", delta)


def update_sh(character: VChar, delta: str) -> str:
    """Apply or remove superficial health damage."""
    return __update_damage(character, "health", DAMAGE.superficial, delta)


def update_ah(character: VChar, delta: str) -> str:
    """Apply or remove aggravated health damage."""
    return __update_damage(character, "health", DAMAGE.aggravated, delta)


def update_sw(character: VChar, delta: str) -> str:
    """Apply or remove superficial health damage."""
    return __update_damage(character, "willpower", DAMAGE.superficial, delta)


def update_aw(character: VChar, delta: str) -> str:
    """Apply or remove aggravated health damage."""
    return __update_damage(character, "willpower", DAMAGE.aggravated, delta)


def update_current_xp(character: VChar, delta: str) -> str:
    """Set or modify current XP."""
    return __update_xp(character, "current", delta)


def update_total_xp(character: VChar, delta: str) -> str:
    """Set or modify total XP."""
    return __update_xp(character, "total", delta)


def __update_track(character: VChar, tracker: str, new_len: int) -> str:
    """
    Update the size of a character's tracker.
    Args:
        character (VChar): The character to update
        tracker (str): "health" or "willpower"
        new_size (int): The tracker's new size

    Does not catch exceptions.
    """
    if tracker not in ["health", "willpower"]:
        raise SyntaxError(f"Unknown tracker {tracker}")

    track = getattr(character, tracker) # Get tracker string
    cur_len = len(track)

    new_len = int(new_len)

    # Ensure the tracker is the right size
    minimum = 4 if tracker == "health" else 3 # Minimum size
    if not minimum <= new_len <= 15:
        raise ValueError(f"{tracker.title()} must be between {minimum} and 15.")

    if new_len > cur_len: # Growing
        track = track.rjust(new_len, DAMAGE.none)
    elif new_len < cur_len:
        track = track[-new_len:]

    if tracker == "health":
        character.health = track
        return f"Set Health to `{len(track)}`."

    character.willpower = track
    return f"Set Willpower to `{len(track)}`."


# pylint: disable=too-many-arguments
def __update_damage(character: VChar, tracker: str, dtype: str, delta_str: int) -> str:
    """
    Update a character's tracker damage.
    Args:
        character (VChar): The character to update
        tracker (str): "health" or "willpower"
        type (str): "/" or "x"
        delta (int): The amount to add or remove

    Raises ValueError if delta_str can't be made an integer.
    """
    if tracker not in ["health", "willpower"]:
        raise SyntaxError(f"Unknown tracker {tracker}")
    if not dtype in [DAMAGE.superficial, DAMAGE.aggravated]:
        raise SyntaxError(f"Unknown damage type: {dtype}")

    # If the user doesn't supply a sign, they are setting the XP total rather
    # than modifying it

    try:
        delta = int(delta_str)
        if isinstance(delta_str, str) and delta_str[0] in ["+", "-"]:
            character.apply_damage(tracker, dtype, delta)
        else:
            character.set_damage(tracker, dtype, delta)

        return __damage_adjust_message(tracker, dtype, delta_str)

    except ValueError as err:
        raise ValueError(f"Expected a number. Got `{delta_str}`.") from err


def __damage_adjust_message(tracker, dtype, delta_str) -> str:
    """Generate a human-readable damage adjustment message."""
    if dtype == DAMAGE.superficial:
        severity = "Superficial"
    else:
        severity = "Aggravated"

    if delta_str[0] in ["+", "-"]:
        return f"`{delta_str}` {severity} {tracker.title()} damage."

    return f"Set {severity} {tracker.title()} damage to `{delta_str}`."


def __update_xp(character: VChar, xp_type: str, delta: str) -> str:
    """
    Update a character's XP.
    Args:
        character (VChar): The character to update
        xp_type (str): "total" or "current"
        delta (str): The amount to add or remove

    Does not catch exceptions.
    """
    setting = False

    # If the user doesn't supply a sign, they are setting the XP total rather
    # than modifying it
    if isinstance(delta, str):
        if delta[0] not in ["+", "-"]:
            setting = True

    if not xp_type in ["total", "current"]:
        raise SyntaxError(f"Unknown XP type: {xp_type}.") # Should never be seen

    delta = int(delta)
    new_xp = None

    if setting:
        new_xp = delta
    else:
        current = getattr(character, f"{xp_type.lower()}_xp")
        new_xp = current + delta

    if xp_type == "current":
        character.current_xp = new_xp
        return f"Set current/unspent XP to `{new_xp}`."

    character.total_xp = new_xp
    return f"Set current/unspent XP to `{character.current_xp}.`\nSet total XP to `{new_xp}`."


def __update_humanity(character: VChar, hu_type: str, delta: str) -> str:
    """
    Update a character's humanity or stains.
    Args:
        character (VChar): The character to update
        hu_type (str): "humanity" or "stains"
        delta (str): The amount to add or remove

    Does not catch exceptions.
    """
    if hu_type not in ["humanity", "stains"]:
        raise SyntaxError(f"Unknown humanity syntax: {hu_type}.")

    setting = False
    if isinstance(delta, str):
        if delta[0] not in ["+", "-"]:
            setting = True

    delta = int(delta)
    new_value = delta if setting else None

    if new_value is None:
        current = getattr(character, hu_type)
        new_value = current + delta

    if not 0 <= new_value <= 10:
        raise ValueError(f"{hu_type.title()} must be between 0 and 10.")

    if hu_type == "humanity":
        character.humanity = new_value
        return f"Set Humanity to `{new_value}`."

    # If a character enters degeneration, they automatically take AW damage
    message = f"Set Stains to `{new_value}`."
    delta = new_value - character.stains
    if delta > 0 and new_value > (10 - character.humanity):
        # We are in degeneration; calculate the overlap
        old_overlap = abs(min(10 - character.humanity - character.stains, 0))
        new_overlap = abs(10 - character.humanity - new_value)
        overlap_delta = new_overlap - old_overlap

        character.apply_damage("willpower", DAMAGE.aggravated, overlap_delta)
        message += f"\n**Degeneration!** `+{overlap_delta}` Aggravated Willpower damage."

    character.stains = new_value
    return message
