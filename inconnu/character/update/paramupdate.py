"""character/update/paramupdate.py - Functions for updating a character's non-trait parameters."""

import asyncio

import inconnu

from ...constants import Damage
from ...vchar import VChar

VALID_SPLATS = ["vampire", "ghoul", "mortal", "thinblood"]


async def update_name(character: VChar, new_name: str) -> str:
    """Update the character's name."""
    if not inconnu.character.valid_name(new_name):
        raise ValueError("Names may only contain letters, numbers, and underscores.")
    if (name_len := len(new_name)) > 30:
        raise ValueError(f"`{new_name}` is too long by {name_len - 30} characters.")

    all_chars = await inconnu.char_mgr.fetchall(character.guild, character.user)
    for char in all_chars:
        if char.name.lower() == new_name.lower():
            raise ValueError(f"You already have a character named `{new_name}`!")

    old_name = character.name
    await character.set_name(new_name)
    inconnu.char_mgr.sort_user(character.guild, character.user)

    return f"Rename `{old_name}` to `{new_name}`."


async def update_splat(character: VChar, new_splat: str) -> str:
    """Update the character's splat."""
    if new_splat not in VALID_SPLATS:
        splats = map(lambda splat: f"`{splat}`", VALID_SPLATS)
        splats = ", ".join(splats)
        raise ValueError(f"The `splat` must be one of: {splats}.")

    await character.set_splat(new_splat)
    return f"Set splat to `{new_splat}`."


async def update_hunger(character: VChar, delta: str) -> str:
    """Update the character's Hunger."""
    return await __update_hunger_potency(character, delta, "hunger", 5)


async def update_potency(character: VChar, delta: str) -> str:
    """Update the character's Blood Potency."""
    return await __update_hunger_potency(character, delta, "potency", 10)


async def __update_hunger_potency(character: VChar, delta: str, key: str, maximum: int) -> str:
    """Update the character's hunger if they are a vampire."""
    if not character.is_vampire:
        raise ValueError(f"Mortals and ghouls do not have {key.title()}.")

    setting = not delta[0] in ["+", "-"]
    try:
        delta = int(delta)
    except ValueError:
        raise ValueError(f"{key.title()} must be a number.")  # pylint: disable=raise-missing-from

    new_value = delta if setting else getattr(character, key) + delta
    if not 0 <= new_value <= maximum:
        raise ValueError(f"{key.title()} {new_value} is not between 0 and {maximum}.")

    if key == "hunger":
        await character.set_hunger(new_value)
        return f"Set Hunger to `{new_value}`."

    await character.set_potency(new_value)
    return f"Set Blood Potency to `{new_value}`."


async def update_health(character: VChar, new_max: str) -> str:
    """Update the character's maximum HP. If decreasing, this truncates from the right."""
    return await __update_track(character, "health", new_max)


async def update_willpower(character: VChar, new_max: str) -> str:
    """Update the character's maximum WP. If decreasing, this truncates from the right."""
    return await __update_track(character, "willpower", new_max)


async def update_humanity(character: VChar, delta: str) -> str:
    """Update the character's humanity rating. If decreasing, this truncates from the right."""
    await __update_humanity(character, "stains", "0")
    return await __update_humanity(character, "humanity", delta)


async def update_stains(character: VChar, delta: str) -> str:
    """Apply or remove superficial health damage."""
    return await __update_humanity(character, "stains", delta)


async def update_sh(character: VChar, delta: str) -> str:
    """Apply or remove superficial health damage."""
    return await __update_damage(character, "health", Damage.SUPERFICIAL, delta)


async def update_ah(character: VChar, delta: str) -> str:
    """Apply or remove aggravated health damage."""
    return await __update_damage(character, "health", Damage.AGGRAVATED, delta)


async def update_sw(character: VChar, delta: str) -> str:
    """Apply or remove superficial health damage."""
    return await __update_damage(character, "willpower", Damage.SUPERFICIAL, delta)


async def update_aw(character: VChar, delta: str) -> str:
    """Apply or remove aggravated health damage."""
    return await __update_damage(character, "willpower", Damage.AGGRAVATED, delta)


async def update_current_xp(character: VChar, delta: str) -> str:
    """Set or modify current XP."""
    return await __update_xp(character, "current", delta)


async def update_total_xp(character: VChar, delta: str) -> str:
    """Set or modify total XP."""
    return await __update_xp(character, "total", delta)


