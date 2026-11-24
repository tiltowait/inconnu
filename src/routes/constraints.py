"""The bot's validation constraints, served so the web app checks input the
same way the bot does."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from constants import (
    MAX_CONVICTION_LENGTH,
    MAX_CONVICTIONS,
    MAX_HUMANITY,
    MAX_HUNGER,
    MAX_POTENCY,
    MAX_PROFILE_LENGTH,
    MAX_STAINS,
    MAX_THIN_BLOOD_POTENCY,
    MAX_TRAIT_RATING,
)
from models.vchar import Tracker, VChar
from models.vchardocs import VCharSplat
from routes.auth import verify_api_key
from utils.validation import (
    HUNGER_ALIASES,
    HUNGER_WORD,
    MACRO_STAINING,
    MAX_MACRO_COMMENT_LENGTH,
    MAX_MACRO_DIFFICULTY,
    MAX_MACRO_NAME_LENGTH,
    MAX_MACRO_ROUSES,
    MAX_NAME_LENGTH,
    MAX_TRAIT_LENGTH,
    POWER_BONUS_KEYS,
    RESERVED_TRAIT_KEYS,
    VALID_MACRO_NAME_PATTERN,
    VALID_NAME_PATTERN_JS,
    VALID_TRAIT_PATTERN,
)

router = APIRouter()


class Range(BaseModel):
    """An inclusive range of allowed values."""

    min: int
    max: int


def _tracker_ranges() -> dict[Tracker, Range]:
    """The allowed Health and Willpower box counts."""
    ranges: dict[Tracker, Range] = {}
    for tracker in Tracker:
        low, high = VChar.tracker_limits(tracker)
        ranges[tracker] = Range(min=low, max=high)
    return ranges


def _splat_ranges(maximums: dict[VCharSplat, int]) -> dict[VCharSplat, Range | None]:
    """A range for every splat: 0 to its maximum, or None for splats missing
    from maximums, which don't have the stat."""
    return {
        splat: Range(min=0, max=maximums[splat]) if splat in maximums else None
        for splat in VCharSplat
    }


def _potency_ranges() -> dict[VCharSplat, Range | None]:
    """The allowed Blood Potency for each splat."""
    return _splat_ranges(
        {VCharSplat.VAMPIRE: MAX_POTENCY, VCharSplat.THIN_BLOOD: MAX_THIN_BLOOD_POTENCY}
    )


def _hunger_ranges() -> dict[VCharSplat, Range | None]:
    """The allowed Hunger for each splat."""
    return _splat_ranges({VCharSplat.VAMPIRE: MAX_HUNGER, VCharSplat.THIN_BLOOD: MAX_HUNGER})


class Constraints(BaseModel):
    """What the bot accepts for character names, traits, and sheet values.
    Character, trait, and specialty names are checked after collapsing
    whitespace and straightening curly apostrophes (U+2018, U+2019), so the
    app should do the same first. Lengths count code points, not UTF-16 units
    (in JS, [...name].length). Trait comparisons use name keys: casefolded,
    spaces removed."""

    # A JS pattern; use it with the u flag
    name_pattern: str = VALID_NAME_PATTERN_JS
    name_max_length: int = MAX_NAME_LENGTH
    # Shared by traits, specialties, and powers
    trait_pattern: str = VALID_TRAIT_PATTERN.pattern
    trait_max_length: int = MAX_TRAIT_LENGTH
    trait_rating: Range = Range(min=0, max=MAX_TRAIT_RATING)
    # Name keys no trait may have
    reserved_traits: list[str] = Field(
        default_factory=lambda: sorted([*RESERVED_TRAIT_KEYS, *POWER_BONUS_KEYS])
    )
    # No word after a trait's first may be a prefix of hunger_word or one of
    # hunger_aliases (case-insensitive), since rolls read it as Hunger
    hunger_word: str = HUNGER_WORD
    hunger_aliases: list[str] = list(HUNGER_ALIASES)
    conviction_count: int = MAX_CONVICTIONS
    conviction_max_length: int = MAX_CONVICTION_LENGTH
    profile_max_length: int = MAX_PROFILE_LENGTH
    trackers: dict[Tracker, Range] = Field(default_factory=_tracker_ranges)
    humanity: Range = Range(min=0, max=MAX_HUMANITY)
    stains: Range = Range(min=0, max=MAX_STAINS)
    # By splat. None means the splat doesn't have the stat, so requests must
    # leave it out
    hunger: dict[VCharSplat, Range | None] = Field(default_factory=_hunger_ranges)
    potency: dict[VCharSplat, Range | None] = Field(default_factory=_potency_ranges)
    macro_name_pattern: str = VALID_MACRO_NAME_PATTERN.pattern
    macro_name_max_length: int = MAX_MACRO_NAME_LENGTH
    macro_comment_max_length: int = MAX_MACRO_COMMENT_LENGTH
    macro_difficulty: Range = Range(min=0, max=MAX_MACRO_DIFFICULTY)
    macro_rouses: Range = Range(min=0, max=MAX_MACRO_ROUSES)
    macro_staining: list[str] = list(MACRO_STAINING)


CONSTRAINTS = Constraints()


@router.get("/constraints", dependencies=[Depends(verify_api_key)])
async def get_constraints() -> Constraints:
    """The bot's validation constraints."""
    return CONSTRAINTS
