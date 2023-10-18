"""Player-character model."""
# pylint: disable=missing-class-docstring, too-few-public-methods, abstract-method
# pylint: disable=too-many-public-methods

import bisect
import copy
import math
import random
from collections import Counter
from datetime import datetime
from enum import Enum
from types import SimpleNamespace

from discord import Embed
from umongo import Document, fields

import inconnu
from inconnu.constants import ATTRIBUTES, DISCIPLINES, SKILLS, UNIVERSAL_TRAITS, Damage
from inconnu.models.vchardocs import (
    VCharExperience,
    VCharExperienceEntry,
    VCharHeader,
    VCharMacro,
    VCharProfile,
    VCharTrait,
)
from logger import Logger


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

    VAMPIRE_TRAITS = ["Hunger", "Potency", "Surge", "Bane", "PowerBonus"]
    SPC_OWNER = 0

    # Ownership
    guild = fields.IntField()
    user = fields.IntField()

    # Basic stats used in trackers
    _name = fields.StrField(attribute="name")
    splat = fields.StrField()
    health = fields.StrField()
    willpower = fields.StrField()
    _humanity = fields.IntField(attribute="humanity")
    stains = fields.IntField(default=0)
    _hunger = fields.IntField(default=1, attribute="hunger")
    potency = fields.IntField()
    _traits = fields.ListField(fields.EmbeddedField(VCharTrait), default=list, attribute="traits")

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
            self.header.blush = -1

        Logger.info("VCHAR: Created %s", self.name)

    def pre_update(self):
        """Clamp values within required bounds."""
        if self.is_vampire:
            self.hunger = max(0, min(5, self.hunger))
        else:
            self.hunger = 0
        self.potency = max(0, min(10, self.potency))
        self.stains = max(0, min(10, self.stains))
        self.experience.unspent = max(0, min(self.experience.unspent, self.experience.lifetime))

        if self.splat == "thinblood":
            self.splat = "thin-blood"

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
    def hunger(self) -> int:
        """Get the character's Hunger rating."""
        if self.is_vampire:
            return self._hunger
        return 0

    @hunger.setter
    def hunger(self, new_hunger: int):
        """Set the character's Hunger rating."""
        new_hunger = max(0, min(new_hunger, 5))
        self._hunger = new_hunger

    @property
    def humanity(self) -> int:
        """The character's Humanity rating."""
        return self._humanity

    @humanity.setter
    def humanity(self, new_humanity: int):
        """Set the character's new Humanity rating, clamped, and wipe stains."""
        new_humanity = max(0, min(new_humanity, 10))
        self._humanity = new_humanity
        self.stains = 0

    @property
    def traits(self) -> dict[str, int]:
        """A copy of the character's traits."""
        return copy.deepcopy(self._traits)

    @property
    def has_biography(self) -> bool:
        """Whether the character has a biography set."""
        return any([self.profile.biography, self.profile.description])

    @property
    def profile_image_url(self) -> str:
        """Get the URL of the first profile image."""
        return self.profile.images[0] if self.profile.images else Embed.Empty

    def random_image_url(self) -> str:
        """Get a random image URL."""
        return random.choice(self.profile.images) if self.profile.images else Embed.Empty

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
        try:
            resolve = self.find_trait("Resolve").rating
        except inconnu.errors.TraitNotFound:
            resolve = 0

        try:
            composure = self.find_trait("Composure").rating
        except inconnu.errors.TraitNotFound:
            composure = 0

        return max(resolve, composure)

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
        if self.health.count(Damage.AGGRAVATED) == len(self.health):
            if self.is_vampire:
                return "You are IN TORPOR!"
            return "You are DEAD!"

        physical = self.health.count(Damage.NONE) == 0
        mental = self.willpower.count(Damage.NONE) == 0
        total = self.degeneration or (physical and mental)

        if total:
            return "You are totally impaired. Remember to subtract 2 dice from all pools."

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
        return self.user != VChar.SPC_OWNER

    @property
    def is_spc(self) -> bool:
        """Whether the character is an SPC."""
        return not self.is_pc

    @property
    def is_vampire(self):
        """Whether the character is a vampire."""
        return self.splat in {"vampire", "thin-blood"}

    @property
    def is_ghoul(self) -> bool:
        """Whether the character is a bool."""
        return self.splat == "ghoul"

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
            inherents = filter(lambda t: t not in VChar.VAMPIRE_TRAITS, UNIVERSAL_TRAITS)

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
        for trait in self._traits:
            if trait.matching(name, True):
                return True
        return False

    def find_trait(self, name: str, exact=False) -> SimpleNamespace:
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
            raise inconnu.errors.TraitNotFound(self, name)

        if len(found) > 1:
            keys = map(lambda m: m.key, found)
            raise inconnu.errors.AmbiguousTraitError(name, keys)

        # One single match found
        return found[0]

    def assign_traits(self, traits: dict[str, int], category=VCharTrait.Type.CUSTOM) -> str:
        """Add traits to the character. Overwrites old traits if they exist."""
        for name in traits:
            if name.lower() in map(str.lower, UNIVERSAL_TRAITS):
                raise ValueError(f"`{name}` is a reserved trait and can't be added")

        assignments = {}
        counter = Counter()

        for input_name, input_rating in traits.items():
            updated = False
            for trait in self._traits:
                if trait.matching(input_name, True):
                    if trait.name in ["Resolve", "Composure"]:
                        counter["willpower"] += input_rating - trait.rating
                    elif trait.name == "Stamina":
                        counter["health"] += input_rating - trait.rating

                    trait.rating = input_rating
                    assignments[trait.name] = input_rating
                    updated = True

            if not updated:
                # Automatically categorize attributes and skills (helps with chargen)
                if input_name in ATTRIBUTES:
                    category = VCharTrait.Type.ATTRIBUTE
                elif input_name in SKILLS:
                    category = VCharTrait.Type.SKILL
                elif input_name.lower() in map(str.lower, DISCIPLINES):
                    category = VCharTrait.Type.DISCIPLINE

                new_trait = VCharTrait(name=input_name, rating=input_rating, type=category.value)
                bisect.insort(self._traits, new_trait, key=lambda t: t.name.casefold())
                assignments[input_name] = input_rating

        # Traits added; now adjust HP/WP
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

        return adjustment_text, assignments

    def delete_trait(self, name: str) -> str:
        """Delete a trait. Raises TraitNotFound if the trait doesn't exist."""
        for index, trait in enumerate(self._traits):
            if trait.matching(name, True):
                del self._traits[index]
                return trait.name

        raise inconnu.errors.TraitNotFound(self, name)

    def add_powers(self, trait_name: str, powers: list[str] | str) -> tuple[VCharTrait, set[str]]:
        """Add powers to a Discipline and return a copy."""
        return self._add_subtraits(trait_name, powers, VCharTrait.add_powers)

    def add_specialties(
        self, trait_name: str, specialties: list[str] | str
    ) -> tuple[VCharTrait, set[str]]:
        """Add specialties to a trait and return a copy of that trait."""
        return self._add_subtraits(trait_name, specialties, VCharTrait.add_specialties)

    def _add_subtraits(
        self,
        trait_name: str,
        specialties: list[str] | str,
        action: callable,
    ) -> tuple[VCharTrait, set[str]]:
        """The actual work of adding subtraits."""
        for trait in self._traits:
            if trait.matching(trait_name, True):
                before = set(trait.specialties)
                action(trait, specialties)
                after = set(trait.specialties)
                delta = sorted(after.symmetric_difference(before))

                return copy.deepcopy(trait), delta

        raise inconnu.errors.TraitNotFound(self, trait_name)

    def remove_specialties(
        self, trait_name: str, specialties: list[str] | str
    ) -> tuple[VCharTrait, set[str]]:
        """Remove specialties from a trait."""
        for trait in self._traits:
            if trait.matching(trait_name, True):
                before = set(trait.specialties)
                trait.remove_specialties(specialties)
                after = set(trait.specialties)
                delta = sorted(after.symmetric_difference(before))

                return copy.deepcopy(trait), delta

        raise inconnu.errors.TraitNotFound(self, trait_name)

    # Macros!

    def _macro_index(self, search: str) -> int:
        """Find a macro's index. Raises MacroNotFoundError if not found."""
        lower = search.lower()
        for index, macro in enumerate(self.macros):
            if macro.name.lower() == lower:
                return index

        raise inconnu.errors.MacroNotFoundError(f"**{self.name}** has no macro named `{search}`.")

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
                f"You already have a macro named `{kwargs['name']}`."
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
