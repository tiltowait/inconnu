"""update/paramupdate.py - Functions for updating a character's non-trait parameters."""

import re

from ..constants import character_db, DAMAGE, valid_splats


async def update_name(charid: int, new_name: str):
    """Update the character's name."""
    if not re.match(r"[A-z_]+", new_name):
        raise ValueError("Names may only contain letters and underscores.")

    await character_db.rename_character(charid, new_name)


async def update_splat(charid: int, new_splat: str):
    """Update the character's splat."""
    try:
        splat = valid_splats[new_splat]
        await character_db.set_splat(charid, splat)
    except KeyError:
        splats = map(lambda splat: f"`{splat}`", valid_splats)
        splats = ", ".join(splats)
        raise ValueError(f"The `splat` must be one of: {splats}.") # pylint: disable=raise-missing-from


async def update_hunger(charid: int, delta: str):
    """Update the character's Hunger."""
    await __update_hunger_potency(charid, delta, "hunger", 5)


async def update_potency(charid: int, delta: str):
    """Update the character's Blood Potency."""
    await __update_hunger_potency(charid, delta, "potency", 10)


async def __update_hunger_potency(charid: int, delta: str, key: str, maximum: int):
    """Update the character's hunger if they are a vampire."""
    splat = await character_db.get_splat(charid)
    if splat != 0: # Not a vampire
        raise ValueError("Mortals and ghouls do not have Hunger.")

    setting = not delta[0] in ["+", "-"]
    try:
        delta = int(delta)
    except ValueError:
        raise ValueError(f"{key.title()} must be a number.") # pylint: disable=raise-missing-from

    new_value = delta if setting else await getattr(character_db, f"get_{key}")(charid) + delta
    if not 0 <= new_value <= maximum:
        raise ValueError(f"{key.title()} {new_value} is not between 0 and {maximum}.")

    await getattr(character_db, f"set_{key}")(charid, new_value)


async def update_health(charid: int, new_max: str):
    """Update the character's maximum HP. If decreasing, this truncates from the right."""
    await __update_track(charid, "health", new_max)


async def update_willpower(charid: int, new_max: str):
    """Update the character's maximum WP. If decreasing, this truncates from the right."""
    __update_track(charid, "willpower", new_max)


async def update_humanity(charid: int, delta: str):
    """Update the character's humanity rating. If decreasing, this truncates from the right."""
    await __update_humanity(charid, "humanity", delta)
    await __update_humanity(charid, "stains", "0")


async def update_stains(charid: int, delta: str):
    """Apply or remove superficial health damage."""
    await __update_humanity(charid, "stains", delta)


async def update_sh(charid: int, delta: str):
    """Apply or remove superficial health damage."""
    await __update_damage(charid, "health", DAMAGE.superficial, delta)


async def update_ah(charid: int, delta: str):
    """Apply or remove aggravated health damage."""
    await __update_damage(charid, "health", DAMAGE.aggravated, delta)


async def update_sw(charid: int, delta: str):
    """Apply or remove superficial health damage."""
    await __update_damage(charid, "willpower", DAMAGE.superficial, delta)


async def update_aw(charid: int, delta: str):
    """Apply or remove aggravated health damage."""
    await __update_damage(charid, "willpower", DAMAGE.aggravated, delta)


async def update_current_xp(charid: int, delta: str):
    """Set or modify current XP."""
    await __update_xp(charid, "current", delta)


async def update_total_xp(charid: int, delta: str):
    """Set or modify total XP."""
    await __update_xp(charid, "total", delta)


async def __update_track(charid: int, tracker: str, new_len: int):
    """
    Update the size of a character's tracker.
    Args:
        charid (int): The character's database ID
        tracker (str): "health" or "willpower"
        new_size (int): The tracker's new size

    Does not catch exceptions.
    """
    if tracker not in ["health", "willpower"]:
        raise SyntaxError(f"Unknown tracker {tracker}")

    track = await getattr(character_db, f"get_{tracker}")(charid) # Get tracker string

    cur_len = len(track)
    new_len = int(new_len)

    if new_len > cur_len: # Growing
        track = track.rjust(new_len, DAMAGE.none)
    elif new_len < cur_len:
        track = track[-new_len:]

    await getattr(character_db, f"set_{tracker}")(charid, track) # Set the tracker


# pylint: disable=too-many-arguments
async def __update_damage(charid: int, tracker: str, dtype: str, delta: int):
    """
    Update a character's tracker damage.
    Args:
        guildid (int): The guild's Discord ID
        userid (int): The user's Discord ID
        charid (int): The character's database ID
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

    track = await getattr(character_db, f"get_{tracker}")(charid) # Get
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

    await getattr(character_db, f"set_{tracker}")(charid, track) # Set


async def __update_xp(charid: int, xp_type: str, delta: str):
    """
    Update a character's XP.
    Args:
        guildid (int): The guild's Discord ID
        userid (int): The user's Discord ID
        charid (int): The character's database ID
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
        current = await getattr(character_db, f"get_{xp_type.lower()}_xp")(charid)
        new_xp = current + delta

    await getattr(character_db, f"set_{xp_type.lower()}_xp")(charid, new_xp)


async def __update_humanity(charid: int, hu_type: str, delta: str):
    """
    Update a character's humanity or stains.
    Args:
        charid (int): The character's database ID
        xp_type (str): "humanity" or "stains"
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
        current = await getattr(character_db, f"get_{hu_type}")(charid)
        new_value = current + delta

    if not 0 <= new_value <= 10:
        raise ValueError(f"{hu_type.title()} must be between 0 and 10.")

    await getattr(character_db, f"set_{hu_type}")(charid, new_value)
