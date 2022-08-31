"""Player-character model."""
# pylint: disable=missing-class-docstring, too-few-public-methods, abstract-method
# pylint: disable=too-many-public-methods

import bisect
import math
import random
from collections import Counter
from datetime import datetime
from enum import Enum
from types import SimpleNamespace

from umongo import Document, fields

import inconnu
from logger import Logger

from ..constants import INCONNU_ID, UNIVERSAL_TRAITS, Damage
from .vchardocs import (
    VCharExperience,
    VCharExperienceEntry,
    VCharHeader,
    VCharMacro,
    VCharProfile,
)


class _Properties(str, Enum):
    """An enum to avoid stringly typing database fields."""

    USER = "user"
    NAME = "_name"
    SPLAT = "splat"
    HUMANITY = "humanity"
    STAINS = "stains"
    HEALTH = "health"
    WILLPOWER = "willpower"
    HUNGER = "hunger"
    POTENCY = "potency"
    TRAITS = "_traits"
    PROFILE = "profile"
    BIOGRAPHY = "biography"
    DESCRIPTION = "description"
    IMAGES = "images"
    CONVICTIONS = "convictions"
    RP_HEADER = "header"
    MACROS = "macros"


@inconnu.db.instance.register
class VChar(Document):
    """A vampire, mortal, ghoul, or thin-blood character."""

    VAMPIRE_TRAITS = ["Hunger", "Potency", "Surge", "Bane"]

    # Ownership
    guild = fields.IntField()
    user = fields.IntField()

    # Basic stats used in trackers
    _name = fields.StrField(attribute="name")
    splat = fields.StrField()
    health = fields.StrField()
    willpower = fields.StrField()
    humanity = fields.IntField()
    stains = fields.IntField(default=0)
    hunger = fields.IntField(default=1)
    potency = fields.IntField()
    _traits = fields.DictField(attribute="traits")

    # Biographical/profile data
    profile = fields.EmbeddedField(VCharProfile, default=VCharProfile)
    convictions = fields.ListField(fields.StrField, default=list)
    header = fields.EmbeddedField(VCharHeader, default=VCharHeader)

    # Misc/convenience
    macros = fields.ListField(fields.EmbeddedField(VCharMacro), default=list)
    experience = fields.EmbeddedField(VCharExperience, default=VCharExperience)
    stat_log = fields.DictField(default=dict, attribute="log")

    class Meta:
        collection_name = "characters"

    # umongo methods

    def pre_insert(self):
        """Last-minute prep."""
        self.stat_log["created"] = datetime.utcnow()

        if self.splat == "thinblood":
            self.splat = "thin-blood"

        if self.is_thin_blood:
            self.header.blush = -1
        elif self.is_vampire:
            self.header.blush = 0
        else:
            self.blush = -1

        Logger.info("VCHAR: Created %s", self.name)

    def pre_update(self):
        """Clamp values within required bounds."""
        self.hunger = max(0, min(5, self.hunger))
        self.potency = max(0, min(10, self.potency))
        self.experience.unspent = max(0, min(self.experience.unspent, self.experience.lifetime))

        Logger.debug("VCHAR: %s will update", self.name)

    # Comparators

    def __lt__(self, other):
        return self.name.lower() < other.name.lower()

    def __gt__(self, other):
        return self.name.lower() > other.name.lower()

    def __eq__(self, other):
        """Just check the IDs."""
        return self.id == other.id

    def __le__(self, other):
        return self.name.lower() <= other.name.lower()

    def __ge__(self, other):
        return self.name.lower() >= other.name.lower()

    def __ne__(self, other):
        return self.id != other.id

    # Synthetic properties

    @property
    def id(self) -> str:
        """The ObjectId's string value."""
        return str(self.pk)

    @property
    def name(self) -> str:
        """The character's name plus an indicator if it's an SPC."""
        if not self.is_pc:
            return self._name + " (SPC)"
        return self._name

    @name.setter
    def name(self, new_name: str):
        """Set the character's name."""
        self._name = new_name

    @property
    def traits(self) -> dict[str, int]:
        """A copy of the character's traits."""
        return self._traits.copy()

    @property
    def has_biography(self) -> bool:
        """Whether the character has a biography set."""
        return any([self.profile.biography, self.profile.description])

    @property
    def profile_image_url(self) -> str:
        """Get the URL of the first profile image."""
        return self.profile.images[0] if self.profile.images else ""

    def random_image_url(self) -> str:
        """Get a random image URL."""
        return random.choice(self.profile.images) if self.profile.images else ""

    @property
    def aggravated_hp(self) -> int:
        """The amount of Aggravated Health damage sustained."""
        return self.health.count(Damage.AGGRAVATED)

    def set_aggravated_hp(self, new_value):
        """Set the Aggravated Health damage."""
        self.set_damage(_Properties.HEALTH, Damage.AGGRAVATED, new_value, wrap=False)

    @property
    def aggravated_wp(self) -> int:
        """The amount of Aggravated Willpower damage sustained."""
        return self.willpower.count(Damage.AGGRAVATED)

    @property
    def willpower_recovery(self) -> int:
        """The amount of Superficial Willpower damage healed per night."""
        resolve = self.find_trait("Resolve")
        composure = self.find_trait("Composure")

        return max(resolve.rating, composure.rating)

    @property
    def superficial_wp(self) -> int:
        """The amount of Superficial Willpower damage sustained."""
        return self.willpower.count(Damage.SUPERFICIAL)

    def set_superficial_wp(self, new_value):
        """Set the Superficial Willpower damage."""
        self.set_damage(_Properties.WILLPOWER, Damage.SUPERFICIAL, new_value, wrap=True)

    @property
    def superficial_hp(self) -> int:
        """The amount of Superficial Health damage sustained."""
        return self.health.count(Damage.SUPERFICIAL)

    def set_lifetime_xp(self, new_lifetime_xp):
        """Set the lifetime XP and adjust unspent by the delta."""
        new_lifetime_xp = max(0, new_lifetime_xp)
        delta = new_lifetime_xp - self.experience.lifetime

        self.experience.lifetime = new_lifetime_xp
        self.experience.unspent += delta

    def set_blush(self, new_blush: int):
        """Toggle the character's Blush of Life."""
        if self.header.blush == new_blush:
            Logger.debug("VCHAR: %s's Blush of Life (%s) is unchanged", self.name, new_blush)
            return
        if self.header.blush >= 0:
            # We only want to update blush of full vampires
            self.header.blush = new_blush
            Logger.debug("VCHAR: Setting %s's Blush of Life to %s", self.name, new_blush)
        else:
            Logger.warning("VCHAR: Can't set Blush of Life; %s is not a vampire", self.name)

    # Derived attributes

    @property
    def degeneration(self) -> bool:
        """Whether the character is in degeneration."""
        return self.stains > (10 - self.humanity)

    @property
    def impairment(self):
        """A string for describing the character's physical/mental impairment."""
        physical = self.health.count(Damage.NONE) == 0
        mental = self.willpower.count(Damage.NONE) == 0
        total = self.degeneration or (physical and mental)

        if total:
            return "You are impaired. Remember to subtract 2 dice from all pools."

        if physical:
            return "You are physically impaired. Subtract 2 dice from physical pools."

        if mental:
            return "You are mentally impaired. Subtract 2 dice from social and mental pools."

        return None

    @property
    def physically_impaired(self):
        """Whether the character is physically impaired."""
        return self.health.count(Damage.NONE) == 0 or self.stains > (10 - self.humanity)

    @property
    def mentally_impaired(self):
        """Whether the character is physically impaired."""
        return self.willpower.count(Damage.NONE) == 0 or self.stains > (10 - self.humanity)

    @property
    def is_pc(self):
        """Whether the character is a PC."""
        return self.user != INCONNU_ID

    @property
    def is_vampire(self):
        """Whether the character is a vampire."""
        return self.splat in {"vampire", "thin-blood"}

    @property
    def is_thin_blood(self):
        """Whether the character is thin-blooded."""
        return self.splat == "thin-blood"

    @property
    def surge(self):
        """The number of dice added to a Blood Surge."""
        return math.ceil(self.potency / 2) + 1

    @property
    def mend_amount(self):
        """The amount of Superficial damage recovered when mending."""
        if self.is_vampire:
            mends = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5}
            return mends[self.potency]

        # Mortal or ghoul
        return self.find_trait("Stamina", exact=True).rating

    @property
    def frenzy_resist(self):
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

    # Traits

    def has_trait(self, trait: str) -> bool:
        """Determine whether a character has a given trait."""
        return trait.lower() in map(lambda t: t.lower(), self.traits.keys())

    def find_trait(self, trait: str, exact=False) -> SimpleNamespace:
        """
        Finds the closest matching trait.
        Raises AmbiguousTraitError if more than one are found.
        """
        trait = trait.lower()

        # Add universal traits. Only add the vampire traits if it's a vampire.
        my_traits = self.traits
        if self.is_vampire:
            universals = UNIVERSAL_TRAITS
        else:
            universals = filter(lambda t: t not in VChar.VAMPIRE_TRAITS, UNIVERSAL_TRAITS)

        for universal in universals:
            # Only add universal traits if they might match the trait
            if universal.lower().startswith(trait):
                my_traits[universal] = getattr(self, universal.lower())

        matches = [(k, v) for k, v in my_traits.items() if k.lower().startswith(trait)]

        if not matches:
            raise inconnu.errors.TraitNotFoundError(self, trait)

        # A character might have a trait whose name is a subset of another trait.
        # The canonical example: "Surge", "Surgery". Typing "Surge" should work.
        # If we've found an exact match, then we replace our matches list with it
        # and move on from there.

        filtered = [match for match in matches if match[0].lower() == trait]
        if len(filtered) == 1:
            matches = filtered

        # From here, we've found the most accurate match possible. If there's
        # only one match, we're good to go. If, however, there are more than
        # one match, we give them a list of matches so they can disambiguate.

        if len(matches) == 1:
            found_trait, rating = matches[0]

            if exact and trait != found_trait.lower():
                raise inconnu.errors.TraitNotFoundError(self, trait)

            # Convert trackers to a rating
            if isinstance(rating, str):
                rating = rating.count(Damage.NONE)
            return SimpleNamespace(name=found_trait, rating=rating)

        matches = map(lambda t: t[0], matches)
        raise inconnu.errors.AmbiguousTraitError(trait, matches)

    def assign_traits(self, traits: dict) -> str:
        """Add traits to the collection. Overwrites old traits if they exist."""
        canonical_traits = {}

        # This semi-funky structure (example: {stamina: (Stamina, 2)}) is used
        # to make it easy to quickly get the current rating and canonical name
        # for a trait. We could use VChar.find_trait(), but it's slower because
        # of how it tries to do partial matches.
        current_traits = {t.lower(): (t, r) for t, r in self.traits.items()}

        # WHen the user ups Composure, Resolve, or Stamina, we want to modify
        # HP or WP by the appropriate amount as well. We use a Counter to track
        # the amount by which the appropriate track should change.
        counter = Counter()

        # When updating, we want to keep the old capitalization
        for input_trait, rating in traits.items():
            trait, current_rating = current_traits.get(input_trait.lower(), (input_trait, 0))

            # Check for Resolve or Composure
            if trait in ["Resolve", "Composure"]:
                counter["willpower"] += rating - current_rating
            elif trait == "Stamina":
                counter["health"] += rating - current_rating

            canonical_traits[trait] = rating
            self._traits[trait] = rating

        # Determine HP/WP gain, if any
        adjustments = []

        for track, delta in counter.items():
            if delta:
                adjustments.append(track.title())
                new_rating = len(getattr(self, track)) + delta
                self.adjust_tracker_rating(track, new_rating)

        if adjustments:
            adjustment = " and ".join(adjustments)
            verb = "have" if len(adjustments) > 1 else "has"
            adjustment_text = f"{adjustment} {verb} been adjusted accordingly."
        else:
            adjustment_text = ""

        return adjustment_text, canonical_traits

    def delete_trait(self, trait: str) -> str:
        """Delete a trait. Raises TraitNotFoundError if the trait doesn't exist."""
        trait = self.find_trait(trait, exact=True).name
        del self._traits[trait]

        return trait

    # Macros!

    def _macro_index(self, search: str) -> int:
        """Find a macro's index. Raises MacroNotFoundError if not found."""
        lower = search.lower()
        for index, macro in enumerate(self.macros):
            if macro.name.lower() == lower:
                return index

        raise inconnu.errors.MacroNotFoundError(f"{self.name} has no macro named `{search}`.")

    def find_macro(self, search: str) -> VCharMacro:
        """
        Find a macro by name.
        Raises MacroNotFoundError if the macro wasn't found.
        """
        index = self._macro_index(search)
        return self.macros[index]

    def add_macro(self, **kwargs):
        """
        Create and store a macro.
        Raises MacroAlreadyExistsError if the macro already exists.
        """
        try:
            _ = self._macro_index(kwargs["name"])
            raise inconnu.errors.MacroAlreadyExistsError(
                f"You already have a macro named `{kwargs['macro']}`."
            )
        except inconnu.errors.MacroNotFoundError:
            pass

        macro = VCharMacro(**kwargs)
        bisect.insort(self.macros, macro, key=lambda m: m.name.casefold())

        Logger.debug("VCHAR: %s: Added new macro %s", self.name, macro.name)

    def update_macro(self, search: str, update: dict[str, str | int | bool]):
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

    def adjust_tracker_rating(self, track: _Properties, new_rating: int) -> bool:
        """Adjust a character's Health or Willpower rating. Returns true if changed."""
        if track == _Properties.HEALTH:
            current_rating = len(self.health)
            current_track = self.health
        elif track == _Properties.WILLPOWER:
            current_rating = len(self.willpower)
            current_track = self.willpower
        else:
            raise ValueError(f"Invalid tracker: {track}.")

        delta = new_rating - current_rating
        if delta > 0:
            # Increasing the track
            new_track = Damage.NONE * delta + current_track
        elif delta < 0:
            # Decreasing the track
            reduction = abs(delta)
            new_track = current_track[reduction:]
        else:
            # No change
            return False

        setattr(self, track, new_track)
        return True

    def set_damage(self, tracker: _Properties, severity: Damage, amount: int, wrap=False):
        """
        Set the current damage level.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): Damage.SUPERFICIAL or Damage.AGGRAVATED
            amount (int): The amount to set it to
        """
        if not severity in [Damage.SUPERFICIAL, Damage.AGGRAVATED]:
            raise SyntaxError("Severity must be superficial or aggravated.")
        if not tracker in [_Properties.HEALTH, _Properties.WILLPOWER]:
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

        if tracker == _Properties.HEALTH:
            self.health = new_track
        else:
            self.willpower = new_track

        # Log it!
        old_agg = cur_track.count(Damage.AGGRAVATED)
        old_sup = cur_track.count(Damage.SUPERFICIAL)
        new_agg = new_track.count(Damage.AGGRAVATED)
        new_sup = new_track.count(Damage.SUPERFICIAL)

        self.__update_log(f"{tracker}_superficial", old_sup, new_sup)
        self.__update_log(f"{tracker}_aggravated", old_agg, new_agg)

    def apply_damage(self, tracker: _Properties, severity: Damage, delta: int) -> bool:
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
        if not severity in [Damage.SUPERFICIAL, Damage.AGGRAVATED]:
            raise SyntaxError("Severity must be superficial or aggravated.")
        if not tracker in [_Properties.HEALTH, _Properties.WILLPOWER]:
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = getattr(self, tracker)
        cur_dmg = cur_track.count(severity)
        new_dmg = cur_dmg + delta

        if delta < 0 and cur_dmg == 0:
            return False

        self.set_damage(tracker, severity, new_dmg, wrap=True)
        return True

    def apply_experience(self, amount: int, scope: str, reason: str, admin: int):
        """
        Add or remove experience from a character.
        Args:
            amount: The amount of XP to add/subtract
            scope: Unspent or lifetime XP
            reason: The reason for the application
            admin; The Discord ID of the admin who added/deducted
        """
        event = "award" if amount > 0 else "deduct"

        event = VCharExperienceEntry(
            event=f"{event}_{scope}", amount=amount, reason=reason, admin=admin
        )
        self.experience.log.append(event)
        Logger.info("VCHAR: %s: Experience event: %s", self.name, event)

        if scope == "lifetime":
            self.set_lifetime_xp(self.experience.lifetime + amount)
        else:
            self.experience.unspent += amount

    # Misc

    def log(self, key, increment=1):
        """Updates the log for a given field."""
        if increment < 1:
            # We only want to see increments, not decrements
            return

        valid_keys = {
            "remorse",
            "rouse",
            "slake",
            "awaken",
            "frenzy",
            "degen",
            "health_superficial",
            "health_aggravated",
            "stains",
            "willpower_superficial",
            "willpower_aggravated",
            "blush",
        }
        if key not in valid_keys:
            raise inconnu.errors.InvalidLogKeyError(f"{key} is not a valid log key.")

        if key in self.stat_log:
            self.stat_log[key] += increment
        else:
            self.stat_log[key] = increment

    def __update_log(self, key, old_value, new_value):
        """
        Updates the character log.
        Args:
            key (str): The key to be updated
            addition (int): The amount to increase it by
        """
        if new_value > old_value:
            delta = new_value - old_value

            if key in self.stat_log:
                self.stat_log[key] += delta
            else:
                self.stat_log[key] = delta
