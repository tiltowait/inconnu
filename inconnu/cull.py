"""inconnu/cull.py - Cull inactive players and guilds."""

import os
from datetime import datetime, timedelta
from operator import itemgetter

import pymongo

from .vchar import VChar


class Culler:
    """A class for culling inactive characters and guilds."""

    _CLIENT = None
    _GUILDS = None
    _CHARACTERS = None


    @classmethod
    def cull(cls, days=30):
        """Cull inactive guilds, characters, and macros."""
        Culler._prepare()

        past = datetime.utcnow() - timedelta(days=days)
        guilds = Culler._GUILDS.find({ "left": { "$lt": past } }, { "guild": 1 })
        guilds = list(map(itemgetter("guild"), guilds))

        characters = Culler._CHARACTERS.find({
            "$or": [
                { "guild": { "$in": guilds } },
                { "log.left": { "$lt": past } }
            ]
        }, { "_id": 1 })
        characters = list(map(itemgetter("_id"), characters))

        for guild in guilds:
            #Culler._GUILDS.delete_one({ "guild": guild })
            print("Deleting guild", guild)

        for character in characters:
            character = VChar.fetch(0, 0, str(character))
            print("Deleting", character.name)
            #character.delete_character()


    @classmethod
    def _prepare(cls):
        """Prepare the database collections."""
        try:
            Culler._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            Culler._CLIENT = None
        finally:
            if Culler._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                Culler._CLIENT = mongo
                Culler._GUILDS = mongo.inconnu.guilds
                Culler._CHARACTERS = mongo.inconnu.characters
