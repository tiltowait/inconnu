"""update/paramupdate.py - Functions for updating a character's non-trait parameters."""

import re

from ..constants import DAMAGE
from ..vchar import VChar

VALID_SPLATS = ["vampire", "ghoul", "mortal"]


def update_name(character: VChar, new_name: str):
    """Update the character's name."""
    if not re.match(r"[A-z_]+", new_name):
        raise ValueError("Names may only contain letters and underscores.")

    character.name = new_name


def update_splat(character: VChar, new_splat: str):
    """Update the character's splat."""
    if new_splat not in VALID_SPLATS:
        splats = map(lambda splat: f"`{splat}`", VALID_SPLATS)
        splats = ", ".join(splats)
        raise ValueError(f"The `splat` must be one of: {splats}.")

    character.splat = new_splat


def update_hunger(character: VChar, delta: str):
    """Update the character's Hunger."""
    __update_hunger_potency(character, delta, "hunger", 5)


def update_potency(character: VChar, delta: str):
    """Update the character's Blood Potency."""
    __update_hunger_potency(character, delta, "potency", 10)


def __update_hunger_potency(character: VChar, delta: str, key: str, maximum: int):
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
    else:
        character.potency = new_value


def update_health(character: VChar, new_max: str):
    """Update the character's maximum HP. If decreasing, this truncates from the right."""
    __update_track(character, "health", new_max)


def update_willpower(character: VChar, new_max: str):
    """Update the character's maximum WP. If decreasing, this truncates from the right."""
    __update_track(character, "willpower", new_max)


def update_humanity(character: VChar, delta: str):
    """Update the character's humanity rating. If decreasing, this truncates from the right."""
    __update_humanity(character, "humanity", delta)
    __update_humanity(character, "stains", "0")


def update_stains(character: VChar, delta: str):
    """Apply or remove superficial health damage."""
    __update_humanity(character, "stains", delta)


def update_sh(character: VChar, delta: str):
    """Apply or remove superficial health damage."""
    __update_damage(character, "health", DAMAGE.superficial, delta)


def update_ah(character: VChar, delta: str):
    """Apply or remove aggravated health damage."""
    __update_damage(character, "health", DAMAGE.aggravated, delta)


def update_sw(character: VChar, delta: str):
    """Apply or remove superficial health damage."""
    __update_damage(character, "willpower", DAMAGE.superficial, delta)


def update_aw(character: VChar, delta: str):
    """Apply or remove aggravated health damage."""
    __update_damage(character, "willpower", DAMAGE.aggravated, delta)


def update_current_xp(character: VChar, delta: str):
    """Set or modify current XP."""
    __update_xp(character, "current", delta)


def update_total_xp(character: VChar, delta: str):
    """Set or modify total XP."""
    __update_xp(character, "total", delta)


def __update_track(character: VChar, tracker: str, new_len: int):
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

    if new_len > cur_len: # Growing
        track = track.rjust(new_len, DAMAGE.none)
    elif new_len < cur_len:
        track = track[-new_len:]

    if tracker == "health":
        character.health = track
    else:
        character.willpower = track


# pylint: disable=too-many-arguments
def __update_damage(character: VChar, tracker: str, dtype: str, delta: int):
    """
    Update a character's tracker damage.
    Args:
        character (VChar): The character to update
        tracker (str): "health" or "willpower"
        type (str): "/" or "x"
        delta (int): The amount to add or remove

    Does not catch exceptions.
    """
    setting = False

    # If the user doesn't supply a sign, they are setting the XP total rather
    # than modifying it
    if isinstance(delta, str):
        if delta[0] not in ["+", "-"]:
            setting = True

    delta = int(delta)

    if tracker not in ["health", "willpower"]:
        raise SyntaxError(f"Unknown tracker {tracker}")

    if not dtype in [DAMAGE.superficial, DAMAGE.aggravated]:
        raise SyntaxError(f"Unknown damage type: {dtype}")

    track = getattr(character, tracker) # Get
    track_size = len(track)

    fine = track.count(DAMAGE.none)
    sup = track.count(DAMAGE.superficial)
    agg = track.count(DAMAGE.aggravated)

    if dtype == DAMAGE.superficial:
        sup = delta if setting else sup + delta
    else:
        agg = delta if setting else agg + delta

    fine = DAMAGE.none * fine
    sup = DAMAGE.superficial * sup
    agg = DAMAGE.aggravated * agg

    track = f"{fine}{sup}{agg}"

    if len(track) > track_size:
        track = track[-track_size:]
    else:
        track = track.rjust(track_size, DAMAGE.none)

    if tracker == "health":
        character.health = track
    else:
        character.willpower = track


def __update_xp(character: VChar, xp_type: str, delta: str):
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
    else:
        character.total_xp = new_xp


def __update_humanity(character: VChar, hu_type: str, delta: str):
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
    else:
        character.stains = new_value