async def __update_track(character: VChar, tracker: str, new_len: str) -> str:
    """
    Update the size of a character's tracker.
    Args:
        character (VChar): The character to update
        tracker (str): "health" or "willpower"
        new_size (str): The tracker's new size

    Does not catch exceptions.
    """
    if tracker not in ["health", "willpower"]:
        raise SyntaxError(f"Unknown tracker {tracker}")

    if new_len[0] in ["+", "-"]:
        raise ValueError(f"You must supply an exact value for {tracker.capitalize()}.")

    track = getattr(character, tracker)  # Get tracker string
    cur_len = len(track)
    new_len = int(new_len)

    # Ensure the tracker is the right size
    minimum = 4 if tracker == "health" else 3  # Minimum size
    if not minimum <= new_len <= 17:
        raise ValueError(f"{tracker.title()} must be between {minimum} and 17.")

    if new_len > cur_len:  # Growing
        track = track.rjust(new_len, Damage.NONE)
    elif new_len < cur_len:
        track = track[-new_len:]

    setter = getattr(character, f"set_{tracker}")
    await setter(track)
    return f"Set {tracker.capitalize()} to `{new_len}`."


# pylint: disable=too-many-arguments
async def __update_damage(character: VChar, tracker: str, dtype: str, delta_str: int) -> str:
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
    if not dtype in [Damage.SUPERFICIAL, Damage.AGGRAVATED]:
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
            damaged = await character.apply_damage(tracker, dtype, delta)
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

            await character.set_damage(tracker, dtype, delta)
            damaged = True

        if not damaged and delta < 1:
            return f"Trying to subtract damage that doesn't exist. (Hint: try `+{abs(delta)}`.)"

        return await __damage_adjust_message(tracker, dtype, delta_str, overflow)

    except ValueError as err:
        raise ValueError(f"Expected a number. Got `{delta_str}`.") from err


async def __damage_adjust_message(tracker, dtype, delta_str, overflow) -> str:
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


async def __update_xp(character: VChar, xp_type: str, delta: str) -> str:
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
        raise SyntaxError(f"Unknown XP type: {xp_type}.")  # Should never be seen

    delta = int(delta)
    new_xp = None

    if setting:
        new_xp = delta
    else:
        current = getattr(character, f"{xp_type.lower()}_xp")
        new_xp = current + delta

    # Make sure we can fit the XP. The only way this will happen is if someone
    # is explicitly trying to break the bot, but ...

    if new_xp > 9223372036854775807:
        raise ValueError("`lifetime_xp` may not exceed 9,223,372,036,854,775,807!")

    # When displaying the update, we want to say whether they are doing a delta vs
    # set and, if doing a delta, the *final* amound added/subtracted, after doing
    # bounds-checking.
    current = character.current_xp
    if xp_type == "current":
        await character.set_current_xp(new_xp)
        cur_delta = character.current_xp - current
        if setting:
            return f"Set current/unspent XP to `{new_xp}`."
        return f"`{cur_delta:+}` current/unspent XP."

    total = character.total_xp
    await character.set_total_xp(new_xp)
    tot_delta = character.total_xp - total
    cur_delta = character.current_xp - current

    if setting:
        return f"Set unspent XP to `{character.current_xp}`.\nSet lifetime XP to `{new_xp}`."
    return f"`{cur_delta:+}` unspent XP.\n`{tot_delta:+}` lifetime XP."


async def __update_humanity(character: VChar, hu_type: str, delta: str) -> str:
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
        await character.set_humanity(new_value)
        return f"Set Humanity to `{new_value}`."

    tasks = []
    # If a character enters degeneration, they automatically take AW damage
    message = f"Set Stains to `{new_value}`."
    delta = new_value - character.stains

    if delta > 0 and new_value > (10 - character.humanity):
        # We are in degeneration; calculate the overlap
        old_overlap = abs(min(10 - character.humanity - character.stains, 0))
        new_overlap = abs(10 - character.humanity - new_value)
        overlap_delta = new_overlap - old_overlap

        tasks.append(character.apply_damage("willpower", Damage.AGGRAVATED, overlap_delta))
        message += f"\n**Degeneration!** `+{overlap_delta}` Aggravated Willpower damage."

    tasks.append(character.set_stains(new_value))
    await asyncio.gather(*tasks)

    return message
