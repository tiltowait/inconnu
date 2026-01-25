"""character/update/paramupdate.py - Functions for updating a character's non-trait parameters."""

from typing import TYPE_CHECKING

import inconnu
from inconnu.constants import Damage

if TYPE_CHECKING:
    from inconnu.models import VChar

VALID_SPLATS = ["vampire", "ghoul", "mortal", "thinblood"]


async def update_name(character: "VChar", new_name: str) -> str:
    """Update the character's name."""
    if not inconnu.character.valid_name(new_name):
        raise ValueError("Names may only contain letters, numbers, and underscores.")
    if (name_len := len(new_name)) > 30:
        raise ValueError(f"`{new_name}` is too long by {name_len - 30} characters.")

    if character.name == new_name:
        raise ValueError(f"{new_name} is already this character's name!")
    if character.name.lower() != new_name.lower():
        # We want to let them rename a character to fix capitalization
        all_chars = await inconnu.char_mgr.fetchall(character.guild, character.user)
        for char in all_chars:
            if char.name.lower() == new_name.lower():
                raise ValueError(f"You already have a character named `{new_name}`!")

    old_name = character.name
    character.name = new_name
    inconnu.char_mgr.sort_user(character.guild, character.user)

    return f"Rename `{old_name}` to `{new_name}`."


def update_splat(character: "VChar", new_splat: str) -> str:
    """Update the character's splat."""
    if new_splat not in VALID_SPLATS:
        splats = map(lambda splat: f"`{splat}`", VALID_SPLATS)
        splats = ", ".join(splats)
        raise ValueError(f"The `splat` must be one of: {splats}.")

    character.splat = new_splat
    return f"Set splat to `{new_splat}`."


def update_hunger(character: "VChar", delta: str) -> str:
    """Update the character's Hunger."""
    return __update_hunger_potency(character, delta, "hunger", 5)


def update_potency(character: "VChar", delta: str) -> str:
    """Update the character's Blood Potency."""
    return __update_hunger_potency(character, delta, "potency", 10)


def __update_hunger_potency(character: "VChar", delta: str, key: str, maximum: int) -> str:
    """Update the character's hunger if they are a vampire."""
    if not character.is_vampire:
        raise ValueError(f"Mortals and ghouls do not have {key.title()}.")

    setting = delta[0] not in ["+", "-"]
    try:
        delta = int(delta)
    except ValueError:
        raise ValueError(f"{key.title()} must be a number.") from None

    new_value = delta if setting else getattr(character, key) + delta
    if not 0 <= new_value <= maximum:
        raise ValueError(f"{key.title()} {new_value} is not between 0 and {maximum}.")

    if key == "hunger":
        character.hunger = new_value
        return f"Set Hunger to `{new_value}`."

    character.potency = new_value
    return f"Set Blood Potency to `{new_value}`."


def update_health(character: "VChar", new_max: str) -> str:
    """Update the character's maximum HP. If decreasing, this truncates from the right."""
    return __update_track(character, "health", new_max)


def update_willpower(character: "VChar", new_max: str) -> str:
    """Update the character's maximum WP. If decreasing, this truncates from the right."""
    return __update_track(character, "willpower", new_max)


def update_humanity(character: "VChar", delta: str) -> str:
    """Update the character's humanity rating. If decreasing, this truncates from the right."""
    __update_humanity(character, "stains", "0")
    return __update_humanity(character, "humanity", delta)


def update_stains(character: "VChar", delta: str) -> str:
    """Apply or remove superficial health damage."""
    return __update_humanity(character, "stains", delta)


def update_sh(character: "VChar", delta: str) -> str:
    """Apply or remove superficial health damage."""
    return __update_damage(character, "health", Damage.SUPERFICIAL, delta)


def update_ah(character: "VChar", delta: str) -> str:
    """Apply or remove aggravated health damage."""
    return __update_damage(character, "health", Damage.AGGRAVATED, delta)


def update_sw(character: "VChar", delta: str) -> str:
    """Apply or remove superficial health damage."""
    return __update_damage(character, "willpower", Damage.SUPERFICIAL, delta)


def update_aw(character: "VChar", delta: str) -> str:
    """Apply or remove aggravated health damage."""
    return __update_damage(character, "willpower", Damage.AGGRAVATED, delta)


def update_current_xp(character: "VChar", delta: str) -> str:
    """Set or modify current XP."""
    return __update_xp(character, "unspent", delta)


def update_total_xp(character: "VChar", delta: str) -> str:
    """Set or modify total XP."""
    return __update_xp(character, "lifetime", delta)


def __update_track(character: "VChar", tracker: str, new_len: str) -> str:
    """
    Update the size of a character's tracker.
    Args:
        character (VChar): The character to update
        tracker (str): "health" or "willpower"
        new_size (str): The tracker's new size

    Does not catch exceptions.
    """
    if tracker not in {"health", "willpower"}:
        raise SyntaxError(f"Unknown tracker {tracker}")

    if new_len[0] in ["+", "-"]:
        raise ValueError(f"You must supply an exact value for {tracker.capitalize()}.")

    track = getattr(character, tracker)  # Get tracker string
    cur_len = len(track)
    new_len = int(new_len)

    # Ensure the tracker is the right size
    if not 3 <= new_len <= 25:
        raise ValueError(f"{tracker.title()} must be between 3 and 25.")

    if new_len > cur_len:  # Growing
        track = track.rjust(new_len, Damage.NONE)
    elif new_len < cur_len:
        track = track[-new_len:]

    setattr(character, tracker, track)
    return f"Set {tracker.capitalize()} to `{new_len}`."


