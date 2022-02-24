"""vchar/vchar.py - Persistent character management using MongoDB."""
# pylint: disable=too-many-public-methods, too-many-arguments, c-extension-no-member

import datetime
import math
import os
import re
from enum import Enum

from collections import OrderedDict
from types import SimpleNamespace

import pymongo
import bson
from bson.objectid import ObjectId

from . import errors
from ..constants import Damage, INCONNU_ID, UNIVERSAL_TRAITS

# This cache is not an efficiency cache. Instead, it keeps persistent character
# references that can be passed to different bot functions. This helps prevent
# stale data from being used. Consider the following scenario:
#
#   1. Player rolls, then rerolls with 2 superficial WP damage
#   2. Player uses /character update to change his character's WP damage to 0
#   3. Player clicks the "Mark WP" button
#
# Without the cache, the character will end with 3 superficial WP damage instead
# of 1, because both the roll function and the character updater would be
# accessing different copies of the character. With the cache, they will use the
# same copy.
#
# In benchmarking, an efficiency version adds complexity without any measurable
# performance gains.
_CHARACTER_CACHE = {}


_digits = re.compile(r"\d")
def contains_digit(string: str):
    """Determine whether a string contains a digit."""
    if string is None:
        return False
    return bool(_digits.search(string)) # Much faster than using any()


class _Properties(str, Enum):
    """An enum to prevent needing to stringly type database fields."""

    USER = "user"
    NAME = "name"
    SPLAT = "splat"
    HUMANITY = "humanity"
    STAINS = "stains"
    HEALTH = "health"
    WILLPOWER = "willpower"
    HUNGER = "hunger"
    POTENCY = "potency"


