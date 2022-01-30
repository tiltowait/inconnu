"""vchar/vchar.py - Persistent character management using MongoDB."""
# pylint: disable=too-many-public-methods, too-many-arguments, c-extension-no-member

import datetime
import math
import os
import re

from collections import OrderedDict
from types import SimpleNamespace

import pymongo
import bson
from bson.objectid import ObjectId

from . import errors
from ..constants import DAMAGE, INCONNU_ID, UNIVERSAL_TRAITS


_digits = re.compile(r"\d")
def contains_digit(string: str):
    """Determine whether a string contains a digit."""
    if string is None:
        return False
    return bool(_digits.search(string)) # Much faster than using any()


class VChar:
    """A class that maintains a character's property and automatically manages persistence."""

    # We keep characters, traits, and macros all in their own collections in order to
    # massively simplify queries and lookups.

    _CLIENT = None # MongoDB client
    _CHARS = None # Characters collection
    _MACROS = None # Macros collection

    VAMPIRE_TRAITS = ["Hunger", "Potency", "Surge"]


    def __init__(self, params: dict):
        VChar.__prepare()
        self._params = params
        self.id = params["_id"] # pylint: disable=invalid-name
        self.guild = params["guild"]
        self.user = params["user"]


    # Character creation and fetching

    @classmethod
    def create(cls, guild: int, user: int, name: str):
        """
        Create a named character with an associated guild and user.
        All other stats are default, minimum values, and no traits are assigned.
        """

        # Traits and macros are stored in separate collections!
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
        VChar.__prepare()

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
        if contains_digit(name):
            char_params = VChar._id_fetch(name)
            if char_params is None:
                raise errors.CharacterNotFoundError(f"`{name}` is not a valid character name.")
            return VChar(char_params)

        VChar.__prepare()

        count = VChar._CHARS.count_documents({ "guild": guild, "user": user })
        if count == 0:
            raise errors.NoCharactersError("You have no characters!")

        if name is None:
            if count == 1:
                character = VChar._CHARS.find_one({ "guild": guild, "user": user })
                return VChar(character)

            errmsg = f"You have {count} characters. Please specify which you want."
            raise errors.UnspecifiedCharacterError(errmsg)

        query = {
            "guild": guild,
            "user": user,
            "name": { "$regex": re.compile("^" + name + "$", re.IGNORECASE) }
        }
        character = VChar._CHARS.find_one(query)

        if character is None:
            raise errors.CharacterNotFoundError(f"You have no character named `{name}`.")

        return VChar(character)


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

    @property
    def name(self):
        """The character's name."""
        if self.is_pc:
            return self._params["name"]
        return self._params["name"] + " (SPC)"


    @name.setter
    def name(self, new_name):
        """Set the character's name."""
        self._params["name"] = new_name
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "name": new_name } })


    @property
    def splat(self):
        """The character's splat."""
        return self._params["splat"]


    @splat.setter
    def splat(self, new_splat):
        """Set the character's splat."""
        self._params["splat"] = new_splat
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "splat": new_splat } })


    @property
    def humanity(self):
        """The character's humanity."""
        return self._params["humanity"]


    @humanity.setter
    def humanity(self, new_humanity):
        """Set the character's humanity."""
        new_humanity = max(0, min(10, new_humanity))
        self._params["humanity"] = new_humanity
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "humanity": new_humanity } })
        self.stains = 0


    @property
    def stains(self):
        """The character's stains."""
        return self._params["stains"]


    @stains.setter
    def stains(self, new_stains):
        """Set the character's stains."""
        self.__update_log("stains", self.stains, new_stains)
        self._params["stains"] = new_stains
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "stains": new_stains } })


    @property
    def health(self):
        """The character's health."""
        return self._params["health"]


    @health.setter
    def health(self, new_health):
        """Set the character's health."""
        self._params["health"] = new_health
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "health": new_health } })


    @property
    def aggravated_hp(self) -> int:
        """The amount of Aggravated Health damage sustained."""
        return self.health.count(DAMAGE.aggravated)


    @aggravated_hp.setter
    def aggravated_hp(self, new_value):
        """Set the Aggravated Health damage."""
        self.set_damage("health", DAMAGE.aggravated, new_value, wrap=False)


    @property
    def willpower(self):
        """The character's willpower."""
        return self._params["willpower"]


    @willpower.setter
    def willpower(self, new_willpower):
        """Set the character's willpower."""
        self._params["willpower"] = new_willpower
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "willpower": new_willpower } })


    @property
    def willpower_recovery(self) -> int:
        """The amount of Superficial Willpower damage healed per night."""
        resolve = self.find_trait("Resolve")
        composure = self.find_trait("Composure")

        return max(resolve.rating, composure.rating)


    @property
    def superficial_wp(self) -> int:
        """The amount of Superficial Willpower damage sustained."""
        return self.willpower.count(DAMAGE.superficial)


    @superficial_wp.setter
    def superficial_wp(self, new_value):
        """Set the Superficial Willpower damage."""
        self.set_damage("willpower", DAMAGE.superficial, new_value, wrap=True)


    @property
    def superficial_hp(self) -> int:
        """The amount of Superficial Health damage sustained."""
        return self.health.count(DAMAGE.superficial)


    @superficial_hp.setter
    def superficial_hp(self, new_value):
        """Set the Superficial Health damage."""
        self.set_damage("health", DAMAGE.superficial, new_value, wrap=True)


    @property
    def hunger(self):
        """The character's hunger."""
        return self._params["hunger"]


    @hunger.setter
    def hunger(self, new_hunger):
        """Set the character's hunger."""
        new_hunger = max(0, min(5, new_hunger)) # Clamp between 0 and 5

        self.__update_log("hunger", self.hunger, new_hunger)
        self._params["hunger"] = new_hunger
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "hunger": new_hunger } })


    @property
    def potency(self):
        """The character's potency."""
        return self._params["potency"]


    @potency.setter
    def potency(self, new_potency):
        """Set the character's potency."""
        new_potency = max(0, min(10, new_potency))

        self._params["potency"] = new_potency
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { "potency": new_potency } })


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
            { "_id": self.id },
            { "$set": { "experience.current": new_current_xp } }
        )


    @property
    def total_xp(self):
        """The character's total xp."""
        return self._params["experience"]["total"]


    @total_xp.setter
    def total_xp(self, new_total_xp):
        """Set the character's total XP and update current accordingly."""
        if new_total_xp < 0:
            new_total_xp = 0

        delta = new_total_xp - self.total_xp

        self._params["experience"]["total"] = new_total_xp
        VChar._CHARS.update_one(
            { "_id": self.id },
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
        physical = self.health.count(DAMAGE.none) == 0
        mental = self.willpower.count(DAMAGE.none) == 0
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
        return self.health.count(DAMAGE.none) == 0 or self.stains > (10 - self.humanity)


    @property
    def mentally_impaired(self):
        """Whether the character is physically impaired."""
        return self.willpower.count(DAMAGE.none) == 0 or self.stains > (10 - self.humanity)


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
        if self.splat == "vampire":
            mends = { 0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5 }
            return mends[self.potency]

        # Mortal or ghoul
        return self.find_trait("Stamina", exact=True).rating


    @property
    def frenzy_resist(self):
        """The dice pool for resisting frenzy. Equal to current WP + 1/3 Humanity."""
        cur_wp = self.willpower.count(DAMAGE.none)
        third_hu = int(self.humanity / 3)
        return max(cur_wp + third_hu, 1)


    @property
    def agg_health(self):
        """The number of Aggravated health damage the character has taken."""
        return self.health.count(DAMAGE.aggravated)


    @property
    def bane_severity(self) -> int:
        """The character's bane severity."""
        if self.potency == 0:
            return 0
        return math.ceil(self.potency / 2) + 1


    # Traits

    @property
    def traits(self):
        """A dictionary of the user's traits."""
        _traits = self._params["traits"]
        return OrderedDict(sorted(_traits.items()))


    def find_trait(self, trait: str, exact=False) -> SimpleNamespace:
        """
        Finds the closest matching trait.
        Raises AmbiguousTraitError if more than one are found.
        """

        # Add universal traits
        my_traits = self.traits
        for universal in UNIVERSAL_TRAITS:
            rating = getattr(self, universal)
            my_traits[universal.capitalize()] = rating

        # While it would technically be more efficient to remove the vampire traits
        # here if the character isn't a vampire, we leave them in so we can present
        # a more helpful error message should they be attempting to invoke one.

        VChar.VAMPIRE_TRAITS = ["Hunger", "Potency", "Surge"]
        matches = [(k, v) for k, v in my_traits.items() if k.lower().startswith(trait.lower())]

        if not matches:
            raise errors.TraitNotFoundError(f"{self.name} has no trait named `{trait}`.")

        if len(matches) == 1:
            found_trait, rating = matches[0]
            if not self.is_vampire and found_trait in VChar.VAMPIRE_TRAITS:
                raise errors.TraitNotFoundError(f"Only vampires may use `{found_trait}`.")

            if exact and trait.lower() != found_trait.lower():
                raise errors.TraitNotFoundError(f"{self.name} has no trait named `{trait}`.")

            # Convert trackers to a rating
            if isinstance(rating, str):
                rating = rating.count(DAMAGE.none)
            return SimpleNamespace(name=found_trait, rating=rating)

        # We found multiple matches

        # We don't want to display vampire terms as an option if it isn't a vampire
        if not self.is_vampire:
            matches = [match for match in matches if match[0] not in VChar.VAMPIRE_TRAITS]
            if len(matches) == 1:
                # Removing the vampire traits may have got us down to zero
                return SimpleNamespace(name=matches[0][0], rating=matches[0][1])

        matches = map(lambda t: t[0], matches)
        raise errors.AmbiguousTraitError(trait, matches)


    def add_trait(self, trait: str, rating: int):
        """
        Add a trait to the collection.
        Raises TraitAlreadyExistsError if the trait already exists.
        """
        if trait.lower() in map(lambda t: t.lower(), self.traits.keys()):
            raise errors.TraitAlreadyExistsError(f"You already have a trait named `{trait}`.")

        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { f"traits.{trait}": rating } })
        self._params["traits"][trait] = rating


    def update_trait(self, trait: str, new_rating: int):
        """
        Update a given trait.
        Raises TraitNotFoundError if the trait does not exist.
        """
        if trait.lower() in map(lambda t: t.lower(), UNIVERSAL_TRAITS):
            err = f"`{trait}` is an automatic trait that cannot be modified."
            raise errors.TraitAlreadyExistsError(err)

        trait = self.find_trait(trait, exact=True).name
        VChar._CHARS.update_one({ "_id": self.id }, { "$set": { f"traits.{trait}": new_rating } })
        self._params["traits"][trait] = new_rating


    def delete_trait(self, trait: str):
        """
        Delete a trait.
        Raises TraitNotFoundError if the trait doesn't exist.
        """
        trait = self.find_trait(trait, exact=True).name
        VChar._CHARS.update_one({ "_id": self.id }, { "$unset": { f"traits.{trait}": "" } })


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
        raw_macros = list(
            VChar._MACROS.find({ "charid": self.id }, { "_id": 0, "charid": 0 })
                .collation({ "locale": "en", "strength": 2 })
                .sort("name")
        )

        # All characters have a hunger stat in the background, but we only care
        # about it if the character is a vampire
        for macro in raw_macros:
            if self.splat != "vampire":
                macro["hunger"] = False
            if not "staining" in macro:
                macro["staining"] = "show"

        return [SimpleNamespace(**macro) for macro in raw_macros]


    def find_macro(self, macro):
        """
        Return a macro object.
        Raises MacroNotFoundError if the macro wasn't found.
        """
        matches = self.__find_items(VChar._MACROS, macro, exact=True)
        if not matches:
            raise errors.MacroNotFoundError(f"{self.name} has no macro named `{macro}`.")

        macro = matches[0] # We do not allow multiple macros of the same name, so this is safe
        if self.splat != "vampire":
            macro["hunger"] = False

        if "staining" not in macro:
            macro["staining"] = "show"

        return SimpleNamespace(**macro)


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
        if self.__item_exists(VChar._MACROS, macro):
            raise errors.MacroAlreadyExistsError(f"You already have a macro named `{macro}`.")

        macro_query = {
            "charid": self.id,
            "name": macro,
            "pool": list(map(str, pool)),
            "rouses": rouses,
            "reroll_rouses": reroll_rouses,
            "staining": staining,
            "hunger": hunger,
            "difficulty": difficulty,
            "comment": comment
        }
        VChar._MACROS.insert_one(macro_query)


    def update_macro(self, macro: str, update: dict):
        """Update a macro."""
        query = { "name": { "$regex": re.compile(f"^{macro}$", re.IGNORECASE) }, "charid": self.id }
        VChar._MACROS.update_one(query, { "$set": update })


    def delete_macro(self, macro):
        """
        Delete a macro.
        Raises MacroNotFoundError if the macro doesn't exist.
        """
        macro = self.find_macro(macro) # For getting the exact name
        VChar._MACROS.delete_one({ "charid": self.id, "name": macro.name })


    # Specialized mutators

    def set_damage(self, tracker: str, severity: str, amount: int, wrap=False):
        """
        Set the current damage level.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): DAMAGE.superficial or DAMAGE.aggravated
            amount (int): The amount to set it to
        """
        if not severity in [DAMAGE.superficial, DAMAGE.aggravated]:
            raise SyntaxError("Severity must be superficial or aggravated.")
        if not tracker in ["health", "willpower"]:
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = self._params[tracker]
        sup = cur_track.count(DAMAGE.superficial)
        agg = cur_track.count(DAMAGE.aggravated)

        if severity == DAMAGE.superficial:
            sup = amount

            if wrap:
                overflow = sup + agg - len(cur_track)
                if overflow > 0:
                    agg += overflow
        else:
            agg = amount

        unhurt = (len(cur_track) - sup - agg) * DAMAGE.none
        sup = sup * DAMAGE.superficial
        agg = agg * DAMAGE.aggravated

        new_track = unhurt + sup + agg
        new_track = new_track[-len(cur_track):] # Shrink it if necessary

        if tracker == "health":
            self.health = new_track
        else:
            self.willpower = new_track

        # Log it!
        old_agg = cur_track.count(DAMAGE.aggravated)
        old_sup = cur_track.count(DAMAGE.superficial)
        new_agg = new_track.count(DAMAGE.aggravated)
        new_sup = new_track.count(DAMAGE.superficial)

        self.__update_log(f"{tracker}_superficial", old_sup, new_sup)
        self.__update_log(f"{tracker}_aggravated", old_agg, new_agg)


    def apply_damage(self, tracker: str, severity: str, delta: int):
        """
        Apply Superficial damage.
        Args:
            tracker (str): "willpower" or "health"
            severity (str): DAMAGE.superficial or DAMAGE.aggravated
            delta (int): The amount to apply
        If the damage exceeds the tracker, it will wrap around to aggravated.
        """
        if not severity in [DAMAGE.superficial, DAMAGE.aggravated]:
            raise SyntaxError("Severity must be superficial or aggravated.")
        if not tracker in ["health", "willpower"]:
            raise SyntaxError("Tracker must be health or willpower.")

        cur_track = self._params[tracker]
        cur_dmg = cur_track.count(severity)
        new_dmg = cur_dmg + delta

        self.set_damage(tracker, severity, new_dmg, wrap=True)


    # Misc

    def delete_character(self) -> bool:
        """Delete this character and all associated traits and macros."""
        VChar._MACROS.delete_many({ "charid": self.id })
        return VChar._CHARS.delete_one({ "_id": self.id }).acknowledged


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

        VChar._CHARS.update_one({ "_id": self.id }, { "$inc": { f"log.{key}": increment } })


    def log_injury(self, injury: str):
        """Log a crippling injury."""
        VChar._CHARS.update_one({ "_id": self.id }, { "$push": { "injuries": injury } })


    # Helpers

    def __find_items(self, collection, name, exact=False):
        """Find an item in the collection. Raises no exceptions."""
        query = { "charid": self.id, "name": name }
        exact_match = list(collection.find(query, { "_id": 0, "charid": 0 }).collation({
            'locale': 'en',
            'strength': 2
            }
        ))

        if len(exact_match) == 1:
            return exact_match

        if not exact: # Fallback; try and get closest unambiguous
            query = {
                "charid": self.id,
                "name": {
                    "$regex": re.compile("^" + name, re.IGNORECASE)
                }
            }
            return list(collection.find(query, { "_id": 0, "charid": 0 }))

        return []


    def __item_exists(self, collection, name) -> bool:
        """
        Check whether an item by a given name exists in the collection.
        The match is case-insensitive but otherwise exact.
        """
        query = {
            "charid": self.id,
            "name": { "$regex": re.compile("^" + name + "$", re.IGNORECASE) }
        }
        return collection.count_documents(query) > 0


    def __update_log(self, key, old_value, new_value):
        """
        Updates the character log.
        Args:
            key (str): The key to be updated
            addition (int): The amount to increase it by
        """
        if new_value > old_value:
            delta = new_value - old_value
            VChar._CHARS.update_one({ "_id": self.id }, { "$inc": { f"log.{key}": delta } })


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
                VChar._MACROS = mongo.inconnu.macros