def __update_damage(character: "VChar", tracker: str, dtype: str, delta_str: int) -> str:
    """
    Update a character's tracker damage.
    Args:
        character (VChar): The character to update
        tracker (str): "health" or "willpower"
        type (str): "/" or "x"
        delta (int): The amount to add or remove

    Raises ValueError if delta_str can't be made an integer.
    """
    if tracker not in {"health", "willpower"}:
        raise SyntaxError(f"Unknown tracker {tracker}")
    if dtype not in {Damage.SUPERFICIAL, Damage.AGGRAVATED}:
        raise SyntaxError(f"Unknown damage type: {dtype}")

    # If the user doesn't supply a sign, they are setting the damage total rather
    # than modifying it

    try:
        delta = int(delta_str)

        if delta == 0 and delta_str[0] in ["+", "-"]:
            return "Can't adjust by 0 damage. Nothing to do."

        # delta_str can be an int if called by another command
        if isinstance(delta_str, str) and delta_str[0] in ["+", "-"]:
            # If they are applying superficial damage, it can wrap.
            old_agg = getattr(character, tracker).count(Damage.AGGRAVATED)
            damaged = character.apply_damage(tracker, dtype, delta)
            new_agg = getattr(character, tracker).count(Damage.AGGRAVATED)
            overflow = new_agg - old_agg if dtype == Damage.SUPERFICIAL else 0
        else:
            # Setting damage
            # First, figure out if they're setting too much damage
            track_len = len(getattr(character, tracker))

            if dtype == Damage.SUPERFICIAL:
                track = getattr(character, tracker)
                available = track_len - track.count(Damage.AGGRAVATED)
            else:
                # Aggravated damage
                available = track_len

            if delta > available:
                overflow = delta - available
            else:
                overflow = 0

            character.set_damage(tracker, dtype, delta)
            damaged = True

        if not damaged and delta < 1:
            return f"Trying to subtract damage that doesn't exist. (Hint: try `+{abs(delta)}`.)"

        return __damage_adjust_message(tracker, dtype, delta_str, overflow)

    except ValueError as err:
        raise ValueError(f"Expected a number. Got `{delta_str}`.") from err


def __damage_adjust_message(tracker, dtype, delta_str, overflow) -> str:
    """Generate a human-readable damage adjustment message."""
    if dtype == Damage.SUPERFICIAL:
        severity = "Superficial"
    else:
        severity = "Aggravated"

    if delta_str[0] in ["+", "-"]:
        msg = f"`{delta_str}` {severity} {tracker.title()} damage."
        if overflow > 0:
            msg += f" `{overflow}` wrapped to Aggravated."

        return msg

    attempted_damage = int(delta_str)
    applied_damage = attempted_damage - overflow

    msg = f"Set {severity} {tracker.title()} damage to `{applied_damage}`."

    if overflow > 0:
        msg += f" (Attempted `{attempted_damage}`, but available track exceeded by `{overflow}`.)"

    return msg


def __update_xp(character: "VChar", xp_type: str, delta: str) -> str:
    """
    Update a character's XP.
    Args:
        character (VChar): The character to update
        xp_type (str): "lifetime" or "unspent"
        delta (str): The amount to add or remove

    Does not catch exceptions.
    """
    setting = False

    # If the user doesn't supply a sign, they are setting the XP total rather
    # than modifying it
    if isinstance(delta, str):
        if delta[0] not in ["+", "-"]:
            setting = True

    if xp_type not in {"lifetime", "unspent"}:
        raise SyntaxError(f"Unknown XP type: {xp_type}.")  # Should never be seen

    delta = int(delta)
    new_xp = None

    if setting:
        new_xp = delta
    else:
        current = getattr(character.experience, xp_type)
        new_xp = current + delta

    # Make sure we can fit the XP. The only way this will happen is if someone
    # is explicitly trying to break the bot, but ...

    if new_xp > 9223372036854775807:
        raise ValueError("`lifetime_xp` may not exceed 9,223,372,036,854,775,807!")

    # When displaying the update, we want to say whether they are doing a delta vs
    # set and, if doing a delta, the *final* amound added/subtracted, after doing
    # bounds-checking.
    current = character.experience.unspent
    if xp_type == "unspent":
        character.experience.unspent = new_xp
        cur_delta = character.experience.unspent - current
        if setting:
            return f"Set current/unspent XP to `{new_xp}`."
        return f"`{cur_delta:+}` current/unspent XP."

    total = character.experience.lifetime
    character.set_lifetime_xp(new_xp)
    tot_delta = character.experience.lifetime - total
    cur_delta = character.experience.unspent - current

    if setting:
        return (
            f"Set unspent XP to `{character.experience.unspent}`.\nSet lifetime XP to `{new_xp}`."
        )
    return f"`{cur_delta:+}` unspent XP.\n`{tot_delta:+}` lifetime XP."


def __update_humanity(character: "VChar", hu_type: str, delta: str) -> str:
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

        character.apply_damage("willpower", Damage.AGGRAVATED, overlap_delta)
        message += f"\n**Degeneration!** `+{overlap_delta}` Aggravated Willpower damage."

    character.stains = new_value
    return message
