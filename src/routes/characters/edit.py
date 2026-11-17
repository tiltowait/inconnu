"""Applying the web app's character edits. Edits are corrections: they never
touch the Chronicle log or experience."""

from fastapi.exceptions import RequestValidationError

from constants import Damage
from models import VChar
from models.vchar import Tracker
from models.vchardocs import VCharTrait
from routes.characters.models import (
    EditBody,
    ErrorLoc,
    conviction_too_long,
    long_convictions,
    trait_errors,
    with_core_traits,
)
from services import char_mgr

MAX_SUMMARY_LENGTH = 4000  # Embed descriptions max out at 4096
SEVERITIES = ((Damage.SUPERFICIAL, "Superficial"), (Damage.AGGRAVATED, "Aggravated"))


async def check_edit(char: VChar, body: EditBody):
    """Run the checks that need the character. Raises RequestValidationError,
    so the app gets FastAPI's own 422 shape, with every error at once."""
    errors: list[tuple[ErrorLoc, str]] = []

    # Attributes may keep their specialties, but not gain any
    kept = {t.name.casefold(): t.raw_subtraits for t in char.raw_traits if t.is_attribute}
    errors.extend((("traits", *loc), msg) for loc, msg in trait_errors(body.traits, kept))

    for index, limit in long_convictions(body.convictions, char.convictions):
        errors.append((("convictions", index), conviction_too_long(limit)))

    if body.name.casefold() != char.raw_name.casefold():
        # Changing only capitalization is fine
        if await char_mgr.has_character(char.guild, char.user, body.name):
            errors.append((("name",), f"There's already a character named `{body.name}`."))

    if char.is_vampire:
        for field in ("potency", "hunger"):
            if getattr(body, field) is None:
                errors.append(((field,), "Required for vampires."))
        # Discord allows thin-bloods any Potency, so only check a new one
        if char.is_thin_blood and body.potency not in (None, char.potency) and body.potency > 2:
            errors.append((("potency",), "Thin-bloods must have Blood Potency between 0 and 2."))
    else:
        for field in ("potency", "hunger"):
            if getattr(body, field) is not None:
                errors.append(((field,), f"{char.splat.title()}s don't have {field.title()}."))

    if errors:
        raise RequestValidationError(
            [{"loc": ("body", *loc), "msg": msg, "type": "value_error"} for loc, msg in errors]
        )


def apply_edit(char: VChar, body: EditBody):
    """Assign the editable fields. Assigns raw fields, because the properties
    have side effects (the Humanity setter wipes Stains, for instance)."""
    char.raw_name = body.name
    char.health = body.health
    char.willpower = body.willpower
    char.raw_humanity = body.humanity
    char.stains = body.stains
    if char.is_vampire:
        # check_edit() makes sure these are present
        if body.potency is not None:
            char.potency = body.potency
        if body.hunger is not None:
            char.raw_hunger = body.hunger
    char.convictions = [conviction for conviction in body.convictions if conviction]
    char.profile.description = body.profile.description
    char.profile.biography = body.profile.biography
    char.raw_traits = with_core_traits(body.traits)


def summarize(old: VChar, new: VChar) -> list[str]:
    """Describe the differences between two versions of a character."""
    changes: list[str] = []

    if old.raw_name != new.raw_name:
        changes.append(f"Rename `{old.raw_name}` to `{new.raw_name}`.")

    for tracker in Tracker:
        old_track: str = getattr(old, tracker)
        new_track: str = getattr(new, tracker)
        if len(old_track) != len(new_track):
            changes.append(f"Set {tracker.title()} to `{len(new_track)}`.")
        for severity, label in SEVERITIES:
            if (count := new_track.count(severity)) != old_track.count(severity):
                changes.append(f"Set {label} {tracker.title()} damage to `{count}`.")

    ratings = [
        ("raw_humanity", "Humanity"),
        ("stains", "Stains"),
        ("potency", "Blood Potency"),
        ("raw_hunger", "Hunger"),
    ]
    for field, label in ratings:
        if (value := getattr(new, field)) != getattr(old, field):
            changes.append(f"Set {label} to `{value}`.")

    if old.convictions != new.convictions:
        changes.append("Edited Convictions.")
    if old.profile.description != new.profile.description:
        changes.append("Edited description.")
    if old.profile.biography != new.profile.biography:
        changes.append("Edited biography.")

    changes.extend(_trait_changes(old.raw_traits, new.raw_traits))
    return changes


def _trait_changes(old: list[VCharTrait], new: list[VCharTrait]) -> list[str]:
    """Describe added, removed, and changed traits, in name order."""
    old_traits = {t.name.casefold(): t for t in old}
    new_traits = {t.name.casefold(): t for t in new}
    changes: list[str] = []

    for key in sorted(old_traits.keys() | new_traits.keys()):
        before = old_traits.get(key)
        after = new_traits.get(key)
        if after is None:
            if before is not None:
                changes.append(f"Removed `{before.name}`.")
            continue
        if before is None:
            changes.append(f"Added `{after.name}`: `{after.rating}`.")
            before = VCharTrait(name=after.name, rating=after.rating, type=after.type)
        elif after.rating != before.rating or after.name != before.name:
            changes.append(f"Set `{after.name}` to `{after.rating}`.")

        old_subs = {s.casefold(): s for s in before.raw_subtraits}
        new_subs = {s.casefold(): s for s in after.raw_subtraits}
        if added := [s for k, s in new_subs.items() if k not in old_subs]:
            changes.append(f"`{after.name}`: added {_join(added)}.")
        if removed := [s for k, s in old_subs.items() if k not in new_subs]:
            changes.append(f"`{after.name}`: removed {_join(removed)}.")

    return changes


def _join(items: list[str]) -> str:
    """Backtick and comma-join some names."""
    return ", ".join(f"`{item}`" for item in items)


def edit_summary(char: VChar, editor_id: int, changes: list[str]) -> str:
    """The update channel's summary of an edit, in the style of /character
    update."""
    lines = "\n".join(f"* {change}" for change in changes)
    if len(lines) > MAX_SUMMARY_LENGTH:
        lines = lines[:MAX_SUMMARY_LENGTH].rsplit("\n", 1)[0] + "\n* …"
    return f"__<@{editor_id}> updated {char.name} on the web:__\n{lines}"
