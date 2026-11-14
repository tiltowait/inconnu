"""Player-character model."""

import bisect
import copy
import math
import random
from collections import Counter
from collections.abc import Callable
from enum import StrEnum
from functools import total_ordering
from typing import Any, ClassVar, Self

from beanie import Document, Insert, Replace, Save, SaveChanges, before_event
from loguru import logger
from pydantic import ConfigDict, Field
from pymongo import ASCENDING

import errors
from constants import ATTRIBUTES, DISCIPLINES, SKILLS, UNIVERSAL_TRAITS, Damage
from models.impairment import Impairment
from models.vchardocs import (
    BlushState,
    MacroUpdate,
    TraitMatch,
    VCharExperience,
    VCharExperienceEntry,
    VCharHeader,
    VCharLog,
    VCharMacro,
    VCharProfile,
    VCharTrait,
)


class Tracker(StrEnum):
    """An enum to avoid stringly typing database fields."""

    HEALTH = "health"
    WILLPOWER = "willpower"


@total_ordering
class VChar(Document):
    """A vampire, mortal, ghoul, or thin-blood character."""

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, validate_assignment=True
    )

    class Settings:
        name = "characters"
        use_state_management = True
        validate_on_save = True
        indexes = [
            [("guild", ASCENDING), ("user", ASCENDING)],
            "log.left",  # Culling
        ]

    VAMPIRE_TRAITS: ClassVar[list[str]] = ["Hunger", "Potency", "Surge", "Bane", "PowerBonus"]
    MIN_TRACKER: ClassVar[int] = 3
    MAX_TRACKER: ClassVar[int] = 25
    SPC_OWNER: ClassVar[int] = 0

    # Ownership
    guild: int
    user: int

    # Basic stats used in trackers
    raw_name: str = Field(alias="name")
    splat: str
    health: str
    willpower: str
    raw_humanity: int = Field(alias="humanity")
    stains: int = Field(default=0)
    raw_hunger: int = Field(default=1, alias="hunger")
    potency: int
    raw_traits: list[VCharTrait] = Field(default_factory=list, alias="traits")

    # Biographical/profile data
    profile: VCharProfile = Field(default_factory=VCharProfile)
    convictions: list[str] = Field(default_factory=list)
    header: VCharHeader = Field(default_factory=VCharHeader)

    # Misc/convenience
    macros: list[VCharMacro] = Field(default_factory=list)
    experience: VCharExperience = Field(default_factory=VCharExperience)
    log: VCharLog = Field(default_factory=VCharLog)

    @before_event(Insert)
    def pre_insert(self):
        """Last-minute prep."""
        if self.splat == "thinblood":
            self.splat = "thin-blood"

        self.reset_blush()
        self.note_worst_damage()

        logger.info("VCHAR: Created {}", self.name)

    @before_event(Save, Replace, SaveChanges)
    def pre_update(self):
        """Clamp values within required bounds, and keep the Blush consistent
        with changes to Humanity and splat."""
        if self.is_vampire:
            self.hunger = max(0, min(5, self.hunger))
        else:
            self.hunger = 0
        self.potency = max(0, min(10, self.potency))
        self.stains = max(0, min(10, self.stains))
        self.experience.unspent = max(0, min(self.experience.unspent, self.experience.lifetime))

        if self.splat == "thinblood":
            self.splat = "thin-blood"

        if not self.can_blush:
            self.header.blush = BlushState.NA
        elif self.header.blush == BlushState.NA:
            self.header.blush = BlushState.OFF

        logger.info("VCHAR: {} will update", self.name)

    # Comparators

    def __lt__(self, other: Self) -> bool:
        return self.name.casefold() < other.name.casefold()

    def __eq__(self, other: object) -> bool:
        """Just check the IDs."""
        return isinstance(other, VChar) and self.id == other.id

    # Synthetic properties

    @property
    def id_str(self) -> str:
        """The ObjectId's string value."""
        return str(self.id)

    @property
    def name(self) -> str:
        """The character's name plus an indicator if it's an SPC."""
        if not self.is_pc:
            return self.raw_name + " (SPC)"
        return self.raw_name

    @name.setter
    def name(self, new_name: str):
        """Set the character's name."""
        self.raw_name = new_name

    @property
    def hunger(self) -> int:
        """Get the character's Hunger rating."""
        if self.is_vampire:
            return self.raw_hunger
        return 0

    @hunger.setter
    def hunger(self, new_hunger: int):
        """Set the character's Hunger rating."""
        new_hunger = max(0, min(new_hunger, 5))
        self.raw_hunger = new_hunger

    @property
    def humanity(self) -> int:
        """The character's Humanity rating."""
        return self.raw_humanity

    @humanity.setter
    def humanity(self, new_humanity: int):
        """Set the character's new Humanity rating, clamped, and wipe stains."""
        new_humanity = max(0, min(new_humanity, 10))
        self.raw_humanity = new_humanity
        self.stains = 0

    @property
    def traits(self) -> list[VCharTrait]:
        """A copy of the character's traits."""
        return copy.deepcopy(self.raw_traits)

    @traits.setter
    def traits(self, value: list[VCharTrait]):
        """Set the character's traits (used by beanie rollback)."""
        self.raw_traits = value

    @property
    def has_biography(self) -> bool:
        """Whether the character has a biography set."""
        return any([self.profile.biography, self.profile.description])

    @property
    def profile_image_url(self) -> str | None:
        """Get the URL of the first profile image."""
        return self.profile.images[0] if self.profile.images else None

    def random_image_url(self) -> str | None:
        """Get a random image URL."""
        return random.choice(self.profile.images) if self.profile.images else None

    @property
    def aggravated_hp(self) -> int:
        """The amount of Aggravated Health damage sustained."""
        return self.health.count(Damage.AGGRAVATED)

    def set_aggravated_hp(self, new_value: int):
        """Set the Aggravated Health damage."""
        self.set_damage(Tracker.HEALTH, Damage.AGGRAVATED, new_value, wrap=False)

    @property
    def aggravated_wp(self) -> int:
        """The amount of Aggravated Willpower damage sustained."""
        return self.willpower.count(Damage.AGGRAVATED)

    @property
    def willpower_recovery(self) -> int:
        """The amount of Superficial Willpower damage healed per night."""
        try:
            resolve = self.find_trait("Resolve").rating
        except errors.TraitNotFound:
            resolve = 0

        try:
            composure = self.find_trait("Composure").rating
        except errors.TraitNotFound:
            composure = 0

        return max(resolve, composure)

    @property
    def superficial_wp(self) -> int:
        """The amount of Superficial Willpower damage sustained."""
        return self.willpower.count(Damage.SUPERFICIAL)

    def set_superficial_wp(self, new_value: int):
        """Set the Superficial Willpower damage."""
        self.set_damage(Tracker.WILLPOWER, Damage.SUPERFICIAL, new_value, wrap=True)

    @property
    def superficial_hp(self) -> int:
        """The amount of Superficial Health damage sustained."""
        return self.health.count(Damage.SUPERFICIAL)

    def set_lifetime_xp(self, new_lifetime_xp: int):
        """Set the lifetime XP and adjust unspent by the delta."""
        new_lifetime_xp = max(0, new_lifetime_xp)
        delta = new_lifetime_xp - self.experience.lifetime

        self.experience.lifetime = new_lifetime_xp
        self.experience.unspent += delta

    def reset_blush(self):
        """Turn off the Blush of Life, or mark it N/A if the character can't Blush."""
        self.header.blush = BlushState.OFF if self.can_blush else BlushState.NA

    def blush(self):
        """Turn on the Blush of Life and count it, if the character can Blush.
        Blushing again while it's on still counts."""
        if self.can_blush:
            self.set_blush(BlushState.ON)
            self.log.times_blushed += 1

    def set_blush(self, new_blush: BlushState):
        """Toggle the character's Blush of Life."""
        if self.header.blush == new_blush:
            logger.debug("VCHAR: {}'s Blush of Life ({}) is unchanged", self.name, new_blush)
            return
        if self.can_blush:
            # Not checked by header, because a vampire whose header was set at
            # Humanity 9+ has Blush N/A
            self.header.blush = new_blush
            logger.debug("VCHAR: Setting {}'s Blush of Life to {}", self.name, new_blush)
        else:
            logger.debug("Can't set Blush of Life; {} can't Blush", self.name)

    # Derived attributes

    @property
    def degeneration(self) -> bool:
        """Whether the character is in degeneration."""
        return self.stains > (10 - self.humanity)

    @property
    def incapacitated(self) -> bool:
        """Whether the character's Health is entirely Aggravated (torpor or death)."""
        return self.health.count(Damage.AGGRAVATED) == len(self.health)

    @property
    def physically_impaired(self) -> bool:
        """Whether the character is physically impaired: every Health box is damaged,
        or they're in degeneration."""
        return Damage.NONE not in self.health or self.degeneration

    @property
    def mentally_impaired(self) -> bool:
        """Whether the character is mentally impaired: every Willpower box is damaged,
        or they're in degeneration."""
        return Damage.NONE not in self.willpower or self.degeneration

    @property
    def impairment_state(self) -> Impairment:
        """Which kinds of pools the character's impairment penalizes."""
        state = Impairment.NONE
        if self.physically_impaired:
            state |= Impairment.PHYSICAL
        if self.mentally_impaired:
            state |= Impairment.MENTAL
        return state

    @property
    def is_pc(self) -> bool:
        """Whether the character is a PC."""
        return self.user != VChar.SPC_OWNER

    @property
    def is_spc(self) -> bool:
        """Whether the character is an SPC."""
        return not self.is_pc

    @property
    def is_vampire(self) -> bool:
        """Whether the character is a vampire."""
        return self.splat in {"vampire", "thin-blood"}

    @property
    def can_blush(self) -> bool:
        """Whether the character can use the Blush of Life, which only full
        vampires below Humanity 9 need."""
        return self.is_vampire and not self.is_thin_blood and self.humanity < 9

    @property
    def is_ghoul(self) -> bool:
        """Whether the character is a bool."""
        return self.splat == "ghoul"

    @property
    def is_thin_blood(self) -> bool:
        """Whether the character is thin-blooded."""
        return self.splat == "thin-blood"

    @property
    def surge(self) -> int:
        """The number of dice added to a Blood Surge."""
        return math.ceil(self.potency / 2) + 1

    @property
    def mend_amount(self) -> int:
        """The amount of Superficial damage recovered when mending."""
        if self.is_vampire:
            mends = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5}
            return mends[self.potency]

        # Mortal or ghoul
        return self.find_trait("Stamina", exact=True).rating

    @property
    def frenzy_resist(self) -> int:
        """The dice pool for resisting frenzy. Equal to current WP + 1/3 Humanity."""
        cur_wp = self.willpower.count(Damage.NONE)
        third_hu = int(self.humanity / 3)
        return max(cur_wp + third_hu, 1)

    @property
    def bane_severity(self) -> int:
        """The character's bane severity."""
        if self.potency == 0:
            return 0
        return math.ceil(self.potency / 2) + 1

    @property
    def bane(self) -> int:
        """Shorthand for bane_severity. Used in traits."""
        return self.bane_severity

    @property
    def power_bonus(self) -> int:
        """The character's power bonus."""
        if not self.is_vampire:
            return 0
        return self.potency // 2

    # Traits

    @property
    def _inherent_traits(self) -> list[VCharTrait]:
        """Get this character's inherent traits."""
        if self.is_vampire:
            inherents = UNIVERSAL_TRAITS
        else:
            inherents = (t for t in UNIVERSAL_TRAITS if t not in VChar.VAMPIRE_TRAITS)

        traits = []
        for inherent in inherents:
            rating = getattr(self, inherent.lower())
            if isinstance(rating, str):
                # Tracker string, so get the undamaged count
                rating = rating.count(Damage.NONE)
            traits.append(VCharTrait(name=inherent, rating=rating, type=VCharTrait.Type.INHERENT))

        return traits

    @property
    def _all_traits(self) -> list[VCharTrait]:
        """A copy of all the character's traits, including inherent traits."""
        return self.traits + self._inherent_traits

    def has_trait(self, name: str) -> bool:
        """Determine whether a character has a given trait."""
        for trait in self.raw_traits:
            if trait.matching(name, True):
                return True
        return False

    def find_trait(self, name: str, exact=False) -> TraitMatch:
        """
        Finds the closest matching trait.
        Raises AmbiguousTraitError if more than one are found.
        """
        found = []

        for trait in self._all_traits:
            if matches := trait.matching(name, exact):
                for match in matches:
                    if match.exact:
                        return match
            found.extend(matches)

        if not found:
            raise errors.TraitNotFound(self, name)

        if len(found) > 1:
            keys = (m.key for m in found)
            raise errors.AmbiguousTraitError(name, keys)

        # One single match found
        return found[0]

    def assign_traits(
        self, traits: dict[str, int], category=VCharTrait.Type.CUSTOM
    ) -> tuple[str, dict[str, int]]:
        """Add traits to the character. Overwrites old traits if they exist."""
        for name in traits:
            if name.lower() in map(str.lower, UNIVERSAL_TRAITS):
                raise ValueError(f"`{name}` is a reserved trait and can't be added")

        assignments: dict[str, int] = {}
        counter: Counter[Tracker] = Counter()

        for input_name, input_rating in traits.items():
            updated = False
            for trait in self.raw_traits:
                if trait.matching(input_name, True):
                    if trait.name in ("Resolve", "Composure"):
                        counter[Tracker.WILLPOWER] += input_rating - trait.rating
                    elif trait.name == "Stamina":
                        counter[Tracker.HEALTH] += input_rating - trait.rating

                    trait.rating = input_rating
                    assignments[trait.name] = input_rating
                    updated = True

            if not updated:
                # Automatically categorize attributes and skills (helps with chargen)
                if input_name in ATTRIBUTES:
                    assigned_category = VCharTrait.Type.ATTRIBUTE
                elif input_name in SKILLS:
                    assigned_category = VCharTrait.Type.SKILL
                elif input_name.lower() in map(str.lower, DISCIPLINES):
                    assigned_category = VCharTrait.Type.DISCIPLINE
                else:
                    assigned_category = category

                new_trait = VCharTrait(
                    name=input_name,
                    rating=input_rating,
                    type=assigned_category.value,
                )
                bisect.insort(self.raw_traits, new_trait, key=lambda t: t.name.casefold())
                assignments[input_name] = input_rating

        # Traits added; now adjust HP/WP
        adjustments = []

        for track, delta in counter.items():
            if delta and self.adjust_tracker_rating(track, len(getattr(self, track)) + delta):
                adjustments.append(track.title())

        if adjustments:
            adjustment = " and ".join(adjustments)
            verb = "have" if len(adjustments) > 1 else "has"
            adjustment_text = f"{adjustment} {verb} been adjusted accordingly."
        else:
            adjustment_text = ""

        return adjustment_text, assignments

    def delete_trait(self, name: str) -> str:
        """Delete a trait. Raises TraitNotFound if the trait doesn't exist."""
        for index, trait in enumerate(self.raw_traits):
            if trait.matching(name, True):
                del self.raw_traits[index]
                return trait.name

        raise errors.TraitNotFound(self, name)

    def add_powers(self, trait_name: str, powers: list[str] | str) -> tuple[VCharTrait, list[str]]:
        """Add powers to a Discipline and return a copy."""
        return self._add_subtraits(trait_name, powers, VCharTrait.add_powers)

    def add_specialties(
        self, trait_name: str, specialties: list[str] | str
    ) -> tuple[VCharTrait, list[str]]:
        """Add specialties to a trait and return a copy of that trait."""
        return self._add_subtraits(trait_name, specialties, VCharTrait.add_specialties)

    def _add_subtraits(
        self,
        trait_name: str,
        specialties: list[str] | str,
        action: Callable,
    ) -> tuple[VCharTrait, list[str]]:
        """The actual work of adding subtraits."""
        for trait in self.raw_traits:
            if trait.matching(trait_name, True):
                before = set(trait.specialties)
                action(trait, specialties)
                after = set(trait.specialties)
                delta = sorted(after.symmetric_difference(before))

                return copy.deepcopy(trait), delta

        raise errors.TraitNotFound(self, trait_name)

    def remove_specialties(
        self, trait_name: str, specialties: list[str] | str
    ) -> tuple[VCharTrait, list[str]]:
        """Remove specialties from a trait."""
        for trait in self.raw_traits:
            if trait.matching(trait_name, True):
                before = set(trait.specialties)
                trait.remove_specialties(specialties)
                after = set(trait.specialties)
                delta = sorted(after.symmetric_difference(before))

                return copy.deepcopy(trait), delta

        raise errors.TraitNotFound(self, trait_name)

    # Macros!

    def _macro_index(self, search: str) -> int:
        """Find a macro's index. Raises MacroNotFoundError if not found."""
        lower = search.lower()
        for index, macro in enumerate(self.macros):
            if macro.name.lower() == lower:
                return index

        raise errors.MacroNotFoundError(f"**{self.name}** has no macro named `{search}`.")

    def find_macro(self, search: str) -> VCharMacro:
        """
        Find a macro by name.
        Raises MacroNotFoundError if the macro wasn't found.
        """
        index = self._macro_index(search)
        return self.macros[index]

    def add_macro(self, **kwargs: Any):
        """
        Create and store a macro.
        Raises MacroAlreadyExistsError if the macro already exists.
        """
        try:
            _ = self._macro_index(kwargs["name"])
            raise errors.MacroAlreadyExistsError(
                f"You already have a macro named `{kwargs['name']}`."
            )
        except errors.MacroNotFoundError:
            pass

        macro = VCharMacro(**kwargs)
        bisect.insort(self.macros, macro, key=lambda m: m.name.casefold())

        logger.debug("VCHAR: {}: Added new macro {}", self.name, macro.name)

    def update_macro(self, search: str, update: MacroUpdate) -> str:
        """Update a macro."""
        macro = self.find_macro(search)
        for field, value in update.items():
            setattr(macro, field, value)

        if "name" in update:
            self.macros.sort(key=lambda m: m.name.casefold())

        return macro.name

    def delete_macro(self, search: str):
        """
        Delete a macro.
        Raises MacroNotFoundError if the macro doesn't exist.
        """
        index = self._macro_index(search)
        del self.macros[index]

    # Specialized mutators

    def adjust_tracker_rating(self, track: Tracker, new_rating: int) -> bool:
        """Resize Health or Willpower, keeping its damage: boxes are added and
        removed at the undamaged end. The rating is clamped to MIN_TRACKER and
        MAX_TRACKER. Returns True if it changed."""
        current_track: str = getattr(self, track)
        new_rating = max(self.MIN_TRACKER, min(new_rating, self.MAX_TRACKER))
        delta = new_rating - len(current_track)
        if delta == 0:
            return False

        if delta > 0:
            new_track = Damage.NONE * delta + current_track
        else:
            new_track = current_track[-delta:]

        setattr(self, track, new_track)
        return True

    def set_damage(self, tracker: Tracker, severity: Damage, amount: int, wrap=False):
        """
        Set the current damage level.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): Damage.SUPERFICIAL or Damage.AGGRAVATED
            amount (int): The amount to set it to
        """
        if severity not in (Damage.SUPERFICIAL, Damage.AGGRAVATED):
            raise SyntaxError("Severity must be superficial or aggravated.")
        if tracker not in (Tracker.HEALTH, Tracker.WILLPOWER):
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = getattr(self, tracker)
        sup = cur_track.count(Damage.SUPERFICIAL)
        agg = cur_track.count(Damage.AGGRAVATED)

        if severity == Damage.SUPERFICIAL:
            sup = amount

            if wrap:
                overflow = sup + agg - len(cur_track)
                if overflow > 0:
                    agg += overflow
        else:
            agg = amount

        unhurt = (len(cur_track) - sup - agg) * Damage.NONE
        sup = sup * Damage.SUPERFICIAL
        agg = agg * Damage.AGGRAVATED

        new_track = unhurt + sup + agg
        new_track = new_track[-len(cur_track) :]  # Shrink it if necessary

        if new_track == cur_track:
            # No need to do anything if the track is unchanged
            return

        was_impaired = self.impairment_state != Impairment.NONE
        if tracker == Tracker.HEALTH:
            self.health = new_track
        else:
            self.willpower = new_track

        # Log it!
        self._count_impairment(was_impaired)
        old_agg = cur_track.count(Damage.AGGRAVATED)
        old_sup = cur_track.count(Damage.SUPERFICIAL)
        new_agg = new_track.count(Damage.AGGRAVATED)
        new_sup = new_track.count(Damage.SUPERFICIAL)

        self._count_damage(tracker, new_sup - old_sup, new_agg - old_agg)

    def _count_impairment(self, was_impaired: bool):
        """Count the character becoming impaired, if they weren't already."""
        if not was_impaired and self.impairment_state != Impairment.NONE:
            self.log.times_impaired += 1

    @staticmethod
    def damage_severity(track: str) -> float:
        """How badly a track is damaged: 3 per Superficial and 10 per Aggravated,
        divided by its length, so the same damage is worse on a shorter track."""
        if not track:
            return 0
        score = 3 * track.count(Damage.SUPERFICIAL) + 10 * track.count(Damage.AGGRAVATED)
        return score / len(track)

    def _count_damage(self, tracker: Tracker, superficial: int, aggravated: int):
        """Count damage taken, and keep the track if it's the worst it has been.
        Healing isn't counted."""
        superficial, aggravated = max(superficial, 0), max(aggravated, 0)
        log = self.log
        if tracker == Tracker.HEALTH:
            log.health_superficial += superficial
            log.health_aggravated += aggravated
        else:
            log.willpower_superficial += superficial
            log.willpower_aggravated += aggravated
        self.note_worst_damage()

    def note_worst_damage(self):
        """Snapshot each track that's the worst it has been, or that has no
        snapshot yet. Called when damage is set, when the character is created,
        and by the character manager on load, which gives characters from
        before the snapshots their first ones. Not called on save, so resizing
        a track (often a mistake, quickly undone) never sets a snapshot."""
        log = self.log
        if not log.worst_health or (
            self.damage_severity(self.health) > self.damage_severity(log.worst_health)
        ):
            log.worst_health = self.health
        if not log.worst_willpower or (
            self.damage_severity(self.willpower) > self.damage_severity(log.worst_willpower)
        ):
            log.worst_willpower = self.willpower

    def apply_damage(self, tracker: Tracker, severity: Damage, delta: int) -> bool:
        """
        Apply Superficial damage.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): Damage.SUPERFICIAL or Damage.AGGRAVATED
            delta (int): The amount to apply
        If the damage exceeds the tracker, it will wrap around to aggravated.
        Returns True if there was damage to apply. Returns False if not.
        Damage won't be applied if delta is 0 or if we are subtracting damage when
            there is none.
        """
        if severity not in (Damage.SUPERFICIAL, Damage.AGGRAVATED):
            raise SyntaxError("Severity must be superficial or aggravated.")
        if tracker not in (Tracker.HEALTH, Tracker.WILLPOWER):
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = getattr(self, tracker)
        cur_dmg = cur_track.count(severity)
        new_dmg = cur_dmg + delta

        if delta < 0 and cur_dmg == 0:
            return False

        self.set_damage(tracker, severity, new_dmg, wrap=True)
        return True

    def add_stains(self, delta: int, *, log: bool) -> int:
        """
        Add (or remove) Stains, clamped to 0-10. Each Stain that overflows the
        boxes Humanity leaves empty deals 1 Aggravated Willpower damage.
        Args:
            delta (int): The number of Stains to add; negative removes them
            log (bool): Whether to count Stains gained and degeneration in the
                log (False for manual updates)
        Returns the Aggravated Willpower damage dealt.
        """
        unfilled = 10 - self.humanity
        new_stains = max(0, min(10, self.stains + delta))
        old_overflow = max(self.stains - unfilled, 0)
        new_overflow = max(new_stains - unfilled, 0)
        damage = max(new_overflow - old_overflow, 0)

        if damage > 0:
            self.apply_damage(Tracker.WILLPOWER, Damage.AGGRAVATED, damage)

        if log:
            self.log.stains_gained += max(new_stains - self.stains, 0)
            if old_overflow == 0 and new_overflow > 0:
                self.log.degenerations += 1
            self.log.deepest_degeneration = max(self.log.deepest_degeneration, new_overflow)

        # After the damage, which counts any impairment it causes itself
        was_impaired = self.impairment_state != Impairment.NONE
        self.stains = new_stains
        if log:
            self._count_impairment(was_impaired)

        return damage

    def apply_experience(self, amount: int, scope: str, reason: str, admin: int):
        """
        Add or remove experience from a character.
        Args:
            amount: The amount of XP to add/subtract
            scope: Unspent or lifetime XP
            reason: The reason for the application
            admin; The Discord ID of the admin who added/deducted
        Zero amounts are ignored and not logged.
        """
        if amount == 0:
            return

        event_verb = "award" if amount > 0 else "deduct"
        event = VCharExperienceEntry(
            event=f"{event_verb}_{scope}",
            amount=amount,
            reason=reason,
            admin=admin,
        )
        self.experience.log.append(event)
        logger.info("VCHAR: {}: Experience event: {}", self.name, event)

        if scope == "lifetime":
            self.set_lifetime_xp(self.experience.lifetime + amount)
        else:
            self.experience.unspent += amount