class VChar:
    """A class that maintains a character's property and automatically manages persistence."""

    _CLIENT = None # MongoDB client
    _CHARS = None # Characters collection

    VAMPIRE_TRAITS = ["Hunger", "Potency", "Surge", "Bane"]


    def __init__(self, params: dict):
        self._params = params
        self.id = params["_id"] # pylint: disable=invalid-name
        self.find_query = { "_id": self.id }
        self.guild = params["guild"]


    # Character creation and fetching

    @classmethod
    def create(cls, guild: int, user: int, name: str):
        """
        Create a named character with an associated guild and user.
        All other stats are default, minimum values, and no traits are assigned.
        """
        VChar.__prepare()

        character = {
            "guild": guild,
            "user": user,
            "name": name,
            "splat": "vampire",
            "humanity": 7,
            "stains": 0,
            "health": "....",
            "willpower": "...",
            "hunger": 1,
            "potency": 0,
            "experience": { "current": 0, "total": 0 },
            "log": { "created": datetime.datetime.utcnow() }
        }
        _id = VChar._CHARS.insert_one(character).inserted_id
        params = VChar._CHARS.find_one({ "_id": _id })
        return VChar(params)


    @classmethod
    def _id_fetch(cls, charid: str):
        """Fetch a character by ID and return its raw parameters."""
        try:
            params = VChar._CHARS.find_one({ "_id": ObjectId(charid) })
        except bson.errors.InvalidId:
            return None

        return params


    @classmethod
    def fetch(cls, guild: int, user: int, name: str):
        """
        Fetch a character by name.

        Raises NoCharactersError if the user has no character.
        Raises CharacterNotFoundError if the character doesn't exist.

        If the name isn't specified, then:
            1 character: Return that character
           >1 character: Raise UnspecifiedCharacterError
        """
        VChar.__prepare()

        if contains_digit(name):
            if (char := _CHARACTER_CACHE.get(name, None)) is not None:
                return char
            if (char_params := VChar._id_fetch(name)) is None:
                raise errors.CharacterNotFoundError(f"`{name}` is not a valid character name.")

            char = VChar(char_params)
            return _CHARACTER_CACHE.setdefault(char.id, char)

        if (count := VChar._CHARS.count_documents({ "guild": guild, "user": user })) == 0:
            raise errors.NoCharactersError("You have no characters!")

        if name is None:
            if count == 1:
                character = VChar._CHARS.find_one({ "guild": guild, "user": user })
                char = VChar(character)
                return _CHARACTER_CACHE.setdefault(char.id, char)

            errmsg = f"You have {count} characters. Please specify which you want."
            raise errors.UnspecifiedCharacterError(errmsg)

        query = {
            "guild": guild,
            "user": user,
            "name": { "$regex": re.compile("^" + name + "$", re.IGNORECASE) }
        }

        if (character := VChar._CHARS.find_one(query)) is None:
            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        char = VChar(character)
        return _CHARACTER_CACHE.setdefault(char.id, char)


    @classmethod
    def character_exists(cls, guild: int, user: int, name: str, is_spc: bool):
        """Determine wheter a character exists."""
        VChar.__prepare()

        query = {
            "guild": guild,
            "user": user if not is_spc else INCONNU_ID,
            "name": { "$regex": re.compile("^" + name + "$", re.IGNORECASE) }
        }
        return VChar._CHARS.count_documents(query) > 0


    @classmethod
    def all_characters(cls, guild: int, user: int):
        """
        Fetch all of the user's characters.
        """
        VChar.__prepare()

        characters = list(
            VChar._CHARS.find({ "guild": guild, "user": user })
                .collation({ "locale": "en", "strength": 2 })
                .sort("name")
        )
        return [VChar(params) for params in characters]


    # Property accessors

    def _set_property(self, field, value):
        """Set a field to a given value."""
        VChar.__prepare()
        self._params[field] = value
        VChar._CHARS.update_one(self.find_query, { "$set": { field: value } })


    @property
    def user(self):
        """The owner's Discord user ID."""
        return self._params[_Properties.USER]


    @user.setter
    def user(self, new_user):
        """Set the new user."""
        if not isinstance(new_user, int):
            new_user = new_user.id

        self._set_property(_Properties.USER, new_user)


    @property
    def name(self):
        """The character's name."""
        if self.is_pc:
            return self._params[_Properties.NAME]
        return self._params[_Properties.NAME] + " (SPC)"


    @name.setter
    def name(self, new_name):
        """Set the character's name."""
        self._set_property(_Properties.NAME, new_name)


    @property
    def splat(self):
        """The character's splat."""
        return self._params[_Properties.SPLAT]


    @splat.setter
    def splat(self, new_splat):
        """Set the character's splat."""
        self._set_property(_Properties.SPLAT, new_splat)


    @property
    def humanity(self):
        """The character's humanity."""
        return self._params[_Properties.HUMANITY]


    @humanity.setter
    def humanity(self, new_humanity):
        """Set the character's humanity."""
        new_humanity = max(0, min(10, new_humanity))
        self._set_property(_Properties.HUMANITY, new_humanity)
        self.stains = 0


    @property
    def stains(self):
        """The character's stains."""
        return self._params[_Properties.STAINS]


    @stains.setter
    def stains(self, new_stains):
        """Set the character's stains."""
        new_stains = max(0, min(10, new_stains))
        self.__update_log("stains", self.stains, new_stains)
        self._set_property(_Properties.STAINS, new_stains)


    @property
    def health(self):
        """The character's health."""
        return self._params[_Properties.HEALTH]


    @health.setter
    def health(self, new_health):
        """Set the character's health."""
        self._set_property(_Properties.HEALTH, new_health)


    @property
    def aggravated_hp(self) -> int:
        """The amount of Aggravated Health damage sustained."""
        return self.health.count(Damage.AGGRAVATED)


    @aggravated_hp.setter
    def aggravated_hp(self, new_value):
        """Set the Aggravated Health damage."""
        self.set_damage("health", Damage.AGGRAVATED, new_value, wrap=False)


    @property
    def willpower(self):
        """The character's willpower."""
        return self._params[_Properties.WILLPOWER]


    @willpower.setter
    def willpower(self, new_willpower):
        """Set the character's willpower."""
        self._set_property(_Properties.WILLPOWER, new_willpower)


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


    @superficial_wp.setter
    def superficial_wp(self, new_value):
        """Set the Superficial Willpower damage."""
        self.set_damage("willpower", Damage.SUPERFICIAL, new_value, wrap=True)


    @property
    def superficial_hp(self) -> int:
        """The amount of Superficial Health damage sustained."""
        return self.health.count(Damage.SUPERFICIAL)


    @superficial_hp.setter
    def superficial_hp(self, new_value):
        """Set the Superficial Health damage."""
        self.set_damage("health", Damage.SUPERFICIAL, new_value, wrap=True)


    @property
    def hunger(self):
        """The character's hunger."""
        return self._params[_Properties.HUNGER] if self.is_vampire else 0


    @hunger.setter
    def hunger(self, new_hunger):
        """Set the character's hunger."""
        new_hunger = max(0, min(5, new_hunger)) # Clamp between 0 and 5
        self.__update_log("hunger", self.hunger, new_hunger)
        self._set_property(_Properties.HUNGER, new_hunger)


    @property
    def potency(self):
        """The character's potency."""
        return self._params[_Properties.POTENCY]


    @potency.setter
    def potency(self, new_potency):
        """Set the character's potency."""
        new_potency = max(0, min(10, new_potency))
        self._set_property(_Properties.POTENCY, new_potency)


    @property
    def current_xp(self):
        """The character's current xp."""
        return self._params["experience"]["current"]


    @current_xp.setter
    def current_xp(self, new_current_xp):
        """Set the character's current xp."""
        if new_current_xp > self.total_xp:
            new_current_xp = self.total_xp
        elif new_current_xp < 0:
            new_current_xp = 0

        self._params["experience"]["current"] = new_current_xp
        VChar._CHARS.update_one(
            self.find_query,
            { "$set": { "experience.current": new_current_xp } }
        )


    @property
    def total_xp(self):
        """The character's total xp."""
        return self._params["experience"]["total"]


    @total_xp.setter
    def total_xp(self, new_total_xp):
        """Set the character's total XP and update current accordingly."""
        new_total_xp = max(new_total_xp, 0)
        delta = new_total_xp - self.total_xp

        self._params["experience"]["total"] = new_total_xp
        VChar._CHARS.update_one(
            self.find_query,
            { "$set": { "experience.total": new_total_xp } }
        )
        self.current_xp += delta


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
        return self._params["user"] != INCONNU_ID


    @property
    def is_vampire(self):
        """Whether the character is a vampire."""
        return self.splat == "vampire"


    @property
    def surge(self):
        """The number of dice added to a Blood Surge."""
        return math.ceil(self.potency / 2) + 1


    @property
    def mend_amount(self):
        """The amount of Superficial damage recovered when mending."""
        if self.is_vampire:
            mends = { 0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5 }
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
    def agg_health(self):
        """The number of Aggravated health damage the character has taken."""
        return self.health.count(Damage.AGGRAVATED)


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

    @property
    def traits(self):
        """A dictionary of the user's traits."""
        _traits = self._params.get("traits", {})
        if not _traits:
            self._params["traits"] = {}
        return OrderedDict(sorted(_traits.items(), key = lambda s: s[0].casefold()))


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
            rating = getattr(self, universal.lower())
            my_traits[universal] = rating

        matches = [(k, v) for k, v in my_traits.items() if k.lower().startswith(trait)]

        if not matches:
            raise errors.TraitNotFoundError(f"{self.name} has no trait named `{trait}`.")

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
                raise errors.TraitNotFoundError(f"{self.name} has no trait named `{trait}`.")

            # Convert trackers to a rating
            if isinstance(rating, str):
                rating = rating.count(Damage.NONE)
            return SimpleNamespace(name=found_trait, rating=rating)

        matches = map(lambda t: t[0], matches)
        raise errors.AmbiguousTraitError(trait, matches)


    def add_trait(self, trait: str, rating: int):
        """
        Add a trait to the collection.
        Raises TraitAlreadyExistsError if the trait already exists.
        """
        if self.has_trait(trait):
            raise errors.TraitAlreadyExistsError(f"You already have a trait named `{trait}`.")

        VChar._CHARS.update_one(self.find_query, { "$set": { f"traits.{trait}": rating } })
        self._params["traits"][trait] = rating


    def update_trait(self, trait: str, new_rating: int):
        """
        Update a given trait.
        Raises TraitNotFoundError if the trait does not exist.
        """
        if trait.title() in UNIVERSAL_TRAITS:
            err = f"`{trait.title()}` is an automatic trait that cannot be modified."
            raise errors.TraitAlreadyExistsError(err)

        trait = self.find_trait(trait, exact=True).name
        VChar._CHARS.update_one(self.find_query, { "$set": { f"traits.{trait}": new_rating } })
        self._params["traits"][trait] = new_rating

        return trait


    def delete_trait(self, trait: str):
        """
        Delete a trait.
        Raises TraitNotFoundError if the trait doesn't exist.
        """
        trait = self.find_trait(trait, exact=True).name
        VChar._CHARS.update_one(self.find_query, { "$unset": { f"traits.{trait}": "" } })

        return trait


    def owned_traits(self, **traits):
        """Partition the list of traits into owned and unowned groups."""
        my_traits = self.traits
        owned = {}
        unowned = {}

        for trait, rating in traits.items():
            if trait.lower() in map(lambda t: t.lower(), my_traits.keys()):
                owned[trait] = rating
            else:
                unowned[trait] = rating

        return SimpleNamespace(owned=owned, unowned=unowned)


    # Macros!

    @property
    def macros(self):
        """The user's macros."""
        if (_macros := self._params.get("macros")) is not None:
            raw_macros = []
            for name, macro in sorted(_macros.items(), key = lambda s: s[0].casefold()):
                macro["name"] = name

                if not self.is_vampire:
                    macro["hunger"] = False
                if not "staining" in macro:
                    macro["staining"] = "show"

                raw_macros.append(macro)

            return [SimpleNamespace(**macro) for macro in raw_macros]

        return []


    def find_macro(self, search):
        """
        Return a macro object.
        Raises MacroNotFoundError if the macro wasn't found.
        """
        matches = [macro for macro in self.macros if macro.name.lower() == search.lower()]
        if not matches:
            raise errors.MacroNotFoundError(f"{self.name} has no macro named `{search}`.")

        return matches[0]


    def add_macro(
        self,
        macro: str,
        pool: list,
        hunger: bool,
        rouses:int,
        reroll_rouses: int,
        staining: str,
        difficulty: int,
        comment: str
    ):
        """
        Store a macro.
        Raises MacroAlreadyExistsError if the macro already exists.
        """
        try:
            _ = self.find_macro(macro)
            raise errors.MacroAlreadyExistsError(f"You already have a macro named `{macro}`.")
        except errors.MacroNotFoundError:
            pass

        macro_query = {
            "$set": {
                f"macros.{macro}": {
                    "pool": list(map(str, pool)),
                    "rouses": rouses,
                    "reroll_rouses": reroll_rouses,
                    "staining": staining,
                    "hunger": hunger,
                    "difficulty": difficulty,
                    "comment": comment
                }
            }
        }
        VChar._CHARS.update_one(self.find_query, macro_query)


    def update_macro(self, macro: str, update: dict):
        """Update a macro."""
        macro = self.find_macro(macro) # For getting the exact name
        for param, val in update.items():
            VChar._CHARS.update_one(
                self.find_query,
                { "$set": { f"macros.{macro.name}.{param}": val } }
            )
        return macro.name


    def delete_macro(self, macro):
        """
        Delete a macro.
        Raises MacroNotFoundError if the macro doesn't exist.
        """
        macro = self.find_macro(macro) # For getting the exact name
        VChar._CHARS.update_one(self.find_query, { "$unset": { f"macros.{macro.name}": "" } })


    # Specialized mutators

    def set_damage(self, tracker: str, severity: str, amount: int, wrap=False):
        """
        Set the current damage level.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): Damage.SUPERFICIAL or Damage.AGGRAVATED
            amount (int): The amount to set it to
        """
        if not severity in [Damage.SUPERFICIAL, Damage.AGGRAVATED]:
            raise SyntaxError("Severity must be superficial or aggravated.")
        if not tracker in ["health", "willpower"]:
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = self._params[tracker]
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
        new_track = new_track[-len(cur_track):] # Shrink it if necessary

        if tracker == "health":
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


    def apply_damage(self, tracker: str, severity: str, delta: int):
        """
        Apply Superficial damage.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): Damage.SUPERFICIAL or Damage.AGGRAVATED
            delta (int): The amount to apply
        If the damage exceeds the tracker, it will wrap around to aggravated.
        """
        if not severity in [Damage.SUPERFICIAL, Damage.AGGRAVATED]:
            raise SyntaxError("Severity must be superficial or aggravated.")
        if not tracker in ["health", "willpower"]:
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = self._params[tracker]
        cur_dmg = cur_track.count(severity)
        new_dmg = cur_dmg + delta

        self.set_damage(tracker, severity, new_dmg, wrap=True)


    # Experience Logging

    @property
    def experience_log(self):
        """The list of experience log events."""
        return self._params["experience"].get("log", [])


    def apply_experience(self, amount: int, scope: str, reason: str, admin: int):
        """
        Add or remove experience from a character.
        Args:
            amount: The amount of XP to add/subtract
            scope: Unspent or lifetime XP
            reason: The reason for the application
            admin; The Discord ID of the admin who added/deducted
        """
        VChar.__prepare()

        event = "award" if amount > 0 else "deduct"

        event_document = {
            "event": f"{event}_{scope}",
            "amount": amount,
            "reason": reason,
            "admin": admin,
            "date": datetime.datetime.utcnow()
        }
        push_query = { "$push": { "experience.log": event_document }}

        VChar._CHARS.update_one(self.find_query, push_query)

        if scope == "lifetime":
            self.total_xp += amount
        else:
            self.current_xp += amount


    def remove_experience_log_entry(self, entry):
        """Remove an entry from the log."""
        VChar.__prepare()

        VChar._CHARS.update_one(self.find_query, {
            "$pull": {
                "experience.log": entry
            }
        })


    # Misc

    def delete_character(self) -> bool:
        """Delete this character and all associated traits and macros."""
        try:
            del _CHARACTER_CACHE[self.id]
            return VChar._CHARS.delete_one(self.find_query).acknowledged
        except KeyError:
            # Somehow, they weren't in the cache
            return False


    @classmethod
    def mark_player_inactive(cls, player):
        """Mark all of the player's characters as inactive."""
        VChar.__prepare()

        VChar._CHARS.update_many({ "guild": player.guild.id, "user": player.id }, {
            "$set": { "log.left": datetime.datetime.utcnow() }
            }
        )


    @classmethod
    def reactivate_player_characters(cls, player):
        """Reactivate all of the player's characters when they rejoin the guild."""
        VChar.__prepare()

        VChar._CHARS.update_many({ "guild": player.guild.id, "user": player.id }, {
            "$unset": { "log.left": 1 }
            }
        )


    def log(self, key, increment=1):
        """Updates the log for a given field."""
        if increment < 1:
            return

        valid_keys = [
            "remorse", "rouse", "slake", "awaken", "frenzy", "degen",
            "health_superficial", "health_aggravated", "stains",
            "willpower_superficial", "willpower_aggravated", "blush"
        ]
        if key not in valid_keys:
            raise errors.InvalidLogKeyError(f"{key} is not a valid log key.")

        VChar._CHARS.update_one(self.find_query, { "$inc": { f"log.{key}": increment } })


    def log_injury(self, injury: str):
        """Log a crippling injury."""
        VChar._CHARS.update_one(self.find_query, { "$push": { "injuries": injury } })


    def __update_log(self, key, old_value, new_value):
        """
        Updates the character log.
        Args:
            key (str): The key to be updated
            addition (int): The amount to increase it by
        """
        if new_value > old_value:
            delta = new_value - old_value
            VChar._CHARS.update_one(self.find_query, { "$inc": { f"log.{key}": delta } })


    @classmethod
    def __prepare(cls):
        """Prepare the database."""
        try:
            VChar._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            VChar._CLIENT = None
        finally:
            if VChar._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                VChar._CLIENT = mongo
                VChar._CHARS = mongo.inconnu.characters
